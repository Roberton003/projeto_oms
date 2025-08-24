import subprocess
import os

def run_command(command: list[str], cwd: str = None):
    """Executa um comando shell e retorna sua saída."""
    try:
        result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=True)
        print(result.stdout)
        if result.stderr:
            print(f"Erro (stderr):\n{result.stderr}")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Erro ao executar comando: {e.cmd}")
        print(f"Stdout: {e.stdout}")
        print(f"Stderr: {e.stderr}")
        raise

def automate_github_push(repo_name: str = "projeto_oms"):
    """Automatiza a inicialização do Git e o push para um novo repositório GitHub.

    Args:
        repo_name (str): O nome do repositório GitHub a ser criado e para onde o projeto será enviado.
    """
    project_root = os.getcwd()
    print(f"\n--- Iniciando automação Git para o projeto: {repo_name} ---")

    # 1. Inicializar um novo repositório Git local
    print("\n1. Inicializando repositório Git local...")
    run_command(["git", "init"], cwd=project_root)

    # 2. Adicionar todos os arquivos ao stage
    print("\n2. Adicionando arquivos ao stage...")
    run_command(["git", "add", "."], cwd=project_root)

    # 3. Fazer o commit inicial
    print("\n3. Realizando o commit inicial...")
    run_command(["git", "commit", "-m", "Initial commit: Setup project structure and core pipeline"], cwd=project_root)

    # 4. Solicitar informações do usuário para o push remoto
    print("\n--- Configuração do Repositório Remoto GitHub ---")
    print("Para continuar, você precisará de um Token de Acesso Pessoal (PAT) do GitHub.")
    print("Se você não tiver um, crie um em: https://github.com/settings/tokens?type=personal")
    
    github_username = input("Digite seu nome de usuário do GitHub: ")
    github_pat = input("Digite seu Token de Acesso Pessoal (PAT) do GitHub: ")

    # Construir a URL do repositório remoto
    # Assumimos que o repositório já foi criado no GitHub
    remote_url = f"https://{github_username}:{github_pat}@github.com/{github_username}/{repo_name}.git"
    
    print(f"\n4. Adicionando repositório remoto: {remote_url.split('@')[1]}...") # Esconde o PAT no print
    run_command(["git", "remote", "add", "origin", remote_url], cwd=project_root)

    # 5. Enviar (push) os arquivos para o GitHub
    print("\n5. Enviando arquivos para o GitHub...")
    # Usamos -f (force) para sobrescrever se houver histórico diferente, o que pode acontecer em repositórios recém-criados
    # Em um cenário real, você pode querer usar --set-upstream origin main/master
    run_command(["git", "push", "-u", "origin", "main"], cwd=project_root) # Assumindo branch 'main'
    # Se o seu branch padrão for 'master', use: run_command(["git", "push", "-u", "origin", "master"], cwd=project_root)

    print("\n--- Processo de push para o GitHub concluído! ---")
    print(f"Seu projeto deve estar disponível em: https://github.com/{github_username}/{repo_name}")

if __name__ == "__main__":
    automate_github_push()
