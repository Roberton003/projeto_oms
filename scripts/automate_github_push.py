import subprocess
import os
import requests
import json

def run_command(command: list[str], cwd: str = None, input_data: str = None):
    """Executa um comando shell e retorna sua saída."""
    try:
        process = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
            input=input_data
        )
        if process.stdout:
            print(process.stdout)
        if process.stderr:
            print(f"Erro (stderr):\n{process.stderr}")
        return process.stdout
    except subprocess.CalledProcessError as e:
        print(f"Erro ao executar comando: {' '.join(e.cmd)}")
        print(f"Stdout: {e.stdout}")
        print(f"Stderr: {e.stderr}")
        raise
    except FileNotFoundError:
        print(f"Erro: Comando '{command[0]}' não encontrado. Certifique-se de que o Git está instalado e no PATH.")
        raise

def create_github_repository(repo_name: str, github_token: str, is_private: bool = False):
    """Cria um novo repositório no GitHub via API."""
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "name": repo_name,
        "private": is_private,
        "auto_init": False # Não inicializa com README, .gitignore, etc.
    }
    
    print(f"Tentando criar o repositório '{repo_name}' no GitHub...")
    try:
        response = requests.post("https://api.github.com/user/repos", headers=headers, data=json.dumps(data))
        response.raise_for_status() # Levanta um erro para códigos de status HTTP ruins (4xx ou 5xx) 
        
        repo_info = response.json()
        print(f"Repositório '{repo_name}' criado com sucesso! URL: {repo_info['html_url']}")
        return repo_info['html_url']
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 422 and "name already exists on this account" in e.response.text:
            print(f"Aviso: Repositório '{repo_name}' já existe na sua conta do GitHub. Prosseguindo...")
            # Se o repositório já existe, tentamos obter a URL para continuar
            try:
                response = requests.get(f"https://api.github.com/repos/{{os.environ.get('GITHUB_USERNAME') or ''}}/{repo_name}", headers=headers)
                response.raise_for_status()
                return response.json()['html_url']
            except requests.exceptions.RequestException as get_e:
                print(f"Erro ao tentar obter URL do repositório existente: {get_e}")
                raise
        else:
            print(f"Erro ao criar repositório no GitHub: {e}")
            print(f"Resposta da API: {e.response.text}")
            raise
    except requests.exceptions.RequestException as e:
        print(f"Erro de conexão ao tentar criar repositório no GitHub: {e}")
        raise

def automate_github_push():
    """Automatiza o processo de commit e push para o GitHub de forma interativa."""
    project_root = os.getcwd()
    print(f"\n--- Iniciando automação Git no diretório: {project_root} ---")

    github_token = os.environ.get("GITHUB_TOKEN")
    if not github_token:
        print("Erro: Variável de ambiente GITHUB_TOKEN não encontrada.")
        print("Por favor, defina a variável de ambiente GITHUB_TOKEN com seu Personal Access Token do GitHub.")
        print("Exemplo (Linux/macOS): export GITHUB_TOKEN=\"seu_token_aqui\"")
        print("Veja como gerar um PAT aqui: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token")
        return

    # 1. Verificar status do Git
    print("\n1. Verificando status do Git...")
    try:
        run_command(["git", "status"], cwd=project_root)
    except Exception:
        print("Parece que este não é um repositório Git ou há problemas. Deseja inicializar um novo repositório? (s/n)")
        if input().lower() == 's':
            print("Inicializando repositório Git local...")
            run_command(["git", "init"], cwd=project_root)
        else:
            print("Operação cancelada. Por favor, inicialize o repositório Git manualmente ou resolva os problemas.")
            return

    # Perguntar o nome do repositório GitHub
    repo_name = input("\nDigite o nome do repositório GitHub a ser criado/usado (ex: projeto_oms): ")
    if not repo_name:
        print("Nome do repositório não pode ser vazio. Operação cancelada.")
        return

    # Perguntar se o repositório deve ser privado
    is_private_str = input(f"Deseja que o repositório '{repo_name}' seja privado? (s/n, padrão: n): ")
    is_private = is_private_str.lower() == 's'

    # Tentar criar o repositório no GitHub
    try:
        github_repo_url = create_github_repository(repo_name, github_token, is_private)
    except Exception as e:
        print(f"Não foi possível criar ou verificar o repositório no GitHub. Erro: {e}")
        return

    # 2. Adicionar todos os arquivos ao stage
    print("\n2. Adicionando todos os arquivos modificados/novos ao stage...")
    run_command(["git", "add", "."], cwd=project_root)
    run_command(["git", "status"], cwd=project_root) # Mostrar o que foi adicionado

    # 3. Solicitar mensagem de commit
    commit_message = input("\n3. Digite a mensagem do commit (obrigatório): ")
    while not commit_message:
        commit_message = input("A mensagem do commit não pode ser vazia. Digite a mensagem do commit: ")

    print(f"Realizando commit com a mensagem: '{commit_message}'...")
    run_command(["git", "commit", "-m", commit_message], cwd=project_root)

    # 4. Verificar e configurar o repositório remoto
    print("\n4. Verificando configuração do repositório remoto...")
    try:
        # Tenta remover o remoto 'origin' se ele já existir para evitar erros
        run_command(["git", "remote", "remove", "origin"], cwd=project_root)
        print("Remoto 'origin' existente removido para reconfiguração.")
    except subprocess.CalledProcessError:
        pass # Não há remoto 'origin' para remover, o que é esperado na primeira vez

    # Adicionar o repositório remoto
    # Usamos a URL retornada pela API de criação
    # A URL retornada pela API é a mais limpa: github_repo_url
    print(f"Adicionando repositório remoto: {github_repo_url}...")
    run_command(["git", "remote", "add", "origin", github_repo_url], cwd=project_root)

    # 5. Enviar (push) os arquivos para o GitHub
    default_branch = "main"
    branch_to_push = input(f"\n5. Digite o nome do branch para o push (padrão: {default_branch}): ")
    if not branch_to_push:
        branch_to_push = default_branch

    print(f"Enviando (push) para o branch '{branch_to_push}' no GitHub...")
    try:
        run_command(["git", "push", "-u", "origin", branch_to_push], cwd=project_root)
        print("\n--- Processo de push para o GitHub concluído com sucesso! ---")
        print(f"Seu projeto deve estar disponível em: {github_repo_url}")
    except subprocess.CalledProcessError as e:
        if "set the upstream branch" in e.stderr:
            print(f"Erro: O branch '{branch_to_push}' não tem um upstream configurado. Tentando configurar e fazer push novamente...")
            run_command(["git", "push", "--set-upstream", "origin", branch_to_push], cwd=project_root)
            print("\n--- Processo de push para o GitHub concluído com sucesso! ---")
            print(f"Seu projeto deve estar disponível em: {github_repo_url}")
        else:
            print("Erro durante o push. Verifique as mensagens acima para detalhes.")
            print("Certifique-se de que você tem permissão para fazer push e que o branch existe no remoto.")
            print("Você pode precisar configurar suas credenciais Git ou criar o repositório no GitHub primeiro.")

if __name__ == "__main__":
    automate_github_push()
