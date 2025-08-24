# Catálogo de Dados: Data Warehouse da OMS

Este documento serve como um guia e dicionário de dados para o Data Warehouse construído a partir da API do Observatório de Saúde Global (GHO) da Organização Mundial da Saúde (OMS).

## 1. Visão Geral da API

A fonte de dados é a API OData do GHO da OMS. A análise inicial revelou os seguintes endpoints principais que usamos para estruturar nosso banco de dados.

### Endpoints Estruturais (Metadados)

*   **/api/Indicator**: Fornece a lista completa de todos os milhares de indicadores de saúde disponíveis, com seus códigos (`IndicatorCode`) e nomes (`IndicatorName`). Foi a fonte para nossa tabela `dim_indicators`.
*   **/api/DIMENSION**: Lista todas as dimensões possíveis que podem ser usadas para filtrar ou agrupar os dados. Exemplos incluem `COUNTRY` (País), `YEAR` (Ano), e `SEX` (Sexo). Esta lista informa quais outras tabelas de dimensão podemos criar.
*   **/api/Region**: Lista as regiões oficiais da OMS (ex: Américas, Europa). (Observação: este endpoint apresentou instabilidade durante a análise).

### Endpoints de Dados

A API possui um endpoint para cada indicador individual. O padrão da URL é:

`https://ghoapi.azureedge.net/api/{IndicatorCode}`

Cada chamada a um desses endpoints retorna os valores observados para aquele indicador, geralmente com dimensões como país, ano e sexo.

## 2. Categorias de Indicadores

Para facilitar a navegação, os mais de 3000 indicadores foram agrupados em categorias baseadas no prefixo de seus códigos. As 20 categorias com mais indicadores são:

| Categoria       | Nº de Indicadores |
|-----------------|-------------------|
| SA              | 456               |
| GDO             | 220               |
| NCD             | 176               |
| RSUD            | 166               |
| GOE             | 92                |
| TB              | 76                |
| TOBACCO         | 64                |
| R               | 61                |
| FOODBORNE       | 52                |
| FINPROTECTION   | 49                |
| PRISON          | 48                |
| M               | 45                |
| NTD             | 42                |
| HRH             | 40                |
| AIR             | 39                |
| RADON           | 34                |
| WCO             | 33                |
| SCSUD           | 33                |
| HEPATITIS       | 30                |
| MDG             | 30                |

*Uma lista completa e categorizada está disponível em `data/categorized_indicators.csv`.*

## 3. Esquema do Banco de Dados (Star Schema)

O banco de dados (`database/who_gho.db`) foi modelado usando um **Star Schema** para otimizar consultas e análises.

### Tabela Fato: `fact_observations`
Esta é a tabela central que armazena os valores numéricos de cada observação.

| Coluna         | Tipo    | Descrição                                      |
|----------------|---------|--------------------------------------------------|
| `observation_id` | INTEGER | Chave Primária, identificador único da observação. |
| `indicator_id` | INTEGER | Chave Estrangeira para `dim_indicators.indicator_id`. |
| `location_id`  | INTEGER | Chave Estrangeira para `dim_locations.location_id`.   |
| `period_id`    | INTEGER | Chave Estrangeira para `dim_periods.period_id`.       |
| `sex_id`       | INTEGER | Chave Estrangeira para `dim_sex.sex_id`.              |
| `value`        | REAL    | O valor numérico da observação.                  |

### Tabelas de Dimensão

#### `dim_indicators`
Armazena os detalhes de cada indicador.

| Coluna           | Tipo    | Descrição                               |
|------------------|---------|-------------------------------------------|
| `indicator_id`   | INTEGER | Chave Primária.                           |
| `indicator_code` | TEXT    | O código único do indicador (ex: NCDMORT3070). |
| `indicator_name` | TEXT    | O nome completo do indicador.             |
| `category`       | TEXT    | A categoria do indicador (ex: NCD).       |

#### `dim_locations`
Armazena os locais geográficos.

| Coluna         | Tipo    | Descrição                               |
|----------------|---------|-------------------------------------------|
| `location_id`  | INTEGER | Chave Primária.                           |
| `country_code` | TEXT    | O código do país (ex: BRA para Brasil).   |
| `country_name` | TEXT    | O nome do país (a ser populado).          |
| `region_code`  | TEXT    | O código da região (a ser populado).      |

#### `dim_periods`
Armazena os períodos de tempo.

| Coluna      | Tipo    | Descrição                         |
|-------------|---------|-----------------------------------|
| `period_id` | INTEGER | Chave Primária.                     |
| `year`      | INTEGER | O ano da observação.              |

#### `dim_sex`
Armazena a dimensão de sexo.

| Coluna     | Tipo    | Descrição                         |
|------------|---------|-----------------------------------|
| `sex_id`   | INTEGER | Chave Primária.                     |
| `sex_code` | TEXT    | O código para o sexo (ex: MLE, FMLE). |
| `sex_name` | TEXT    | O nome do sexo (ex: Male, Female).  |

## 4. Mapeamento API -> Banco de Dados

A tabela abaixo descreve como os campos do JSON retornado pela API são mapeados para as colunas do nosso banco de dados durante o processo de ETL.

| Campo da API     | Tabela do Banco de Dados | Coluna do Banco de Dados | Lógica                                                                 |
|------------------|--------------------------|--------------------------|------------------------------------------------------------------------|
| `IndicatorCode`  | `dim_indicators`         | `indicator_code`         | Inserido diretamente.                                                  |
| `IndicatorName`  | `dim_indicators`         | `indicator_name`         | Inserido diretamente.                                                  |
| `SpatialDim`     | `dim_locations`          | `country_code`           | O valor é usado para popular a tabela de locais.                       |
| `TimeDim`        | `dim_periods`            | `year`                   | O valor é usado para popular a tabela de períodos.                     |
| `Dim1`           | `dim_sex`                | `sex_code`               | Geralmente representa o sexo; o valor é usado para popular a tabela de sexo. |
| `NumericValue`   | `fact_observations`      | `value`                  | O valor numérico da observação.                                        |
