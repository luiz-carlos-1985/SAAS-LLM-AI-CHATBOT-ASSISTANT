import { useState, useEffect } from 'react'
import { Settings, Database, Package, CheckCircle, Loader, Eye, EyeOff, Key } from 'lucide-react'
import styles from './Sidebar.module.css'

const API = 'http://localhost:8000'

const PROVIDER_LABELS = {
  openai: { name: 'GPT-4o-mini', placeholder: 'sk-...' },
  groq:   { name: 'Llama 3.3',   placeholder: 'gsk_...' },
}

export default function Sidebar({ provider, setProvider, apiKey, setApiKey, sessionId, onIndex, providerChanged }) {
  const [products, setProducts] = useState([])
  const [indexStatus, setIndexStatus] = useState('idle')
  const [apiStatus, setApiStatus] = useState('checking')
  const [showKey, setShowKey] = useState(false)

  useEffect(() => {
    fetch(`${API}/`)
      .then(r => r.ok ? setApiStatus('online') : setApiStatus('offline'))
      .catch(() => setApiStatus('offline'))

    fetch(`${API}/products`)
      .then(r => r.json())
      .then(setProducts)
      .catch(() => {})
  }, [])

  const handleIndex = async () => {
    setIndexStatus('loading')
    try {
      const data = await onIndex()
      setIndexStatus(data.status === 'success' ? 'done' : 'error')
    } catch {
      setIndexStatus('error')
    }
  }

  const handleSetProvider = (p) => {
    setProvider(p)
    if (indexStatus === 'done') setIndexStatus('idle')
  }

  const catEmoji = { plano: '📦', addon: '🔧', servico: '🎯' }
  const { placeholder } = PROVIDER_LABELS[provider]

  return (
    <div className={styles.sidebar}>
      <div className={styles.logo}>
        <div className={styles.logoIcon}>S</div>
        <div>
          <div className={styles.logoName}>SaaSFlow</div>
          <div className={styles.logoSub}>Assistant</div>
        </div>
        <div className={styles.apiStatus} style={{ background: apiStatus === 'online' ? '#10b98122' : '#ef444422' }}>
          <span style={{ color: apiStatus === 'online' ? '#10b981' : '#ef4444' }}>
            {apiStatus === 'online' ? '● Online' : apiStatus === 'checking' ? '○ ...' : '● Offline'}
          </span>
        </div>
      </div>

      <div className={styles.section}>
        <div className={styles.sectionTitle}><Settings size={13} /> Settings</div>

        <div className={styles.field}>
          <label className={styles.label}>AI Provider</label>
          <div className={styles.toggle}>
            <button
              className={provider === 'openai' ? styles.toggleActive : styles.toggleBtn}
              onClick={() => handleSetProvider('openai')}
            >GPT-4o-mini</button>
            <button
              className={provider === 'groq' ? styles.toggleActive : styles.toggleBtn}
              onClick={() => handleSetProvider('groq')}
            >Llama 3.3</button>
          </div>
        </div>

        <div className={styles.field}>
          <label className={styles.label}><Key size={11} style={{ display: 'inline', marginRight: 4 }} />API Key</label>
          <div className={styles.keyInputWrapper}>
            <input
              className={styles.keyInput}
              type={showKey ? 'text' : 'password'}
              value={apiKey}
              onChange={e => setApiKey(e.target.value)}
              placeholder={placeholder}
              spellCheck={false}
              autoComplete="off"
            />
            <button className={styles.eyeBtn} onClick={() => setShowKey(v => !v)} tabIndex={-1}>
              {showKey ? <EyeOff size={13} /> : <Eye size={13} />}
            </button>
          </div>
          <p className={styles.keyHint}>
            {apiKey ? '● Saved in session' : '○ Falls back to server .env'}
          </p>
        </div>

        {sessionId && (
          <div className={styles.field}>
            <label className={styles.label}>Active Session</label>
            <code className={styles.sessionId}>{sessionId.slice(0, 16)}...</code>
          </div>
        )}
      </div>

      <div className={styles.section}>
        <div className={styles.sectionTitle}><Database size={13} /> Knowledge Base</div>
        <button
          className={styles.indexBtn}
          onClick={handleIndex}
          disabled={indexStatus === 'loading'}
        >
          {indexStatus === 'loading' && <Loader size={13} className={styles.spin} />}
          {indexStatus === 'done' && !providerChanged && <CheckCircle size={13} />}
          {(indexStatus === 'idle' || providerChanged) && <Database size={13} />}
          {indexStatus === 'loading' ? 'Indexing...' : (indexStatus === 'done' && !providerChanged) ? 'Indexed!' : 'Index Documents'}
        </button>
        {indexStatus === 'done' && !providerChanged && (
          <p className={styles.hint}>✓ RAG ready to use</p>
        )}
        {providerChanged && (
          <p className={styles.hintWarn}>⚠️ Switch provider and re-index</p>
        )}
        {indexStatus === 'error' && (
          <p className={styles.hintError}>✗ Indexing failed. Check API key and connection</p>
        )}
      </div>

      <div className={styles.section} style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <div className={styles.sectionTitle}><Package size={13} /> Catalog</div>
        <div className={styles.productList}>
          {products.length === 0 && <p className={styles.hint}>Start the API to see</p>}
          {products.map(p => (
            <div key={p.id} className={styles.product}>
              <span>{catEmoji[p.category] || '📦'}</span>
              <div className={styles.productInfo}>
                <div className={styles.productName}>{p.name}</div>
                <div className={styles.productPrice}>R$ {p.price}</div>
              </div>
              <div className={styles.rating}>⭐ {p.rating}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
