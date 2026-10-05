export type TipoVinculo = "ATIVO" | "APOSENTADO";

export interface Servidor {
  id: number;
  cpf: string;
  nome: string;
  cargo: string | null;
  orgao: string | null;
  uf: string | null;
  tipo_vinculo: TipoVinculo;
  remuneracao: number | null;
}

export interface FiltrosServidor {
  nome: string;
  modoNome: "exata" | "similar";
  cargo: string;
  orgao: string;
  uf: string;
  limite: number;
}

export class ApiError extends Error {
  constructor(message: string, public readonly status?: number) {
    super(message);
    this.name = "ApiError";
  }
}

const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

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

export async function consultarServidores(filtros: FiltrosServidor, signal?: AbortSignal): Promise<Servidor[]> {
  const params = new URLSearchParams();
  const nome = filtros.nome.trim();

  if (nome) params.set(filtros.modoNome === "exata" ? "nome" : "similar", nome);
  if (filtros.cargo.trim()) params.set("cargo", filtros.cargo.trim());
  if (filtros.orgao.trim()) params.set("orgao", filtros.orgao.trim());
  if (filtros.uf) params.set("uf", filtros.uf);
  params.set("limite", String(Math.min(Math.max(filtros.limite, 1), 100)));

  let response: Response;
  try {
    response = await fetch(`${API_URL}/api/servidores?${params.toString()}`, {
      cache: "no-store",
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new ApiError(`Não foi possível conectar à API em ${API_URL}. Verifique se o backend está em execução.`);
  }

  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw new ApiError("A API respondeu em um formato inesperado.", response.status);
  }

  if (!response.ok) {
    const apiMessage = payload && typeof payload === "object" && "erro" in payload && typeof payload.erro === "string"
      ? payload.erro
      : `A consulta falhou (HTTP ${response.status}).`;
    throw new ApiError(apiMessage, response.status);
  }

  if (!Array.isArray(payload) || !payload.every(isServidor)) {
    throw new ApiError("A resposta da API não corresponde ao formato esperado.", response.status);
  }
  return payload;
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
