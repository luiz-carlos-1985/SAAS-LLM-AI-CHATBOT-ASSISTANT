# SaaSFlow Assistant

A hybrid AI system combining **RAG-powered customer support** with **intelligent product recommendation** for a SaaS platform. Built with a real-time observability frontend that lets you watch every step the agent takes as it processes your request.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [Backend](#backend)
  - [API Endpoints](#api-endpoints)
  - [SSE Event Types](#sse-event-types)
  - [Agent Tools](#agent-tools)
  - [RAG Pipeline](#rag-pipeline)
- [Frontend](#frontend)
  - [React Web App](#react-web-app)
  - [Streamlit App](#streamlit-app)
- [Data Layer](#data-layer)
- [How It Works](#how-it-works)
- [Example Requests](#example-requests)
- [Troubleshooting](#troubleshooting)
- [Design Decisions](#design-decisions)
- [Contributing](#contributing)
- [Changelog](#changelog)
- [License](#license)

---

## Overview

SaaSFlow Assistant is a two-part system:

1. **Customer Support Agent (RAG)** — Sofia, an AI assistant that answers questions about plans, pricing, policies, and features by retrieving relevant context from a vector database before generating a response.

2. **Intelligent Recommender** — When a user describes their team size, budget, or specific needs, the agent runs a dedicated recommendation tool that performs semantic search across the product catalog and generates a personalized, explainable recommendation.

Both capabilities are exposed through a single conversational interface with **full real-time observability**: every LLM call, tool invocation, and RAG retrieval is streamed to the frontend as it happens via Server-Sent Events (SSE).

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        React Frontend                        │
│  ┌──────────┐   ┌──────────────────┐   ┌─────────────────┐  │
│  │ Sidebar  │   │   Chat Panel     │   │  Agent Trace    │  │
│  │ Settings │   │   (Sofia UI)     │   │  (Live Events)  │  │
│  │ Catalog  │   │                  │   │                 │  │
│  └──────────┘   └──────────────────┘   └─────────────────┘  │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTP + SSE (text/event-stream)
┌─────────────────────────▼───────────────────────────────────┐
│                     FastAPI Backend                          │
│                                                              │
│  POST /chat/stream ──► AgentExecutor (LangChain)            │
│                              │                               │
│         ┌────────────────────┼────────────────────┐         │
│         ▼                    ▼                    ▼         │
│  buscar_conhecimento  recomendar_produtos  comparar_planos  │
│         │                    │                              │
│         ▼                    ▼                              │
│     ChromaDB ◄── OpenAI Embeddings / HuggingFace            │
│         │                                                   │
│    knowledge_base.txt + products.json                       │
└─────────────────────────────────────────────────────────────┘
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
        OpenAI GPT-4o-mini     Groq Llama 3.3-70b
```

---

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| LLM (primary) | OpenAI GPT-4o-mini | via `openai==1.84.0` |
| LLM (free tier) | Groq Llama 3.3-70b-versatile | via `groq==0.13.0` |
| Agent framework | LangChain OpenAI Tools Agent | `langchain==0.3.25` |
| Vector store | ChromaDB | `chromadb==0.5.23` + `langchain-chroma==0.1.4` |
| Embeddings (OpenAI) | text-embedding-3-small | `langchain-openai==0.3.18` |
| Embeddings (free) | all-MiniLM-L6-v2 | `sentence-transformers==3.3.1` |
| Backend API | FastAPI + Uvicorn | `fastapi==0.115.5` + `uvicorn==0.32.1` |
| Streaming | Server-Sent Events (SSE) | native FastAPI `StreamingResponse` |
| React frontend | React 19 + Vite 8 | `lucide-react` for icons |
| Streamlit frontend | Streamlit | `streamlit==1.45.1` |

---

## Project Structure

```
saas-assistant/
│
├── backend/
│   ├── main.py                   # FastAPI app, SSE streaming endpoint
│   ├── agents/
│   │   ├── __init__.py
│   │   └── saas_agent.py         # LangChain agent, tools, SSE callback
│   ├── rag/
│   │   ├── __init__.py
│   │   └── vectorstore.py        # ChromaDB build/load, retriever factory
│   ├── data/
│   │   ├── products.json         # Fictional SaaS product catalog (8 items)
│   │   └── knowledge_base.txt    # FAQ + full platform documentation
│   ├── BACKEND.md                # Backend module reference
│   └── requirements.txt          # Python dependencies (backend-scoped copy)
│
├── frontend-web/                 # React 19 + Vite 8 (primary UI)
│   └── src/
│       ├── hooks/
│       │   └── useAgentStream.js # SSE consumer hook, all state management
│       ├── components/
│       │   ├── Sidebar.jsx       # Settings, RAG indexing, product catalog
│       │   ├── ChatPanel.jsx     # Conversation UI with Sofia
│       │   └── AgentTrace.jsx    # Real-time agent observability panel
│       ├── App.jsx               # Root layout (3-column)
│       └── index.css             # Global dark theme design system
│
├── frontend/
│   └── app.py                    # Streamlit alternative frontend
│
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment variable template
├── ARCHITECTURE.md               # Design decisions and rationale
├── CHANGELOG.md                  # Version history
└── README.md                     # This file
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- An OpenAI API key and/or a Groq API key

### 1. Clone and install Python dependencies

```bash
cd saas-assistant
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
copy .env.example .env
```

Edit `.env` and fill in your keys (see [Environment Variables](#environment-variables)).

### 3. Start the backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.  
Interactive docs: `http://localhost:8000/docs`

### 4. Start the React frontend

```bash
cd frontend-web
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

### 5. Index the knowledge base

In the sidebar of the React app, click **"Index Documents"**. This builds the ChromaDB vector store from `knowledge_base.txt` and `products.json`. You only need to do this once (or after changing the data files).

> **Alternative:** Use the Streamlit frontend instead:
> ```bash
> cd frontend
> streamlit run app.py
> ```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes (if using OpenAI) | Get at [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
| `GROQ_API_KEY` | Yes (if using Groq) | Get for free at [console.groq.com/keys](https://console.groq.com/keys) |

Both keys can coexist. The active provider is selected per-request via the `provider` field (`"openai"` or `"groq"`).

---

## Backend

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Health check |
| `POST` | `/index` | Build or rebuild the ChromaDB vector store |
| `POST` | `/upload` | Add documents from files, URLs, or raw text to the vector store |
| `POST` | `/chat/stream` | Send a message; returns an SSE stream of agent events |
| `GET` | `/session/{session_id}` | Retrieve conversation history for a session |
| `DELETE` | `/session/{session_id}` | Clear a session's conversation history |
| `GET` | `/products` | Return the full product catalog as JSON |

#### POST `/index`

```json
{ "provider": "openai", "api_key": "sk-..." }
```

Loads `knowledge_base.txt` and `products.json`, splits them into chunks, generates embeddings, and persists the vector store to `backend/chroma_db/`. If the provider has changed since the last index, the old `chroma_db/` directory is automatically deleted before rebuilding to avoid embedding dimension mismatches.

#### POST `/upload`

Accepts `multipart/form-data` with any combination of:

| Field | Type | Description |
|-------|------|-------------|
| `provider` | `string` | `"openai"` or `"groq"` (default: `"openai"`) |
| `api_key` | `string` | Optional — overrides server `.env` |
| `files` | `File[]` | One or more files: `.txt`, `.pdf`, `.md`, `.csv`, `.json` |
| `url` | `string` | A web page URL to scrape and index |
| `text` | `string` | Raw text to index directly |

Adds chunks to the **existing** vector store without rebuilding it. Returns:

```json
{
  "status": "success",
  "added": [
    { "type": "file", "name": "manual.pdf", "chunks": 12 },
    { "type": "url",  "name": "https://...", "chunks": 5 }
  ]
}
```

#### POST `/chat/stream`

```json
{
  "message": "Which plan is best for a 15-person team?",
  "session_id": "optional-uuid-to-continue-a-conversation",
  "provider": "openai"
}
```

Constraints: `message` max 2000 characters; `provider` must be `"openai"` or `"groq"`. Optional `api_key` overrides the server `.env` key for that request.

Returns `Content-Type: text/event-stream`. Each line is a JSON event (see [SSE Event Types](#sse-event-types)).  
Session history is stored in-memory and capped at the last 20 messages.

---

### SSE Event Types

Every event is a JSON object with at minimum a `type` and `ts` (UTC ISO timestamp) field.

| Event type | When it fires | Extra fields |
|-----------|--------------|-------------|
| `session` | Immediately, confirms session ID | `session_id` |
| `thinking` | Before agent starts | `message` |
| `llm_start` | LLM receives a prompt | `model` |
| `llm_end` | LLM finishes generating | `message` |
| `agent_action` | Agent decides to call a tool | `tool`, `input` |
| `tool_start` | Tool execution begins | `tool`, `input` |
| `tool_end` | Tool execution completes | `output` (truncated to 600 chars) |
| `tool_error` | Tool threw an exception | `error` |
| `rag_doc` | A document was retrieved from ChromaDB | `source`, `preview` (200 chars) |
| `agent_finish` | Agent completed its reasoning loop | `message` |
| `final_response` | The agent's final answer | `content` |
| `error` | Any unhandled exception or 60s timeout | `message` |
| `done` | Stream closed cleanly | `session_id`, `history_length` |

**Example stream output:**

```
data: {"type": "session", "ts": "2024-01-15T10:30:00", "session_id": "abc-123"}

data: {"type": "thinking", "ts": "...", "message": "Analisando sua pergunta..."}

data: {"type": "llm_start", "ts": "...", "model": "gpt-4o-mini"}

data: {"type": "agent_action", "ts": "...", "tool": "buscar_conhecimento", "input": "planos preços equipe"}

data: {"type": "tool_start", "ts": "...", "tool": "buscar_conhecimento", "input": "planos preços equipe"}

data: {"type": "rag_doc", "ts": "...", "source": "knowledge_base", "preview": "Growth Plan - R$ 149.90/mês..."}

data: {"type": "tool_end", "ts": "...", "output": "Growth Plan inclui até 25 usuários..."}

data: {"type": "final_response", "ts": "...", "content": "Para uma equipe de 15 pessoas, recomendo o Growth Plan..."}

data: {"type": "done", "ts": "...", "session_id": "abc-123", "history_length": 2}
```

---

### Agent Tools

The agent (`saas_agent.py`) is a LangChain **OpenAI Tools Agent** with four tools. All tools are defined in Portuguese and respond in Brazilian Portuguese.

#### `buscar_conhecimento(query: str)`
Performs semantic search against the ChromaDB vector store. Retrieves the top-4 most relevant chunks from `knowledge_base.txt` and `products.json`. Each retrieved document also emits a `rag_doc` SSE event so the frontend can display it in real time.

#### `recomendar_produtos(perfil: str)`
Used when the user describes their context (team size, budget, specific needs). Retrieves the top-6 relevant product chunks, then calls the LLM with a structured prompt to generate a personalized, explainable recommendation of 2–3 products with pricing and complementary add-ons.

#### `listar_produtos(categoria: str)`
Returns a formatted list of all products with name, price, description excerpt, and rating. Accepts `"plano"`, `"addon"`, `"servico"`, or `"todos"` (all).

#### `comparar_planos(planos: str)`
Accepts a comma-separated list of plan names and returns a side-by-side feature comparison. Example: `"Starter Plan, Growth Plan"`.

---

### RAG Pipeline

**File:** `backend/rag/vectorstore.py`

1. **Document loading** — `knowledge_base.txt` is loaded via `TextLoader`. Each product in `products.json` is converted to a `Document` with structured text (name, category, price, description, features, tags, rating).

2. **Chunking** — `RecursiveCharacterTextSplitter` with `chunk_size=800` and `chunk_overlap=100`.

3. **Embedding** — OpenAI `text-embedding-3-small` (when `provider="openai"`) or HuggingFace `all-MiniLM-L6-v2` (when `provider="groq"`).

4. **Storage** — ChromaDB persisted to `backend/chroma_db/`. A `.provider` file is written alongside the DB to track which embedding model was used.

5. **Provider change detection** — On `build_vectorstore`, if the stored provider differs from the requested one, `chroma_db/` is deleted automatically before rebuilding (embedding dimensions differ: OpenAI 1536 vs HuggingFace 384).

6. **Retrieval** — `similarity_search` with configurable `k` (default 4, 6 for recommendations).

---

## Frontend

### React Web App

**Location:** `frontend-web/`  
**URL:** `http://localhost:5173`

Three-column dark-theme layout built with React 19 + Vite 8:

#### Sidebar (`Sidebar.jsx`)
- API health indicator (polls `GET /` on mount)
- AI provider toggle: GPT-4o-mini ↔ Llama 3.3
- API Key input with show/hide toggle — persisted in `localStorage`, falls back to server `.env` if empty
- Active session ID display
- "Index Documents" button with four states: idle, loading (spinner), done (green check), error (red message)
- `KnowledgeManager` component embedded below the index button
- Live product catalog fetched from `GET /products`

#### Knowledge Manager (`KnowledgeManager.jsx`)
Collapsible panel for adding knowledge sources at runtime without rebuilding the full index:
- **File tab** — drag & drop or click-to-browse; accepts `.txt`, `.pdf`, `.md`, `.csv`, `.json`
- **URL tab** — paste any web page URL to scrape and index
- **Text tab** — paste raw text directly
- Source list shows each added source with type icon, name, chunk count, and status (loading / done / error)
- Each source can be removed from the visual list (does not remove from ChromaDB)

#### Chat Panel (`ChatPanel.jsx`)
- Conversation history with user/assistant bubbles
- Typing indicator (animated dots) while streaming
- Quick suggestion buttons on empty state
- Stop button to abort the SSE stream mid-response
- `Enter` to send, `Shift+Enter` for newline
- Auto-scrolls to bottom on new messages

#### Agent Trace (`AgentTrace.jsx`)
Real-time observability panel. Displays every SSE event as a color-coded card:

| Color | Event |
|-------|-------|
| 🟣 Indigo | Thinking / analyzing |
| 🟣 Purple | LLM started |
| 🟢 Green | LLM finished, tool result, agent finished |
| 🟡 Yellow | Agent action (tool decision) |
| 🔵 Blue | Tool execution started |
| 🩵 Cyan | RAG document retrieved |
| 🔴 Red | Error |

Live counters at the top: LLM Calls, Tool Calls, RAG Docs, Total Events. The `● LIVE` badge pulses while streaming.

The panel is hidden on viewports narrower than 900px.

#### `useAgentStream` hook (`hooks/useAgentStream.js`)
Manages all state and SSE communication:
- Opens a `fetch` stream to `POST /chat/stream`
- Reads the response body with `ReadableStream` + `TextDecoder`
- Routes each parsed event to the correct state update
- Exposes `sendMessage`, `stop`, `newSession`, `indexDocs`, `provider`, `setProvider`, `apiKey`, `setApiKey`
- `provider` and `apiKey` are persisted in `localStorage` (`sf_provider`, `sf_api_key`)
- Uses `AbortController` to cancel in-flight requests

---

### Streamlit App

**Location:** `frontend/app.py`  
**URL:** `http://localhost:8501`

Alternative frontend for users who prefer Streamlit. Features:
- Provider selector (OpenAI / Groq)
- Index Documents button
- Chat interface with message history
- Quick suggestion buttons in the sidebar
- Product catalog in the sidebar
- Session management (new conversation button)

> The Streamlit app calls `POST /chat/stream` but does not display the real-time agent trace. Use the React app for full observability.

---

## Data Layer

### `backend/data/products.json`

Eight fictional SaaS products across three categories:

| ID | Name | Category | Price |
|----|------|----------|-------|
| p001 | Starter Plan | plano | R$ 49.90/mês |
| p002 | Growth Plan | plano | R$ 149.90/mês |
| p003 | Enterprise Plan | plano | R$ 499.90/mês |
| p004 | Add-on: Analytics Pro | addon | R$ 29.90/mês |
| p005 | Add-on: Automações | addon | R$ 39.90/mês |
| p006 | Add-on: Suporte Premium | addon | R$ 59.90/mês |
| p007 | Add-on: Segurança Avançada | addon | R$ 49.90/mês |
| p008 | Consultoria de Implementação | servico | R$ 899.00 (único) |

Each product has: `id`, `name`, `category`, `price`, `description`, `features[]`, `tags[]`, `rating`, `reviews`.

### `backend/data/knowledge_base.txt`

Plain-text documentation covering:
- Company overview
- Detailed plan descriptions with all features
- All add-on descriptions
- Professional services
- 12 FAQ entries (trial period, plan changes, cancellation, security, integrations, API limits, data migration, discounts, SLA, multi-workspace, onboarding)

---

## How It Works

**End-to-end flow for a single message:**

```
User types message
       │
       ▼
useAgentStream.sendMessage()
  → POST /chat/stream (SSE)
       │
       ▼
FastAPI: creates asyncio.Queue, spawns thread
       │
       ▼
Thread: build_agent_streaming()
  → StreamingEventCallback attached to LLM + AgentExecutor
  → agent.invoke({ input, chat_history })
       │
       ├─ LLM decides which tool to call
       │    └─ emits: llm_start, agent_action
       │
       ├─ Tool executes (e.g. buscar_conhecimento)
       │    └─ emits: tool_start, rag_doc (per doc), tool_end
       │
       ├─ LLM generates final answer
       │    └─ emits: llm_start, llm_end, agent_finish
       │
       └─ puts __done__ on queue
       │
       ▼
FastAPI async loop: drains queue → yields SSE events
       │
       ▼
Browser: useAgentStream reads stream
  → routes events to AgentTrace (observability)
  → routes final_response to ChatPanel (message bubble)
```

---

## Example Requests

### cURL — Send a message

```bash
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Tenho uma equipe de 15 pessoas e preciso de integrações com CRM",
    "provider": "openai"
  }'
```

### cURL — Index documents

```bash
curl -X POST http://localhost:8000/index \
  -H "Content-Type: application/json" \
  -d '{ "provider": "openai" }'
```

### cURL — Get session history

```bash
curl http://localhost:8000/session/YOUR-SESSION-ID
```

### cURL — Clear session

```bash
curl -X DELETE http://localhost:8000/session/YOUR-SESSION-ID
```

### Python — Consume the SSE stream

```python
import httpx, json

with httpx.stream("POST", "http://localhost:8000/chat/stream",
                  json={"message": "Compare Starter e Growth Plan", "provider": "openai"}) as r:
    for line in r.iter_lines():
        if line.startswith("data: "):
            event = json.loads(line[6:])
            print(f"[{event['type']}]", event.get("content") or event.get("message") or "")
```

---

## Troubleshooting

| Problem | Likely cause | Fix |
|---------|-------------|-----|
| `API offline` shown in sidebar | Backend not running | Run `uvicorn main:app --reload --port 8000` in `backend/` |
| `chromadb` import error | Missing dependency | `pip install -r requirements.txt` |
| Empty responses from agent | Documents not indexed | Click "Index Documents" in the sidebar |
| Upload fails with 422 | No source provided | Attach at least one file, URL, or text |
| Upload fails with 500 | Missing `python-multipart` | `pip install -r requirements.txt` |
| URL indexing returns empty | Page blocked or JS-rendered | Use a static/public URL; JS-heavy SPAs are not supported |
| `AuthenticationError` from OpenAI | Missing or invalid key | Check `OPENAI_API_KEY` in `.env` |
| `AuthenticationError` from Groq | Missing or invalid key | Check `GROQ_API_KEY` in `.env` |
| SSE stream hangs after 60s | Agent timeout | Reduce prompt complexity or switch provider |
| React app shows blank page | Build error | Run `npm install` then `npm run dev` in `frontend-web/` |
| ChromaDB dimension mismatch | Switched providers after indexing | Delete `backend/chroma_db/` and re-index (or just re-index — it auto-detects the change) |

---

## Design Decisions

**SSE over WebSockets** — The communication is unidirectional (server → client): the client sends one request and receives a stream of events. SSE is simpler, works over plain HTTP/1.1, and requires no extra libraries in the browser.

**Background thread for the agent** — LangChain's `AgentExecutor.invoke()` is synchronous. Running it directly inside an `async def` endpoint would block FastAPI's event loop. The solution is a `threading.Thread` bridged to the async loop via `asyncio.Queue` + `loop.call_soon_threadsafe`.

**ChromaDB** — Embedded, no separate server process, persists to disk, first-class LangChain integration. For production at scale, Pinecone or pgvector would be more appropriate.

**Two embedding options** — OpenAI `text-embedding-3-small` (higher quality, paid) vs. HuggingFace `all-MiniLM-L6-v2` (free, local). The `provider` field controls both the LLM and the embeddings throughout the entire stack. A `.provider` sentinel file in `chroma_db/` enables automatic detection of provider switches, triggering a clean rebuild.

**In-memory sessions** — Sessions are stored in a Python `dict`. They are lost on server restart. For production, replace with Redis. The 20-message cap prevents unbounded memory growth and keeps the context window manageable.

**No global state library on the frontend** — All state lives in the `useAgentStream` hook and flows down as props. The app is simple enough that Redux or Zustand would be over-engineering.

**CSS Modules over Tailwind** — Styles are co-located with components, class names never collide, and no build-time purge step is needed. The design system is expressed as CSS custom properties in `index.css`.

> See [ARCHITECTURE.md](ARCHITECTURE.md) for the full rationale behind each decision.

---

## Contributing

1. Fork the repository and create a feature branch.
2. Install dependencies: `pip install -r requirements.txt` and `npm install` inside `frontend-web/`.
3. Make your changes. Keep commits focused and descriptive.
4. Test the backend manually with the cURL examples above, and verify the React app renders correctly.
5. Open a pull request describing what changed and why.

Areas where contributions are especially welcome:
- Additional agent tools (e.g. `criar_ticket`, `verificar_uso`)
- Persistent session storage (Redis adapter)
- Unit tests for `vectorstore.py` and `saas_agent.py`
- Accessibility improvements in the React frontend

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for the full version history.

**Latest — v2.1.0**
- `POST /upload` endpoint — add files, URLs, and raw text to the vector store at runtime
- `KnowledgeManager` React component with drag & drop, URL input, and text input
- API Key input in Sidebar — per-request key override, persisted in `localStorage`
- Provider and API key now sent on every request (chat, index, upload)
- Groq `failed_generation` error handling with automatic retry and LLM fallback
- Agent responds in the user's language (removed hardcoded Portuguese)
- `max_iterations` raised to 100,000,000

**v2.0.0**
- React 19 + Vite 8 frontend with 3-column dark-theme layout
- Real-time SSE streaming replacing the synchronous `/chat` endpoint
- `AgentTrace` observability panel with color-coded event cards and live counters
- `useAgentStream` hook with `AbortController` support for mid-stream cancellation

---

## SCREENSHOTS

<img width="2932" height="1668" alt="image" src="https://github.com/user-attachments/assets/e10189a4-889d-4f1f-9c4a-2117c9a80881" />
<img width="2922" height="1649" alt="image" src="https://github.com/user-attachments/assets/75c0151a-a558-4072-a698-c917b5232a91" />
<img width="2939" height="1654" alt="image" src="https://github.com/user-attachments/assets/f1ead2b0-6002-4c8c-951c-58defc9027a2" />
<img width="2942" height="1655" alt="image" src="https://github.com/user-attachments/assets/54c8069b-524e-425e-bada-79dd4e057baa" />
