import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion } from "motion/react";
import { ChevronLeft, ChevronRight, Highlighter, X } from "lucide-react";
import type { Evidence, Report } from "../types";
import { DOC_LABEL } from "../labels";
import { fileUrl } from "../store";
import { type EvTarget, snippetsOf } from "../model";

/** Visor: la cita y el PDF en su página si se subió en esta sesión; si no, la hoja reconstruida con las citas. */
export function EvidencePanel({
  report,
  target,
  narrow,
  onClose,
  onLocate,
}: {
  report: Report;
  target: EvTarget;
  narrow: boolean;
  onClose: () => void;
  onLocate?: (e: Evidence) => void;
}) {
  const { evidence, doubt } = target;
  const [page, setPage] = useState(evidence.page ?? 1);
  useEffect(() => setPage(evidence.page ?? 1), [evidence]);
  // En teléfono el visor tapa la pantalla: no dejar que la página de atrás se desplace.
  useEffect(() => {
    if (!narrow) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [narrow]);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const url = fileUrl(report.expediente_id, evidence.document_name);
  const isImage = /\.(jpe?g|png|tiff?)$/i.test(evidence.document_name);
  const analysis = report.document_analyses.find((a) => a.document_name === evidence.document_name);
  const title = analysis ? DOC_LABEL[analysis.document_type] : evidence.document_name;
  const paras = snippetsOf(report, evidence.document_name, evidence.page);
  if (!paras.includes(evidence.snippet)) paras.unshift(evidence.snippet);

  const sheet = narrow
    ? {
        initial: { y: "100%" },
        animate: { y: 0 },
        exit: { y: "100%" },
        drag: "y" as const,
        dragConstraints: { top: 0, bottom: 0 },
        dragElastic: { top: 0, bottom: 0.6 },
        onDragEnd: (_: unknown, info: { offset: { y: number }; velocity: { y: number } }) => {
          if (info.offset.y > 120 || info.velocity.y > 600) onClose();
        },
      }
    : { initial: { opacity: 0, x: 40, scale: 0.97 }, animate: { opacity: 1, x: 0, scale: 1 }, exit: { opacity: 0, x: 40 } };

  const ui = (
    <>
    {narrow && (
      <motion.div
        className="ev__backdrop"
        onClick={onClose}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
      />
    )}
    <motion.aside
      className={`ev${narrow ? " ev--sheet" : ""}`}
      aria-label="Visor de evidencia"
      role={narrow ? "dialog" : undefined}
      aria-modal={narrow || undefined}
      transition={{ type: "spring", stiffness: 420, damping: 36 }}
      {...sheet}
    >
      {narrow && <div className="ev__grip" aria-hidden />}
      <div className="ev__head">
        <div className="sec" style={{ gap: 2, minWidth: 0 }}>
          <span className="eyebrow">Evidencia</span>
          <b>{title}</b>
          <span className="mono small muted" style={{ overflowWrap: "anywhere" }}>
            {evidence.document_name} · {evidence.page ? `Página ${page}` : "Página no indicada"}
          </span>
        </div>
        <motion.button className="iconbtn iconbtn--lg" onClick={onClose} aria-label="Cerrar visor" whileTap={{ scale: 0.88 }} whileHover={{ rotate: 90 }}>
          <X size={22} aria-hidden />
        </motion.button>
      </div>
      <div className="ev__body">
        <AnimatePresence mode="wait">
        <motion.div
          key={evidence.snippet + evidence.document_name}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -6 }}
          transition={{ duration: 0.2 }}
          className="sec"
          style={{ gap: 14 }}
        >
        {doubt ? (
          <div className="doubtbox" style={{ flexDirection: "column", alignItems: "flex-start", gap: 6 }}>
            <strong>? Dato en duda</strong>
            <span className="pretty">{doubt}</span>
          </div>
        ) : (
          <figure className="quote">
            <blockquote style={{ fontSize: 18 }}>“{evidence.snippet}”</blockquote>
          </figure>
        )}

        {onLocate && (
          <motion.button className="btn btn--primary" style={{ alignSelf: "flex-start" }} onClick={() => onLocate(evidence)} whileTap={{ scale: 0.96 }}>
            <Highlighter size={18} aria-hidden /> Ver subrayado en el documento
          </motion.button>
        )}

        {url ? (
          <>
            {!isImage && (
              <div className="ev__pager">
                <span>
                  <button className="pagebtn" aria-label="Página anterior" disabled={page <= 1} onClick={() => setPage(page - 1)}>
                    <ChevronLeft size={18} />
                  </button>
                  Página {page}
                  <button className="pagebtn" aria-label="Página siguiente" onClick={() => setPage(page + 1)}>
                    <ChevronRight size={18} />
                  </button>
                </span>
                {evidence.page && page !== evidence.page && (
                  <button className="linkbtn" onClick={() => setPage(evidence.page!)}>
                    Volver a la página de la cita
                  </button>
                )}
              </div>
            )}
            {isImage ? (
              <img className="viewer" src={url} alt={evidence.document_name} style={{ minHeight: 0 }} />
            ) : (
              <iframe key={page} className="viewer" src={`${url}#page=${page}`} title={evidence.document_name} />
            )}
          </>
        ) : (
          <>
            <div className="paper" aria-label="Hoja reconstruida con las citas">
              <div className="paper__head">{title}</div>
              {paras.map((p, i) => {
                const hit = p === evidence.snippet;
                return (
                  <motion.p
                    key={p}
                    className={hit ? (doubt ? "is-doubt" : "is-hit") : ""}
                    initial={{ opacity: 0, y: 6 }}
                    animate={
                      hit && !doubt
                        ? { opacity: 1, y: 0, backgroundSize: ["0% 100%", "100% 100%"] }
                        : { opacity: 1, y: 0 }
                    }
                    transition={{ delay: 0.08 * i, duration: hit ? 0.6 : 0.25, ease: "easeOut" }}
                  >
                    {p}
                  </motion.p>
                );
              })}
            </div>
            <p className="small muted pretty">
              El PDF original no está en esta sesión (es un ejemplo o se subió antes), así que la
              hoja se arma con las citas que se extrajeron de esa página. Lo resaltado es la prueba.
            </p>
          </>
        )}
        </motion.div>
        </AnimatePresence>
      </div>
    </motion.aside>
    </>
  );
  // En teléfono va directo en <body>: un ancestro animado (transform) rompería position: fixed.
  return narrow ? createPortal(ui, document.body) : ui;
}
