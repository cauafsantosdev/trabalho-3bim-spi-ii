CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;

-- Uma única sequência identifica vínculos das duas fontes na consulta pública.
CREATE SEQUENCE IF NOT EXISTS vinculo_id_seq AS bigint;

-- O importador anterior gravava somente algumas colunas em servidores.
-- Guarde essa tabela no volume e libere o nome para a visão das bases completas.
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_class WHERE oid = to_regclass('servidores') AND relkind = 'r') THEN
        ALTER TABLE servidores RENAME TO servidores_legado;
        IF EXISTS (SELECT FROM servidores_legado) THEN
            PERFORM setval('vinculo_id_seq', (SELECT max(id) FROM servidores_legado));
        END IF;
    END IF;
END;
$$;

CREATE TABLE IF NOT EXISTS carreiras (
    id bigint PRIMARY KEY DEFAULT nextval('vinculo_id_seq'),
    nome text NOT NULL,
    cpf text NOT NULL,
    codigo_carreira text,
    cargo text,
    uf text,
    orgao text,
    mes_referencia text,
    remuneracao numeric
);

CREATE TABLE IF NOT EXISTS totais_carreira (
    rotulo text PRIMARY KEY,
    valor numeric NOT NULL
);

CREATE TABLE IF NOT EXISTS aposentadorias (
    id bigint PRIMARY KEY DEFAULT nextval('vinculo_id_seq'),
    nome text NOT NULL,
    cpf text NOT NULL,
    matricula text,
    orgao text,
    sigla_orgao text,
    orgao_vinculacao text,
    cargo text,
    classe text,
    padrao text,
    referencia text,
    nivel text,
    tipo_aposentadoria text,
    fundamento_legal text,
    portaria text,
    data_inatividade date,
    ocorrencia text,
    data_ingresso_servico_publico date,
    valor_aposentadoria numeric
);

CREATE TABLE IF NOT EXISTS importacoes (
    fonte text PRIMARY KEY,
    arquivo text NOT NULL,
    sha256 text NOT NULL,
    registros bigint NOT NULL,
    importado_em timestamptz NOT NULL DEFAULT now()
);

-- O arquivo de carreiras traz o nome do órgão. As siglas vêm dos registros
-- de aposentadoria com essa mesma denominação.
CREATE MATERIALIZED VIEW IF NOT EXISTS orgaos AS
SELECT nome, coalesce(array_agg(sigla ORDER BY sigla) FILTER (WHERE sigla IS NOT NULL),
                      ARRAY[]::text[]) AS siglas
FROM (
    SELECT DISTINCT orgao AS nome, sigla_orgao AS sigla FROM aposentadorias
    UNION
    SELECT DISTINCT orgao, NULL::text FROM carreiras
) AS fontes
WHERE nome IS NOT NULL
GROUP BY nome
WITH NO DATA;

CREATE UNIQUE INDEX IF NOT EXISTS orgaos_nome_idx ON orgaos (nome);

-- Siglas institucionais que diferem do cadastro da folha ou só aparecem
-- na base de carreiras. Os nomes à esquerda são os publicados nos arquivos.
CREATE OR REPLACE VIEW siglas_universidades (orgao, sigla) AS VALUES
    ('FUNDACAO UNIVERSIDADE DO AMAZONAS', 'UFAM'),
    ('FUNDACAO UNIV. FEDERAL DE OURO PRETO', 'UFOP'),
    ('FUNDACAO UNIVERSIDADE FEDERAL DE PELOTAS', 'UFPEL'),
    ('UNIVERSIDADE FEDERAL DE SAO CARLOS', 'UFSCAR'),
    ('FUND. UNIVERSIDADE DE SAO JOAO DEL REI', 'UFSJ'),
    ('FUNDACAO UNIVERSIDADE FEDERAL DE SERGIPE', 'UFS'),
    ('FUNDACAO UNIVERSIDADE FED. DO TOCANTINS', 'UFT'),
    ('UNIV.FED. DA INTEGRACAO LATINO-AMERICANA', 'UNILA'),
    ('UNIVERSIDADE FEDERAL DE GOIAS', 'UFG'),
    ('UNIVERSIDADE FEDERAL DO CEARA', 'UFC'),
    ('UNIVERSIDADE FEDERAL DO SUL DA BAHIA', 'UFSB'),
    ('UNIVERSIDADE FEDERAL DE ALFENAS', 'UNIFAL'),
    ('UNIVERSIDADE FED. RURAL DO SEMI-ARIDO', 'UFERSA');

CREATE OR REPLACE VIEW servidores AS
SELECT c.id, c.cpf, c.nome, c.cargo, c.orgao,
       coalesce((SELECT u.sigla FROM siglas_universidades u WHERE u.orgao = c.orgao),
                CASE WHEN cardinality(o.siglas) = 1 THEN o.siglas[1] END) AS sigla_orgao,
       c.uf, 'ATIVO'::text AS tipo_vinculo, c.remuneracao,
       jsonb_build_object('codigo_carreira', c.codigo_carreira,
                          'mes_referencia', c.mes_referencia) AS detalhes
FROM carreiras c LEFT JOIN orgaos o ON o.nome = c.orgao
UNION ALL
SELECT a.id, a.cpf, a.nome, a.cargo, a.orgao, a.sigla_orgao,
       NULL::text AS uf, 'APOSENTADO'::text AS tipo_vinculo, a.valor_aposentadoria,
       to_jsonb(a) - ARRAY['id','cpf','nome','cargo','orgao','sigla_orgao','valor_aposentadoria']
FROM aposentadorias a;
