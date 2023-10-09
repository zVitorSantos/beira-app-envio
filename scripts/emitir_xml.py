import requests
import json
import os
import customtkinter as tk
import tkinter.messagebox as messagebox
from xml.etree import ElementTree as ET
from xml.dom import minidom

if not os.environ.get("LAUNCHED_FROM_MAIN"):
    print("Por favor, inicie o programa pelo launch.py")
    exit()

print("=============================================================================================================")

# Carregar dados de configuração
with open("config.json", "r") as file:
    consolidated_data = json.load(file)

# Dicionário para mapear a empresa selecionada ao CNPJ e nome do fornecedor
empresa_mapping = {
    "Brilha Natal": {"CNPJ_EPC": "00699893000105", "Fornecedor": "BRILHA NATAL M"},
    "Maggiore Modas": {"CNPJ_EPC": "24914470000129", "Fornecedor": "MAGGIORE ACESS"}
}

# Recuperar a empresa selecionada
try:
    with open("sel.json", "r") as file:
        selected_company_data = json.load(file)
    selected_company = selected_company_data.get("sel", None)
    CNPJ_EPC = empresa_mapping[selected_company]["CNPJ_EPC"]
    Fornecedor = empresa_mapping[selected_company]["Fornecedor"]
except FileNotFoundError:
    print("Arquivo de empresa selecionada não encontrado.")
    exit(1)

# Recuperar o ACCESS_TOKEN
ACCESS_TOKEN = consolidated_data.get(selected_company, {}).get("tokens", {}).get("ACCESS_TOKEN", None)
BASE_URL = 'https://www.bling.com.br/Api/v3'

def get_nfe(nfe_id, BASE_URL, ACCESS_TOKEN):
    url = f"{BASE_URL}/nfe/{nfe_id}"  
    headers = {'Authorization': f'Bearer {ACCESS_TOKEN}'}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        try:
            return json.loads(response.text)
        except json.JSONDecodeError:
            print("Erro ao decodificar a resposta JSON.")
            return None
    except Exception as e:
        print(f"Erro ao fazer a requisição: {e}")
        return None
    
def get_xml(data):
    xml_url = data.get('data', {}).get('xml', '')
    namespaces = {'ns0': 'http://www.portalfiscal.inf.br/nfe'}
    
    if not xml_url:
        print("URL do XML vazia ou inválida.")
        return None, None, None  
    
    xml_response = requests.get(xml_url)

    if xml_response.status_code == 200:
        xml_data = xml_response.text
        if xml_data:
            root = ET.fromstring(xml_data)
        else:
            print("XML vazio.")
            return None, None, None
        
        nNF_elem = root.find('.//ns0:nNF', namespaces)
        if nNF_elem is not None:
            nNF = nNF_elem.text
        else:
            nNF = 'Número da NF não disponível'
        
        # Verificar se a pasta com o nNF já existe
        nfe_dir = f'etiquetas/{Fornecedor}/{nNF}'
        if os.path.exists(nfe_dir):
            print(f"A Nota Fiscal {nNF} já foi consultada.")
            messagebox.showwarning("Aviso", f"Essa Nota Fiscal {nNF} já foi consultada. Por favor, insira um novo ID.")
            return None, None, None, None

        return xml_data, nNF
    else:
        print("Erro ao tentar acessar o XML. Código de status:", xml_response.status_code)
        return None, None, None, None
    
def extract_xml(nfe_id):
    nfe_data = get_nfe(nfe_id, BASE_URL, ACCESS_TOKEN)
    if nfe_data is None:
        print("Erro ao buscar dados NFE.")
        return None, None

    xml_data, nNF = get_xml(nfe_data)
    if xml_data is None:
        print("Erro ao buscar XML.")
        return None, None

    save_xml(xml_data, nNF)
    return xml_data, nNF
    
def save_xml(xml_data, nNF):
    empresa_path = f'etiquetas/{Fornecedor}'  
    if not os.path.exists(empresa_path):
        os.makedirs(empresa_path)

    nfe_path = f'{empresa_path}/{nNF}'
    if not os.path.exists(nfe_path):
        os.makedirs(nfe_path)

    # Formatar o XML
    parsed_xml = minidom.parseString(xml_data)
    pretty_xml = parsed_xml.toprettyxml(indent="  ")  # Você pode ajustar a indentação como preferir

    with open(f"{nfe_path}/{nNF}.xml", 'w', encoding='utf-8') as f:
        f.write(pretty_xml)


def center_window(root, width, height):
    # Obtém a resolução da tela
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    # Calcula as coordenadas x e y para centralizar a janela
    x = (screen_width / 2) - (width / 2)
    y = (screen_height / 2) - (height / 2)

    root.geometry(f"{width}x{height}+{int(x)}+{int(y)}")

def main():
    global root, nfe_entry

    def process_nfe():
        nfe_id = nfe_entry.get()
        xml_data, nNF = extract_xml(nfe_id)
        if xml_data:
            messagebox.showwarning("XML Emitida", "Sucesso!")

    # Interface Tkinter
    root = tk.CTk()
    root.geometry("300x200")
    root.resizable(False, False)
    root.title("Gerar Etiquetas")

    center_window(root, 410, 535)

    def check_entry_length(event):
        content = nfe_entry.get()
        if len(content) > 20:
            nfe_entry.delete(50, 'end') 
        elif len(content) > 10:
            buscar_button.configure(state="normal")
        else:
            buscar_button.configure(state="disabled")

    # Função para esconder o placeholder
    def hide_placeholder(event):
        if nfe_entry.get() == 'ID da NFe':
            nfe_entry.delete(0, 'end')
            nfe_entry.configure(fg_color='black')

    # Função para mostrar o placeholder
    def show_placeholder(event):
        if nfe_entry.get() == '':
            nfe_entry.insert(0, 'ID da NFe')
            nfe_entry.configure(fg_color='black')

    # Campo de entrada
    nfe_entry = tk.CTkEntry(root)
    nfe_entry.insert(0, 'ID da NFe')
    nfe_entry.configure(fg_color='black')
    nfe_entry.grid(row=0, column=1, sticky='we', padx=5, pady=5)
    nfe_entry.bind("<KeyRelease>", check_entry_length)
    nfe_entry.bind("<FocusIn>", hide_placeholder)
    nfe_entry.bind("<FocusOut>", show_placeholder)

    # Botão de pesquisa
    buscar_button = tk.CTkButton(root, font=('Helvetica', 15, 'bold'), text_color='white', text="🔎", fg_color='black', border_width=2, border_color='#4d7cff', state="disabled", command=process_nfe, width=16, height=25)
    buscar_button.grid(row=0, column=2, padx=5, pady=5)

    # Faz a coluna 1 se expandir para preencher o espaço extra
    root.grid_columnconfigure(1, weight=1)

    root.mainloop()

if __name__ == "__main__":
    main()