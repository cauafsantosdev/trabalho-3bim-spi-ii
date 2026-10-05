"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ServidorForm } from "@/components/ServidorForm";
import { lerServidorLocal, Servidor } from "@/lib/servidores";

export default function EditarServidorPage() {
  const params = useParams<{ id: string }>();
  const [servidor, setServidor] = useState<Servidor | null | undefined>(undefined);
  useEffect(() => setServidor(lerServidorLocal(params.id)), [params.id]);

  if (servidor === undefined) return <div className="page"><p className="mono-meta">Carregando registro…</p></div>;
  if (!servidor) {
    return (
      <div className="page narrow-page">
        <div className="status-message error"><strong>Registro indisponível.</strong><span>A edição deve ser aberta a partir de um resultado da consulta.</span></div>
        <Link className="button button-outline" href="/">Voltar para a consulta</Link>
      </div>
    );
  }

  return (
    <div className="page form-page edit-page">
      <header className="page-heading compact">
        <p className="breadcrumbs"><span>Registros</span><i>/</i><span>{servidor.nome}</span><i>/</i><strong>Editar</strong></p>
        <h1>Editar registro</h1>
      </header>
      <div className="record-identification"><strong>{servidor.nome}</strong><span>CPF&nbsp; {servidor.cpf}</span></div>
      <ServidorForm servidor={servidor} />
    </div>
  );
}
