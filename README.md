# Trabalho 3º Bimestre — SPI II

Aplicação web para consulta de dados de servidores do Poder Executivo Federal, desenvolvida na disciplina de Sistemas para Internet II (FURG). O sistema permite pesquisar por nome, cargo/profissão, UF e órgão (por nome ou sigla), combinar filtros e consultar nomes por similaridade.

## Tecnologias e estrutura

- **Backend:** Python, Flask e Gunicorn.
- **Frontend:** Next.js (React).
- **Banco de dados:** PostgreSQL, com índices B-tree e GIN/`pg_trgm`.
- **Execução:** Docker Compose, com PostgreSQL, um importador de execução única, API e frontend.

```text
.
├── backend/              # API, Gunicorn e teste de requisições paralelas
├── frontend/             # Aplicação Next.js
├── db/                   # Arquivos de dados, esquema SQL e script de importação
├── docker-compose.yml
└── README.md
```

## Execução e deploy com Docker Compose

Na raiz do projeto, inicie a aplicação com Docker e o plugin Compose.

```bash
docker compose up -d --build
```

O PostgreSQL inicia primeiro. O serviço `importador` cria o esquema, carrega os arquivos e prepara os índices. A API aguarda a conclusão da carga, e o frontend aguarda a API responder. A primeira inicialização processa cerca de 1,5 milhão de vínculos. Para acompanhar o progresso, use `docker compose logs -f importador`. O estado `Exited (0)` nesse serviço indica que a carga terminou com sucesso.

| Serviço | Endereço local |
| --- | --- |
| Frontend | http://localhost:3000 |
| API | http://localhost:8000/api/servidores |
| Saúde da API | http://localhost:8000/health |
| PostgreSQL | `127.0.0.1:5432` (banco e usuário `spi`) |

No deploy, o navegador consulta `/api/servidores` no mesmo domínio do frontend. O Next.js encaminha a requisição à API pela rede do Compose. Se o navegador precisar acessar diretamente um domínio próprio da API, defina `NEXT_PUBLIC_API_URL` antes do build. No servidor de destino, defina `POSTGRES_PASSWORD` antes da criação do volume. A senha padrão de desenvolvimento é `spi`. Em um volume existente, use a senha já configurada no PostgreSQL. A porta local do banco pode ser configurada com `DB_HOST_PORT`.

### Dados e atualização automática

As duas bases completas estão incluídas no repositório em gzip. Os arquivos são lidos diretamente da imagem do importador.

| Arquivo em `db/` | Competência | Campos de origem | Vínculos |
| --- | --- | ---: | ---: |
| `CARREIRA_082026.csv.gz` | Agosto de 2026 | 8 | 1.092.162 |
| `APOSENTADOS_082025_FULL.csv.gz` | Agosto de 2025 | 18 | 414.671 |

As tabelas `carreiras` e `aposentadorias` preservam as colunas de cada fonte. Códigos e matrículas são textuais para manter zeros à esquerda. Valores monetários usam `numeric` e datas usam `date`. As 133 linhas de totais da base de carreiras ficam em `totais_carreira`. A visão `servidores` reúne os vínculos para a API. O catálogo `orgaos` associa as siglas informadas na base de aposentadorias aos nomes correspondentes das duas bases. A UF pertence à unidade pagadora da base de carreiras.

A cada inicialização do importador, o SHA-256 do conteúdo é comparado com a tabela `importacoes`. Só os arquivos alterados são recarregados. A carga usa `COPY` em fluxo e uma transação para os dois arquivos, com bloqueio para execuções simultâneas. Em caso de falha, a transação é revertida. O volume `postgres_data` mantém os dados após `docker compose down`. Ao atualizar um volume do projeto antigo, a tabela original fica disponível em `servidores_legado`.

Fontes dos registros no Portal Brasileiro de Dados Abertos

- [Gestão de Pessoas do Executivo Federal — Aposentados](https://dados.gov.br/dados/conjuntos-dados/gestao-de-pessoas-executivo-federal--aposentados)
- [Gestão de Pessoas do Executivo Federal — Carreiras/Cargos](https://dados.gov.br/dados/conjuntos-dados/gestao-de-pessoas-executivo-federal---carreiras--cargos)

Algumas universidades usam uma sigla diferente da folha. A visão `siglas_universidades` acrescenta essas formas à busca. Por exemplo, `UFPel` e `FUFPEL` encontram o mesmo órgão, e `UNILA` identifica uma universidade que só aparece em carreiras. As correspondências usam as denominações das bases e os cadastros institucionais. [Lista de órgãos do Arquivo Nacional](https://www.gov.br/arquivonacional/pt-br/siga/informes/arquivo-nacional-inicia-ciclo-de-aplicacao-do-imgd-2026/lista_de_orgaos) · [Quadro A.1 do Ipea](https://repositorio.ipea.gov.br/bitstream/11058/13150/1/Digitalizacao_e_tecnologias_Capitulo_11.pdf)

## API de servidores

**Endpoint principal:** `GET /api/servidores`

| Parâmetro              | Comportamento                                                                    |
| ----------------------- | -------------------------------------------------------------------------------- |
| `nome`                | Correspondência exata, desconsiderando diferenças de maiúsculas e minúsculas |
| `similar`             | Similaridade por `pg_trgm` ou correspondência parcial com `ILIKE`           |
| `cargo`               | Correspondência parcial do cargo/profissão                                     |
| `orgao`               | Trecho do nome do órgão ou sigla, como `FURG` ou `UFRGS`                                |
| `uf`                  | Sigla de UF, como `RS` ou `DF`                                               |
| `pagina` ou `page`  | Número da página, iniciado em 1 (padrão: 1)                                   |
| `limite` ou `limit` | Quantidade por página (padrão: 20; máximo: 100)                               |
| `ordenar`             | `nome-asc`, `nome-desc` ou `remuneracao-desc`                              |

Os filtros podem ser combinados. Na ausência de ordenação explícita, buscas com `similar` são ordenadas por relevância; as demais utilizam `nome-asc`.

Exemplos:

```http
GET /api/servidores?nome=Maria%20Silva
GET /api/servidores?cargo=analista&uf=RS
GET /api/servidores?orgao=FURG
GET /api/servidores?orgao=furg&uf=RS
GET /api/servidores?orgao=universidade&pagina=2&limite=20
GET /api/servidores?similar=maria&limite=20
```

O retorno de sucesso é um JSON com os campos `itens` (lista de servidores) e `paginacao` (`pagina`, `limite`, `total`, `total_paginas`, `tem_anterior` e `tem_proxima`). Cada item inclui `id`, `cpf`, `nome`, `cargo`, `orgao`, `sigla_orgao`, `uf`, `tipo_vinculo` e `remuneracao`, conforme os valores armazenados. A pesquisa por `FURG` encontra 4.222 vínculos da Universidade Federal do Rio Grande nas edições incluídas. Aplicar também uma UF seleciona apenas vínculos com esse estado informado.

Para consultar um registro completo, use `GET /api/servidores/{id}` com um ID retornado na busca. O objeto `detalhes` traz os campos específicos da fonte. A interface apresenta esses campos em **Ver detalhes**.

A API valida os parâmetros e utiliza consultas SQL parametrizadas. As respostas de erro também são JSON, com `erro`, `codigo`, `status` e, quando aplicável, `campo`.

| HTTP | Situação                                                     |
| ---- | -------------------------------------------------------------- |
| 400  | Parâmetros inválidos, duplicados ou entradas não permitidas |
| 404  | Registro ou nome não encontrado, página ou rota inexistente              |
| 405  | Método HTTP não permitido                                    |
| 429  | Limite de requisições excedido (`Retry-After`)             |
| 500  | Erro interno ou falha de consulta não classificada            |
| 503  | Banco indisponível ou sobrecarga temporária                  |
| 504  | Consulta ao banco excedeu o tempo limite                       |

## Concorrência e teste de sobrecarga

O Gunicorn utiliza o modelo `gthread`. A API implementa limite de requisições por IP da conexão, controle de concorrência por semáforo e timeout de consultas ao PostgreSQL. Requisições encaminhadas pelo Next.js compartilham o IP desse serviço. Os endpoints `/` e `/health` não passam pelos limitadores de requisições. Os limites de taxa e concorrência são mantidos **na memória de cada processo do Gunicorn**, não são globais entre os workers.

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
