import os

import psycopg
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from psycopg.rows import dict_row

load_dotenv()

app = Flask(__name__)

# Configurações de conexão com o banco de dados PostgreSQL
db_user = os.getenv("DB_USER", "spi")
db_password = os.getenv("DB_PASSWORD", "spi")
db_host = os.getenv("DB_HOST", "localhost")
db_port = os.getenv("DB_PORT", "5432")
db_name = os.getenv("DB_NAME", "spi")

db_string = (
    f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
)

app.config["DB_URL"] = db_string

# Limite padrão e limite máximo de registros retornados
MAX_LIMIT = 100
DEFAULT_LIMIT = 100


def get_db_connection():
    """Retorna uma conexão ativa com o PostgreSQL configurada com dict_row."""
    return psycopg.connect(
        db_string,
        row_factory=dict_row,
        connect_timeout=5,
    )


def format_servidor(row: dict) -> dict:
    """Padroniza o registro do servidor para serialização JSON."""
    return {
        "id": row["id"],
        "cpf": row["cpf"],
        "nome": row["nome"],
        "cargo": row["cargo"],
        "orgao": row["orgao"],
        "uf": row["uf"],
        "tipo_vinculo": row["tipo_vinculo"],
        "remuneracao": float(row["remuneracao"]) if row["remuneracao"] is not None else None,
    }


@app.after_request
def add_cors_headers(response):
    """Permite requisições do frontend em outros domínios/portas (CORS)."""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return response


@app.get("/")
def home():
    return jsonify({
        "status": "ok",
        "service": "backend",
        "database_url": db_string,
    })


@app.get("/health")
def health():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        return jsonify({"status": "healthy", "database": "connected"}), 200
    except Exception as exc:
        return jsonify({
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(exc),
        }), 500


@app.get("/servidores")
@app.get("/api/servidores")
def listar_servidores():
    # 1. Obtenção e higienização dos parâmetros de consulta 
    nome = request.args.get("nome", type=str)
    cargo = request.args.get("cargo", type=str)
    uf = request.args.get("uf", type=str)
    orgao = request.args.get("orgao", type=str)
    similar = request.args.get("similar", type=str)
    limite_param = request.args.get("limite") or request.args.get("limit")

    nome = nome.strip() if nome and nome.strip() else None
    cargo = cargo.strip() if cargo and cargo.strip() else None
    uf = uf.strip().upper() if uf and uf.strip() else None
    orgao = orgao.strip() if orgao and orgao.strip() else None
    similar = similar.strip() if similar and similar.strip() else None

    # Validação e aplicação do teto de limite
    if limite_param is not None:
        try:
            limite = int(limite_param)
            if limite <= 0:
                limite = DEFAULT_LIMIT
            else:
                limite = min(limite, MAX_LIMIT)
        except ValueError:
            return jsonify({
                "erro": "O parâmetro 'limite' deve ser um número inteiro válido."
            }), 400
    else:
        limite = DEFAULT_LIMIT

    # 2. Construção dinâmica e parametrizada da consulta SQL (proteção contra SQL Injection)
    conditions = []
    params = {}
    order_by = "ORDER BY nome ASC"

    # Busca direta por nome completo
    if nome:
        conditions.append("LOWER(TRIM(nome)) = LOWER(%(nome)s)")
        params["nome"] = nome

    # Busca por similaridade e padrões parciais
    if similar:
        # Utiliza o operador de similaridade do pg_trgm (%% no psycopg) ou correspondência parcial (ILIKE)
        conditions.append("(nome %% %(similar)s OR nome ILIKE %(similar_like)s)")
        params["similar"] = similar
        params["similar_like"] = f"%{similar}%"
        # Ordena prioritariamente pelo nível de similaridade fonética/trigramas
        order_by = "ORDER BY similarity(nome, %(similar)s) DESC, nome ASC"

    # Filtros por cargo, UF e órgão (combináveis)
    if cargo:
        conditions.append("cargo ILIKE %(cargo)s")
        params["cargo"] = f"%{cargo}%"

    if uf:
        conditions.append("UPPER(uf) = %(uf)s")
        params["uf"] = uf

    if orgao:
        conditions.append("orgao ILIKE %(orgao)s")
        params["orgao"] = f"%{orgao}%"

    # Montagem da cláusula WHERE caso haja filtros
    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    # Adiciona o parâmetro de limite à query
    params["limit"] = limite

    query = f"""
        SELECT id, cpf, nome, cargo, orgao, uf, tipo_vinculo, remuneracao
        FROM servidores
        {where_clause}
        {order_by}
        LIMIT %(limit)s
    """

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchall()

        # Tratar nome não encontrado
        if nome and not rows:
            return jsonify({
                "erro": f"Nenhum servidor encontrado com o nome '{nome}'."
            }), 404

        resultados = [format_servidor(row) for row in rows]
        return jsonify(resultados), 200

    except Exception as exc:
        return jsonify({
            "erro": "Erro ao consultar o banco de dados.",
            "detalhes": str(exc)
        }), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port)