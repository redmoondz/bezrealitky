import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useCallback, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { api } from '../api'
import { useMainButton } from '../hooks/useMainButton'
import { confirmAction, hapticNotification } from '../telegram'
import type { SyncSummary } from '../types'

function SummaryNote({ summary }: { summary: SyncSummary }) {
  const newNote = summary.new_count ? `${summary.new_count} new` : 'no new matches'
  return (
    <p className="listing-card__meta">
      Synced {summary.synced} listing(s) ({newNote}).
      {summary.failures ? ` ${summary.failures} publication(s) failed to parse.` : ''}
    </p>
  )
}

export default function SearchSettings() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const search = useQuery({ queryKey: ['search'], queryFn: api.getSearch })

  const [urlInput, setUrlInput] = useState('')
  const [priceFrom, setPriceFrom] = useState('')
  const [priceTo, setPriceTo] = useState('')
  const [delay, setDelay] = useState('')
  const [timeout_, setTimeout_] = useState('')
  const [maxRetries, setMaxRetries] = useState('')
  const [summary, setSummary] = useState<SyncSummary | null>(null)
  const [error, setError] = useState<string | null>(null)

  const refreshAfterRun = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['queue'] })
    queryClient.invalidateQueries({ queryKey: ['charts'] })
  }, [queryClient])

  const runNow = useMutation({
    mutationFn: api.runSearch,
    onSuccess: (result) => {
      setError(null)
      setSummary(result)
      hapticNotification('success')
      refreshAfterRun()
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : 'Could not run the scraper.')
      hapticNotification('error')
    },
  })

  const saveAndRun = useMutation({
    mutationFn: () =>
      api.updateSearch({
        url: urlInput.trim() || undefined,
        price_from: priceFrom.trim() ? Number(priceFrom) : undefined,
        price_to: priceTo.trim() ? Number(priceTo) : undefined,
        delay: delay.trim() ? Number(delay) : undefined,
        timeout: timeout_.trim() ? Number(timeout_) : undefined,
        max_retries: maxRetries.trim() ? Number(maxRetries) : undefined,
      }),
    onSuccess: (result) => {
      setError(null)
      setSummary(result)
      setUrlInput('')
      queryClient.invalidateQueries({ queryKey: ['search'] })
      hapticNotification('success')
      refreshAfterRun()
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : 'Could not update your search.')
      hapticNotification('error')
    },
  })

  useMainButton({
    text: saveAndRun.isPending ? 'Saving…' : 'Save & run',
    onClick: () => saveAndRun.mutate(),
    loading: saveAndRun.isPending,
  })

  const resetOnboarding = useMutation({
    mutationFn: api.resetOnboarding,
    onSuccess: () => {
      hapticNotification('success')
      queryClient.invalidateQueries({ queryKey: ['me'] })
      navigate('/onboarding')
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : 'Could not reset onboarding.')
      hapticNotification('error')
    },
  })

  async function onRestartOnboarding() {
    const confirmed = await confirmAction(
      'Restart onboarding? This clears your saved search and preferences — you’ll set them up again from scratch.',
    )
    if (confirmed) resetOnboarding.mutate()
  }

  return (
    <div className="stack">
      <h1 className="screen-title">Search</h1>

      <div className="card">
        <p className="listing-card__meta">Your current saved search</p>
        {search.isLoading ? (
          <p>Loading…</p>
        ) : (
          <p style={{ wordBreak: 'break-all' }}>{search.data?.url}</p>
        )}
        <button
          type="button"
          className="btn btn--ghost btn--block"
          disabled={runNow.isPending}
          onClick={() => runNow.mutate()}
        >
          {runNow.isPending ? 'Running…' : 'Run now'}
        </button>
      </div>

      {error && <p className="listing-card__meta">{error}</p>}
      {summary && <SummaryNote summary={summary} />}

      <div className="card stack">
        <p className="listing-card__meta">Paste a new search URL, or leave blank to keep the current one</p>
        <div className="field">
          <label htmlFor="new-url">Search URL</label>
          <input
            id="new-url"
            value={urlInput}
            onChange={(event) => setUrlInput(event.target.value)}
            placeholder="https://www.bezrealitky.com/search?..."
          />
        </div>
        <div className="field-grid">
          <div className="field">
            <label htmlFor="price-from">Price from</label>
            <input
              id="price-from"
              inputMode="numeric"
              value={priceFrom}
              onChange={(event) => setPriceFrom(event.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="price-to">Price to</label>
            <input
              id="price-to"
              inputMode="numeric"
              value={priceTo}
              onChange={(event) => setPriceTo(event.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="delay">Delay (s)</label>
            <input
              id="delay"
              inputMode="decimal"
              value={delay}
              onChange={(event) => setDelay(event.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="timeout">Timeout (s)</label>
            <input
              id="timeout"
              inputMode="decimal"
              value={timeout_}
              onChange={(event) => setTimeout_(event.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="max-retries">Max retries</label>
            <input
              id="max-retries"
              inputMode="numeric"
              value={maxRetries}
              onChange={(event) => setMaxRetries(event.target.value)}
            />
          </div>
        </div>
        <button
          type="button"
          className="btn btn--primary btn--block"
          disabled={saveAndRun.isPending}
          onClick={() => saveAndRun.mutate()}
        >
          {saveAndRun.isPending ? 'Saving…' : 'Save & run'}
        </button>
      </div>

      <div className="card stack">
        <p className="listing-card__meta">Redo the setup wizard from scratch, same as the bot's /onboarding command</p>
        <button
          type="button"
          className="btn btn--ghost btn--block"
          disabled={resetOnboarding.isPending}
          onClick={onRestartOnboarding}
        >
          {resetOnboarding.isPending ? 'Resetting…' : 'Restart onboarding'}
        </button>
      </div>
    </div>
  )
}
