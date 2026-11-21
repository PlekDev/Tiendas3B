import { useState } from "react";
import type { DocType, Evidence, Report } from "../types";
import { CONFIDENCE_HELP, DOC_LABEL, DOC_ORDER, seconds } from "../labels";
import { ConfidenceRing, Section, SeverityChip, VerdictChip } from "./Bits";
import { Compare } from "./Compare";
import { Matrix } from "./Matrix";
import { Fields } from "./Fields";
import { Trace } from "./Trace";
import { EvidencePanel } from "./EvidencePanel";

function download(report: Report) {
  const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `dictamen-${report.expediente_id}.json`;
  a.click();
  URL.revokeObjectURL(a.href);
}

const RANK = { critical: 0, warning: 1, info: 2 } as const;

export function Dictamen({ report, onBack }: { report: Report; onBack: () => void }) {
  const [evidence, setEvidence] = useState<Evidence | null>(null);

  const notes = report.reasons.filter((r) => r.startsWith("Nota:"));
  const reasons = report.reasons.filter((r) => !r.startsWith("Nota:"));

  // Hallazgos: cruces entre documentos + reglas incumplidas, de lo más grave a lo menos.
  const findings = [
    ...report.cross_validation_issues.map((i) => ({
      key: `x-${i.field_name}`,
      severity: i.severity,
      title: i.description,
      values: i.values_found,
      evidence: i.evidence,
      origin: "Entre documentos",
    })),
    ...report.document_analyses.flatMap((a) =>
      a.rule_evaluations
        .filter((r) => !r.passed)
        .map((r) => ({
          key: `r-${a.document_name}-${r.rule_id}`,
          severity: r.severity,
          title: `${r.description.replace(/\.+$/, "")}. ${r.details}`,
          values: {} as Record<string, string>,
          evidence: r.evidence,
          origin: a.document_name,
        })),
    ),
  ].sort((a, b) => RANK[a.severity] - RANK[b.severity]);

  const received = new Map<DocType, number>();
  report.document_analyses.forEach((a) =>
    received.set(a.document_type, (received.get(a.document_type) ?? 0) + 1),
  );

  return (
    <div className={`layout${evidence ? " layout--panel" : ""}`}>
      <div className="main">
        <button className="btn btn--ghost" onClick={onBack}>
          ← Bandeja
        </button>

        <header className={`hero hero--${verdictCls(report)}`}>
          <div className="hero__text">
            <div className="muted small">Expediente {report.expediente_id}</div>
            <VerdictChip verdict={report.recommendation} big />
            <ul className="reasons">
              {reasons.slice(0, 3).map((r, i) => (
                <li key={i}>{r}</li>
              ))}
              {!reasons.length && <li>{report.explanation}</li>}
            </ul>
            <div className="muted small">
              {seconds(report.processing_ms)} ·{" "}
              {report.llm_mode === "heuristico" ? "Modo sin IA (reglas y patrones)" : report.llm_mode}
            </div>
            <button className="btn" onClick={() => download(report)}>
              Descargar JSON
            </button>
          </div>
          <div className="hero__ring">
            <ConfidenceRing value={report.confidence} />
            <p className="muted small">Confianza. {CONFIDENCE_HELP}</p>
          </div>
        </header>

        {notes.length > 0 && (
          <ul className="notes">
            {notes.map((n, i) => (
              <li key={i}>
                <span className="chip chip--info">i Nota</span> {n.replace(/^Nota:\s*/, "")}
              </li>
            ))}
          </ul>
        )}

        <Section title="Documentos" count={DOC_ORDER.length}>
          <div className="cards">
            {DOC_ORDER.map((t) => {
              const docs = report.document_analyses.filter((a) => a.document_type === t);
              const missing = !received.get(t);
              return (
                <article key={t} className={`card${missing ? " card--missing" : ""}`}>
                  <h3>{DOC_LABEL[t]}</h3>
                  {missing ? (
                    <span className="chip chip--bad">✕ Falta</span>
                  ) : (
                    docs.map((d) => {
                      const failed = d.rule_evaluations.filter((r) => !r.passed).length;
                      return (
                        <div key={d.document_name} className="card__doc">
                          <div className="small">{d.document_name}</div>
                          <div className="muted small">
                            Identificado con {Math.round(d.classification_confidence * 100)} % de
                            seguridad
                          </div>
                          <span className={`chip chip--${failed ? "warn" : "ok"}`}>
                            {failed ? `! ${failed} regla(s) sin cumplir` : "✓ Reglas cumplidas"}
                          </span>
                        </div>
                      );
                    })
                  )}
                </article>
              );
            })}
            {report.document_analyses
              .filter((a) => a.document_type === "desconocido")
              .map((a) => (
                <article key={a.document_name} className="card card--missing">
                  <h3>Sin identificar</h3>
                  <div className="small">{a.document_name}</div>
                  <span className="chip chip--warn">! No se pudo clasificar</span>
                </article>
              ))}
          </div>
        </Section>

        <Section title="Hallazgos" count={findings.length} hint="De lo más grave a lo menos">
          {findings.length === 0 && <p>✓ No se encontraron hallazgos.</p>}
          {findings.map((f) => (
            <details key={f.key} className={`finding finding--${f.severity}`}>
              <summary>
                <SeverityChip severity={f.severity} /> <span>{f.title}</span>
              </summary>
              <div className="finding__body">
                <div className="muted small">Origen: {f.origin}</div>
                {Object.keys(f.values).length > 0 && (
                  <ul className="values">
                    {Object.entries(f.values).map(([doc, v]) => (
                      <li key={doc}>
                        <strong>{doc}:</strong> {v}
                      </li>
                    ))}
                  </ul>
                )}
                {f.evidence.length === 0 && <p className="muted small">Sin cita asociada.</p>}
                {f.evidence.map((e, i) => (
                  <div key={i} className="evidence">
                    <blockquote className="quote">“{e.snippet}”</blockquote>
                    <div className="small">
                      {e.document_name}
                      {e.page ? ` · página ${e.page}` : ""}{" "}
                      <button className="link" onClick={() => setEvidence(e)}>
                        Ver en el documento
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </details>
          ))}
        </Section>

        <Section title="Comparación entre documentos" count={5}>
          <Compare report={report} onEvidence={setEvidence} />
        </Section>
        <Section title="Matriz de reglas" open={false}>
          <Matrix report={report} />
        </Section>
        <Section title="Datos extraídos" open={false}>
          <Fields analyses={report.document_analyses} onEvidence={setEvidence} />
        </Section>
        <Section title="Cómo se decidió" open={false}>
          <Trace report={report} />
        </Section>
      </div>

      {evidence && (
        <EvidencePanel
          expedienteId={report.expediente_id}
          evidence={evidence}
          onClose={() => setEvidence(null)}
        />
      )}
    </div>
  );
}

function verdictCls(r: Report) {
  return r.recommendation === "Cumple" ? "ok" : r.recommendation === "No cumple" ? "bad" : "warn";
}
