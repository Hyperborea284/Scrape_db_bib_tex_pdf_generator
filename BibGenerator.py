import os
import sqlite3
import logging
import bibtexparser
from bibtexparser.bwriter import BibTexWriter
from bibtexparser.bibdatabase import BibDatabase
from datetime import datetime
from DatabaseUtils import DatabaseUtils

# Configuração do logger para registrar eventos e erros em 'BibGenerator.log'
logging.basicConfig(filename='BibGenerator.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


class BibGenerator:
    def __init__(self, db_name: str, output_dir: str = "pdf_output"):
        """
        Inicializa o BibGenerator, garantindo o uso do banco correto.
        """
        self.db_utils = DatabaseUtils(db_name)
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.bib_database = BibDatabase()

    def fetch_entries_from_db(self) -> list:
        """
        Busca as entradas BibTeX do banco de dados.

        Retorna:
        list: Lista de entradas em formato BibTeX.
        """
        query = "SELECT id, title, author, year, journal, volume, number, pages, doi, url FROM bib_references"
        try:
            with self.db_utils.connect() as conn:
                rows = conn.execute(query).fetchall()
            return [
                {
                    "ENTRYTYPE": "article",
                    "ID": f"entry_{row[0]}",
                    "title": row[1],
                    "author": row[2] or "Desconhecido",
                    "year": str(row[3]) if row[3] else "0",
                    "journal": row[4] or "",
                    "volume": row[5] or "",
                    "number": row[6] or "",
                    "pages": row[7] or "",
                    "doi": row[8] or "",
                    "url": row[9] or ""
                }
                for row in rows
            ]
        except sqlite3.Error as e:
            logging.error(f"Erro ao buscar entradas do banco de dados: {e}")
            return []

    def verify_bib_integrity(self, bib_content: str) -> bool:
        """
        Verifica a integridade do conteúdo BibTeX para garantir que ele esteja bem-formado.

        Parâmetros:
        bib_content (str): Conteúdo BibTeX gerado.

        Retorna:
        bool: True se o conteúdo estiver bem-formado, False caso contrário.
        """
        try:
            bibtexparser.loads(bib_content)
            return True
        except Exception as e:
            logging.error(f"Erro de integridade no conteúdo BibTeX: {e}")
            return False

    def generate_and_save_bib(self) -> str:
        """
        Gera e salva o arquivo BibTeX com referências do banco de dados.

        Retorna:
        str: Caminho do arquivo BibTeX salvo ou uma string vazia em caso de erro.
        """
        try:
            entries = self.fetch_entries_from_db()
            if not entries:
                logging.warning("Nenhuma entrada encontrada para gerar o arquivo BibTeX.")
                return ""

            # Prepara as entradas BibTeX
            self.bib_database.entries = entries
            writer = BibTexWriter()

            # Caminho do arquivo BibTeX
            timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
            bib_path = os.path.join(self.output_dir, f"{timestamp}.bib")

            # Salva o conteúdo BibTeX no arquivo
            with open(bib_path, "w", encoding="utf-8") as bib_file:
                bib_file.write(writer.write(self.bib_database))

            logging.info(f"Arquivo BibTeX salvo em: {bib_path}")
            return bib_path
        except Exception as e:
            logging.error(f"Erro ao gerar e salvar o arquivo BibTeX: {e}")
            return ""
