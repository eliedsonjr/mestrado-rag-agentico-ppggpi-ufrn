import os
from typing import List, Any
from langchain_core.tools import tool
import config
from db.parent_store_manager import ParentStoreManager

class ToolFactory:
    """
    Fábrica de Ferramentas (Tools) para o Agente RAG.
    
    Fornece as capacidades de percepção ao agente, permitindo que ele pesquise 
    no banco de dados vetorial e acesse o sistema de arquivos local. Utiliza 
    a arquitetura de recuperação Small-to-Big (Parent-Child Chunking).
    """
    
    def __init__(self, collection: Any) -> None:
        """
        Inicializa a fábrica com acesso às bases de conhecimento.

        Args:
            collection (Any): A coleção ativa no banco de dados vetorial Qdrant 
                              (usada para busca semântica em fragmentos pequenos).
        """
        self.collection = collection
        self.parent_store_manager: ParentStoreManager = ParentStoreManager()
    
    def _search_child_chunks(self, query: str, limit: int) -> str:
        """
        Pesquisa no banco vetorial pelos fragmentos "filhos" mais relevantes.
        
        Realiza uma busca por similaridade semântica para encontrar blocos pequenos
        de texto (alta precisão). Retorna o texto e o ID do seu respectivo "pai".
        
        Args:
            query (str): A string de busca formulada pelo LLM.
            limit (int): O número máximo de fragmentos a retornar (Top K).
            
        Returns:
            str: O conteúdo dos fragmentos formatado com metadados, ou mensagem de erro.
        """
        try:
            results = self.collection.similarity_search(query, k=limit, score_threshold=0.7)
            if not results:
                return "NO_RELEVANT_CHUNKS"

            return "\n\n".join([
                f"Parent ID: {doc.metadata.get('parent_id', '')}\n"
                f"File Name: {doc.metadata.get('source', '')}\n"
                f"Content: {doc.page_content.strip()}"
                for doc in results
            ])            

        except Exception as e:
            return f"RETRIEVAL_ERROR: {str(e)}"
    
    def _retrieve_many_parent_chunks(self, parent_ids: List[str]) -> str:
        """
        Recupera múltiplos fragmentos "pai" baseados em seus identificadores únicos.
        
        Expande o contexto de múltiplos resultados da busca vetorial simultaneamente,
        buscando os blocos originais completos no armazenamento local de arquivos JSON.
        
        Args:
            parent_ids (List[str]): Lista contendo os identificadores dos nós pai.
            
        Returns:
            str: O conteúdo expandido dos pais com seus metadados.
        """
        try:
            ids = [parent_ids] if isinstance(parent_ids, str) else list(parent_ids)
            raw_parents = self.parent_store_manager.load_content_many(ids)
            if not raw_parents:
                return "NO_PARENT_DOCUMENTS"

            return "\n\n".join([
                f"Parent ID: {doc.get('parent_id', 'n/a')}\n"
                f"File Name: {doc.get('metadata', {}).get('source', 'unknown')}\n"
                f"Content: {doc.get('content', '').strip()}"
                for doc in raw_parents
            ])            

        except Exception as e:
            return f"PARENT_RETRIEVAL_ERROR: {str(e)}"
    
    def _retrieve_parent_chunks(self, parent_id: str) -> str:
        """
        Recupera o contexto completo (Pai) a partir de um fragmento específico.
        
        Etapa crucial da técnica 'Small-to-Big Retrieval'. O LLM usa esta ferramenta 
        quando nota que um fragmento filho promissor está com o contexto cortado, 
        puxando a página/seção inteira para garantir uma resposta livre de alucinações.
        
        Args:
            parent_id (str): O identificador exato do documento pai.
            
        Returns:
            str: O texto completo do documento âncora associado.
        """
        try:
            parent = self.parent_store_manager.load_content(parent_id)
            if not parent:
                return "NO_PARENT_DOCUMENT"

            return (
                f"Parent ID: {parent.get('parent_id', 'n/a')}\n"
                f"File Name: {parent.get('metadata', {}).get('source', 'unknown')}\n"
                f"Content: {parent.get('content', '').strip()}"
            )          

        except Exception as e:
            return f"PARENT_RETRIEVAL_ERROR: {str(e)}"

    def _list_available_documents(self) -> str:
        """
        Lista todos os documentos oficiais que compõem a base de conhecimento atual.
        
        Permite ao agente ter consciência de domínio (saber o que ele sabe). 
        Utilizado para responder meta-perguntas do usuário, como "Quais manuais 
        você tem disponíveis para leitura?".
        
        Returns:
            str: Lista formatada com os nomes dos arquivos lidos (extensão .pdf).
        """
        try:
            if not os.path.exists(config.MARKDOWN_DIR):
                return "A base de conhecimento está vazia no momento."
            
            files = [f.replace('.md', '.pdf') for f in os.listdir(config.MARKDOWN_DIR) if f.endswith('.md')]
            if not files:
                return "A base de conhecimento está vazia no momento."
            
            lista = "\n".join([f"- {f}" for f in files])
            return f"Atualmente, tenho acesso aos seguintes documentos oficiais do CERES/UFRN:\n\n{lista}"
        except Exception as e:
            return f"Erro ao acessar base de documentos: {str(e)}"
    
    def create_tools(self) -> List[Any]:
        """
        Compila as funções da classe no formato exigido pelo framework LangChain.

        Returns:
            List[Any]: Lista de ferramentas formatadas (@tool) injetáveis no Agente LLM.
        """
        search_tool = tool("search_child_chunks")(self._search_child_chunks)
        retrieve_tool = tool("retrieve_parent_chunks")(self._retrieve_parent_chunks)
        list_tool = tool("list_available_documents")(self._list_available_documents)
        
        return [search_tool, retrieve_tool, list_tool]
