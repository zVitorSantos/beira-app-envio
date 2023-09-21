import tkinter as tk
import json
import subprocess
import sys

# Função para salvar a escolha do usuário em um arquivo temporário
def save_choice():
    selected_company = company_var.get()
    if selected_company:
        with open("sel.json", "w") as file:
            json.dump({"sel": selected_company}, file)
        root.quit()
        root.destroy()
        subprocess.run(["python", "main.py"])
    else:
        tk.Label(root, text="Por favor, selecione uma empresa.").pack()

# Inicializando a interface gráfica
root = tk.Tk()
root.title("Seleção de Empresa")

# Variável para armazenar a empresa selecionada
company_var = tk.StringVar(value="None")

# Lista de empresas disponíveis (Você pode preencher esta lista dinamicamente)
companies = ["Brilha Natal", "Maggiore Modas"]

# Criando os widgets
label = tk.Label(root, text="Selecione a empresa:")
label.pack()

for company in companies:
    tk.Radiobutton(root, text=company, variable=company_var, value=company).pack()

# Botão para confirmar a escolha
button = tk.Button(root, text="Confirmar", command=save_choice)
button.pack()

# Executando o loop da interface gráfica
root.mainloop()
