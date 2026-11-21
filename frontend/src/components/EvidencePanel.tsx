import { useEffect, useState } from "react";
import { motion } from "motion/react";
import type { Report } from "../types";
import { DOC_LABEL } from "../labels";
import { fileUrl } from "../store";
import { type EvTarget, snippetsOf } from "../model";

/** Visor: la cita y el PDF en su página si se subió en esta sesión; si no, la hoja reconstruida con las citas. */
export function EvidencePanel({
  report,
  target,
  onClose,
}: {
  report: Report;
  target: EvTarget;
  onClose: () => void;
}) {
  const { evidence, doubt } = target;
  const [page, setPage] = useState(evidence.page ?? 1);
  useEffect(() => setPage(evidence.page ?? 1), [evidence]);

  const url = fileUrl(report.expediente_id, evidence.document_name);
  const isImage = /\.(jpe?g|png|tiff?)$/i.test(evidence.document_name);
  const analysis = report.document_analyses.find((a) => a.document_name === evidence.document_name);
  const title = analysis ? DOC_LABEL[analysis.document_type] : evidence.document_name;
  const paras = snippetsOf(report, evidence.document_name, evidence.page);
  if (!paras.includes(evidence.snippet)) paras.unshift(evidence.snippet);

  return (
    <motion.aside
      className="ev"
      aria-label="Visor de evidencia"
      initial={{ opacity: 0, x: 16 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 16 }}
      transition={{ type: "spring", stiffness: 500, damping: 38 }}
    >
      <div className="ev__head">
        <div className="sec" style={{ gap: 2, minWidth: 0 }}>
          <span className="eyebrow">Evidencia</span>
          <b>{title}</b>
          <span className="mono small muted" style={{ overflowWrap: "anywhere" }}>
            {evidence.document_name} · {evidence.page ? `Página ${page}` : "Página no indicada"}
          </span>
        </div>
        <button className="btn" onClick={onClose}>
          <span className="only-wide">Cerrar ✕</span>
          <span className="only-narrow">← Volver al dictamen</span>
        </button>
      </div>
      <div className="ev__body">
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

        {url ? (
          <>
            {!isImage && (
              <div className="ev__pager">
                <span>
                  <button className="pagebtn" aria-label="Página anterior" disabled={page <= 1} onClick={() => setPage(page - 1)}>
                    ‹
                  </button>
                  Página {page}
                  <button className="pagebtn" aria-label="Página siguiente" onClick={() => setPage(page + 1)}>
                    ›
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
              {paras.map((p) => (
                <p key={p} className={p === evidence.snippet ? (doubt ? "is-doubt" : "is-hit") : ""}>
                  {p}
                </p>
              ))}
            </div>
            <p className="small muted pretty">
              El PDF original no está en esta sesión (es un ejemplo o se subió antes), así que la
              hoja se arma con las citas que se extrajeron de esa página. Lo resaltado es la prueba.
            </p>
          </>
        )}
      </div>
    </motion.aside>
  );
}
