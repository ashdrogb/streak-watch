// In production set VITE_API_URL to the deployed backend's URL, e.g.
// https://football-streaks-api.vercel.app/api -- locally it falls back to
// the relative "/api" path, which vite.config.js proxies to Flask on :5000.
const API_BASE = import.meta.env.VITE_API_URL || '/api'

async function getJSON(path) {
  const res = await fetch(`${API_BASE}${path}`)
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.error || `Request failed (${res.status})`)
  }
  return res.json()
}

export function fetchLeagues() {
  return getJSON('/leagues')
}

export function fetchStreaks({ leagues = [], type = null, minLength = 1 } = {}) {
  const params = new URLSearchParams()
  if (leagues.length) params.set('league', leagues.join(','))
  if (type && type !== 'all') params.set('type', type)
  if (minLength && minLength > 1) params.set('min_length', String(minLength))

  const query = params.toString()
  return getJSON(`/streaks${query ? `?${query}` : ''}`)
}
