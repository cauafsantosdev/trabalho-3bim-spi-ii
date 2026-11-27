-- Na primeira carga, construa os índices depois do COPY dos arquivos completos.
CREATE INDEX IF NOT EXISTS carreiras_cpf_idx ON carreiras (cpf);
CREATE INDEX IF NOT EXISTS aposentadorias_cpf_idx ON aposentadorias (cpf);
CREATE INDEX IF NOT EXISTS carreiras_uf_idx ON carreiras (uf);
CREATE INDEX IF NOT EXISTS carreiras_orgao_idx ON carreiras (orgao);
CREATE INDEX IF NOT EXISTS aposentadorias_orgao_idx ON aposentadorias (orgao);

CREATE INDEX IF NOT EXISTS carreiras_ordem_nome_idx ON carreiras (nome, id);
CREATE INDEX IF NOT EXISTS aposentadorias_ordem_nome_idx ON aposentadorias (nome, id);
CREATE INDEX IF NOT EXISTS carreiras_nome_exato_idx ON carreiras (lower(trim(nome)));
CREATE INDEX IF NOT EXISTS aposentadorias_nome_exato_idx ON aposentadorias (lower(trim(nome)));
CREATE INDEX IF NOT EXISTS carreiras_remuneracao_idx ON carreiras (remuneracao DESC NULLS LAST, nome, id);
CREATE INDEX IF NOT EXISTS aposentadorias_valor_idx ON aposentadorias (valor_aposentadoria DESC NULLS LAST, nome, id);

CREATE INDEX IF NOT EXISTS carreiras_nome_trgm_idx ON carreiras USING gin (nome gin_trgm_ops);
CREATE INDEX IF NOT EXISTS aposentadorias_nome_trgm_idx ON aposentadorias USING gin (nome gin_trgm_ops);
CREATE INDEX IF NOT EXISTS carreiras_cargo_trgm_idx ON carreiras USING gin (cargo gin_trgm_ops);
CREATE INDEX IF NOT EXISTS aposentadorias_cargo_trgm_idx ON aposentadorias USING gin (cargo gin_trgm_ops);
