import { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { FileSearch, LoaderCircle, RotateCcw, ScanText } from "lucide-react";
import type { Report } from "../types";
import { type VisorData, type VisorMark, getVisor, getVisorEjemplo } from "../api";
import { fileOf } from "../store";
import { DOC_LABEL } from "../labels";
import { type DocMark, docMarks } from "../model";
import { Reveal, spring } from "../anim";
import { Dot } from "./Bits";

/** Pedido de "llévame a esta cita en el documento marcado". `n` cambia en cada clic. */
export interface Locate {
  doc: string;
  snippet: string;
  n: number;
}

type Load =
  | { s: "loading" }
  | { s: "ok"; data: VisorData }
  | { s: "error"; msg: string }
  | { s: "nofile" };

const isDemo = (r: Report) => r.expediente_id.startsWith("DEMO-");

/** El visor marcado necesita el archivo subido en esta sesión (o un ejemplo). */
export function canView(report: Report, doc: string): boolean {
  return !!fileOf(report.expediente_id, doc) || isDemo(report);
}

// Una sola petición por documento y análisis: el OCR de un escaneo puede tardar.
const cache = new Map<string, Promise<VisorData>>();

function fetchView(report: Report, doc: string, marks: DocMark[]): Promise<VisorData> | null {
  const key = `${report.expediente_id}/${doc}/${report.processing_ms}`;
  const hit = cache.get(key);
  if (hit) return hit;
  const body = marks.map((m) => ({ id: m.id, texto: m.value, contexto: m.snippet, pagina: m.page }));
  const file = fileOf(report.expediente_id, doc);
  const p = file
    ? getVisor(file, doc, body)
    : isDemo(report)
      ? getVisorEjemplo(report.expediente_id, doc, body)
      : null;
  if (!p) return null;
  cache.set(key, p);
  p.catch(() => cache.delete(key));
  return p;
}

const domId = (doc: string, id: string) => `vm-${doc.replace(/[^\w-]/g, "_")}-${id}`;
const pctBox = (r: VisorMark["rects"][number]) => ({
  left: `calc(${r[0] * 100}% - 3px)`,
  top: `calc(${r[1] * 100}% - 2px)`,
  width: `calc(${(r[2] - r[0]) * 100}% + 6px)`,
  height: `calc(${(r[3] - r[1]) * 100}% + 4px)`,
});

const LEGEND = [
  { tone: "ok", label: "Dato leído" },
  { tone: "doubt", label: "En duda" },
  { tone: "warn", label: "Por revisar" },
  { tone: "bad", label: "No cumple" },
  { tone: "info", label: "Nota" },
] as const;

export function DocViewer({ report, locate }: { report: Report; locate: Locate | null }) {
  const docs = report.document_analyses;
  const [doc, setDoc] = useState(docs[0]?.document_name ?? "");
  const [loads, setLoads] = useState<Record<string, Load>>({});
  const [sel, setSel] = useState<string | null>(null);
  const pending = useRef<string | null>(null);
  const root = useRef<HTMLDivElement>(null);

  const marksByDoc = useMemo(
    () => Object.fromEntries(docs.map((a) => [a.document_name, docMarks(report, a)])),
    [report, docs],
  );
  const marks = marksByDoc[doc] ?? [];
  const load = loads[doc];

  const start = (name: string) => {
    const p = fetchView(report, name, marksByDoc[name] ?? []);
    if (!p) {
      setLoads((l) => ({ ...l, [name]: { s: "nofile" } }));
      return;
    }
    setLoads((l) => ({ ...l, [name]: { s: "loading" } }));
    p.then(
      (data) => setLoads((l) => ({ ...l, [name]: { s: "ok", data } })),
      (e: Error) => setLoads((l) => ({ ...l, [name]: { s: "error", msg: e.message } })),
    );
  };

  useEffect(() => {
    if (doc && !loads[doc]) start(doc);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [doc]);

  // "Ver subrayado" desde el visor de evidencia o los hallazgos.
  useEffect(() => {
    if (!locate) return;
    setDoc(locate.doc);
    pending.current = locate.snippet;
    root.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [locate]);

  const found = load?.s === "ok" ? new Map(load.data.marks.map((m) => [m.id, m])) : new Map<string, VisorMark>();

  const focus = (id: string) => {
    setSel(id);
    requestAnimationFrame(() =>
      document.getElementById(domId(doc, id))?.scrollIntoView({ behavior: "smooth", block: "center" }),
    );
  };

  useEffect(() => {
    if (load?.s !== "ok" || !pending.current) return;
    const snip = pending.current;
    pending.current = null;
    const m = marks.find((x) => x.snippet === snip && found.has(x.id)) ?? marks.find((x) => x.snippet === snip);
    if (m) setTimeout(() => focus(m.id), 350);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [load, doc]);

  if (!docs.length) return null;
  const pages = load?.s === "ok" ? load.data.pages : [];
  const ocr = pages.some((p) => p.source === "ocr");
  const located = marks.filter((m) => found.has(m.id)).length;
  const selMark = marks.find((m) => m.id === sel);

  return (
    <div ref={root} className="vwrap">
      <Reveal className="sec">
        <div className="sec__head sec__head--row">
          <h2 className="h2">Documentos marcados</h2>
          <span className="small muted">
            Subrayado lo que se leyó de cada documento. En color, lo que no cumple o no coincide.
          </span>
        </div>

        <div className="vtabs" role="tablist" aria-label="Documento">
          {docs.map((a) => {
            const probs = (marksByDoc[a.document_name] ?? []).filter((m) => m.tone === "bad" || m.tone === "warn").length;
            const on = a.document_name === doc;
            return (
              <button
                key={a.document_name}
                role="tab"
                aria-selected={on}
                className={`vtab${on ? " is-on" : ""}`}
                onClick={() => {
                  setDoc(a.document_name);
                  setSel(null);
                }}
              >
                {on && <motion.span layoutId="vtab-bg" className="vtab__bg" transition={spring} />}
                <span className="vtab__label">
                  <b>{DOC_LABEL[a.document_type]}</b>
                  <span className="mono small">{a.document_name}</span>
                </span>
                {probs > 0 && <span className="vtab__count">{probs}</span>}
              </button>
            );
          })}
        </div>

        <div className="card vview">
          <aside className="vlist" aria-label="Lo que se marcó">
            <div className="vlegend">
              {LEGEND.map((l) => (
                <span key={l.tone} className={`vlegend__item t-${l.tone}`}>
                  <i aria-hidden />
                  {l.label}
                </span>
              ))}
            </div>
            {load?.s === "ok" && (
              <span className="small muted vlist__meta">
                {ocr ? <ScanText size={15} aria-hidden /> : <FileSearch size={15} aria-hidden />}
                {located} de {marks.length} ubicados · {ocr ? "leído con OCR" : "texto del PDF"}
              </span>
            )}
            <div className="vlist__items">
              {marks.map((m) => {
                const hit = found.get(m.id);
                return (
                  <button
                    key={m.id}
                    className={`vitem t-${m.tone}${sel === m.id ? " is-on" : ""}`}
                    disabled={load?.s === "ok" && !hit}
                    onClick={() => focus(m.id)}
                  >
                    <Dot tone={m.tone} />
                    <span className="vitem__text">
                      <b>{m.campo}</b>
                      <span className="small">{m.value ?? m.note}</span>
                      {load?.s === "ok" && (
                        <span className="small faint">{hit ? `Página ${hit.page}` : "No se ubicó en el documento"}</span>
                      )}
                    </span>
                  </button>
                );
              })}
              {!marks.length && <span className="small muted">No se leyeron datos de este documento.</span>}
            </div>
          </aside>

          <div className="vpages">
            {(!load || load.s === "loading") && (
              <div className="vstate">
                <LoaderCircle className="spin" size={28} aria-hidden />
                <b>Preparando {doc}…</b>
                <span className="small muted">Si es un escaneo, el OCR puede tardar unos segundos por página.</span>
              </div>
            )}
            {load?.s === "nofile" && (
              <div className="vstate">
                <FileSearch size={28} aria-hidden />
                <b>El documento no está en esta sesión</b>
                <span className="small muted pretty">
                  Los PDF solo viven en tu navegador mientras la página está abierta. Vuelve a subir el
                  expediente para verlo marcado.
                </span>
              </div>
            )}
            {load?.s === "error" && (
              <div className="vstate">
                <b>No se pudo preparar el documento</b>
                <span className="small muted">{load.msg}</span>
                <button className="btn" onClick={() => start(doc)}>
                  <RotateCcw size={16} aria-hidden /> Reintentar
                </button>
              </div>
            )}
            {pages.map((p) => {
              const here = marks.filter((m) => found.get(m.id)?.page === p.page);
              return (
                <div key={p.page} className="vpage" style={{ aspectRatio: `${p.width} / ${p.height}` }}>
                  <img src={p.image} alt={`${doc}, página ${p.page}`} loading="lazy" draggable={false} />
                  {here.map((m, i) =>
                    found.get(m.id)!.rects.map((r, k) => (
                      <motion.button
                        key={`${m.id}-${k}`}
                        id={k === 0 ? domId(doc, m.id) : undefined}
                        className={`vmark vmark--${m.kind} t-${m.tone}${sel === m.id ? " is-on" : ""}`}
                        style={{ ...pctBox(r), originX: 0 }}
                        initial={{ opacity: 0, scaleX: 0 }}
                        whileInView={{ opacity: 1, scaleX: 1 }}
                        viewport={{ once: true }}
                        transition={{ duration: 0.45, ease: "easeOut", delay: 0.04 * i }}
                        aria-label={`${m.campo}: ${m.value ?? m.note}`}
                        title={`${m.campo}: ${m.value ?? m.note}`}
                        onClick={() => setSel(sel === m.id ? null : m.id)}
                      />
                    )),
                  )}
                  <AnimatePresence>
                    {selMark && found.get(selMark.id)?.page === p.page && (
                      <motion.div
                        key={selMark.id}
                        className={`vtip t-${selMark.tone}`}
                        style={{
                          left: `${Math.min(found.get(selMark.id)!.rects[0][0] * 100, 55)}%`,
                          top: `calc(${found.get(selMark.id)!.rects.at(-1)![3] * 100}% + 8px)`,
                        }}
                        initial={{ opacity: 0, y: -6, scale: 0.96 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: -4 }}
                        transition={spring}
                      >
                        <b>{selMark.campo}</b>
                        {selMark.value && <span>{selMark.value}</span>}
                        <span className="small">{selMark.note}</span>
                      </motion.div>
                    )}
                  </AnimatePresence>
                  <span className="vpage__num">
                    Página {p.page}
                    {p.source === "ocr" ? " · OCR" : ""}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </Reveal>
    </div>
  );
}
