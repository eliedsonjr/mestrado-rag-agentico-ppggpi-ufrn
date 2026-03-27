import os
import glob
import json
import datetime
from typing import Any, List

import gradio as gr

import config
from core.chat_interface import ChatInterface
from core.document_manager import DocumentManager
from core.rag_system import RAGSystem

def registrar_log_cientifico(pergunta: str, resposta: str) -> None:
    """
    Grava os dados da interação em formato JSONL para análise metodológica.

    Garante a rastreabilidade (logs) do sistema, salvando a entrada do usuário
    e a saída gerada pela IA, juntamente com o timestamp. Os dados são
    utilizados para validação qualitativa e quantitativa da dissertação.

    Args:
        pergunta (str): A consulta original formulada pelo usuário.
        resposta (str): A resposta final gerada pelo sistema RAG.
    """
    os.makedirs(config.LOGS_DIR, exist_ok=True)
    arquivo_log = os.path.join(config.LOGS_DIR, "testes_dissertacao.jsonl")
    
    dados = {
        "timestamp": datetime.datetime.now().isoformat(),
        "input_usuario": pergunta,
        "output_sistema": resposta
    }
    
    # Salva silenciosamente no arquivo (modo 'a' para adicionar no final)
    with open(arquivo_log, "a", encoding="utf-8") as f:
        f.write(json.dumps(dados, ensure_ascii=False) + "\n")

def create_gradio_ui() -> gr.Blocks:
    """
    Constrói e inicializa a interface gráfica de usuário (GUI) utilizando Gradio.

    Esta função atua como o ponto de entrada da camada de Apresentação (Front-end).
    Ela instancia o 'cérebro' do sistema (RAGSystem), o gerenciador de documentos
    e a interface de chat. Além disso, define os componentes visuais, o tema
    institucional e os manipuladores de eventos (event handlers) para interação.

    Returns:
        gr.Blocks: O aplicativo Gradio configurado e pronto para ser executado.
    """
    # Inicialização do Cérebro (Core System)
    rag_system = RAGSystem()
    rag_system.initialize()
    
    doc_manager = DocumentManager(rag_system)
    chat_interface = ChatInterface(rag_system)
    
    # --- FUNÇÕES DE APOIO (EVENT HANDLERS) ---
    
    def sync_local_docs(progress: Any = gr.Progress()) -> str:
        """Sincroniza os PDFs da pasta local com o banco de dados vetorial."""
        if not os.path.exists(config.DOCS_DIR):
            os.makedirs(config.DOCS_DIR, exist_ok=True)
            return "Pasta 'docs' criada. Adicione PDFs lá."
            
        pdf_files = glob.glob(os.path.join(config.DOCS_DIR, "*.pdf"))
        if not pdf_files:
            return "Nenhum PDF encontrado na pasta 'docs'."
            
        added, skipped = doc_manager.add_documents(
            pdf_files, 
            progress_callback=lambda p, desc: progress(p, desc=desc) if progress else None
        )
        msg = f"✅ Sincronização: {added} novos indexados | {skipped} já existiam na base."
        print(msg)
        return msg

    print("🔄 Verificando novos documentos na pasta local...")
    sync_local_docs(progress=None)

    def format_file_list() -> str:
        """Formata a lista de arquivos disponíveis na base de conhecimento para exibição."""
        files = doc_manager.get_markdown_files()
        if not files:
            return "📭 Nenhum documento na base de conhecimento."
        return "\n".join([f"📄 {f}" for f in files])
        
    def clear_handler() -> str:
        """Apaga toda a base de conhecimento e retorna a lista vazia."""
        doc_manager.clear_all()
        gr.Info("🗑️ Todos os documentos foram apagados do banco de dados.")
        return format_file_list()
    
    def chat_handler(msg: str, hist: List[Any]) -> str:
        """
        Processa a mensagem do chat, invoca a IA e registra o log científico.
        """
        # 1. O sistema gera a resposta normalmente
        resposta_final = chat_interface.chat(msg, hist)
        
        # 2. Gravamos a interação nos bastidores (silenciosamente)
        try:
            registrar_log_cientifico(msg, resposta_final)
        except Exception as e:
            print(f"⚠️ Aviso: Falha ao gravar o log da dissertação: {e}")
            
        # 3. Devolvemos a resposta para o usuário ver na tela
        return resposta_final
    
    def clear_chat_handler() -> None:
        """Limpa o histórico da sessão de chat atual."""
        chat_interface.clear_session()
    
    # --- DEFINIÇÃO DO TEMA VISUAL (IDENTIDADE UFRN) ---
    tema_institucional = gr.themes.Soft(
        primary_hue="blue",      
        secondary_hue="indigo",  
        neutral_hue="slate",     
        font=[gr.themes.GoogleFont("Inter"), "sans-serif"]
    ).set(
        button_primary_background_fill="*primary_600",
        button_primary_background_fill_hover="*primary_700",
        block_title_text_weight="600",
        block_border_width="1px",
        block_shadow="none"
    )
    
    # --- CONSTRUÇÃO DA INTERFACE ---
    with gr.Blocks(title="Assistente CERES/UFRN", theme=tema_institucional) as demo:
        
        with gr.Row():
            with gr.Column(scale=8):
                gr.Markdown(
                    """
                    # 🏛️ Assistente Virtual de Processos - CERES/UFRN
                    **Plataforma de Suporte à Decisão Baseada em Inteligência Artificial Agêntica**
                    """
                )
            with gr.Column(scale=2):
                gr.Markdown("**Status:** 🟢 Online\n**Modelo:** Gemini 2.5 Flash")

        with gr.Tabs() as tabs:
            
            # ABA DO USUÁRIO FINAL
            with gr.Tab("💬 Consulta ao Assistente", id="chat-tab"):
                with gr.Row():
                    with gr.Column(scale=7):
                        chatbot = gr.Chatbot(
                            height=550, 
                            show_label=False,
                            placeholder="<strong>Olá! Sou o Assistente Virtual do CERES/UFRN.</strong><br>Estou lendo os documentos oficiais para ajudar. Pergunte sobre processos, resoluções ou calendários!"
                        )
                        chatbot.clear(clear_chat_handler)
                        
                        gr.ChatInterface(
                            fn=chat_handler, 
                            chatbot=chatbot
                        )
                    
                    with gr.Column(scale=3):
                        gr.Markdown("### 📚 Base de Conhecimento Ativa")
                        gr.Markdown("*(Documentos lidos automaticamente da pasta `docs`)*")
                        
                        file_list_display = gr.Markdown(format_file_list())
                        
                        with gr.Accordion("ℹ️ Orientações de Uso", open=True):
                            gr.Markdown(
                                """
                                - **Seja Específico:** Mencione o assunto ou o tipo de processo.
                                - **Checklist:** A IA indicará os documentos necessários para a secretaria.
                                - **Base Legal:** Verifique o PDF e o Artigo citados no final da resposta.
                                """
                            )

            # ABA DO ADMINISTRADOR
            with gr.Tab("⚙️ Gestão de Banco Vetorial (Admin)", id="doc-management-tab"):
                gr.Markdown("## 📥 Sincronização de Documentos")
                gr.Markdown("Para adicionar normas, coloque o PDF na pasta `docs` do servidor. O sistema fará a leitura automática ao iniciar. Caso o servidor já esteja ligado, clique no botão abaixo para forçar a leitura de novos arquivos.")
                
                sync_result = gr.Textbox(label="Status da Sincronização", interactive=False)
                sync_btn = gr.Button("🔄 Sincronizar Pasta Local 'docs'", variant="primary", size="md")
                
                gr.Markdown("## 📂 Acervo Atual no Qdrant")
                file_list = gr.Textbox(
                    value=format_file_list(),
                    interactive=False,
                    lines=7,
                    max_lines=10,
                    show_label=False
                )
                
                with gr.Row():
                    refresh_btn = gr.Button("🔄 Atualizar Visualização", size="md")
                    clear_btn = gr.Button("⚠️ Apagar Toda a Base (Requer Re-Sincronização)", variant="stop", size="md")
                
                sync_btn.click(
                    sync_local_docs, 
                    inputs=[], 
                    outputs=[sync_result]
                ).then(
                    format_file_list, None, file_list
                ).then(
                    format_file_list, None, file_list_display
                )
                
                refresh_btn.click(format_file_list, None, file_list)
                clear_btn.click(clear_handler, None, file_list).then(format_file_list, None, file_list_display)
    
    return demo
