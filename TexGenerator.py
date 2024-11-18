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
    
                # Verifica o formato das linhas retornadas
                if rows:
                    # Adiciona uma verificação extra para garantir que o conteúdo seja válido
                    summaries[section] = [row[0] for row in rows if isinstance(row, tuple) and len(row) > 0 and row[0]]
                else:
                    summaries[section] = []
    
                logging.info(f"Resumos recuperados para a seção '{section}': {summaries[section]}")
    
            conn.close()
    
            # Carregar o arquivo BibTeX correspondente
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
    
        Parâmetros:
        summaries (dict): Dicionário com os resumos por seção.
        tags (list): Lista de palavras-chave extraídas do banco de dados.
        bib_path (str): Caminho do arquivo BibTeX.
    
        Retorna:
        Document: Documento LaTeX.
        """
        doc = Document()
    
        # Preâmbulo com pacotes e configurações
        doc.preamble.append(NoEscape(r'\usepackage{lmodern}'))
        doc.preamble.append(NoEscape(r'\usepackage[T1]{fontenc}'))
        doc.preamble.append(NoEscape(r'\usepackage[utf8]{inputenc}'))
        doc.preamble.append(NoEscape(r'\usepackage{indentfirst}'))
        doc.preamble.append(NoEscape(r'\usepackage{nomencl}'))
        doc.preamble.append(NoEscape(r'\usepackage{color}'))
        doc.preamble.append(NoEscape(r'\usepackage{graphicx}'))
        doc.preamble.append(NoEscape(r'\usepackage{microtype}'))
        doc.preamble.append(NoEscape(r'\usepackage[brazilian,hyperpageref]{backref}'))
        doc.preamble.append(NoEscape(r'\usepackage[alf]{abntex2cite}'))
    
        # Configurações de metadados e cores
        doc.preamble.append(NoEscape(r'\definecolor{blue}{RGB}{41,5,195}'))
        doc.preamble.append(NoEscape(r'''
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
        '''))
    
        # Título, autor e local
        doc.preamble.append(Command("title", "Modelo Canônico de Artigo científico com \\abnTeX"))
        doc.preamble.append(Command("author", "Ephor Linguística Computacional - Maringá - PR \\url{http://ephor.com.br/}"))
        doc.preamble.append(Command("local", "Maringá - PR - Brasil"))
        doc.preamble.append(Command("date", datetime.now().strftime("%Y-%m-%d")))
    
        # Resumo
        with doc.create(NoEscape(r'\begin{resumoumacoluna}')):
            doc.append(NoEscape(r'''
            Aviso Importante:
            Este documento foi gerado usando processamento de linguística computacional auxiliado por inteligência artificial.
            Portanto, este conteúdo requer revisão humana, pois pode conter erros.
            '''))
            if tags:
                doc.append(NoEscape(r'\textbf{Palavras-chave}: ' + ', '.join(tags) + '.'))
    
        # Corpo do texto
        for section, texts in summaries.items():
            with doc.create(Section(section.capitalize())):
                for text in texts:
                    if isinstance(text, str) and text.strip():  # Verifica se o texto é válido
                        doc.append(self.encoder.unicode_to_latex(text))
                    else:
                        logging.warning(f"Texto inválido ignorado na seção '{section}': {text}")
    
        # Bibliografia
        if bib_path and os.path.exists(bib_path):
            doc.append(NoEscape(r'\bibliography{' + os.path.splitext(os.path.basename(bib_path))[0] + '}'))
        else:
            logging.warning("Bibliografia não encontrada. O documento será gerado sem referências.")
    
        return doc

    def save_files(self, tex_content: str, bib_content: str, timestamp: str) -> tuple:
        """
        Salva os arquivos LaTeX (.tex) e BibTeX (.bib) com o mesmo timestamp.
        """
        tex_file_path = os.path.join(self.base_dir, f"{timestamp}.tex")
        bib_file_path = os.path.join(self.base_dir, f"{timestamp}.bib")  # Ajustado para usar o mesmo caminho

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
        tex_file_path (str): Caminho do arquivo LaTeX (.tex).
    
        Retorna:
        str: Caminho do PDF gerado, ou uma string vazia em caso de erro.
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

    def cleanup_auxiliary_files(self, tex_file_path: str):
        """
        Remove arquivos auxiliares gerados durante a compilação LaTeX.
        """
        base_name = os.path.splitext(os.path.basename(tex_file_path))[0]
        aux_extensions = ['.aux', '.log', '.out', '.fls', '.fdb_latexmk', '.toc', '.synctex.gz', '.bbl', '.blg']

        for ext in aux_extensions:
            aux_file = os.path.join(self.base_dir, base_name + ext)
            if os.path.exists(aux_file):
                try:
                    os.remove(aux_file)
                    logging.info(f"Removed auxiliary file: {aux_file}")
                except OSError as e:
                    logging.warning(f"Failed to remove {aux_file}: {e}")

    def generate_and_compile_document(self, summaries=None, bib_content=None) -> str:
        """
        Gera um documento LaTeX e compila-o para PDF.
        """
        # Gera o timestamp para nomear arquivos
        timestamp = self.generate_timestamp()
        
        if summaries is None or bib_content is None:
            summaries, bib_content = self.fetch_summaries_and_sources()
    
        if not summaries:
            logging.error("Nenhum resumo disponível para gerar o documento.")
            return ""
    
        # Gera e salva o arquivo BibTeX
        bib_file_path = os.path.join(self.base_dir, f"{timestamp}.bib")
        try:
            with open(bib_file_path, 'w', encoding='utf-8') as bib_file:
                bib_file.write(bib_content)
            logging.info(f"Arquivo BibTeX salvo: {bib_file_path}")
        except Exception as e:
            logging.error(f"Erro ao salvar arquivo BibTeX: {e}")
            return ""
    
        # Cria o documento LaTeX
        doc = self.create_tex_document(summaries, [], bib_file_path)
        tex_content = doc.dumps()
    
        # Salva os arquivos .tex e .bib com o mesmo timestamp
        tex_file_path = os.path.join(self.base_dir, f"{timestamp}.tex")
        try:
            with open(tex_file_path, 'w', encoding='utf-8') as tex_file:
                tex_file.write(tex_content)
            logging.info(f"Arquivo LaTeX salvo: {tex_file_path}")
        except Exception as e:
            logging.error(f"Erro ao salvar arquivo LaTeX: {e}")
            return ""
    
        # Compila o arquivo .tex para PDF
        pdf_file_path = self.compile_tex_to_pdf(tex_file_path)
        if pdf_file_path:
            self.cleanup_auxiliary_files(tex_file_path)
        return pdf_file_path
    