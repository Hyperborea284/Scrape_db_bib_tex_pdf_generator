import os
import sys
import logging
from datetime import datetime
from time import sleep
from pdf_generator import PDFGenerator  # Assumindo que PDFGenerator está implementado corretamente
from summarizer import Summarizer  # Assumindo que Summarizer está implementado corretamente
from link_manager import LinkManager  # Assumindo que LinkManager está implementado corretamente
from database_utils import DatabaseUtils  # Assumindo que DatabaseUtils está implementado corretamente
from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env, incluindo chaves de API e configurações de ambiente
load_dotenv()

# Configuração básica para o logger, que registra eventos de execução em um arquivo para fins de auditoria e depuração
logging.basicConfig(filename='main.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

class Main:
    def __init__(self, nome_banco='database.db'):
        """
        Inicializa a classe principal `Main`, responsável por gerenciar o fluxo de trabalho completo,
        desde a inserção de links até a geração do PDF final. 

        Esta classe interage com as principais funcionalidades do sistema, incluindo:
        - Gerenciamento do banco de dados SQLite.
        - Extração e validação de dados de links.
        - Sumarização de conteúdo textual.
        - Geração de documentos PDF a partir dos sumários.

        Parâmetros:
        nome_banco (str): O nome do arquivo do banco de dados SQLite que será utilizado.
        """
        self.nome_banco = nome_banco
        self.caminho_banco = os.path.join('databases', nome_banco)  # Caminho completo do banco de dados
        self.database_utils = DatabaseUtils(self.caminho_banco)  # Instância para operações do banco de dados
        self.link_manager = LinkManager(self.database_utils)  # Instância para gerenciamento de links
        self.summarizer = Summarizer(self.caminho_banco)  # Instância para gerar resumos dos conteúdos
        self.pdf_generator = PDFGenerator()  # Instância para geração e compilação do PDF
        self.numero_links = 0  # Contador de links inseridos, para monitoramento
        self.run()  # Inicia o fluxo de interação do usuário

    def loop_inserir_links(self):
        """
        Loop contínuo para inserção de links fornecidos pelo usuário.

        Este método permite que o usuário insira múltiplos links, um por vez, 
        para registro e análise. Ele permanece ativo até que o usuário digite 's'
        para sair do loop. Cada link é validado e, em seguida, registrado no banco de dados 
        se a URL for acessível e válida.
        """
        print("\nAtivação do Loop de Inserção de Links")
        print("Pressione 's' para encerrar o loop e iniciar a sumarização.")
        
        while True:
            # Solicita o link ao usuário
            link = input('Digite o link que deseja registrar: ')
            
            # Condição de saída do loop
            if link.lower() == 's':
                break
            
            # Validação do link para evitar URLs inválidas
            if not self.link_manager.is_valid_url(link):
                print("Link inválido. Por favor, forneça um link válido ou 's' para encerrar.")
                continue
    
            try:
                # Tenta acessar e processar o conteúdo do link
                response = self.link_manager.get_link_data(link)
                self.link_manager.registrar_link(link, response)
            except Exception as e:
                # Em caso de erro, exibe a mensagem para o usuário
                print(f"Erro ao acessar o link: {e}")
                print("Não foi possível registrar o link.")

    def interacao_usuario(self):
        """
        Gerencia o menu principal de interação com o usuário.

        Este método exibe um menu com opções que o usuário pode escolher para manipular
        os dados de links e iniciar a geração de documentos. Cada opção é processada para 
        permitir a inserção, remoção, alteração de dados ou finalização do fluxo.

        Opções:
        1 - Inserir novos links
        2 - Remover dados existentes
        3 - Alterar dados existentes
        4 - Continuar para geração do documento final (sumário e PDF)
        5 - Encerrar o programa
        """
        while True:
            escolha = input('\nEscolha a opção:\n'
                            '1. Inserir links\n'
                            '2. Remover dados\n'
                            '3. Alterar dados\n'
                            '4. Continuar para a geração do documento\n'
                            '5. Encerrar\n'
                            'Digite o número da opção desejada: \n')

            # Processa a escolha do usuário e chama o método correspondente
            if escolha == '1':
                self.loop_inserir_links()
            elif escolha == '2':
                self.link_manager.remover_dados()
            elif escolha == '3':
                self.link_manager.alterar_dados()
            elif escolha == '4':
                self.processar_summarize()
            elif escolha == '5':
                sys.exit(0)
            else:
                print("Opção inválida. Tente novamente.")

    def processar_summarize(self):
        """
        Executa o processo de sumarização dos textos registrados e gera o PDF final.

        Este método utiliza a classe `Summarizer` para sintetizar o conteúdo dos links
        armazenados no banco de dados em um sumário conciso. Em seguida, a classe 
        `PDFGenerator` é utilizada para criar um documento PDF com o conteúdo sumarizado.
        """
        print("\nIniciando a sumarização dos textos registrados...")
        # Gera os resumos para cada link registrado no banco de dados
        summarized_texts = self.summarizer.synthesize_with_gpt(self.caminho_banco)
        print(f"\nSumário gerado: {summarized_texts[:2]}...")  # Exibe os primeiros 2 textos para verificação

        # Gera o PDF final com o conteúdo sumarizado
        print("\nGerando o documento PDF...")
        generated_pdf_path = self.pdf_generator.generate_and_compile_pdf(summarized_texts, "sumario_documento")
        if generated_pdf_path:
            print(f"PDF gerado com sucesso em: {generated_pdf_path}")
        else:
            print("Erro na geração do PDF.")

    def run(self):
        """
        Inicia o fluxo de trabalho principal da aplicação.

        Este método exibe uma mensagem inicial de boas-vindas e executa o menu
        de interação com o usuário, permitindo a escolha de ações para manipular dados 
        de links, gerar resumos e documentos, ou encerrar o sistema.
        """
        print(f"\nIniciando o sistema com banco de dados: {self.caminho_banco}")
        self.interacao_usuario()

if __name__ == "__main__":
    """
    Ponto de entrada para a execução do sistema.

    Este bloco é executado apenas se o script for chamado diretamente. Ele solicita ao usuário
    o nome do banco de dados, inicializa o sistema e inicia o fluxo principal de trabalho 
    a partir da classe `Main`.
    """
    nome_banco = input("Digite o nome do banco de dados (com a extensão .db): ") or "database.db"
    main_system = Main(nome_banco)
