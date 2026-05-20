import os
import json
import asyncio
from langchain_groq import ChatGroq
from langchain_classic.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.callbacks.base import BaseCallbackHandler
from rag.vectorstore import get_retriever

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data")

with open(os.path.join(DATA_PATH, "products.json"), "r", encoding="utf-8") as f:
    PRODUCTS = json.load(f)


def get_llm(provider: str = "openai", callbacks=None, api_key: str = None):
    if provider == "groq":
        return ChatGroq(model="llama-3.3-70b-versatile", temperature=0.3, callbacks=callbacks,
                        api_key=api_key or os.getenv("GROQ_API_KEY"))
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(model="gpt-4o-mini", temperature=0.3, callbacks=callbacks,
                      api_key=api_key or os.getenv("OPENAI_API_KEY"))


class StreamingEventCallback(BaseCallbackHandler):
    def __init__(self, queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
        self.queue = queue
        self.loop = loop

    def _emit(self, event_type: str, data: dict):
        self.loop.call_soon_threadsafe(self.queue.put_nowait, {"type": event_type, **data})

    def on_tool_start(self, serialized, input_str, **kwargs):
        self._emit("tool_start", {
            "tool": serialized.get("name", "unknown"),
            "input": input_str if isinstance(input_str, str) else json.dumps(input_str)
        })

    def on_tool_end(self, output, **kwargs):
        out = output if isinstance(output, str) else str(output)
        self._emit("tool_end", {"output": out[:600]})

    def on_tool_error(self, error, **kwargs):
        self._emit("tool_error", {"error": str(error)})

    def on_llm_start(self, serialized, prompts, **kwargs):
        self._emit("llm_start", {"model": serialized.get("name", "llm")})

    def on_llm_end(self, response, **kwargs):
        self._emit("llm_end", {"message": "LLM finalizou geração"})

    def on_agent_action(self, action, **kwargs):
        self._emit("agent_action", {
            "tool": action.tool,
            "input": action.tool_input if isinstance(action.tool_input, str) else json.dumps(action.tool_input)
        })

    def on_agent_finish(self, finish, **kwargs):
        self._emit("agent_finish", {"message": "Agente concluiu raciocínio"})


def build_agent_streaming(provider: str = "openai", queue: asyncio.Queue = None, loop=None, api_key: str = None, reply_language: str = "the same language as the user's message"):
    cb = StreamingEventCallback(queue, loop)

    def _retrieve(query: str, k: int = 6):
        """Always creates a fresh retriever so newly added documents are included."""
        return get_retriever(provider, k=k, api_key=api_key).invoke(query)

    @tool
    def buscar_conhecimento(query: str) -> str:
        """Busca qualquer informação na base de conhecimento: planos, preços, FAQ, políticas, documentos e arquivos adicionados pelo usuário."""
        docs = _retrieve(query, k=6)
        results = []
        for d in docs:
            loop.call_soon_threadsafe(queue.put_nowait, {
                "type": "rag_doc",
                "source": d.metadata.get("source", "knowledge_base"),
                "preview": d.page_content[:200]
            })
            results.append(d.page_content)
        return "\n\n".join(results) if results else "Nenhum documento encontrado para essa consulta."

    @tool
    def recomendar_produtos(perfil: str) -> str:
        """Recomenda produtos e planos SaaSFlow com base no perfil e necessidades do cliente."""
        docs = _retrieve(perfil, k=6)
        for d in docs:
            loop.call_soon_threadsafe(queue.put_nowait, {
                "type": "rag_doc",
                "source": d.metadata.get("source", "products"),
                "preview": d.page_content[:200]
            })
        context = "\n\n".join([d.page_content for d in docs])
        llm = get_llm(provider, api_key=api_key)
        prompt = f"""Based on the client profile: "{perfil}"
And the available documents (products, plans and knowledge base):
{context}
Recommend the 2-3 most suitable products/plans. For each one explain:
1. Why it is ideal for this profile
2. Main benefits
3. Price
4. Relevant complementary add-ons
Be direct, empathetic and consultative. Reply in {reply_language}."""
        response = llm.invoke(prompt)
        return response.content

    @tool
    def listar_produtos(categoria: str = "todos") -> str:
        """Lista todos os produtos disponíveis. Categorias: plano, addon, servico, todos."""
        filtered = PRODUCTS if categoria == "todos" else [p for p in PRODUCTS if p["category"] == categoria]
        result = []
        for p in filtered:
            preco_label = "único" if p["category"] == "servico" else "mês"
            result.append(
                f"• {p['name']} - R$ {p['price']:.2f}/{preco_label}\n"
                f"  {p['description'][:100]}...\n"
                f"  ⭐ {p['rating']}/5 ({p['reviews']} avaliações)"
            )
        return "\n\n".join(result)

    @tool
    def comparar_planos(planos: str) -> str:
        """Compara dois ou mais planos lado a lado. Informe os nomes separados por vírgula."""
        nomes = [n.strip().lower() for n in planos.split(",")]
        selecionados = [p for p in PRODUCTS if any(n in p["name"].lower() for n in nomes)]
        if not selecionados:
            return "Planos não encontrados. Tente: Starter Plan, Growth Plan, Enterprise Plan"
        parts = ["COMPARAÇÃO DE PLANOS\n" + "=" * 40 + "\n"]
        for p in selecionados:
            preco_label = "único" if p["category"] == "servico" else "mês"
            features = "\n".join(f"  ✓ {f}" for f in p["features"])
            parts.append(f"📦 {p['name']} - R$ {p['price']:.2f}/{preco_label}\nFuncionalidades:\n{features}\nAvaliação: ⭐ {p['rating']}/5")
        return "\n\n".join(parts)

    tools = [buscar_conhecimento, recomendar_produtos, listar_produtos, comparar_planos]

    system_prompt = f"""You are Sofia, an intelligent virtual assistant for SaaSFlow, a SaaS business management platform.
Your role is to answer questions about plans, pricing, features, policies, and any documents added to the knowledge base.

CRITICAL LANGUAGE RULE: You MUST reply EXCLUSIVELY in {reply_language}. This is non-negotiable. Do not switch to any other language regardless of the language of the documents retrieved.

Guidelines:
- Use the `buscar_conhecimento` tool when the question is about SaaSFlow, its products, or topics that may be covered by uploaded documents — including any documents, CVs, manuals, or files the user has added
- When asked about a person, company, or topic you are not sure about, always search the knowledge base first before saying you don't know
- Do NOT use tools for simple greetings or pure general knowledge questions that clearly have no relation to any uploaded content
- Never invent or fabricate information about people, companies, or facts not present in the knowledge base
- If asked about something not in the knowledge base, say clearly that you don't have that information
- Never invent prices, features, or information not present in the documents
- When quoting document excerpts, preserve the original language of the document
- Always provide a final answer to the user"""

    llm = get_llm(provider, callbacks=[cb], api_key=api_key)

    if provider == "groq":
        from langgraph.prebuilt import create_react_agent

        def _run_groq(input_data: dict):
            messages = [SystemMessage(content=system_prompt)]
            messages.extend(input_data.get("chat_history", []))
            messages.append(HumanMessage(content=input_data["input"]))
            graph = create_react_agent(llm, tools)
            result = graph.invoke({"messages": messages})
            last = result["messages"][-1]
            return {"output": last.content}

        class _GroqExecutor:
            def invoke(self, input_data):
                return _run_groq(input_data)

        return _GroqExecutor(), cb

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent = create_openai_tools_agent(llm, tools, prompt)
    executor = AgentExecutor(agent=agent, tools=tools, verbose=False, max_iterations=10,
                             handle_parsing_errors=True, callbacks=[cb],
                             return_intermediate_steps=False)
    return executor, cb


def format_history(history: list) -> list:
    messages = []
    for msg in history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))
    return messages
