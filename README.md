# Trabalho 3º Bimestre — SPI II

Aplicação web para consulta de dados de servidores do Poder Executivo Federal, desenvolvida na disciplina de Sistemas para Internet II (FURG). O sistema permite pesquisar por nome, cargo/profissão, UF e órgão, combinar filtros e consultar nomes por similaridade.

## Tecnologias e estrutura

- **Backend:** Python, Flask e Gunicorn.
- **Frontend:** Next.js (React).
- **Banco de dados:** PostgreSQL, com índices B-tree e GIN/`pg_trgm`.
- **Execução:** Docker Compose, com três serviços (`db`, `backend` e `frontend`).

```text
.
├── backend/              # API, Gunicorn e teste de requisições paralelas
├── frontend/             # Aplicação Next.js
├── db/                   # Arquivos de dados, esquema SQL e script de importação
├── docker-compose.yml
└── README.md
```

## Execução local

**Pré-requisitos:** Docker com Compose e Python 3 com `venv` e `pip` para executar o importador. A porta 5432 deve estar disponível no host, assim como as portas 8000 e 3000.

Na raiz do repositório, construa e inicie os serviços:

```bash
docker compose up -d --build
docker compose ps
```

Os serviços ficam acessíveis em:

| Serviço             | Endereço                                            |
| -------------------- | ---------------------------------------------------- |
| Frontend             | http://localhost:3000                                |
| API                  | http://localhost:8000/api/servidores                 |
| Verificação da API | http://localhost:8000/health                         |
| PostgreSQL           | `localhost:5432` (banco `spi`, usuário `spi`) |

**Importante:** o Compose inicializa o PostgreSQL, mas **não executa automaticamente a importação dos dados**. Para realizar consultas sobre registros, conclua a preparação descrita abaixo. O endpoint `/health` verifica a conexão com o banco, não se a tabela já foi populada.

### Preparação e importação dos dados

Os arquivos utilizados pelo importador são `db/CARREIRA-012017.TXT` e `db/APOSENTADOS.112016.csv`, associados aos conjuntos oficiais do Portal Brasileiro de Dados Abertos:

- [Gestão de Pessoas do Executivo Federal — Aposentados](https://dados.gov.br/dados/conjuntos-dados/gestao-de-pessoas-executivo-federal--aposentados)
- [Gestão de Pessoas do Executivo Federal — Carreiras/Cargos](https://dados.gov.br/dados/conjuntos-dados/gestao-de-pessoas-executivo-federal---carreiras--cargos)

Com os contêineres em execução, na raiz do projeto:

```bash
python3 -m venv db/.venv
db/.venv/bin/python -m pip install -r db/requirements.txt
(cd db && .venv/bin/python csv_read_tool.py)
```

O script `db/csv_read_tool.py` cria a tabela e índices necessários e carrega os dois arquivos no PostgreSQL. Ele se conecta a `localhost:5432` utilizando as credenciais de desenvolvimento definidas no Compose. **Não execute a importação repetidamente sobre o mesmo banco**, pois o script não elimina registros previamente carregados.

Após a importação, acesse `http://localhost:3000` ou faça uma consulta simples:

```bash
curl 'http://localhost:8000/api/servidores?limite=2'
```

Para acompanhar a execução ou interromper os serviços:

```bash
docker compose logs -f
docker compose down
```

O volume `postgres_data` mantém os registros após `docker compose down`.

## API de servidores

**Endpoint principal:** `GET /api/servidores`

| Parâmetro              | Comportamento                                                                    |
| ----------------------- | -------------------------------------------------------------------------------- |
| `nome`                | Correspondência exata, desconsiderando diferenças de maiúsculas e minúsculas |
| `similar`             | Similaridade por `pg_trgm` ou correspondência parcial com `ILIKE`           |
| `cargo`               | Correspondência parcial do cargo/profissão                                     |
| `orgao`               | Correspondência parcial do órgão/instituição                                |
| `uf`                  | Sigla de UF, como `RS` ou `DF`                                               |
| `pagina` ou `page`  | Número da página, iniciado em 1 (padrão: 1)                                   |
| `limite` ou `limit` | Quantidade por página (padrão: 20; máximo: 100)                               |
| `ordenar`             | `nome-asc`, `nome-desc` ou `remuneracao-desc`                              |

Os filtros podem ser combinados. Na ausência de ordenação explícita, buscas com `similar` são ordenadas por relevância; as demais utilizam `nome-asc`.

Exemplos:

```http
GET /api/servidores?nome=Maria%20Silva
GET /api/servidores?cargo=analista&uf=RS
GET /api/servidores?orgao=universidade&pagina=2&limite=20
GET /api/servidores?similar=maria&limite=20
```

O retorno de sucesso é um JSON com os campos `itens` (lista de servidores) e `paginacao` (`pagina`, `limite`, `total`, `total_paginas`, `tem_anterior` e `tem_proxima`). Cada item inclui `id`, `cpf`, `nome`, `cargo`, `orgao`, `uf`, `tipo_vinculo` e `remuneracao`, conforme os valores armazenados. Os exemplos acima usam parâmetros ilustrativos, não registros reais.

A API valida os parâmetros e utiliza consultas SQL parametrizadas. As respostas de erro também são JSON, com `erro`, `codigo`, `status` e, quando aplicável, `campo`.

| HTTP | Situação                                                     |
| ---- | -------------------------------------------------------------- |
| 400  | Parâmetros inválidos, duplicados ou entradas não permitidas |
| 404  | Nome não encontrado, página ou rota inexistente              |
| 405  | Método HTTP não permitido                                    |
| 429  | Limite de requisições excedido (`Retry-After`)             |
| 500  | Erro interno ou falha de consulta não classificada            |
| 503  | Banco indisponível ou sobrecarga temporária                  |
| 504  | Consulta ao banco excedeu o tempo limite                       |

## Concorrência e teste de sobrecarga

O Gunicorn utiliza o modelo `gthread`. A API implementa limite de requisições por IP, controle de concorrência por semáforo e timeout de consultas ao PostgreSQL. Os endpoints `/` e `/health` não passam pelos limitadores de requisições. Os limites de taxa e concorrência são mantidos **na memória de cada processo do Gunicorn**, não são globais entre os workers.

| Variável                   |         Padrão |
| --------------------------- | --------------: |
| `GUNICORN_WORKERS`        |           `4` |
| `GUNICORN_THREADS`        |           `8` |
| `QUERY_TIMEOUT_MS`        |        `5000` |
| `RATE_LIMIT_REQUESTS`     |         `120` |
| `RATE_LIMIT_WINDOW`       | `60` segundos |
| `MAX_CONCURRENT_REQUESTS` |          `20` |
| `CONCURRENCY_TIMEOUT_MS`  |         `250` |

Para executar o procedimento de teste previsto no código, com os serviços iniciados e o banco populado:

```bash
python3 backend/teste_paralelo.py
```
