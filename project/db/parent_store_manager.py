import re
import json
import shutil
from pathlib import Path
from typing import List, Dict, Any

import config

class ParentStoreManager:
    """
    Gerenciador de Armazenamento de Documentos Pai (Parent Store).

    Responsável por persistir e recuperar os blocos de texto maiores (pais) no 
    sistema de arquivos local. Esta classe é a base da técnica de recuperação 
    'Small-to-Big', permitindo que o sistema encontre um fragmento pequeno (filho) 
    no banco vetorial, mas devolva o contexto completo (pai) para o LLM processar.
    """
    __store_path: Path

    def __init__(self, store_path: str = config.PARENT_STORE_PATH) -> None:
        """
        Inicializa o gerenciador e garante a existência do diretório de armazenamento.

        Args:
            store_path (str, opcional): Caminho para o diretório local onde os arquivos 
                JSON dos nós pai serão salvos. Padrão definido em config.py.
        """
        self.__store_path = Path(store_path) 
        self.__store_path.mkdir(parents=True, exist_ok=True)

    def save(self, parent_id: str, content: str, metadata: Dict[str, Any]) -> None:
        """
        Salva um único documento pai no disco em formato JSON.

        Args:
            parent_id (str): Identificador único do fragmento pai (ex: doc_parent_0).
            content (str): O conteúdo textual completo do fragmento.
            metadata (Dict[str, Any]): Dicionário com metadados adicionais (fonte, página, etc).
        """
        file_path = self.__store_path / f"{parent_id}.json"
        file_path.write_text(
            json.dumps({"page_content": content, "metadata": metadata}, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    
    def save_many(self, parents: List[Any]) -> None:
        """
        Salva múltiplos documentos pai no disco iterativamente.

        Args:
            parents (List[Any]): Lista de tuplos ou objetos contendo o ID e o documento.
        """
        for parent_id, doc in parents:
            self.save(parent_id, doc.page_content, doc.metadata)

    def load(self, parent_id: str) -> Dict[str, Any]:
        """
        Carrega o arquivo JSON bruto de um documento pai a partir do disco.

        Args:
            parent_id (str): Identificador único do fragmento pai.

        Returns:
            Dict[str, Any]: Dicionário contendo os dados brutos salvos no arquivo JSON.
        """
        file_path = self.__store_path / (
            parent_id if parent_id.lower().endswith(".json") else f"{parent_id}.json"
        )
        return json.loads(file_path.read_text(encoding="utf-8"))
    
    def load_content(self, parent_id: str) -> Dict[str, Any]:
        """
        Carrega um documento pai e o formata para consumo do Agente RAG.

        Args:
            parent_id (str): Identificador único do fragmento pai.

        Returns:
            Dict[str, Any]: Dicionário estruturado com 'content', 'parent_id' e 'metadata'.
        """
        data = self.load(parent_id)
        return {
                "content": data["page_content"],
                "parent_id": parent_id,
                "metadata": data["metadata"]
            }

    @staticmethod
    def _get_sort_key(id_str: str) -> int:
        """
        Extrai o índice numérico do ID do pai para ordenação lógica.

        Args:
            id_str (str): A string do ID (ex: 'documento_parent_12').

        Returns:
            int: O número extraído (ex: 12) ou 0 se não for encontrado.
        """
        match = re.search(r'_parent_(\d+)$', id_str)
        return int(match.group(1)) if match else 0

    def load_content_many(self, parent_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Carrega múltiplos documentos pai, garantindo unicidade e ordenação.

        Args:
            parent_ids (List[str]): Lista de identificadores a serem recuperados.

        Returns:
            List[Dict[str, Any]]: Lista ordenada de dicionários de conteúdo pai.
        """
        unique_ids = set(parent_ids)
        return [self.load_content(pid) for pid in sorted(unique_ids, key=self._get_sort_key)]
    
    def clear_store(self) -> None:
        """
        Limpa fisicamente o diretório, apagando todos os fragmentos pai salvos.
        """
        if self.__store_path.exists():
            shutil.rmtree(self.__store_path)
        self.__store_path.mkdir(parents=True, exist_ok=True)
