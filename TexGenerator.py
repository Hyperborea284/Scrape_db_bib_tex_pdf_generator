import os
import sqlite3
import logging
from datetime import datetime
from pylatex import Document, Section, Command, NoEscape
from pylatex.utils import escape_latex
from pylatexenc.latexencode import UnicodeToLatexEncoder
import re
import subprocess
import hashlib
from openai import OpenAI
from dotenv import load_dotenv

# Configuração do logger para registrar eventos e erros em 'TexGenerator.log'
logging.basicConfig(filename='TexGenerator.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Carrega as variáveis de ambiente do arquivo .env, incluindo a chave de API da OpenAI
load_dotenv(".env")

class DatabaseHandler:
    """
    Classe DatabaseHandler para gerenciar operações de extração de dados do banco de dados SQLite.
    """
    def __init__(self, db_name):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.db_name = db_name

    def get_all_elements_from_db(self, table_name, column_name):
        """
        Recupera todos os elementos de uma coluna específica de uma tabela específica no banco de dados.
        
        Parâmetros:
        table_name (str): Nome da tabela no banco de dados.
        column_name (str): Nome da coluna da qual os dados serão recuperados.
        
        Retorna:
        List[str]: Uma lista com os valores recuperados da coluna especificada.
        """
        query = f"SELECT {column_name} FROM {table_name}"
        self.cursor.execute(query)
        elements = self.cursor.fetchall()
        all_elements = [element[0] for element in elements] if elements else []
        return all_elements


class TexGenerator:
    """
    Classe TexGenerator para gerar, revisar e compilar documentos LaTeX a partir de dados no banco de dados.
    """
    base_dir = 'pdf_output/'

    def __init__(self, db_name):
        """
        Inicializa o TexGenerator, define o diretório de saída e cria uma instância do encoder UnicodeToLatexEncoder.
        
        Parâmetros:
        db_name (str): Nome do banco de dados de onde os dados serão recuperados.
        """
        self.db_name = db_name
        os.makedirs(self.base_dir, exist_ok=True)
        self.encoder = UnicodeToLatexEncoder(unknown_char_policy='replace')
        self.database_handler = DatabaseHandler(db_name)
        
        # Extrai o nome do arquivo sem extensão para o caminho do arquivo .bib
        _, db_file_name = os.path.split(db_name)
        db_name_without_extension, _ = os.path.splitext(db_file_name)
        self.bib_path = os.path.join(self.base_dir, f"{db_name_without_extension}.bib")

    @staticmethod
    def generate_timestamp():
        """
        Gera uma string de timestamp no formato 'AAAA-MM-DD-HH-MM-SS'.

        Retorna:
        str: Timestamp formatado como string.
        """
        now = datetime.now()
        return now.strftime("%Y-%m-%d-%H-%M-%S")

    def generate_dynamic_entries_section(self) -> str:
        """
        Gera a seção dinâmica de avisos e citações para o documento LaTeX, incluindo uma lista de fontes citadas.

        Retorna:
        str: String formatada contendo a seção de aviso e citações.
        """
        entry_keys = self.get_entry_keys()
        dynamic_section = "\\section{Aviso Importante}\n" \
                          "\\textbf{Este documento foi gerado usando processamento de linguística computacional auxiliado por inteligência artificial.}\n"
        
        # Adiciona as chaves de entrada, se disponíveis, formatadas para citações no LaTeX
        if entry_keys:
            dynamic_section += "Para tanto foram analisadas as seguintes fontes: "
            dynamic_section += ", ".join(f"\\cite{{{key}}}" for key in entry_keys)
            dynamic_section += ".\n"
        
        dynamic_section += "\\textbf{Portanto este conteúdo requer revisão humana, pois pode conter erros.} Decisões jurídicas, de saúde, financeiras ou similares " \
                           "não devem ser tomadas com base somente neste documento. A Ephor - Linguística Computacional não se responsabiliza " \
                           "por decisões ou outros danos oriundos da tomada de decisão sem a consulta dos devidos especialistas.\n" \
                           "A consulta da originalidade deste conteúdo para fins de verificação de plágio pode ser feita em " \
                           "\\href{http://www.ephor.com.br}{ephor.com.br}.\n"
        
        return dynamic_section

    def get_entry_keys(self):
        """
        Extrai todas as chaves de entrada do arquivo .bib para gerar citações no documento LaTeX.

        Retorna:
        List[str]: Lista das chaves das entradas encontradas no arquivo .bib.
        """
        if not os.path.exists(self.bib_path):
            logging.warning(f"Arquivo .bib não encontrado: {self.bib_path}")
            return []
        
        with open(self.bib_path, 'r', encoding='utf-8') as bib_file:
            bib_content = bib_file.read()

        entry_keys = re.findall(r'@[\w]+\{([^,]+),', bib_content)
        return entry_keys

    def create_tex_document(self, db_data: list) -> Document:
        """
        Cria um objeto Document do LaTeX a partir dos dados recuperados do banco de dados.
        
        Parâmetros:
        db_data (list): Lista contendo os dados de cada seção do documento.
        
        Retorna:
        Document: Documento LaTeX criado com todas as seções e entradas.
        """
        doc = Document()
        
        # Configurações iniciais, substituindo o conteúdo do arquivo ini_latex.txt
        title = db_data[0]
        doc.preamble.append(Command("title", escape_latex(title)))
        doc.preamble.append(Command("bibliography", os.path.splitext(self.bib_path)[0]))

        # Seção dinâmica de avisos
        with doc.create(Section("Aviso Importante")):
            doc.append(NoEscape(self.generate_dynamic_entries_section()))

        # Adiciona o conteúdo das outras seções
        sections = ["Relato", "Contexto", "Entidades", "Linha do Tempo", "Contradições", "Conclusão", "Questionário"]
        for section_title, content in zip(sections, db_data[1:]):
            with doc.create(Section(section_title)):
                doc.append(NoEscape(self.encoder.unicode_to_latex(content)))

        return doc

    def save_tex_file(self, doc: Document) -> str:
        """
        Salva o documento LaTeX gerado em um arquivo .tex no diretório de saída.

        Parâmetros:
        doc (Document): Documento LaTeX a ser salvo.

        Retorna:
        str: Caminho completo do arquivo .tex salvo.
        """
        timestamp = self.generate_timestamp()
        tex_file_path = os.path.join(self.base_dir, f"{timestamp}.tex")
        doc.generate_tex(tex_file_path)
        logging.info(f"Arquivo LaTeX salvo em: {tex_file_path}")
        return tex_file_path

    def compile_tex_to_pdf(self, tex_file_path: str) -> str:
        """
        Compila o arquivo .tex em um arquivo PDF usando pdflatex e retorna o caminho do PDF gerado.

        Parâmetros:
        tex_file_path (str): Caminho completo do arquivo .tex a ser compilado.

        Retorna:
        str: Caminho completo do arquivo PDF gerado ou uma string vazia em caso de erro.
        """
        try:
            subprocess.run(['pdflatex', '-output-directory', self.base_dir, tex_file_path], check=True)
            pdf_file_path = os.path.splitext(tex_file_path)[0] + ".pdf"
            
            if os.path.exists(pdf_file_path):
                print(f"PDF file generated: {pdf_file_path}")
                return pdf_file_path
            else:
                print(f"Erro: PDF não foi gerado.")
                return ""
        except subprocess.CalledProcessError as e:
            logging.error(f"Erro ao compilar o arquivo LaTeX: {e}")
            return ""

    def review_tex_content(self, tex_content: str, model="gpt-4-0125-preview") -> str:
        """
        Envia o conteúdo LaTeX para revisão por um modelo GPT e armazena o resultado em cache no banco de dados.

        Parâmetros:
        tex_content (str): Conteúdo LaTeX a ser revisado.
        model (str): Modelo GPT a ser utilizado para a revisão.

        Retorna:
        str: Conteúdo revisado após a análise do modelo GPT.
        """
        conn = sqlite3.connect(f'databases/{self.db_name}')
        cursor = conn.cursor()

        arg_hash = hashlib.sha256(tex_content.encode("utf-8")).hexdigest()
        cursor.execute(f'SELECT review_content FROM tex_reviews WHERE hash = ?', (arg_hash,))
        review = cursor.fetchone()

        if review:
            logging.info(f"Revisão encontrada em cache para hash {arg_hash}.")
            return review[0]

        prompt = f"Revisar o seguinte conteúdo gerado, garantindo consistência e correção:\n{tex_content}"
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=model
        )

        reviewed_content = response['choices'][0]['message']['content']

        cursor.execute(f"INSERT INTO tex_reviews (hash, review_content) VALUES (?, ?)", (arg_hash, reviewed_content))
        conn.commit()
        conn.close()

        return reviewed_content

    def generate_and_compile_document(self, db_data: list):
        """
        Gera um documento LaTeX a partir dos dados do banco, revisa o conteúdo, salva em um arquivo .tex e compila para PDF.

        Parâmetros:
        db_data (list): Lista contendo dados do banco que serão utilizados nas seções do documento.

        Retorna:
        str: Caminho completo do arquivo PDF gerado ou uma string vazia em caso de erro.
        """
        # Cria o documento LaTeX
        doc = self.create_tex_document(db_data)
        tex_file_path = self.save_tex_file(doc)
        
        # Faz a revisão do conteúdo LaTeX gerado
        reviewed_content = self.review_tex_content(tex_file_path)
        
        # Salva o conteúdo revisado antes de compilar
        with open(tex_file_path, 'w', encoding='utf-8') as f:
            f.write(reviewed_content)
        
        # Compila para PDF
        pdf_file_path = self.compile_tex_to_pdf(tex_file_path)
        return pdf_file_path
