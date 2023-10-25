from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
import requests
import os
import time
import json
from pdfminer.high_level import extract_text
import subprocess
import tabula
import pandas as pd
import re
import tkinter as tk
from tkinter import messagebox
import tkinter.messagebox as messagebox
from tkinter import filedialog
from datetime import datetime, timedelta

# if not os.environ.get("LAUNCHED_FROM_MAIN"):
#     print("Por favor, inicie o programa pelo launch.py")
#     exit()

def carregar_acesso():
    try:
        with open("config.json", "r") as file:
            consolidated_data = json.load(file)

        with open("sel.json", "r") as file:
            selected_company_data = json.load(file)

        selected_company = selected_company_data.get("sel", None)
        ACCESS_TOKEN = consolidated_data.get(selected_company, {}).get("tokens", {}).get("ACCESS_TOKEN", None)
        beirario_data = consolidated_data.get(selected_company, {}).get("beirario", {})
        
        return ACCESS_TOKEN, selected_company, beirario_data

    except FileNotFoundError:
        print("Arquivo de configuração ou empresa selecionada não encontrado.")
        return None, None, None
    
def buscar_id_item(codigo_item, codigo_cor):
    ACCESS_TOKEN, _, _ = carregar_acesso()
    if ACCESS_TOKEN is None:
        print("Token de acesso não encontrado.")
        return None

    BASE_URL = 'https://www.bling.com.br/Api/v3'
    url = f"{BASE_URL}/produtos?nome={codigo_item} - {codigo_cor}"
    headers = {'Authorization': f'Bearer {ACCESS_TOKEN}'}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json().get('data', [])
        if data:
            return data[0]['id']
        else:
            print(f"ID não encontrado para Código: {codigo_item}, Cor: {codigo_cor}")
    else:
        print(response.text)
        print(f"Resposta da API inesperada. Código: {response.status_code}")

    return None

def format_date(date_str):
    try:
        date_obj = datetime.strptime(date_str, "%d/%m/%Y")
        return date_obj.strftime("%Y-%m-%d")
    except Exception as e:
        print(f"Erro ao formatar a data: {e}")
        return None
    
def post(numero_oc):
    ACCESS_TOKEN, selected_company, _ = carregar_acesso()
    empresa_ids = {
        "Brilha Natal": {
            "vendedor_id": "15596262453",
            "contato_id": "16251322487"
        },
        "Maggiore Modas": {
            "vendedor_id": "16251444838",
            "contato_id": "15596292520"
        },
        "Maggiore Pecas": {
            "vendedor_id": "16364857694",
            "contato_id": "15596296690"
        }
    }

    # Buscar os IDs corretos
    ids = empresa_ids.get(selected_company, {})
    vendedor_id = ids.get("vendedor_id", None)
    contato_id = ids.get("contato_id", None)

    if vendedor_id is None or contato_id is None:
        print(f"IDs não encontrados para a empresa {selected_company}")
        exit(1)

    # Caminhos para os arquivos
    file_path = r"C:\Users\Usuario\Desktop\Bling ENVIO\preparo\preparo.xlsx"

    # 1. Carregar os Dados
    dados_coletados_itens_df = pd.read_excel(file_path, sheet_name='Items')
    dados_coletados_infos_df = pd.read_excel(file_path, sheet_name='Infos')

    # Verifique se a pasta da empresa selecionada existe, caso contrário, crie-a
    company_folder = os.path.join(f"pedidos/{selected_company}/{numero_oc}")
    print("pasta do pedido", company_folder)
    if not os.path.exists(company_folder):
        os.makedirs(company_folder)

    # Nome do arquivo baseado no número da O.C.
    company_file = f"{numero_oc}.xlsx"

    # Caminho completo para o novo local do arquivo
    new_path = os.path.join(company_folder, company_file)

    # Mova o arquivo preparo.xlsx para o novo local com o nome correto
    os.rename(file_path, new_path)

    # Função para criar a estrutura de item para o JSON
    def create_item(row):
        return {
            "id": str(row['ID']),
            "codigo": str(row['Código']),
            "unidade": "",
            "quantidade": str(row['Quant.']),
            "desconto": 0,
            "valor": str(row['Vl. Unit.']),
            "aliquotaIPI": 0,
            "descricao": "",
            "descricaoDetalhada": "",
            "produto": {
                "id": str(row['ID'])
            },
            "comissao": {
                "base": "<float>",
                "aliquota": "<float>",
                "valor": "<float>"
            }
        }

    # Criando a lista de itens
    itens_list = [create_item(row) for index, row in dados_coletados_itens_df.iterrows()]

    # Criando o JSON para a requisição
    json_data = {
        "id": "",
        "numero": str(dados_coletados_infos_df['Número OC'].iloc[0]),
        "data": dados_coletados_infos_df['Data de Emissão'].iloc[0],
        "dataPrevista": dados_coletados_infos_df['Data Prevista'].iloc[0],
        "contato": {
            "id": vendedor_id,
            "nome": "",
            "tipoPessoa": "J",
            "numeroDocumento": "88.379.771/0035-21"
        },
        "numeroPedidoCompra": str(dados_coletados_infos_df['Número OC'].iloc[0]),
        "itens": itens_list,
        "vendedor": {
            "id": contato_id
        }
    }

    url = "https://www.bling.com.br/Api/v3/pedidos/vendas"
    headers = {'Authorization': f'Bearer {ACCESS_TOKEN}'}
    response = requests.post(url, json=json_data, headers=headers)

    # Capturando e exibindo o código de status e o corpo da resposta
    status_code = response.status_code
    response_body = response.json()

    if status_code in [200, 201]:
        messagebox.showwarning("Concluído!", "Pedido adicionado com sucesso!")
    else:
        formatted_json = json.dumps(response.json(), indent=4, ensure_ascii=False).encode('utf8').decode()
        messagebox.showwarning("Erro!", f"{formatted_json}")

    
def extrair_dados(pdf_path):
    texto = extract_text(pdf_path)
    numero_oc = re.search(r'Número OC:\s*(\d+)', texto).group(1) if re.search(r'Número OC:\s*(\d+)', texto) else 'na'
    data_emissao = re.search(r'DATA DE EMISSÃO:\s*(\d{2}/\d{2}/\d{4})', texto)
    tabelas = tabula.read_pdf(pdf_path, pages='all', multiple_tables=True)
    ACCESS_TOKEN, selected_company, _ = carregar_acesso()

    tabela_produtos = tabelas[0]

    # Criar uma nova tabela para armazenar as linhas não problemáticas
    nova_tabela_produtos = pd.DataFrame(columns=tabela_produtos.columns)

    # Iterar pelas linhas da tabela original
    for index, row in tabela_produtos.iterrows():
        # Se a linha não for problemática, adicionar à nova tabela
        if not 'Remessa:' in str(row['Seq.']):
            nova_tabela_produtos.loc[index] = row

    # Manter a tabela nova como a tabela de produtos
    tabela_produtos = nova_tabela_produtos

    # Remover as colunas não necessárias e manter a coluna 'Código'
    tabela_produtos = tabela_produtos.drop(columns=['% IPI', 'Tam.', 'Descrição'])
    
    data_prevista = str(tabela_produtos['Dt.'].iloc[0])

    # Filtrar a coluna 'Cor' para pegar apenas o primeiro conjunto de números
    tabela_produtos['Cor'] = tabela_produtos['Cor'].str.split(' ').str[0]

    # Reordenar as colunas e adicionar uma coluna 'Item' com números sequenciais
    colunas_ordenadas = ['Seq.', 'Cor', 'Código', 'Quant.', 'Vl. Unit.', 'Total']
    tabela_produtos = tabela_produtos[colunas_ordenadas]

    # Adicionar novamente a coluna 'ID', se necessário
    if 'ID' not in tabela_produtos.columns:
        tabela_produtos['ID'] = None

    itens_faltantes = []

    # Após o DataFrame tabela_produtos estar pronto
    for index, row in tabela_produtos.iterrows():
        codigo_item = str(int(row['Código'])).zfill(6)
        codigo_cor = str(int(row['Cor'])).zfill(5)
        id_item = buscar_id_item(codigo_item, codigo_cor)
        tabela_produtos.at[index, 'ID'] = id_item

        if id_item is None:
            itens_faltantes.append(f"Código: {codigo_item}, Cor: {codigo_cor}")
    
    if itens_faltantes:
        root = tk.Tk()
        root.withdraw() 
        mensagem = "Itens faltantes no sistema:\n" + "\n".join(itens_faltantes)
        messagebox.showwarning("Itens Faltantes", mensagem)
        root.mainloop()

    # Ajustar a ordem final das colunas
    colunas_finais = ['Seq.', 'ID', 'Código', 'Cor', 'Quant.', 'Vl. Unit.', 'Total'] 
    tabela_produtos = tabela_produtos[colunas_finais]

    general_info = {
    'Número OC': numero_oc if numero_oc != 'na' else 'Não encontrado',
    'Data de Emissão': format_date(data_emissao.group(1)) if data_emissao else 'Não encontrado',
    'Data Prevista': format_date(data_prevista)
    }

    general_info_df = pd.DataFrame([general_info])

    general_info_df = pd.DataFrame([general_info])

    file_name = 'preparo/preparo.xlsx'
    writer = pd.ExcelWriter(file_name, engine='xlsxwriter')

    general_info_df.to_excel(writer, sheet_name='Infos', index=False)

    tabela_produtos.to_excel(writer, sheet_name='Items', index=False)

    writer.close()

    # Chama o post
    post(numero_oc=numero_oc)

# Carregando os dados
_, selected_company, beirario_data = carregar_acesso()

# Verifica se conseguiu carregar os dados do Beirario
if beirario_data:
    usuario = beirario_data.get('usuario', None)
    senha = beirario_data.get('senha', None)

    if usuario and senha:
        # Configure o driver do Firefox com a opção headless
        options = webdriver.FirefoxOptions()
        options.add_argument('-headless')
        driver = webdriver.Firefox(options=options)

        # Acesse o site
        driver.get("https://brportal.beirario.com.br/brportal/acesso/login")

        # Encontre o campo de usuário e insira o nome de usuário
        campo_usuario = driver.find_element(By.NAME, "usuario")
        campo_usuario.clear()
        campo_usuario.send_keys(usuario)

        # Encontre o campo de senha e insira a senha
        campo_senha = driver.find_element(By.NAME, "senha")
        campo_senha.clear()
        campo_senha.send_keys(senha)

        # Encontre o botão de login e clique nele
        botao_entrar = driver.find_element(By.XPATH, '//button[@type="submit"]')
        botao_entrar.click()

        print("Login efetuado com sucesso!")

        # Navegue até a URL após o login
        driver.get('https://brportal.beirario.com.br/brportal/com/ArquivosOrdemCompraForm.jsp')

        # Preencha o campo fil_filial com o valor 17
        campo_filial = driver.find_element(By.NAME, 'fil_filial')
        campo_filial.clear()
        campo_filial.send_keys('17')

        # Obtenha a data atual e calcule as datas inicial e final
        data_atual = datetime.now()
        data_inicial = (data_atual - timedelta(days=30)).strftime('%d%m%Y')
        data_final = (data_atual + timedelta(days=14)).strftime('%d%m%Y')

        action = ActionChains(driver)

        # Para o campo de data inicial
        campo_dt_inicial = driver.find_element(By.ID, 'dt_inicial')
        action.move_to_element(campo_dt_inicial).click().send_keys(data_inicial).perform()

        # Para o campo de data final
        campo_dt_final = driver.find_element(By.ID, 'dt_final')
        action.move_to_element(campo_dt_final).click().send_keys(data_final).perform()

        botao_pesquisar = driver.find_element(By.NAME, 'select1_action')
        botao_pesquisar.click()

        print("Pedidos pesquisados!")

        # Localize a tabela pelo seu ID
        tabela = driver.find_element(By.ID, 'TRbl_report_Jw_consulta_titulos')

        # Encontre todas as linhas da tabela
        linhas = tabela.find_elements(By.TAG_NAME, 'tr')

        # Guarde o identificador da janela original
        main_window_handle = driver.current_window_handle

        # Itere através das linhas da tabela
        for linha in linhas:
            try:
                oco_numero_elemento = linha.find_element(By.XPATH, './/input[contains(@name, "oco_numero")]')
                oco_numero = oco_numero_elemento.get_attribute('value')
            except NoSuchElementException:
                continue

            # Caminho onde o arquivo seria salvo
            arquivo_path = f"pedidos/{selected_company}/{oco_numero}/{oco_numero}.pdf"

            # Verifica se o arquivo já existe
            if os.path.exists(arquivo_path):
                print(f"Arquivo para OC {oco_numero} já existe.")
                continue

            # Clique no botão "Remessa"
            try:
                remessa_button = linha.find_element(By.XPATH, './/input[@value="Remessa"]')
                remessa_button.click()
            except NoSuchElementException:
                continue

            # Espere até que a nova janela/aba seja aberta
            wait = WebDriverWait(driver, 5)
            wait.until(EC.number_of_windows_to_be(2))

            # Alterne para a nova janela/aba
            new_window_handle = [window for window in driver.window_handles if window != main_window_handle][0]
            driver.switch_to.window(new_window_handle)

            # Espere até que o elemento esteja presente
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//a[contains(@href, 'OrdemCompraRemessa')]"))
            )

            # Obtenha o link do PDF
            try:
                pdf_link_element = driver.find_element(By.XPATH, "//a[contains(@href, 'OrdemCompraRemessa')]")
                pdf_link = pdf_link_element.get_attribute('href')
                print(f"PDF Link: {pdf_link}")
            except NoSuchElementException:
                print("Elemento não encontrado.")
                continue

            # Baixar o arquivo PDF
            response = requests.get(pdf_link)

            # Verifique se a requisição foi bem-sucedida
            if response.status_code == 200:
                # Verifique se o diretório existe, senão, crie-o
                diretorio = os.path.dirname(arquivo_path)
                if not os.path.exists(diretorio):
                    os.makedirs(diretorio)

                # Escrever o conteúdo do PDF no arquivo
                with open(arquivo_path, 'wb') as f:
                    f.write(response.content)
                print(f"Arquivo {oco_numero}.pdf salvo com sucesso!")
                extrair_dados(arquivo_path)
            else:
                print(f"Não foi possível baixar o arquivo {oco_numero}.pdf")

            print("Próximo Item")

            # Feche a nova janela/aba e volte para a janela original
            driver.close()
            driver.switch_to.window(main_window_handle)

        print("Acabaram todos!")

        # Feche o navegador
        driver.quit()
    else:
        print("Usuário ou senha não disponíveis.")
else:
    print("Dados do Beirario não encontrados.")