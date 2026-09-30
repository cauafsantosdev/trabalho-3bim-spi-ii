-- Habilita a extensão para busca por similaridade e operadores de trigramas
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Criação da tabela unificada de servidores (ativos e aposentados)
CREATE TABLE IF NOT EXISTS servidores (
id BIGSERIAL PRIMARY KEY,
cpf VARCHAR(14) NOT NULL,
nome VARCHAR(150) NOT NULL,
cargo VARCHAR(120),
orgao VARCHAR(150),
sigla_orgao VARCHAR(30),
uf CHAR(2),
tipo_vinculo VARCHAR(20) NOT NULL CHECK (tipo_vinculo IN ('ATIVO', 'APOSENTADO')),
remuneracao NUMERIC(12, 2) DEFAULT 0.00,
criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ===============================================================
-- ÍNDICES B-TREE (Busca exata, filtros categóricos e ordenações)
-- ===============================================================

-- Busca direta por CPF
CREATE INDEX IF NOT EXISTS idx_servidores_cpf
ON servidores (cpf);

-- Filtro exato por Estado (UF)
CREATE INDEX IF NOT EXISTS idx_servidores_uf
ON servidores (uf);

-- Filtro por vínculo ('ATIVO' vs 'APOSENTADO')
CREATE INDEX IF NOT EXISTS idx_servidores_tipo_vinculo
ON servidores (tipo_vinculo);

-- Filtro composto muito comum: Estado + Órgão
CREATE INDEX IF NOT EXISTS idx_servidores_uf_orgao
ON servidores (uf, orgao);

-- ===============================================================
-- ÍNDICES GIN / pg_trgm (Busca textual por aproximação e LIKE/ILIKE)
-- Permite queries como:
--   WHERE nome ILIKE '%silva%'
--   WHERE nome % 'Rodrigo' (operador de similaridade)
-- ===============================================================

-- Busca textual e similaridade por Nome
CREATE INDEX IF NOT EXISTS idx_servidores_nome_trgm
ON servidores USING gin (nome gin_trgm_ops);

-- Busca textual e similaridade por Cargo / Profissão
CREATE INDEX IF NOT EXISTS idx_servidores_cargo_trgm
ON servidores USING gin (cargo gin_trgm_ops);

-- Busca textual e similaridade por Órgão / Instituição
CREATE INDEX IF NOT EXISTS idx_servidores_orgao_trgm
ON servidores USING gin (orgao gin_trgm_ops);