from typing import List, Dict, Any, Annotated
from langgraph.graph import MessagesState

def accumulate_or_reset(existing: List[Dict[str, Any]], new: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Função redutora (reducer) para gerenciar o acúmulo de respostas.

    No padrão Map-Reduce de grafos cognitivos, esta função decide como mesclar
    as respostas geradas pelos sub-agentes paralelos de volta ao estado global.
    Se receber um sinalizador de reset, limpa a lista para iniciar um novo ciclo.

    Args:
        existing (List[Dict[str, Any]]): A lista atual de respostas no estado do grafo.
        new (List[Dict[str, Any]]): A nova resposta a ser anexada ou o sinal de reset.

    Returns:
        List[Dict[str, Any]]: A lista atualizada de respostas do agente.
    """
    if new and any(item.get('__reset__') for item in new):
        return []
    return existing + new

class State(MessagesState):
    """
    Estado global do Grafo Orquestrador (Memória de Trabalho Principal).
    
    Mantém o contexto de alto nível da sessão do usuário, como o resumo da conversa,
    a avaliação de clareza da pergunta e o controle das consultas reescritas
    que serão enviadas em paralelo (Fan-out) para os sub-agentes de pesquisa.
    """
    questionIsClear: bool = False
    conversation_summary: str = ""
    originalQuery: str = "" 
    rewrittenQuestions: List[str] = []
    agent_answers: Annotated[List[Dict[str, Any]], accumulate_or_reset] = []

class AgentState(MessagesState):
    """
    Estado local do Subgrafo do Agente (Memória de Trabalho Específica).
    
    Utilizado quando uma pergunta complexa é dividida em várias. Cada sub-agente 
    recebe uma cópia isolada deste estado para realizar suas buscas no Qdrant 
    sem interferir ou sobrescrever as outras pesquisas em andamento.
    """
    question: str = ""
    question_index: int = 0
    final_answer: str = ""
    agent_answers: List[Dict[str, Any]] = []
