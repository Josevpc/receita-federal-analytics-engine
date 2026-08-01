# Receita Federal Analytics Engine

Pipeline local-first que converte a base pública de CNPJ da Receita Federal (arquivos ZIP com texto delimitado) em **Apache Parquet**, consultável via **DuckDB** — sem precisar de servidor de banco de dados.

---

## Visão geral

O projeto resolve um problema recorrente ao trabalhar com a base de CNPJ da Receita Federal: os arquivos são grandes, compactados, separados por entidade e lentos de consultar em CSV. Este pipeline automatiza:

1. **Varredura** dos ZIPs baixados
2. **Extração** com validação de integridade
3. **Conversão** para Parquet (formato colunar, compactado, tipado)
4. **Disponibilização** via DuckDB, com uma view SQL por entidade

O resultado é um Data Lake local, reutilizável entre projetos, sem precisar reprocessar a base toda vez.

---

## Pré-requisitos

- Python 3.10 ou superior
- ~Espaço em disco livre proporcional à base baixada (os arquivos completos da Receita somam vários GB compactados e dezenas de GB descompactados)

---

## Instalação

```bash
git clone <url-do-repositorio>
cd receita-analytics
pip install -r requirements.txt
```

Principais dependências: `duckdb`, `pyarrow`, `typer`, `pyyaml`, `pandas`.

---

## De onde vêm os dados

Os arquivos são baixados diretamente do portal de **Dados Abertos do CNPJ**, mantido pela Receita Federal:

🔗 **https://dados.gov.br/dados/conjuntos-dados/cadastro-nacional-da-pessoa-juridica---cnpj**

> O link exato do portal pode mudar com o tempo — se o endereço acima não funcionar, busque por "dados abertos CNPJ Receita Federal" para encontrar a página atual.

Os arquivos são organizados por competência (mês/ano de atualização) e por entidade, com nomes como:

| Arquivo | Conteúdo |
|---|---|
| `*.EMPRECSV.zip` | Empresas (razão social, natureza jurídica, capital social...) |
| `*.SOCIOCSV.zip` | Sócios/administradores |
| `*.ESTABELE.zip` | Estabelecimentos (endereço, situação cadastral, CNAE...) |

Este projeto já trata essas três entidades. As tabelas de domínio auxiliares da própria Receita (municípios, países, naturezas jurídicas, qualificações, CNAEs, motivos de situação cadastral) também estão disponíveis no mesmo portal, mas ainda não têm schema implementado — ver [Roadmap](#roadmap--próximas-etapas).

### Baixando os arquivos

Não há download automático no momento (item futuro do roadmap). O processo é manual:

1. Acesse o portal e baixe os ZIPs da competência desejada
2. Copie (ou mova) os arquivos baixados para a pasta `data/raw/` do projeto

```
receita-analytics/
└── data/
    └── raw/
        ├── K3241.K03200Y0.D60411.EMPRECSV.zip
        ├── K3241.K03200Y0.D60411.SOCIOCSV.zip
        └── K3241.K03200Y0.D60411.ESTABELE.zip
```

---

## Como usar

### 1. Configuração (opcional)

O comportamento do pipeline é controlado por `config/config.yaml` — caminhos de dados, encoding, tamanho de batch, compressão do Parquet, etc. Os valores padrão já funcionam para o layout público oficial; normalmente não é preciso alterar nada.

### 2. Rodar o setup do banco

Com os ZIPs já em `data/raw/`, execute:

```bash
python init_duck_db.py
```

Esse script varre os ZIPs, extrai, converte cada entidade para Parquet (em `data/parquet/`) e inicializa o DuckDB (`data/receita.duckdb`) com uma view por entidade. Dependendo do volume de dados, essa etapa pode levar de minutos a dezenas de minutos.

Flags úteis:

```bash
python init_duck_db.py --clean-first       # reprocessa tudo do zero (limpa extracted/ e parquet/)
python init_duck_db.py --skip-convert      # só reabre o DuckDB sobre Parquet já existente
python init_duck_db.py --raw-dir /outro/caminho   # usa outra pasta de origem dos ZIPs
```

### 3. Consultar os dados

Via CLI, usando as consultas de exemplo em `consultas/*.sql`:

```bash
python main.py query empresas
python main.py query socios
python main.py query estabelecimentos
```

Ou conectando diretamente no banco a partir de outro script, notebook ou ferramenta de BI que suporte DuckDB:

```python
import duckdb

conn = duckdb.connect("data/receita.duckdb")
df = conn.execute("SELECT * FROM empresas LIMIT 10").df()
```

Novas consultas podem ser adicionadas livremente como arquivos `.sql` em `consultas/`, sem alterar código.

#### Salvando o resultado em arquivo

Por padrão, `query` só imprime um preview no terminal (20 linhas) e descarta o restante. Para salvar o resultado completo, use `--output` (ou `-o`), indicando o formato pela extensão do arquivo — `.csv`, `.parquet` ou `.json` são suportados:

```bash
python main.py query empresas --output resultado.csv
python main.py query empresas -o resultado.parquet
python main.py query empresas -o resultado.json
```

O terminal continua mostrando só o preview limitado por `--limit`, mas o arquivo salvo sempre contém o resultado completo da consulta.

### 4. Outros comandos da CLI

```bash
python main.py convert    # roda apenas a conversão (equivalente ao core do init_duck_db.py)
python main.py update     # reprocessa a base completa
python main.py clean      # remove extracted/ e parquet/
```

### 5. Rodar os testes

A suíte de testes usa arquivos ZIP sintéticos gerados na hora — não é necessário baixar a base real para validar que o pipeline está funcionando:

```bash
python -m pytest tests/ -v
```

---

## Estrutura do projeto

```
receita-federal-analytics-engine/
├── config/config.yaml          # configuração central
├── schemas/                    # um JSON por entidade (colunas, delimitador, encoding)
├── consultas/                  # consultas SQL reutilizáveis
├── src/receita_analytics/      # código-fonte (scanner, extractor, parser, writer, pipeline, duckdb_engine, cli)
├── tests/                      # testes automatizados + fixtures sintéticas
├── data/                       # raw, extracted, parquet, temp (vazio no repositório)
├── init_duck_db.py             # script de setup do banco
└── main.py                     # entry point da CLI
```

---

## Desenvolvimento

Este projeto foi desenvolvido utilizando uma abordagem de desenvolvimento assistido por IA.

O `Claude Code` foi utilizado para acelerar tarefas como implementação de funcionalidades, refatorações, geração de documentação e testes.

As decisões de arquitetura, modelagem do pipeline, definição dos requisitos, validação dos resultados e evolução técnica do projeto foram conduzidas manualmente, utilizando a IA como ferramenta de apoio ao processo de engenharia.

---

## Roadmap / próximas etapas

- Tabelas de domínio da própria Receita (municípios, países, naturezas jurídicas, qualificações, CNAEs) — decodificação dos códigos já presentes em `empresas`/`estabelecimentos`, sem depender de fonte externa
- Enriquecimento com dados do IBGE (população, PIB municipal etc.) — mudança de escopo a ser formalizada em ADR antes da implementação
- Download automático da base mais recente
- API REST e interface Web de consulta

---

## Licença

O código deste projeto pode ser distribuído sob licença MIT. Os dados processados pertencem à Receita Federal do Brasil e seguem os termos de uso definidos pelo órgão — este repositório não redistribui os arquivos oficiais, apenas o código para processá-los.