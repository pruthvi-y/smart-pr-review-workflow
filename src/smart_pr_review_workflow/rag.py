"""Small local RAG layer for the Stage 4 learning project."""

from __future__ import annotations

import os
from pathlib import Path

from langchain_chroma import Chroma
from langchain_aws import BedrockEmbeddings
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .model import get_bedrock_kwargs

BASE_DIR = Path(__file__).resolve().parents[2]
KNOWLEDGE_DIR = BASE_DIR / "knowledge"
CHROMA_DIR = BASE_DIR / ".chroma"
COLLECTION_NAME = "engineering_policy"


def get_embeddings() -> BedrockEmbeddings:
    """Create the Bedrock embedding client used by the local vector store."""
    model_id = os.getenv("BEDROCK_EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0")
    return BedrockEmbeddings(model_id=model_id, **get_bedrock_kwargs())


def load_knowledge_documents() -> list[Document]:
    """Load Markdown policy documents as LangChain Documents."""
    documents: list[Document] = []
    for path in sorted(KNOWLEDGE_DIR.glob("*.md")):
        if path.name.startswith("_"):
            continue
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            continue
        documents.append(Document(page_content=text, metadata={"source": path.name}))
    return documents


def get_vector_store() -> Chroma:
    """Create/open a local persistent Chroma store backed by Bedrock embeddings."""
    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=get_embeddings(),
        persist_directory=str(CHROMA_DIR),
    )


def build_index(force: bool = False) -> int:
    """Chunk and index the local knowledge base. Returns indexed chunk count."""
    store = get_vector_store()
    existing = store.get(include=[])
    existing_ids = existing.get("ids", []) if isinstance(existing, dict) else []

    if existing_ids and not force:
        return len(existing_ids)

    if existing_ids:
        store.delete(ids=existing_ids)

    splitter = RecursiveCharacterTextSplitter(chunk_size=900, chunk_overlap=120)
    chunks: list[Document] = []
    for document in load_knowledge_documents():
        chunks.extend(splitter.split_documents([document]))

    if not chunks:
        raise RuntimeError(f"No Markdown knowledge documents found in {KNOWLEDGE_DIR}")

    ids = [f"{doc.metadata.get('source', 'doc')}-{index}" for index, doc in enumerate(chunks)]
    store.add_documents(chunks, ids=ids)
    return len(chunks)


def retrieve_policy_context(query: str, k: int = 4) -> list[dict[str, str]]:
    """Retrieve the most relevant policy chunks for a PR review query."""
    store = get_vector_store()
    results = store.similarity_search_with_score(query, k=k)
    return [
        {
            "source": doc.metadata.get("source", "unknown"),
            "content": doc.page_content,
            "score": f"{score:.4f}",
        }
        for doc, score in results
    ]
