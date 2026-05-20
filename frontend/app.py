import streamlit as st
import requests
import uuid
import json

API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="SaaSFlow Assistant",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 1.5rem;
    }
    .product-card {
        background: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 0.8rem;
    }
    .price-tag {
        background: #667eea;
        color: white;
        padding: 0.2rem 0.6rem;
        border-radius: 20px;
        font-weight: bold;
        font-size: 0.9rem;
    }
    .chat-user {
        background: #667eea;
        color: white;
        padding: 0.8rem 1rem;
        border-radius: 12px 12px 2px 12px;
        margin: 0.5rem 0;
        max-width: 80%;
        margin-left: auto;
    }
    .chat-assistant {
        background: #f0f2f6;
        color: #1a1a2e;
        padding: 0.8rem 1rem;
        border-radius: 12px 12px 12px 2px;
        margin: 0.5rem 0;
        max-width: 85%;
    }
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1.5rem;
    }
</style>
""", unsafe_allow_html=True)

import html


def _safe(text: str) -> str:
    return html.escape(str(text))



    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []
if "provider" not in st.session_state:
    st.session_state.provider = "openai"
if "indexed" not in st.session_state:
    st.session_state.indexed = False

with st.sidebar:
    st.markdown("## ⚙️ Configurações")

    provider = st.selectbox(
        "Provedor de IA",
        ["openai", "groq"],
        index=0 if st.session_state.provider == "openai" else 1,
        help="OpenAI GPT-4o-mini ou Groq Llama 3.3 (gratuito)"
    )
    st.session_state.provider = provider

    st.markdown("---")
    st.markdown("### 🗄️ Base de Conhecimento")

    if st.button("📚 Indexar Documentos", use_container_width=True):
        with st.spinner("Indexando..."):
            try:
                r = requests.post(f"{API_URL}/index", json={"provider": provider})
                if r.status_code == 200:
                    st.success("✅ Indexado com sucesso!")
                    st.session_state.indexed = True
                else:
                    st.error(f"Erro: {r.text}")
            except Exception as e:
                st.error(f"API offline: {e}")

    st.markdown("---")
    st.markdown("### 💬 Sessão")
    st.code(f"ID: {st.session_state.session_id[:8]}...", language=None)

    if st.button("🔄 Nova Conversa", use_container_width=True):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()

    st.markdown("---")
    st.markdown("### 💡 Sugestões de Perguntas")
    suggestions = [
        "Qual plano é ideal para uma equipe de 10 pessoas?",
        "Compare o Starter com o Growth",
        "Quais add-ons vocês oferecem?",
        "Como funciona o cancelamento?",
        "Preciso de segurança LGPD, o que recomendam?",
        "Qual o plano mais barato com suporte prioritário?"
    ]
    for s in suggestions:
        if st.button(s, use_container_width=True, key=f"sug_{s[:20]}"):
            st.session_state.pending_message = s
            st.rerun()

    st.markdown("---")
    st.markdown("### 📦 Catálogo Rápido")
    try:
        r = requests.get(f"{API_URL}/products")
        if r.status_code == 200:
            products = r.json()
            for p in products:
                emoji = "📦" if p["category"] == "plano" else "🔧" if p["category"] == "addon" else "🎯"
                st.markdown(f"{emoji} **{p['name']}** — R$ {p['price']}")
    except:
        st.info("Inicie a API para ver o catálogo")

st.markdown("""
<div class="main-header">
    <h1>🚀 SaaSFlow Assistant</h1>
    <p>Assistente inteligente com RAG + Recomendação personalizada</p>
</div>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("🤖 Modelo", "GPT-4o-mini" if provider == "openai" else "Llama 3.3")
with col2:
    st.metric("💬 Mensagens", len(st.session_state.messages))
with col3:
    st.metric("📚 RAG", "Ativo" if st.session_state.indexed else "Pendente")

st.markdown("---")

chat_container = st.container()

with chat_container:
    if not st.session_state.messages:
        st.markdown("""
        <div class="chat-assistant">
        👋 Olá! Sou a <strong>Sofia</strong>, assistente virtual da SaaSFlow!<br><br>
        Posso te ajudar com:<br>
        • 📋 Informações sobre planos e preços<br>
        • 🎯 Recomendações personalizadas para seu perfil<br>
        • 🔍 Comparação entre planos<br>
        • ❓ Dúvidas sobre funcionalidades e políticas<br><br>
        Como posso te ajudar hoje?
        </div>
        """, unsafe_allow_html=True)

    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(f'<div class="chat-user">👤 {_safe(msg["content"])}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="chat-assistant">🤖 {_safe(msg["content"])}</div>', unsafe_allow_html=True)

pending = st.session_state.pop("pending_message", None)

with st.form("chat_form", clear_on_submit=True):
    col_input, col_btn = st.columns([5, 1])
    with col_input:
        user_input = st.text_input(
            "Mensagem",
            value=pending or "",
            placeholder="Digite sua pergunta sobre planos, preços ou funcionalidades...",
            label_visibility="collapsed"
        )
    with col_btn:
        submitted = st.form_submit_button("Enviar 📤", use_container_width=True)

def call_chat_stream(message: str, session_id: str, provider: str) -> str:
    """Consome o endpoint SSE e retorna a resposta final."""
    payload = {"message": message, "session_id": session_id, "provider": provider}
    try:
        with requests.post(f"{API_URL}/chat/stream", json=payload, stream=True, timeout=90) as r:
            if r.status_code != 200:
                detail = ""
                try:
                    detail = r.json().get("detail", r.text)
                except Exception:
                    detail = r.text
                return f"❌ Erro na API: {detail}"
            for line in r.iter_lines(decode_unicode=True):
                if not line.startswith("data: "):
                    continue
                try:
                    ev = json.loads(line[6:])
                    if ev.get("type") == "final_response":
                        return ev.get("content", "")
                    if ev.get("type") == "error":
                        return f"❌ {ev.get('message', 'Erro desconhecido')}"
                except Exception:
                    continue
    except requests.exceptions.ConnectionError:
        return "❌ Não consegui conectar à API. Verifique se o backend está rodando com `uvicorn main:app --reload`"
    except Exception as e:
        return f"❌ Erro inesperado: {str(e)}"
    return "❌ Sem resposta do agente."


if submitted and user_input.strip():
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.spinner("Sofia está pensando..."):
        answer = call_chat_stream(user_input, st.session_state.session_id, st.session_state.provider)
        st.session_state.messages.append({"role": "assistant", "content": answer})
    st.rerun()
