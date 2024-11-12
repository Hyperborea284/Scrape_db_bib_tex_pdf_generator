import sqlite3
import os
from typing import Any, Tuple, List, Optional
import logging

# Configuração do logger para registrar eventos e erros no arquivo 'DatabaseUtils.log'
logging.basicConfig(filename='DatabaseUtils.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

class DatabaseUtils:
    def __init__(self, db_name: str = "database.db"):
        """
        Inicializa a classe DatabaseUtils e configura o caminho do banco de dados SQLite.
        
        Parâmetros:
        db_name (str): O nome do arquivo do banco de dados.
        """
        self.db_name = db_name
        self.db_path = os.path.join("databases", self.db_name)
        os.makedirs("databases", exist_ok=True)  # Cria o diretório 'databases' se ele não existir
        self._initialize_database()  # Chama o método privado para inicializar o banco de dados

    def _initialize_database(self):
        """
        Cria o banco de dados e as tabelas necessárias, caso elas ainda não existam.

        Este método configura as tabelas `links`, `metaresumo`, e várias tabelas de memoização 
        (`relato`, `contexto`, etc.) para armazenamento de resumos específicos gerados por diferentes modelos.
        """
        self.create_table_links()  # Tabela para armazenamento de links e informações associadas
        self.create_table_memoization("relato")
        self.create_table_memoization("contexto")
        self.create_table_memoization("entidades")
        self.create_table_memoization("linha_tempo")
        self.create_table_memoization("contradicoes")
        self.create_table_memoization("conclusao")
        self.create_table_memoization("questionario")
        self.create_table_metaresumo()  # Tabela para armazenamento de resumos agregados

    def connect(self) -> sqlite3.Connection:
        """
        Conecta ao banco de dados e retorna o objeto de conexão.

        Retorna:
        sqlite3.Connection: O objeto de conexão ao banco de dados SQLite.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            return conn
        except sqlite3.Error as e:
            print(f"Erro ao conectar ao banco de dados: {e}")
            raise

    def disconnect(self, conn: sqlite3.Connection):
        """
        Desconecta do banco de dados, com commit automático das operações pendentes.

        Parâmetros:
        conn (sqlite3.Connection): O objeto de conexão ao banco de dados.
        """
        if conn:
            conn.commit()  # Salva as operações pendentes
            conn.close()  # Fecha a conexão

    def execute_query(self, query: str, params: Tuple[Any, ...] = ()) -> Optional[List[Tuple]]:
        """
        Executa uma consulta SQL no banco de dados e retorna o resultado.

        Parâmetros:
        query (str): A instrução SQL a ser executada.
        params (Tuple[Any, ...]): Os parâmetros a serem usados na consulta, se houver.

        Retorna:
        Optional[List[Tuple]]: O resultado da consulta, ou None em caso de erro.
        """
        conn = self.connect()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Erro ao executar consulta: {e}")
            return None
        finally:
            self.disconnect(conn)

    def create_table_links(self):
        """
        Cria a tabela `links` para armazenar as informações extraídas dos links, caso não exista.

        Esta tabela armazena dados como o link original, texto limpo, autores, domínio,
        data de publicação, descrição, título, tags, schema, e opengraph.
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
        self.execute_query(query)

    def create_table_memoization(self, table_name: str):
        """
        Cria uma tabela de memoização para armazenar resumos de uma seção específica.

        Parâmetros:
        table_name (str): O nome da tabela que será criada para armazenamento de resumos.
        
        Exemplo:
        Tabelas podem incluir `relato`, `contexto`, `entidades`, etc., cada uma delas 
        contendo colunas para armazenar resumos dos modelos GPT-3 e GPT-4.
        """
        query = f'''
            CREATE TABLE IF NOT EXISTS {table_name} (
                hash_gpt3 TEXT PRIMARY KEY,
                summary_gpt3 TEXT,
                hash_gpt4 TEXT,
                summary_gpt4 TEXT
            )
        '''
        self.execute_query(query)

    def create_table_metaresumo(self):
        """
        Cria a tabela `metaresumo` para armazenar informações agregadas dos resumos.

        Esta tabela é utilizada para armazenar dados de resumos completos, incluindo
        links agregados e o resumo resultante.
        """
        query = '''
            CREATE TABLE IF NOT EXISTS metaresumo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT,
                aggregate_links TEXT,
                resume TEXT
            )
        '''
        self.execute_query(query)

    def insert_link(self, link_data: dict) -> bool:
        """
        Insere um link e suas informações associadas na tabela `links`.

        Parâmetros:
        link_data (dict): Um dicionário contendo os dados do link a serem inseridos.

        Retorna:
        bool: `True` se a inserção for bem-sucedida, `False` caso contrário.
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
            link_data.get("opengraph")
        )
        result = self.execute_query(query, params)
        return result is not None

    def insert_memoization(self, table_name: str, hash_value: str, summary: str, model: str):
        """
        Insere um resumo memoizado na tabela específica, associando-o a um hash e modelo específico.

        Parâmetros:
        table_name (str): O nome da tabela onde o resumo será inserido.
        hash_value (str): O valor hash do conteúdo, usado para verificação de memoização.
        summary (str): O conteúdo do resumo.
        model (str): O modelo utilizado para gerar o resumo (`gpt-3` ou `gpt-4`).
        """
        column = "summary_gpt3" if model == "gpt-3" else "summary_gpt4"
        hash_column = "hash_gpt3" if model == "gpt-3" else "hash_gpt4"
        query = f'''
            INSERT OR IGNORE INTO {table_name} ({hash_column}, {column})
            VALUES (?, ?)
        '''
        params = (hash_value, summary)
        self.execute_query(query, params)

    def retrieve_memoization(self, table_name: str, hash_value: str, model: str) -> Optional[str]:
        """
        Recupera um resumo memoizado com base no hash e no modelo especificado.

        Parâmetros:
        table_name (str): O nome da tabela onde buscar o resumo.
        hash_value (str): O valor hash do conteúdo.
        model (str): O modelo usado para gerar o resumo (`gpt-3` ou `gpt-4`).

        Retorna:
        Optional[str]: O resumo memoizado, ou `None` se não encontrado.
        """
        column = "summary_gpt3" if model == "gpt-3" else "summary_gpt4"
        hash_column = "hash_gpt3" if model == "gpt-3" else "hash_gpt4"
        query = f'SELECT {column} FROM {table_name} WHERE {hash_column} = ?'
        result = self.execute_query(query, (hash_value,))
        return result[0][0] if result else None

    def insert_metaresumo(self, data: str, aggregate_links: str, resume: str) -> bool:
        """
        Insere um metaresumo na tabela `metaresumo`.

        Parâmetros:
        data (str): A data da inserção.
        aggregate_links (str): Uma string com links agregados ou informações associadas.
        resume (str): O resumo agregado.

        Retorna:
        bool: `True` se a inserção for bem-sucedida, `False` caso contrário.
        """
        query = '''
            INSERT INTO metaresumo (data, aggregate_links, resume)
            VALUES (?, ?, ?)
        '''
        params = (data, aggregate_links, resume)
        result = self.execute_query(query, params)
        return result is not None

    def fetch_all_links(self) -> List[Tuple]:
        """
        Recupera todos os links e suas informações da tabela `links`.

        Retorna:
        List[Tuple]: Uma lista de tuplas com os dados dos links.
        """
        query = 'SELECT * FROM links'
        return self.execute_query(query) or []

    def fetch_summary_by_section(self, section_name: str) -> List[Tuple]:
        """
        Recupera todos os resumos de uma seção específica, como `relato` ou `contexto`.

        Parâmetros:
        section_name (str): O nome da seção cujos resumos serão recuperados.

        Retorna:
        List[Tuple]: Uma lista de tuplas contendo os resumos da seção especificada.
        """
        query = f'SELECT * FROM {section_name}'
        return self.execute_query(query) or []
