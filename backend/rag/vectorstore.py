import os
import json
import shutil
from langchain_community.document_loaders import TextLoader, PyPDFLoader, CSVLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document

CHROMA_PATH = os.path.join(os.path.dirname(__file__), "..", "chroma_db")
DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data")
PROVIDER_FILE = os.path.join(os.path.dirname(__file__), "..", "chroma_db", ".provider")


def get_embeddings(provider: str = "openai", api_key: str = None):
    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(model="text-embedding-3-small",
                                api_key=api_key or os.getenv("OPENAI_API_KEY"))
    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")


def _get_stored_provider() -> str:
    if os.path.exists(PROVIDER_FILE):
        with open(PROVIDER_FILE, "r") as f:
            return f.read().strip()
    return ""


def _save_provider(provider: str):
    os.makedirs(CHROMA_PATH, exist_ok=True)
    with open(PROVIDER_FILE, "w") as f:
        f.write(provider)


def build_vectorstore(provider: str = "openai", api_key: str = None):
    if os.path.exists(CHROMA_PATH) and _get_stored_provider() != provider:
        shutil.rmtree(CHROMA_PATH)

    docs = []

    kb_path = os.path.join(DATA_PATH, "knowledge_base.txt")
    loader = TextLoader(kb_path, encoding="utf-8")
    docs.extend(loader.load())

    products_path = os.path.join(DATA_PATH, "products.json")
    with open(products_path, "r", encoding="utf-8") as f:
        products = json.load(f)

    for p in products:
        content = (
            f"Produto: {p['name']}\n"
            f"Categoria: {p['category']}\n"
            f"Preço: R$ {p['price']:.2f}\n"
            f"Descrição: {p['description']}\n"
            f"Funcionalidades: {', '.join(p['features'])}\n"
            f"Tags: {', '.join(p['tags'])}\n"
            f"Avaliação: {p['rating']}/5 ({p['reviews']} avaliações)"
        )
        docs.append(Document(page_content=content, metadata={"source": "products", "product_id": p["id"]}))

    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    chunks = splitter.split_documents(docs)

    embeddings = get_embeddings(provider, api_key=api_key)
    vectorstore = Chroma.from_documents(chunks, embeddings, persist_directory=CHROMA_PATH)
    _save_provider(provider)
    return vectorstore


def add_documents_to_store(path: str, provider: str = "openai", api_key: str = None,
                           source_name: str = "upload", is_url: bool = False, raw_text: str = None) -> int:
    docs = []
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)

    if raw_text:
        docs = [Document(page_content=raw_text, metadata={"source": source_name})]

    elif is_url:
        from langchain_community.document_loaders import WebBaseLoader
        loader = WebBaseLoader(path)
        docs = loader.load()
        for d in docs:
            d.metadata["source"] = source_name

    else:
        ext = os.path.splitext(path)[1].lower()
        if ext == ".pdf":
            loader = PyPDFLoader(path)
        elif ext == ".csv":
            loader = CSVLoader(path)
        elif ext == ".docx":
            from langchain_community.document_loaders import Docx2txtLoader
            loader = Docx2txtLoader(path)
        elif ext in (".md", ".markdown"):
            try:
                from langchain_community.document_loaders import UnstructuredMarkdownLoader
                loader = UnstructuredMarkdownLoader(path)
            except Exception:
                loader = TextLoader(path, encoding="utf-8")
        elif ext == ".json":
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            text = json.dumps(data, ensure_ascii=False, indent=2)
            docs = [Document(page_content=text, metadata={"source": source_name})]
        else:
            loader = TextLoader(path, encoding="utf-8")

        if not docs:
            docs = loader.load()
            for d in docs:
                d.metadata["source"] = source_name

    chunks = splitter.split_documents(docs)
    embeddings = get_embeddings(provider, api_key=api_key)

    if os.path.exists(CHROMA_PATH) and _get_stored_provider() == provider:
        vs = Chroma(persist_directory=CHROMA_PATH, embedding_function=embeddings)
        vs.add_documents(chunks)
    else:
        Chroma.from_documents(chunks, embeddings, persist_directory=CHROMA_PATH)
        _save_provider(provider)

    return len(chunks)


def load_vectorstore(provider: str = "openai", api_key: str = None):
    embeddings = get_embeddings(provider, api_key=api_key)
    if os.path.exists(CHROMA_PATH) and _get_stored_provider() == provider:
        return Chroma(persist_directory=CHROMA_PATH, embedding_function=embeddings)
    return build_vectorstore(provider, api_key=api_key)


def get_retriever(provider: str = "openai", k: int = 4, api_key: str = None):
    vs = load_vectorstore(provider, api_key=api_key)
    return vs.as_retriever(search_kwargs={"k": k})
