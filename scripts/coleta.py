from pdfminer.high_level import extract_text
import subprocess
import tabula
import pandas as pd
import re
import time
import os
import requests
import tkinter as tk
from tkinter import messagebox
import json
from tkinter import filedialog
from datetime import datetime

if not os.environ.get("LAUNCHED_FROM_MAIN"):
    print("Por favor, inicie o programa pelo launch.py")
    exit()

# Função para carregar o ACCESS_TOKEN
def carregar_access_token():
    try:
        with open("config.json", "r") as file:
            consolidated_data = json.load(file)

        with open("sel.json", "r") as file:
            selected_company_data = json.load(file)

        selected_company = selected_company_data.get("sel", None)
        ACCESS_TOKEN = consolidated_data.get(selected_company, {}).get("tokens", {}).get("ACCESS_TOKEN", None)
        return ACCESS_TOKEN

    except FileNotFoundError:
        print("Arquivo de configuração ou empresa selecionada não encontrado.")
        return None

# Função para buscar o ID do item
def buscar_id_item(codigo_item, codigo_cor):
    ACCESS_TOKEN = carregar_access_token()
    if ACCESS_TOKEN is None:
        return None

    BASE_URL = 'https://www.bling.com.br/Api/v3'
    url = f"{BASE_URL}/produtos?nome={codigo_item} - {codigo_cor}"
    headers = {'Authorization': f'Bearer {ACCESS_TOKEN}'}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json().get('data', [])
        if data:
            return data[0]['id']
        # Dentro da função buscar_id_item
        print(f"Buscando ID para código: {codigo_item}, cor: {codigo_cor}")
        print(f"Resposta da API: {response.json()}")
    return None

def selecionar_pdf():
    root = tk.Tk()
    root.withdraw() 
    # Abre a janela de seleção de arquivo
    pdf_path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
    if pdf_path:
        extrair_dados(pdf_path)
    else:
        print("Nenhum arquivo selecionado.")

def format_date(date_str):
    try:
        date_obj = datetime.strptime(date_str, "%d/%m/%Y")
        return date_obj.strftime("%Y-%m-%d")
    except Exception as e:
        print(f"Erro ao formatar a data: {e}")
        return None

def extrair_dados(pdf_path):
    texto = extract_text(pdf_path)
    numero_oc = re.search(r'Número OC:\s*(\d+)', texto)
    data_emissao = re.search(r'DATA DE EMISSÃO:\s*(\d{2}/\d{2}/\d{4})', texto)
    tabelas = tabula.read_pdf(pdf_path, pages='all', multiple_tables=True)
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
    tabela_produtos = tabela_produtos.drop(columns=['Seq.', '% IPI', 'Tam.', 'Descrição'])
    
    data_prevista = str(tabela_produtos['Dt.'].iloc[0])

    # Filtrar a coluna 'Cor' para pegar apenas o primeiro conjunto de números
    tabela_produtos['Cor'] = tabela_produtos['Cor'].str.split(' ').str[0]

    # Reordenar as colunas e adicionar uma coluna 'Item' com números sequenciais
    colunas_ordenadas = ['Cor', 'Código', 'Quant.', 'Vl. Unit.', 'Total']
    tabela_produtos = tabela_produtos[colunas_ordenadas]
    tabela_produtos['Item'] = range(1, len(tabela_produtos) + 1)

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
    colunas_finais = ['Item', 'ID', 'Código', 'Cor', 'Quant.', 'Vl. Unit.', 'Total'] 
    tabela_produtos = tabela_produtos[colunas_finais]

    general_info = {
    'Número OC': numero_oc.group(1) if numero_oc else 'Não encontrado',
    'Data de Emissão': format_date(data_emissao.group(1)) if data_emissao else 'Não encontrado',
    'Data Prevista': format_date(data_prevista)
    }

    general_info_df = pd.DataFrame([general_info])

    file_name = 'data/coleta.xlsx'
    writer = pd.ExcelWriter(file_name, engine='xlsxwriter')

    general_info_df.to_excel(writer, sheet_name='Infos', index=False)

    tabela_produtos.to_excel(writer, sheet_name='Items', index=False)

    writer.close()

    subprocess.call(["python", "scripts/post.py"])

selecionar_pdf()
