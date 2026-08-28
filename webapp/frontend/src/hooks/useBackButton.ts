import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

import { showBackButton } from '../telegram'

/** Shows Telegram's native Back button for as long as the calling screen is
 * mounted; defaults to browser-history back when no handler is given.
 */
export function useBackButton(onBack?: () => void): void {
  const navigate = useNavigate()
  useEffect(() => {
    const handleClick = onBack ?? (() => navigate(-1))
    return showBackButton(handleClick)
  }, [navigate, onBack])
}
