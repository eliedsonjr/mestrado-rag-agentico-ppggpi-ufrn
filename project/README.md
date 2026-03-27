```markdown
# 🏛️ Assistente Virtual RAG Agêntico - CERES/UFRN

Um sistema de **Retrieval-Augmented Generation (RAG) Agêntico** construído com **LangGraph**, projetado para mitigar a fragmentação informacional e otimizar o fluxo de trabalho dos Técnicos-Administrativos (TAEs) e alunos do CERES/UFRN.

A arquitetura apresenta **fragmentação hierárquica (parent-child chunking)**, **recuperação híbrida (densa + esparsa)** e suporte para modelos de linguagem avançados (focado nativamente no Google Gemini 2.5 Flash).

## 📑 Índice

[Início Rápido](#-início-rápido) | [Visão Geral da Arquitetura](#-visão-geral-da-arquitetura) | [Estrutura do Projeto](#-estrutura-do-projeto) | [Guia de Configuração](#-guia-de-configuração) | [Rastreabilidade Científica](#-rastreabilidade-científica-jsonl) | [Como Citar](#-como-citar-este-trabalho)

---

## 🚀 Início Rápido

### Instalação

Instale todas as dependências necessárias através do arquivo de requisitos:

```bash
pip install -r requirements.txt
```

### Variáveis de Ambiente

O sistema utiliza o Google Gemini como motor cognitivo principal. Exporte sua chave de API no terminal ou crie um arquivo `.env`:

```bash
export GOOGLE_API_KEY="sua-chave-api-aqui"
```

### Executando a Aplicação

Inicie a interface Gradio localmente:

```bash
python app.py
```

A aplicação estará disponível em `http://localhost:7860` (porta padrão do Gradio).

---

## 🧠 Visão Geral da Arquitetura

Este sistema implementa um pipeline RAG avançado com os seguintes recursos principais:

- **Segmentação Hierárquica (Parent-Child Chunking):** Os documentos são divididos em fragmentos filhos pequenos (para recuperação precisa) vinculados a fragmentos pais maiores (para contexto rico).
- **Busca Híbrida (Hybrid Search):** Combina embeddings densos (semântica) e recuperação esparsa BM25 (léxica) para resultados ótimos no domínio jurídico/acadêmico.
- **Agente LangGraph:** Orquestra a reescrita de consultas, a recuperação paralela (Padrão Fan-out) e a geração da resposta estruturada.
- **Armazenamento Vetorial:** Utiliza o Qdrant para busca de similaridade eficiente.
- **Aterramento Visível (Explainable AI):** Respostas geram checklists obrigatórios e exibem citações diretas (Artigos e Links) da base legal do CERES/UFRN.

### Fluxo de Dados (Data Flow)

```text
PDF Institucional → Conversão Markdown → Parent/Child Chunking → Indexação Vetorial → Recuperação Agêntica → Resposta LLM
```

---

## 📂 Estrutura do Projeto

### Ponto de Entrada & Configuração

| Arquivo | Propósito |
|------|---------|
| `app.py` | Ponto de entrada da aplicação, inicia a interface Gradio. |
| `config.py` | **Central de configuração (SSOT)** - edite para mudar parâmetros de chunking ou modelos. |
| `util.py` | Conversão de PDF para Markdown utilizando `pymupdf4llm`. |
| `document_chunker.py` | Lógica de divisão hierárquica (pai/filho) com regras de limpeza e mesclagem. |

### Sistema Central (Core)

| Arquivo | Propósito |
|------|---------|
| `core/rag_system.py` | Inicializador do sistema - cria os gerenciadores e compila o agente LangGraph. |
| `core/document_manager.py` | Pipeline de ingestão de documentos (conversão, fragmentação, indexação). |
| `core/chat_interface.py` | Camada de abstração para interação com o grafo do agente. |

### Camada de Banco de Dados

| Arquivo | Propósito |
|------|---------|
| `db/vector_db_manager.py` | Wrapper do cliente Qdrant com inicialização de embeddings (Híbrido). |
| `db/parent_store_manager.py` | Armazenamento local em JSON para os fragmentos pais. |

### Agente RAG (LangGraph)

| Arquivo | Propósito |
|------|---------|
| `rag_agent/graph.py` | Lógica de construção e compilação do grafo (Map-Reduce). |
| `rag_agent/graph_state.py` | Definições de estado global e local do grafo e lógica de acúmulo de respostas. |
| `rag_agent/nodes.py` | Implementações dos nós (sumarizar, reescrever, execução do agente, agregar). |
| `rag_agent/edges.py` | Lógica de roteamento condicional (baseada na clareza da consulta). |
| `rag_agent/tools.py` | Ferramentas de recuperação ativadas via ReAct (`search_child_chunks`, `retrieve_parent_chunks`). |
| `rag_agent/prompts.py` | Engenharia de prompts do sistema (incluindo o dicionário estático de links institucionais). |
| `rag_agent/schemas.py` | Esquemas de saída estruturada (modelos Pydantic para roteamento JSON). |

### Interface de Usuário (Gradio)

| Arquivo | Propósito |
|------|---------|
| `ui/css.py` | Estilização CSS customizada (Identidade visual CERES/UFRN). |
| `ui/gradio_app.py` | Implementação da UI Gradio com abas de chat e gestão de documentos. |

---

## ⚙️ Guia de Configuração

Todas as configurações primárias estão em `config.py`. Parâmetros principais:

### Configuração de Diretórios

```python
MARKDOWN_DIR = "markdown_docs"        # Armazenamento para arquivos PDF → Markdown convertidos
PARENT_STORE_PATH = "parent_store"    # Armazenamento local para fragmentos pais
QDRANT_DB_PATH = "qdrant_db"          # Caminho local do banco de dados vetorial Qdrant
DOCS_DIR = "docs"                     # Pasta de entrada para os PDFs institucionais brutos
LOGS_DIR = "logs"                     # Armazenamento de telemetria científica (JSONL)
```

### Configuração do Splitter de Texto

```python
CHILD_CHUNK_SIZE = 500              # Tamanho dos fragmentos usados para recuperação
CHILD_CHUNK_OVERLAP = 100           # Sobreposição entre fragmentos (evita perda de contexto)
MIN_PARENT_SIZE = 2000              # Tamanho mínimo do fragmento pai
MAX_PARENT_SIZE = 10000             # Tamanho máximo do fragmento pai
```

---

## 📊 Rastreabilidade Científica (JSONL)

Diferente de sistemas corporativos comuns, este artefato possui um módulo de coleta empírica voltado para a **Design Science Research (DSR)**.

Todas as interações realizadas na aba "Consulta ao Assistente" são anonimizadas e gravadas automaticamente no arquivo `logs/testes_dissertacao.jsonl`. O log inclui:

- `timestamp` (Formato ISO)
- `input_usuario` (A dúvida exata do TAE/Aluno)
- `output_sistema` (A resposta completa gerada pela IA, incluindo os metadados da Base Legal)

Estes dados são utilizados exclusivamente para extração de métricas de acurácia e avaliação qualitativa na fase de resultados da pesquisa.

---

## 🎓 Como Citar Este Trabalho

Este software foi desenvolvido como parte da dissertação de mestrado no Programa de Gestão de Processos do CERES/UFRN. Se você utilizar este código ou arquitetura em sua pesquisa, por favor, cite da seguinte forma:

**ABNT:**
> SEU SOBRENOME, Seu Nome. *Título da sua Dissertação*. 2026. Dissertação (Mestrado) - Centro de Ensino Superior do Seridó (CERES), Universidade Federal do Rio Grande do Norte (UFRN), Caicó, 2026.

**BibTeX:**
```bibtex
@mastersthesis{SeuSobrenome2026,
  author       = {Seu Nome e Sobrenome},
  title        = {O Título Completo da sua Dissertação},
  school       = {Universidade Federal do Rio Grande do Norte (CERES/UFRN)},
  year         = {2026},
  type         = {Dissertação de Mestrado}
}
```
```