// Datos de la Bandeja "Archivo vivo": todo se deriva de las Entry que ya guarda useBandeja.
import type { Entry, Verdict } from "../../types";
import { seconds } from "../../labels";

export type Filter = "todos" | "warn" | "bad" | "ok" | "proc";
/** Estado visual de una carpeta: el veredicto, o "proc"/"error" si aún no hay dictamen. */
export type Kind = "warn" | "bad" | "ok" | "proc" | "error";
export type VerdictKind = "warn" | "bad" | "ok";

export const KIND_VERDICT: Record<VerdictKind, Verdict> = {
  warn: "Requiere revisión",
  bad: "No cumple",
  ok: "Cumple",
};

const VERDICT_KIND: Record<Verdict, VerdictKind> = {
  "Requiere revisión": "warn",
  "No cumple": "bad",
  Cumple: "ok",
};

/** Texto corto del sello (mono, mayúsculas por CSS). */
export const STAMP: Record<Kind, string> = {
  warn: "Revisión",
  bad: "No cumple",
  ok: "Cumple",
  proc: "Analizando",
  error: "Error",
};

export const FILTER_TITLE: Record<Filter, string> = {
  todos: "Todas las carpetas",
  warn: "Cajón: requiere revisión",
  bad: "Cajón: no cumple",
  ok: "Cajón: cumple",
  proc: "Carpetas en proceso",
};

export interface Carpeta {
  id: string;
  kind: Kind;
  createdAt: number;
  /** Confianza 0–100, o null si no hay dictamen. */
  conf: number | null;
  blocking: number;
  ms: number | null;
  error?: string;
}

export function blocking(e: Entry): number {
  if (!e.report) return 0;
  return (
    e.report.cross_validation_issues.filter((i) => i.severity === "critical").length +
    e.report.document_analyses.flatMap((a) =>
      a.rule_evaluations.filter((r) => !r.passed && r.severity === "critical"),
    ).length
  );
}

export function toCarpeta(e: Entry): Carpeta {
  const r = e.report;
  const kind: Kind = r ? VERDICT_KIND[r.recommendation] : e.status === "procesando" ? "proc" : "error";
  return {
    id: e.id,
    kind,
    createdAt: e.createdAt,
    conf: r ? Math.round(r.confidence * 100) : null,
    blocking: blocking(e),
    ms: r ? r.processing_ms : null,
    error: e.error,
  };
}

/** Primero lo que necesita a una persona: errores, no cumple, revisión, en proceso, cumple. */
const RANK: Record<Kind, number> = { error: 0, bad: 1, warn: 2, proc: 2.5, ok: 3 };

export function sortCarpetas(a: Carpeta, b: Carpeta): number {
  return RANK[a.kind] - RANK[b.kind] || b.createdAt - a.createdAt;
}

export function blockingText(n: number): string {
  return n === 0 ? "Sin bloqueantes" : n === 1 ? "1 bloqueante" : `${n} bloqueantes`;
}

/** "veredicto · N bloqueantes" (o el estado, si aún no hay dictamen). */
export function summaryText(c: Carpeta): string {
  if (c.kind === "proc") return "Analizando · aún sin veredicto";
  if (c.kind === "error") return "Error · no se pudo analizar";
  return `${STAMP[c.kind]} · ${blockingText(c.blocking)}`;
}

/** Mensajes del ticker a partir de los expedientes recientes (no hay feed de eventos en la API). */
export function tickerEvents(cs: Carpeta[]): string[] {
  return [...cs]
    .sort((a, b) => b.createdAt - a.createdAt)
    .slice(0, 12)
    .map((c) => {
      if (c.kind === "proc") return `${c.id} en análisis…`;
      if (c.kind === "error") return `${c.id} no se pudo analizar`;
      const t = c.ms != null ? ` en ${seconds(c.ms)}` : "";
      const v = c.kind === "ok" ? "cumple" : c.kind === "bad" ? "no cumple" : "requiere revisión";
      return `${c.id} dictaminado${t} · ${v}`;
    });
}
