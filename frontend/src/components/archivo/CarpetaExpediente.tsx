import type { CSSProperties } from "react";
import { STAMP, blockingText, type Carpeta } from "./data";
import { DOUBT_THRESHOLD } from "../../labels";

const fmt = (ms: number) =>
  new Date(ms).toLocaleDateString("es-MX", { day: "numeric", month: "short", year: "numeric" });

/**
 * Un expediente como carpeta manila. Un clic la selecciona (el panel "Archivo en vivo" reacciona);
 * el dictamen se abre con doble clic o con el botón "Abrir".
 */
export function CarpetaExpediente({
  c,
  i,
  selected,
  onSelect,
  onOpen,
}: {
  c: Carpeta;
  i: number;
  selected: boolean;
  onSelect: () => void;
  onOpen: () => void;
}) {
  const doubt = c.conf != null && c.conf < DOUBT_THRESHOLD * 100;
  const status =
    c.kind === "proc"
      ? "Analizando en el servidor"
      : c.kind === "error"
        ? "✕ No se pudo analizar"
        : `${blockingText(c.blocking)} · ✓ Listo`;
  const aria = [
    `Expediente ${c.id}`,
    STAMP[c.kind],
    c.conf != null ? `confianza ${c.conf} por ciento` : null,
    status,
  ]
    .filter(Boolean)
    .join(", ");

  return (
    <div className="carp-wrap" style={{ "--i": Math.min(i, 14) } as CSSProperties}>
      <div className="carp-lift">
        <button
          type="button"
          className={`carp tone-${c.kind}${selected ? " is-sel" : ""}`}
          aria-pressed={selected}
          aria-label={aria}
          title="Clic: ver en el archivo · doble clic: abrir dictamen"
          onClick={onSelect}
          onDoubleClick={onOpen}
        >
          <span className="carp__sheet carp__sheet--a" aria-hidden />
          <span className="carp__sheet carp__sheet--b" aria-hidden />
          <span className="carp__tab" aria-hidden>
            {c.id}
          </span>
          <span className="carp__body" aria-hidden>
            <span className="carp__top">
              {c.kind === "proc" ? (
                <span className="carp__scan">
                  <span className="carp__scanline" />
                  <span className="carp__scantxt">Leyendo…</span>
                </span>
              ) : (
                <span className="carp__stamp">{STAMP[c.kind]}</span>
              )}
              {c.conf != null && (
                <span className="ar-ring" style={{ "--pv": c.conf } as CSSProperties}>
                  <span className="ar-ring__arc" />
                  <b className="ar-ring__n">
                    {c.conf}%{doubt ? "?" : ""}
                  </b>
                </span>
              )}
            </span>
            <span className="carp__date">{fmt(c.createdAt)}</span>
            <span className="carp__status">{status}</span>
          </span>
        </button>
        <button type="button" className="carp__open" onClick={onOpen} aria-label={`Abrir ${c.id}`}>
          Abrir →
        </button>
      </div>
    </div>
  );
}
