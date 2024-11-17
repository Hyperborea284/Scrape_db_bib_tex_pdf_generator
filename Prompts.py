from typing import List
import logging
from EntityProtoProcessor import EntityProtoProcessor
from DatabaseUtils import memoize_to_db, DatabaseUtils

# Configuração do logger para registrar eventos e erros em 'Prompts.log'
logging.basicConfig(filename='Prompts.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

class PromptProcessor:
    def __init__(self, db_name: str):
        """
        Inicializa o processador de prompts, incluindo o EntityProtoProcessor e a integração com o banco de dados.

        Parâmetros:
        db_name (str): Nome do banco de dados a ser utilizado.
        """
        self.db_utils = DatabaseUtils(db_name)
        self.entity_processor = EntityProtoProcessor()

    def _generate_prompt_with_entities(self, section_name: str, texts: List[str], description: str) -> str:
        """
        Gera o prompt completo, incluindo a análise de entidades extraídas.

        Parâmetros:
        section_name (str): Nome da seção para identificar o tipo de resumo.
        texts (List[str]): Lista de textos a serem processados.
        description (str): Descrição que define o foco do resumo.

        Retorna:
        str: Prompt gerado.
        """
        # Combina os textos para análise de entidades
        combined_text = " ".join(texts)
        entities, _, _, _ = self.entity_processor.extract_entities(combined_text)

        # Formata as entidades como parte do prompt
        entities_info = "\n".join([f"- {entity[0]} ({entity[1]})" for entity in entities])
        entities_section = f"\nEntidades identificadas no texto:\n{entities_info}" if entities else "\nNenhuma entidade identificada."

        # Monta o prompt final
        prompt = f"""
Seção: {section_name}
Descrição: {description}
{entities_section}

Texto de entrada:
{combined_text}
"""
        logging.info(f"Prompt gerado para '{section_name}': {prompt}")
        return prompt.strip()

    @memoize_to_db(table_name="relato")
    def relato(self, texts: List[str]) -> str:
        """
        Gera um resumo do tipo 'relato' baseado nos textos fornecidos.
        
        Parâmetros:
        texts (List[str]): Lista de textos a serem resumidos.
        
        Retorna:
        str: Resumo gerado para o tipo 'relato'.
        """
        description = "Resumo do tipo 'relato' que destaca os principais eventos ou pontos mencionados."
        return self._generate_prompt_with_entities("Relato", texts, description)

    @memoize_to_db(table_name="entidades")
    def entidades(self, texts: List[str]) -> str:
        """
        Gera um resumo com foco na análise de entidades, como pessoas e organizações.

        Parâmetros:
        texts (List[str]): Lista de textos para serem resumidos.

        Retorna:
        str: Resumo gerado para a seção 'entidades'.
        """
        description = "Resumo que apresenta as principais entidades mencionadas, incluindo pessoas, organizações e locais."
        return self._generate_prompt_with_entities("Entidades", texts, description)

    @memoize_to_db(table_name="contexto")
    def contexto(self, texts: List[str]) -> str:
        """
        Gera um resumo apresentando o contexto geral e elementos contextuais.

        Parâmetros:
        texts (List[str]): Lista de textos para serem resumidos.

        Retorna:
        str: Resumo gerado para a seção 'contexto'.
        """
        description = "Resumo que apresenta o contexto geral, elementos contextuais e casuística analisada."
        return self._generate_prompt_with_entities("Contexto", texts, description)

    @memoize_to_db(table_name="linha_tempo")
    def linha_tempo(self, texts: List[str]) -> str:
        """
        Gera um resumo apresentando as linhas do tempo deduzidas ou mencionadas.

        Parâmetros:
        texts (List[str]): Lista de textos para serem resumidos.

        Retorna:
        str: Resumo gerado para a seção 'linha do tempo'.
        """
        description = "Resumo detalhado das sequências temporais e eventos apresentados."
        return self._generate_prompt_with_entities("Linha do Tempo", texts, description)

    @memoize_to_db(table_name="contradicoes")
    def contradicoes(self, texts: List[str]) -> str:
        """
        Gera um resumo das contradições, polarizações e tensões dialéticas presentes nos textos.

        Parâmetros:
        texts (List[str]): Lista de textos para serem resumidos.

        Retorna:
        str: Resumo gerado para a seção 'contradições'.
        """
        description = "Resumo das contradições, polarizações e tensões dialéticas identificadas."
        return self._generate_prompt_with_entities("Contradições", texts, description)

    @memoize_to_db(table_name="conclusao")
    def conclusao(self, texts: List[str]) -> str:
        """
        Gera um resumo apresentando as conclusões sintéticas dos conteúdos.

        Parâmetros:
        texts (List[str]): Lista de textos para serem resumidos.

        Retorna:
        str: Resumo gerado para a seção 'conclusão'.
        """
        description = "Resumo conclusivo com atenção às implicações dos temas abordados."
        return self._generate_prompt_with_entities("Conclusão", texts, description)
