# Backend — SaaSFlow Assistant API

FastAPI application that exposes the LangChain agent via a Server-Sent Events (SSE) streaming endpoint.

## Entry Point

`main.py` — run with:

```bash
uvicorn main:app --reload --port 8000
```

## Module Overview

```
backend/
├── main.py              # FastAPI app, request models, SSE endpoint
├── agents/
│   └── saas_agent.py    # Agent builder, tools, streaming callback
└── rag/
    └── vectorstore.py   # ChromaDB setup, embeddings, retriever
```

---

## `main.py`

### Request Models

**`ChatRequest`**
| Field | Type | Default | Constraints | Description |
|-------|------|---------|-------------|-------------|
| `message` | `str` | required | max 2000 chars | User's input message |
| `session_id` | `str` | `None` | — | UUID to continue an existing conversation. Auto-generated if omitted |
| `provider` | `str` | `"openai"` | `"openai"` or `"groq"` | LLM + embedding provider |
| `api_key` | `str` | `None` | — | Optional key override — takes precedence over server `.env` |

**`IndexRequest`**
| Field | Type | Default | Constraints | Description |
|-------|------|---------|-------------|-------------|
| `provider` | `str` | `"openai"` | `"openai"` or `"groq"` | Embedding provider to use when building the vector store |
| `api_key` | `str` | `None` | — | Optional key override |

Both models expose a `validate_fields()` method that raises `HTTPException 422` on invalid input.

### Session Management

Sessions are stored in a module-level `dict` keyed by `session_id`. Each session holds a list of `{"role": "user"|"assistant", "content": str}` dicts. History is capped at the last 20 messages to control context window size. Sessions are lost on server restart.

### SSE Streaming (`POST /chat/stream`)

The endpoint uses `asyncio.Queue` as a bridge between the synchronous LangChain agent (running in a background thread) and the async FastAPI event generator:

```
asyncio event loop (async)          background thread (sync)
─────────────────────────           ────────────────────────
event_generator()                   run_agent()
  await queue.get()  ◄────────────  queue.put_nowait(event)
  yield SSE event                   (via loop.call_soon_threadsafe)
```

Timeout is set to 60 seconds per event. If the queue produces no event within that window, an `error` SSE event is emitted and the stream closes.

The thread is joined with a 5-second timeout after the agent finishes. Session history is only updated if a `final_response` was produced.

---

## `agents/saas_agent.py`

### `StreamingEventCallback`

Extends `BaseCallbackHandler`. Intercepts LangChain lifecycle hooks and pushes structured dicts onto the `asyncio.Queue` using `loop.call_soon_threadsafe` (thread-safe bridge).

Hooks implemented:

| Hook | SSE event emitted |
|------|------------------|
| `on_llm_start` | `llm_start` |
| `on_llm_end` | `llm_end` |
| `on_tool_start` | `tool_start` |
| `on_tool_end` | `tool_end` (output truncated to 600 chars) |
| `on_tool_error` | `tool_error` |
| `on_agent_action` | `agent_action` |
| `on_agent_finish` | `agent_finish` |

### `build_agent_streaming(provider, queue, loop)`

Builds and returns a configured `(AgentExecutor, StreamingEventCallback)` tuple with the callback attached to both the LLM and the executor.

The agent uses `create_openai_tools_agent` (from `langchain_classic`) which relies on OpenAI-style function/tool calling. This works with both OpenAI and Groq models that support the tools API.

**Agent configuration:**
- `max_iterations=100_000_000` — effectively unlimited
- `handle_parsing_errors=True` — recovers from malformed tool call responses
- `verbose=False` — suppresses stdout logging (events go through the callback instead)

**System prompt (Sofia):** Friendly, empathetic assistant for SaaSFlow. Responds in the same language as the user. Never invents prices or features. Answers off-topic questions directly without using tools.

### Tools

All four tools are defined as closures inside `build_agent_streaming` so they have access to `queue` and `loop` for emitting `rag_doc` events during retrieval.

| Tool | Description |
|------|-------------|
| `buscar_conhecimento(query)` | Semantic search over knowledge base and products (top-4 chunks) |
| `recomendar_produtos(perfil)` | Profile-based recommendation using top-6 chunks + LLM synthesis |
| `listar_produtos(categoria)` | Lists products filtered by `plano`, `addon`, `servico`, or `todos` |
| `comparar_planos(planos)` | Side-by-side feature comparison for comma-separated plan names |

### `format_history(history)`

Converts the session history list (`[{"role": ..., "content": ...}]`) into LangChain `HumanMessage` / `AIMessage` objects for the `chat_history` prompt slot.

### `POST /upload` — `multipart/form-data`

Adds documents to the **existing** vector store without a full rebuild. Accepts any combination of:

| Field | Type | Description |
|-------|------|-------------|
| `provider` | `string` | `"openai"` or `"groq"` |
| `api_key` | `string` | Optional key override |
| `files` | `File[]` | `.txt`, `.pdf`, `.md`, `.csv`, `.json` |
| `url` | `string` | Web page to scrape and index |
| `text` | `string` | Raw text to index directly |

File handling per extension:
- `.pdf` → `PyPDFLoader`
- `.csv` → `CSVLoader`
- `.md` → `UnstructuredMarkdownLoader` (falls back to `TextLoader` if `unstructured` not installed)
- `.json` → serialized to text via `json.dumps`
- `.txt` and others → `TextLoader`
- URL → `WebBaseLoader` (requires `beautifulsoup4` + `lxml`)

---

## `rag/vectorstore.py`

### `add_documents_to_store(path, provider, api_key, source_name, is_url, raw_text)`

Adds documents from a single source to the existing ChromaDB. Called by `POST /upload` once per source item. If the store doesn't exist yet, creates it. Supports files, URLs, and raw text strings.

### `build_vectorstore(provider)`

Full rebuild of the vector store. Called by `POST /index`. Steps:

1. If `chroma_db/` exists and the stored provider differs from the requested one, delete `chroma_db/` to avoid embedding dimension mismatch
2. Load `knowledge_base.txt` with `TextLoader`
3. Load `products.json` and convert each product to a `Document` with structured text
4. Split all documents with `RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)`
5. Generate embeddings (OpenAI `text-embedding-3-small` or HuggingFace `all-MiniLM-L6-v2`)
6. Persist to `backend/chroma_db/`
7. Write the provider name to `backend/chroma_db/.provider` for future change detection

### `load_vectorstore(provider)`

Loads an existing ChromaDB from disk if `chroma_db/` exists **and** the stored provider matches. Otherwise calls `build_vectorstore`.

### `get_retriever(provider, k=4)`

Returns a LangChain `VectorStoreRetriever` configured for top-`k` similarity search.

> **Embedding dimensions:** OpenAI `text-embedding-3-small` → 1536 dims. HuggingFace `all-MiniLM-L6-v2` → 384 dims. Mixing them in the same ChromaDB collection causes a dimension mismatch error — the auto-detection logic in `build_vectorstore` handles this automatically.
