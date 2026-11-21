import { useMemo, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { ArrowLeft, Download, Trash2 } from "lucide-react";
import { Reveal, bouncy, fadeUp, press, softSpring, stagger, useNarrow } from "../anim";
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
  const narrow = useNarrow();
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
            <motion.button className="back back--icon" onClick={onBack} whileHover={{ x: -3 }} whileTap={{ scale: 0.95 }}>
              <ArrowLeft size={20} aria-hidden /> Bandeja
            </motion.button>
            <span className="mono" style={{ fontSize: 14, fontWeight: 500 }}>
              {report.expediente_id}
            </span>
          </div>
          <div className="dict__meta">
            <span>{shortDate(entry.createdAt)}</span>
            <span>·</span>
            <span>Analizado en {seconds(report.processing_ms)}</span>
            {heur ? <Chip tone="info">Modo sin IA</Chip> : <Chip tone="ok">IA: {report.llm_mode}</Chip>}
            <motion.button className="btn btn--icon" onClick={() => download(report)} title="Descargar JSON" {...press}>
              <Download size={18} aria-hidden />
              <span className="btn__label">Descargar JSON</span>
            </motion.button>
            <motion.button className="btn btn--icon" onClick={onRemove} title="Quitar de la bandeja" {...press}>
              <Trash2 size={18} aria-hidden />
              <span className="btn__label">Quitar</span>
            </motion.button>
          </div>
        </div>

        <motion.section
          className={`hero t-${v.cls}`}
          initial={{ opacity: 0, y: 30, scale: 0.97 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={softSpring}
        >
          <motion.span
            className="hero__glow"
            aria-hidden
            initial={{ opacity: 0 }}
            animate={{ opacity: [0, 0.9, 0.5] }}
            transition={{ duration: 1.4, ease: "easeOut" }}
          />
          <div className="hero__top">
            <div className="hero__verdict">
              <div className="hero__title">
                <motion.span
                  className="hero__icon"
                  aria-hidden
                  initial={{ scale: 0, rotate: -180 }}
                  animate={{ scale: [0, 1.25, 1], rotate: 0 }}
                  transition={{ duration: 0.7, times: [0, 0.6, 1], ease: "easeOut", delay: 0.1 }}
                >
                  {v.icon}
                </motion.span>
                <motion.h1
                  className="hero__h1"
                  initial={{ opacity: 0, x: -20, filter: "blur(6px)" }}
                  animate={{ opacity: 1, x: 0, filter: "blur(0px)" }}
                  transition={{ ...softSpring, delay: 0.2 }}
                >
                  {report.recommendation}
                </motion.h1>
              </div>
              <motion.p className="hero__lead" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.35 }}>
                {vm.lead}
              </motion.p>
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
          <motion.div className="reasons" variants={stagger(0.08, 0.4)} initial="hidden" animate="show">
            <span className="eyebrow" style={{ marginBottom: 6 }}>
              Razones principales
            </span>
            {vm.reasons.map((r, i) => (
              <motion.button
                key={i}
                variants={fadeUp}
                whileHover={{ x: 6 }}
                whileTap={{ scale: 0.98 }}
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
              </motion.button>
            ))}
          </motion.div>
        </motion.section>

        <div className="dict__cols">
        <Reveal className="sec dict__docs">
          <h2 className="h2">Documentos</h2>
          <motion.div className="docs" variants={stagger(0.07)} initial="hidden" whileInView="show" viewport={{ once: true }}>
            {vm.docs.map((d) => (
              <motion.div
                key={d.key}
                variants={fadeUp}
                whileHover={{ y: -3 }}
                className={`doc${d.missing ? " doc--missing" : ""}`}
              >
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
                    <motion.button className="btn" style={{ alignSelf: "flex-start" }} onClick={onUpload} {...press}>
                      Subir documento
                    </motion.button>
                  )}
                </div>
              </motion.div>
            ))}
          </motion.div>
        </Reveal>

        <Reveal className="sec dict__findings">
          <div className="sec__head sec__head--row">
            <h2 className="h2">Hallazgos</h2>
            <span className="small muted">{summary}</span>
          </div>
          {!vm.findings.length && (
            <motion.div className="okbox" initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} transition={bouncy}>
              ✓ Nada requiere acción en este expediente.
            </motion.div>
          )}
          <motion.div className="findings" variants={stagger(0.06)} initial="hidden" whileInView="show" viewport={{ once: true }}>
            {vm.findings.map((f) => {
              const isOpen = !!open[f.key];
              const doubt = !f.evidence.length && !f.missingDoc;
              return (
                <motion.div
                  key={f.key}
                  id={`f-${f.key}`}
                  variants={fadeUp}
                  layout
                  className={`finding t-${f.tone}${doubt ? " finding--doubt" : ""}${isOpen ? " is-open" : ""}`}
                >
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
                    <motion.span className="chev" animate={{ rotate: isOpen ? 180 : 0 }} transition={bouncy} aria-label={isOpen ? "Ocultar" : "Ver detalle"}>
                      ▾
                    </motion.span>
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
                </motion.div>
              );
            })}
            {vm.passes.length > 0 && (
              <div className="card">
                <button className="passes__head" aria-expanded={passesOpen} onClick={() => setPassesOpen(!passesOpen)}>
                  <Dot tone="ok" />
                  <span style={{ flex: 1, fontWeight: 600 }}>{vm.passes.length} reglas cumplen</span>
                  <motion.span className="chev" style={{ marginTop: 0 }} animate={{ rotate: passesOpen ? 180 : 0 }} transition={bouncy}>
                    ▾
                  </motion.span>
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
          </motion.div>
        </Reveal>
        </div>

        <Compare rows={vm.comp} onEvidence={setEv} />
        <div className="dict__duo">
          <Matrix rows={vm.matrix} />
          <Trace report={report} rows={vm.agents} />
        </div>
        <Fields rows={vm.fields} onEvidence={setEv} />
      </main>

      <AnimatePresence>
        {ev && <EvidencePanel key="ev" report={report} target={ev} narrow={narrow} onClose={() => setEv(null)} />}
      </AnimatePresence>
    </div>
  );
}
