Responda em português. Em todas as alterações que forem sugeridas, obrigatoriamente:

Altere somente o mínimo estritamente necessário e preserve todas as outras estruturas,  funcionalidades, características, estruturas lógicas, roteamentos, ativações, importações, comentários, doctrings, namespaces.

Considere estas versões destes scripts e garanta as convergências durante as alterações adiante.

Sempre preserve as características visando garantir a plena e completa, convergente funcionalidade de manipulação nessas operações envolvendo os links, e o db se assegure de que todas as operações sejam preservadas.

Em caso nenhum, nunca, remova ou omita funcionalidades. 

Apenas sintetize estas funcionalidades quando necessário, preserve todas as funcionalidades. 

Não altere nada nos caminhos para os bancos de dados e outros filepaths.

Somente apresente a correção convergente, a qual garanta que a ativação sequencial destas instruções seja capaz de preservar todas as funcionalidades propostas.

Reescreva as versões dos arquivos para incorporar as alterações propostas e apresente a  versão completa e corrigida do script para fins de teste.  

Aguarde a que o problema seja apresentado antes de sugerir alterações.

No presente momento a ativação dos prompts não está ocorrendo corretamente devido à um erro com a indexação das tuplas extraídas do db. A partir de agora, os trechos registrados na coluna cleaned text da tabela links devem conter, desde sua população, as strings extraídas pelo goose. Partindo daí, todas as operações seguintes que se baseiam nessas strings devem usar strings para montar o prompt, ativar a api e registrar o retorno da api, nas tabelas do db. Todas as operações envolvendo tuplas, no contexto desse fluxo de trabalho, devem ser substituídas por operações equivalentes usando strings.  Remova as operações de validação das strings, as quais podem eliminar conteúdos que serão repassados ao prompt; todos os conteúdos da coluna cleaned text, na forma de strings, devem ser usados para compor o prompt.    

preserve
memoize_to_db
decorator
wrapped
DatabaseUtils
_initialize_database
connect
disconnect
create_table_links
create_table_bib_references
create_summary_tables
execute_query
insert_link
insert_summary
fetch_cleaned_texts
create_and_populate_references_table
LinkManager
is_valid_url
fetch_and_store_link
remove_all_links
get_all_links
clean_old_links
get_link_data
register_multiple_links
fetch_link_data
delete_link
update_link_data
fetch_links_by_domain


Main
escolher_ou_criar_banco
atualizar_banco
limpar_tela
exibir_logo
loop_inserir_links
remover_link_especifico
gerar_pdf
consultar_db_llama
menu_principal
iniciar

PDFGenerator
generate_timestamp
compile_tex_to_pdf
cleanup_auxiliary_files
move_pdf_to_output
open_pdf_with_okular
generate_and_compile_pdf

SummarizerManager
synthesize_content
get_token_price
display_cost_estimate
_generate_summary
split_message_into_sections
process_remaining_sections
generate_response


PromptProcessor
_generate_prompt_with_entities
relato
entidades
contexto
linha_tempo
contradicoes
conclusao

TexGenerator
generate_timestamp
fetch_summaries_and_sources
create_tex_document
save_files
compile_tex_to_pdf
cleanup_auxiliary_files
generate_and_compile_document









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
        timestamp = self.generate_timestamp()
        
        if summaries is None or bib_content is None:
            summaries, bib_content = self.fetch_summaries_and_sources()
    
        if not summaries:
            logging.error("Nenhum resumo disponível para gerar o documento.")
            return ""
    
        tex_file_path, bib_file_path = self.save_files(
            Document().dumps(), bib_content, timestamp
        )
    
        pdf_file_path = self.compile_tex_to_pdf(tex_file_path)
        if pdf_file_path:
            self.cleanup_auxiliary_files(tex_file_path)
        return pdf_file_path
