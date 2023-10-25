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

def center_window(root, width, height):
    # Obtém a resolução da tela
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    # Calcula as coordenadas x e y para centralizar a janela
    x = (screen_width / 2) - (width / 2)
    y = (screen_height / 2) - (height / 2)

    root.geometry(f"{width}x{height}+{int(x)}+{int(y)}")

BASE_URL = 'https://www.bling.com.br/Api/v3'

def pedido_oc():
    # Certifique-se de ter carregado o ACCESS_TOKEN e o BASE_URL corretamente
    ACCESS_TOKEN, _ = carregar_access_token()

    # Pega o valor da entrada da Ordem de Compra
    oc_number = oc_entry.get()
    
    # Constrói a URL e os headers da requisição
    url = f"{BASE_URL}/pedidos/vendas?numero={oc_number}"
    headers = {'Authorization': f'Bearer {ACCESS_TOKEN}'}
    
    # Faz a requisição GET
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:  # Verifica se a requisição foi bem-sucedida
        data = response.json()['data']
        if data:  # Verifica se algum dado foi retornado
            pedido_id = data[0]['id']  # Extrai o campo "id"
            pedido_full(pedido_id)  # Chama a próxima função passando o id como argumento
            return pedido_id
    
    return None

def pedido_full(pedido_id):
    # Certifique-se de ter carregado o ACCESS_TOKEN e o BASE_URL corretamente
    ACCESS_TOKEN, _ = carregar_access_token()
    
    # Constrói a URL e os headers da requisição
    url = f"{BASE_URL}/pedidos/vendas/{pedido_id}"
    headers = {'Authorization': f'Bearer {ACCESS_TOKEN}'}
    
    # Faz a requisição GET
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:  # Verifica se a requisição foi bem-sucedida
        data = response.json()
        # Processa os dados como necessário
        print(data)  # Isso é apenas um exemplo; você pode fazer o que precisar com os dados aqui
    
    else:
        print(f"Erro ao obter detalhes do pedido: {response.status_code}")

def main():
    global oc_entry  
    
    # Janela principal
    root = tk.CTk()
    root.title("Buscar NFe")
    root.geometry("250x350")
    root.resizable(False, False)

    center_window(root, 250, 350)

    # Função para checar o tamanho da entrada
    def check_entry_length(event):
        content = oc_entry.get()
        
        if len(content) > 20:  # Limita a entrada a 20 caracteres
            oc_entry.delete(20, 'end')
        elif len(content) >= 8:  
            buscar_button.configure(state="normal", font=("Lucida Sans", 16, 'bold'), text_color="white", border_width=2, border_color="white", fg_color="black")
        else:
            buscar_button.configure(state="disabled", font=("Lucida Sans", 16, 'bold'), text_color="grey", border_width=2, border_color="white", fg_color="black")
    
    # Função para esconder o placeholder
    def hide_placeholder(event):
        if oc_entry.get() == 'Número da O.C':
            oc_entry.delete(0, 'end')

    # Função para mostrar o placeholder
    def show_placeholder(event):
        if oc_entry.get() == '':
            oc_entry.insert(0, 'Número da O.C')
    
    oc_entry = tk.CTkEntry(root)
    oc_entry.insert(0, 'Número da O.C')
    oc_entry.grid(row=0, column=1, sticky='we', padx=1, pady=5)
    oc_entry.bind("<FocusIn>", hide_placeholder)
    oc_entry.bind("<FocusOut>", show_placeholder)
    oc_entry.bind("<KeyRelease>", check_entry_length)

    # Configura a coluna 1 para se expandir e preencher todo o espaço extra
    root.grid_columnconfigure(1, weight=1)

    # Botão de pesquisa (mantendo pequeno)
    buscar_button = tk.CTkButton(root, text="🔎", command=pedido_oc, width=1, font=("Lucida Sans", 16, 'bold'), state="disabled", text_color="grey", border_width=2, border_color="white", fg_color="black")
    buscar_button.grid(row=0, column=2, padx=5, pady=5, sticky='ns')

    root.mainloop()

# Se o script for executado diretamente, inicie a interface gráfica
if __name__ == "__main__":
    main()