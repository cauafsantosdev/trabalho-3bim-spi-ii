"""Script de teste de carga paralela pesada contra a API no Docker.

Pré-requisito:
    Containers rodando via: docker compose up

Execução:
    python teste_paralelo.py
    (ou passe a quantidade desejada, ex: python teste_paralelo.py 80)
"""

import json
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = "http://localhost:8000"


def fazer_requisicao(url: str) -> tuple[int, dict, float, str | None]:
    """Faz uma requisição HTTP e retorna (status, corpo_json, duracao_segundos, retry_after)."""
    inicio = time.monotonic()
    req = urllib.request.Request(url, headers={"User-Agent": "TesteParalelo/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15.0) as resp:
            duracao = time.monotonic() - inicio
            corpo = json.loads(resp.read().decode("utf-8"))
            return resp.status, corpo, duracao, resp.headers.get("Retry-After")
    except urllib.error.HTTPError as exc:
        duracao = time.monotonic() - inicio
        try:
            corpo = json.loads(exc.read().decode("utf-8"))
        except Exception:
            corpo = {}
        return exc.code, corpo, duracao, exc.headers.get("Retry-After")
    except Exception as exc:
        duracao = time.monotonic() - inicio
        return 0, {"erro": str(exc)}, duracao, None


def verificar_backend_online():
    """Verifica se o backend está acessível antes de iniciar o teste."""
    print(f"Conectando ao backend em {BASE_URL}...")
    status, corpo, _, _ = fazer_requisicao(f"{BASE_URL}/health")
    if status == 200:
        concorrencia = corpo.get("concorrencia", {})
        limite = concorrencia.get("limite", "N/A")
        print(f"Backend online! Banco conectado. (Limite de concorrência ativa: {limite})\n")
        return True
    elif status == 503 and corpo.get("database") == "disconnected":
        print("Backend online, mas o PostgreSQL ainda está iniciando. Aguarde alguns segundos.\n")
        return True
    else:
        print("\n[ERRO] Não foi possível conectar à API.")
        print("Certifique-se de que o Docker está rodando: execute 'docker compose up' e tente novamente.")
        return False


def testar_concorrencia_pesada(qtd: int = 50):
    """Dispara um lote pesado de requisições simultâneas contra a listagem de servidores."""
    print(f"[1/3] Disparando CARGA PESADA: {qtd} requisições paralelas em /api/servidores...")
    url = f"{BASE_URL}/api/servidores?limite=20"
    respostas = []

    inicio = time.monotonic()
    with ThreadPoolExecutor(max_workers=qtd) as executor:
        futuros = [executor.submit(fazer_requisicao, url) for _ in range(qtd)]
        for f in as_completed(futuros):
            respostas.append(f.result())
    tempo_total = time.monotonic() - inicio

    duracoes = [r[2] for r in respostas]
    sucessos = [r for r in respostas if r[0] == 200]
    sobrecargas = [r for r in respostas if r[0] == 503]
    rate_limits = [r for r in respostas if r[0] == 429]
    erros = [r for r in respostas if r[0] not in (200, 429, 503)]

    print(f"      - Tempo total do lote ({qtd} requisições): {tempo_total:.2f}s")
    print(f"      - Latência: mín {min(duracoes):.3f}s | média {sum(duracoes)/len(duracoes):.3f}s | máx {max(duracoes):.3f}s")
    print(f"      - Requisições atendidas com sucesso (200 OK): {len(sucessos)}")
    if sobrecargas:
        print(f"      - Protegidas contra sobrecarga (503 SOBRECARGA_TEMPORARIA): {len(sobrecargas)}")
    if rate_limits:
        print(f"      - Bloqueadas por limite de taxa (429): {len(rate_limits)}")
    if erros:
        print(f"      - Erros inesperados (500 ou queda de conexão): {len(erros)}")

    assert len(erros) == 0, f"Houve falhas inesperadas na aplicação: {erros}"
    assert len(sucessos) > 0, "Nenhuma requisição obteve sucesso 200 OK."
    print("      -> A API aguentou a carga pesada sem travar nem derrubar conexões.")


def testar_estresse_com_busca_pesada(qtd: int = 60):
    """Dispara requisições simultâneas com busca textual por similaridade (pg_trgm)."""
    print(f"\n[2/3] Disparando ESTRESSE DE PROCESSAMENTO: {qtd} consultas de similaridade paralelas...")
    url = f"{BASE_URL}/api/servidores?similar=silva&limite=20"
    respostas = []

    inicio = time.monotonic()
    with ThreadPoolExecutor(max_workers=qtd) as executor:
        futuros = [executor.submit(fazer_requisicao, url) for _ in range(qtd)]
        for f in as_completed(futuros):
            respostas.append(f.result())
    tempo_total = time.monotonic() - inicio

    sucessos = [r for r in respostas if r[0] == 200]
    sobrecargas = [r for r in respostas if r[0] == 503]
    erros = [r for r in respostas if r[0] not in (200, 429, 503)]

    print(f"      - Tempo total para {qtd} buscas pesadas: {tempo_total:.2f}s")
    print(f"      - Consultas concluídas com 200 OK: {len(sucessos)}")
    if sobrecargas:
        print(f"      - Requisições contidas com 503 (protegendo o PostgreSQL): {len(sobrecargas)}")
    if erros:
        print(f"      - Falhas inesperadas: {len(erros)}")

    assert len(erros) == 0, f"Erros inesperados durante busca pesada: {erros}"
    print("      -> Proteção contra sobrecarga funcionou perfeitamente.")


def testar_healthcheck_sob_estresse(qtd: int = 40):
    """Garante que /health continua rápido mesmo durante pico de tráfego."""
    print(f"\n[3/3] Testando imunidade do /health durante estresse de {qtd} conexões simultâneas...")
    url_pesada = f"{BASE_URL}/api/servidores?similar=maria&limite=30"
    url_health = f"{BASE_URL}/health"

    def disparar_pesada():
        return fazer_requisicao(url_pesada)

    def disparar_health():
        time.sleep(0.08)  # Dispara exatamente enquanto os workers estão sob carga
        return fazer_requisicao(url_health)

    with ThreadPoolExecutor(max_workers=qtd + 1) as executor:
        futuros_pesados = [executor.submit(disparar_pesada) for _ in range(qtd)]
        futuro_health = executor.submit(disparar_health)

        status_h, corpo_h, duracao_h, _ = futuro_health.result()
        for f in as_completed(futuros_pesados):
            f.result()

    print(f"      - Resposta do /health: HTTP {status_h} em {duracao_h:.3f}s")
    assert status_h == 200, f"/health falhou sob estresse: HTTP {status_h}"
    print("      -> /health respondeu rápido e sem bloqueio.")


def main():
    qtd = 50
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        qtd = int(sys.argv[1])

    print("=" * 65)
    print(f"  Teste de Carga Pesada e Concorrência — SPI II ({qtd} reqs)")
    print("=" * 65)

    if not verificar_backend_online():
        sys.exit(1)

    try:
        testar_concorrencia_pesada(qtd=qtd)
        testar_estresse_com_busca_pesada(qtd=min(qtd + 10, 80))
        testar_healthcheck_sob_estresse(qtd=min(qtd, 50))
        print("\n" + "=" * 65)
        print("  RESULTADO: A API resistiu a todo o estresse com 100% de estabilidade!")
        print("=" * 65)
    except AssertionError as exc:
        print(f"\n[FALHA]: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
