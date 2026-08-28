import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { api } from '../api'
import ListingCardView from '../components/ListingCardView'

export default function Liked() {
  const [offset, setOffset] = useState(0)
  const navigate = useNavigate()

  const page = useQuery({ queryKey: ['liked', offset], queryFn: () => api.liked(offset) })

  if (page.isLoading) return <p>Loading…</p>
  if (page.isError || !page.data) return <p>Could not load liked listings.</p>

  const { item, total } = page.data

  if (!item) {
    return (
      <div className="centered-message">
        <h2>No liked listings yet</h2>
        <p>Listings you like in Browse show up here.</p>
      </div>
    )
  }

  return (
    <div className="stack">
      <h1 className="screen-title">Liked</h1>
      <ListingCardView card={item} onOpenDetail={() => navigate(`/listing/${item.listing_id}`)} />
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
