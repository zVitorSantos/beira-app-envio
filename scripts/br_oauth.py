from flask import Flask, request
import json
import datetime

def load_config():
    with open("config.json", "r") as file:
        data = json.load(file)
    return data

def update_config(company, new_access_token, new_refresh_token):
    with open("config.json", "r") as file:
        data = json.load(file)
        
    data[company]["tokens"]["ACCESS_TOKEN"] = new_access_token
    data[company]["tokens"]["REFRESH_TOKEN"] = new_refresh_token
    data[company]["time"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    with open("config.json", "w") as file:
        json.dump(data, file, indent=4)

app = Flask(__name__)

AUTH_URL = "https://api.calcadosbeirario.app.br/oauth/grant-code"
TOKEN_URL = "https://api.calcadosbeirario.app.br/oauth/access-token"

# Função para verificar se o token está expirado
def is_token_expired(issued_time_str, expires_in=3600):
    issued_time = datetime.datetime.strptime(issued_time_str, '%Y-%m-%d %H:%M:%S')
    current_time = datetime.datetime.now()
    delta = current_time - issued_time
    return delta.total_seconds() >= expires_in

# Carregar dados do config.json
config_data = load_config()
CLIENT_ID = config_data.get("Beira Rio", {}).get("config", {}).get("CLIENT_ID")
CLIENT_SECRET = config_data.get("Beira Rio", {}).get("config", {}).get("CLIENT_SECRET")
issued_time = config_data.get("Beira Rio", {}).get("time", "2000-01-01 00:00:00")

@app.route('/')
def callback():
    try:
        print("Servidor Usado")
    except Exception as e:
        print(f"Exceção: {e}")
        return f"Erro interno do servidor: {e}"

if __name__ == "__main__":
    app.run(debug=False)