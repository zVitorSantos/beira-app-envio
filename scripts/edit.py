import os
import requests
import customtkinter as tk
import json

# Verifica se o programa foi iniciado corretamente
if not os.environ.get("LAUNCHED_FROM_MAIN"):
    print("Por favor, inicie o programa pelo launch.py")
    exit()

# Carrega o ACCESS_TOKEN e a empresa selecionada
def carregar_access_token():
    try:
        with open("config.json", "r") as file:
            consolidated_data = json.load(file)

        with open("sel.json", "r") as file:
            selected_company_data = json.load(file)

        selected_company = selected_company_data.get("sel", None)
        ACCESS_TOKEN = consolidated_data.get(selected_company, {}).get("tokens", {}).get("ACCESS_TOKEN", None)
        return ACCESS_TOKEN, selected_company

    except FileNotFoundError:
        print("Arquivo de configuração ou empresa selecionada não encontrado.")
        return None, None

# Sua função para buscar uma NFe
def get_nfe(nfe_id):
    ACCESS_TOKEN, _ = carregar_access_token()
    BASE_URL = 'https://www.bling.com.br/Api/v3'
    
    if ACCESS_TOKEN is None:
        print("Token de acesso não encontrado.")
        return None
    
    url = f"{BASE_URL}/nfe/{nfe_id}"
    headers = {'Authorization': f'Bearer {ACCESS_TOKEN}'}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        return json.loads(response.text)
    except Exception as e:
        print(f"Erro ao fazer a requisição: {e}")
        print(response.text)
        return None
    
def salvar_pdf(link_pdf, numero_nfe, selected_company):

    # Caminho onde o PDF será salvo
    pasta_empresa = f'notas-fiscais/{selected_company}'
    pasta_nfe = f'{pasta_empresa}/{numero_nfe}'
    
    # Verifica se os diretórios existem, senão cria
    if not os.path.exists(pasta_empresa):
        os.mkdir(pasta_empresa)
    if not os.path.exists(pasta_nfe):
        os.mkdir(pasta_nfe)
    
    caminho_pdf = os.path.join(pasta_nfe, f'{numero_nfe}.pdf')
    
    # Baixar o PDF
    response = requests.get(link_pdf)
    
    if response.status_code == 200:
        with open(caminho_pdf, 'wb') as f:
            f.write(response.content)
        print(f"PDF salvo como {caminho_pdf}")
    else:
        print(f"Não foi possível baixar o PDF. Código de Status: {response.status_code}")
    
def process_nfe():
    nfe_id = nfe_entry.get()
    nfe_data = get_nfe(nfe_id)

    access_token, selected_company = carregar_access_token()
    
    if nfe_data:
        linkPDF = nfe_data['data']['linkPDF']
        numero_NF = nfe_data['data']['numero']
        
        salvar_pdf(linkPDF, numero_NF, selected_company)
        
        print(f"PDF da NF {numero_NF} baixado com sucesso!")
    else:
        print("Falha ao recuperar os dados da NFe.")

def center_window(root, width, height):
    # Obtém a resolução da tela
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    # Calcula as coordenadas x e y para centralizar a janela
    x = (screen_width / 2) - (width / 2)
    y = (screen_height / 2) - (height / 2)

    root.geometry(f"{width}x{height}+{int(x)}+{int(y)}")

def main():
    global nfe_entry  
    
    # Janela principal
    root = tk.CTk()
    root.title("Buscar NFe")
    root.geometry("250x350")
    root.resizable(False, False)

    center_window(root, 250, 350)

    # Função para checar o tamanho da entrada
    def check_entry_length(event):
        content = nfe_entry.get()
        
        if len(content) > 20:  # Limita a entrada a 20 caracteres
            nfe_entry.delete(20, 'end')
        elif len(content) >= 10:  
            buscar_button.configure(state="normal", font=("Lucida Sans", 16, 'bold'), text_color="white", border_width=2, border_color="white", fg_color="black")
        else:
            buscar_button.configure(state="disabled", font=("Lucida Sans", 16, 'bold'), text_color="grey", border_width=2, border_color="white", fg_color="black")
    
    # Função para esconder o placeholder
    def hide_placeholder(event):
        if nfe_entry.get() == 'ID da NFe':
            nfe_entry.delete(0, 'end')

    # Função para mostrar o placeholder
    def show_placeholder(event):
        if nfe_entry.get() == '':
            nfe_entry.insert(0, 'ID da NFe')
    
    nfe_entry = tk.CTkEntry(root)
    nfe_entry.insert(0, 'ID da NFe')
    nfe_entry.grid(row=0, column=1, sticky='we', padx=1, pady=5)
    nfe_entry.bind("<FocusIn>", hide_placeholder)
    nfe_entry.bind("<FocusOut>", show_placeholder)
    nfe_entry.bind("<KeyRelease>", check_entry_length)

    # Configura a coluna 1 para se expandir e preencher todo o espaço extra
    root.grid_columnconfigure(1, weight=1)

    # Botão de pesquisa (mantendo pequeno)
    buscar_button = tk.CTkButton(root, text="🔎", command=process_nfe, width=1, font=("Lucida Sans", 16, 'bold'), state="disabled", text_color="grey", border_width=2, border_color="white", fg_color="black")
    buscar_button.grid(row=0, column=2, padx=5, pady=5, sticky='ns')

    root.mainloop()

# Se o script for executado diretamente, inicie a interface gráfica
if __name__ == "__main__":
    main()