# Trabalho 3º Bimestre — SPI II

Aplicação full stack desenvolvida para o trabalho do 3º bimestre da disciplina de SPI II.

## Estrutura

```text
.
├── backend/
├── frontend/
├── db/
└── docker-compose.yml
```

A aplicação será composta por:

- backend em Python, Flask e Gunicorn;
- frontend web;
- banco de dados PostgreSQL;
- execução dos serviços com Docker Compose.

## Status

Estrutura inicial do projeto criada. A configuração dos serviços e a implementação da aplicação serão adicionadas nas próximas tarefas.

## API de servidores

`GET /api/servidores`

| Parâmetro | Descrição |
|---|---|
| `nome` | Busca exata pelo nome completo |
| `similar` | Busca aproximada pelo nome (pg_trgm / ILIKE) |
| `cargo`, `orgao` | Filtros parciais por cargo/profissão e órgão/instituição |
| `uf` | Sigla de um estado brasileiro (ex.: `SP`) |
| `pagina` (`page`) | Página desejada, a partir de 1 (padrão `1`) |
| `limite` (`limit`) | Registros por página (padrão `20`, máximo `100`) |
| `ordenar` | `nome-asc` (padrão; com `similar`, relevância), `nome-desc` ou `remuneracao-desc` |

Resposta de sucesso:

```json
{
  "itens": [{ "id": 1, "cpf": "***796204**", "nome": "...", "cargo": "...", "orgao": "...", "uf": "DF", "tipo_vinculo": "ATIVO", "remuneracao": 9996.79 }],
  "paginacao": { "pagina": 1, "limite": 20, "total": 277029, "total_paginas": 13852, "tem_anterior": false, "tem_proxima": true }
}
```

Erros são sempre JSON no formato `{ "erro": "...", "codigo": "...", "status": 400, "campo": "..." }`:

| HTTP | Códigos |
|---|---|
| 400 | `NOME_INVALIDO`, `CARGO_INVALIDO`, `ORGAO_INVALIDO`, `UF_INVALIDA`, `SQL_NAO_PERMITIDO`, `PARAMETRO_BUSCA_INVALIDO`, `PARAMETRO_DUPLICADO` |
| 404 | `NOME_NAO_ENCONTRADO`, `PAGINA_INEXISTENTE`, `ROTA_NAO_ENCONTRADA` |
| 405 | `METODO_NAO_PERMITIDO` |
| 429 | `LIMITE_REQUISICOES_EXCEDIDO` (cabeçalho `Retry-After`) |
| 500 / 503 / 504 | `ERRO_INTERNO`, `BANCO_INDISPONIVEL`, `CONSULTA_EXCEDEU_TEMPO` |

Configuração opcional (variáveis de ambiente do backend): `QUERY_TIMEOUT_MS` (padrão 5000), `RATE_LIMIT_REQUESTS` (padrão 120) e `RATE_LIMIT_WINDOW` em segundos (padrão 60).
