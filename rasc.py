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
generate_and_compile_document




    











Remova todas as operações envolvendo tuplas em todo este arquivo, remova as funçoes proto e process_text , sintetize cleaner detect_language e cleaner numa única função sintética e




























