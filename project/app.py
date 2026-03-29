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
    
    # --- DEFINIÇÃO DO TEMA VISUAL (IDENTIDADE UFRN) ---
    '''tema_institucional = gr.themes.Soft(
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
    )'''
    
    '''tema_institucional = gr.themes.Soft(
        primary_hue="blue",      
        secondary_hue="indigo",  
        neutral_hue="slate",     
        font=[gr.themes.GoogleFont("Inter"), "sans-serif"]
    )'''
    tema_institucional = gr.themes.Ocean(
        primary_hue="blue",
        secondary_hue="cyan",
        neutral_hue="slate",
        font=[gr.themes.GoogleFont("Roboto"), "sans-serif"]
    )
    
    print("\n🚀 Iniciando o Assistente RAG do CERES/UFRN...")
    
    demo.launch( 
        css=custom_css,
        theme=tema_institucional
    )

if __name__ == "__main__":
    main()
