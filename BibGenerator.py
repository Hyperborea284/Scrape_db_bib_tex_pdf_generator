import os
import sqlite3
import hashlib
import bibtexparser
from bibtexparser.bwriter import BibTexWriter
from bibtexparser.bibdatabase import BibDatabase
from typing import List, Dict, Optional
import logging

# Configuração do logger para registrar eventos e erros em 'BibGenerator.log'
logging.basicConfig(filename='BibGenerator.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

class BibGenerator:
    def __init__(self, db_name: str, output_dir: str = "bib_output"):
        """
        Inicializa o BibGenerator, que é responsável por extrair entradas de referências do banco de dados SQLite,
        formatá-las no estilo BibTeX e salvá-las em um arquivo .bib.

        Parâmetros:
        db_name (str): Nome do banco de dados SQLite que contém as referências.
        output_dir (str): Diretório onde o arquivo .bib gerado será salvo.
        """
        self.db_name = db_name
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.bib_database = BibDatabase()
        
    def fetch_entries_from_db(self) -> List[Dict[str, str]]:
        """
        Busca entradas de referências no banco de dados SQLite, estruturando-as para o formato BibTeX.
        
        Retorna:
        List[Dict[str, str]]: Uma lista de dicionários, onde cada dicionário representa uma entrada BibTeX.
        """
        try:
            # Conecta ao banco de dados e executa uma consulta para obter os dados de referência
            conn = sqlite3.connect(f"databases/{self.db_name}")
            cursor = conn.cursor()
            cursor.execute("SELECT id, title, author, year, journal, volume, number, pages, doi, url FROM references")
            entries = cursor.fetchall()
            conn.close()

            # Formata cada entrada em um dicionário conforme o padrão BibTeX
            formatted_entries = [
                {
                    "ENTRYTYPE": "article",
                    "ID": f"entry_{entry[0]}",
                    "title": entry[1],
                    "author": entry[2],
                    "year": str(entry[3]),
                    "journal": entry[4],
                    "volume": str(entry[5]) if entry[5] else "",
                    "number": str(entry[6]) if entry[6] else "",
                    "pages": entry[7] if entry[7] else "",
                    "doi": entry[8] if entry[8] else "",
                    "url": entry[9] if entry[9] else ""
                }
                for entry in entries
            ]
            return formatted_entries
        except sqlite3.Error as e:
            print(f"Erro ao buscar entradas do banco de dados: {e}")
            return []

    def generate_bib_entries(self) -> str:
        """
        Gera o conteúdo BibTeX com base nas entradas obtidas do banco de dados, convertendo os dados
        em um formato adequado para o BibTeX.

        Retorna:
        str: O conteúdo BibTeX gerado como uma string.
        """
        entries = self.fetch_entries_from_db()
        if not entries:
            print("Nenhuma entrada encontrada no banco de dados.")
            return ""

        # Define as entradas na estrutura BibDatabase e usa o BibTexWriter para formatação
        self.bib_database.entries = entries
        writer = BibTexWriter()
        writer.indent = "  "  # Define a indentação para o arquivo BibTeX
        return bibtexparser.dumps(self.bib_database, writer)

    def save_bib_file(self, filename: Optional[str] = None) -> str:
        """
        Salva o conteúdo BibTeX gerado em um arquivo `.bib` no diretório de saída especificado.

        Parâmetros:
        filename (Optional[str]): Nome do arquivo .bib a ser salvo. Se não fornecido, usa 'references.bib'.

        Retorna:
        str: Caminho completo do arquivo .bib salvo.
        """
        # Define o nome do arquivo padrão se nenhum for especificado
        filename = filename or "references.bib"
        file_path = os.path.join(self.output_dir, filename)
        
        # Gera o conteúdo BibTeX e verifica se há conteúdo para salvar
        bib_content = self.generate_bib_entries()
        if not bib_content:
            print("Não foi possível salvar o arquivo .bib porque não há conteúdo.")
            return ""

        # Salva o conteúdo em um arquivo .bib no diretório especificado
        with open(file_path, "w", encoding="utf-8") as bib_file:
            bib_file.write(bib_content)
        
        print(f"Arquivo .bib salvo em: {file_path}")
        return file_path

    def verify_bib_integrity(self, bib_content: str) -> bool:
        """
        Verifica a integridade do conteúdo BibTeX para garantir que ele esteja bem-formado e possa ser lido sem erros.

        Parâmetros:
        bib_content (str): O conteúdo BibTeX a ser verificado.

        Retorna:
        bool: True se o conteúdo BibTeX estiver bem-formado; False caso contrário.
        """
        try:
            # Tenta carregar o conteúdo com bibtexparser para verificar a integridade
            bibtexparser.loads(bib_content)
            return True
        except Exception as e:
            print(f"Erro de integridade no conteúdo BibTeX: {e}")
            return False

    def generate_and_save_bib(self) -> str:
        """
        Gera o conteúdo BibTeX, verifica sua integridade e, se estiver bem-formado, salva em um arquivo `.bib`.

        Retorna:
        str: Caminho completo do arquivo .bib salvo se bem-sucedido; string vazia se houve erro.
        """
        # Gera o conteúdo BibTeX das entradas do banco de dados
        bib_content = self.generate_bib_entries()
        
        # Verifica a integridade do conteúdo BibTeX antes de salvá-lo
        if not self.verify_bib_integrity(bib_content):
            print("Conteúdo BibTeX inválido. Abortando salvamento.")
            return ""
        
        # Salva o arquivo .bib no diretório de saída
        return self.save_bib_file()
