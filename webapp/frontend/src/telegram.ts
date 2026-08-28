// Thin, defensive wrapper over `window.Telegram.WebApp`. Telegram's own
// `telegram-web-app.js` (loaded in index.html) always defines this object,
// even outside the Telegram client — with safe no-op methods and empty
// `initData` — but we still guard every access so the app degrades to a
// plain, unauthenticated web page rather than crashing when that script
// fails to load at all (offline, blocked, etc.).

import type { Telegram, WebApp as TelegramWebApp } from '@twa-dev/types'

declare global {
  interface Window {
    Telegram?: Telegram
  }
}

export function webApp(): TelegramWebApp | undefined {
  return window.Telegram?.WebApp
}

export function isInsideTelegram(): boolean {
  return Boolean(webApp()?.initData)
}

export function getInitData(): string {
  return webApp()?.initData ?? ''
}

const THEME_KEYS = [
  'bg_color',
  'secondary_bg_color',
  'text_color',
  'hint_color',
  'link_color',
  'button_color',
  'button_text_color',
  'header_bg_color',
  'accent_text_color',
  'section_bg_color',
  'section_header_text_color',
  'subtitle_text_color',
  'destructive_text_color',
  'section_separator_color',
  'bottom_bar_bg_color',
] as const

function applyTheme(): void {
  const app = webApp()
  if (!app) return
  const root = document.documentElement
  for (const key of THEME_KEYS) {
    const value = app.themeParams[key]
    if (value) root.style.setProperty(`--tg-${key.replace(/_/g, '-')}`, value)
  }
  root.style.setProperty('--tg-color-scheme', app.colorScheme)
}

function applySafeArea(): void {
  const app = webApp()
  if (!app) return
  const root = document.documentElement
  const inset = app.contentSafeAreaInset
  root.style.setProperty('--tg-safe-top', `${inset.top}px`)
  root.style.setProperty('--tg-safe-bottom', `${inset.bottom}px`)
  root.style.setProperty('--tg-safe-left', `${inset.left}px`)
  root.style.setProperty('--tg-safe-right', `${inset.right}px`)
}

export function initTelegram(): void {
  const app = webApp()
  if (!app) return
  app.ready()
  app.expand()
  applyTheme()
  applySafeArea()
  app.onEvent('themeChanged', applyTheme)
  app.onEvent('viewportChanged', applySafeArea)
}

/** Shows the native Back button while mounted; returns a cleanup function. */
export function showBackButton(onClick: () => void): () => void {
  const app = webApp()
  if (!app) return () => {}
  app.BackButton.show()
  app.BackButton.onClick(onClick)
  return () => {
    app.BackButton.offClick(onClick)
    app.BackButton.hide()
  }
}

export function hapticImpact(style: 'light' | 'medium' | 'heavy' = 'light'): void {
  webApp()?.HapticFeedback.impactOccurred(style)
}

/** Opens an external (non-Telegram) URL — via the WebApp bridge so it lands in
 * the system browser instead of being trapped in the Mini App's webview, or a
 * plain new tab when running outside Telegram.
 */
/** Native confirm dialog when inside Telegram, `window.confirm` otherwise. */
export function confirmAction(message: string): Promise<boolean> {
  const app = webApp()
  if (app && isInsideTelegram()) {
    return new Promise((resolve) => app.showConfirm(message, resolve))
  }
  return Promise.resolve(window.confirm(message))
}

export function openExternalLink(url: string): void {
  const app = webApp()
  if (app && isInsideTelegram()) {
    app.openLink(url)
    return
  }
  window.open(url, '_blank', 'noopener,noreferrer')
}

export function hapticNotification(type: 'error' | 'success' | 'warning'): void {
  webApp()?.HapticFeedback.notificationOccurred(type)
}
