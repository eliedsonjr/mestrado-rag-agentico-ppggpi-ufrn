from typing import Any, List
from langgraph.graph import START, END, StateGraph
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import ToolNode, tools_condition
from functools import partial

from .graph_state import State, AgentState
from .nodes import (
    analyze_chat_and_summarize, 
    analyze_and_rewrite_query, 
    human_input_node, 
    agent_node, 
    extract_final_answer, 
    aggregate_responses
)
from .edges import route_after_rewrite

def create_agent_graph(llm: Any, tools_list: List[Any]) -> Any:
    """
    Constrói, configura e compila o Grafo de Estados do Agente RAG.

    Implementa uma arquitetura multi-nível utilizando LangGraph:
    1. Sub-Grafo (AgentState): Um agente cíclico ('ReAct' pattern) focado estritamente
       em utilizar ferramentas de busca (tools) para responder a uma sub-consulta.
    2. Grafo Principal (State): Orquestra o fluxo de alto nível, desde a sumarização
       do contexto, reescrita da consulta, despacho paralelo (fan-out) para os 
       sub-grafos, até a agregação final (Map-Reduce).

    Args:
        llm (Any): A instância do modelo de linguagem primário (ex: Gemini) 
                   que será o "motor" de raciocínio de todos os nós.
        tools_list (List[Any]): Lista de ferramentas (tools) fornecidas pelo ToolFactory, 
                                permitindo as operações de recuperação no Qdrant.

    Returns:
        Any: O grafo compilado (CompiledGraph) pronto para invocação pela interface, 
             equipado com memória de curto prazo (InMemorySaver).
    """
    llm_with_tools = llm.bind_tools(tools_list)
    tool_node = ToolNode(tools_list)

    # Inicializa o checkpointer para manter a memória (Thread) da sessão
    checkpointer = InMemorySaver()

    print("🔧 Compilando a arquitetura do Grafo Agêntico...")
    
    # --- CONSTRUÇÃO DO SUB-GRAFO (Agente de Pesquisa Isolada) ---
    agent_builder = StateGraph(AgentState)
    agent_builder.add_node("agent", partial(agent_node, llm_with_tools=llm_with_tools))
    agent_builder.add_node("tools", tool_node)
    agent_builder.add_node("extract_answer", extract_final_answer)
    
    # Fluxo do Sub-Grafo (Padrão ReAct)
    agent_builder.add_edge(START, "agent")    
    agent_builder.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: "extract_answer"})
    agent_builder.add_edge("tools", "agent")    
    agent_builder.add_edge("extract_answer", END)
    
    agent_subgraph = agent_builder.compile()
    
    # --- CONSTRUÇÃO DO GRAFO PRINCIPAL (Orquestrador) ---
    graph_builder = StateGraph(State)
    graph_builder.add_node("summarize", partial(analyze_chat_and_summarize, llm=llm))
    graph_builder.add_node("analyze_rewrite", partial(analyze_and_rewrite_query, llm=llm))
    graph_builder.add_node("human_input", human_input_node)
    
    # O nó de processamento invoca o Sub-Grafo compilado acima
    graph_builder.add_node("process_question", agent_subgraph)
    graph_builder.add_node("aggregate", partial(aggregate_responses, llm=llm))
    
    # Fluxo do Grafo Principal (Pipeline Map-Reduce)
    graph_builder.add_edge(START, "summarize")
    graph_builder.add_edge("summarize", "analyze_rewrite")
    graph_builder.add_conditional_edges("analyze_rewrite", route_after_rewrite)
    graph_builder.add_edge("human_input", "analyze_rewrite")
    graph_builder.add_edge(["process_question"], "aggregate")
    graph_builder.add_edge("aggregate", END)

    # Compila o grafo final injetando o Checkpointer e configurando o ponto de interrupção
    agent_graph = graph_builder.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_input"]
    )

    print("✓ Grafo do Agente compilado com sucesso.")
    return agent_graph
