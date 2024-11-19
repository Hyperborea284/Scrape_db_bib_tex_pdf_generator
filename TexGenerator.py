import os
import logging
import sqlite3
from datetime import datetime
from pylatex import Document, Section, Command, NoEscape
from pylatexenc.latexencode import UnicodeToLatexEncoder
import subprocess
import shutil
from BibGenerator import BibGenerator

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
        self.bib_generator = BibGenerator(db_name)

    @staticmethod
    def generate_timestamp() -> str:
        """
        Gera um timestamp formatado para nomear arquivos.
        """
        now = datetime.now()
        return now.strftime("%Y-%m-%d-%H-%M-%S")

    def fetch_summaries_and_sources(self) -> tuple:
        """
        Busca os resumos de cada seção e o conteúdo do arquivo BibTeX.
    
        Retorna:
        tuple: (Dicionário de resumos, Conteúdo do arquivo BibTeX).
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
    
            for section in sections:
                query = f"SELECT summary_gpt3 FROM {section}"
                cursor.execute(query)
                rows = cursor.fetchall()
    
                if rows:
                    summaries[section] = [row[0] for row in rows if row[0]]
                else:
                    summaries[section] = []
    
                logging.info(f"Resumos recuperados para a seção '{section}': {summaries[section]}")
    
            conn.close()
    
            # Carregar o conteúdo do BibTeX
            bib_path = os.path.join(self.base_dir, f"{self.generate_timestamp()}.bib")
            if os.path.exists(bib_path):
                with open(bib_path, 'r', encoding='utf-8') as f:
                    bib_content = f.read()
    
        except sqlite3.Error as e:
            logging.error(f"Erro ao buscar resumos ou fontes: {e}")
        except Exception as e:
            logging.error(f"Erro geral ao carregar fontes ou resumos: {e}")
    
        return summaries, bib_content

    def create_tex_document(self, summaries: dict, tags: list, bib_path: str) -> Document:
        """
        Cria um documento LaTeX com os resumos e fontes fornecidos.
        """
        doc = Document()
    
        # Preâmbulo
        preamble = [
            r'\usepackage[T1]{fontenc}',
            r'\usepackage[utf8]{inputenc}',
            r'\usepackage{lmodern}',
            r'\usepackage{textcomp}',
            r'\usepackage{lastpage}',
            r'\usepackage{indentfirst}',
            r'\usepackage{graphicx}',
            r'\usepackage[alf]{abntex2cite}',
            r'\usepackage[brazilian,hyperpageref]{backref}',
            r'\usepackage{color}',
            r'\usepackage{hyperref}',
            r'\definecolor{blue}{RGB}{41,5,195}',
            r'''
            \hypersetup{
                pdftitle={Relatório de Resumos},
                pdfauthor={Ephor Linguística Computacional - Maringá - PR},
                pdfsubject={Relatório gerado automaticamente},
                colorlinks=true,
                linkcolor=blue,
                citecolor=blue,
                filecolor=magenta,
                urlcolor=blue
            }
            '''
        ]
    
        for command in preamble:
            doc.preamble.append(NoEscape(command))
    
        doc.preamble.append(Command("title", "Relatório de Resumos"))
        doc.preamble.append(Command("author", "Ephor Linguística Computacional"))
        doc.preamble.append(Command("date", datetime.now().strftime("%Y-%m-%d")))
    
        if tags:
            with doc.create(Section("Palavras-chave")):
                doc.append(NoEscape(r'\textbf{Palavras-chave}: ' + ', '.join(tags) + '.'))
    
        for section, texts in summaries.items():
            with doc.create(Section(section.capitalize())):
                for text in texts:
                    if text.strip():
                        escaped_text = self.encoder.unicode_to_latex(text)
                        doc.append(escaped_text)
    
        if bib_path and os.path.exists(bib_path):
            doc.append(NoEscape(r'\bibliography{' + os.path.splitext(os.path.basename(bib_path))[0] + '}'))
    
        return doc

    def save_files(self, tex_content: str, bib_content: str, timestamp: str) -> tuple:
        """
        Salva os arquivos LaTeX (.tex) e BibTeX (.bib) com o mesmo timestamp.
        """
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
            logging.error(f"Erro ao salvar arquivos: {e}")
            return "", ""

        return tex_file_path, bib_file_path

    def compile_tex_to_pdf(self, tex_file_path: str) -> str:
        """
        Compila o arquivo LaTeX para PDF.
        """
        try:
            for _ in range(2):  # Executar duas vezes para resolver referências
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

    def cleanup_auxiliary_files(self, tex_file_path: str):
        """
        Remove arquivos auxiliares gerados durante a compilação LaTeX.
        """
        base_name = os.path.splitext(os.path.basename(tex_file_path))[0]
        aux_extensions = ['.aux', '.log', '.out', '.fls', '.fdb_latexmk', '.toc', '.bbl', '.blg']

        for ext in aux_extensions:
            aux_file = os.path.join(self.base_dir, base_name + ext)
            if os.path.exists(aux_file):
                try:
                    os.remove(aux_file)
                    logging.info(f"Arquivo auxiliar removido: {aux_file}")
                except OSError as e:
                    logging.warning(f"Falha ao remover {aux_file}: {e}")

    def generate_and_compile_document(self, summaries=None, bib_content=None) -> str:
        """
        Gera um documento LaTeX e compila-o para PDF.
        """
        # Gera o timestamp para nomear arquivos
        timestamp = self.generate_timestamp()
        
        if summaries is None or bib_content is None:
            summaries, bib_content = self.fetch_summaries_and_sources()
        
        if not summaries or all(len(texts) == 0 for texts in summaries.values()):
            logging.error("Nenhum resumo válido disponível para gerar o documento.")
            # Cria um documento mínimo para evitar falha total
            summaries = {"Aviso": ["Nenhum conteúdo disponível para gerar o PDF."]}
    
        # Gera o arquivo LaTeX com conteúdo válido
        doc = self.create_tex_document(summaries, [], None)
        tex_content = doc.dumps()
    
        # Salva os arquivos .tex e .bib
        tex_file_path, bib_file_path = self.save_files(tex_content, bib_content, timestamp)
    
        if not tex_file_path:
            logging.error("Erro ao salvar o arquivo LaTeX.")
            return ""
    
        # Compila o arquivo LaTeX para PDF
        pdf_file_path = self.compile_tex_to_pdf(tex_file_path)
    
        if pdf_file_path:
            self.cleanup_auxiliary_files(tex_file_path)
        else:
            logging.error("Erro durante a compilação do PDF.")
        
        return pdf_file_path