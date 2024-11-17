import os
import logging
import sqlite3
from datetime import datetime
from pylatex import Document, Section, Command, NoEscape
from pylatexenc.latexencode import UnicodeToLatexEncoder
import subprocess

# Configuração do logger
logging.basicConfig(filename='TexGenerator.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


class TexGenerator:
    """
    Classe TexGenerator para gerar, revisar e compilar documentos LaTeX a partir de dados do banco de dados.
    """
    base_dir = 'pdf_output/'

    def __init__(self, db_name: str):
        """
        Inicializa o TexGenerator, definindo o caminho do banco e o diretório de saída.
        """
        self.db_name = os.path.join(os.getcwd(), "databases", os.path.basename(db_name))
        os.makedirs(self.base_dir, exist_ok=True)
        self.encoder = UnicodeToLatexEncoder(unknown_char_policy='replace')

    @staticmethod
    def generate_timestamp() -> str:
        """
        Gera um timestamp formatado para nomear arquivos.

        Retorna:
        str: Timestamp no formato 'AAAA-MM-DD-HH-MM-SS'.
        """
        now = datetime.now()
        return now.strftime("%Y-%m-%d-%H-%M-%S")

    def fetch_summaries_and_sources(self) -> tuple:
        """
        Busca os resumos de cada seção e o conteúdo do arquivo BibTeX.

        Retorna:
        tuple: Dicionário com os resumos e o conteúdo BibTeX.
        """
        sections = ["relato", "contexto", "entidades", "linha_tempo", "contradicoes", "conclusao"]
        summaries = {}
        bib_content = ""

        try:
            if not os.path.exists(self.db_name):
                logging.error(f"Banco de dados não encontrado: {self.db_name}")
                return summaries, bib_content

            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            # Busca os resumos de cada seção
            for section in sections:
                cursor.execute(f"SELECT summary_gpt3 FROM {section}")
                rows = cursor.fetchall()
                summaries[section] = [row[0] for row in rows if row[0]]  # Apenas resumos não vazios

            conn.close()

            # Carregar conteúdo BibTeX
            bib_path = os.path.join(self.base_dir, "references.bib")
            if os.path.exists(bib_path):
                with open(bib_path, 'r', encoding='utf-8') as f:
                    bib_content = f.read()
        except sqlite3.Error as e:
            logging.error(f"Erro ao buscar resumos ou fontes: {e}")
        except Exception as e:
            logging.error(f"Erro geral ao carregar fontes ou resumos: {e}")

        return summaries, bib_content

    def create_tex_document(self, summaries: dict, bib_content: str) -> Document:
        """
        Cria um documento LaTeX com os resumos e fontes fornecidos.

        Parâmetros:
        summaries (dict): Dicionário com os resumos por seção.
        bib_content (str): Conteúdo do arquivo BibTeX.

        Retorna:
        Document: Documento LaTeX.
        """
        doc = Document()

        # Configurações iniciais do documento
        doc.preamble.append(Command("title", "Relatório de Resumos"))
        doc.append(NoEscape("\\maketitle"))

        # Adiciona a seção de fontes
        with doc.create(Section("Fontes Utilizadas")):
            doc.append(NoEscape(self.encoder.unicode_to_latex(bib_content)))

        # Adiciona cada seção com os resumos
        for section, texts in summaries.items():
            with doc.create(Section(section.capitalize())):
                for text in texts:
                    doc.append(f"{self.encoder.unicode_to_latex(text)}\n\n")

        return doc

    def save_files(self, tex_content: str, bib_content: str) -> tuple:
        """
        Salva os arquivos LaTeX (.tex) e BibTeX (.bib).

        Parâmetros:
        tex_content (str): Conteúdo LaTeX.
        bib_content (str): Conteúdo BibTeX.

        Retorna:
        tuple: Caminhos dos arquivos .tex e .bib salvos.
        """
        timestamp = self.generate_timestamp()
        tex_file_path = os.path.join(self.base_dir, f"{timestamp}.tex")
        bib_file_path = os.path.join(self.base_dir, f"{timestamp}.bib")

        try:
            with open(tex_file_path, 'w', encoding='utf-8') as tex_file:
                tex_file.write(tex_content)
            logging.info(f"Arquivo LaTeX salvo: {tex_file_path}")

            with open(bib_file_path, 'w', encoding='utf-8') as bib_file:
                bib_file.write(bib_content)
            logging.info(f"Arquivo BibTeX salvo: {bib_file_path}")
        except Exception as e:
            logging.error(f"Erro ao salvar arquivos .tex e .bib: {e}")
            return "", ""

        return tex_file_path, bib_file_path

    def compile_tex_to_pdf(self, tex_file_path: str) -> str:
        """
        Compila o arquivo LaTeX para PDF.

        Parâmetros:
        tex_file_path (str): Caminho do arquivo .tex.

        Retorna:
        str: Caminho do PDF gerado ou string vazia em caso de erro.
        """
        try:
            subprocess.run(['pdflatex', '-output-directory', self.base_dir, tex_file_path], check=True)
            pdf_file_path = os.path.splitext(tex_file_path)[0] + ".pdf"

            if os.path.exists(pdf_file_path):
                logging.info(f"PDF gerado com sucesso: {pdf_file_path}")
                return pdf_file_path
            else:
                logging.error("Erro: PDF não foi gerado.")
                return ""
        except subprocess.CalledProcessError as e:
            logging.error(f"Erro ao compilar o arquivo LaTeX: {e}")
            return ""

    def generate_and_compile_document(self, summaries=None, bib_content=None) -> str:
        """
        Gera um documento LaTeX e compila-o para PDF.

        Parâmetros:
        summaries (dict, opcional): Dicionário com os resumos.
        bib_content (str, opcional): Conteúdo BibTeX.

        Retorna:
        str: Caminho do PDF gerado ou string vazia em caso de erro.
        """
        if summaries is None or bib_content is None:
            summaries, bib_content = self.fetch_summaries_and_sources()

        if not summaries:
            logging.error("Nenhum resumo disponível para gerar o documento.")
            return ""

        # Cria o documento LaTeX
        doc = self.create_tex_document(summaries, bib_content)
        tex_content = doc.dumps()

        # Salva os arquivos .tex e .bib
        tex_file_path, bib_file_path = self.save_files(tex_content, bib_content)
        if not tex_file_path or not bib_file_path:
            logging.error("Erro ao salvar arquivos .tex ou .bib.")
            return ""

        # Compila o arquivo .tex para PDF
        pdf_file_path = self.compile_tex_to_pdf(tex_file_path)
        return pdf_file_path
