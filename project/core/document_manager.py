from pathlib import Path
import shutil
from typing import List, Tuple, Union, Callable, Optional, Any
import config
from util import pdfs_to_markdowns

class DocumentManager:
    """
    Gerenciador de documentos para o sistema RAG do CERES/UFRN.

    Esta classe é responsável pelo pipeline de ingestão de documentos,
    o que inclui a conversão de PDFs para Markdown, a fragmentação
    (chunking) em nós pai/filho e a indexação no banco de dados vetorial.
    """

    def __init__(self, rag_system: Any) -> None:
        """
        Inicializa o gerenciador de documentos.

        Args:
            rag_system (Any): A instância principal do sistema RAG que contém
                as referências para o banco vetorial, armazenamento pai e chunker.
        """
        self.rag_system = rag_system
        self.markdown_dir = Path(config.MARKDOWN_DIR)
        self.markdown_dir.mkdir(parents=True, exist_ok=True)
        
    def add_documents(
        self, 
        document_paths: Union[str, List[str]], 
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> Tuple[int, int]:
        """
        Processa e indexa novos documentos no banco de dados vetorial.

        Lê os arquivos PDF ou Markdown, realiza o chunking semântico e salva 
        os fragmentos no Qdrant (filhos) e no sistema de arquivos local (pais).
        Documentos que já existam na base de conhecimento serão ignorados.

        Args:
            document_paths (Union[str, List[str]]): Caminho único (string) ou 
                lista de caminhos para os documentos a serem indexados.
            progress_callback (Optional[Callable[[float, str], None]], opcional):
                Função de callback para atualizar a interface gráfica (Gradio)
                sobre o progresso do processamento. O padrão é None.

        Returns:
            Tuple[int, int]: Uma tupla contendo:
                - (int): Número de documentos indexados com sucesso.
                - (int): Número de documentos ignorados (já existentes ou com erro).
        """
        if not document_paths:
            return 0, 0
            
        document_paths = [document_paths] if isinstance(document_paths, str) else document_paths
        document_paths = [p for p in document_paths if p and Path(p).suffix.lower() in [".pdf", ".md"]]
        
        if not document_paths:
            return 0, 0
            
        added = 0
        skipped = 0
            
        for i, doc_path in enumerate(document_paths):
            if progress_callback:
                progress_callback((i + 1) / len(document_paths), f"Processando {Path(doc_path).name}")
                
            doc_name = Path(doc_path).stem
            md_path = self.markdown_dir / f"{doc_name}.md"
            
            if md_path.exists():
                skipped += 1
                continue
                
            try:            
                if Path(doc_path).suffix.lower() == ".md":
                    shutil.copy(doc_path, md_path)
                else:
                    pdfs_to_markdowns(str(doc_path), overwrite=False)            
                parent_chunks, child_chunks = self.rag_system.chunker.create_chunks_single(md_path)
                
                if not child_chunks:
                    skipped += 1
                    continue
                
                collection = self.rag_system.vector_db.get_collection(self.rag_system.collection_name)
                collection.add_documents(child_chunks)
                self.rag_system.parent_store.save_many(parent_chunks)
                
                added += 1
                
            except Exception as e:
                print(f"Erro ao processar {doc_path}: {e}")
                skipped += 1
            
        return added, skipped
    
    def get_markdown_files(self) -> List[str]:
        """
        Lista os documentos processados e disponíveis na base de conhecimento.

        A função simula a extensão '.pdf' no retorno para manter a familiaridade
        visual na interface do usuário.

        Returns:
            List[str]: Lista ordenada contendo os nomes dos arquivos na base.
        """
        if not self.markdown_dir.exists():
            return []
        return sorted([p.name.replace(".md", ".pdf") for p in self.markdown_dir.glob("*.md")])
    
    def clear_all(self) -> None:
        """
        Apaga todos os documentos e reinicia completamente a base de conhecimento.

        Remove o diretório de markdowns em cache, limpa o armazenamento de
        fragmentos pai e recria a coleção vetorial no Qdrant a partir do zero.
        """
        if self.markdown_dir.exists():
            shutil.rmtree(self.markdown_dir)
            self.markdown_dir.mkdir(parents=True, exist_ok=True)
        
        self.rag_system.parent_store.clear_store()
        self.rag_system.vector_db.delete_collection(self.rag_system.collection_name)
        self.rag_system.vector_db.create_collection(self.rag_system.collection_name)
