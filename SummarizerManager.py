import hashlib
import sqlite3
import os
from typing import List, Optional, Dict, Tuple
from openai import OpenAI
from functools import wraps
from database_utils import DatabaseUtils
from dotenv import load_dotenv
import logging

# Configuração do logger para registrar eventos e erros em 'SummarizerManager.log'
logging.basicConfig(filename='SummarizerManager.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Carregar variáveis de ambiente do arquivo .env
load_dotenv(".env")

class SummarizerManager:
    def __init__(self, db_name: str):
        """
        Inicializa o SummarizerManager, que gerencia a síntese de textos e a integração com o banco de dados 
        e a API OpenAI.

        Parâmetros:
        db_name (str): Nome do banco de dados SQLite onde os resumos e links são armazenados.
        """
        self.db_utils = DatabaseUtils(db_name)
        self.client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        self.db_name = db_name
        # Configurações dos modelos e seus limites de contexto e tokens
        self.model_name_gpt3 = "gpt-3.5-turbo-1106"
        self.model_name_gpt4 = "gpt-4-0125-preview"
        self.context_gpt3 = 16385
        self.context_gpt4 = 128000
        self.requests_per_minute_limit = {self.model_name_gpt3: 5000, self.model_name_gpt4: 500}
        self.tokens_per_minute_limit = {self.model_name_gpt3: 80000, self.model_name_gpt4: 450000}
        self.total_tokens_used = {self.model_name_gpt3: 0, self.model_name_gpt4: 0}
        self.target_summary_size = 4096

    def memoize_to_db(table_name: str):
        """
        Decorador para memoizar o resultado de uma função no banco de dados, evitando chamadas repetidas à API.

        Parâmetros:
        table_name (str): Nome da tabela onde o resultado da função será armazenado.
        """
        def decorator(func):
            @wraps(func)
            def wrapped(self, *args, **kwargs):
                # Criação de um hash dos argumentos para uso na memoização
                arg_hash = hashlib.sha256(str(args).encode('utf-8')).hexdigest()
                conn = sqlite3.connect(f'databases/{self.db_name}')
                cursor = conn.cursor()
                
                # Verifica no banco de dados se o resumo já foi memoizado
                cursor.execute(f"SELECT summary_gpt3 FROM {table_name} WHERE hash_gpt3 = ?", (arg_hash,))
                row = cursor.fetchone()
                
                if row:
                    print(f"Memoization hit for {table_name}.")
                    return row[0]
                
                # Gera o resumo e salva no banco caso não haja memoização prévia
                print(f"Memoization miss for {table_name}. Generating summary.")
                result = func(self, *args, **kwargs)
                if result:
                    cursor.execute(f"INSERT INTO {table_name} (hash_gpt3, summary_gpt3) VALUES (?, ?)", (arg_hash, result))
                    conn.commit()
                conn.close()
                return result
            return wrapped
        return decorator

    def synthesize_content(self) -> List[str]:
        """
        Faz a síntese de conteúdo para diferentes tipos de resumos (relato, contexto, entidades, etc.) e 
        armazena cada resumo no banco de dados.

        Retorna:
        List[str]: Uma lista de resumos gerados para cada tipo de conteúdo.
        """
        summaries = []
        try:
            # Recupera os textos limpos dos links para a síntese
            all_entries = self.db_utils.fetch_cleaned_texts()
            entries = [entry[0] for entry in all_entries] if all_entries else []
            
            # Gera os resumos para cada seção
            for prompt_name in ["relato", "contexto", "entidades", "linha_tempo", "contradicoes", "conclusao", "questionario"]:
                method = getattr(self, prompt_name)
                summary = method(entries)
                summaries.append(summary)
                
                # Armazena cada resumo no banco de dados
                self.db_utils.insert_summary(prompt_name, summary)
        except Exception as e:
            print(f"Error synthesizing content: {e}")
        return summaries

    @memoize_to_db(table_name="relato")
    def relato(self, texts: List[str]) -> str:
        """
        Gera um resumo detalhado com base em uma análise temática.

        Parâmetros:
        texts (List[str]): Lista de textos para serem resumidos.

        Retorna:
        str: Resumo gerado para a seção 'relato'.
        """
        return self._generate_summary("relato", texts, "Detailed report based on thematic analysis")

    @memoize_to_db(table_name="contexto")
    def contexto(self, texts: List[str]) -> str:
        """
        Gera um resumo que fornece o contexto geral e informações de fundo.

        Parâmetros:
        texts (List[str]): Lista de textos para serem resumidos.

        Retorna:
        str: Resumo gerado para a seção 'contexto'.
        """
        return self._generate_summary("contexto", texts, "Contextual background analysis")

    @memoize_to_db(table_name="entidades")
    def entidades(self, texts: List[str]) -> str:
        """
        Gera um resumo com foco na análise de entidades, como pessoas e organizações.

        Parâmetros:
        texts (List[str]): Lista de textos para serem resumidos.

        Retorna:
        str: Resumo gerado para a seção 'entidades'.
        """
        return self._generate_summary("entidades", texts, "Entities analysis with focus on individuals, organizations, and subjects")

    @memoize_to_db(table_name="linha_tempo")
    def linha_tempo(self, texts: List[str]) -> str:
        """
        Gera um resumo com base na sequência lógica de eventos.

        Parâmetros:
        texts (List[str]): Lista de textos para serem resumidos.

        Retorna:
        str: Resumo gerado para a seção 'linha_tempo'.
        """
        return self._generate_summary("linha_tempo", texts, "Timeline with logical event sequences")

    @memoize_to_db(table_name="contradicoes")
    def contradicoes(self, texts: List[str]) -> str:
        """
        Gera um resumo sobre contradições e tensões dialéticas encontradas nos textos.

        Parâmetros:
        texts (List[str]): Lista de textos para serem resumidos.

        Retorna:
        str: Resumo gerado para a seção 'contradicoes'.
        """
        return self._generate_summary("contradicoes", texts, "Contradictions, polarizations, and dialectical tensions")

    @memoize_to_db(table_name="conclusao")
    def conclusao(self, texts: List[str]) -> str:
        """
        Gera um resumo conclusivo que sintetiza os temas e implicações abordados.

        Parâmetros:
        texts (List[str]): Lista de textos para serem resumidos.

        Retorna:
        str: Resumo gerado para a seção 'conclusao'.
        """
        return self._generate_summary("conclusao", texts, "Synthesized conclusion of themes with implications")

    @memoize_to_db(table_name="questionario")
    def questionario(self, texts: List[str]) -> str:
        """
        Gera um questionário abrangente com base nos conteúdos dos textos.

        Parâmetros:
        texts (List[str]): Lista de textos para serem resumidos.

        Retorna:
        str: Questionário gerado para a seção 'questionario'.
        """
        return self._generate_summary("questionario", texts, "Comprehensive questionnaire based on content, with high-level questions")

    def _generate_summary(self, section_name: str, texts: List[str], description: str) -> str:
        """
        Gera um resumo baseado em uma lista de textos e uma descrição do tipo de resumo a ser gerado,
        fazendo uma chamada à API OpenAI para criar o resumo.

        Parâmetros:
        section_name (str): Nome da seção para memoização.
        texts (List[str]): Lista de textos a serem resumidos.
        description (str): Descrição do tipo de resumo para a API.

        Retorna:
        str: Resumo gerado para a seção específica.
        """
        try:
            messages = [{"role": "user", "content": f"Provide a {description} for the following texts:"}]
            for text in texts:
                messages.append({"role": "user", "content": text.strip()})
            
            # Divide as mensagens em seções dentro do limite de tokens
            sections, remaining_sections = self.split_message_into_sections(messages)
            
            # Gera o resumo principal
            summary_text = self.generate_response(sections)
            
            # Processa as seções que excederam o limite
            if remaining_sections:
                self.process_remaining_sections(remaining_sections, section_name)
            
            return summary_text
        except Exception as e:
            print(f"Error generating summary for {section_name}: {e}")
            return ""

    def split_message_into_sections(self, messages: List[Dict[str, str]]) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
        """
        Divide as mensagens em seções com base no limite de tokens, para evitar ultrapassar o limite permitido pela API.

        Parâmetros:
        messages (List[Dict[str, str]]): Lista de mensagens a serem enviadas para a API.

        Retorna:
        Tuple[List[Dict[str, str]], List[Dict[str, str]]]: Uma tupla contendo a seção principal e as mensagens excedentes.
        """
        total_tokens, max_tokens = 0, self.context_gpt3
        primary_section, overflow_section = [], []
        
        for message in messages:
            token_count = len(message["content"].split())  # Simplificação da contagem de tokens
            if total_tokens + token_count <= max_tokens:
                primary_section.append(message)
                total_tokens += token_count
            else:
                overflow_section.append(message)
        
        return primary_section, overflow_section

    def process_remaining_sections(self, sections: List[Dict[str, str]], section_name: str) -> None:
        """
        Processa e memoiza as seções que excedem o limite permitido pela API, evitando a perda de informações.

        Parâmetros:
        sections (List[Dict[str, str]]): Lista de mensagens excedentes.
        section_name (str): Nome da seção para identificar memoização.
        """
        for section in sections:
            method = getattr(self, section_name)
            method([section["content"]])

    def generate_response(self, messages: List[Dict[str, str]]) -> str:
        """
        Envia a solicitação para a API OpenAI para gerar o resumo baseado nas mensagens fornecidas.

        Parâmetros:
        messages (List[Dict[str, str]]): Mensagens para enviar à API.

        Retorna:
        str: O conteúdo do resumo gerado pela API.
        """
        try:
            response = self.client.chat.completions.create(
                messages=messages,
                model=self.model_name_gpt3,
                max_tokens=self.target_summary_size
            )
            return response['choices'][0]['message']['content']
        except Exception as e:
            print(f"Error generating response: {e}")
            return ""

    def remaining_tokens(self, model: str) -> int:
        """
        Calcula o número de tokens restantes para o modelo com base nos limites de requisições por minuto.

        Parâmetros:
        model (str): Nome do modelo (e.g., gpt-3 ou gpt-4).

        Retorna:
        int: Número de tokens restantes permitidos para o modelo.
        """
        requests_limit = self.requests_per_minute_limit.get(model, 0)
        tokens_used = self.total_tokens_used.get(model, 0)
        return max(0, requests_limit - tokens_used)
