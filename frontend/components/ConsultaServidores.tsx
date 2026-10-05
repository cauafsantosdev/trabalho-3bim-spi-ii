"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import {
  ApiError,
  consultarServidores,
  FiltrosServidor,
  formatarMoeda,
  formatarVinculo,
  salvarServidorLocal,
  Servidor,
} from "@/lib/servidores";

const UFS = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"];
const filtrosIniciais: FiltrosServidor = { nome: "", modoNome: "similar", cargo: "", orgao: "", uf: "", limite: 100 };
type Ordenacao = "nome-asc" | "nome-desc" | "remuneracao-desc";

export function ConsultaServidores() {
  const [filtros, setFiltros] = useState(filtrosIniciais);
  const [resultados, setResultados] = useState<Servidor[]>([]);
  const [selecionado, setSelecionado] = useState<Servidor | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [buscaExataVazia, setBuscaExataVazia] = useState(false);
  const [ordenacao, setOrdenacao] = useState<Ordenacao>("nome-asc");
  const [avisoAcao, setAvisoAcao] = useState<string | null>(null);

  const executarBusca = useCallback(async (valores: FiltrosServidor, signal?: AbortSignal) => {
    setCarregando(true);
    setErro(null);
    setBuscaExataVazia(false);
    setAvisoAcao(null);
    try {
      const data = await consultarServidores(valores, signal);
      setResultados(data);
      data.forEach(salvarServidorLocal);
      setSelecionado((atual) => data.find((item) => item.id === atual?.id) ?? data[0] ?? null);
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
      if (error instanceof ApiError && error.status === 404 && valores.modoNome === "exata") {
        setResultados([]);
        setSelecionado(null);
        setBuscaExataVazia(true);
      } else {
        setResultados([]);
        setSelecionado(null);
        setErro(error instanceof Error ? error.message : "Não foi possível concluir a consulta.");
      }
    } finally {
      if (!signal?.aborted) setCarregando(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void executarBusca(filtrosIniciais, controller.signal);
    return () => controller.abort();
  }, [executarBusca]);

  const ordenados = useMemo(() => {
    const data = [...resultados];
    if (ordenacao === "nome-desc") return data.sort((a, b) => b.nome.localeCompare(a.nome, "pt-BR"));
    if (ordenacao === "remuneracao-desc") return data.sort((a, b) => (b.remuneracao ?? -1) - (a.remuneracao ?? -1));
    return data.sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR"));
  }, [resultados, ordenacao]);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void executarBusca(filtros);
  }

  function escolher(servidor: Servidor) {
    salvarServidorLocal(servidor);
    setSelecionado(servidor);
    setAvisoAcao(null);
  }

  return (
    <div className="page query-page">
      <header className="page-heading">
        <p className="eyebrow">Consulta pública</p>
        <h1>Consultar servidores</h1>
        <p className="page-lead">Pesquise os registros disponíveis na base.</p>
      </header>

      <form className="search-form" onSubmit={submit}>
        <div className="field field-name">
          <label htmlFor="nome">Buscar por nome</label>
          <input id="nome" value={filtros.nome} onChange={(event) => setFiltros({ ...filtros, nome: event.target.value })} placeholder={filtros.modoNome === "exata" ? "Digite o nome completo" : "Nome ou parte do nome"} />
          <div className="search-mode" aria-label="Modo da busca por nome">
            <button className={filtros.modoNome === "similar" ? "selected" : ""} type="button" onClick={() => setFiltros({ ...filtros, modoNome: "similar" })}>Aproximada</button>
            <button className={filtros.modoNome === "exata" ? "selected" : ""} type="button" onClick={() => setFiltros({ ...filtros, modoNome: "exata" })}>Exata</button>
          </div>
        </div>
        <div className="field">
          <label htmlFor="cargo">Cargo</label>
          <input id="cargo" value={filtros.cargo} onChange={(event) => setFiltros({ ...filtros, cargo: event.target.value })} placeholder="Todos" />
        </div>
        <div className="field">
          <label htmlFor="orgao">Órgão</label>
          <input id="orgao" value={filtros.orgao} onChange={(event) => setFiltros({ ...filtros, orgao: event.target.value })} placeholder="Todos" />
        </div>
        <div className="field field-uf">
          <label htmlFor="uf">UF</label>
          <select id="uf" value={filtros.uf} onChange={(event) => setFiltros({ ...filtros, uf: event.target.value })}>
            <option value="">Todas</option>
            {UFS.map((uf) => <option key={uf}>{uf}</option>)}
          </select>
        </div>
        <button className="button button-dark search-button" type="submit" disabled={carregando}>{carregando ? "Consultando…" : "Pesquisar"}</button>
      </form>

      <div className="query-layout">
        <section className="results" aria-live="polite">
          <div className="results-toolbar">
            <span className="mono-meta">{carregando ? "Carregando registros…" : resultados.length === 100 ? "100 registros encontrados · limite da API" : `${resultados.length} ${resultados.length === 1 ? "registro encontrado" : "registros encontrados"}`}</span>
            <label className="sort-control">
              <span>Ordenar por</span>
              <select value={ordenacao} onChange={(event) => setOrdenacao(event.target.value as Ordenacao)}>
                <option value="nome-asc">Nome (A–Z)</option>
                <option value="nome-desc">Nome (Z–A)</option>
                <option value="remuneracao-desc">Maior remuneração</option>
              </select>
            </label>
          </div>

          {erro && <div className="status-message error"><strong>Falha na consulta.</strong><span>{erro}</span></div>}
          {buscaExataVazia && <div className="status-message"><strong>Nenhum resultado exato.</strong><span>A API não encontrou um servidor com esse nome completo.</span></div>}
          {!carregando && !erro && !buscaExataVazia && resultados.length === 0 && <div className="status-message"><strong>Nenhum registro encontrado.</strong><span>Revise os filtros e tente novamente.</span></div>}

          {resultados.length > 0 && (
            <div className="table-wrap">
              <table>
                <thead><tr><th>Nome</th><th>Cargo</th><th>Órgão</th><th>UF</th><th>Vínculo</th><th>Remuneração</th></tr></thead>
                <tbody>
                  {ordenados.map((servidor) => (
                    <tr className={selecionado?.id === servidor.id ? "selected-row" : ""} key={servidor.id} onClick={() => escolher(servidor)}>
                      <td data-label="Nome"><button className="row-name" type="button" onClick={() => escolher(servidor)}>{servidor.nome}</button></td>
                      <td data-label="Cargo">{servidor.cargo || "—"}</td>
                      <td data-label="Órgão">{servidor.orgao || "—"}</td>
                      <td data-label="UF">{servidor.uf || "—"}</td>
                      <td data-label="Vínculo">{formatarVinculo(servidor.tipo_vinculo)}</td>
                      <td data-label="Remuneração">{formatarMoeda(servidor.remuneracao)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <aside className="detail-panel" aria-live="polite">
          {selecionado ? (
            <>
              <p className="mono-meta">Registro #{selecionado.id}</p>
              <h2>{selecionado.nome}</h2>
              <dl>
                <div><dt>CPF</dt><dd>{selecionado.cpf}</dd></div>
                <div><dt>Cargo</dt><dd>{selecionado.cargo || "Não informado"}</dd></div>
                <div><dt>Órgão</dt><dd>{selecionado.orgao || "Não informado"}</dd></div>
                <div><dt>UF</dt><dd>{selecionado.uf || "Não informada"}</dd></div>
                <div><dt>Vínculo</dt><dd>{formatarVinculo(selecionado.tipo_vinculo)}</dd></div>
                <div><dt>Remuneração</dt><dd>{formatarMoeda(selecionado.remuneracao)}</dd></div>
              </dl>
              {avisoAcao && <p className="inline-notice">{avisoAcao}</p>}
              <div className="detail-actions">
                <Link className="button button-outline" href={`/servidores/${selecionado.id}`} onClick={() => salvarServidorLocal(selecionado)}>Ver detalhes</Link>
                <Link className="button button-outline" href={`/servidores/${selecionado.id}/editar`} onClick={() => salvarServidorLocal(selecionado)}>Editar</Link>
                <button className="button button-danger" type="button" onClick={() => setAvisoAcao("Exclusão indisponível: o backend atual não possui uma rota DELETE.")}>Excluir</button>
              </div>
            </>
          ) : (
            <div className="panel-empty"><span>Detalhes</span><p>Selecione um registro na lista para visualizar os dados.</p></div>
          )}
        </aside>
      </div>
    </div>
  );
}
