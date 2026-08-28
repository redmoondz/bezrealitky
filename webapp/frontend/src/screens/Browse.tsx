import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { api } from '../api'
import ListingCardView from '../components/ListingCardView'
import { hapticImpact } from '../telegram'
import type { Reaction } from '../types'

export default function Browse() {
  const [offset, setOffset] = useState(0)
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const page = useQuery({ queryKey: ['queue', offset], queryFn: () => api.queue(offset) })

  const react = useMutation({
    mutationFn: ({ id, reaction }: { id: string; reaction: Reaction }) => api.react(id, reaction),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['queue'] })
      queryClient.invalidateQueries({ queryKey: ['liked'] })
    },
  })

  if (page.isLoading) return <p>Loading…</p>
  if (page.isError || !page.data) return <p>Could not load listings.</p>

  const { item, total } = page.data

  if (!item) {
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

  const currentItem = item

  function onReact(reaction: Reaction) {
    hapticImpact('light')
    react.mutate({ id: currentItem.listing_id, reaction })
  }

  return (
    <div className="stack">
      <h1 className="screen-title">Browse</h1>
      <ListingCardView card={currentItem} onOpenDetail={() => navigate(`/listing/${currentItem.listing_id}`)} />
      <div className="listing-card__actions">
        <button
          type="button"
          className="btn btn--icon btn--dislike"
          disabled={react.isPending}
          onClick={() => onReact('dislike')}
        >
          👎
        </button>
        <button
          type="button"
          className="btn btn--icon btn--like"
          disabled={react.isPending}
          onClick={() => onReact('like')}
        >
          ❤️
        </button>
      </div>
      <div className="row row--between">
        <button
          type="button"
          className="btn btn--ghost"
          disabled={offset === 0}
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
          disabled={offset + 1 >= total}
          onClick={() => setOffset(offset + 1)}
        >
          Next ▸
        </button>
      </div>
    </div>
  )
}
