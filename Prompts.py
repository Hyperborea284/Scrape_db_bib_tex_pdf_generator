from typing import List
import logging
from EntityProtoProcessor import EntityProtoProcessor
from DatabaseUtils import memoize_to_db, DatabaseUtils

# Configuração do logger para registrar eventos e erros em 'Prompts.log'
logging.basicConfig(
    filename='Prompts.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class PromptProcessor:
    def __init__(self, db_name: str):
        """
        Inicializa o processador de prompts, incluindo o EntityProtoProcessor e a integração com o banco de dados.

        Parâmetros:
        db_name (str): Nome do banco de dados a ser utilizado.
        """
        self.db_utils = DatabaseUtils(db_name)
        self.entity_processor = EntityProtoProcessor()

    def _generate_prompt_with_entities(self, section_name: str, texts: List[str], description: str, sources: List[str]) -> str:
        """
        Gera o prompt completo, incluindo a análise de entidades e fontes.
        """
        try:
            combined_text = " ".join(texts)
            logging.info(f"Texto combinado para '{section_name}': {combined_text}")
    
            processed_result = self.entity_processor.process_text(combined_text)
            entities = processed_result.get("entities", [])
            logging.info(f"Entidades identificadas para '{section_name}': {entities}")
    
            entities_info = (
                "\n".join([f"- {entity}" for entity in entities])
                if entities
                else "Nenhuma entidade identificada."
            )
            sources_info = (
                "\n".join([f"- {source}" for source in sources])
                if sources
                else "Nenhuma fonte disponível."
            )
    
            prompt = f"""
    Seção: {section_name}
    Descrição: {description}
    Entidades identificadas no texto:
    {entities_info}
    Fontes utilizadas:
    {sources_info}
    
    Gere um resumo considerando apenas as informações disponíveis acima.
    """
            logging.info(f"Prompt gerado para '{section_name}': {prompt.strip()}")
            return prompt.strip()
        except Exception as e:
            logging.error(f"Erro ao gerar prompt para '{section_name}': {e}")
            return ""

    @memoize_to_db(table_name="relato")
    def relato(self, texts: List[str], sources: List[str]) -> str:
        """
        Gera um resumo do tipo 'relato' baseado nos textos fornecidos.

        Parâmetros:
        texts (List[str]): Lista de textos a serem resumidos.
        sources (List[str]): Lista de fontes associadas.

        Retorna:
        str: Resumo gerado para o tipo 'relato'.
        """
        description = "Resumo do tipo 'relato' que destaca os principais eventos ou pontos mencionados."
        return self._generate_prompt_with_entities("Relato", texts, description, sources)

    @memoize_to_db(table_name="entidades")
    def entidades(self, texts: List[str], sources: List[str]) -> str:
        """
        Gera um resumo com foco na análise de entidades, como pessoas e organizações.

        Parâmetros:
        texts (List[str]): Lista de textos para serem resumidos.
        sources (List[str]): Lista de fontes associadas.

        Retorna:
        str: Resumo gerado para a seção 'entidades'.
        """
        description = "Resumo que apresenta as principais entidades mencionadas, incluindo pessoas, organizações e locais."
        return self._generate_prompt_with_entities("Entidades", texts, description, sources)

    @memoize_to_db(table_name="contexto")
    def contexto(self, texts: List[str], sources: List[str]) -> str:
        """
        Gera um resumo apresentando o contexto geral e elementos contextuais.

        Parâmetros:
        texts (List[str]): Lista de textos para serem resumidos.
        sources (List[str]): Lista de fontes associadas.

        Retorna:
        str: Resumo gerado para a seção 'contexto'.
        """
        description = "Resumo que apresenta o contexto geral, elementos contextuais e casuística analisada."
        return self._generate_prompt_with_entities("Contexto", texts, description, sources)

    @memoize_to_db(table_name="linha_tempo")
    def linha_tempo(self, texts: List[str], sources: List[str]) -> str:
        """
        Gera um resumo apresentando as linhas do tempo deduzidas ou mencionadas.

        Parâmetros:
        texts (List[str]): Lista de textos para serem resumidos.
        sources (List[str]): Lista de fontes associadas.

        Retorna:
        str: Resumo gerado para a seção 'linha do tempo'.
        """
        description = "Resumo detalhado das sequências temporais e eventos apresentados."
        return self._generate_prompt_with_entities("Linha do Tempo", texts, description, sources)

    @memoize_to_db(table_name="contradicoes")
    def contradicoes(self, texts: List[str], sources: List[str]) -> str:
        """
        Gera um resumo das contradições, polarizações e tensões dialéticas presentes nos textos.

        Parâmetros:
        texts (List[str]): Lista de textos para serem resumidos.
        sources (List[str]): Lista de fontes associadas.

        Retorna:
        str: Resumo gerado para a seção 'contradições'.
        """
        description = "Resumo das contradições, polarizações e tensões dialéticas identificadas."
        return self._generate_prompt_with_entities("Contradições", texts, description, sources)

    @memoize_to_db(table_name="conclusao")
    def conclusao(self, texts: List[str], sources: List[str]) -> str:
        """
        Gera um resumo apresentando as conclusões sintéticas dos conteúdos.

        Parâmetros:
        texts (List[str]): Lista de textos para serem resumidos.
        sources (List[str]): Lista de fontes associadas.

        Retorna:
        str: Resumo gerado para a seção 'conclusão'.
        """
        description = "Resumo conclusivo com atenção às implicações dos temas abordados."
        return self._generate_prompt_with_entities("Conclusão", texts, description, sources)
