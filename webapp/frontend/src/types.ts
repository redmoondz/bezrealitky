// Mirrors webapp/backend/schemas.py — one interface per response model.

export interface MeResponse {
  id: number
  language: string
  has_search: boolean
}

export interface LanguageOption {
  code: string
  label: string
}

export interface SyncSummary {
  synced: number
  failures: number
  new_count: number
}

export interface SearchUpdateResponse extends SyncSummary {
  new_url: string
}

export interface SearchResponse {
  url: string
}

export interface ListingCard {
  listing_id: string
  name: string
  total_price: number | null
  currency: string
  refundable_deposit: number | null
  area: number | null
  format: string
  fully_furnished: string
  floor_number: number | null
  floor_total: number | null
  floor: string
  pets_friendly: boolean | null
  location: string
  url: string
  images: string[]
  score: number
  tags: string[]
}

export interface ListingDetail extends ListingCard {
  description: string
  translation_ok: boolean
  latitude: number | null
  longitude: number | null
}

export interface ListingQueuePage {
  total: number
  offset: number
  item: ListingCard | null
}

export interface ChartOption {
  key: string
  label: string
}

export interface HistogramData {
  values: number[]
}

export interface ScatterData {
  points: { area: number; price: number; url: string }[]
}

export interface BreakdownData {
  counts: { label: string; value: number }[]
}

export interface ChartDataResponse {
  key: string
  label: string
  kind: 'histogram' | 'scatter' | 'pie'
  data: HistogramData | ScatterData | BreakdownData
}

export interface HelpResponse {
  text: string
}

export type Reaction = 'like' | 'dislike'

export interface SearchUpdatePayload {
  url?: string
  price_from?: number
  price_to?: number
  delay?: number
  timeout?: number
  max_retries?: number
}

export interface PreferencesPayload {
  wants_pets?: boolean
  budget_total_price?: number
  min_area_m2?: number
}
