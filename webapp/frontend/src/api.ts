import { getInitData } from './telegram'
import type {
  AdminNotifyPayload,
  AdminNotifyResult,
  AdminStats,
  AdminUser,
  ChartDataResponse,
  ChartOption,
  HelpResponse,
  LanguageOption,
  ListingDetail,
  ListingQueuePage,
  MeResponse,
  PreferencesPayload,
  Reaction,
  SearchResponse,
  SearchUpdatePayload,
  SearchUpdateResponse,
  SyncSummary,
} from './types'

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      'X-Telegram-Init-Data': getInitData(),
      ...init.headers,
    },
  })
  if (!response.ok) {
    let detail = response.statusText
    try {
      const body = (await response.json()) as { detail?: string }
      detail = body.detail ?? detail
    } catch {
      // No JSON body to read a detail message from — fall back to statusText.
    }
    throw new ApiError(response.status, detail)
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

const get = <T>(path: string): Promise<T> => request<T>(path)
const post = <T>(path: string, body?: unknown): Promise<T> =>
  request<T>(path, { method: 'POST', body: JSON.stringify(body ?? {}) })

export const api = {
  me: () => get<MeResponse>('/me'),
  languages: () => get<LanguageOption[]>('/languages'),
  setLanguage: (code: string) => post<{ ok: boolean }>('/language', { code }),
  help: () => get<HelpResponse>('/help'),

  setOnboardingSearchUrl: (url?: string) =>
    post<{ search_url: string }>('/onboarding/search-url', url ? { url } : {}),
  setOnboardingPreferences: (payload: PreferencesPayload) =>
    post<{ ok: boolean }>('/onboarding/preferences', payload),
  finishOnboarding: () => post<SyncSummary>('/onboarding/finish'),

  queue: (offset: number) => get<ListingQueuePage>(`/listings/queue?offset=${offset}`),
  liked: (offset: number) => get<ListingQueuePage>(`/liked?offset=${offset}`),
  listing: (id: string) => get<ListingDetail>(`/listings/${encodeURIComponent(id)}`),
  react: (id: string, reaction: Reaction) =>
    post<{ ok: boolean }>(`/listings/${encodeURIComponent(id)}/reaction`, { reaction }),

  getSearch: () => get<SearchResponse>('/search'),
  runSearch: () => post<SyncSummary>('/search/run'),
  updateSearch: (payload: SearchUpdatePayload) => post<SearchUpdateResponse>('/search', payload),

  charts: () => get<ChartOption[]>('/charts'),
  chartData: (key: string) => get<ChartDataResponse>(`/charts/${key}/data`),

  adminStats: () => get<AdminStats>('/admin/stats'),
  adminUsers: () => get<AdminUser[]>('/admin/users'),
  adminNotify: (payload: AdminNotifyPayload) => post<AdminNotifyResult>('/admin/notify', payload),
}
