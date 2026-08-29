import { useEffect, useRef, useState } from 'react'

import type { ListingCard } from '../types'
import ListingCardView from './ListingCardView'

export interface SwipeTransform {
  x: number
  y: number
  rotate: number
}

export type SwipeDirection = 'left' | 'right'

// A plain, structured-clone-friendly stand-in for DOMRect — react-router's
// browser history state must survive history.pushState's serialization.
export interface RectLike {
  top: number
  left: number
  width: number
  height: number
}

// Tinder's own swipe mechanic: rotation is simply proportional to how far the
// card has been dragged horizontally, capped at MAX_ROTATION_DEG — the same
// model Marc Kremers described in "Prototyping a Tinder-like swiping
// mechanism" (the article the react-tinder-card library is based on).
const MAX_ROTATION_DEG = 20
const ROTATION_DISTANCE = 320 // px of drag needed to reach MAX_ROTATION_DEG
const SWIPE_DISTANCE_RATIO = 0.32 // fraction of card width that confirms a swipe
const FLICK_VELOCITY = 0.5 // px/ms — a fast short flick also confirms
const EXIT_DURATION_MS = 380
const RETURN_DURATION_MS = 320
const TAP_MOVE_TOLERANCE = 6 // px — below this, a pointer-up is a tap, not a drag

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}

interface DragState {
  pointerId: number
  startX: number
  startY: number
  lastX: number
  lastT: number
  velocity: number
  moved: boolean
}

interface Props {
  card: ListingCard
  variant: 'live' | 'stacked' | 'overlay'
  onOpenDetail?: (originRect: RectLike) => void
  onSwipeConfirmed?: (direction: SwipeDirection, transform: SwipeTransform) => void
  disabled?: boolean
  initialTransform?: SwipeTransform
  exitDirection?: SwipeDirection
  onExitComplete?: () => void
}

const REST: SwipeTransform = { x: 0, y: 0, rotate: 0 }

export default function SwipeCard({
  card,
  variant,
  onOpenDetail,
  onSwipeConfirmed,
  disabled,
  initialTransform,
  exitDirection,
  onExitComplete,
}: Props) {
  const cardRef = useRef<HTMLDivElement>(null)
  const dragRef = useRef<DragState | null>(null)
  const suppressNextClickRef = useRef(false)

  const [transform, setTransform] = useState<SwipeTransform>(initialTransform ?? REST)
  const [transitionMs, setTransitionMs] = useState(0)

  // Overlay cards start frozen at the exact spot the live card left off, then
  // launch off-screen on the next frame so the hand-off from drag to fling is
  // a continuous motion rather than a jump-cut.
  useEffect(() => {
    if (variant !== 'overlay') return
    const frame = requestAnimationFrame(() => {
      const width = cardRef.current?.offsetWidth || window.innerWidth
      const sign = exitDirection === 'left' ? -1 : 1
      setTransitionMs(EXIT_DURATION_MS)
      setTransform({
        x: sign * Math.max(window.innerWidth, width) * 1.4,
        y: (initialTransform?.y ?? 0) + 80,
        rotate: sign * (MAX_ROTATION_DEG + 10),
      })
    })
    // Belt-and-braces in case `transitionend` never fires (e.g. the tab was
    // backgrounded mid-animation) — an exiting overlay that never clears
    // would otherwise permanently block the next swipe.
    const fallback = setTimeout(() => onExitComplete?.(), EXIT_DURATION_MS + 150)
    return () => {
      cancelAnimationFrame(frame)
      clearTimeout(fallback)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [variant])

  function onPointerDown(event: React.PointerEvent) {
    if (variant !== 'live' || disabled) return
    event.currentTarget.setPointerCapture(event.pointerId)
    dragRef.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      lastX: event.clientX,
      lastT: performance.now(),
      velocity: 0,
      moved: false,
    }
    setTransitionMs(0)
  }

  function onPointerMove(event: React.PointerEvent) {
    const drag = dragRef.current
    if (!drag || drag.pointerId !== event.pointerId) return
    const dx = event.clientX - drag.startX
    const dy = event.clientY - drag.startY
    if (Math.abs(dx) > TAP_MOVE_TOLERANCE || Math.abs(dy) > TAP_MOVE_TOLERANCE) drag.moved = true

    const now = performance.now()
    const dt = now - drag.lastT
    if (dt > 0) drag.velocity = (event.clientX - drag.lastX) / dt
    drag.lastX = event.clientX
    drag.lastT = now

    const rotate = clamp((dx / ROTATION_DISTANCE) * MAX_ROTATION_DEG, -MAX_ROTATION_DEG, MAX_ROTATION_DEG)
    setTransform({ x: dx, y: dy * 0.4, rotate })
  }

  // The single entry point for "open the detail view" — called either
  // programmatically (a tap detected via pointer events, see endDrag below)
  // or natively (a button click from keyboard/screen-reader activation,
  // which never goes through a pointerdown and so isn't suppressed there).
  function handlePhotoClick() {
    if (variant !== 'live' || !cardRef.current) return
    const { top, left, width, height } = cardRef.current.getBoundingClientRect()
    onOpenDetail?.({ top, left, width, height })
  }

  function endDrag(event: React.PointerEvent) {
    const drag = dragRef.current
    if (!drag || drag.pointerId !== event.pointerId) return
    dragRef.current = null
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId)
    }

    const width = cardRef.current?.offsetWidth || 300
    const distanceRatio = Math.abs(transform.x) / width
    const isFlick = Math.abs(drag.velocity) > FLICK_VELOCITY
    const confirmed = drag.moved && (distanceRatio > SWIPE_DISTANCE_RATIO || isFlick)

    if (confirmed) {
      const direction: SwipeDirection = transform.x !== 0 ? (transform.x > 0 ? 'right' : 'left') : drag.velocity > 0 ? 'right' : 'left'
      onSwipeConfirmed?.(direction, transform)
      return
    }

    setTransitionMs(RETURN_DURATION_MS)
    setTransform(REST)

    // A tap (pointer never crossed the move tolerance) opens the detail view
    // right here rather than waiting for the native click that follows —
    // setPointerCapture on this element can retarget that click away from
    // the nested photo button, so it may never actually reach it. Either way
    // (handled here, or an aborted drag that shouldn't open anything), mark
    // the upcoming click as spent so it can't double-fire; self-clears
    // shortly after in case no click actually follows.
    suppressNextClickRef.current = true
    setTimeout(() => {
      suppressNextClickRef.current = false
    }, 400)
    if (event.type === 'pointerup' && !drag.moved) {
      handlePhotoClick()
    }
  }

  function onTransitionEnd(event: React.TransitionEvent) {
    if (event.target !== event.currentTarget) return
    onExitComplete?.()
  }

  function guardClick(event: React.MouseEvent) {
    if (suppressNextClickRef.current) {
      suppressNextClickRef.current = false
      event.preventDefault()
      event.stopPropagation()
      return
    }
    if (variant !== 'live') {
      event.preventDefault()
      event.stopPropagation()
    }
  }

  const likeOpacity =
    variant === 'overlay' ? (exitDirection === 'right' ? 1 : 0) : clamp(transform.x / (300 * SWIPE_DISTANCE_RATIO), 0, 1)
  const nopeOpacity =
    variant === 'overlay' ? (exitDirection === 'left' ? 1 : 0) : clamp(-transform.x / (300 * SWIPE_DISTANCE_RATIO), 0, 1)

  const style: React.CSSProperties =
    variant === 'stacked'
      ? { transform: 'scale(0.94) translateY(14px)', transition: 'none' }
      : {
          transform: `translate(${transform.x}px, ${transform.y}px) rotate(${transform.rotate}deg)`,
          transition: transitionMs ? `transform ${transitionMs}ms cubic-bezier(0.23, 1, 0.32, 1)` : 'none',
        }

  return (
    <div
      ref={cardRef}
      className={`swipe-card swipe-card--${variant}`}
      style={style}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={endDrag}
      onPointerCancel={endDrag}
      onClickCapture={guardClick}
      onTransitionEnd={variant === 'overlay' ? onTransitionEnd : undefined}
    >
      <div className="swipe-card__surface">
        <ListingCardView card={card} onOpenDetail={handlePhotoClick} />
        {variant !== 'stacked' && (
          <>
            <span className="swipe-card__stamp swipe-card__stamp--like" style={{ opacity: likeOpacity }}>
              LIKE
            </span>
            <span className="swipe-card__stamp swipe-card__stamp--nope" style={{ opacity: nopeOpacity }}>
              NOPE
            </span>
          </>
        )}
      </div>
    </div>
  )
}
