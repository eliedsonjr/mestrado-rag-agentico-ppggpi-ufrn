from typing import Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage, RemoveMessage, AIMessage
from .graph_state import State, AgentState
from .schemas import QueryAnalysis
from .prompts import (
    get_conversation_summary_prompt,
    get_query_analysis_prompt,
    get_rag_agent_prompt,
    get_aggregation_prompt
)

def analyze_chat_and_summarize(state: State, llm: Any) -> Dict[str, Any]:
    """
    Analisa o histórico recente do chat e gera um resumo contextual.

    Esta etapa atua como a memória de curto prazo do agente. Condensa as interações
    anteriores para manter o contexto semântico sem estourar a janela de contexto
    (token limit) do modelo de linguagem.

    Args:
        state (State): O estado atual do grafo global.
        llm (Any): Instância do modelo de linguagem configurado (ex: Gemini).

    Returns:
        Dict[str, Any]: Atualização do estado contendo o resumo da conversa e 
                        o sinalizador para resetar o array de respostas anteriores.
    """
    if len(state["messages"]) < 4:
        return {"conversation_summary": ""}
    
    relevant_msgs = [
        msg for msg in state["messages"][:-1]
        if isinstance(msg, (HumanMessage, AIMessage))
        and not getattr(msg, "tool_calls", None)
    ]

    if not relevant_msgs:
        return {"conversation_summary": ""}
    
    conversation = "Conversation history:\n"
    for msg in relevant_msgs[-6:]:
        role = "User" if isinstance(msg, HumanMessage) else "Assistant"
        conversation += f"{role}: {msg.content}\n"

    summary_response = llm.with_config(temperature=0.2).invoke(
        [SystemMessage(content=get_conversation_summary_prompt())] + 
        [HumanMessage(content=conversation)]
    )
    return {"conversation_summary": summary_response.content, "agent_answers": [{"__reset__": True}]}

def analyze_and_rewrite_query(state: State, llm: Any) -> Dict[str, Any]:
    """
    Analisa a intenção do usuário e reescreve a consulta para otimização de busca.

    Utiliza o LLM com saída estruturada (Structured Output - JSON) para classificar 
    a pergunta, pedir esclarecimentos (se ambígua) ou dividi-la em sub-consultas 
    autossuficientes para processamento paralelo (Fan-out).

    Args:
        state (State): O estado atual do grafo global.
        llm (Any): Instância do modelo de linguagem.

    Returns:
        Dict[str, Any]: Atualização do estado com o status de clareza, a consulta original 
                        e a lista de perguntas reescritas prontas para a recuperação vetorial.
    """
    last_message = state["messages"][-1]
    conversation_summary = state.get("conversation_summary", "")

    context_section = (f"Conversation Context:\n{conversation_summary}\n" if conversation_summary.strip() else "") + f"User Query:\n{last_message.content}\n"

    llm_with_structure = llm.with_config(temperature=0.1).with_structured_output(QueryAnalysis)
    response = llm_with_structure.invoke(
        [SystemMessage(content=get_query_analysis_prompt())] + 
        [HumanMessage(content=context_section)]
    )

    if len(response.questions) > 0 and response.is_clear:
        delete_all = [
            RemoveMessage(id=m.id)
            for m in state["messages"]
            if not isinstance(m, SystemMessage)
        ]
        return {
            "questionIsClear": True,
            "messages": delete_all,
            "originalQuery": last_message.content,
            "rewrittenQuestions": response.questions
        }
    else:
        clarification = response.clarification_needed if (response.clarification_needed and len(response.clarification_needed.strip()) > 10) else "I need more information to understand your question."
        return {
            "questionIsClear": False,
            "messages": [AIMessage(content=clarification)]
        }

def human_input_node(state: State) -> Dict[str, Any]:
    """
    Nó de interrupção para aguardar o input (Human-in-the-Loop).

    É ativado pelo orquestrador quando a intenção do usuário não é clara 
    e o sistema precisa de mais informações antes de prosseguir com a pesquisa.
    """
    return {}

def agent_node(state: AgentState, llm_with_tools: Any) -> Dict[str, Any]:
    """
    Nó executor do sub-agente RAG (Retrieval-Augmented Generation).

    Invoca o LLM equipado com ferramentas de busca. O modelo decide autonomamente 
    quais documentos pesquisar e formula uma resposta preliminar baseada estritamente 
    nas evidências recuperadas.

    Args:
        state (AgentState): Estado local (isolado) contendo a sub-consulta.
        llm_with_tools (Any): LLM com acesso às ferramentas definidas no ToolFactory.

    Returns:
        Dict[str, Any]: O histórico de mensagens atualizado com a chamada da ferramenta 
                        ou a resposta final do sub-agente.
    """
    sys_msg = SystemMessage(content=get_rag_agent_prompt())    
    if not state.get("messages"):
        human_msg = HumanMessage(content=state["question"])
        response = llm_with_tools.invoke([sys_msg] + [human_msg])
        return {"messages": [human_msg, response]}
    
    return {"messages": [llm_with_tools.invoke([sys_msg] + state["messages"])]}

def extract_final_answer(state: AgentState) -> Dict[str, Any]:
    """
    Extrai a resposta final gerada pelo sub-agente RAG.

    Percorre o histórico do sub-grafo para encontrar a última mensagem da IA 
    que não seja uma chamada de ferramenta, preparando-a para agregação.

    Returns:
        Dict[str, Any]: A resposta extraída e envelopada com seu índice original.
    """
    for msg in reversed(state["messages"]):
        if isinstance(msg, AIMessage) and msg.content and not msg.tool_calls:
            res = {
                "final_answer": msg.content,
                "agent_answers": [{
                    "index": state["question_index"],
                    "question": state["question"],
                    "answer": msg.content
                }]
            }
            return res
    return {
        "final_answer": "Não foi possível gerar uma resposta baseada nos documentos.",
        "agent_answers": [{
            "index": state["question_index"],
            "question": state["question"],
            "answer": "Não foi possível gerar uma resposta baseada nos documentos."
        }]
    }

def aggregate_responses(state: State, llm: Any) -> Dict[str, Any]:
    """
    Sintetiza as múltiplas respostas dos sub-agentes em uma resposta final unificada.

    Nó final do padrão Map-Reduce. Pega em todas as conclusões das pesquisas 
    paralelas, ordena-as e utiliza o LLM para redigir a resposta oficial e coesa 
    para o usuário, aplicando as regras de citação institucional do CERES.

    Args:
        state (State): O estado global contendo todas as respostas acumuladas.
        llm (Any): Instância do modelo de linguagem.

    Returns:
        Dict[str, Any]: A resposta final e consolidada a ser exibida na interface.
    """
    if not state.get("agent_answers"):
        return {"messages": [AIMessage(content="Nenhuma resposta pôde ser gerada com os documentos atuais.")]}

    sorted_answers = sorted(state["agent_answers"], key=lambda x: x["index"])

    formatted_answers = ""
    for i, ans in enumerate(sorted_answers, start=1):
        formatted_answers += (f"\nAnswer {i}:\n"f"{ans['answer']}\n")

    user_message = HumanMessage(content=f"""Original user question: {state["originalQuery"]}\nRetrieved answers:{formatted_answers}""")
    synthesis_response = llm.invoke([SystemMessage(content=get_aggregation_prompt())] + [user_message])
    
    return {"messages": [AIMessage(content=synthesis_response.content)]}
