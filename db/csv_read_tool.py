"""Importa as duas bases do Executivo Federal e conserva as colunas de cada fonte."""
import gzip
import hashlib
import os
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

DIRETORIO = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Fonte:
    arquivo: str
    tabela: str
    # Rótulo no cabeçalho, coluna no PostgreSQL e largura publicada do campo.
    campos: tuple[tuple[str, str, int], ...]
    preambulo: str | None = None


CARREIRAS = Fonte("CARREIRA_082026.csv", "carreiras", (
    ("Nome", "nome", 60),
    ("CPF", "cpf", 11),
    ("Código da carreira", "codigo_carreira", 3),
    ("Descrição do cargo emprego", "cargo", 40),
    ("UF da UPAG de vinculação", "uf", 2),
    ("Denominação do órgão de atuação", "orgao", 40),
    ("Mês de referência", "mes_referencia", 2),
    ("Valor da remuneração", "remuneracao", 18),
), preambulo="CARREIRA.082026")

APOSENTADOS = Fonte("APOSENTADOS_082025_FULL.csv", "aposentadorias", (
    ("Nome", "nome", 60),
    ("CPF", "cpf", 11),
    ("Matricula", "matricula", 12),
    ("Orgao", "orgao", 40),
    ("Sigla Orgao", "sigla_orgao", 10),
    ("Orgao vinculacao", "orgao_vinculacao", 5),
    ("Cargo emprego", "cargo", 40),
    ("Classe", "classe", 1),
    ("Padrao", "padrao", 3),
    ("Referencia", "referencia", 2),
    ("Nivel", "nivel", 3),
    ("Tipo aposentadoria", "tipo_aposentadoria", 27),
    ("Fund legal aposentadoria", "fundamento_legal", 40),
    ("Portaria aposentadoria", "portaria", 60),
    ("Dt ocorrencia inatividade", "data_inatividade", 8),
    ("Nome ocorrencia", "ocorrencia", 50),
    ("Dt ingresso servico publico", "data_ingresso_servico_publico", 8),
    ("Valor aposentadoria", "valor_aposentadoria", 14),
))

VALOR_BR = re.compile(r"-?(?:[0-9]+|[0-9]{1,3}(?:\.[0-9]{3})+),[0-9]{2}")
ROTULO_TOTAL = re.compile(r"TOTAL (?:DA CARREIRA [0-9]{3}|GERAL):")


def localizar(fonte, diretorio):
    compactado = diretorio / (fonte.arquivo + ".gz")
    return compactado if compactado.is_file() else diretorio / fonte.arquivo


def abrir(caminho, modo, **kwargs):
    return (gzip.open if caminho.suffix == ".gz" else open)(caminho, modo, **kwargs)


def ler_registros(fonte, caminho):
    # Os separadores têm posição fixa. Um ';' ou uma aspa dentro de uma
    # portaria integra o texto original e não pode deslocar datas e proventos.
    padrao = ";".join(f"(.{{{largura}}})" for _, _, largura in fonte.campos)
    layout = re.compile(padrao + (";" if fonte == CARREIRAS else ""))
    with abrir(caminho, "rt", encoding="latin-1", newline="") as arquivo:
        if fonte.preambulo and arquivo.readline().strip() != fonte.preambulo:
            raise ValueError(f"{caminho.name}: identificação da edição inesperada")
        cabecalho = arquivo.readline().strip().removesuffix(";").split(";")
        if [c.strip() for c in cabecalho] != [c for c, _, _ in fonte.campos]:
            raise ValueError(f"{caminho.name}: cabeçalho incompatível")
        for numero, linha in enumerate(arquivo, 3 if fonte.preambulo else 2):
            m = layout.fullmatch(linha.rstrip("\r\n"))
            if not m:
                raise ValueError(f"{caminho.name}, linha {numero}: estrutura de campos inválida")
            campos = [s.strip() or None for s in m.groups()]
            valor = campos[-1]
            if valor is not None:
                if not VALOR_BR.fullmatch(valor):
                    raise ValueError(f"{caminho.name}, linha {numero}: valor monetário inválido")
                campos[-1] = valor.replace(".", "").replace(",", ".")
            # Dois vínculos de carreiras têm CPF, mas vieram sem nome.
            campos[0] = campos[0] or ""
            if fonte == APOSENTADOS:
                for i in (14, 16):
                    if campos[i]:
                        d = campos[i]
                        try:
                            campos[i] = date(int(d[4:]), int(d[2:4]), int(d[:2]))
                        except ValueError as exc:
                            raise ValueError(f"{caminho.name}, linha {numero}: data inválida") from exc
            yield campos


def importar(cur, fonte, caminho, assinatura):
    cur.execute("SELECT sha256 FROM importacoes WHERE fonte = %s", (fonte.tabela,))
    if cur.fetchone() == (assinatura,):
        print(f"{fonte.arquivo} já está carregado.", flush=True)
        return False

    print(f"Importando {fonte.arquivo}…", flush=True)
    # Os identificadores SQL abaixo vêm exclusivamente dos dois layouts acima.
    cur.execute(f"TRUNCATE {fonte.tabela}")
    colunas = ", ".join(coluna for _, coluna, _ in fonte.campos)
    totais = []
    quantidade = 0
    with cur.copy(f"COPY {fonte.tabela} ({colunas}) FROM STDIN") as copia:
        for campos in ler_registros(fonte, caminho):
            if fonte == CARREIRAS and not any(campos[1:-1]) and ROTULO_TOTAL.fullmatch(campos[0]):
                totais.append((campos[0], campos[-1]))
            else:
                copia.write_row(campos)
                quantidade += 1
    if not quantidade:
        raise ValueError(f"{fonte.arquivo} não contém registros de servidores")
    if fonte == CARREIRAS:
        cur.execute("TRUNCATE totais_carreira")
        cur.executemany("INSERT INTO totais_carreira (rotulo, valor) VALUES (%s, %s)", totais)
    cur.execute("""
        INSERT INTO importacoes (fonte, arquivo, sha256, registros) VALUES (%s, %s, %s, %s)
        ON CONFLICT (fonte) DO UPDATE SET arquivo = EXCLUDED.arquivo, sha256 = EXCLUDED.sha256,
            registros = EXCLUDED.registros, importado_em = now()
    """, (fonte.tabela, fonte.arquivo, assinatura, quantidade))
    print(f"{quantidade} vínculos lidos de {fonte.arquivo}.", flush=True)
    return True


def main():
    import psycopg

    dados = Path(os.getenv("DATA_DIR", DIRETORIO))
    fontes = []
    for fonte in (CARREIRAS, APOSENTADOS):
        caminho = localizar(fonte, dados)
        with abrir(caminho, "rb") as arquivo:
            assinatura = hashlib.file_digest(arquivo, "sha256").hexdigest()
        fontes.append((fonte, caminho, assinatura))

    with psycopg.connect(host=os.getenv("DB_HOST", "localhost"), port=os.getenv("DB_PORT", "5432"),
                         dbname=os.getenv("DB_NAME", "spi"), user=os.getenv("DB_USER", "spi"),
                         password=os.getenv("DB_PASSWORD", "spi")) as conn, conn.cursor() as cur:
        # Uma transação para esquema, dados, catálogo e marcadores, mesmo com
        # dois deploys simultâneos. Uma falha reverte a carga completa.
        cur.execute("SELECT pg_advisory_xact_lock(hashtext('spi.importar_servidores'))")
        cur.execute((DIRETORIO / "db.sql").read_text(encoding="utf-8"))
        alteradas = []
        for fonte, caminho, assinatura in fontes:
            if importar(cur, fonte, caminho, assinatura):
                alteradas.append(fonte.tabela)
        print("Verificando índices de consulta…", flush=True)
        cur.execute((DIRETORIO / "indices.sql").read_text(encoding="utf-8"))
        if alteradas:
            cur.execute("REFRESH MATERIALIZED VIEW orgaos")
            for tabela in [*alteradas, "orgaos"]:
                cur.execute(f"ANALYZE {tabela}")
    print("Banco pronto para consulta.", flush=True)


if __name__ == "__main__":
    main()
