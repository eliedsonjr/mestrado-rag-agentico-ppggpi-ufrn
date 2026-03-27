from typing import List
from pydantic import BaseModel, Field

class QueryAnalysis(BaseModel):
    """
    Esquema de dados (Schema) estruturado para a análise de intenção do usuário.
    
    Garante que o modelo de linguagem (LLM) retorne a análise inicial 
    em um formato previsível (JSON) durante o nó de reescrita de consultas. 
    Isso é vital para o roteamento determinístico dentro do grafo.
    """
    is_clear: bool = Field(
        description="Booleano que indica se a pergunta do usuário é clara, autossuficiente e passível de pesquisa."
    )
    questions: List[str] = Field(
        description="Lista de perguntas reescritas e limpas, otimizadas para busca semântica no banco vetorial."
    )
    clarification_needed: str = Field(
        description="Explicação gerada pelo LLM ou pedido de contexto adicional caso a pergunta original seja ambígua."
    )
