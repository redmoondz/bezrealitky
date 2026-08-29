import { useQuery } from '@tanstack/react-query'
import 'leaflet/dist/leaflet.css'
import { useRef, useState } from 'react'
import { MapContainer, Marker, TileLayer } from 'react-leaflet'
import { useParams } from 'react-router-dom'

import { api } from '../api'
import { useBackButton } from '../hooks/useBackButton'
import { formatFloor, formatPrice, petsLabel } from '../utils/listingFormat'

const TOP_MATCH_THRESHOLD = 25
// Above this many photos, dots would overcrowd the strip — the counter alone stays legible.
const MAX_DOTS = 10

export default function ListingDetail() {
  const { listingId } = useParams<{ listingId: string }>()
  useBackButton()
  const [activeIndex, setActiveIndex] = useState(0)
  const carouselRef = useRef<HTMLDivElement>(null)

  const detail = useQuery({
    queryKey: ['listing', listingId],
    queryFn: () => api.listing(listingId as string),
    enabled: Boolean(listingId),
  })

  if (detail.isLoading) return <p>Loading…</p>
  if (detail.isError || !detail.data) return <p>Listing not found.</p>

  const row = detail.data

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

  return (
    <div className="stack">
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
      </div>

      {row.description && (
        <div className="card">
          {!row.translation_ok && (
            <p className="listing-card__meta">
              ⚠️ Translation temporarily unavailable — showing the original text.
            </p>
          )}
          <p className="detail-description">{row.description}</p>
        </div>
      )}

      {row.latitude != null && row.longitude != null && (
        <div className="map-frame">
          <MapContainer
            center={[row.latitude, row.longitude]}
            zoom={15}
            style={{ height: '100%', width: '100%' }}
            scrollWheelZoom={false}
          >
            <TileLayer
              attribution="&copy; OpenStreetMap contributors"
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            <Marker position={[row.latitude, row.longitude]} />
          </MapContainer>
        </div>
      )}

      <a className="btn btn--primary btn--block" href={row.url} target="_blank" rel="noreferrer">
        Open on Bezrealitky
      </a>
    </div>
  )
}
