import { useCallback, useEffect, useRef, useState } from 'react'

export interface ApiState<T> {
  data: T | undefined
  error: unknown
  loading: boolean
  reload: () => void
}

interface Settled<T> {
  requestKey: string | null
  data?: T
  error?: unknown
}

/**
 * Load data whenever `key` changes. Pass `null` as the key to skip loading.
 * The previous data stays available while a new request is in flight, and responses
 * from superseded requests are ignored.
 */
export function useApi<T>(key: string | null, loader: () => Promise<T>): ApiState<T> {
  const [nonce, setNonce] = useState(0)
  const [settled, setSettled] = useState<Settled<T>>({ requestKey: null })
  const loaderRef = useRef(loader)
  const requestKey = key === null ? null : `${key}#${nonce}`

  useEffect(() => {
    loaderRef.current = loader
  })

  useEffect(() => {
    if (requestKey === null) return
    let active = true
    loaderRef.current().then(
      (data) => {
        if (active) setSettled({ requestKey, data })
      },
      (error: unknown) => {
        if (active) setSettled({ requestKey, error: error ?? new Error('Request failed') })
      },
    )
    return () => {
      active = false
    }
  }, [requestKey])

  const reload = useCallback(() => setNonce((value) => value + 1), [])
  const current = settled.requestKey === requestKey
  return {
    data: requestKey === null ? undefined : settled.data,
    error: current ? settled.error : undefined,
    loading: requestKey !== null && !current,
    reload,
  }
}
