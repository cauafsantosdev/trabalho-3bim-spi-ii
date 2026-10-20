import math
import os
import re
import threading
import time
import unicodedata
from collections import defaultdict, deque

import psycopg
from dotenv import load_dotenv
from flask import Flask, g, jsonify, request
from psycopg import errors as pg_errors
from psycopg.rows import dict_row
from werkzeug.exceptions import HTTPException

load_dotenv()

app = Flask(__name__)


def _env_int(nome: str, padrao: int) -> int:
    """Lê uma variável de ambiente inteira positiva, usando o padrão se inválida."""
    try:
        valor = int(os.getenv(nome, padrao))
        return valor if valor > 0 else padrao
    except (TypeError, ValueError):
        return padrao


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

# Paginação: limite padrão e limite máximo de registros por página
MAX_LIMIT = 100
DEFAULT_LIMIT = 20

# Tempo máximo (ms) de uma consulta no banco antes de ser cancelada
QUERY_TIMEOUT_MS = _env_int("QUERY_TIMEOUT_MS", 5000)

# Limite de requisições por IP dentro de uma janela de tempo (segundos)
RATE_LIMIT_REQUESTS = _env_int("RATE_LIMIT_REQUESTS", 120)
RATE_LIMIT_WINDOW = _env_int("RATE_LIMIT_WINDOW", 60)

# Proteção contra sobrecarga: limite de concorrência ativa simultânea e timeout de fila
MAX_CONCURRENT_REQUESTS = _env_int("MAX_CONCURRENT_REQUESTS", 20)
CONCURRENCY_TIMEOUT_MS = _env_int("CONCURRENCY_TIMEOUT_MS", 250)
CONCURRENCY_TIMEOUT_SECS = CONCURRENCY_TIMEOUT_MS / 1000.0

# Parâmetros de busca aceitos por /api/servidores
PARAMETROS_PERMITIDOS = {
    "nome", "similar", "cargo", "orgao", "uf",
    "pagina", "page", "limite", "limit", "ordenar",
}

# Ordenações aceitas em 'ordenar' (o id sempre desempata, mantendo a paginação estável)
ORDENACOES = {
    "nome-asc": "ORDER BY nome ASC, id ASC",
    "nome-desc": "ORDER BY nome DESC, id ASC",
    "remuneracao-desc": "ORDER BY remuneracao DESC NULLS LAST, nome ASC, id ASC",
}

UFS_VALIDAS = frozenset(
    "AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split()
)

# Texto livre: letras, números, espaços e pontuação comum em nomes/cargos/órgãos.
# Curingas do LIKE ('%' e '_') e aspas duplas ficam de fora propositalmente.
TEXTO_PERMITIDO = re.compile(r"^(?:[^\W_]|[ .,\-'/()&ºª])+$")

# Defesa em profundidade contra SQL injection (a proteção principal é o uso de
# consultas parametrizadas): rejeita entradas que se pareçam com comandos SQL.
PADRAO_SQL = re.compile(
    r"""
    ;|--|/\*|\*/
    | \b(?:select|insert|update|delete|drop|alter|truncate|create|grant|revoke|union|exec|execute|copy)\b
      \s+.*?
      \b(?:from|into|table|set|where|select|all|database|schema|user|role|index|view|function)\b
    | \b(?:pg_sleep|information_schema|pg_catalog)\b
    | (?:'|\b)\s*(?:or|and)\b\s+['"]?\w+['"]?\s*(?:=|<|>|\blike\b)
    | '\s*(?:or|and|union)\b
    """,
    re.IGNORECASE | re.VERBOSE,
)


# ---------------------------------------------------------------------------
# Erros padronizados
# ---------------------------------------------------------------------------

class ApiError(Exception):
    """Erro previsto da API, convertido em resposta JSON com código HTTP."""

    def __init__(self, status: int, codigo: str, mensagem: str, campo: str | None = None,
                 headers: dict | None = None):
        super().__init__(mensagem)
        self.status = status
        self.codigo = codigo
        self.mensagem = mensagem
        self.campo = campo
        self.headers = headers or {}


def erro_json(status: int, codigo: str, mensagem: str, campo: str | None = None):
    corpo = {"erro": mensagem, "codigo": codigo, "status": status}
    if campo:
        corpo["campo"] = campo
    resposta = jsonify(corpo)
    resposta.status_code = status
    return resposta


@app.errorhandler(ApiError)
def tratar_api_error(exc: ApiError):
    resposta = erro_json(exc.status, exc.codigo, exc.mensagem, exc.campo)
    for chave, valor in exc.headers.items():
        resposta.headers[chave] = valor
    return resposta


MENSAGENS_HTTP = {
    400: ("REQUISICAO_INVALIDA", "Requisição inválida."),
    404: ("ROTA_NAO_ENCONTRADA", "A rota solicitada não existe."),
    405: ("METODO_NAO_PERMITIDO", "Método HTTP não permitido para esta rota."),
    414: ("URL_MUITO_LONGA", "A URL da requisição é longa demais."),
    431: ("CABECALHOS_MUITO_LONGOS", "Os cabeçalhos da requisição são longos demais."),
}


@app.errorhandler(HTTPException)
def tratar_http_exception(exc: HTTPException):
    status = exc.code or 500
    codigo, mensagem = MENSAGENS_HTTP.get(
        status, (re.sub(r"\W+", "_", exc.name).upper(), exc.description or exc.name)
    )
    resposta = erro_json(status, codigo, mensagem)
    if status == 405 and getattr(exc, "valid_methods", None):
        resposta.headers["Allow"] = ", ".join(exc.valid_methods)
    return resposta


@app.errorhandler(Exception)
def tratar_erro_inesperado(exc: Exception):
    # Detalhes ficam apenas no log do servidor, nunca na resposta.
    app.logger.exception("Erro inesperado: %s", exc)
    return erro_json(500, "ERRO_INTERNO", "Erro interno do servidor.")


# ---------------------------------------------------------------------------
# Limite de requisições (rate limit) em memória, por IP
# ---------------------------------------------------------------------------

class RateLimiter:
    """Janela deslizante de requisições por chave (thread-safe, por processo)."""

    def __init__(self, maximo: int, janela: int):
        self.maximo = maximo
        self.janela = janela
        self._acessos: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def verificar(self, chave: str) -> tuple[bool, int]:
        """Registra o acesso. Retorna (permitido, segundos_para_nova_tentativa)."""
        agora = time.monotonic()
        with self._lock:
            if len(self._acessos) > 10000:
                self._limpar(agora)
            fila = self._acessos[chave]
            while fila and agora - fila[0] >= self.janela:
                fila.popleft()
            if len(fila) >= self.maximo:
                return False, max(1, math.ceil(self.janela - (agora - fila[0])))
            fila.append(agora)
            return True, 0

    def _limpar(self, agora: float) -> None:
        for chave in [c for c, f in self._acessos.items() if not f or agora - f[-1] >= self.janela]:
            del self._acessos[chave]


rate_limiter = RateLimiter(RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW)


# ---------------------------------------------------------------------------
# Proteção contra sobrecarga: semáforo de concorrência com timeout
# ---------------------------------------------------------------------------

class ConcurrencyLimiter:
    """Controla o número máximo de requisições processadas simultaneamente.

    Protege a aplicação e o banco contra saturação de conexões, CPU e memória
    quando múltiplas requisições paralelas chegam ao mesmo tempo.
    """

    def __init__(self, max_concorrentes: int):
        self.max_concorrentes = max(1, max_concorrentes)
        self._semaforo = threading.BoundedSemaphore(self.max_concorrentes)
        self._ativas = 0
        self._lock = threading.Lock()

    def adquirir(self, timeout: float = 0.0) -> bool:
        """Tenta adquirir um slot de execução. Retorna True se obteve vaga dentro do timeout."""
        if timeout <= 0:
            adquiriu = self._semaforo.acquire(blocking=False)
        else:
            adquiriu = self._semaforo.acquire(blocking=True, timeout=timeout)
        if adquiriu:
            with self._lock:
                self._ativas += 1
        return adquiriu

    def liberar(self) -> None:
        """Libera o slot previamente adquirido."""
        with self._lock:
            if self._ativas > 0:
                self._ativas -= 1
                try:
                    self._semaforo.release()
                except ValueError:
                    pass

    @property
    def ativas(self) -> int:
        with self._lock:
            return self._ativas


concurrency_limiter = ConcurrencyLimiter(MAX_CONCURRENT_REQUESTS)


@app.before_request
def aplicar_controles_requisicao():
    # Rotas de checagem de saúde e CORS preflight não devem sofrer bloqueio
    if request.method == "OPTIONS" or request.path in ("/health", "/"):
        return None

    # 1. Limite de taxa de requisições por IP (Rate Limiting)
    permitido, espera = rate_limiter.verificar(request.remote_addr or "desconhecido")
    if not permitido:
        raise ApiError(
            429, "LIMITE_REQUISICOES_EXCEDIDO",
            f"Limite de requisições excedido. Tente novamente em {espera} segundo(s).",
            headers={"Retry-After": str(espera)},
        )

    # 2. Proteção contra sobrecarga: limite de concorrência ativa simultânea
    adquiriu = concurrency_limiter.adquirir(timeout=CONCURRENCY_TIMEOUT_SECS)
    if not adquiriu:
        raise ApiError(
            503, "SOBRECARGA_TEMPORARIA",
            "O servidor está temporariamente sobrecarregado. Tente novamente em instantes.",
            headers={"Retry-After": "1"},
        )
    g.concorrencia_adquirida = True
    return None


@app.teardown_request
def liberar_recursos_requisicao(exc=None):
    if getattr(g, "concorrencia_adquirida", False):
        concurrency_limiter.liberar()
        g.concorrencia_adquirida = False


# ---------------------------------------------------------------------------
# Banco de dados
# ---------------------------------------------------------------------------

def get_db_connection():
    """Retorna uma conexão ativa com o PostgreSQL configurada com dict_row."""
    return psycopg.connect(
        db_string,
        row_factory=dict_row,
        connect_timeout=5,
        options=f"-c statement_timeout={QUERY_TIMEOUT_MS}",
    )


def traduzir_erro_banco(exc: Exception) -> ApiError:
    """Converte exceções do psycopg em erros HTTP adequados."""
    if isinstance(exc, pg_errors.QueryCanceled):
        return ApiError(
            504, "CONSULTA_EXCEDEU_TEMPO",
            f"A consulta excedeu o tempo limite de {QUERY_TIMEOUT_MS / 1000:g} segundo(s). "
            "Refine os filtros e tente novamente.",
        )
    if isinstance(exc, psycopg.OperationalError):
        app.logger.error("Banco de dados indisponível: %s", exc)
        return ApiError(503, "BANCO_INDISPONIVEL", "Banco de dados indisponível no momento.")
    app.logger.exception("Erro ao consultar o banco de dados: %s", exc)
    return ApiError(500, "ERRO_BANCO_DE_DADOS", "Erro ao consultar o banco de dados.")


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
    response.headers["Access-Control-Expose-Headers"] = "Retry-After"
    return response


# ---------------------------------------------------------------------------
# Validação dos parâmetros
# ---------------------------------------------------------------------------

def _valor_unico(campo: str) -> str | None:
    """Retorna o valor (sem espaços nas pontas) de um parâmetro, ou None se vazio."""
    valores = request.args.getlist(campo)
    if not valores:
        return None
    if len(valores) > 1:
        raise ApiError(400, "PARAMETRO_DUPLICADO",
                       f"O parâmetro '{campo}' foi informado mais de uma vez.", campo)
    valor = valores[0].strip()
    return valor or None


def _rejeitar_sql(valor: str, campo: str) -> None:
    if PADRAO_SQL.search(valor):
        raise ApiError(400, "SQL_NAO_PERMITIDO",
                       f"O parâmetro '{campo}' contém comandos ou caracteres SQL não permitidos.", campo)


def ler_texto(campo: str, codigo: str, tamanho_max: int, rotulo: str) -> str | None:
    """Lê e valida um parâmetro textual (nome, cargo, órgão...)."""
    valor = _valor_unico(campo)
    if valor is None:
        return None

    if any(unicodedata.category(c).startswith("C") and c not in "\t " for c in valor):
        raise ApiError(400, codigo, f"O parâmetro '{campo}' contém caracteres de controle inválidos.", campo)

    valor = re.sub(r"\s+", " ", valor)

    if len(valor) > tamanho_max:
        raise ApiError(400, codigo,
                       f"O parâmetro '{campo}' ({rotulo}) deve ter no máximo {tamanho_max} caracteres.", campo)

    _rejeitar_sql(valor, campo)

    if not any(c.isalnum() for c in valor) or not TEXTO_PERMITIDO.match(valor):
        raise ApiError(400, codigo, f"O parâmetro '{campo}' ({rotulo}) contém caracteres inválidos.", campo)

    return valor


def ler_uf() -> str | None:
    valor = _valor_unico("uf")
    if valor is None:
        return None
    _rejeitar_sql(valor, "uf")
    valor = valor.upper()
    if valor not in UFS_VALIDAS:
        raise ApiError(400, "UF_INVALIDA",
                       f"UF inválida: '{valor[:10]}'. Informe a sigla de um estado brasileiro (ex.: SP, DF).", "uf")
    return valor


def ler_inteiro_positivo(campos: tuple[str, ...], padrao: int, maximo: int | None = None) -> int:
    """Lê um inteiro >= 1 aceitando nomes alternativos (ex.: 'limite' ou 'limit')."""
    presentes = [c for c in campos if request.args.getlist(c)]
    if not presentes:
        return padrao
    campo = presentes[0]
    valores = request.args.getlist(campo)
    if len(valores) > 1 or len(presentes) > 1:
        raise ApiError(400, "PARAMETRO_DUPLICADO",
                       f"O parâmetro '{campo}' foi informado mais de uma vez.", campo)
    bruto = valores[0].strip()
    if not bruto.isascii() or not bruto.isdigit() or int(bruto) < 1:
        raise ApiError(400, "PARAMETRO_BUSCA_INVALIDO",
                       f"O parâmetro '{campo}' deve ser um número inteiro maior que zero.", campo)
    numero = int(bruto)
    return min(numero, maximo) if maximo else numero


# ---------------------------------------------------------------------------
# Rotas
# ---------------------------------------------------------------------------

@app.get("/")
def home():
    return jsonify({
        "status": "ok",
        "service": "backend",
    })


@app.get("/health")
def health():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        return jsonify({
            "status": "healthy",
            "database": "connected",
            "concorrencia": {
                "ativas": concurrency_limiter.ativas,
                "limite": concurrency_limiter.max_concorrentes,
            },
        }), 200
    except Exception as exc:
        app.logger.error("Health check falhou: %s", exc)
        return jsonify({
            "status": "unhealthy",
            "database": "disconnected",
            "erro": "Banco de dados indisponível.",
        }), 503


@app.get("/servidores")
@app.get("/api/servidores")
def listar_servidores():
    # 1. Validação dos parâmetros de consulta
    desconhecidos = sorted(set(request.args) - PARAMETROS_PERMITIDOS)
    if desconhecidos:
        raise ApiError(
            400, "PARAMETRO_BUSCA_INVALIDO",
            f"Parâmetro(s) de busca desconhecido(s): {', '.join(p[:30] for p in desconhecidos[:5])}. "
            f"Permitidos: {', '.join(sorted(PARAMETROS_PERMITIDOS))}.",
        )

    nome = ler_texto("nome", "NOME_INVALIDO", 150, "nome")
    similar = ler_texto("similar", "NOME_INVALIDO", 150, "nome para similaridade")
    cargo = ler_texto("cargo", "CARGO_INVALIDO", 120, "cargo/profissão")
    orgao = ler_texto("orgao", "ORGAO_INVALIDO", 150, "instituição/órgão")
    uf = ler_uf()
    limite = ler_inteiro_positivo(("limite", "limit"), DEFAULT_LIMIT, MAX_LIMIT)
    pagina = ler_inteiro_positivo(("pagina", "page"), 1)
    ordenar = _valor_unico("ordenar")
    if ordenar is not None and ordenar not in ORDENACOES:
        raise ApiError(
            400, "PARAMETRO_BUSCA_INVALIDO",
            f"Valor inválido para 'ordenar'. Permitidos: {', '.join(ORDENACOES)}.", "ordenar",
        )

    # 2. Construção dinâmica e parametrizada da consulta SQL (proteção contra SQL Injection)
    conditions = []
    params = {}
    order_by = ORDENACOES[ordenar or "nome-asc"]

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
        # Sem 'ordenar' explícito, ordena pelo nível de similaridade fonética/trigramas
        # (id como desempate mantém a paginação estável)
        if ordenar is None:
            order_by = "ORDER BY similarity(nome, %(similar)s) DESC, nome ASC, id ASC"

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

    count_query = f"SELECT COUNT(*) AS total FROM servidores {where_clause}"
    query = f"""
        SELECT id, cpf, nome, cargo, orgao, uf, tipo_vinculo, remuneracao
        FROM servidores
        {where_clause}
        {order_by}
        LIMIT %(limit)s OFFSET %(offset)s
    """

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(count_query, params)
                total = cur.fetchone()["total"]

                total_paginas = math.ceil(total / limite)

                # Nome não encontrado
                if nome and total == 0:
                    raise ApiError(404, "NOME_NAO_ENCONTRADO",
                                   f"Nenhum servidor encontrado com o nome '{nome}'.", "nome")

                # Página inexistente (uma consulta sem resultados ainda possui a página 1)
                if pagina > max(total_paginas, 1):
                    raise ApiError(
                        404, "PAGINA_INEXISTENTE",
                        f"A página {pagina} não existe. Total de páginas: {total_paginas}.", "pagina",
                    )

                rows = []
                if total > 0:
                    cur.execute(query, {**params, "limit": limite, "offset": (pagina - 1) * limite})
                    rows = cur.fetchall()
    except ApiError:
        raise
    except psycopg.Error as exc:
        raise traduzir_erro_banco(exc) from exc

    return jsonify({
        "itens": [format_servidor(row) for row in rows],
        "paginacao": {
            "pagina": pagina,
            "limite": limite,
            "total": total,
            "total_paginas": total_paginas,
            "tem_anterior": pagina > 1,
            "tem_proxima": pagina < total_paginas,
        },
    }), 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, threaded=True)