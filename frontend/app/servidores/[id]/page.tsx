"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowIcon } from "@/components/Icons";
import { consultarServidor, formatarMoeda, formatarVinculo, salvarServidorLocal, ServidorDetalhado } from "@/lib/servidores";

const camposDaFonte: Record<string, string> = {
  codigo_carreira: "Código da carreira",
  mes_referencia: "Mês de referência",
  matricula: "Matrícula",
  orgao_vinculacao: "Código do órgão de vinculação",
  classe: "Classe",
  padrao: "Padrão",
  referencia: "Referência",
  nivel: "Nível",
  tipo_aposentadoria: "Tipo de aposentadoria",
  fundamento_legal: "Fundamento legal",
  portaria: "Portaria de aposentadoria",
  data_inatividade: "Data de inatividade",
  ocorrencia: "Nome da ocorrência",
  data_ingresso_servico_publico: "Data de ingresso no serviço público",
};

function formatarCampo(chave: string, valor: string | null) {
  if (!valor) return "Não informado";
  return chave.startsWith("data_") ? valor.split("-").reverse().join("/") : valor;
}

export default function ServidorDetalhesPage() {
  const params = useParams<{ id: string }>();
  const [servidor, setServidor] = useState<ServidorDetalhado | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setServidor(null);
    setErro(null);
    setAviso(null);
    consultarServidor(params.id, controller.signal)
      .then((dado) => { if (!controller.signal.aborted) setServidor(dado); })
      .catch((e: Error) => { if (!controller.signal.aborted) setErro(e.message); });
    return () => controller.abort();
  }, [params.id]);

  if (!erro && !servidor) return <div className="page"><p className="mono-meta">Carregando registro…</p></div>;
  if (!servidor) {
    return (
      <div className="page narrow-page">
        <div className="status-message error"><strong>Registro indisponível.</strong><span>{erro}</span></div>
        <Link className="button button-outline" href="/">Voltar para a consulta</Link>
      </div>
    );
  }

  return (
    <article className="page details-page">
      <Link className="back-link" href="/"><ArrowIcon /> Voltar para os resultados</Link>
      <header className="detail-heading">
        <h1>{servidor.nome || "Nome não informado"}</h1>
        <p className="mono-meta">Registro #{servidor.id}</p>
      </header>
      <dl className="details-grid">
        <div><dt>CPF</dt><dd>{servidor.cpf}</dd></div>
        <div><dt>UF</dt><dd>{servidor.uf || "Não informada"}</dd></div>
        <div><dt>Cargo</dt><dd>{servidor.cargo || "Não informado"}</dd></div>
        <div><dt>Vínculo</dt><dd>{formatarVinculo(servidor.tipo_vinculo)}</dd></div>
        <div><dt>Órgão</dt><dd>{servidor.orgao || "Não informado"}</dd></div>
        <div><dt>Sigla do órgão</dt><dd>{servidor.sigla_orgao || "Não informada"}</dd></div>
        <div><dt>{servidor.tipo_vinculo === "APOSENTADO" ? "Valor da aposentadoria" : "Remuneração"}</dt><dd>{formatarMoeda(servidor.remuneracao)}</dd></div>
        {Object.entries(camposDaFonte).filter(([chave]) => chave in servidor.detalhes).map(([chave, rotulo]) => (
          <div key={chave}><dt>{rotulo}</dt><dd>{formatarCampo(chave, servidor.detalhes[chave])}</dd></div>
        ))}
      </dl>
      {aviso && <div className="status-message warning"><strong>Exclusão não realizada.</strong><span>{aviso}</span></div>}
      <div className="record-actions">
        <Link className="button button-outline" href={`/servidores/${servidor.id}/editar`} onClick={() => salvarServidorLocal(servidor)}>Editar</Link>
        <button className="button button-danger" type="button" onClick={() => setAviso("O backend atual não possui uma rota DELETE. Nenhum dado foi removido.")}>Excluir</button>
      </div>
    </article>
  );
}
