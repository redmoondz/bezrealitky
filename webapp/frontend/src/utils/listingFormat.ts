import type { ListingCard } from '../types'

export function formatPrice(price: number | null, currency: string): string {
  if (price == null) return '—'
  return `${price.toLocaleString()} ${currency}`.trim()
}

export function formatFloor(card: Pick<ListingCard, 'floor_number' | 'floor_total' | 'floor'>): string {
  if (card.floor_number != null) {
    return card.floor_total != null ? `${card.floor_number}/${card.floor_total}` : `${card.floor_number}`
  }
  return card.floor || '—'
}

export function petsLabel(value: boolean | null): string {
  if (value === true) return 'Yes'
  if (value === false) return 'No'
  return 'Unknown'
}
