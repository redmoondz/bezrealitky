import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { api } from '../api'
import type { SyncSummary } from '../types'

type Step = 'language' | 'search-url' | 'pets' | 'budget' | 'area' | 'running' | 'done'

const STEP_ORDER: Step[] = ['language', 'search-url', 'pets', 'budget', 'area']

function ProgressDots({ step }: { step: Step }) {
  const index = STEP_ORDER.indexOf(step)
  if (index < 0) return null
  return (
    <div className="progress-dots">
      {STEP_ORDER.map((candidate, i) => (
        <span
          key={candidate}
          className={`progress-dots__dot${i === index ? ' progress-dots__dot--active' : ''}`}
        />
      ))}
    </div>
  )
}

export default function Onboarding() {
  const [step, setStep] = useState<Step>('language')
  const [searchUrlInput, setSearchUrlInput] = useState('')
  const [budgetInput, setBudgetInput] = useState('')
  const [areaInput, setAreaInput] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [summary, setSummary] = useState<SyncSummary | null>(null)
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const languages = useQuery({ queryKey: ['languages'], queryFn: api.languages })
  const setLanguage = useMutation({ mutationFn: (code: string) => api.setLanguage(code) })
  const setSearchUrl = useMutation({ mutationFn: (url?: string) => api.setOnboardingSearchUrl(url) })
  const setPreferences = useMutation({ mutationFn: api.setOnboardingPreferences })
  const finish = useMutation({
    mutationFn: api.finishOnboarding,
    onSuccess: (result) => {
      setSummary(result)
      setStep('done')
      queryClient.invalidateQueries({ queryKey: ['me'] })
    },
  })

  async function chooseLanguage(code: string) {
    setError(null)
    try {
      await setLanguage.mutateAsync(code)
      setStep('search-url')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save that language.')
    }
  }

  async function submitSearchUrl(useDefault: boolean) {
    setError(null)
    try {
      await setSearchUrl.mutateAsync(useDefault ? undefined : searchUrlInput)
      setStep('pets')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'That doesn’t look like a bezrealitky.com search link.')
    }
  }

  async function submitPets(wantsPets: boolean | null) {
    if (wantsPets !== null) await setPreferences.mutateAsync({ wants_pets: wantsPets })
    setStep('budget')
  }

  async function submitBudget(skip: boolean) {
    if (!skip) {
      const value = Number(budgetInput)
      if (Number.isFinite(value) && value > 0) {
        await setPreferences.mutateAsync({ budget_total_price: value })
      }
    }
    setStep('area')
  }

  async function submitArea(skip: boolean) {
    if (!skip) {
      const value = Number(areaInput)
      if (Number.isFinite(value) && value > 0) {
        await setPreferences.mutateAsync({ min_area_m2: value })
      }
    }
    setStep('running')
    finish.mutate()
  }

  if (step === 'running') {
    return <div className="centered-message">
      <h2>Saving your search…</h2>
      <p>Running the scraper now — this can take a little while the first time.</p>
    </div>
  }

  if (step === 'done' && summary) {
    return (
      <div className="centered-message">
        <h2>You’re all set</h2>
        <p>
          Synced {summary.synced} listing(s)
          {summary.new_count ? `, ${summary.new_count} new for you` : ''}.
          {summary.failures ? ` ${summary.failures} publication(s) failed to parse.` : ''}
        </p>
        <button className="btn btn--primary" onClick={() => navigate('/browse')}>
          Start browsing
        </button>
      </div>
    )
  }

  return (
    <div className="stack">
      <ProgressDots step={step} />
      {error && <p className="listing-card__meta">{error}</p>}

      {step === 'language' && (
        <div className="stack">
          <h1 className="screen-title">Choose a language</h1>
          <p className="listing-card__meta">Listing descriptions will be translated into this language.</p>
          <div className="option-list">
            {(languages.data ?? []).map((language) => (
              <button key={language.code} onClick={() => chooseLanguage(language.code)}>
                {language.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {step === 'search-url' && (
        <div className="stack">
          <h1 className="screen-title">Your search</h1>
          <p className="listing-card__meta">
            Open bezrealitky.com, set your filters, run the search, then paste the resulting URL here.
          </p>
          <div className="field">
            <label htmlFor="search-url">Search URL</label>
            <input
              id="search-url"
              value={searchUrlInput}
              onChange={(event) => setSearchUrlInput(event.target.value)}
              placeholder="https://www.bezrealitky.com/search?..."
            />
          </div>
          <button
            className="btn btn--primary btn--block"
            disabled={!searchUrlInput.trim() || setSearchUrl.isPending}
            onClick={() => submitSearchUrl(false)}
          >
            Use this search
          </button>
          <button className="btn btn--ghost btn--block" onClick={() => submitSearchUrl(true)}>
            Use the default search instead
          </button>
        </div>
      )}

      {step === 'pets' && (
        <div className="stack">
          <h1 className="screen-title">🐾 Pet-friendly?</h1>
          <p className="listing-card__meta">Do you have — or want — a place that's pet-friendly?</p>
          <div className="row">
            <button className="btn btn--primary" onClick={() => submitPets(true)}>
              Yes
            </button>
            <button className="btn btn--ghost" onClick={() => submitPets(false)}>
              No
            </button>
          </div>
          <button className="btn btn--ghost btn--block" onClick={() => submitPets(null)}>
            Skip
          </button>
        </div>
      )}

      {step === 'budget' && (
        <div className="stack">
          <h1 className="screen-title">💰 Budget</h1>
          <p className="listing-card__meta">
            Monthly budget, all costs included (rent + service + utilities). This only affects ranking.
          </p>
          <div className="field">
            <label htmlFor="budget">Budget</label>
            <input
              id="budget"
              inputMode="numeric"
              value={budgetInput}
              onChange={(event) => setBudgetInput(event.target.value)}
              placeholder="25000"
            />
          </div>
          <button className="btn btn--primary btn--block" onClick={() => submitBudget(false)}>
            Continue
          </button>
          <button className="btn btn--ghost btn--block" onClick={() => submitBudget(true)}>
            Skip
          </button>
        </div>
      )}

      {step === 'area' && (
        <div className="stack">
          <h1 className="screen-title">📐 Minimum size</h1>
          <p className="listing-card__meta">Any minimum size you need, in m²?</p>
          <div className="field">
            <label htmlFor="area">Minimum area (m²)</label>
            <input
              id="area"
              inputMode="numeric"
              value={areaInput}
              onChange={(event) => setAreaInput(event.target.value)}
              placeholder="40"
            />
          </div>
          <button className="btn btn--primary btn--block" onClick={() => submitArea(false)}>
            Continue
          </button>
          <button className="btn btn--ghost btn--block" onClick={() => submitArea(true)}>
            Skip
          </button>
        </div>
      )}
    </div>
  )
}
