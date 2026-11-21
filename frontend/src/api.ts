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
