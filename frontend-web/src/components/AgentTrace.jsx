import { useEffect, useRef } from 'react'
import { Brain, Search, Wrench, CheckCircle, AlertCircle, FileText, Zap, ChevronRight } from 'lucide-react'
import styles from './AgentTrace.module.css'

const EVENT_CONFIG = {
  thinking:      { icon: Brain,        color: '#6366f1', label: 'Analyzing' },
  llm_start:     { icon: Zap,          color: '#8b5cf6', label: 'LLM Started' },
  llm_end:       { icon: Zap,          color: '#10b981', label: 'LLM Done' },
  agent_action:  { icon: ChevronRight, color: '#f59e0b', label: 'Agent Action' },
  tool_start:    { icon: Wrench,       color: '#3b82f6', label: 'Tool' },
  tool_end:      { icon: CheckCircle,  color: '#10b981', label: 'Result' },
  tool_error:    { icon: AlertCircle,  color: '#ef4444', label: 'Error' },
  rag_doc:       { icon: FileText,     color: '#06b6d4', label: 'RAG Doc' },
  agent_finish:  { icon: CheckCircle,  color: '#10b981', label: 'Done' },
  error:         { icon: AlertCircle,  color: '#ef4444', label: 'Error' },
}

function EventCard({ ev }) {
  const cfg = EVENT_CONFIG[ev.type] || { icon: Brain, color: '#64748b', label: ev.type }
  const Icon = cfg.icon

  const getContent = () => {
    if (ev.type === 'tool_start' || ev.type === 'agent_action')
      return <><span className={styles.tag} style={{ background: cfg.color + '22', color: cfg.color }}>{ev.tool}</span><span className={styles.detail}>{String(ev.input || '').slice(0, 120)}</span></>
    if (ev.type === 'tool_end')
      return <span className={styles.detail}>{String(ev.output || '').slice(0, 200)}</span>
    if (ev.type === 'rag_doc')
      return <><span className={styles.tag} style={{ background: '#06b6d422', color: '#06b6d4' }}>{ev.source}</span><span className={styles.detail}>{String(ev.preview || '').slice(0, 150)}</span></>
    if (ev.type === 'llm_start')
      return <span className={styles.tag} style={{ background: '#8b5cf622', color: '#8b5cf6' }}>{ev.model}</span>
    if (ev.type === 'error')
      return <span className={styles.error}>{ev.message}</span>
    return <span className={styles.detail}>{ev.message || ''}</span>
  }

  return (
    <div className={styles.card}>
      <div className={styles.iconWrap} style={{ background: cfg.color + '22' }}>
        <Icon size={13} style={{ color: cfg.color }} />
      </div>
      <div className={styles.cardBody}>
        <div className={styles.cardLabel} style={{ color: cfg.color }}>{cfg.label}</div>
        <div className={styles.cardContent}>{getContent()}</div>
      </div>
      <div className={styles.ts}>{ev.ts ? new Date(ev.ts).toLocaleTimeString('en-US') : ''}</div>
    </div>
  )
}

export default function AgentTrace({ events, isStreaming }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [events])

  const toolCalls = events.filter(e => e.type === 'tool_start').length
  const ragDocs   = events.filter(e => e.type === 'rag_doc').length
  const llmCalls  = events.filter(e => e.type === 'llm_start').length

  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <Brain size={16} style={{ color: 'var(--accent)' }} />
        <span>Agent Observability</span>
        {isStreaming && <span className={styles.live}>● LIVE</span>}
      </div>

      <div className={styles.stats}>
        <div className={styles.stat}>
          <span className={styles.statVal} style={{ color: '#3b82f6' }}>{llmCalls}</span>
          <span className={styles.statLabel}>LLM Calls</span>
        </div>
        <div className={styles.stat}>
          <span className={styles.statVal} style={{ color: '#f59e0b' }}>{toolCalls}</span>
          <span className={styles.statLabel}>Tools</span>
        </div>
        <div className={styles.stat}>
          <span className={styles.statVal} style={{ color: '#06b6d4' }}>{ragDocs}</span>
          <span className={styles.statLabel}>RAG Docs</span>
        </div>
        <div className={styles.stat}>
          <span className={styles.statVal} style={{ color: '#10b981' }}>{events.length}</span>
          <span className={styles.statLabel}>Total Events</span>
        </div>
      </div>

      <div className={styles.timeline}>
        {events.length === 0 && !isStreaming && (
          <div className={styles.empty}>
            <Brain size={28} style={{ color: 'var(--text3)', marginBottom: 8 }} />
            <p>Send a message to see the agent in action</p>
          </div>
        )}
        {events.map(ev => <EventCard key={ev.id} ev={ev} />)}
        {isStreaming && (
          <div className={styles.streaming}>
            <span className={styles.streamDot} />
            Processing...
          </div>
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
