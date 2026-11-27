export type TipoVinculo = "ATIVO" | "APOSENTADO";

export interface Servidor {
  id: number;
  cpf: string;
  nome: string;
  cargo: string | null;
  orgao: string | null;
  sigla_orgao: string | null;
  uf: string | null;
  tipo_vinculo: TipoVinculo;
  remuneracao: number | null;
}

export interface ServidorDetalhado extends Servidor {
  detalhes: Record<string, string | null>;
}

export interface FiltrosServidor {
  nome: string;
  modoNome: "exata" | "similar";
  cargo: string;
  orgao: string;
  uf: string;
}

export type Ordenacao = "nome-asc" | "nome-desc" | "remuneracao-desc";

export interface Paginacao {
  pagina: number;
  limite: number;
  total: number;
  total_paginas: number;
  tem_anterior: boolean;
  tem_proxima: boolean;
}

export interface ResultadoConsulta {
  itens: Servidor[];
  paginacao: Paginacao;
}

export interface OpcoesConsulta {
  pagina: number;
  limite: number;
  ordenacao: Ordenacao;
}

export class ApiError extends Error {
  constructor(message: string, public readonly status?: number, public readonly codigo?: string) {
    super(message);
    this.name = "ApiError";
  }
}

const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/$/, "");

function isServidor(value: unknown): value is Servidor {
  if (!value || typeof value !== "object") return false;
  const item = value as Partial<Servidor>;
  return (
    typeof item.id === "number" &&
    typeof item.cpf === "string" &&
    typeof item.nome === "string" &&
    (item.tipo_vinculo === "ATIVO" || item.tipo_vinculo === "APOSENTADO")
  );
}

function isPaginacao(value: unknown): value is Paginacao {
  if (!value || typeof value !== "object") return false;
  const item = value as Partial<Paginacao>;
  return (
    typeof item.pagina === "number" &&
    typeof item.limite === "number" &&
    typeof item.total === "number" &&
    typeof item.total_paginas === "number"
  );
}

async function requisitar(caminho: string, signal?: AbortSignal): Promise<unknown> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}/api/servidores${caminho}`, {
      cache: "no-store",
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new ApiError("Não foi possível conectar à API de servidores.");
  }

  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw new ApiError("A API respondeu em um formato inesperado.", response.status);
  }

  if (!response.ok) {
    const corpo = payload && typeof payload === "object" ? (payload as { erro?: unknown; codigo?: unknown }) : {};
    const apiMessage = typeof corpo.erro === "string" ? corpo.erro : `A consulta falhou (HTTP ${response.status}).`;
    throw new ApiError(apiMessage, response.status, typeof corpo.codigo === "string" ? corpo.codigo : undefined);
  }
  return payload;
}

export async function consultarServidores(
  filtros: FiltrosServidor,
  opcoes: OpcoesConsulta,
  signal?: AbortSignal,
): Promise<ResultadoConsulta> {
  const params = new URLSearchParams();
  const nome = filtros.nome.trim();
  if (nome) params.set(filtros.modoNome === "exata" ? "nome" : "similar", nome);
  if (filtros.cargo.trim()) params.set("cargo", filtros.cargo.trim());
  if (filtros.orgao.trim()) params.set("orgao", filtros.orgao.trim());
  if (filtros.uf) params.set("uf", filtros.uf);
  params.set("pagina", String(Math.max(opcoes.pagina, 1)));
  params.set("limite", String(Math.min(Math.max(opcoes.limite, 1), 100)));
  params.set("ordenar", opcoes.ordenacao);

  const payload = await requisitar(`?${params}`, signal);
  const corpo = payload && typeof payload === "object" ? (payload as { itens?: unknown; paginacao?: unknown }) : {};
  if (!Array.isArray(corpo.itens) || !corpo.itens.every(isServidor) || !isPaginacao(corpo.paginacao)) {
    throw new ApiError("A resposta da API não corresponde ao formato esperado.");
  }
  return { itens: corpo.itens, paginacao: corpo.paginacao };
}

export async function consultarServidor(id: string, signal?: AbortSignal): Promise<ServidorDetalhado> {
  const dado = await requisitar(`/${encodeURIComponent(id)}`, signal);
  if (!isServidor(dado) || !("detalhes" in dado) || !dado.detalhes || typeof dado.detalhes !== "object") {
    throw new ApiError("A API retornou um registro em formato inesperado.");
  }
  return { ...dado, detalhes: dado.detalhes as ServidorDetalhado["detalhes"] };
}

export function salvarServidorLocal(servidor: Servidor): void {
  if (typeof window !== "undefined") {
    window.sessionStorage.setItem(`servidor:${servidor.id}`, JSON.stringify(servidor));
  }
}

export function lerServidorLocal(id: string): Servidor | null {
  if (typeof window === "undefined") return null;
  const value = window.sessionStorage.getItem(`servidor:${id}`);
  if (!value) return null;
  try {
    const parsed: unknown = JSON.parse(value);
    return isServidor(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

export function formatarMoeda(valor: number | null): string {
  if (valor === null) return "Não informado";
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(valor);
}

export function formatarVinculo(tipo: TipoVinculo): string {
  return tipo === "ATIVO" ? "Ativo" : "Aposentado";
}
