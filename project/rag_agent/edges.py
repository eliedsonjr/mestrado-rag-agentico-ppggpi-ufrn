from typing import Literal, List, Union
from langgraph.types import Send
from .graph_state import State

def route_after_rewrite(state: State) -> Union[Literal["human_input"], List[Send]]:
    """
    Roteador condicional do grafo cognitivo (Arquitetura Map-Reduce).

    Avalia o estado da análise da consulta do usuário. Se a pergunta for ambígua,
    desvia o fluxo para solicitar intervenção humana (Human-in-the-Loop). 
    Se a pergunta for clara e tiver sido reescrita, aplica o padrão de roteamento 
    'Fan-out', criando e despachando sub-processos paralelos para cada sub-consulta.

    Args:
        state (State): O estado global do orquestrador após a reescrita da consulta.

    Returns:
        Union[Literal["human_input"], List[Send]]: 
            - O nome do próximo nó ("human_input") para interromper o fluxo.
            - Uma lista de objetos `Send`, que instruem o framework a instanciar 
              múltiplos sub-agentes ("process_question") com estados isolados.
    """
    if not state.get("questionIsClear", False):
        return "human_input"
    else:
        # Padrão Fan-out: Envia cada pergunta reescrita para um sub-agente RAG independente
        return [
                Send("process_question", {"question": query, "question_index": idx, "messages": []})
                for idx, query in enumerate(state["rewrittenQuestions"])
            ]
