"""
Módulo de Configuração Central (Single Source of Truth).

Armazena todas as constantes, caminhos de diretórios, nomes de modelos 
e parâmetros de fragmentação (chunking) utilizados pelo sistema RAG. 
Facilita a reprodutibilidade e o ajuste fino (fine-tuning) da pesquisa.
"""
from typing import List, Tuple

# --- Configuração de Diretórios ---
MARKDOWN_DIR: str = "markdown_docs"
PARENT_STORE_PATH: str = "parent_store"
QDRANT_DB_PATH: str = "qdrant_db"
DOCS_DIR: str = "docs"
LOGS_DIR: str = "logs"

# --- Configuração do Qdrant (Banco Vetorial) ---
CHILD_COLLECTION: str = "document_child_chunks"
SPARSE_VECTOR_NAME: str = "sparse"

# --- Configuração dos Modelos (IA e Embeddings) ---
DENSE_MODEL: str = "sentence-transformers/all-mpnet-base-v2"
SPARSE_MODEL: str = "Qdrant/bm25"
LLM_MODEL: str = "gemini-2.5-flash"
LLM_TEMPERATURE: float = 0.0

# --- Configuração de Fragmentação (Text Splitter) ---
CHILD_CHUNK_SIZE: int = 500
CHILD_CHUNK_OVERLAP: int = 100
MIN_PARENT_SIZE: int = 2000
MAX_PARENT_SIZE: int = 10000

# Estratégia de quebra de cabeçalhos Markdown para preservação semântica
HEADERS_TO_SPLIT_ON: List[Tuple[str, str]] = [
    ("#", "H1"),
    ("##", "H2"),
    ("###", "H3")
]
