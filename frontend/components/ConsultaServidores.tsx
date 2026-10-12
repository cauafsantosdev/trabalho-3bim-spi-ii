"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import {
  ApiError,
  consultarServidores,
  FiltrosServidor,
  formatarMoeda,
  formatarVinculo,
  Ordenacao,
  Paginacao,
  salvarServidorLocal,
  Servidor,
} from "@/lib/servidores";

const UFS = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"];
const filtrosIniciais: FiltrosServidor = { nome: "", modoNome: "similar", cargo: "", orgao: "", uf: "" };
const ITENS_POR_PAGINA = 10;

export function ConsultaServidores() {
  const [filtros, setFiltros] = useState(filtrosIniciais);
  // Filtros da última busca enviada: a navegação entre páginas usa estes, não o que está digitado no formulário.
  const [filtrosAplicados, setFiltrosAplicados] = useState(filtrosIniciais);
  const [resultados, setResultados] = useState<Servidor[]>([]);
  const [paginacao, setPaginacao] = useState<Paginacao | null>(null);
  const [selecionado, setSelecionado] = useState<Servidor | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [buscaExataVazia, setBuscaExataVazia] = useState(false);
  const [ordenacao, setOrdenacao] = useState<Ordenacao>("nome-asc");
  const [avisoAcao, setAvisoAcao] = useState<string | null>(null);
  const controladorRef = useRef<AbortController | null>(null);

  const executarBusca = useCallback(async (valores: FiltrosServidor, pagina: number, ordem: Ordenacao): Promise<void> => {
    controladorRef.current?.abort();
    const controller = new AbortController();
    controladorRef.current = controller;

    setCarregando(true);
    setErro(null);
    setBuscaExataVazia(false);
    setAvisoAcao(null);
    try {
      const data = await consultarServidores(valores, { pagina, limite: ITENS_POR_PAGINA, ordenacao: ordem }, controller.signal);
      setResultados(data.itens);
      setPaginacao(data.paginacao);
      setFiltrosAplicados(valores);
      data.itens.forEach(salvarServidorLocal);
      setSelecionado((atual) => data.itens.find((item) => item.id === atual?.id) ?? data.itens[0] ?? null);
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
      // Os dados mudaram e a página pedida deixou de existir: volta para a primeira.
      if (error instanceof ApiError && error.codigo === "PAGINA_INEXISTENTE" && pagina > 1) {
        void executarBusca(valores, 1, ordem);
        return;
      }
      setResultados([]);
      setPaginacao(null);
      setSelecionado(null);
      if (error instanceof ApiError && error.codigo === "NOME_NAO_ENCONTRADO") {
        setBuscaExataVazia(true);
      } else {
        setErro(error instanceof Error ? error.message : "Não foi possível concluir a consulta.");
      }
    } finally {
      if (!controller.signal.aborted) setCarregando(false);
    }
  }, []);

  useEffect(() => {
    void executarBusca(filtrosIniciais, 1, "nome-asc");
    return () => controladorRef.current?.abort();
  }, [executarBusca]);

  const paginaAtual = paginacao?.pagina ?? 1;
  const totalPaginas = Math.max(1, paginacao?.total_paginas ?? 1);
  const totalRegistros = paginacao?.total ?? 0;

  function mudarOrdenacao(novaOrdenacao: Ordenacao) {
    setOrdenacao(novaOrdenacao);
    void executarBusca(filtrosAplicados, 1, novaOrdenacao);
  }

  function mudarPagina(novaPagina: number) {
    if (carregando || novaPagina < 1 || novaPagina > totalPaginas || novaPagina === paginaAtual) return;
    void executarBusca(filtrosAplicados, novaPagina, ordenacao);
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void executarBusca(filtros, 1, ordenacao);
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
            <span className="mono-meta">{carregando ? "Carregando registros…" : `${totalRegistros.toLocaleString("pt-BR")} ${totalRegistros === 1 ? "registro encontrado" : "registros encontrados"}`}</span>
            <label className="sort-control">
              <span>Ordenar por</span>
              <select value={ordenacao} onChange={(event) => mudarOrdenacao(event.target.value as Ordenacao)}>
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
                  {resultados.map((servidor) => (
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

          {resultados.length > 0 && (
            <nav className="pagination" aria-label="Paginação dos resultados">
              <button className="button button-outline" type="button" onClick={() => mudarPagina(paginaAtual - 1)} disabled={carregando || !paginacao?.tem_anterior}>
                Anterior
              </button>
              <span aria-live="polite">
                Página <strong>{paginaAtual.toLocaleString("pt-BR")}</strong> de {totalPaginas.toLocaleString("pt-BR")}
              </span>
              <button className="button button-outline" type="button" onClick={() => mudarPagina(paginaAtual + 1)} disabled={carregando || !paginacao?.tem_proxima}>
                Próxima
              </button>
            </nav>
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
