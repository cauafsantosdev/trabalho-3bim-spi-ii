import csv
import psycopg2
from psycopg2.extras import execute_values

DB_CONFIG = {
    "dbname": "spi",
    "user": "spi",
    "password": "spi",
    "host": "localhost",
    "port": 5432,
}

BATCH_SIZE = 5000  # Inserções em blocos de 5000 para alto desempenho

def criar_tabelas():
    ddl = """
    CREATE EXTENSION IF NOT EXISTS pg_trgm;

    CREATE TABLE IF NOT EXISTS servidores (
        id BIGSERIAL PRIMARY KEY,
        cpf VARCHAR(14) NOT NULL,
        nome VARCHAR(150) NOT NULL,
        cargo VARCHAR(100),
        orgao VARCHAR(150),
        uf VARCHAR(2),
        tipo_vinculo VARCHAR(20) NOT NULL,
        remuneracao NUMERIC(12, 2)
    );

    CREATE INDEX IF NOT EXISTS idx_servidores_cpf ON servidores(cpf);
    CREATE INDEX IF NOT EXISTS idx_servidores_uf ON servidores(uf);
    CREATE INDEX IF NOT EXISTS idx_servidores_tipo_vinculo ON servidores(tipo_vinculo);

    CREATE INDEX IF NOT EXISTS idx_servidores_nome_trgm ON servidores USING gin (nome gin_trgm_ops);
    CREATE INDEX IF NOT EXISTS idx_servidores_cargo_trgm ON servidores USING gin (cargo gin_trgm_ops);
    CREATE INDEX IF NOT EXISTS idx_servidores_orgao_trgm ON servidores USING gin (orgao gin_trgm_ops);
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(ddl)
        conn.commit()
        print("[+] Extensão pg_trgm, tabela 'servidores' e índices criados com sucesso!")
    finally:
        conn.close()

def parse_remuneracao(valor_str: str):
    """Trata strings monetárias brasileiras (ex: '  9.996,79 ') para float."""
    if not valor_str:
        return None
    cleaned = valor_str.strip().replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


def carregar_carreiras(caminho_arquivo: str):
    """
    Lê o arquivo de Carreiras/Cargos (ativos) e insere na tabela servidores.
    Campos esperados:
    Nome;CPF;Código da carreira;Descrição do cargo;UF;Órgão;Mês;Valor da remuneração;
    """
    print(f"[*] Processando arquivo de Carreiras: {caminho_arquivo}")
    records = []
    
    with open(caminho_arquivo, mode="r", encoding="latin1") as f:
        reader = csv.reader(f, delimiter=";")
        
        for linha in reader:
            if not linha or len(linha) < 8:
                continue

            # Se for a linha de cabeçalho, pula
            if "Nome" in linha[0] or "CPF" in linha[1]:
                continue

            nome = linha[0].strip()
            cpf = linha[1].strip()
            cargo = linha[3].strip()
            uf = linha[4].strip() if linha[4].strip() else None
            orgao = linha[5].strip()
            remuneracao = parse_remuneracao(linha[7])

            records.append((
                cpf,
                nome,
                cargo,
                orgao,
                uf,
                'ATIVO',
                remuneracao
            ))

    _inserir_em_lote(records)
    print(f"[+] {len(records)} registros de Carreiras/Ativos inseridos com sucesso!")


def carregar_aposentados(caminho_arquivo: str):
    """
    Lê o arquivo de Aposentados e insere na tabela servidores.
    Campos esperados (18 colunas):
    0: Nome | 1: CPF | 3: Órgão | 6: Cargo | 17: Proventos
    UF fica NULL e tipo_vinculo fica 'APOSENTADO'.
    """
    print(f"[*] Processando arquivo de Aposentados: {caminho_arquivo}")
    records = []
    
    with open(caminho_arquivo, mode="r", encoding="latin1") as f:
        reader = csv.reader(f, delimiter=";")
        
        for linha in reader:
            if not linha or len(linha) < 18:
                continue

            # Caso o arquivo contenha cabeçalho
            if "Nome" in linha[0] or "CPF" in linha[1]:
                continue

            nome = linha[0].strip()
            cpf = linha[1].strip()
            orgao = linha[3].strip()
            cargo = linha[6].strip()
            remuneracao = parse_remuneracao(linha[17])
            uf = None  # Aposentados não possuem UF explícita na base

            records.append((
                cpf,
                nome,
                cargo,
                orgao,
                uf,
                'APOSENTADO',
                remuneracao
            ))

    _inserir_em_lote(records)
    print(f"[+] {len(records)} registros de Aposentados inseridos com sucesso!")


def _inserir_em_lote(records):
    """Executa o INSERT em lotes otimizados utilizando execute_values."""
    if not records:
        return

    query = """
        INSERT INTO servidores (cpf, nome, cargo, orgao, uf, tipo_vinculo, remuneracao)
        VALUES %s;
    """

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            execute_values(cur, query, records, page_size=BATCH_SIZE)
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"[!] Erro ao inserir dados no banco: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    # Exemplo de execução apontando para os seus arquivos:
    # carregar_carreiras("caminho/para/carreiras.txt")
    # carregar_aposentados("caminho/para/aposentados.112016.csv")
    criar_tabelas()
    carregar_carreiras("CARREIRA-012017.TXT")
    carregar_aposentados("APOSENTADOS.112016.csv")