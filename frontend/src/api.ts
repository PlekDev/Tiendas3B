import type { ApiStatus, DemoCase, Report } from "./types";

class ApiError extends Error {}

async function parse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `${res.status}`;
    try {
      const body = await res.json();
      detail = body.error ?? body.detail ?? detail;
    } catch {
      /* sin cuerpo JSON */
    }
    throw new ApiError(detail);
  }
  return (await res.json()) as T;
}

export const getStatus = () => fetch("/api/v1/status").then(parse<ApiStatus>);
export const getCasos = () => fetch("/api/v1/casos").then(parse<DemoCase[]>);
export const getEjemplo = (caso: string) =>
  fetch(`/api/v1/ejemplo?caso=${encodeURIComponent(caso)}`).then(parse<Report>);
export const getGrafo = () =>
  fetch("/api/v1/grafo").then(parse<{ mermaid: string }>);

export function analizar(id: string, files: File[], usarLlm: boolean): Promise<Report> {
  const body = new FormData();
  body.append("expediente_id", id);
  body.append("usar_llm", String(usarLlm));
  files.forEach((f) => body.append("files", f));
  return fetch("/api/v1/analizar", { method: "POST", body }).then(parse<Report>);
}

/* ---------- Visor: páginas y dónde está cada dato ---------- */

export interface VisorMarkIn {
  id: string;
  texto: string | null;
  contexto: string | null;
  pagina: number | null;
}
export interface VisorPage {
  page: number;
  width: number;
  height: number;
  image: string;
  source: "pdf" | "ocr" | "vacia";
}
export interface VisorMark {
  id: string;
  page: number;
  rects: [number, number, number, number][];
  score: number;
  exact: boolean;
}
export interface VisorData {
  document_name: string;
  pages: VisorPage[];
  marks: VisorMark[];
  missing: string[];
}

export function getVisor(file: Blob, name: string, marcas: VisorMarkIn[]): Promise<VisorData> {
  const body = new FormData();
  body.append("file", file, name);
  body.append("marcas", JSON.stringify(marcas));
  return fetch("/api/v1/visor", { method: "POST", body }).then(parse<VisorData>);
}

export function getVisorEjemplo(expedienteId: string, documento: string, marcas: VisorMarkIn[]): Promise<VisorData> {
  const body = new FormData();
  body.append("expediente_id", expedienteId);
  body.append("documento", documento);
  body.append("marcas", JSON.stringify(marcas));
  return fetch("/api/v1/visor/ejemplo", { method: "POST", body }).then(parse<VisorData>);
}
