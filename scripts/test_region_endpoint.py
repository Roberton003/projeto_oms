import requests

url = "https://ghoapi.azureedge.net/api/Region"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
}

print(f"Tentando acessar a URL: {url}")

try:
    response = requests.get(url, headers=headers, timeout=15)
    print(f"Status Code: {response.status_code}")
    print("--- Conteúdo da Resposta ---")
    print(response.text)
    print("--------------------------")

    # Try to parse as JSON
    try:
        response.json()
        print("Análise JSON: Sucesso!")
    except Exception as e:
        print(f"Análise JSON: Falhou. Erro: {e}")

except requests.exceptions.RequestException as e:
    print(f"Ocorreu um erro na requisição: {e}")
