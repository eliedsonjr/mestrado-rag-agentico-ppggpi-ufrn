import gradio as gr
from ui.css import custom_css
from ui.gradio_app import create_gradio_ui

def main() -> None:
    """
    Ponto de entrada principal da aplicação (Entry Point).
    
    Inicializa a interface gráfica do Gradio, aplica as folhas de estilo 
    personalizadas (CSS institucional do CERES/UFRN) e lança o servidor local 
    para interação do usuário com o agente RAG.
    """
    demo = create_gradio_ui()
    print("\n🚀 Iniciando o Assistente RAG do CERES/UFRN...")
    demo.launch(css=custom_css)

if __name__ == "__main__":
    main()
