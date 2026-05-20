import { useEffect, useRef, useState } from 'react'
import { Send, Square, RotateCcw, Bot, User } from 'lucide-react'
import styles from './ChatPanel.module.css'

const SUGGESTIONS = [
  'Which plan is ideal for a team of 10 people?',
  'Compare the Starter with the Growth Plan',
  'I need GDPR compliance, what do you recommend?',
  'What add-ons do you offer?',
  'How does cancellation work?',
]

export default function ChatPanel({ messages, isStreaming, onSend, onNew, stop }) {
  const [input, setInput] = useState('')
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isStreaming])

  const submit = () => {
    const text = input.trim()
    if (!text || isStreaming) return
    setInput('')
    onSend(text)
  }

  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <div className={styles.avatar}><Bot size={18} /></div>
        <div>
          <div className={styles.name}>Sofia</div>
          <div className={styles.status}>
            <span className={isStreaming ? styles.dotActive : styles.dot} />
            {isStreaming ? 'Thinking...' : 'Online'}
          </div>
        </div>
        <button className={styles.newBtn} onClick={onNew} title="New conversation">
          <RotateCcw size={15} />
        </button>
      </div>

      <div className={styles.messages}>
        {messages.length === 0 && (
          <div className={styles.welcome}>
            <div className={styles.welcomeIcon}><Bot size={32} /></div>
            <p>Hi! I'm <strong>Sofia</strong>, SaaSFlow's assistant.</p>
            <p className={styles.sub}>Choose a suggestion or type your question:</p>
            <div className={styles.suggestions}>
              {SUGGESTIONS.map(s => (
                <button key={s} className={styles.suggestion} onClick={() => onSend(s)}>{s}</button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={msg.role === 'user' ? styles.userMsg : styles.assistantMsg}>
            <div className={styles.msgIcon}>
              {msg.role === 'user' ? <User size={14} /> : <Bot size={14} />}
            </div>
            <div className={styles.bubble}>{msg.content}</div>
          </div>
        ))}

        {isStreaming && (
          <div className={styles.assistantMsg}>
            <div className={styles.msgIcon}><Bot size={14} /></div>
            <div className={styles.typing}>
              <span /><span /><span />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className={styles.inputArea}>
        <input
          className={styles.input}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !e.shiftKey && submit()}
          placeholder="Type your message..."
          disabled={isStreaming}
        />
        {isStreaming
          ? <button className={styles.stopBtn} onClick={stop}><Square size={16} /></button>
          : <button className={styles.sendBtn} onClick={submit} disabled={!input.trim()}><Send size={16} /></button>
        }
      </div>
    </div>
  )
}
