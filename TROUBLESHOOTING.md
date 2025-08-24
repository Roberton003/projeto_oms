# Solução de Problemas e Notas de Desenvolvimento

Este documento detalha alguns problemas comuns que podem ser encontrados durante o desenvolvimento e uso deste projeto, bem como as soluções aplicadas.

## 1. Erro "LFS Budget Exceeded" ao fazer Push

**Problema:** Ao tentar fazer `git push`, você pode encontrar um erro como `remote: This repository exceeded its LFS budget.` ou `File database/who_gho.db is ... MB; this exceeds GitHub's file size limit of 100.00 MB`.

**Causa:** O arquivo `database/who_gho.db` (o banco de dados SQLite local) é grande e excede o limite de tamanho de arquivo do GitHub (100 MB para arquivos individuais). Embora o Git LFS (Large File Storage) seja usado para gerenciar arquivos grandes, o GitHub tem um orçamento de armazenamento LFS que pode ser excedido.

**Solução:**

Para evitar custos e manter o repositório leve, decidimos **não versionar o arquivo `database/who_gho.db` no GitHub**. Em vez disso, ele deve ser recriado localmente ou obtido de outra fonte.

Os passos para resolver e evitar este problema foram:

1.  **Remover o arquivo do histórico do Git:**
    *   O arquivo `database/who_gho.db` foi removido do histórico do repositório usando `git filter-repo`. Este é um processo destrutivo que reescreve o histórico do Git. Se você clonou o repositório antes desta alteração, é recomendável cloná-lo novamente para ter um histórico limpo.
    *   Comando usado: `git filter-repo --path database/who_gho.db --invert-paths --force`

2.  **Ignorar o arquivo em futuras operações Git:**
    *   O arquivo `database/who_gho.db` foi adicionado ao `.gitignore` para que o Git o ignore em futuros commits.

3.  **Remover o rastreamento LFS (se aplicável):**
    *   A linha de rastreamento LFS para `database/who_gho.db` foi removida do arquivo `.gitattributes` para garantir que o Git LFS não tente mais gerenciar este arquivo.

4.  **Limpar o cache LFS local:**
    *   Comandos como `git lfs prune` e `git lfs gc` foram usados para limpar o cache local de objetos LFS que não são mais referenciados.

**Como recriar o `database/who_gho.db` localmente:**

Se você precisar do banco de dados localmente, pode recriá-lo executando os scripts:

```bash
python scripts/create_database.py
python scripts/populate_database.py
```

## 2. Erro "nothing to commit, working tree clean" no Script de Push

**Problema:** O script `automate_github_push.py` falhava com um erro `subprocess.CalledProcessError` e a mensagem "nothing to commit, working tree clean" durante a etapa de commit.

**Causa:** O script tentava executar um `git commit` mesmo quando não havia alterações pendentes no repositório local. O comando `git commit` falha se não houver nada para comitar.

**Solução:**

O script `automate_github_push.py` foi modificado para verificar se há alterações pendentes (`git status --porcelain`) antes de tentar adicionar e comitar. Se não houver alterações, ele pulará a etapa de commit e prosseguirá diretamente para o push, garantindo que o processo não seja interrompido desnecessariamente.
