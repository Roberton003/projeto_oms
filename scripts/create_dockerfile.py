import os

def create_dockerfile():
    dockerfile_content = """
# Use uma imagem base Python
FROM python:3.10-slim-buster

# Define o diretório de trabalho dentro do contêiner
WORKDIR /app

# Copia o arquivo requirements.txt e instala as dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o código do projeto para o contêiner
COPY . .

# Define o comando padrão para quando o contêiner for iniciado
# Por exemplo, para rodar o script de população do banco de dados
CMD ["python", "scripts/populate_database.py"]
"""

    dockerfile_path = "Dockerfile"
    with open(dockerfile_path, "w") as f:
        f.write(dockerfile_content)
    print(f"Dockerfile criado em: {os.path.abspath(dockerfile_path)}")

if __name__ == "__main__":
    create_dockerfile()
