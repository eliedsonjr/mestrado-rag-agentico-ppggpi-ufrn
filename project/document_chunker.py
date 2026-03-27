import os
import glob
from pathlib import Path
from typing import List, Tuple, Any

import config
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

class DocumentChuncker:
    """
    Processador de Fragmentação de Documentos (Document Chunker).

    Implementa a lógica central de preparação de dados. Utiliza uma estratégia 
    hierárquica (Parent-Child) onde o documento é primeiro dividido semanticamente 
    por cabeçalhos Markdown (Pais) e depois subdividido em blocos menores de tamanho 
    fixo (Filhos) para aumentar a precisão da busca vetorial (Retrieval).
    """

    def __init__(self) -> None:
        """Inicializa os algoritmos de divisão de texto com os parâmetros do config."""
        self.__parent_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=config.HEADERS_TO_SPLIT_ON, 
            strip_headers=False
        )
        self.__child_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.CHILD_CHUNK_SIZE, 
            chunk_overlap=config.CHILD_CHUNK_OVERLAP
        )
        self.__min_parent_size = config.MIN_PARENT_SIZE
        self.__max_parent_size = config.MAX_PARENT_SIZE

    def create_chunks(self, path_dir: str = config.MARKDOWN_DIR) -> Tuple[List[Any], List[Any]]:
        """
        Processa todos os arquivos Markdown de um diretório em lote.

        Args:
            path_dir (str, opcional): Caminho do diretório contendo os arquivos .md.

        Returns:
            Tuple[List[Any], List[Any]]: Tupla contendo a lista consolidada de 
                                         todos os fragmentos pai e fragmentos filho.
        """
        all_parent_chunks: List[Any] = []
        all_child_chunks: List[Any] = []

        for doc_path_str in sorted(glob.glob(os.path.join(path_dir, "*.md"))):
            doc_path = Path(doc_path_str)
            parent_chunks, child_chunks = self.create_chunks_single(doc_path)
            all_parent_chunks.extend(parent_chunks)
            all_child_chunks.extend(child_chunks)
        
        return all_parent_chunks, all_child_chunks

    def create_chunks_single(self, md_path: Path) -> Tuple[List[Any], List[Any]]:
        """
        Processa um único arquivo Markdown aplicando regras estritas de limpeza e fusão.

        Executa o pipeline completo: quebra por cabeçalhos, mescla pais muito pequenos 
        (para preservar contexto), divide pais muito grandes e gera os filhos recursivamente.
        """
        doc_path = Path(md_path)
        
        with open(doc_path, "r", encoding="utf-8") as f:
            parent_chunks = self.__parent_splitter.split_text(f.read())
        
        merged_parents = self.__merge_small_parents(parent_chunks)
        split_parents = self.__split_large_parents(merged_parents)
        cleaned_parents = self.__clean_small_chunks(split_parents)
        
        all_parent_chunks: List[Any] = []
        all_child_chunks: List[Any] = []
        self.__create_child_chunks(all_parent_chunks, all_child_chunks, cleaned_parents, doc_path)
        return all_parent_chunks, all_child_chunks

    def __merge_small_parents(self, chunks: List[Any]) -> List[Any]:
        """Mescla blocos pai consecutivos se forem menores que o tamanho mínimo estipulado."""
        if not chunks:
            return []
        
        merged: List[Any] = []
        current: Any = None
        
        for chunk in chunks:
            if current is None:
                current = chunk
            else:
                current.page_content += "\n\n" + chunk.page_content
                for k, v in chunk.metadata.items():
                    if k in current.metadata:
                        current.metadata[k] = f"{current.metadata[k]} -> {v}"
                    else:
                        current.metadata[k] = v

            if len(current.page_content) >= self.__min_parent_size:
                merged.append(current)
                current = None
        
        if current:
            if merged:
                merged[-1].page_content += "\n\n" + current.page_content
                for k, v in current.metadata.items():
                    if k in merged[-1].metadata:
                        merged[-1].metadata[k] = f"{merged[-1].metadata[k]} -> {v}"
                    else:
                        merged[-1].metadata[k] = v
            else:
                merged.append(current)
        
        return merged

    def __split_large_parents(self, chunks: List[Any]) -> List[Any]:
        """Divide recursivamente os blocos pai que ultrapassam o tamanho máximo permitido."""
        split_chunks: List[Any] = []
        
        for chunk in chunks:
            if len(chunk.page_content) <= self.__max_parent_size:
                split_chunks.append(chunk)
            else:
                splitter = RecursiveCharacterTextSplitter(
                    chunk_size=self.__max_parent_size,
                    chunk_overlap=config.CHILD_CHUNK_OVERLAP
                )
                sub_chunks = splitter.split_documents([chunk])
                split_chunks.extend(sub_chunks)
        
        return split_chunks

    def __clean_small_chunks(self, chunks: List[Any]) -> List[Any]:
        """Garante que não restem fragmentos soltos muito pequenos nas extremidades."""
        cleaned: List[Any] = []
        
        for i, chunk in enumerate(chunks):
            if len(chunk.page_content) < self.__min_parent_size:
                if cleaned:
                    cleaned[-1].page_content += "\n\n" + chunk.page_content
                    for k, v in chunk.metadata.items():
                        if k in cleaned[-1].metadata:
                            cleaned[-1].metadata[k] = f"{cleaned[-1].metadata[k]} -> {v}"
                        else:
                            cleaned[-1].metadata[k] = v
                elif i < len(chunks) - 1:
                    chunks[i + 1].page_content = chunk.page_content + "\n\n" + chunks[i + 1].page_content
                    for k, v in chunk.metadata.items():
                        if k in chunks[i + 1].metadata:
                            chunks[i + 1].metadata[k] = f"{v} -> {chunks[i + 1].metadata[k]}"
                        else:
                            chunks[i + 1].metadata[k] = v
                else:
                    cleaned.append(chunk)
            else:
                cleaned.append(chunk)
        
        return cleaned

    def __create_child_chunks(self, all_parent_pairs: List[Any], all_child_chunks: List[Any], parent_chunks: List[Any], doc_path: Path) -> None:
        """Gera os fragmentos filhos a partir dos pais consolidados, anexando seus IDs cruzados."""
        for i, p_chunk in enumerate(parent_chunks):
            parent_id = f"{doc_path.stem}_parent_{i}"
            p_chunk.metadata.update({"source": str(doc_path.stem)+".pdf", "parent_id": parent_id})
            
            all_parent_pairs.append((parent_id, p_chunk))
            all_child_chunks.extend(self.__child_splitter.split_documents([p_chunk]))
