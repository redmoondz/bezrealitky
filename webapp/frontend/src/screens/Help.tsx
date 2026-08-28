import { useQuery } from '@tanstack/react-query'

import { api } from '../api'

export default function Help() {
  const help = useQuery({ queryKey: ['help'], queryFn: api.help })

  return (
    <div className="stack">
      <h1 className="screen-title">Help</h1>
      <div className="card">
        {help.isLoading ? <p>Loading…</p> : <p className="help-text">{help.data?.text}</p>}
      </div>
    </div>
  )
}
