custom_css = """
    /* ============================================
       DESIGN INSTITUCIONAL - CERES/UFRN
       ============================================ */
       
    /* 1. Esconde o rodapé padrão do Gradio para um visual "White-Label" mais oficial */
    footer {
        display: none !important;
        visibility: hidden !important;
    }

    /* 2. Limita a largura da tela para leitura confortável (Evita linhas de texto muito longas) */
    .gradio-container {
        max-width: 95% !important;
        margin: auto !important;
        font-family: 'Inter', system-ui, sans-serif !important;
    }

    /* 3. Estilização amigável das bolhas de Chat */
    .message.user {
        border-radius: 16px 16px 0 16px !important;
    }
    
    .message.bot {
        border-radius: 16px 16px 16px 0 !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
    }
    
    /* Remove sombras exageradas do projeto original */
    * {
        box-shadow: none;
    }
"""
