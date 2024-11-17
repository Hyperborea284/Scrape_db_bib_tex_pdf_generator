import hashlib
import sqlite3
import os
from typing import List, Optional, Dict, Tuple
from openai import OpenAI
from functools import wraps
from DatabaseUtils import DatabaseUtils
from dotenv import load_dotenv
import logging
from Prompts import PromptProcessor

# Configuração do logger
logging.basicConfig(filename='SummarizerManager.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Carrega as variáveis de ambiente do arquivo .env
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
        self.prompts = PromptProcessor(db_name)
        self.client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        self.db_name = db_name

        # Garante que as tabelas necessárias estão criadas
        self.db_utils.create_summary_tables()

        # Configurações dos modelos e seus limites de contexto e tokens
        self.model_name_gpt3 = "gpt-3.5-turbo-1106"
        self.model_name_gpt4 = "gpt-4-0125-preview"
        self.context_gpt3 = 16385
        self.context_gpt4 = 128000
        self.requests_per_minute_limit = {self.model_name_gpt3: 5000, self.model_name_gpt4: 500}
        self.tokens_per_minute_limit = {self.model_name_gpt3: 80000, self.model_name_gpt4: 450000}
        self.total_tokens_used = {self.model_name_gpt3: 0, self.model_name_gpt4: 0}
        self.target_summary_size = 4096

    def synthesize_content(self) -> List[str]:
        """
        Faz a síntese de conteúdo para diferentes tipos de resumos e armazena no banco de dados.

        Retorna:
        List[str]: Lista de resumos gerados.
        """
        summaries = []
        try:
            # Recupera os textos limpos dos links para a síntese
            all_entries = self.db_utils.fetch_cleaned_texts()
            entries = [entry[0] for entry in all_entries] if all_entries else []

            # Gera os resumos para cada seção usando o PromptProcessor
            for prompt_name in ["relato", "contexto", "entidades", "linha_tempo", "contradicoes", "conclusao"]:
                method = getattr(self.prompts, prompt_name)
                summary = method(entries)
                summaries.append(summary)

                # Salva apenas os novos resumos
                if summary:
                    self.db_utils.insert_summary(prompt_name, summary)
        except sqlite3.Error as e:
            logging.error(f"Erro no banco de dados durante a síntese: {e}")
        except Exception as e:
            logging.error(f"Erro geral ao sintetizar conteúdo: {e}")
        return summaries

    def get_token_price(self) -> float:
        """
        Verifica o preço atual dos tokens da API e retorna o valor em dólares por 1000 tokens.

        Retorna:
        float: Preço por 1000 tokens.
        """
        try:
            response = requests.get("https://api.openai.com/v1/pricing")
            response.raise_for_status()
            pricing_data = response.json()
            price_per_1000_tokens = pricing_data.get("usd_per_1000_tokens", {}).get(self.model_name_gpt3, 0.02)
            return price_per_1000_tokens
        except requests.RequestException as e:
            logging.error(f"Erro ao obter o preço dos tokens: {e}")
            return 0.02

    def display_cost_estimate(self, token_count: int) -> bool:
        """
        Calcula e exibe uma estimativa de custo baseado no número de tokens e solicita confirmação do usuário.

        Parâmetros:
        token_count (int): Número de tokens estimados.

        Retorna:
        bool: True se o usuário confirmar a continuidade, False caso contrário.
        """
        token_price = self.get_token_price()
        estimated_cost = (token_count / 1000) * token_price
        print(f"\n=== Estimativa de Custo ===")
        print(f"Tokens estimados: {token_count}")
        print(f"Custo estimado: ${estimated_cost:.4f}")
        confirm = input("Deseja continuar com a geração do resumo? (s/n): ").lower()
        return confirm == 's'

    def _generate_summary(self, section_name: str, texts: List[str], description: str) -> str:
        """
        Gera um resumo baseado em uma lista de textos e uma descrição do tipo de resumo.

        Parâmetros:
        section_name (str): Nome da seção.
        texts (List[str]): Lista de textos.
        description (str): Descrição do tipo de resumo.

        Retorna:
        str: Resumo gerado.
        """
        try:
            messages = [{"role": "user", "content": f"Provide a {description} for the following texts:"}]
            for text in texts:
                messages.append({"role": "user", "content": text.strip()})

            sections, remaining_sections = self.split_message_into_sections(messages)
            estimated_tokens = sum(len(msg["content"].split()) for msg in sections)
            if not self.display_cost_estimate(estimated_tokens):
                logging.info("Operação cancelada pelo usuário.")
                return ""

            summary_text = self.generate_response(sections)

            if remaining_sections:
                self.process_remaining_sections(remaining_sections, section_name)

            return summary_text
        except Exception as e:
            logging.error(f"Erro ao gerar resumo para {section_name}: {e}")
            return ""

    def split_message_into_sections(self, messages: List[Dict[str, str]]) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
        """
        Divide mensagens em seções com base no limite de tokens.

        Parâmetros:
        messages (List[Dict[str, str]]): Mensagens a serem enviadas.

        Retorna:
        Tuple[List[Dict[str, str]], List[Dict[str, str]]]: Seção principal e excedente.
        """
        total_tokens, max_tokens = 0, self.context_gpt3
        primary_section, overflow_section = [], []

        for message in messages:
            token_count = len(message["content"].split())
            if total_tokens + token_count <= max_tokens:
                primary_section.append(message)
                total_tokens += token_count
            else:
                overflow_section.append(message)

        return primary_section, overflow_section

    def process_remaining_sections(self, sections: List[Dict[str, str]], section_name: str) -> None:
        """
        Processa e memoiza as seções que excedem o limite.

        Parâmetros:
        sections (List[Dict[str, str]]): Lista de mensagens excedentes.
        section_name (str): Nome da seção.
        """
        for section in sections:
            method = getattr(self.prompts, section_name)
            method([section["content"]])

    def generate_response(self, messages: List[Dict[str, str]]) -> str:
        """
        Envia solicitação para a API OpenAI para gerar o resumo.

        Parâmetros:
        messages (List[Dict[str, str]]): Mensagens para enviar.

        Retorna:
        str: Conteúdo do resumo gerado.
        """
        try:
            response = self.client.chat.completions.create(
                messages=messages,
                model=self.model_name_gpt3,
                max_tokens=self.target_summary_size
            )
            return response['choices'][0]['message']['content']
        except Exception as e:
            logging.error(f"Erro ao gerar resposta da API: {e}")
            return ""
