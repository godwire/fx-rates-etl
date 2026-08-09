const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function handleResponse(res) {
  if (res.status === 404) return null
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`Request failed (${res.status}): ${body}`)
  }
  return res.json()
}

export async function fetchMeta() {
  const res = await fetch(`${API_URL}/api/meta`)
  return handleResponse(res)
}

export async function fetchRates(base, currencies, start, end) {
  const params = new URLSearchParams({ base, currencies: currencies.join(',') })
  if (start) params.append('start', start)
  if (end) params.append('end', end)

  const res = await fetch(`${API_URL}/api/rates?${params.toString()}`)
  const data = await handleResponse(res)
  return data ?? [] // 404 (no matching rows) is a valid empty result, not an error
}

export async function refreshRates() {
  const res = await fetch(`${API_URL}/api/refresh`, { method: 'POST' })
  return handleResponse(res)
}
