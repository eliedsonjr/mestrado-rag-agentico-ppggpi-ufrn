import uuid
import os
from typing import Dict, Any, Optional

# from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI

import config
from db.vector_db_manager import VectorDbManager
from db.parent_store_manager import ParentStoreManager
from document_chunker import DocumentChuncker
from rag_agent.tools import ToolFactory
from rag_agent.graph import create_agent_graph

class RAGSystem:
    """
    Orquestrador central do sistema RAG (Retrieval-Augmented Generation) do CERES/UFRN.
    
    Esta classe gerencia o ciclo de vida dos componentes principais do assistente,
    incluindo o banco de dados vetorial, o armazenamento de fragmentos originais (pai),
    o processador de textos (chunker) e a inicialização do grafo do agente cognitivo (LangGraph).
    """
    
    def __init__(self, collection_name: str = config.CHILD_COLLECTION) -> None:
        """
        Inicializa os gerenciadores de dados e a sessão do agente.

        Args:
            collection_name (str, opcional): Nome da coleção no banco vetorial Qdrant 
                onde os fragmentos de busca serão armazenados. O padrão é definido em config.py.
        """
        self.collection_name: str = collection_name
        self.vector_db: VectorDbManager = VectorDbManager()
        self.parent_store: ParentStoreManager = ParentStoreManager()
        self.chunker: DocumentChuncker = DocumentChuncker()
        self.agent_graph: Optional[Any] = None
        self.thread_id: str = str(uuid.uuid4())
        
    def initialize(self) -> None:
        """
        Constrói e compila o "cérebro" do assistente (LLM + Ferramentas + Grafo).

        Garante que a coleção vetorial exista, configura o modelo de linguagem principal 
        (Gemini Flash) com os parâmetros do sistema e compila a arquitetura de roteamento 
        e execução utilizando o LangGraph.

        Raises:
            ValueError: Se a variável de ambiente 'GOOGLE_API_KEY' não estiver configurada.
        """
        self.vector_db.create_collection(self.collection_name)
        collection = self.vector_db.get_collection(self.collection_name)
        
        # llm = ChatOllama(model=config.LLM_MODEL, temperature=config.LLM_TEMPERATURE)
        if "GOOGLE_API_KEY" not in os.environ:
            raise ValueError("⚠️ Defina export GOOGLE_API_KEY='sua-chave' no terminal!")
        
        llm = ChatGoogleGenerativeAI(model=config.LLM_MODEL, temperature=config.LLM_TEMPERATURE)
        tools = ToolFactory(collection).create_tools()
        self.agent_graph = create_agent_graph(llm, tools)
        
    def get_config(self) -> Dict[str, Dict[str, str]]:
        """
        Retorna a configuração de estado atual do agente.

        Necessário para que o LangGraph mantenha a memória da conversa (Thread)
        separada e contínua durante a sessão do usuário.

        Returns:
            Dict[str, Dict[str, str]]: Dicionário com o 'thread_id' configurável.
        """
        return {"configurable": {"thread_id": self.thread_id}}
    
    def reset_thread(self) -> None:
        """
        Apaga a memória de curto prazo (histórico da conversa) do agente.

        Gera um novo identificador único de sessão (UUID), permitindo que o 
        usuário inicie uma nova consulta (ex: botão "Limpar Conversa") 
        sem influência do contexto semântico anterior.
        """
        try:
            self.agent_graph.checkpointer.delete_thread(self.thread_id)
        except Exception as e:
            print(f"Warning: Could not delete thread {self.thread_id}: {e}")
        self.thread_id = str(uuid.uuid4())
