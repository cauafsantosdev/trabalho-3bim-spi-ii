"use client";

import Link from "next/link";
import { FormEvent, useMemo, useState } from "react";
import type { Servidor, TipoVinculo } from "@/lib/servidores";

const UFS = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"];

interface FormData {
  nome: string;
  cpf: string;
  cargo: string;
  orgao: string;
  uf: string;
  tipo_vinculo: TipoVinculo;
  remuneracao: string;
}

function dadosIniciais(servidor?: Servidor): FormData {
  return {
    nome: servidor?.nome ?? "",
    cpf: servidor?.cpf ?? "",
    cargo: servidor?.cargo ?? "",
    orgao: servidor?.orgao ?? "",
    uf: servidor?.uf ?? "",
    tipo_vinculo: servidor?.tipo_vinculo ?? "ATIVO",
    remuneracao: servidor?.remuneracao === null || servidor?.remuneracao === undefined ? "" : String(servidor.remuneracao).replace(".", ","),
  };
}

export function ServidorForm({ servidor }: { servidor?: Servidor }) {
  const inicial = useMemo(() => dadosIniciais(servidor), [servidor]);
  const [dados, setDados] = useState<FormData>(inicial);
  const [aviso, setAviso] = useState<string | null>(null);
  const editando = Boolean(servidor);

  function atualizar<K extends keyof FormData>(campo: K, valor: FormData[K]) {
    setDados((atual) => ({ ...atual, [campo]: valor }));
    setAviso(null);
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAviso(`${editando ? "Atualização" : "Cadastro"} indisponível: o backend atual não possui uma rota de ${editando ? "atualização (PUT/PATCH)" : "criação (POST)"}. Nenhum dado foi enviado ou salvo.`);
  }

  function descartar() {
    setDados(inicial);
    setAviso(null);
  }

  return (
    <form className="record-form" onSubmit={submit}>
      <fieldset>
        <legend>Dados pessoais</legend>
        <div className="form-grid form-grid-personal">
          <div className="field">
            <label htmlFor="nome-form">Nome completo <span aria-hidden="true">*</span></label>
            <input id="nome-form" required value={dados.nome} onChange={(event) => atualizar("nome", event.target.value)} placeholder="Ex.: Mariana de Souza Almeida" />
          </div>
          <div className="field">
            <label htmlFor="cpf-form">CPF <span aria-hidden="true">*</span></label>
            <input id="cpf-form" required value={dados.cpf} onChange={(event) => atualizar("cpf", event.target.value)} placeholder="000.000.000-00" />
          </div>
        </div>
      </fieldset>

      <fieldset>
        <legend>Vínculo</legend>
        <div className="form-grid">
          <div className="field">
            <label htmlFor="cargo-form">Cargo</label>
            <input id="cargo-form" value={dados.cargo} onChange={(event) => atualizar("cargo", event.target.value)} placeholder="Ex.: Analista Administrativo" />
          </div>
          <div className="field">
            <label htmlFor="orgao-form">Órgão</label>
            <input id="orgao-form" value={dados.orgao} onChange={(event) => atualizar("orgao", event.target.value)} placeholder="Ex.: Secretaria de Educação" />
          </div>
          <div className="field">
            <label htmlFor="uf-form">UF</label>
            <select id="uf-form" value={dados.uf} onChange={(event) => atualizar("uf", event.target.value)}>
              <option value="">Não informada</option>
              {UFS.map((uf) => <option key={uf}>{uf}</option>)}
            </select>
          </div>
          <div className="field">
            <label htmlFor="vinculo-form">Tipo de vínculo <span aria-hidden="true">*</span></label>
            <select id="vinculo-form" required value={dados.tipo_vinculo} onChange={(event) => atualizar("tipo_vinculo", event.target.value as TipoVinculo)}>
              <option value="ATIVO">Ativo</option>
              <option value="APOSENTADO">Aposentado</option>
            </select>
          </div>
        </div>
      </fieldset>

      <fieldset>
        <legend>Remuneração</legend>
        <div className="form-grid form-grid-remuneracao">
          <div className="field">
            <label htmlFor="remuneracao-form">Valor mensal (R$)</label>
            <input id="remuneracao-form" inputMode="decimal" value={dados.remuneracao} onChange={(event) => atualizar("remuneracao", event.target.value)} placeholder="Ex.: 12.345,67" />
          </div>
        </div>
      </fieldset>

      {aviso && <div className="status-message warning" role="status"><strong>Operação não realizada.</strong><span>{aviso}</span></div>}

      <div className="form-actions">
        {editando ? (
          <button className="button button-outline" type="button" onClick={descartar}>Descartar alterações</button>
        ) : (
          <Link className="button button-outline" href="/">Cancelar</Link>
        )}
        <button className="button button-accent" type="submit">{editando ? "Salvar alterações" : "Salvar registro"}</button>
      </div>
    </form>
  );
}
