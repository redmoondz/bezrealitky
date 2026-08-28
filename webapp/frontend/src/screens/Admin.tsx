import { useMutation, useQuery } from '@tanstack/react-query'
import { useState } from 'react'

import { api } from '../api'
import { confirmAction, hapticNotification } from '../telegram'
import type { AdminNotifyResult, AdminUser } from '../types'

function StatTile({ label, value }: { label: string; value: number }) {
  return (
    <div className="card" style={{ textAlign: 'center' }}>
      <div className="listing-card__price">{value}</div>
      <div className="listing-card__meta">{label}</div>
    </div>
  )
}

function userDisplayName(user: AdminUser): string {
  return [user.first_name, user.last_name].filter(Boolean).join(' ') || 'Unnamed'
}

function UserRow({ user }: { user: AdminUser }) {
  return (
    <div className="row row--between" style={{ borderTop: '1px solid var(--color-border)', padding: '8px 0' }}>
      <div>
        <div>
          {userDisplayName(user)}
          {user.username ? ` · @${user.username}` : ''}
        </div>
        <div className="listing-card__meta">
          ID {user.telegram_user_id} · {user.language_code ?? '—'} ·{' '}
          {user.has_search ? 'has search' : 'no search'}
        </div>
      </div>
    </div>
  )
}

function matchesUserQuery(user: AdminUser, query: string): boolean {
  const q = query.trim().toLowerCase()
  if (!q) return false
  return (
    String(user.telegram_user_id).includes(q) ||
    user.username.toLowerCase().includes(q) ||
    userDisplayName(user).toLowerCase().includes(q)
  )
}

export default function Admin() {
  const stats = useQuery({ queryKey: ['admin', 'stats'], queryFn: api.adminStats })
  const users = useQuery({ queryKey: ['admin', 'users'], queryFn: api.adminUsers })

  const [scope, setScope] = useState<'all' | 'user'>('all')
  const [userId, setUserId] = useState('')
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [text, setText] = useState('')
  const [result, setResult] = useState<AdminNotifyResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  const notify = useMutation({
    mutationFn: () =>
      api.adminNotify({
        scope,
        user_id: scope === 'user' ? Number(userId.trim()) : undefined,
        text: text.trim(),
      }),
    onSuccess: (sendResult) => {
      setError(null)
      setResult(sendResult)
      setText('')
      hapticNotification('success')
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : 'Could not send the notification.')
      hapticNotification('error')
    },
  })

  const suggestions = showSuggestions
    ? (users.data ?? []).filter((user) => matchesUserQuery(user, userId)).slice(0, 6)
    : []
  const isValidUserId = /^\d+$/.test(userId.trim())
  const canSend = Boolean(text.trim()) && (scope === 'all' || isValidUserId)

  function pickSuggestion(user: AdminUser) {
    setUserId(String(user.telegram_user_id))
    setShowSuggestions(false)
  }

  async function onSend() {
    if (!canSend) return
    const confirmMessage =
      scope === 'all'
        ? `Send this message to all ${stats.data?.registered_users ?? 'registered'} users?`
        : `Send this message to user ${userId}?`
    if (await confirmAction(confirmMessage)) {
      notify.mutate()
    }
  }

  return (
    <div className="stack">
      <h1 className="screen-title">Admin</h1>

      {stats.data && (
        <div className="field-grid">
          <StatTile label="Tracked users" value={stats.data.tracked_users} />
          <StatTile label="Onboarded" value={stats.data.onboarded_users} />
          <StatTile label="With saved search" value={stats.data.registered_users} />
          <StatTile label="Listings cached" value={stats.data.total_listings} />
        </div>
      )}

      <div className="card stack">
        <p className="listing-card__meta">Send a notification</p>
        <div className="row">
          <label className="row" style={{ gap: 4 }}>
            <input type="radio" checked={scope === 'all'} onChange={() => setScope('all')} />
            All registered users
          </label>
          <label className="row" style={{ gap: 4 }}>
            <input type="radio" checked={scope === 'user'} onChange={() => setScope('user')} />
            Specific user
          </label>
        </div>
        {scope === 'user' && (
          <div className="field" style={{ position: 'relative' }}>
            <label htmlFor="admin-user-id">Telegram user ID or name</label>
            <input
              id="admin-user-id"
              autoComplete="off"
              value={userId}
              onChange={(event) => {
                setUserId(event.target.value)
                setShowSuggestions(true)
              }}
              onFocus={() => setShowSuggestions(true)}
              onBlur={() => setShowSuggestions(false)}
              placeholder="536212014 or a name"
            />
            {suggestions.length > 0 && (
              <div className="admin-suggestions">
                {suggestions.map((user) => (
                  <button
                    key={user.telegram_user_id}
                    type="button"
                    className="admin-suggestions__item"
                    onMouseDown={(event) => event.preventDefault()}
                    onClick={() => pickSuggestion(user)}
                  >
                    <span>
                      {userDisplayName(user)}
                      {user.username ? ` · @${user.username}` : ''}
                    </span>
                    <span className="listing-card__meta">ID {user.telegram_user_id}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
        <div className="field">
          <label htmlFor="admin-text">Message</label>
          <textarea
            id="admin-text"
            rows={4}
            value={text}
            onChange={(event) => setText(event.target.value)}
            placeholder="Message to send…"
          />
        </div>
        {error && <p className="listing-card__meta">{error}</p>}
        {result && (
          <p className="listing-card__meta">
            Sent to {result.sent} user(s){result.failed ? `, ${result.failed} failed` : ''}.
          </p>
        )}
        <button
          type="button"
          className="btn btn--primary btn--block"
          disabled={notify.isPending || !canSend}
          onClick={onSend}
        >
          {notify.isPending ? 'Sending…' : 'Send'}
        </button>
      </div>

      <div className="card stack">
        <p className="listing-card__meta">Users ({users.data?.length ?? 0})</p>
        {users.isLoading && <p>Loading…</p>}
        {users.data?.map((user) => (
          <UserRow key={user.telegram_user_id} user={user} />
        ))}
      </div>
    </div>
  )
}
