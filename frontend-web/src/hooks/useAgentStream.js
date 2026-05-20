import { useState, useCallback, useRef } from 'react'

const API = 'http://localhost:8000'

export function useAgentStream() {
  const [events, setEvents] = useState([])
  const [messages, setMessages] = useState([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [sessionId, setSessionId] = useState(null)
  const [provider, setProviderState] = useState(() => localStorage.getItem('sf_provider') || 'groq')
  const [apiKey, setApiKeyState] = useState(() => localStorage.getItem('sf_api_key') || '')
  const [providerChanged, setProviderChanged] = useState(false)
  const abortRef = useRef(null)

  const addEvent = useCallback((ev) => {
    setEvents(prev => [...prev, { ...ev, id: Date.now() + Math.random() }])
  }, [])

  const setProvider = useCallback((p) => {
    setProviderState(prev => {
      if (prev !== p) setProviderChanged(true)
      return p
    })
    localStorage.setItem('sf_provider', p)
  }, [])

  const setApiKey = useCallback((k) => {
    setApiKeyState(k)
    localStorage.setItem('sf_api_key', k)
  }, [])

  const sendMessage = useCallback(async (text) => {
    if (isStreaming) return
    setMessages(prev => [...prev, { role: 'user', content: text }])
    setEvents([])
    setIsStreaming(true)
    setProviderChanged(false)

    const controller = new AbortController()
    abortRef.current = controller

    try {
      const res = await fetch(`${API}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          session_id: sessionId,
          provider,
          api_key: apiKey || undefined,
        }),
        signal: controller.signal,
      })

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Erro desconhecido' }))
        addEvent({ type: 'error', message: err.detail || 'Erro na API' })
        setIsStreaming(false)
        setMessages(prev => [...prev, { role: 'assistant', content: `❌ ${err.detail || 'Erro na API'}` }])
        return
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop()

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const ev = JSON.parse(line.slice(6))
            if (ev.type === 'session') setSessionId(ev.session_id)
            else if (ev.type === 'final_response') {
              setMessages(prev => [...prev, { role: 'assistant', content: ev.content }])
            } else if (ev.type === 'done') {
              setIsStreaming(false)
            } else if (ev.type === 'error') {
              addEvent(ev)
              setMessages(prev => [...prev, { role: 'assistant', content: `❌ ${ev.message}` }])
              setIsStreaming(false)
            } else {
              addEvent(ev)
            }
          } catch {}
        }
      }
    } catch (err) {
      if (err.name !== 'AbortError') addEvent({ type: 'error', message: err.message })
    } finally {
      setIsStreaming(false)
    }
  }, [isStreaming, sessionId, provider, apiKey, addEvent])

  const indexDocs = useCallback(async () => {
    const res = await fetch(`${API}/index`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider, api_key: apiKey || undefined }),
    })
    const data = await res.json()
    if (res.ok) setProviderChanged(false)
    return data
  }, [provider, apiKey])

  const newSession = useCallback(() => {
    setSessionId(null)
    setMessages([])
    setEvents([])
    setProviderChanged(false)
  }, [])

  const stop = useCallback(() => {
    abortRef.current?.abort()
    setIsStreaming(false)
  }, [])

  return {
    events, messages, isStreaming, sessionId,
    provider, setProvider,
    apiKey, setApiKey,
    providerChanged,
    sendMessage, indexDocs, newSession, stop,
  }
}
