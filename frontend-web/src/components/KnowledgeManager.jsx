import { useState, useRef, useCallback } from 'react'
import { Upload, Link, FileText, X, CheckCircle, Loader, AlertCircle, ChevronDown, ChevronUp, Plus } from 'lucide-react'
import styles from './KnowledgeManager.module.css'

const API = 'http://localhost:8000'

const FILE_ICONS = { pdf: '📄', txt: '📝', md: '📋', csv: '📊', json: '🗂️' }
const getExt = (name) => name.split('.').pop().toLowerCase()

export default function KnowledgeManager({ provider, apiKey }) {
  const [sources, setSources] = useState([])
  const [dragging, setDragging] = useState(false)
  const [url, setUrl] = useState('')
  const [text, setText] = useState('')
  const [tab, setTab] = useState('file') // file | url | text
  const [open, setOpen] = useState(true)
  const fileRef = useRef()

  const addSource = (name, type) => {
    const id = Date.now() + Math.random()
    setSources(prev => [...prev, { id, name, type, status: 'loading' }])
    return id
  }

  const updateSource = (id, patch) =>
    setSources(prev => prev.map(s => s.id === id ? { ...s, ...patch } : s))

  const removeSource = (id) =>
    setSources(prev => prev.filter(s => s.id !== id))

  const upload = useCallback(async ({ files = [], urlVal = '', textVal = '' }) => {
    const fd = new FormData()
    fd.append('provider', provider)
    if (apiKey) fd.append('api_key', apiKey)
    files.forEach(f => fd.append('files', f))
    if (urlVal) fd.append('url', urlVal)
    if (textVal) fd.append('text', textVal)

    const ids = [
      ...files.map(f => addSource(f.name, 'file')),
      ...(urlVal ? [addSource(urlVal, 'url')] : []),
      ...(textVal ? [addSource('Text snippet', 'text')] : []),
    ]

    try {
      const res = await fetch(`${API}/upload`, { method: 'POST', body: fd })
      const data = await res.json()
      if (res.ok) {
        ids.forEach((id, i) => updateSource(id, {
          status: 'done',
          chunks: data.added[i]?.chunks ?? '?',
        }))
      } else {
        ids.forEach(id => updateSource(id, { status: 'error', error: data.detail }))
      }
    } catch (e) {
      ids.forEach(id => updateSource(id, { status: 'error', error: e.message }))
    }
  }, [provider, apiKey])

  const onFiles = (fileList) => {
    const files = Array.from(fileList).filter(f =>
      ['txt', 'pdf', 'md', 'csv', 'json'].includes(getExt(f.name))
    )
    if (files.length) upload({ files })
  }

  const onDrop = (e) => {
    e.preventDefault()
    setDragging(false)
    onFiles(e.dataTransfer.files)
  }

  const onUrlSubmit = (e) => {
    e.preventDefault()
    if (!url.trim()) return
    upload({ urlVal: url.trim() })
    setUrl('')
  }

  const onTextSubmit = (e) => {
    e.preventDefault()
    if (!text.trim()) return
    upload({ textVal: text.trim() })
    setText('')
  }

  return (
    <div className={styles.wrapper}>
      <button className={styles.header} onClick={() => setOpen(v => !v)}>
        <span className={styles.headerTitle}>
          <FileText size={13} /> Knowledge Sources
          {sources.length > 0 && <span className={styles.badge}>{sources.length}</span>}
        </span>
        {open ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
      </button>

      {open && (
        <div className={styles.body}>
          {/* Tabs */}
          <div className={styles.tabs}>
            {['file', 'url', 'text'].map(t => (
              <button key={t} className={tab === t ? styles.tabActive : styles.tab}
                onClick={() => setTab(t)}>
                {t === 'file' ? <Upload size={11} /> : t === 'url' ? <Link size={11} /> : <FileText size={11} />}
                {t.charAt(0).toUpperCase() + t.slice(1)}
              </button>
            ))}
          </div>

          {/* File tab */}
          {tab === 'file' && (
            <div
              className={`${styles.dropzone} ${dragging ? styles.dropzoneDrag : ''}`}
              onDragOver={e => { e.preventDefault(); setDragging(true) }}
              onDragLeave={() => setDragging(false)}
              onDrop={onDrop}
              onClick={() => fileRef.current.click()}
            >
              <Upload size={20} className={styles.dropIcon} />
              <p className={styles.dropText}>Drop files or click to browse</p>
              <p className={styles.dropHint}>TXT · PDF · MD · CSV · JSON</p>
              <input ref={fileRef} type="file" multiple hidden
                accept=".txt,.pdf,.md,.csv,.json"
                onChange={e => onFiles(e.target.files)} />
            </div>
          )}

          {/* URL tab */}
          {tab === 'url' && (
            <form className={styles.inputRow} onSubmit={onUrlSubmit}>
              <input
                className={styles.input}
                value={url}
                onChange={e => setUrl(e.target.value)}
                placeholder="https://docs.example.com/page"
                type="url"
              />
              <button className={styles.addBtn} type="submit" disabled={!url.trim()}>
                <Plus size={13} />
              </button>
            </form>
          )}

          {/* Text tab */}
          {tab === 'text' && (
            <form onSubmit={onTextSubmit}>
              <textarea
                className={styles.textarea}
                value={text}
                onChange={e => setText(e.target.value)}
                placeholder="Paste any text content to add to the knowledge base..."
                rows={4}
              />
              <button className={styles.submitBtn} type="submit" disabled={!text.trim()}>
                <Plus size={12} /> Add Text
              </button>
            </form>
          )}

          {/* Source list */}
          {sources.length > 0 && (
            <div className={styles.sourceList}>
              {sources.map(s => (
                <div key={s.id} className={styles.sourceItem}>
                  <span className={styles.sourceIcon}>
                    {s.type === 'url' ? '🔗' : s.type === 'text' ? '📝' : (FILE_ICONS[getExt(s.name)] || '📄')}
                  </span>
                  <div className={styles.sourceInfo}>
                    <span className={styles.sourceName}>{s.name}</span>
                    {s.status === 'done' && <span className={styles.sourceChunks}>{s.chunks} chunks</span>}
                    {s.status === 'error' && <span className={styles.sourceError}>{s.error}</span>}
                  </div>
                  <span className={styles.sourceStatus}>
                    {s.status === 'loading' && <Loader size={12} className={styles.spin} />}
                    {s.status === 'done' && <CheckCircle size={12} color="var(--green)" />}
                    {s.status === 'error' && <AlertCircle size={12} color="var(--red)" />}
                  </span>
                  <button className={styles.removeBtn} onClick={() => removeSource(s.id)}>
                    <X size={11} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
