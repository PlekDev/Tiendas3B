import { useMemo, useState } from "react";
import { AnimatePresence } from "motion/react";
import type { Entry, Evidence, Report } from "../types";
import { CONFIDENCE_HELP, VERDICT_UI, seconds, shortDate } from "../labels";
import * as M from "../model";
import { Chip, Collapse, ConfidenceRing, Dot } from "./Bits";
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

export function Dictamen({
  entry,
  onBack,
  onRemove,
  onUpload,
}: {
  entry: Entry;
  onBack: () => void;
  onRemove: () => void;
  onUpload: () => void;
}) {
  const report = entry.report!;
  const [ev, setEv] = useState<M.EvTarget | null>(null);

  const vm = useMemo(() => {
    const comp = M.comparison(report);
    return {
      comp,
      findings: M.findings(report),
      passes: M.passes(report),
      reasons: M.reasons(report, comp),
      docs: M.docCards(report),
      matrix: M.matrix(report, comp),
      fields: M.fieldRows(report),
      agents: M.agents(report),
      lead: M.lead(report),
      why: M.confidenceWhy(report),
    };
  }, [report]);

  const [open, setOpen] = useState<Record<string, boolean>>(() =>
    vm.findings[0] ? { [vm.findings[0].key]: true } : {},
  );
  const [passesOpen, setPassesOpen] = useState(false);
  const show = (t?: M.EvTarget) => t && setEv(t);
  const showEv = (e?: Evidence) => e && setEv({ evidence: e });

  const v = VERDICT_UI[report.recommendation];
  const heur = report.llm_mode === "heuristico";
  const nb = vm.findings.filter((f) => f.tone === "bad").length;
  const nw = vm.findings.filter((f) => f.tone === "warn").length;
  const ni = vm.findings.filter((f) => f.tone === "info").length;
  const summary =
    [
      nb && `${nb} bloqueante${nb > 1 ? "s" : ""}`,
      nw && `${nw} por revisar`,
      ni && `${ni} nota${ni > 1 ? "s" : ""}`,
    ]
      .filter(Boolean)
      .join(" · ") || "Sin hallazgos";

  return (
    <div className={`dict${ev ? " dict--ev" : ""}`}>
      <main className="dict__main" data-screen-label="Dictamen">
        <div className="dict__bar">
          <div className="chips" style={{ alignItems: "center", gap: "8px 14px" }}>
            <button className="back" onClick={onBack}>
              ← Bandeja
            </button>
            <span className="mono" style={{ fontSize: 14, fontWeight: 500 }}>
              {report.expediente_id}
            </span>
          </div>
          <div className="dict__meta">
            <span>{shortDate(entry.createdAt)}</span>
            <span>·</span>
            <span>Analizado en {seconds(report.processing_ms)}</span>
            {heur ? <Chip tone="info">Modo sin IA</Chip> : <Chip tone="ok">IA: {report.llm_mode}</Chip>}
            <button className="btn" onClick={() => download(report)}>
              Descargar JSON
            </button>
            <button className="btn" onClick={onRemove}>
              Quitar de la bandeja
            </button>
          </div>
        </div>

        <section className={`hero t-${v.cls}`}>
          <div className="hero__top">
            <div className="hero__verdict">
              <div className="hero__title">
                <span className="hero__icon" aria-hidden>
                  {v.icon}
                </span>
                <h1 className="hero__h1">{report.recommendation}</h1>
              </div>
              <p className="hero__lead">{vm.lead}</p>
            </div>
            <div className="hero__conf">
              <ConfidenceRing value={report.confidence} tone={v.cls} />
              <div className="sec" style={{ gap: 4 }}>
                <span className="small" style={{ fontWeight: 700 }}>
                  Confianza
                </span>
                <span className="small muted" style={{ lineHeight: 1.4 }}>
                  {CONFIDENCE_HELP}
                </span>
                <span className="small" style={{ lineHeight: 1.4 }}>
                  {vm.why}
                </span>
              </div>
            </div>
          </div>
          <div className="reasons">
            <span className="eyebrow" style={{ marginBottom: 6 }}>
              Razones principales
            </span>
            {vm.reasons.map((r, i) => (
              <button
                key={i}
                className="reason"
                onClick={() => {
                  if (r.target) setEv(r.target);
                  else if (r.findingKey) {
                    setOpen((o) => ({ ...o, [r.findingKey!]: true }));
                    document.getElementById(`f-${r.findingKey}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
                  }
                }}
              >
                <Dot tone={r.tone} />
                <span className="reason__text">
                  {r.text}
                  {r.doc && <span className="small faint"> · {r.doc}</span>}
                </span>
                {(r.target || r.findingKey) && (
                  <span className="small" style={{ fontWeight: 600, color: "var(--info)", whiteSpace: "nowrap" }}>
                    {r.target ? "Ver prueba →" : "Ver hallazgo →"}
                  </span>
                )}
              </button>
            ))}
          </div>
        </section>

        <section className="sec">
          <h2 className="h2">Documentos</h2>
          <div className="docs">
            {vm.docs.map((d) => (
              <div key={d.key} className={`doc${d.missing ? " doc--missing" : ""}`}>
                <div className="doc__head">
                  <span>{d.title}</span>
                  {d.missing ? (
                    <Chip tone="miss" size="sm">
                      Falta
                    </Chip>
                  ) : d.type ? (
                    <Chip tone="ok" size="sm">
                      Recibido
                    </Chip>
                  ) : (
                    <Chip tone="warn" size="sm">
                      Revisar
                    </Chip>
                  )}
                </div>
                <span className="mono small" style={{ color: d.missing ? "var(--ink-3)" : "var(--ink-2)", overflowWrap: "anywhere" }}>
                  {d.file}
                </span>
                {!d.missing && d.conf != null && (
                  <span className="small muted">Identificado con {Math.round(d.conf * 100)} % de seguridad</span>
                )}
                <div className="doc__issues">
                  {d.issues.map((i, k) => (
                    <span key={k} className="issue">
                      <Dot tone={i.tone} ring />
                      {i.label}
                    </span>
                  ))}
                  {d.missing && (
                    <button className="btn" style={{ alignSelf: "flex-start", height: 30 }} onClick={onUpload}>
                      Subir documento
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="sec">
          <div className="sec__head sec__head--row">
            <h2 className="h2">Hallazgos</h2>
            <span className="small muted">{summary}</span>
          </div>
          {!vm.findings.length && <div className="okbox">✓ Nada requiere acción en este expediente.</div>}
          <div className="findings">
            {vm.findings.map((f) => {
              const isOpen = !!open[f.key];
              const doubt = !f.evidence.length && !f.missingDoc;
              return (
                <div key={f.key} id={`f-${f.key}`} className={`finding t-${f.tone}${doubt ? " finding--doubt" : ""}`}>
                  <button
                    className="finding__head"
                    aria-expanded={isOpen}
                    onClick={() => setOpen((o) => ({ ...o, [f.key]: !o[f.key] }))}
                  >
                    <Chip tone={f.tone}>
                      {f.tone === "bad" ? "Bloqueante" : f.tone === "warn" ? "Revisar" : "Nota"}
                    </Chip>
                    <span className="finding__title">
                      <b>{f.title}</b>
                      <span className="small faint">{f.docs}</span>
                    </span>
                    <span className="chev">{isOpen ? "Ocultar ▴" : "Ver detalle ▾"}</span>
                  </button>
                  <Collapse open={isOpen}>
                    <div className="finding__body">
                      <p className="muted pretty" style={{ maxWidth: 720 }}>
                        {f.what}
                      </p>
                      {f.values.length > 0 && (
                        <div className="vals">
                          {f.values.map((x) => (
                            <button
                              key={x.doc}
                              className={`val${x.dev ? ` val--dev t-${f.tone}` : ""}`}
                              disabled={!x.target}
                              onClick={() => show(x.target)}
                            >
                              <span className="small faint">{x.doc}</span>
                              <b>{x.value}</b>
                            </button>
                          ))}
                        </div>
                      )}
                      {f.evidence.map((e, i) => (
                        <figure key={i} className="quote">
                          <blockquote>“{e.snippet}”</blockquote>
                          <figcaption>
                            <span className="mono">
                              {e.document_name}
                              {e.page ? ` · página ${e.page}` : ""}
                            </span>
                            <button className="linkbtn" onClick={() => showEv(e)}>
                              Ver en el documento →
                            </button>
                          </figcaption>
                        </figure>
                      ))}
                      {doubt && (
                        <div className="doubtbox">
                          <span>
                            <strong>? En duda.</strong> Sin cita verificable en {f.docs}.
                          </span>
                        </div>
                      )}
                      {f.missingDoc && (
                        <button className="btn" style={{ alignSelf: "flex-start" }} onClick={onUpload}>
                          Subir documento
                        </button>
                      )}
                    </div>
                  </Collapse>
                </div>
              );
            })}
            {vm.passes.length > 0 && (
              <div className="card">
                <button className="passes__head" aria-expanded={passesOpen} onClick={() => setPassesOpen(!passesOpen)}>
                  <Dot tone="ok" />
                  <span style={{ flex: 1, fontWeight: 600 }}>{vm.passes.length} reglas cumplen</span>
                  <span className="chev" style={{ marginTop: 0 }}>
                    {passesOpen ? "Ocultar ▴" : "Ver ▾"}
                  </span>
                </button>
                <Collapse open={passesOpen}>
                  <div className="passes__list">
                    {vm.passes.map((p) => (
                      <button key={p.key} className="pass" disabled={!p.evidence} onClick={() => showEv(p.evidence)}>
                        <span>
                          {p.text} <span className="small faint">· {p.doc}</span>
                        </span>
                        {p.evidence && (
                          <span className="small" style={{ color: "var(--info)", fontWeight: 600, whiteSpace: "nowrap" }}>
                            Ver prueba
                          </span>
                        )}
                      </button>
                    ))}
                  </div>
                </Collapse>
              </div>
            )}
          </div>
        </section>

        <Compare rows={vm.comp} onEvidence={setEv} />
        <Matrix rows={vm.matrix} />
        <Fields rows={vm.fields} onEvidence={setEv} />
        <Trace report={report} rows={vm.agents} />
      </main>

      <AnimatePresence>
        {ev && <EvidencePanel key="ev" report={report} target={ev} onClose={() => setEv(null)} />}
      </AnimatePresence>
    </div>
  );
}
