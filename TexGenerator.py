import os
import logging
import sqlite3
from datetime import datetime
from pylatex import Document, Section, Command, NoEscape
from pylatexenc.latexencode import UnicodeToLatexEncoder, unicode_to_latex
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
        self.encoder = UnicodeToLatexEncoder(
            unknown_char_policy="replace",
            non_ascii_only=True
        )

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
                summaries[section] = [row[0] for row in rows if row[0]]

            conn.close()
        except sqlite3.Error as e:
            logging.error(f"Erro ao buscar resumos: {e}")
        except Exception as e:
            logging.error(f"Erro geral: {e}")

        return summaries, bib_content

    def create_tex_document(self, summaries: dict, tags: list, bib_path: str) -> Document:
        """
        Cria um documento LaTeX com os resumos e fontes fornecidos.
        """
        doc = Document(
            documentclass="abntex2",
            document_options=["article", "11pt", "oneside", "a4paper", "brazil", "sumario=tradicional"]
        )
    
        # Preâmbulo otimizado
        preamble = [
            r'\usepackage[T1]{fontenc}',
            r'\usepackage[utf8]{inputenc}',
            r'\usepackage{lmodern}',
            r'\usepackage{indentfirst}',
            r'\usepackage{graphicx}',
            r'\usepackage{color}',
            r'\usepackage{microtype}',
            r'\usepackage{lipsum}',
            r'\usepackage[brazilian,hyperpageref]{backref}',
            r'\usepackage[alf]{abntex2cite}',
            r'''
            \definecolor{blue}{RGB}{41,5,195}
            \hypersetup{
                pdftitle={Modelo Canônico de Artigo Científico com abnTeX},
                pdfauthor={Ephor Linguística Computacional - Maringá - PR},
                pdfsubject={Relatório gerado automaticamente},
                pdfkeywords={abnt, latex, abntex, abntex2, artigo científico},
                colorlinks=true,
                linkcolor=blue,
                citecolor=blue,
                urlcolor=blue
            }
            ''',
            # Adicionando definição genérica para \theforeigntitle
            r'\newcommand{\theforeigntitle}{Título genérico}'
        ]
    
        for command in preamble:
            doc.preamble.append(NoEscape(command))
    
        doc.preamble.append(Command("title", "Modelo Canônico de Artigo Científico com abnTeX"))
        doc.preamble.append(Command("author", "Ephor Linguística Computacional - Maringá - PR"))
        doc.preamble.append(Command("date", datetime.now().strftime("%Y, v-1.9.7")))
    
        # Ajustes de layout
        doc.preamble.append(NoEscape(r'\setlength{\parindent}{1.3cm}'))
        doc.preamble.append(NoEscape(r'\setlength{\parskip}{0.2cm}'))
        doc.preamble.append(NoEscape(r'\SingleSpacing'))
    
        doc.append(NoEscape(r'\maketitle'))
        doc.append(NoEscape(r'\selectlanguage{brazil}'))
        doc.append(NoEscape(r'\frenchspacing'))
    
        # Resumo
        with doc.create(Section("Resumo", numbering=False)):
            doc.append(NoEscape(r"""
                Aviso Importante
                Este documento foi gerado usando processamento de linguística computacional auxiliado por inteligência artificial. Portanto este conteúdo requer revisão humana, pois pode conter erros.
                \vspace{\onelineskip}
            """))
            doc.append(NoEscape(r"\textbf{Palavras-chave}: " + ', '.join(tags) + '.'))
    
        # Adiciona seções de conteúdo
        for section, texts in summaries.items():
            with doc.create(Section(section.capitalize())):
                for text in texts:
                    if text.strip():
                        doc.append(NoEscape(unicode_to_latex(text, unknown_char_policy="replace")))
    
        # Referências bibliográficas
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

            with open(bib_file_path, 'w', encoding='utf-8') as bib_file:
                bib_file.write(bib_content)
        except Exception as e:
            logging.error(f"Erro ao salvar arquivos: {e}")
            return "", ""

        return tex_file_path, bib_file_path

    def compile_tex_to_pdf(self, tex_file_path: str) -> str:
        """
        Compila o arquivo LaTeX para PDF.
        """
        try:
            base_name = os.path.splitext(tex_file_path)[0]
            for _ in range(2):  # Executar duas vezes para resolver referências
                subprocess.run(['pdflatex', '-output-directory', self.base_dir, tex_file_path], check=True)
    
            # Executa bibtex para processar as referências
            subprocess.run(['bibtex', base_name + '.aux'], check=True)
    
            # Compila novamente após bibtex
            subprocess.run(['pdflatex', '-output-directory', self.base_dir, tex_file_path], check=True)
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
        aux_extensions = ['.aux', '.out', '.toc', '.bbl', '.blg']

        for ext in aux_extensions:
            aux_file = os.path.join(self.base_dir, base_name + ext)
            if os.path.exists(aux_file):
                os.remove(aux_file)

    def generate_and_compile_document(self, summaries=None, bib_content=None) -> str:
        """
        Gera um documento LaTeX e compila-o para PDF.
        """
        timestamp = self.generate_timestamp()

        if summaries is None or bib_content is None:
            summaries, bib_content = self.fetch_summaries_and_sources()

        doc = self.create_tex_document(summaries, [], None)
        tex_content = doc.dumps()

        tex_file_path, bib_file_path = self.save_files(tex_content, bib_content, timestamp)

        pdf_file_path = self.compile_tex_to_pdf(tex_file_path)

        if pdf_file_path:
            self.cleanup_auxiliary_files(tex_file_path)

        return pdf_file_path
