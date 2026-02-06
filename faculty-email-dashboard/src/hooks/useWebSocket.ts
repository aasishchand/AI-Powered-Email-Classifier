import { useEffect, useState, useRef } from 'react'

/** Build WebSocket URL from env (http(s) -> ws(s)). */
function getWsUrl(path: string): string {
  const base = import.meta.env.VITE_WS_URL || window.location.origin
  const wsBase = base.replace(/^http/, 'ws')
  const token = typeof localStorage !== 'undefined' ? localStorage.getItem('access_token') : null
  const query = token ? `?token=${encodeURIComponent(token)}` : ''
  return `${wsBase.replace(/\/$/, '')}${path.startsWith('/') ? path : `/${path}`}${query}`
}

/**
 * Native WebSocket hook for FastAPI /api/v1/ws/dashboard (not Socket.IO).
 * Stops console spam from Socket.IO failing to handshake with plain WebSocket.
 */
export function useWebSocket(endpoint: string) {
  const [data, setData] = useState<unknown>(null)
  const [isConnected, setIsConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    const url = getWsUrl(endpoint)
    let closed = false

    const connect = () => {
      if (closed) return
      try {
        const ws = new WebSocket(url)
        wsRef.current = ws
        ws.onopen = () => setIsConnected(true)
        ws.onclose = () => {
          setIsConnected(false)
          wsRef.current = null
          if (!closed) {
            reconnectTimeoutRef.current = setTimeout(connect, 5000)
          }
        }
        ws.onerror = () => {}
        ws.onmessage = (event) => {
          try {
            const parsed = JSON.parse(event.data)
            setData(parsed)
            if (parsed?.type === 'connection') {
              ws.send(JSON.stringify({ type: 'ping' }))
            }
          } catch {
            setData(event.data)
          }
        }
      } catch {
        if (!closed) reconnectTimeoutRef.current = setTimeout(connect, 5000)
      }
    }

    connect()
    return () => {
      closed = true
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
        reconnectTimeoutRef.current = null
      }
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
      setIsConnected(false)
    }
  }, [endpoint])

  const sendMessage = (message: unknown) => {
    const ws = wsRef.current
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(typeof message === 'string' ? message : JSON.stringify(message))
    }
  }

  return { data, isConnected, sendMessage }
}
