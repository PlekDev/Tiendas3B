import type { Evidence } from "../types";
import { fileUrl } from "../store";

/** Panel lateral: la cita y, si el PDF se subió en esta sesión, el PDF en la página indicada. */
export function EvidencePanel({
  expedienteId,
  evidence,
  onClose,
}: {
  expedienteId: string;
  evidence: Evidence;
  onClose: () => void;
}) {
  const url = fileUrl(expedienteId, evidence.document_name);
  const isImage = /\.(jpe?g|png|tiff?)$/i.test(evidence.document_name);
  return (
    <aside className="panel" aria-label="Evidencia">
      <header className="panel__head">
        <div>
          <strong>{evidence.document_name}</strong>
          <div className="muted">
            {evidence.page ? `Página ${evidence.page}` : "Página no indicada"}
          </div>
        </div>
        <button className="btn btn--ghost" onClick={onClose} aria-label="Cerrar evidencia">
          ✕
        </button>
      </header>
      <blockquote className="quote">“{evidence.snippet}”</blockquote>
      {url ? (
        isImage ? (
          <img className="panel__viewer" src={url} alt={evidence.document_name} />
        ) : (
          <iframe
            key={`${url}#${evidence.page}`}
            className="panel__viewer"
            src={`${url}#page=${evidence.page ?? 1}`}
            title={evidence.document_name}
          />
        )
      ) : (
        <p className="muted pad">
          Este expediente es un ejemplo o se subió en otra sesión, así que el PDF no está
          disponible. La cita de arriba es la que respalda el hallazgo.
        </p>
      )}
    </aside>
  );
}
