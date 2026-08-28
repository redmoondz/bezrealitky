import type { ListingCard } from '../types'
import { formatFloor, formatPrice, petsLabel } from '../utils/listingFormat'

// Mirrors src/scoring.py's TOP_MATCH_THRESHOLD (25) — the bot shows the same
// "Top match" badge in bot/formatting.py::_top_match_badge.
const TOP_MATCH_THRESHOLD = 25

interface Props {
  card: ListingCard
  onOpenDetail: () => void
}

export default function ListingCardView({ card, onOpenDetail }: Props) {
  const photo = card.images[0]
  return (
    <div className="stack">
      <button type="button" className="listing-card__photos" onClick={onOpenDetail}>
        {photo ? (
          <img src={photo} alt={card.name || 'Listing photo'} width={800} height={600} />
        ) : (
          <div className="listing-card__photos--empty">🏠</div>
        )}
      </button>
      <div className="stack" style={{ gap: 4 }}>
        {card.score >= TOP_MATCH_THRESHOLD && <span className="badge">⭐ Top match</span>}
        <h2 className="listing-card__name">{card.name || 'Untitled listing'}</h2>
        <div className="listing-card__price">{formatPrice(card.total_price, card.currency)}</div>
        <div className="listing-card__meta">
          {card.area != null ? `${card.area} m²` : '—'} · {card.format || '—'} · Floor {formatFloor(card)}
        </div>
        <div className="listing-card__meta">
          🐾 Pets: {petsLabel(card.pets_friendly)} · 📍 {card.location || '—'}
        </div>
        {card.tags.length > 0 && (
          <div className="row row--wrap">
            {card.tags.map((tag) => (
              <span key={tag} className="chip">
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
