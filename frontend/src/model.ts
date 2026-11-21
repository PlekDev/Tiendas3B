// Convierte el Report del contrato en lo que pinta la pantalla de dictamen.
// Toda la lógica de presentación vive aquí para que los componentes solo dibujen.
import type { DocType, DocumentAnalysis, Evidence, ExtractedField, Report, RuleEvaluation } from "./types";
import {
  AGENT_UI,
  CROSS_ROWS,
  DOC_LABEL,
  DOC_ORDER,
  DOC_SHORT,
  DOUBT_THRESHOLD,
  SEV_RANK,
  SEV_TONE,
  type Tone,
  fieldLabel,
} from "./labels";

/** Lo que abre el visor: una cita y, si el dato es dudoso, por qué. */
export interface EvTarget {
  evidence: Evidence;
  doubt?: string;
}

const RULE_REF = /^(?:Nota:\s*)?(\S+\.\w{2,4})(?:\s·\s([\w-]+))?:\s*/;

/** Quita "Nota: archivo.pdf · USO-04: " del inicio de una razón. */
export function cleanReason(text: string): { text: string; doc?: string; rule?: string } {
  const m = text.match(RULE_REF);
  const cap = (t: string) => t.charAt(0).toUpperCase() + t.slice(1);
  if (!m) return { text: cap(text.replace(/^Nota:\s*/, "")) };
  return { text: cap(text.slice(m[0].length)), doc: m[1], rule: m[2] };
}

function norm(v: string): string {
  const n = v
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/m2|m²/g, "")
    .replace(/[^a-z0-9.]+/g, " ")
    .trim();
  const num = Number.parseFloat(n);
  return /^[\d.\s]+$/.test(n) && !Number.isNaN(num) ? String(num) : n.replace(/\.$/, "");
}

const sevTone = (r: { severity: keyof typeof SEV_TONE }) => SEV_TONE[r.severity];

function worst(tones: Tone[]): Tone {
  for (const t of ["bad", "warn", "doubt", "info", "ok"] as Tone[]) if (tones.includes(t)) return t;
  return "na";
}

function firstByType(report: Report) {
  const byType = new Map<DocType, DocumentAnalysis>();
  report.document_analyses.forEach((a) => {
    if (!byType.has(a.document_type)) byType.set(a.document_type, a);
  });
  return byType;
}

function fieldOf(a: DocumentAnalysis | undefined, name: string | undefined) {
  if (!a || !name) return undefined;
  return a.extracted_fields.find((f) => f.name === name && (f.value ?? "").trim());
}

function doubtText(f: ExtractedField, doc: string): string | undefined {
  if (f.confidence >= DOUBT_THRESHOLD) return undefined;
  const base = `Se leyó "${f.value}" con ${Math.round(f.confidence * 100)} % de seguridad en ${doc}.`;
  return f.evidence ? base : `${base} No hay una cita verificable.`;
}

/* ---------- Comparación entre documentos ---------- */

export interface CompCell {
  kind: "val" | "dev" | "doubt" | "na" | "miss" | "empty";
  label: string;
  target?: EvTarget;
}
export interface CompRow {
  key: string;
  label: string;
  cells: CompCell[];
  tone: Tone;
  result: string;
}

export function comparison(report: Report): CompRow[] {
  const byType = firstByType(report);
  return CROSS_ROWS.map((row) => {
    const issue = report.cross_validation_issues.find((i) => i.field_name === row.key);
    const present = DOC_ORDER.map((t) => fieldOf(byType.get(t), row.fields[t]));
    const values = present.filter(Boolean).map((f) => norm(f!.value!));
    const ref = values[0];
    const tone: Tone = issue ? SEV_TONE[issue.severity] : values.length >= 2 ? "ok" : "na";
    const cells = DOC_ORDER.map((t, i): CompCell => {
      if (!row.fields[t]) return { kind: "na", label: "— No aplica" };
      const a = byType.get(t);
      if (!a) return { kind: "miss", label: "✕ Falta" };
      const f = present[i];
      if (!f) return { kind: "empty", label: "No encontrado" };
      const doubt = doubtText(f, a.document_name);
      const target = f.evidence ? { evidence: f.evidence, doubt } : undefined;
      if (doubt) return { kind: "doubt", label: `? ${f.value} · en duda`, target };
      if (issue && norm(f.value!) !== ref) return { kind: "dev", label: f.value!, target };
      return { kind: "val", label: f.value!, target };
    });
    const n = values.length;
    const result = issue
      ? issue.severity === "critical"
        ? "No coincide"
        : "Difiere"
      : n >= 2
        ? missingAny(report) && n < Object.keys(row.fields).length
          ? `Coincide (${n} de ${Object.keys(row.fields).length})`
          : "Coincide"
        : "Sin datos para comparar";
    return { key: row.key, label: row.label, cells, tone, result };
  });
}

const missingAny = (r: Report) => r.missing_document_types.length > 0;

/* ---------- Hallazgos ---------- */

export interface FindingValue {
  doc: string;
  value: string;
  dev: boolean;
  target?: EvTarget;
}
export interface Finding {
  key: string;
  tone: Tone;
  title: string;
  what: string;
  docs: string;
  values: FindingValue[];
  evidence: Evidence[];
  missingDoc?: DocType;
}

function docTypeOf(report: Report, name: string): DocType | undefined {
  return report.document_analyses.find((a) => a.document_name === name)?.document_type;
}

export function findings(report: Report): Finding[] {
  const out: (Finding & { rank: number })[] = [];
  report.missing_document_types.forEach((t) =>
    out.push({
      key: `miss-${t}`,
      rank: 1,
      tone: "warn",
      title: `Falta ${DOC_LABEL[t]}`,
      what: "No se recibió el documento. Sin él no se pueden verificar sus datos ni sus reglas.",
      docs: "No se recibió",
      values: [],
      evidence: [],
      missingDoc: t,
    }),
  );
  report.cross_validation_issues.forEach((i) => {
    const row = CROSS_ROWS.find((r) => r.key === i.field_name);
    const entries = Object.entries(i.values_found);
    const ref = entries[0] ? norm(entries[0][1]) : "";
    out.push({
      key: `x-${i.field_name}`,
      rank: SEV_RANK[i.severity],
      tone: SEV_TONE[i.severity],
      title: `${row?.label ?? fieldLabel(i.field_name)}: no coincide entre documentos`,
      what: i.description,
      docs: i.documents_involved.join(" · "),
      values: entries.map(([doc, value]) => {
        const t = docTypeOf(report, doc);
        const ev = i.evidence.find((e) => e.document_name === doc);
        return {
          doc: t ? DOC_SHORT[t] : doc,
          value,
          dev: norm(value) !== ref,
          target: ev ? { evidence: ev } : undefined,
        };
      }),
      evidence: i.evidence,
    });
  });
  report.document_analyses.forEach((a) =>
    a.rule_evaluations
      .filter((r) => !r.passed)
      .forEach((r) =>
        out.push({
          key: `r-${a.document_name}-${r.rule_id}`,
          rank: SEV_RANK[r.severity],
          tone: sevTone(r),
          title: r.details.replace(/\.+$/, ""),
          what: r.description,
          docs: `${a.document_name} · ${r.rule_id}`,
          values: [],
          evidence: r.evidence,
        }),
      ),
  );
  return out.sort((x, y) => x.rank - y.rank).map(({ rank: _rank, ...f }) => f);
}

export interface Pass {
  key: string;
  text: string;
  doc: string;
  evidence?: Evidence;
}

export function passes(report: Report): Pass[] {
  return report.document_analyses.flatMap((a) =>
    a.rule_evaluations
      .filter((r) => r.passed)
      .map((r) => ({
        key: `${a.document_name}-${r.rule_id}`,
        text: r.description.replace(/\.+$/, ""),
        doc: `${a.document_name} · ${r.rule_id}`,
        evidence: r.evidence[0],
      })),
  );
}

/* ---------- Encabezado del dictamen ---------- */

export interface Reason {
  tone: Tone;
  text: string;
  doc?: string;
  target?: EvTarget;
  findingKey?: string;
}

export function reasons(report: Report, comp: CompRow[]): Reason[] {
  const list: Reason[] = report.reasons.map((raw) => {
    const isNote = raw.startsWith("Nota:");
    const { text, doc, rule } = cleanReason(raw);
    const issue = report.cross_validation_issues.find((i) =>
      raw.startsWith(i.description.slice(0, 40)),
    );
    if (issue)
      return {
        tone: SEV_TONE[issue.severity],
        text,
        target: issue.evidence[0] ? { evidence: issue.evidence[0] } : undefined,
        findingKey: `x-${issue.field_name}`,
      };
    const a = report.document_analyses.find((x) => x.document_name === doc);
    const r: RuleEvaluation | undefined = a?.rule_evaluations.find(
      (x) => x.rule_id === rule || (!rule && !x.passed),
    );
    if (r)
      return {
        tone: isNote ? "info" : sevTone(r),
        text,
        doc,
        target: r.evidence[0] ? { evidence: r.evidence[0] } : undefined,
        findingKey: `r-${doc}-${r.rule_id}`,
      };
    if (/^Faltan/i.test(raw)) return { tone: "warn", text, findingKey: report.missing_document_types[0] ? `miss-${report.missing_document_types[0]}` : undefined };
    return { tone: report.recommendation === "Cumple" ? "ok" : isNote ? "info" : "warn", text };
  });
  // Completa con lo que sí coincide, para que el veredicto muestre ambos lados.
  comp
    .filter((r) => r.tone === "ok")
    .slice(0, Math.max(0, 3 - list.length))
    .forEach((r) => {
      const cell = r.cells.find((c) => c.target);
      const docs = r.cells
        .map((c, i) => (c.kind === "val" ? DOC_SHORT[DOC_ORDER[i]] : null))
        .filter(Boolean);
      list.push({
        tone: "ok",
        text: `${r.label} coincide en ${docs.join(", ")}`,
        target: cell?.target,
      });
    });
  return list;
}

export function lead(report: Report): string {
  const first = report.reasons.find((r) => !r.startsWith("Nota:"));
  return first ? cleanReason(first).text : report.explanation;
}

export function confidenceWhy(report: Report): string {
  const fields = report.document_analyses.flatMap((a) => a.extracted_fields).filter((f) => f.value);
  const cited = fields.filter((f) => f.evidence).length;
  const doubt = fields.filter((f) => f.confidence < DOUBT_THRESHOLD).length;
  const parts = [`${cited} de ${fields.length} datos leídos tienen cita en el documento.`];
  if (doubt) parts.push(`${doubt} ${doubt === 1 ? "dato está" : "datos están"} en duda.`);
  const miss = report.missing_document_types.length;
  if (miss) parts.push(`Faltan ${miss} de 4 documentos.`);
  return parts.join(" ");
}

/* ---------- Tarjetas de documentos ---------- */

export interface DocCard {
  key: string;
  title: string;
  file: string;
  missing: boolean;
  type?: DocType;
  conf?: number;
  issues: { tone: Tone; label: string }[];
}

export function docCards(report: Report): DocCard[] {
  const cards: DocCard[] = DOC_ORDER.map((t) => {
    const docs = report.document_analyses.filter((a) => a.document_type === t);
    if (!docs.length)
      return { key: t, title: DOC_LABEL[t], file: "No se recibió", missing: true, type: t, issues: [] };
    const a = docs[0];
    return {
      key: t,
      title: DOC_LABEL[t],
      file: docs.map((d) => d.document_name).join(" · "),
      missing: false,
      type: t,
      conf: a.classification_confidence,
      issues: issuesFor(report, docs),
    };
  });
  report.document_analyses
    .filter((a) => a.document_type === "desconocido")
    .forEach((a) =>
      cards.push({
        key: a.document_name,
        title: "Documento sin identificar",
        file: a.document_name,
        missing: false,
        conf: a.classification_confidence,
        issues: issuesFor(report, [a]),
      }),
    );
  return cards;
}

function issuesFor(report: Report, docs: DocumentAnalysis[]) {
  const names = docs.map((d) => d.document_name);
  const issues: { tone: Tone; label: string }[] = [];
  report.cross_validation_issues
    .filter((i) => i.documents_involved.some((d) => names.includes(d)))
    .forEach((i) => {
      const others = i.documents_involved
        .filter((d) => !names.includes(d))
        .map((d) => {
          const t = docTypeOf(report, d);
          return t ? DOC_SHORT[t] : d;
        });
      const row = CROSS_ROWS.find((r) => r.key === i.field_name);
      issues.push({
        tone: SEV_TONE[i.severity],
        label: `${row?.label ?? fieldLabel(i.field_name)} difiere de ${others.join(" y ")}`,
      });
    });
  docs
    .flatMap((d) => d.rule_evaluations.filter((r) => !r.passed))
    .sort((a, b) => SEV_RANK[a.severity] - SEV_RANK[b.severity])
    .forEach((r) => issues.push({ tone: sevTone(r), label: r.details.replace(/\.+$/, "") }));
  docs
    .flatMap((d) => d.extracted_fields)
    .filter((f) => f.value && f.confidence < DOUBT_THRESHOLD)
    .forEach((f) => issues.push({ tone: "doubt", label: `${fieldLabel(f.name)} en duda` }));
  if (!issues.length) issues.push({ tone: "ok", label: "Todas las reglas cumplen" });
  return issues;
}

/* ---------- Matriz documento × regla ---------- */

export const MATRIX_COLS = [
  ...CROSS_ROWS.map((r) => ({ key: r.key, label: r.label.replace(" o titular", "").replace(" del inmueble", "") })),
  { key: "vigencia", label: "Vigencia" },
  { key: "uso", label: "Uso permitido" },
];

export interface MatrixCell {
  tone: Tone;
  detail: string;
}

const RULE_GROUPS: Record<string, RegExp> = {
  vigencia: /vigencia|fecha de emisi/i,
  uso: /uso|restricci|condicionante/i,
};

export function matrix(report: Report, comp: CompRow[]): { doc: string; cells: MatrixCell[] }[] {
  const byType = firstByType(report);
  return DOC_ORDER.map((t, i) => {
    const a = byType.get(t);
    const cells = MATRIX_COLS.map((col, j): MatrixCell => {
      if (!a) return { tone: "miss", detail: "No se recibió el documento" };
      if (j < comp.length) {
        const c = comp[j].cells[i];
        if (c.kind === "na") return { tone: "na", detail: "No aplica a este documento" };
        if (c.kind === "empty") return { tone: "doubt", detail: "No se encontró el dato" };
        if (c.kind === "doubt") return { tone: "doubt", detail: `${c.label}, sin cita suficiente` };
        if (c.kind === "dev") return { tone: comp[j].tone, detail: `${c.label} · ${comp[j].result.toLowerCase()}` };
        return { tone: "ok", detail: `${c.label} · coincide` };
      }
      if (col.key === "uso" && t !== "uso_de_suelo") return { tone: "na", detail: "No aplica a este documento" };
      const rules = a.rule_evaluations.filter((r) => RULE_GROUPS[col.key].test(r.description));
      if (!rules.length) return { tone: "na", detail: "No aplica a este documento" };
      const tones = rules.map((r) => (r.passed ? "ok" : sevTone(r)));
      return {
        tone: worst(tones),
        detail: rules.map((r) => `${r.rule_id}: ${r.passed ? "cumple" : r.details}`).join(" · "),
      };
    });
    return { doc: DOC_SHORT[t], cells };
  });
}

/* ---------- Datos extraídos ---------- */

export interface FieldRow {
  key: string;
  campo: string;
  valor: string | null;
  src: string;
  conf: number;
  method: string;
  doubt: boolean;
  target?: EvTarget;
}

export function fieldRows(report: Report): FieldRow[] {
  return report.document_analyses.flatMap((a) =>
    a.extracted_fields.map((f) => ({
      key: `${a.document_name}-${f.name}`,
      campo: fieldLabel(f.name),
      valor: f.value,
      src: `${a.document_name}${f.evidence?.page ? ` · p. ${f.evidence.page}` : ""}`,
      conf: f.confidence,
      method: f.method,
      doubt: !!f.value && f.confidence < DOUBT_THRESHOLD,
      target: f.evidence ? { evidence: f.evidence, doubt: doubtText(f, a.document_name) } : undefined,
    })),
  );
}

/* ---------- Traza ---------- */

export interface AgentRow {
  key: string;
  label: string;
  desc: string;
  ms: number;
  out: string;
}

export function agents(report: Report): AgentRow[] {
  const subs = report.trace.filter((s) => s.agent.startsWith("extractor_"));
  return report.trace
    .filter((s) => !s.agent.startsWith("extractor_"))
    .map((s) => {
      const ui = AGENT_UI[s.agent] ?? { label: s.agent, desc: "" };
      let out = s.detail;
      if (s.agent === "extractores" && subs.length) out = subs.map((x) => x.detail).join(" · ");
      if (s.agent === "validacion_cruzada" && !out) {
        const n = report.cross_validation_issues.length;
        out = n ? `${n} ${n === 1 ? "discrepancia" : "discrepancias"} entre documentos` : "Sin discrepancias";
      }
      if (s.agent === "dictaminador" && !out)
        out = `${report.recommendation} · confianza ${Math.round(report.confidence * 100)} %`;
      return { key: s.agent, label: ui.label, desc: ui.desc, ms: s.ms, out };
    });
}

/** Todas las citas conocidas de un documento: sirven para reconstruir la hoja sin el PDF. */
export function snippetsOf(report: Report, doc: string, page: number | null): string[] {
  const a = report.document_analyses.find((x) => x.document_name === doc);
  if (!a) return [];
  const all = [
    ...a.extracted_fields.map((f) => f.evidence),
    ...a.rule_evaluations.flatMap((r) => r.evidence),
    ...report.cross_validation_issues.flatMap((i) => i.evidence),
  ].filter((e): e is Evidence => !!e && e.document_name === doc && (page == null || e.page === page));
  return [...new Set(all.map((e) => e.snippet))];
}

/* ---------- Documentos marcados ---------- */

export interface DocMark {
  id: string;
  kind: "dato" | "regla";
  campo: string;
  value: string | null;
  snippet: string | null;
  page: number | null;
  tone: Tone;
  note: string;
}

const MARK_RANK: Record<string, number> = { bad: 0, warn: 1, doubt: 2, info: 3, ok: 4 };

/** Qué subrayar en cada documento: cada dato leído y cada regla que no se cumple. */
export function docMarks(report: Report, a: DocumentAnalysis): DocMark[] {
  const marks: DocMark[] = [];
  a.extracted_fields.forEach((f, i) => {
    if (!(f.value ?? "").trim()) return;
    const row = CROSS_ROWS.find((r) => r.fields[a.document_type] === f.name);
    const issue = row && report.cross_validation_issues.find((x) => x.field_name === row.key);
    const involved =
      issue && (issue.documents_involved.includes(a.document_name) || a.document_name in issue.values_found);
    const doubt = f.confidence < DOUBT_THRESHOLD;
    marks.push({
      id: `f${i}`,
      kind: "dato",
      campo: fieldLabel(f.name),
      value: f.value,
      snippet: f.evidence?.document_name === a.document_name ? f.evidence.snippet : null,
      page: f.evidence?.page ?? null,
      tone: involved ? SEV_TONE[issue!.severity] : doubt ? "doubt" : "ok",
      note: involved
        ? cleanReason(issue!.description).text
        : doubt
          ? `En duda: se leyó con ${Math.round(f.confidence * 100)} % de seguridad.`
          : `Leído con ${Math.round(f.confidence * 100)} % de seguridad.`,
    });
  });
  a.rule_evaluations.forEach((r, i) => {
    if (r.passed) return;
    r.evidence
      .filter((e) => e.document_name === a.document_name)
      .forEach((e, j) =>
        marks.push({
          id: `r${i}-${j}`,
          kind: "regla",
          campo: r.description,
          value: null,
          snippet: e.snippet,
          page: e.page,
          tone: sevTone(r),
          note: cleanReason(r.details).text,
        }),
      );
  });
  // Un dato que es la prueba de una regla incumplida toma el color de esa regla.
  marks.forEach((m) => {
    if (m.kind !== "dato" || m.tone !== "ok" || !m.snippet) return;
    const rule = marks.find((r) => r.kind === "regla" && r.snippet === m.snippet);
    if (rule) {
      m.tone = rule.tone;
      m.note = `${rule.campo} ${rule.note}`;
    }
  });
  return marks.sort((x, y) => MARK_RANK[x.tone] - MARK_RANK[y.tone]);
}

/* ---------- Datos listos para copiar ---------- */

export interface CopyDoc {
  key: string;
  title: string;
  file: string;
  rows: { campo: string; value: string | null; doubt: boolean }[];
}

export function copyDocs(report: Report): CopyDoc[] {
  const rank = (t: DocType) => (DOC_ORDER.includes(t) ? DOC_ORDER.indexOf(t) : 99);
  return [...report.document_analyses]
    .sort((x, y) => rank(x.document_type) - rank(y.document_type))
    .map((a) => {
      const rows = a.extracted_fields.map((f) => ({
        campo: fieldLabel(f.name),
        value: (f.value ?? "").trim() || null,
        doubt: !!f.value && f.confidence < DOUBT_THRESHOLD,
      }));
      a.missing_fields
        .filter((m) => !a.extracted_fields.some((f) => f.name === m))
        .forEach((m) => rows.push({ campo: fieldLabel(m), value: null, doubt: false }));
      return { key: a.document_name, title: DOC_LABEL[a.document_type], file: a.document_name, rows };
    })
    .filter((d) => d.rows.length > 0);
}

const copyLine = (r: CopyDoc["rows"][number]) =>
  `${r.campo}: ${r.value ?? "No encontrado"}${r.doubt ? " (en duda)" : ""}`;

export function copyDocText(d: CopyDoc): string {
  return [`${d.title.toUpperCase()} (${d.file})`, ...d.rows.map(copyLine)].join("\n");
}

export function copyAllText(report: Report, docs: CopyDoc[]): string {
  const head = [
    `Expediente: ${report.expediente_id}`,
    `Dictamen: ${report.recommendation} (confianza ${Math.round(report.confidence * 100)} %)`,
  ];
  return [head.join("\n"), ...docs.map(copyDocText)].join("\n\n");
}
