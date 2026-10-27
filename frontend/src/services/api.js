// Service layer: every call to the backend goes through this file,
// so components never build URLs or parse responses themselves.

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '/api'

async function request(path, options = {}) {
  let response
  try {
    response = await fetch(`${API_BASE}${path}`, options)
  } catch {
    throw new Error('Cannot reach the FlowForge backend. Is it running?')
  }
  const body = await response.json().catch(() => null)
  if (!response.ok) {
    throw new Error(body?.detail ?? `Request failed with status ${response.status}`)
  }
  return body
}

export function getHealth() {
  return request('/health')
}
