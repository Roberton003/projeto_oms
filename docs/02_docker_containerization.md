# 02 - Conteinerização com Docker

Este documento explica como o Docker pode ser utilizado para conteinerizar o ambiente do projeto, garantindo portabilidade e reprodutibilidade.

## Conceito de Conteinerização com Docker

Docker é uma plataforma que permite empacotar aplicações e suas dependências em contêineres. Um contêiner é uma unidade de software padronizada que inclui tudo o que é necessário para o software funcionar: código, tempo de execução, bibliotecas do sistema, ferramentas do sistema e configurações.

**Benefícios:**
*   **Isolamento:** O contêiner é um ambiente isolado, garantindo que suas dependências não interfiram com outros softwares no seu sistema.
*   **Portabilidade:** A imagem Docker pode ser executada em qualquer máquina que tenha o Docker instalado, garantindo que o ambiente de execução seja sempre o mesmo.
*   **Reprodutibilidade:** Qualquer pessoa pode construir e executar seu projeto exatamente da mesma forma, eliminando problemas de "funciona na minha máquina".

## Script de Geração do Dockerfile

O `Dockerfile` é um arquivo de texto que contém uma série de instruções para construir uma imagem Docker.

**Localização do Script:** `scripts/create_dockerfile.py`

```python
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
```

## Entendimento e Propósito do Script

Este script Python automatiza a criação do `Dockerfile` para o projeto.

*   **`FROM python:3.10-slim-buster`**: Define a imagem base do contêiner, que é uma versão leve do Python.
*   **`WORKDIR /app`**: Define o diretório de trabalho dentro do contêiner.
*   **`COPY requirements.txt .` e `RUN pip install ...`**: Copia o arquivo de dependências e as instala.
*   **`COPY . .`**: Copia todo o código do seu projeto para o contêiner.
*   **`CMD ["python", "scripts/populate_database.py"]`**: Define o comando que será executado por padrão quando o contêiner for iniciado.

**Significado para o Projeto:**

Este script demonstra como o ambiente de desenvolvimento e execução do seu projeto pode ser empacotado de forma automatizada. Isso é fundamental para garantir que o pipeline de dados funcione de forma consistente em diferentes ambientes, desde o desenvolvimento até a produção.

## Como Executar

Para usar o Docker, você precisaria ter o Docker Engine instalado em sua máquina.

1.  **Gerar o `Dockerfile`:**
    ```bash
    venv/bin/python scripts/create_dockerfile.py
    ```
    Este comando criará o arquivo `Dockerfile` na raiz do seu projeto.

2.  **Construir a Imagem Docker:**
    ```bash
    docker build -t oms-data-pipeline .
    ```
    *   `docker build`: Comando para construir uma imagem Docker.
    *   `-t oms-data-pipeline`: Atribui um nome (`oms-data-pipeline`) e uma tag (opcional, aqui é a `latest` por padrão) à sua imagem.
    *   `.`: Indica que o `Dockerfile` está no diretório atual.

3.  **Executar o Contêiner Docker:**
    ```bash
    docker run oms-data-pipeline
    ```
    *   `docker run`: Comando para criar e executar um contêiner a partir de uma imagem.
    *   `oms-data-pipeline`: O nome da imagem que você construiu.
    *   Por padrão, este comando executará o `CMD` definido no `Dockerfile`, que é `python scripts/populate_database.py`.
