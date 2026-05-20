# Architecture & Design Decisions

## Why SSE instead of WebSockets?

Server-Sent Events are unidirectional (server → client), which is exactly what's needed here: the client sends one HTTP request and receives a stream of events back. SSE is simpler to implement, works over standard HTTP/1.1, and is natively supported by browsers without extra libraries. WebSockets would add bidirectional complexity that isn't needed.

## Why a background thread for the agent?

LangChain's `AgentExecutor.invoke()` is synchronous. FastAPI runs on an async event loop. Running a blocking synchronous call directly inside an `async def` endpoint would block the entire event loop, preventing other requests from being served.

The solution: run the agent in a `threading.Thread`, and use `asyncio.Queue` + `loop.call_soon_threadsafe` as a thread-safe bridge to pass events back to the async generator.

```
async event loop          sync thread
─────────────────         ────────────────
await queue.get()  ◄───  loop.call_soon_threadsafe(queue.put_nowait, event)
```

## Why ChromaDB?

ChromaDB is embedded (no separate server process), persists to disk, and has first-class LangChain integration. For a project of this scale it's the right tradeoff between simplicity and capability. For production at scale, Pinecone or pgvector would be more appropriate.

## Why two embedding options?

- **OpenAI `text-embedding-3-small`**: higher quality, costs money per token, requires API key.
- **HuggingFace `all-MiniLM-L6-v2`**: runs locally, completely free, slightly lower quality.

The provider selection is passed through the entire stack so the same `provider` field controls both the LLM and the embeddings.

### Provider change detection

Switching providers after indexing causes a ChromaDB dimension mismatch (OpenAI: 1536 dims, HuggingFace: 384 dims). To handle this transparently, `build_vectorstore` writes the active provider name to `chroma_db/.provider`. On the next call, if the stored provider differs from the requested one, `chroma_db/` is deleted automatically before rebuilding. Users never need to manually delete the directory.

## Why `create_openai_tools_agent` instead of `create_react_agent`?

OpenAI Tools Agent uses structured function/tool calling via the model's native API, which is more reliable than ReAct's text-based reasoning loop. Both OpenAI and Groq support the tools API, so this works with both providers.

## Why are the tools in Portuguese?

The agent (Sofia) operates exclusively in Brazilian Portuguese. Keeping tool names and docstrings in Portuguese ensures the LLM's tool-selection reasoning stays in the same language as the conversation, reducing translation overhead and improving reliability with both GPT-4o-mini and Llama 3.3.

## Session storage

Sessions are stored in a Python `dict` in memory. This means sessions are lost on server restart. For production, replace with Redis or a database. The 20-message cap prevents unbounded memory growth and keeps the context window manageable.

## Frontend state management

No Redux, Zustand, or Context API. All state lives in the `useAgentStream` hook and flows down as props. The app is simple enough that this is the right call — adding a state library would be over-engineering.

## CSS Modules over Tailwind

CSS Modules keep styles co-located with components, avoid class name collisions, and don't require a build-time purge step. The design system is expressed as CSS custom properties in `index.css`, giving the same token-based consistency as Tailwind without the dependency.
