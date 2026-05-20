# Frontend Web — SaaSFlow Assistant

React 19 + Vite 8 application. Three-column dark-theme UI with real-time agent observability.

## Stack

| Package | Version | Purpose |
|---------|---------|---------| 
| React | 19 | UI framework |
| Vite | 8 | Build tool and dev server |
| lucide-react | ^1.16.0 | Icon library |
| CSS Modules | native | Scoped component styles |

No state management library. All state lives in the `useAgentStream` hook and is passed down as props.

## Running

```bash
npm install
npm run dev      # development server at http://localhost:5173
npm run build    # production build to dist/
npm run preview  # preview production build locally
npm run lint     # ESLint check
```

---

## Component Tree

```
App
├── Sidebar
├── ChatPanel
└── AgentTrace
```

All components receive their data and callbacks from `App`, which sources everything from the `useAgentStream` hook.

---

## `useAgentStream` — `src/hooks/useAgentStream.js`

The single source of truth for the entire application. Manages:

| State | Type | Description |
|-------|------|-------------|
| `messages` | `Array` | Full conversation history `[{role, content}]` |
| `events` | `Array` | Agent trace events for the current turn (cleared on each new message) |
| `isStreaming` | `boolean` | True while an SSE stream is open |
| `sessionId` | `string\|null` | Current session UUID (set by backend on first message) |
| `provider` | `string` | `"openai"` or `"groq"` |

### `sendMessage(text)`

1. Appends user message to `messages`
2. Clears `events` (fresh trace per turn)
3. Opens `fetch` to `POST /chat/stream` with `AbortController`
4. Reads `res.body` as a `ReadableStream` with `TextDecoder`
5. Splits chunks on `\n`, parses `data: {...}` lines
6. Routes events:
   - `session` → sets `sessionId`
   - `final_response` → appends assistant message to `messages`
   - `done` → sets `isStreaming = false`
   - `error` → adds to `events`, sets `isStreaming = false`
   - everything else → adds to `events` (displayed in AgentTrace)

### `stop()`

Calls `AbortController.abort()` to cancel the in-flight fetch. Sets `isStreaming = false`.

### `newSession()`

Resets `sessionId`, `messages`, and `events` to their initial state.

### `indexDocs()`

Calls `POST /index` with the current provider. Returns the response JSON (used by Sidebar to show success/error state).

---

## `Sidebar` — `src/components/Sidebar.jsx`

**Props:** `provider`, `setProvider`, `sessionId`, `onIndex`

On mount, fires two requests:
- `GET /` → sets API status indicator (Online / Offline)
- `GET /products` → populates the product catalog list

**Index Documents button** has four visual states: `idle`, `loading` (spinner), `done` (green check), `error` (red message).

---

## `ChatPanel` — `src/components/ChatPanel.jsx`

**Props:** `messages`, `isStreaming`, `onSend`, `onNew`, `stop`

- Empty state shows quick suggestion buttons that call `onSend` directly
- Typing indicator (3-dot bounce animation) shown when `isStreaming` is true
- Send button disabled when input is empty or `isStreaming` is true
- Stop button (red square) replaces Send button during streaming
- Auto-scrolls to bottom on new messages via `useRef` + `scrollIntoView`
- `Enter` to send, `Shift+Enter` for newline

---

## `AgentTrace` — `src/components/AgentTrace.jsx`

**Props:** `events`, `isStreaming`

Renders each event as a color-coded card with icon, label, and content. The `EVENT_CONFIG` map defines the visual treatment for each event type:

```js
const EVENT_CONFIG = {
  thinking:     { icon: Brain,        color: '#6366f1', label: 'Analyzing' },
  llm_start:    { icon: Zap,          color: '#8b5cf6', label: 'LLM Started' },
  llm_end:      { icon: Zap,          color: '#10b981', label: 'LLM Done' },
  agent_action: { icon: ChevronRight, color: '#f59e0b', label: 'Agent Action' },
  tool_start:   { icon: Wrench,       color: '#3b82f6', label: 'Tool' },
  tool_end:     { icon: CheckCircle,  color: '#10b981', label: 'Result' },
  tool_error:   { icon: AlertCircle,  color: '#ef4444', label: 'Error' },
  rag_doc:      { icon: FileText,     color: '#06b6d4', label: 'RAG Doc' },
  agent_finish: { icon: CheckCircle,  color: '#10b981', label: 'Done' },
  error:        { icon: AlertCircle,  color: '#ef4444', label: 'Error' },
}
```

Live counters derived from `events` array:
- LLM Calls = `events.filter(e => e.type === 'llm_start').length`
- Tool Calls = `events.filter(e => e.type === 'tool_start').length`
- RAG Docs = `events.filter(e => e.type === 'rag_doc').length`
- Total Events = `events.length`

The `● LIVE` badge pulses in red while `isStreaming` is true.

---

## Styling

All styles use **CSS Modules** (`.module.css` files per component). Global design tokens are defined as CSS custom properties in `src/index.css`:

```css
:root {
  --bg: #0f1117;        /* page background */
  --bg2: #161b27;       /* panel background */
  --bg3: #1e2535;       /* header/input background */
  --border: #2a3347;    /* borders */
  --accent: #6366f1;    /* primary (indigo) */
  --accent2: #8b5cf6;   /* secondary (violet) */
  --green: #10b981;
  --yellow: #f59e0b;
  --red: #ef4444;
  --blue: #3b82f6;
  --cyan: #06b6d4;
  --text: #e2e8f0;
  --text2: #94a3b8;
  --text3: #64748b;
}
```

The AgentTrace panel is hidden on viewports narrower than 900px (responsive breakpoint in `App.module.css`).
