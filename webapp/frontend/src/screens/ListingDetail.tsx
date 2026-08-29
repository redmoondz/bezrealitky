import { useQuery } from '@tanstack/react-query'
import 'leaflet/dist/leaflet.css'
import { useLayoutEffect, useRef, useState } from 'react'
import { MapContainer, Marker, TileLayer } from 'react-leaflet'
import { useLocation, useParams } from 'react-router-dom'

import { api } from '../api'
import type { RectLike } from '../components/SwipeCard'
import { useBackButton } from '../hooks/useBackButton'
import type { ListingCard, ListingDetail as ListingDetailData } from '../types'
import { formatFloor, formatPrice, petsLabel } from '../utils/listingFormat'

const TOP_MATCH_THRESHOLD = 25
// Above this many photos, dots would overcrowd the strip — the counter alone stays legible.
const MAX_DOTS = 10
const EXPAND_DURATION_MS = 420

interface DetailTransitionState {
  originRect?: RectLike
  card?: ListingCard
}

export default function ListingDetail() {
  const { listingId } = useParams<{ listingId: string }>()
  const location = useLocation()
  const transition = (location.state as DetailTransitionState | null) ?? null
  useBackButton()
  const [activeIndex, setActiveIndex] = useState(0)
  const carouselRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  const detail = useQuery({
    queryKey: ['listing', listingId],
    queryFn: () => api.listing(listingId as string),
    enabled: Boolean(listingId),
  })

  // The "unfold" transition: Browse hands us the tapped card's on-screen rect
  // (captured the instant it was tapped) via router state. We clip this
  // page's own layout down to a window matching that rect, then widen the
  // window to the full page on the next frame — the page visibly grows out
  // of the card instead of just appearing. Deliberately clip-path (a window
  // that widens) rather than a scale transform: the card is short and this
  // page can be much taller (description, map), so scaling would visibly
  // squash all the text and photos for the duration of the animation. Runs
  // once against the rect captured at tap time, not on every render (hence
  // the empty deps array below).
  useLayoutEffect(() => {
    const origin = transition?.originRect
    const el = containerRef.current
    if (!origin || !el) return
    const final = el.getBoundingClientRect()
    if (final.width === 0 || final.height === 0) return

    const top = Math.max(0, origin.top - final.top)
    const left = Math.max(0, origin.left - final.left)
    const right = Math.max(0, final.width - left - origin.width)
    const bottom = Math.max(0, final.height - top - origin.height)

    el.style.willChange = 'clip-path, opacity'
    el.style.transition = 'none'
    el.style.clipPath = `inset(${top}px ${right}px ${bottom}px ${left}px round 18px)`
    el.style.opacity = '0.85'

    let raf2 = 0
    let cleanupTimer = 0
    const raf1 = requestAnimationFrame(() => {
      raf2 = requestAnimationFrame(() => {
        el.style.transition = `clip-path ${EXPAND_DURATION_MS}ms cubic-bezier(0.16, 1, 0.3, 1), opacity ${Math.round(EXPAND_DURATION_MS * 0.6)}ms ease-out`
        el.style.clipPath = 'inset(0px 0px 0px 0px round 0px)'
        el.style.opacity = '1'
        cleanupTimer = window.setTimeout(() => {
          el.style.transition = ''
          el.style.clipPath = ''
          el.style.opacity = ''
          el.style.willChange = ''
        }, EXPAND_DURATION_MS + 50)
      })
    })
    return () => {
      cancelAnimationFrame(raf1)
      cancelAnimationFrame(raf2)
      clearTimeout(cleanupTimer)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function scrollToIndex(index: number) {
    const el = carouselRef.current
    if (!el) return
    el.scrollTo({ left: index * el.clientWidth, behavior: 'smooth' })
  }

  function onCarouselScroll() {
    const el = carouselRef.current
    if (!el || el.clientWidth === 0) return
    setActiveIndex(Math.round(el.scrollLeft / el.clientWidth))
  }

  // `full` only arrives once /listings/:id resolves (description, translation
  // status, coordinates). Everything else (photos, name, price, meta, tags)
  // is already on the summary card Browse handed us, so the expand
  // animation has real content to grow into instead of a bare spinner.
  const full = detail.data
  const row: ListingCard | ListingDetailData | undefined = full ?? transition?.card ?? undefined

  if (!row) {
    if (detail.isLoading) return <p>Loading…</p>
    return <p>Listing not found.</p>
  }

  return (
    <div className="stack" ref={containerRef}>
      {row.images.length > 0 ? (
        <div className="detail-photo-frame">
          <div className="detail-photo-carousel" ref={carouselRef} onScroll={onCarouselScroll}>
            {row.images.map((src) => (
              <img key={src} src={src} alt={row.name || 'Listing photo'} width={800} height={600} />
            ))}
          </div>
          {row.images.length > 1 && (
            <>
              <div className="detail-photo-counter">
                {activeIndex + 1} / {row.images.length}
              </div>
              {activeIndex > 0 && (
                <button
                  type="button"
                  className="detail-photo-nav detail-photo-nav--prev"
                  onClick={() => scrollToIndex(activeIndex - 1)}
                  aria-label="Previous photo"
                >
                  ‹
                </button>
              )}
              {activeIndex < row.images.length - 1 && (
                <button
                  type="button"
                  className="detail-photo-nav detail-photo-nav--next"
                  onClick={() => scrollToIndex(activeIndex + 1)}
                  aria-label="Next photo"
                >
                  ›
                </button>
              )}
              {row.images.length <= MAX_DOTS && (
                <div className="listing-card__photo-dots">
                  {row.images.map((src, i) => (
                    <span key={src} className={i === activeIndex ? 'active' : undefined} />
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      ) : (
        <div className="listing-card__photos listing-card__photos--empty">🏠</div>
      )}

      <div className="stack" style={{ gap: 4 }}>
        {row.score >= TOP_MATCH_THRESHOLD && <span className="badge">⭐ Top match</span>}
        <h1 className="listing-card__name">{row.name || 'Untitled listing'}</h1>
        <div className="listing-card__price">{formatPrice(row.total_price, row.currency)}</div>
        <div className="listing-card__meta">
          Deposit: {formatPrice(row.refundable_deposit, row.currency)}
        </div>
        <div className="listing-card__meta">
          {row.area != null ? `${row.area} m²` : '—'} · {row.format || '—'} · Floor {formatFloor(row)}
        </div>
        <div className="listing-card__meta">Furnished: {row.fully_furnished || '—'}</div>
        <div className="listing-card__meta">
          🐾 Pets: {petsLabel(row.pets_friendly)} · 📍 {row.location || '—'}
        </div>
        {row.tags.length > 0 && (
          <div className="row row--wrap">
            {row.tags.map((tag) => (
              <span key={tag} className="chip">
                {tag}
              </span>
            ))}
          </div>
        )}
        {detail.isError && !full && (
          <p className="listing-card__meta">⚠️ Couldn't load the full listing — showing what we had.</p>
        )}
      </div>

      {full?.description && (
        <div className="card">
          {!full.translation_ok && (
            <p className="listing-card__meta">
              ⚠️ Translation temporarily unavailable — showing the original text.
            </p>
          )}
          <p className="detail-description">{full.description}</p>
        </div>
      )}

      {full?.latitude != null && full?.longitude != null && (
        <div className="map-frame">
          <MapContainer
            center={[full.latitude, full.longitude]}
            zoom={15}
            style={{ height: '100%', width: '100%' }}
            scrollWheelZoom={false}
          >
            <TileLayer
              attribution="&copy; OpenStreetMap contributors"
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            <Marker position={[full.latitude, full.longitude]} />
          </MapContainer>
        </div>
      )}

      <a className="btn btn--primary btn--block" href={row.url} target="_blank" rel="noreferrer">
        Open on Bezrealitky
      </a>
    </div>
  )
}
