import os
import re
import string
import logging
import spacy
import nltk
from langdetect import detect
from typing import List, Dict, Tuple
import pandas as pd
from nltk.tokenize import word_tokenize
from nltk.util import bigrams, trigrams
from polyglot.detect import Detector

# Configuração do logger para capturar eventos e erros no arquivo 'EntityProtoProcessor.log'
logging.basicConfig(filename='EntityProtoProcessor.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Certifique-se de que os recursos do nltk foram baixados
nltk.download('punkt')
nltk.download('stopwords')

class EntityProtoProcessor:
    def __init__(self):
        """
        Inicializa o processador de entidades e termos, com suporte para análise em português e inglês.
        """
        self.supported_languages = {
            'en': ('english', 'en_core_web_sm'),
            'pt': ('portuguese', 'pt_core_news_sm')
        }

    def detect_language(self, text: str) -> Tuple[str, str, str, str]:
        """
        Detecta o idioma do texto e retorna as informações de código e modelo para o Spacy.

        Parâmetros:
        text (str): O texto a ser analisado para detecção de idioma.

        Retorna:
        Tuple[str, str, str, str]: Um tupla contendo o código do idioma, o código curto, o modelo Spacy e a designação completa.
        """
        lang_code = detect(text)
        if lang_code in self.supported_languages:
            lang_code_short, lang_code_full = self.supported_languages[lang_code]
            logging.info(f"Idioma detectado: {lang_code} ({lang_code_full})")
            return lang_code, lang_code_short, lang_code_full
        else:
            logging.warning(f"Idioma não suportado detectado: {lang_code}")
            return "", "", ""

    def extract_entities(self, text: str) -> Tuple[List[Tuple[str, str]], str, str, str]:
        """
        Extrai entidades nomeadas de um texto com base no idioma detectado.

        Parâmetros:
        text (str): O texto do qual as entidades serão extraídas.

        Retorna:
        Tuple[List[Tuple[str, str]], str, str, str]: Lista de entidades extraídas, o código do idioma, código curto e modelo Spacy.
        """
        lang_code, lang_code_short, lang_code_full = self.detect_language(text)
        if not lang_code_full:
            logging.error("Idioma não suportado para a extração de entidades.")
            return [], "", "", ""

        ent_list = []
        try:
            nlp = spacy.load(lang_code_full)
            doc = nlp(text)
            for entity in doc.ents:
                ent_list.append((entity.text, entity.label_))
            logging.info(f"Entidades extraídas: {ent_list}")
        except Exception as e:
            logging.error(f"Erro ao extrair entidades: {e}")

        return ent_list, lang_code, lang_code_short, lang_code_full

    def cleaner(self, text: str, lang_code_short: str) -> Tuple[List[Tuple[str]], List[Tuple[str]], List[str]]:
        """
        Realiza a limpeza do texto removendo stopwords e caracteres indesejados, e gera bigramas e trigramas.

        Parâmetros:
        text (str): O texto a ser limpo.
        lang_code_short (str): O código curto do idioma para definir as stopwords.

        Retorna:
        Tuple[List[Tuple[str]], List[Tuple[str]], List[str]]: Listas de trigramas, bigramas e palavras filtradas.
        """
        text_tokens = word_tokenize(text)
        stopwords = set(nltk.corpus.stopwords.words(lang_code_short))
        punctuation = string.punctuation + '`“”©–//'
        
        filtered_words = [word.lower() for word in text_tokens if word.lower() not in stopwords and word.lower() not in punctuation]
        filtered_words = [re.sub(r'[0-9]', '', word) for word in filtered_words if len(word) > 1]

        output_bigrams = list(bigrams(filtered_words))
        output_trigrams = list(trigrams(filtered_words))

        logging.info(f"Palavras filtradas: {filtered_words}")
        logging.info(f"Bigrams: {output_bigrams}")
        logging.info(f"Trigrams: {output_trigrams}")

        return output_trigrams, output_bigrams, filtered_words

    def proto(self, filtered_words: List[str]) -> Tuple[List[List], List[List], List[List], List[List]]:
        """
        Constrói dicionários de frequência e posição de termos para análise de relevância de palavras.

        Parâmetros:
        filtered_words (List[str]): Lista de palavras filtradas a serem analisadas.

        Retorna:
        Tuple[List[List], List[List], List[List], List[List]]: Listas de termos organizadas por frequência e ordem.
        """
        term_freq = {}
        term_positions = {}

        for index, word in enumerate(filtered_words):
            if word not in term_freq:
                term_freq[word] = 1
                term_positions[word] = [index]
            else:
                term_freq[word] += 1
                term_positions[word].append(index)

        sorted_freq = sorted(term_freq.items(), key=lambda item: item[1], reverse=True)
        sorted_positions = sorted(term_positions.items(), key=lambda item: item[1][0], reverse=True)

        term_analysis = [
            [word, freq, term_positions[word], sum(term_positions[word]) / len(term_positions[word])]
            for word, freq in sorted_freq
        ]

        alt_freq_bai_ord = sorted(term_analysis, key=itemgetter(1, 3))
        bai_freq_alt_ord = sorted(term_analysis, key=itemgetter(3, 1), reverse=True)
        alt_freq_alt_ord = sorted(term_analysis, key=itemgetter(1), reverse=True)
        bai_freq_bai_ord = sorted(term_analysis, key=itemgetter(3))

        logging.info("Termos organizados por frequência e ordem de aparição.")
        
        return alt_freq_bai_ord, bai_freq_alt_ord, alt_freq_alt_ord, bai_freq_bai_ord

    def process_text(self, text: str) -> Dict[str, List]:
        """
        Processa o texto realizando a detecção de entidades e análise de termos.

        Parâmetros:
        text (str): O texto a ser processado.

        Retorna:
        Dict[str, List]: Um dicionário contendo os resultados da extração de entidades e da análise de termos.
        """
        entities, lang_code, lang_code_short, lang_code_full = self.extract_entities(text)
        trigrams, bigrams, filtered_words = self.cleaner(text, lang_code_short)
        analysis_results = self.proto(filtered_words)

        result = {
            "entities": entities,
            "trigrams": trigrams,
            "bigrams": bigrams,
            "filtered_words": filtered_words,
            "term_analysis": analysis_results
        }

        logging.info(f"Processamento completo do texto: {result}")
        return result
