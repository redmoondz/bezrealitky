import { useEffect } from 'react'

import { webApp } from '../telegram'

interface MainButtonOptions {
  text: string
  onClick: () => void
  visible?: boolean
  loading?: boolean
}

/** Shows Telegram's native bottom MainButton for as long as the calling
 * screen is mounted — used for a screen's one primary action (e.g.
 * SearchSettings' "Save & run").
 */
export function useMainButton({ text, onClick, visible = true, loading = false }: MainButtonOptions): void {
  useEffect(() => {
    const app = webApp()
    if (!app) return
    const button = app.MainButton
    button.setText(text)
    if (visible) button.show()
    else button.hide()
    if (loading) button.showProgress(false)
    else button.hideProgress()
    button.onClick(onClick)
    return () => {
      button.offClick(onClick)
      button.hide()
    }
  }, [text, onClick, visible, loading])
}
