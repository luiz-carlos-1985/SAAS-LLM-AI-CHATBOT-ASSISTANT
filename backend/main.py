import os
import uuid
import json
import asyncio
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

from agents.saas_agent import build_agent_streaming, format_history
from rag.vectorstore import build_vectorstore

app = FastAPI(title="SaaSFlow Assistant API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

sessions: dict = {}


ALLOWED_PROVIDERS = {"openai", "groq"}


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    provider: Optional[str] = "openai"
    api_key: Optional[str] = None

    def validate_fields(self):
        msg = self.message.strip()
        if not msg:
            raise HTTPException(status_code=422, detail="Mensagem não pode ser vazia")
        if len(msg) > 2000:
            raise HTTPException(status_code=422, detail="Mensagem muito longa (máx. 2000 caracteres)")
        if self.provider not in ALLOWED_PROVIDERS:
            raise HTTPException(status_code=422, detail=f"Provedor inválido. Use: {', '.join(ALLOWED_PROVIDERS)}")
        return msg


class IndexRequest(BaseModel):
    provider: Optional[str] = "openai"
    api_key: Optional[str] = None

    def validate_fields(self):
        if self.provider not in ALLOWED_PROVIDERS:
            raise HTTPException(status_code=422, detail=f"Provedor inválido. Use: {', '.join(ALLOWED_PROVIDERS)}")


def sse_event(event_type: str, data: dict) -> str:
    payload = json.dumps({"type": event_type, "ts": datetime.utcnow().isoformat(), **data})
    return f"data: {payload}\n\n"


@app.get("/")
def root():
    return {"status": "ok", "service": "SaaSFlow Assistant API"}


@app.post("/index")
def index_documents(req: IndexRequest):
    req.validate_fields()
    try:
        build_vectorstore(req.provider, api_key=req.api_key)
        return {"status": "success", "message": "Base de conhecimento indexada com sucesso"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    message = req.validate_fields()
    session_id = req.session_id or str(uuid.uuid4())
    if session_id not in sessions:
        sessions[session_id] = []
    history = sessions[session_id]

    async def event_generator():
        final_response = ""
        try:
            yield sse_event("session", {"session_id": session_id})
            yield sse_event("thinking", {"message": "Analisando sua pergunta..."})

            loop = asyncio.get_running_loop()
            events_queue = asyncio.Queue()

            def run_agent():
                try:
                    agent, event_cb = build_agent_streaming(req.provider, events_queue, loop, api_key=req.api_key)
                    result = agent.invoke({
                        "input": message,
                        "chat_history": format_history(history)
                    })
                    loop.call_soon_threadsafe(events_queue.put_nowait, {"type": "__done__", "output": result["output"]})
                except Exception as e:
                    err_str = str(e)
                    if "failed_generation" in err_str or "Failed to call a function" in err_str:
                        # Groq tool-calling failure: retry with explicit instruction
                        try:
                            agent2, _ = build_agent_streaming(req.provider, events_queue, loop, api_key=req.api_key)
                            result2 = agent2.invoke({
                                "input": message,
                                "chat_history": format_history(history)
                            })
                            loop.call_soon_threadsafe(events_queue.put_nowait, {"type": "__done__", "output": result2["output"]})
                            return
                        except Exception:
                            pass
                        # Final fallback: LLM direct (no tools)
                        try:
                            from agents.saas_agent import get_llm
                            llm = get_llm(req.provider, api_key=req.api_key)
                            fallback = llm.invoke(message)
                            loop.call_soon_threadsafe(events_queue.put_nowait, {"type": "__done__", "output": fallback.content})
                            return
                        except Exception as e2:
                            loop.call_soon_threadsafe(events_queue.put_nowait, {"type": "__error__", "message": str(e2)})
                            return
                    loop.call_soon_threadsafe(events_queue.put_nowait, {"type": "__error__", "message": err_str})

            import threading
            thread = threading.Thread(target=run_agent)
            thread.start()

            while True:
                try:
                    event = await asyncio.wait_for(events_queue.get(), timeout=60.0)
                except asyncio.TimeoutError:
                    yield sse_event("error", {"message": "Timeout aguardando resposta do agente"})
                    break

                if event["type"] == "__done__":
                    final_response = event["output"]
                    yield sse_event("final_response", {"content": final_response})
                    break
                elif event["type"] == "__error__":
                    yield sse_event("error", {"message": event["message"]})
                    break
                else:
                    yield sse_event(event["type"], {k: v for k, v in event.items() if k != "type"})

            thread.join(timeout=5)

        except Exception as e:
            yield sse_event("error", {"message": str(e)})
            return

        if final_response:
            history.append({"role": "user", "content": message})
            history.append({"role": "assistant", "content": final_response})
            if len(history) > 20:
                sessions[session_id] = history[-20:]

        yield sse_event("done", {"session_id": session_id, "history_length": len(sessions.get(session_id, []))})

    return StreamingResponse(event_generator(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/session/{session_id}")
def get_session(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    return {"session_id": session_id, "history": sessions[session_id]}


@app.delete("/session/{session_id}")
def clear_session(session_id: str):
    sessions.pop(session_id, None)
    return {"status": "cleared", "session_id": session_id}


@app.get("/products")
def list_products():
    products_path = os.path.join(os.path.dirname(__file__), "data", "products.json")
    with open(products_path, "r", encoding="utf-8") as f:
        return json.load(f)
