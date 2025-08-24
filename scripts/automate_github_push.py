import subprocess
import os

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

def automate_github_push():
    """Automatiza o processo de commit e push para o GitHub de forma interativa."""
    project_root = os.getcwd()
    print(f"\n--- Iniciando automação Git no diretório: {project_root} ---")

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
        run_command(["git", "remote", "-v"], cwd=project_root)
    except subprocess.CalledProcessError:
        print("Nenhum repositório remoto 'origin' configurado.")
        print("Por favor, configure o repositório remoto manualmente usando:")
        print("git remote add origin <URL_DO_SEU_REPOSITORIO>")
        print("Exemplo: git remote add origin https://github.com/Roberton003/projeto_oms.git")
        print("Após configurar, execute o script novamente.")
        return

    # 5. Solicitar branch para push
    default_branch = "main"
    branch_to_push = input(f"5. Digite o nome do branch para o push (padrão: {default_branch}): ")
    if not branch_to_push:
        branch_to_push = default_branch

    print(f"Enviando (push) para o branch '{branch_to_push}' no GitHub...")
    try:
        run_command(["git", "push", "-u", "origin", branch_to_push], cwd=project_root)
        print("\n--- Processo de push para o GitHub concluído com sucesso! ---")
        print(f"Verifique seu repositório em: https://github.com/Roberton003/projeto_oms (assumindo o nome do repositório)")
    except subprocess.CalledProcessError as e:
        if "set the upstream branch" in e.stderr:
            print(f"Erro: O branch '{branch_to_push}' não tem um upstream configurado. Tentando configurar e fazer push novamente...")
            run_command(["git", "push", "--set-upstream", "origin", branch_to_push], cwd=project_root)
            print("\n--- Processo de push para o GitHub concluído com sucesso! ---")
            print(f"Verifique seu repositório em: https://github.com/Roberton003/projeto_oms (assumindo o nome do repositório)")
        else:
            print("Erro durante o push. Verifique as mensagens acima para detalhes.")
            print("Certifique-se de que você tem permissão para fazer push e que o branch existe no remoto.")
            print("Você pode precisar configurar suas credenciais Git ou criar o repositório no GitHub primeiro.")

if __name__ == "__main__":
    automate_github_push()