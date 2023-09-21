import requests
import base64
import json
import datetime
from flask import Flask, request, redirect, Response

app = Flask(__name__)

# Carregando dados consolidados do arquivo JSON
with open("config.json", "r") as file:
    consolidated_data = json.load(file)

# Recuperando a empresa selecionada do arquivo temporário
try:
    with open("sel.json", "r") as file:
        selected_company_data = json.load(file)
    selected_company = selected_company_data.get("sel", None)
except FileNotFoundError:
    print("Arquivo de empresa selecionada não encontrado.")
    exit(1)

# Recuperando configurações e tokens com base na empresa selecionada
STATE = consolidated_data.get(selected_company, {}).get("config", {}).get("STATE", None)
CLIENT_ID = consolidated_data.get(selected_company, {}).get("config", {}).get("CLIENT_ID", None)
CLIENT_SECRET = consolidated_data.get(selected_company, {}).get("config", {}).get("CLIENT_SECRET", None)
SCOPES = consolidated_data.get(selected_company, {}).get("config", {}).get("SCOPES", None)
ACCESS_TOKEN = consolidated_data.get(selected_company, {}).get("tokens", {}).get("ACCESS_TOKEN", None)
REFRESH_TOKEN = consolidated_data.get(selected_company, {}).get("tokens", {}).get("REFRESH_TOKEN", None)

# URL da página de autorização do provedor OAuth
AUTHORIZE_URL = f"https://www.bling.com.br/Api/v3/oauth/authorize?response_type=code&client_id={CLIENT_ID}&state={STATE}&scopes={SCOPES}"

# URLs para obtenção dos tokens de acesso e novo access token usando o refresh token
ACCESS_TOKEN_URL = 'https://www.bling.com.br/Api/v3/oauth/token'
REFRESH_TOKEN_URL = 'https://www.bling.com.br/Api/v3/oauth/token'

def update_config_json(access_token, refresh_token, expires_in):
    with open("config.json", "r") as file:
        config_data = json.load(file)
    config_data[selected_company]["tokens"]["ACCESS_TOKEN"] = access_token
    config_data[selected_company]["tokens"]["REFRESH_TOKEN"] = refresh_token
    config_data[selected_company]["time"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open("config.json", "w") as file:
        json.dump(config_data, file, indent=4)

@app.route('/')
def callback():
    # Obter o código de autorização da URL
    code = request.args.get('code')

    if code:
        # Codificar as credenciais para Base64
        base64_creds = base64.b64encode(f'{CLIENT_ID}:{CLIENT_SECRET}'.encode('utf-8')).decode('utf-8')
        
        # Requisição para obter os tokens de acesso usando o grant type "authorization_code"
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': '1.0',
            'Authorization': f'Basic {base64_creds}'
        }
        data = {
            'grant_type': 'authorization_code',
            'code': code
        }

        response = requests.post(ACCESS_TOKEN_URL, headers=headers, data=data)

        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data["access_token"]
            refresh_token = token_data["refresh_token"]
            expires_in = token_data['expires_in']

            update_config_json(access_token, refresh_token, expires_in)

            with open("flask_done.tmp", "w") as f:
                f.write("done")

        elif response.status_code == 400:
            error_data = response.json()
            error_type = error_data["error"]["type"]
            error_message = error_data["error"]["message"]
            error_description = error_data["error"]["description"]
            return f'Erro: {error_type}, {error_message}, {error_description}'
        else:
            response = Response('Erro ao obter os tokens de acesso.')
            response.status_code = 500
            return response
    else:
        return 'Erro!'

@app.route('/refresh')
def refresh():
    # Obter o refresh token da URL (neste exemplo, você pode fornecer o refresh token como parâmetro da URL)
    refresh_token = request.args.get('refresh_token')

    if not refresh_token:
        return 'Refresh token não fornecido.', 400

    # Codificar as credenciais para Base64
    base64_creds = base64.b64encode(f'{CLIENT_ID}:{CLIENT_SECRET}'.encode('utf-8')).decode('utf-8')
    
    # Requisição para obter um novo access token usando o refresh token
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': '1.0',
        'Authorization': f'Basic {base64_creds}'
    }
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
    }

    response = requests.post(REFRESH_TOKEN_URL, headers=headers, data=data)
    if response.status_code == 200:
        token_data = response.json()
        new_access_token = token_data["access_token"]
        return f'Novo token de acesso: {new_access_token}'
    elif response.status_code == 400:
        error_data = response.json()
        error_type = error_data["error"]["type"]
        error_message = error_data["error"]["message"]
        error_description = error_data["error"]["description"]
        return f'Erro: {error_type}, {error_message}, {error_description}'
    else:
        return 'Erro ao obter novo token de acesso.', 500

if __name__ == '__main__':
    app.run()