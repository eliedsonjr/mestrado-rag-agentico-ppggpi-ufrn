from typing import Any
import config
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore, FastEmbedSparse, RetrievalMode
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

class VectorDbManager:
    """
    Gerenciador do Banco de Dados Vetorial (Qdrant).

    Responsável por inicializar os modelos de embedding e gerenciar as coleções 
    de vetores. Implementa uma arquitetura de Busca Híbrida (Hybrid Search), 
    combinando vetores densos (para similaridade semântica) e vetores esparsos 
    BM25 (para correspondência exata de palavras-chave institucionais).
    """
    __client: QdrantClient
    __dense_embeddings: HuggingFaceEmbeddings
    __sparse_embeddings: FastEmbedSparse
    
    def __init__(self) -> None:
        """
        Inicializa o cliente Qdrant e os modelos de representação vetorial (Embeddings).
        """
        self.__client = QdrantClient(path=config.QDRANT_DB_PATH)
        self.__dense_embeddings = HuggingFaceEmbeddings(model_name=config.DENSE_MODEL)
        self.__sparse_embeddings = FastEmbedSparse(model_name=config.SPARSE_MODEL)

    def create_collection(self, collection_name: str) -> None:
        """
        Cria uma nova coleção no Qdrant configurada para Busca Híbrida.

        Garante que a coleção possua parâmetros tanto para os vetores densos 
        (medida de distância por Cosseno) quanto para vetores esparsos.

        Args:
            collection_name (str): Nome da coleção a ser criada.
        """
        if not self.__client.collection_exists(collection_name):
            print(f"🔧 Criando coleção vetorial: {collection_name}...")
            self.__client.create_collection(
                collection_name=collection_name,
                vectors_config=qmodels.VectorParams(
                    size=len(self.__dense_embeddings.embed_query("test")), 
                    distance=qmodels.Distance.COSINE
                ),
                sparse_vectors_config={config.SPARSE_VECTOR_NAME: qmodels.SparseVectorParams()},
            )
            print(f"✓ Coleção criada: {collection_name}")
        else:
            print(f"✓ Coleção já existente: {collection_name}")

    def delete_collection(self, collection_name: str) -> None:
        """
        Remove permanentemente uma coleção vetorial do banco de dados.

        Args:
            collection_name (str): Nome da coleção a ser excluída.
        """
        try:
            if self.__client.collection_exists(collection_name):
                print(f"⚠️ Removendo coleção Qdrant existente: {collection_name}")
                self.__client.delete_collection(collection_name)
        except Exception as e:
            print(f"Aviso: Não foi possível deletar a coleção {collection_name}: {e}")

    def get_collection(self, collection_name: str) -> QdrantVectorStore:
        """
        Obtém a interface de conexão (VectorStore) para realizar buscas e inserções.

        Configura explicitamente o modo de recuperação para HYBRID, o que funde 
        os escores dos algoritmos denso e esparso para um rankeamento superior.

        Args:
            collection_name (str): Nome da coleção alvo.

        Returns:
            QdrantVectorStore: Objeto do LangChain pronto para operações de IR (Information Retrieval).
        """
        try:
            return QdrantVectorStore(
                    client=self.__client,
                    collection_name=collection_name,
                    embedding=self.__dense_embeddings,
                    sparse_embedding=self.__sparse_embeddings,
                    retrieval_mode=RetrievalMode.HYBRID,
                    sparse_vector_name=config.SPARSE_VECTOR_NAME
                )
        except Exception as e:
            print(f"Erro ao obter a coleção {collection_name}: {e}")
            raise
