import os
import glob
from pathlib import Path

import pymupdf.layout
import pymupdf4llm
import config

# Desativa paralelismo de tokenizadores para evitar deadlocks no Qdrant/HuggingFace
os.environ["TOKENIZERS_PARALLELISM"] = "false"

def pdf_to_markdown(pdf_path: Path, output_dir: Path) -> None:
    """
    Converte um arquivo PDF para o formato Markdown.

    Utiliza a biblioteca pymupdf4llm para extrair o texto preservando a 
    estrutura semântica (tabelas, listas e cabeçalhos). Isso é vital para 
    o posterior 'chunking' estruturado. Ignora imagens para otimizar o armazenamento.

    Args:
        pdf_path (Path): Caminho absoluto ou relativo para o arquivo PDF original.
        output_dir (Path): Diretório de destino onde o arquivo .md será salvo.
    """
    doc = pymupdf.open(pdf_path)
    md = pymupdf4llm.to_markdown(
        doc, 
        header=False, 
        footer=False, 
        page_separators=True, 
        ignore_images=True, 
        write_images=False, 
        image_path=None
    )
    # Limpeza de caracteres corrompidos durante a extração
    md_cleaned = md.encode('utf-8', errors='surrogatepass').decode('utf-8', errors='ignore')
    output_path = output_dir / Path(doc.name).stem
    output_path.with_suffix(".md").write_bytes(md_cleaned.encode('utf-8'))

def pdfs_to_markdowns(path_pattern: str, overwrite: bool = False) -> None:
    """
    Processa em lote (batch) a conversão de múltiplos PDFs para Markdown.

    Args:
        path_pattern (str): Padrão regex de busca de arquivos (ex: 'docs/*.pdf').
        overwrite (bool, opcional): Se True, reescreve arquivos Markdown já existentes. 
                                    Padrão é False para economizar poder computacional.
    """
    output_dir = Path(config.MARKDOWN_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    for pdf_path in map(Path, glob.glob(path_pattern)):
        md_path = (output_dir / pdf_path.stem).with_suffix(".md")
        if overwrite or not md_path.exists():
            pdf_to_markdown(pdf_path, output_dir)
