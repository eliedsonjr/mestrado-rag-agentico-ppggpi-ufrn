from typing import List, Tuple, Any, Optional
from langchain_core.messages import HumanMessage

class ChatInterface:
    """
    Interface de comunicação entre o usuário e o sistema RAG Agêntico do CERES.
    
    Atua como uma camada de abstração (wrapper) que recebe as mensagens da 
    interface gráfica (Gradio), encapsula no formato esperado pelo LangGraph 
    (HumanMessage) e processa a invocação do grafo cognitivo.
    """
    
    def __init__(self, rag_system: Any) -> None:
        """
        Inicializa a interface de chat vinculada ao orquestrador RAG central.

        Args:
            rag_system (Any): Instância inicializada da classe RAGSystem, contendo 
                o grafo do agente e as configurações de sessão (Thread ID).
        """
        self.rag_system = rag_system
        
    def chat(self, message: str, history: Optional[List[Tuple[str, str]]] = None) -> str:
        """
        Processa uma nova mensagem do usuário e retorna a resposta gerada pelo agente.

        Verifica o status de inicialização do sistema, invoca o grafo do agente 
        com a nova pergunta e gerencia possíveis exceções de rede ou limite de tokens 
        durante a execução do modelo de linguagem.

        Args:
            message (str): A pergunta ou instrução em linguagem natural enviada pelo usuário.
            history (Optional[List[Tuple[str, str]]], opcional): Histórico da conversa 
                enviado automaticamente pela interface gráfica do Gradio. O padrão é None.

        Returns:
            str: A resposta final gerada pelo assistente após o fluxo de recuperação de
                 documentos, ou uma string formatada contendo a mensagem de erro.
        """
        if not self.rag_system.agent_graph:
            return "⚠️ Sistema não inicializado corretamente!"
            
        try:
            # Invoca o LangGraph passando a mensagem formatada e a configuração da Thread
            result = self.rag_system.agent_graph.invoke(
                {"messages": [HumanMessage(content=message.strip())]},
                self.rag_system.get_config()
            )
            return result["messages"][-1].content
            
        except Exception as e:
            return f"❌ Erro durante o processamento da resposta: {str(e)}"
    
    def clear_session(self) -> None:
        """
        Limpa o contexto da conversa atual.

        Aciona o método de reset no sistema RAG para gerar um novo identificador 
        de sessão (thread_id), garantindo que as próximas interações do usuário 
        comecem "do zero", sem influência (alucinação) do histórico anterior.
        """
        self.rag_system.reset_thread()
