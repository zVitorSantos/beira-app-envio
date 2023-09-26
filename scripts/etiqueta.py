import requests
import json
import os
from datetime import datetime
import customtkinter as tk
from PIL import Image, ImageTk
from pdf2image import convert_from_path
from xml.etree import ElementTree as ET
import sqlite3

print("=============================================================================================================")

# Inicializar banco de dados SQLite para armazenar EPCs
conn = sqlite3.connect('data/epc_codes.db')
c = conn.cursor()

# Criar a tabela com duas colunas, uma para cada empresa
c.execute("""
CREATE TABLE IF NOT EXISTS epc_codes (
    cnpj TEXT PRIMARY KEY,
    epc TEXT
)""")
conn.commit()

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

def insert_epc(cnpj, epc):
    # Verificar se já existe um registro para o CNPJ fornecido
    c.execute("SELECT * FROM epc_codes WHERE cnpj = ?", (cnpj,))
    existing_record = c.fetchone()
    
    if existing_record:
        # Atualizar o EPC para o CNPJ existente
        c.execute("UPDATE epc_codes SET epc = ? WHERE cnpj = ?", (epc, cnpj))
    else:
        # Inserir novo registro
        c.execute("INSERT INTO epc_codes (cnpj, epc) VALUES (?, ?)", (cnpj, epc))
    
    conn.commit()
    
# Função para apenas fazer o download e decodificação do XML
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

        data_emissao_elem = root.find('.//ns0:dhSaiEnt', namespaces)
        if data_emissao_elem is not None:
            original_data = data_emissao_elem.text.split('T')[0]
            formatted_data = datetime.strptime(original_data, '%Y-%m-%d').strftime('%d/%m/%Y')
            data_emissao = formatted_data
        else:
            data_emissao = 'Data não disponível'

        return xml_data, data_emissao, nNF 
    else:
        print("Erro ao tentar acessar o XML. Código de status:", xml_response.status_code)
        return None, None, None  
    
def xml_item_info(xml_data):
    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError:
        print("Erro na análise do XML.")
        return []

    namespaces = {'ns0': 'http://www.portalfiscal.inf.br/nfe'}  # Define o namespace
    items = []
    ordem_compra = None

    for det in root.findall(".//ns0:det", namespaces):
        item = {}
        prod = det.find("ns0:prod", namespaces)

        if prod is not None:
            xProd_elem = prod.find("ns0:xProd", namespaces)
            uCom_elem = prod.find("ns0:uCom", namespaces)
            qCom_elem = prod.find("ns0:qCom", namespaces)
            xPed_elem = prod.find("ns0:xPed", namespaces)

            if xProd_elem is not None and uCom_elem is not None and qCom_elem is not None:
                xProd = xProd_elem.text.strip()
                uCom = uCom_elem.text
                qCom = qCom_elem.text
                
                xProd_parts = xProd.split(" ")
                item["Código de Item"] = xProd_parts[0]

                if len(xProd_parts) > 1:
                    cor_info_parts = xProd_parts[1].split("/")
                    item["Código de Cor"] = cor_info_parts[0] if cor_info_parts else "Informação não disponível"
                    
                    # Coletando todo o texto após o primeiro espaço e removendo o código de cor
                    material_start_idx = xProd.index(" ") + 1 + len(xProd_parts[1]) + 1
                    item["Material"] = xProd[material_start_idx:]
                else:
                    item["Código de Cor"] = "Informação não disponível"
                    item["Material"] = "Informação não disponível"

                item["Unidade"] = "MIL" if uCom.lower() == "mil" else "PAR"
                item["Qtde"] = qCom
                
                if xPed_elem is not None:
                    item["Pedido"] = xPed_elem.text
                    ordem_compra = xPed_elem.text 
                else:
                    item["Pedido"] = 'Pedido não disponível'
                
                items.append(item)
            else:
                print("Elemento 'prod' não encontrado")
        
    return items, ordem_compra

def generate_epc(cnpj, last_serial):
    return f"{cnpj}{str(last_serial).zfill(10)}"
    
def save_epc(c, CNPJ_EPC):
    c.execute("SELECT * FROM epc_codes WHERE cnpj = ? ORDER BY ROWID DESC LIMIT 1", (CNPJ_EPC,))
    last_epc_record = c.fetchone()
    last_serial = int(last_epc_record[1][-10:]) if last_epc_record else 0
    new_serial = last_serial + 1
    epc_code = generate_epc(CNPJ_EPC, new_serial)
    
    # Salvar novo EPC no banco de dados
    insert_epc(CNPJ_EPC, epc_code)
    
    return epc_code
    
def save_zpl(data, items, Fornecedor, data_emissao, epc_code, ordem_compra, nNF):
    all_zpl_codes = generate_zpl_label(data, items, Fornecedor, data_emissao, epc_code, nNF)

    # Cria o diretório da ordem de compra se ele não existir
    ordem_compra_dir = f'etiquetas/{ordem_compra}'
    if not os.path.exists(ordem_compra_dir):
        os.makedirs(ordem_compra_dir)

    for i, zpl_code in enumerate(all_zpl_codes):
        with open(f'{ordem_compra_dir}/{epc_code}.zpl', 'w') as f:
            f.write(zpl_code)

    return all_zpl_codes
        
def label_zpl(zpl_code, root, epc_code, ordem_compra):
    url = 'http://api.labelary.com/v1/printers/8dpmm/labels/4.5x4.9/0/'
    files = {'file': ('zpl.zpl', zpl_code)}
    headers = {'Accept': 'application/pdf'}
    response = requests.post(url, headers=headers, files=files, stream=True)

    if response.status_code == 200:
        ordem_compra_dir = f'etiquetas/{ordem_compra}'
        if not os.path.exists(ordem_compra_dir):
            os.makedirs(ordem_compra_dir)
            
        pdf_path = f'{ordem_compra_dir}/{epc_code}.pdf'
        
        # Salvar o PDF
        with open(pdf_path, 'wb') as f:
            f.write(response.content)
            
        # Agora você pode abri-lo
        images = convert_from_path(pdf_path)
        
        if len(images) > 0:
            image = images[0]

            # Redimensiona a imagem para caber na tela
            desired_width = 365 
            desired_height = 400

            image.thumbnail((desired_width, desired_height))

            global photo
            photo = ImageTk.PhotoImage(image.convert('RGB'))

            # Crie um canvas e adicione a imagem
            canvas = tk.CTkCanvas(root, width=desired_width, height=desired_height)
            canvas.create_image(0, 0, anchor=tk.NW, image=photo)
            canvas.pack()
        else:
            print("PDF não contém páginas.")
    else:
        print(f"Erro na Labelary API. Código de status: {response.status_code}")

def split_long_text(text, max_length=38):
    words = text.split(' ')
    lines = []
    current_line = ''
    for word in words:
        if len(current_line + word) <= max_length:
            current_line += word + ' '
        else:
            lines.append(current_line.strip())
            current_line = word + ' '
    lines.append(current_line.strip())
    return lines

def generate_zpl_label(data, items, Fornecedor, data_emissao, epc_code, nNF):
    all_zpl_codes = []

    for item in items:
        codigo_item = item.get('Código de Item', '')
        codigo_cor = item.get('Código de Cor', 'N/A')  
        qtde = item.get('Qtde', '')
        unidade = item.get('Unidade', '')
        material = item.get('Material', '').split('/')
        ordem_compra = item.get('Pedido', '')

        # Criação das linhas ZPL para o material
        material_zpl_lines = []
        initial_y_position = 437
        y_position_increment = 45

        for i, line in enumerate(material):
            split_lines = split_long_text(line)
            for j, split_line in enumerate(split_lines):
                material_zpl_lines.append(f"^FO170,{initial_y_position + (y_position_increment * (i + j))}^AS^FD{split_line}^FS")
        
        # Concatenação em uma única string
        material_zpl_code_part = '\n'.join(material_zpl_lines)

        zpl_code = f"""
        ^XA
        ^MCY
        ~SD20
        ^PON
        ^CI13
        ^FO050,200^AR^FDFornecedor:^FS
        ^FO210,193^AT^FD{Fornecedor}^FS
        ^FO550,200^AR^FDData:^FS
        ^FO620,193^AT^FD{data_emissao}^FS
        ^FO050,260^AR^FDItem:^FS
        ^FO120,253^AT^FD{codigo_item}^FS
        ^FO550,260^AR^FDCor:^FS
        ^FO620,253^AT^FD{codigo_cor}^FS
        ^FO050,320^AR^FDQtde./Med.:^FS
        ^FO205,313^AT^FD{qtde}^FS
        ^FO620,313^AT^FD{unidade}^FS
        ^FO050,380^AR^FDTam.:^FS
        ^FO122,373^AS^FD^FS
        ^FO550,380^AR^FDLargura:^FS
        ^FO050,440^AR^FDMaterial:^FS
        {material_zpl_code_part}
        ^FO110,632^AR^FDNF:^FS
        ^FO170,625^AT^FD{nNF}^FS
        ^FO530,632^AR^FDO.C.:^FS
        ^FO600,625^AT^FD{ordem_compra}^FS
        ^FO30,790^BY2,,10^BCN,100,Y,N^FD{epc_code}^FS
        ^FO640,760^BQN,2,7^FDLA,{epc_code}^FS
        ^RFW,H^FD{epc_code}^FS
        ^XZ"""

        all_zpl_codes.append(zpl_code)

    return all_zpl_codes

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
        
        # Passo 2: Fazer o GET para obter o JSON correspondente à NFE
        nfe_data = get_nfe(nfe_id, BASE_URL, ACCESS_TOKEN)
        if nfe_data is None:
            print("Erro ao buscar dados NFE.")
            return
        
        # Passo 3: A partir do JSON, obter o XML
        xml_data, data_emissao, nNF = get_xml(nfe_data)
        if xml_data is None:
            print("Erro ao buscar XML.")
            return
        
        # Passo 4: Extrair as informações desejadas do XML
        items_data = xml_item_info(xml_data)
        if not items_data:
            print("Erro ao extrair informações do XML.")
            return

        # Desempacotar
        items, ordem_compra = xml_item_info(xml_data)
        
        # Passo 5: Gerar um novo EPC
        epc_code = save_epc(c, CNPJ_EPC)
        if epc_code is None:
            print("Erro ao gerar EPC.")
            return
                
        # Passo 6: Montar a etiqueta ZPL com todas essas informações
        zpl_code = save_zpl(nfe_data, items, Fornecedor, data_emissao, epc_code, ordem_compra, nNF)[0]
        if zpl_code is None:
            print("Erro ao montar etiqueta ZPL.")
            return
        
        # Passo 7: Salvar e exibir a etiqueta ZPL
        label_zpl(zpl_code, root, epc_code, ordem_compra)

    # Interface Tkinter
    root = tk.CTk()
    root.geometry("410x510")
    root.title("Gerar Etiquetas")

    center_window(root, 410, 535)

    nfe_entry_label = tk.CTkLabel(root, text="Digite o ID da NFE:")
    nfe_entry_label.pack()

    nfe_entry = tk.CTkEntry(root)
    nfe_entry.insert(0, "18832632012")
    nfe_entry.pack()

    buscar_button = tk.CTkButton(root, text="Buscar", command=process_nfe)
    buscar_button.pack()

    root.mainloop()

if __name__ == "__main__":
    main()
