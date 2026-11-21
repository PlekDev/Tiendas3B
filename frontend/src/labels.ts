import type { DocType, Severity, Verdict } from "./types";

export const DOC_ORDER: DocType[] = [
  "escrituras",
  "predial",
  "alineamiento_y_numero_oficial",
  "uso_de_suelo",
];

export const DOC_LABEL: Record<DocType, string> = {
  escrituras: "Escrituras",
  predial: "Predial",
  alineamiento_y_numero_oficial: "Alineamiento y Número Oficial",
  uso_de_suelo: "Uso de Suelo",
  desconocido: "Sin identificar",
};

export const DOC_SHORT: Record<DocType, string> = {
  escrituras: "Escritura",
  predial: "Predial",
  alineamiento_y_numero_oficial: "Alineamiento",
  uso_de_suelo: "Uso de suelo",
  desconocido: "Sin identificar",
};

/** Tono visual: siempre palabra + color + ícono, y borde punteado para lo incierto o faltante. */
export type Tone = "ok" | "warn" | "bad" | "info" | "doubt" | "miss" | "na" | "neutral";

export const TONE_ICON: Record<Tone, string> = {
  ok: "✓",
  warn: "!",
  bad: "✕",
  info: "i",
  doubt: "?",
  miss: "✕",
  na: "–",
  neutral: "?",
};

export const SEV_TONE: Record<Severity, Tone> = { critical: "bad", warning: "warn", info: "info" };
export const SEV_RANK: Record<Severity, number> = { critical: 0, warning: 1, info: 2 };

export const VERDICT_UI: Record<Verdict, { cls: Tone; icon: string; short: string }> = {
  Cumple: { cls: "ok", icon: "✓", short: "Cumple" },
  "Requiere revisión": { cls: "warn", icon: "!", short: "Requiere revisión" },
  "No cumple": { cls: "bad", icon: "✕", short: "No cumple" },
};

export const SEVERITY_UI: Record<Severity, { cls: Tone; icon: string; label: string }> = {
  critical: { cls: "bad", icon: "✕", label: "Bloqueante" },
  warning: { cls: "warn", icon: "!", label: "Revisar" },
  info: { cls: "info", icon: "i", label: "Nota" },
};

const FIELD_LABEL: Record<string, string> = {
  propietario: "Propietario o titular",
  direccion: "Dirección del inmueble",
  direccion_oficial: "Dirección oficial",
  superficie_terreno: "Superficie del terreno",
  superficie_registrada: "Superficie registrada",
  superficie_aplicable: "Superficie aplicable",
  cuenta_predial: "Cuenta predial",
  clave_catastral: "Clave catastral",
  identificacion_predio: "Identificación del predio",
  numero_oficial: "Número oficial",
  alineamiento: "Alineamiento",
  fecha_emision: "Fecha de emisión",
  vigencia: "Vigencia",
  autoridad_emisora: "Autoridad emisora",
  uso_suelo_autorizado: "Uso de suelo autorizado",
  uso_de_suelo_autorizado: "Uso de suelo autorizado",
  compatibilidad_uso_comercial: "Compatibilidad con uso comercial",
  compatibilidad_comercial: "Compatibilidad con uso comercial",
  uso_autorizado: "Uso de suelo autorizado",
  fecha_emision_vigencia: "Fecha de emisión y vigencia",
  referencia_cruzada: "Información de enlace",
  restricciones: "Restricciones o condicionantes",
  datos_inmueble: "Datos del inmueble",
  datos_relacionados: "Información de enlace",
};

/** Nombre legible de un campo interno. Nunca se muestra el nombre técnico. */
export function fieldLabel(name: string): string {
  if (FIELD_LABEL[name]) return FIELD_LABEL[name];
  const text = name.replace(/_/g, " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/** Copia de CROSS_CHECKS (src/tiendas3b/rules/criteria.py): qué campo de cada documento. */
export interface CrossRow {
  key: string;
  label: string;
  fields: Partial<Record<DocType, string>>;
  unit?: string;
}

export const CROSS_ROWS: CrossRow[] = [
  {
    key: "propietario",
    label: "Propietario o titular",
    fields: { escrituras: "propietario", predial: "propietario" },
  },
  {
    key: "direccion",
    label: "Dirección del inmueble",
    fields: {
      escrituras: "direccion",
      predial: "direccion",
      alineamiento_y_numero_oficial: "direccion_oficial",
      uso_de_suelo: "direccion",
    },
  },
  {
    key: "superficie",
    label: "Superficie del terreno",
    fields: {
      escrituras: "superficie_terreno",
      predial: "superficie_registrada",
      uso_de_suelo: "superficie_aplicable",
    },
  },
  {
    key: "identificacion_predio",
    label: "Clave catastral o cuenta predial",
    fields: { predial: "cuenta_predial", alineamiento_y_numero_oficial: "identificacion_predio" },
  },
  {
    key: "numero_oficial",
    label: "Número oficial",
    fields: { alineamiento_y_numero_oficial: "numero_oficial" },
  },
];

export const CONFIDENCE_HELP =
  "Qué tan respaldado está el dictamen por citas verificadas en los documentos.";
export const DOUBT_THRESHOLD = 0.6;

export function pct(x: number): string {
  return `${Math.round(x * 100)} %`;
}

export function seconds(ms: number): string {
  return ms < 1000 ? `${ms} ms` : `${(ms / 1000).toFixed(1)} s`;
}

/** Pasos principales del grafo (src/tiendas3b/graph). Los extractor_* se agrupan en Extractores. */
export const AGENT_UI: Record<string, { label: string; desc: string }> = {
  clasificador: { label: "Clasificador", desc: "identifica qué documento es cada archivo" },
  extractores: { label: "Extractores", desc: "leen los datos de cada documento" },
  supervisor_reintento: { label: "Reintento", desc: "vuelve a leer lo que faltó" },
  validador_normativo: { label: "Validador", desc: "aplica las reglas de cada documento" },
  validacion_cruzada: { label: "Cruces", desc: "compara los datos entre documentos" },
  dictaminador: { label: "Dictamen", desc: "redacta el veredicto y sus razones" },
};

export function methodLabel(method: string): string {
  if (method === "llm") return "Modelo de IA";
  if (method === "heuristica") return "Reglas y patrones";
  return method || "—";
}

export function shortDate(ms: number): string {
  return new Date(ms).toLocaleString("es-MX", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
