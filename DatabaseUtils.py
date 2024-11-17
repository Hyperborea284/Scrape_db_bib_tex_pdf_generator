import sqlite3
import os
import re
import json
import logging
import hashlib
from typing import List, Dict, Optional, Any, Tuple
from functools import wraps
from datetime import datetime, timedelta
from goose3 import Goose
import requests

# Configuração do logger
logging.basicConfig(filename='DatabaseUtils.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def memoize_to_db(table_name: str):
    """
    Decorador para memoizar o resultado de uma função no banco de dados.
    """
    def decorator(func):
        @wraps(func)
        def wrapped(self, *args, **kwargs):
            db_utils = getattr(self, "db_utils", None)
            if db_utils is None or not hasattr(db_utils, "connect"):
                raise AttributeError("O objeto decorado deve possuir um atributo 'db_utils' com um método 'connect'.")

            prompt = str(args[0])
            prompt_hash = hashlib.sha256(prompt.encode('utf-8')).hexdigest()

            conn = db_utils.connect()
            cursor = conn.cursor()

            try:
                cursor.execute(f"SELECT summary_gpt3 FROM {table_name} WHERE hash_gpt3 = ?", (prompt_hash,))
                row = cursor.fetchone()
                if row:
                    logging.info(f"Memoization hit for {table_name} (hash: {prompt_hash}).")
                    return row[0]

                result = func(self, *args, **kwargs)
                if result:
                    cursor.execute(
                        f"INSERT INTO {table_name} (hash_gpt3, prompt, summary_gpt3) VALUES (?, ?, ?)",
                        (prompt_hash, prompt, result)
                    )
                    conn.commit()
                return result
            except sqlite3.Error as e:
                logging.error(f"Erro ao memoizar dados na tabela {table_name}: {e}")
                return None
            finally:
                db_utils.disconnect(conn)
        return wrapped
    return decorator

class DatabaseUtils:
    def __init__(self, db_name: str = "database.db"):
        """
        Inicializa o DatabaseUtils, garantindo que o banco seja criado no diretório correto.
        """
        self.base_dir = os.path.join(os.getcwd(), "databases")
        os.makedirs(self.base_dir, exist_ok=True)

        self.db_path = os.path.join(self.base_dir, os.path.basename(db_name))
        if not os.path.exists(self.db_path):
            logging.info(f"Criando banco de dados em: {self.db_path}")
            self._initialize_database()

    def _initialize_database(self):
        """
        Inicializa as tabelas necessárias.
        """
        with self.connect() as conn:
            self.create_table_links(conn)
            self.create_table_bib_references(conn)
            self.create_summary_tables()

    def connect(self) -> sqlite3.Connection:
        """
        Estabelece conexão.
        """
        return sqlite3.connect(self.db_path)

    def disconnect(self, conn: sqlite3.Connection):
        """
        Fecha conexão.
        """
        conn.commit()
        conn.close()

    def create_table_links(self, conn: sqlite3.Connection):
        """
        Cria tabela 'links'.
        """
        query = '''
        CREATE TABLE IF NOT EXISTS links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link TEXT UNIQUE,
            cleaned_text TEXT,
            authors TEXT,
            domain TEXT,
            publish_date TEXT,
            meta_description TEXT,
            title TEXT,
            tags TEXT,
            schema TEXT,
            opengraph TEXT
        )
        '''
        conn.execute(query)

    def create_table_bib_references(self, conn: sqlite3.Connection):
        """
        Cria tabela 'bib_references'.
        """
        query = '''
        CREATE TABLE IF NOT EXISTS bib_references (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT DEFAULT 'Autor Desconhecido',
            year INTEGER DEFAULT 0,
            journal TEXT DEFAULT 'Desconhecido',
            volume TEXT DEFAULT '',
            number TEXT DEFAULT '',
            pages TEXT DEFAULT '',
            doi TEXT DEFAULT '',
            url TEXT NOT NULL
        )
        '''
        conn.execute(query)

    def create_summary_tables(self):
        """
        Cria tabelas de resumo.
        """
        summary_tables = ["relato", "contexto", "entidades", "linha_tempo", "contradicoes", "conclusao"]
        with self.connect() as conn:
            for table in summary_tables:
                query = f'''
                CREATE TABLE IF NOT EXISTS {table} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    hash_gpt3 TEXT UNIQUE,
                    prompt TEXT NOT NULL,
                    summary_gpt3 TEXT
                )
                '''
                conn.execute(query)

    def execute_query(self, query: str, params: tuple = ()) -> List[tuple]:
        """
        Executa uma consulta.
        """
        conn = self.connect()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.fetchall()
        finally:
            self.disconnect(conn)

    def insert_link(self, link_data: dict) -> bool:
        """
        Insere link.
        """
        query = '''
        INSERT OR IGNORE INTO links (
            link, cleaned_text, authors, domain, publish_date,
            meta_description, title, tags, schema, opengraph
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        params = (
            link_data.get("link"),
            link_data.get("cleaned_text"),
            link_data.get("authors"),
            link_data.get("domain"),
            link_data.get("publish_date"),
            link_data.get("meta_description"),
            link_data.get("title"),
            link_data.get("tags"),
            link_data.get("schema"),
            link_data.get("opengraph"),
        )
        try:
            self.execute_query(query, params)
            logging.info(f"Link registrado com sucesso: {link_data['link']}")
            return True
        except sqlite3.Error as e:
            logging.error(f"Erro ao inserir o link no banco de dados: {e}")
            return False

    def insert_summary(self, table_name: str, summary: str) -> bool:
        """
        Insere resumo.
        """
        query = f'''
        INSERT INTO {table_name} (hash_gpt3, prompt, summary_gpt3)
        VALUES (?, ?, ?)
        '''
        hash_summary = hashlib.sha256(summary.encode('utf-8')).hexdigest()
        try:
            self.execute_query(query, (hash_summary, summary))
            return True
        except sqlite3.Error as e:
            logging.error(f"Erro ao inserir resumo na tabela {table_name}: {e}")
            return False

    def fetch_cleaned_texts(self) -> List[Tuple[str]]:
        """
        Busca textos limpos.
        """
        query = "SELECT cleaned_text FROM links WHERE cleaned_text IS NOT NULL"
        return self.execute_query(query)

    def create_and_populate_references_table(self):
        """
        Cria e popula tabela 'bib_references'.
        """
        conn = self.connect()
        try:
            self.create_table_bib_references(conn)
            links = conn.execute("SELECT id, meta_description, link FROM links").fetchall()

            for link in links:
                title = link[1] or "Título Desconhecido"
                url = link[2]
                conn.execute('''
                INSERT OR IGNORE INTO bib_references (id, title, url)
                VALUES (?, ?, ?)
                ''', (link[0], title, url))
            conn.commit()
            logging.info("Tabela 'bib_references' criada e populada com sucesso.")
        except sqlite3.Error as e:
            logging.error(f"Erro ao criar ou popular a tabela 'bib_references': {e}")
        finally:
            self.disconnect(conn)

class LinkManager:
    def __init__(self, db_name: str = "database.db"):
        """
        Inicializa o LinkManager, que gerencia os links no banco de dados.
        """
        self.db_utils = DatabaseUtils(db_name)
        self.goose = Goose()

    def is_valid_url(self, url: str) -> bool:
        """
        Valida um URL usando regex.
        """
        url_regex = re.compile(r'^(https?:\/\/)?([a-zA-Z0-9_\-]+\.)+[a-zA-Z]{2,}')
        return re.match(url_regex, url) is not None

    def fetch_and_store_link(self, url: str) -> bool:
        """
        Busca dados de um link e armazena no banco de dados.

        Parâmetros:
        url (str): URL do qual extrair os dados.

        Retorna:
        bool: True se os dados foram armazenados com sucesso, False caso contrário.
        """
        if not self.is_valid_url(url):
            logging.error(f"URL inválida: {url}")
            return False

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            article = self.goose.extract(url)

            if article.cleaned_text:
                # Normalização de publish_date
                publish_date = article.publish_date
                if isinstance(publish_date, list):
                    publish_date = publish_date[0]  # Usa o primeiro valor, se for uma lista

                link_data = {
                    "link": url,
                    "cleaned_text": article.cleaned_text,
                    "authors": ', '.join(article.authors) if article.authors else None,
                    "domain": article.domain,
                    "publish_date": publish_date or None,  # Garantir tipo compatível
                    "meta_description": article.meta_description,
                    "title": article.title,
                    "tags": ', '.join(article.tags) if article.tags else None,
                    "schema": json.dumps(article.schema) if article.schema else None,
                    "opengraph": json.dumps(article.opengraph) if article.opengraph else None,
                }
                return self.db_utils.insert_link(link_data)
            else:
                logging.warning(f"Falha ao extrair conteúdo limpo para o link: {url}")
                return False

        except requests.RequestException as e:
            logging.error(f"Erro ao acessar o link {url}: {e}")
        except Exception as e:
            logging.error(f"Erro ao processar o link {url}: {e}")

        return False

    def remove_all_links(self):
        """
        Remove todos os links armazenados no banco de dados.
        """
        self.db_utils.execute_query("DELETE FROM links")
        logging.info("Todos os links foram removidos com sucesso.")

    def get_all_links(self) -> List[Dict[str, Any]]:
        """
        Recupera todos os links armazenados no banco de dados.
        """
        rows = self.db_utils.execute_query("SELECT * FROM links")
        columns = ['id', 'link', 'cleaned_text', 'authors', 'domain', 'publish_date', 'meta_description', 'title', 'tags', 'schema', 'opengraph']
        return [dict(zip(columns, row)) for row in rows]

    def clean_old_links(self, days: int = 30) -> int:
        """
        Remove links com data de publicação mais antiga que o limite especificado.
        """
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        result = self.db_utils.execute_query("DELETE FROM links WHERE publish_date < ?", (cutoff_date,))
        return len(result)

    def get_link_data(self, url: str) -> dict:
        """
        Extrai dados de um link usando o Goose.
        """
        article = self.goose.extract(url)
        if article.cleaned_text:
            return {
                "link": url,
                "cleaned_text": article.cleaned_text,
                "authors": ', '.join(article.authors) if article.authors else None,
                "domain": article.domain,
                "publish_date": article.publish_date,
                "meta_description": article.meta_description,
                "title": article.title,
                "tags": ', '.join(article.tags) if article.tags else None,
                "schema": article.schema,
                "opengraph": article.opengraph,
            }
        raise ValueError("Nenhum texto limpo foi extraído do link.")

    def register_multiple_links(self, urls: List[str]) -> Dict[str, bool]:
        """
        Registra múltiplos links no banco de dados.
        """
        return {url: self.fetch_and_store_link(url) for url in urls}

    def fetch_link_data(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Busca dados de um link específico no banco de dados.
        """
        result = self.db_utils.execute_query("SELECT * FROM links WHERE link = ?", (url,))
        if result:
            columns = ['id', 'link', 'cleaned_text', 'authors', 'domain', 'publish_date', 'meta_description', 'title', 'tags', 'schema', 'opengraph']
            return dict(zip(columns, result[0]))
        return None

    def delete_link(self, url: str) -> bool:
        """
        Remove um link específico do banco de dados.
        """
        result = self.db_utils.execute_query("DELETE FROM links WHERE link = ?", (url,))
        return bool(result)

    def update_link_data(self, url: str, updated_data: Dict[str, Any]) -> bool:
        """
        Atualiza os dados de um link no banco de dados.
        """
        set_clause = ', '.join([f"{key} = ?" for key in updated_data.keys()])
        query = f"UPDATE links SET {set_clause} WHERE link = ?"
        params = tuple(updated_data.values()) + (url,)
        result = self.db_utils.execute_query(query, params)
        return bool(result)

    def fetch_links_by_domain(self, domain: str) -> List[Dict[str, Any]]:
        """
        Busca todos os links de um domínio específico no banco de dados.
        """
        rows = self.db_utils.execute_query("SELECT * FROM links WHERE domain = ?", (domain,))
        columns = ['id', 'link', 'cleaned_text', 'authors', 'domain', 'publish_date', 'meta_description', 'title', 'tags', 'schema', 'opengraph']
        return [dict(zip(columns, row)) for row in rows]
