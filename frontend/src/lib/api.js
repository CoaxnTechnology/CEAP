const API_BASE = import.meta.env.VITE_API_URL || ''

export async function api(path, options = {}) {
  const url = `${API_BASE}${path}`
  const headers = options.body instanceof FormData
    ? options.headers
    : { 'Content-Type': 'application/json', ...options.headers }
  const res = await fetch(url, {
    headers,
    credentials: 'include',
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.error || `HTTP ${res.status}`)
  }
  return res.json()
}
