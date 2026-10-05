"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowIcon } from "@/components/Icons";
import { formatarMoeda, formatarVinculo, lerServidorLocal, Servidor } from "@/lib/servidores";

export default function ServidorDetalhesPage() {
  const params = useParams<{ id: string }>();
  const [servidor, setServidor] = useState<Servidor | null | undefined>(undefined);
  const [aviso, setAviso] = useState<string | null>(null);

  useEffect(() => setServidor(lerServidorLocal(params.id)), [params.id]);

  if (servidor === undefined) return <div className="page"><p className="mono-meta">Carregando registro…</p></div>;
  if (!servidor) {
    return (
      <div className="page narrow-page">
        <div className="status-message error"><strong>Registro indisponível.</strong><span>A API não possui consulta por ID. Abra os detalhes a partir de um resultado da busca.</span></div>
        <Link className="button button-outline" href="/">Voltar para a consulta</Link>
      </div>
    );
  }

  return (
    <article className="page details-page">
      <Link className="back-link" href="/"><ArrowIcon /> Voltar para os resultados</Link>
      <header className="detail-heading">
        <h1>{servidor.nome}</h1>
        <p className="mono-meta">Registro #{servidor.id}</p>
      </header>
      <dl className="details-grid">
        <div><dt>CPF</dt><dd>{servidor.cpf}</dd></div>
        <div><dt>UF</dt><dd>{servidor.uf || "Não informada"}</dd></div>
        <div><dt>Cargo</dt><dd>{servidor.cargo || "Não informado"}</dd></div>
        <div><dt>Vínculo</dt><dd>{formatarVinculo(servidor.tipo_vinculo)}</dd></div>
        <div><dt>Órgão</dt><dd>{servidor.orgao || "Não informado"}</dd></div>
        <div><dt>Remuneração</dt><dd>{formatarMoeda(servidor.remuneracao)}</dd></div>
      </dl>
      {aviso && <div className="status-message warning"><strong>Exclusão não realizada.</strong><span>{aviso}</span></div>}
      <div className="record-actions">
        <Link className="button button-outline" href={`/servidores/${servidor.id}/editar`}>Editar</Link>
        <button className="button button-danger" type="button" onClick={() => setAviso("O backend atual não possui uma rota DELETE. Nenhum dado foi removido.")}>Excluir</button>
      </div>
    </article>
  );
}
