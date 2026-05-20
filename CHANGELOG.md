# Changelog

## [2.1.0] — Knowledge Manager + API Key UI

### Added
- `POST /upload` endpoint — accepts `multipart/form-data` with files (`.txt`, `.pdf`, `.md`, `.csv`, `.json`), URLs, and raw text; adds to existing ChromaDB without full rebuild
- `add_documents_to_store()` in `vectorstore.py` — unified ingestion function supporting all source types
- `KnowledgeManager` React component — collapsible panel with drag & drop file upload, URL input, and text input; live source list with chunk counts and status
- API Key input in Sidebar — per-request key override persisted in `localStorage`; falls back to server `.env` if empty
- New dependencies: `unstructured`, `beautifulsoup4`, `lxml`, `python-multipart`

### Changed
- `ChatRequest` and `IndexRequest` now accept optional `api_key` field
- `get_llm`, `get_embeddings`, `build_vectorstore`, `get_retriever` all accept `api_key` parameter
- Agent responds in the user's input language (removed hardcoded Portuguese instruction)
- `max_iterations` raised to 100,000,000
- Groq `failed_generation` errors trigger automatic retry then LLM-direct fallback
- `useAgentStream` exposes `apiKey` / `setApiKey`; both `provider` and `apiKey` persisted in `localStorage`
- `App.jsx` passes `apiKey` and `setApiKey` to `Sidebar`

---

## [2.0.0] — React Frontend + Real-time Observability

### Added
- React 19 + Vite 8 frontend (`frontend-web/`) with 3-column dark-theme layout
- `POST /chat/stream` SSE endpoint replacing the previous `POST /chat` endpoint
- `StreamingEventCallback` — LangChain callback that emits 9 event types in real time
- `AgentTrace` component — live observability panel with color-coded event cards and counters
- `useAgentStream` hook — SSE consumer with `AbortController` support for mid-stream cancellation
- `Sidebar` component — API health check, provider toggle, index button, product catalog
- `ChatPanel` component — conversation UI with typing indicator and stop button
- Provider auto-detection in `vectorstore.py` — automatic `chroma_db/` rebuild when switching between OpenAI and HuggingFace embeddings
- `BACKEND.md`, `FRONTEND.md`, `ARCHITECTURE.md` documentation files

### Changed
- `saas_agent.py` — replaced `build_agent()` with `build_agent_streaming()` that accepts a queue and event loop; tools renamed to Portuguese (`buscar_conhecimento`, `recomendar_produtos`, `listar_produtos`, `comparar_planos`)
- `main.py` — replaced synchronous `/chat` endpoint with async SSE `/chat/stream` endpoint; added input validation (max 2000 chars, provider allowlist)
- `README.md` — fully rewritten with complete API reference, accurate versions, and Portuguese tool names

### Removed
- Synchronous `POST /chat` endpoint (replaced by `/chat/stream`)

---

## [1.0.0] — Initial Release

### Added
- FastAPI backend with RAG pipeline (ChromaDB + LangChain)
- LangChain OpenAI Tools Agent with 4 tools: `search_knowledge`, `recommend_products`, `list_products`, `compare_plans`
- Dual LLM support: OpenAI GPT-4o-mini and Groq Llama 3.3-70b
- Dual embedding support: OpenAI text-embedding-3-small and HuggingFace all-MiniLM-L6-v2
- Fictional SaaS product catalog (8 products across 3 categories)
- Knowledge base with full platform documentation and 12 FAQ entries
- Streamlit frontend (`frontend/app.py`)
- Session management with 20-message history cap
- `GET /products`, `GET /session/{id}`, `DELETE /session/{id}` endpoints
