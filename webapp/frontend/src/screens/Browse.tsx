import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { api } from '../api'
import SwipeCard from '../components/SwipeCard'
import type { RectLike, SwipeDirection, SwipeTransform } from '../components/SwipeCard'
import { hapticImpact } from '../telegram'
import type { ListingCard, Reaction } from '../types'

interface ExitingCard {
  card: ListingCard
  direction: SwipeDirection
  transform: SwipeTransform
  animDone: boolean
}

export default function Browse() {
  const [offset, setOffset] = useState(0)
  const [rawExiting, setExiting] = useState<ExitingCard | null>(null)
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const page = useQuery({ queryKey: ['queue', offset], queryFn: () => api.queue(offset) })
  const nextPage = useQuery({
    queryKey: ['queue', offset + 1],
    queryFn: () => api.queue(offset + 1),
    enabled: (page.data?.total ?? 0) > offset + 1,
  })

  const react = useMutation({
    mutationFn: ({ id, reaction }: { id: string; reaction: Reaction }) => api.react(id, reaction),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['queue'] })
      queryClient.invalidateQueries({ queryKey: ['liked'] })
    },
  })

  const currentItem = page.data?.item ?? null
  const nextItem = nextPage.data?.item ?? null

  // The live slot is promoted to the (already-prefetched) next item the
  // instant a swipe is confirmed, so the fly-out overlay never has to wait on
  // the network. Once the queue has actually moved past the swiped listing,
  // the overlay's animation has had long enough to finish — treat the
  // override as spent and let the live slot fall back to query-driven data.
  // (Derived during render rather than mirrored into state via an effect —
  // the raw state is simply overwritten wholesale by the next swipe.)
  const exitSpent = Boolean(
    rawExiting?.animDone && currentItem?.listing_id !== rawExiting.card.listing_id,
  )
  const exiting = exitSpent ? null : rawExiting

  if (page.isLoading) return <p>Loading…</p>
  if (page.isError || !page.data) return <p>Could not load listings.</p>

  const { total } = page.data
  const liveItem = exiting ? nextItem : currentItem
  const peekItem = exiting ? null : nextItem

  function confirmSwipe(direction: SwipeDirection, transform: SwipeTransform) {
    if (!currentItem || exiting) return
    hapticImpact('light')
    setExiting({ card: currentItem, direction, transform, animDone: false })
    react.mutate({ id: currentItem.listing_id, reaction: direction === 'right' ? 'like' : 'dislike' })
  }

  function onReactButton(reaction: Reaction) {
    confirmSwipe(reaction === 'like' ? 'right' : 'left', { x: 0, y: 0, rotate: 0 })
  }

  function openDetail(item: ListingCard, originRect: RectLike) {
    // Kicked off alongside the expand animation so the full detail (which
    // adds description/map on top of what `card` already carries) is likely
    // ready by the time the card finishes unfolding.
    queryClient.prefetchQuery({ queryKey: ['listing', item.listing_id], queryFn: () => api.listing(item.listing_id) })
    navigate(`/listing/${item.listing_id}`, { state: { originRect, card: item } })
  }

  if (!liveItem && !exiting) {
    const emptyQueue = total === 0
    return (
      <div className="centered-message">
        <h2>{emptyQueue ? 'No listings yet' : "You're all caught up"}</h2>
        <p>
          {emptyQueue
            ? 'Nothing matches your saved search yet. Try Search → Run now, or adjust your search.'
            : "You've been through every listing in your queue."}
        </p>
        {!emptyQueue && (
          <button className="btn btn--ghost" onClick={() => setOffset(0)}>
            Back to start
          </button>
        )}
      </div>
    )
  }

  return (
    <div className="stack">
      <h1 className="screen-title">Browse</h1>
      <div className="swipe-deck">
        {peekItem && <SwipeCard key={`peek-${peekItem.listing_id}`} card={peekItem} variant="stacked" />}
        {liveItem && (
          <SwipeCard
            key={`live-${liveItem.listing_id}`}
            card={liveItem}
            variant="live"
            disabled={react.isPending}
            onOpenDetail={(rect) => openDetail(liveItem, rect)}
            onSwipeConfirmed={confirmSwipe}
          />
        )}
        {exiting && (
          <SwipeCard
            key={`exit-${exiting.card.listing_id}`}
            card={exiting.card}
            variant="overlay"
            initialTransform={exiting.transform}
            exitDirection={exiting.direction}
            onExitComplete={() => setExiting((cur) => (cur ? { ...cur, animDone: true } : cur))}
          />
        )}
      </div>
      <div className="listing-card__actions">
        <button
          type="button"
          className="btn btn--icon btn--dislike"
          disabled={react.isPending || !!exiting}
          onClick={() => onReactButton('dislike')}
        >
          👎
        </button>
        <button
          type="button"
          className="btn btn--icon btn--like"
          disabled={react.isPending || !!exiting}
          onClick={() => onReactButton('like')}
        >
          ❤️
        </button>
      </div>
      <div className="row row--between">
        <button
          type="button"
          className="btn btn--ghost"
          disabled={offset === 0 || !!exiting}
          onClick={() => setOffset(Math.max(0, offset - 1))}
        >
          ◂ Prev
        </button>
        <span className="listing-card__counter">
          {offset + 1} / {total}
        </span>
        <button
          type="button"
          className="btn btn--ghost"
          disabled={offset + 1 >= total || !!exiting}
          onClick={() => setOffset(offset + 1)}
        >
          Next ▸
        </button>
      </div>
    </div>
  )
}
