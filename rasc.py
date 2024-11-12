    Início: Ativação do DatabaseUtils para preparar o banco de dados.
    Etapa 1: Ativação do LinkManager para extrair e registrar o conteúdo dos links.
    Etapa 2: Ativação do SummarizerManager para gerar resumos organizados e memoizá-los no banco de dados.
    Etapa 3: Ativação do BibGenerator para compilar o arquivo .bib com as referências.
    Etapa 4: Ativação do TexGenerator para compor o arquivo .tex com os textos resumidos e citações.
    Etapa Final: Ativação do PDFGenerator para compilar o PDF final. 

 existe algo para facilitar a compilação final do pdf , se hover incorpore em PDFGenerator e Apresente a versão mais plena e convergente do que deve ser BibGenerator para fins de teste

import logging

 # Configuração do logger
logging.basicConfig(filename='pdf_generator.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
