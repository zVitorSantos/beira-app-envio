import tkinter.messagebox as messagebox
import pandas as pd
import requests
import json

# Carregando dados consolidados do arquivo JSON
with open("config.json", "r") as file:
    consolidated_data = json.load(file)

empresa_ids = {
    "Brilha Natal": {
        "vendedor_id": "15596262453",
        "contato_id": "16251322487"
    },
    "Maggiore Modas": {
        "vendedor_id": "16251444838",
        "contato_id": "15596292520"
    }
}

# Recuperando a empresa selecionada do arquivo temporário
try:
    with open("sel.json", "r") as file:
        selected_company_data = json.load(file)
    selected_company = selected_company_data.get("sel", None)
except FileNotFoundError:
    print("Arquivo de empresa selecionada não encontrada.")
    exit(1)

# Buscar os IDs corretos
ids = empresa_ids.get(selected_company, {})
vendedor_id = ids.get("vendedor_id", None)
contato_id = ids.get("contato_id", None)

if vendedor_id is None or contato_id is None:
    print(f"IDs não encontrados para a empresa {selected_company}")
    exit(1)

# Recuperando o ACCESS_TOKEN com base na empresa selecionada
ACCESS_TOKEN = consolidated_data.get(selected_company, {}).get("tokens", {}).get("ACCESS_TOKEN", None)

# Caminhos para os arquivos
file_path_dados_coletados = r"C:\Users\Usuario\Desktop\Bling API\data\coleta.xlsx"

# 1. Carregar os Dados
dados_coletados_itens_df = pd.read_excel(file_path_dados_coletados, sheet_name='Items')
dados_coletados_infos_df = pd.read_excel(file_path_dados_coletados, sheet_name='Infos')

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
