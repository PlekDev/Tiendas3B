import type { CSSProperties } from "react";
import { Cajonera } from "./Cajonera";
import { STAMP, summaryText, type Carpeta, type VerdictKind } from "./data";

const SHEETS = [
  { x0: "-46px", r0: "-18deg", r1: "-8deg", dx: "-74px", delay: "0s" },
  { x0: "40px", r0: "16deg", r1: "6deg", dx: "74px", delay: "2s" },
  { x0: "-12px", r0: "-9deg", r1: "2deg", dx: "0px", delay: "4s" },
];

/** Panel oscuro "Archivo · en vivo": hojas que entran, sello, cajonera y ficha. */
export function ArchivoVivo({
  selected,
  counts,
  processing,
  onOpen,
}: {
  selected: Carpeta | null;
  counts: Record<VerdictKind, number>;
  processing: number;
  onOpen: () => void;
}) {
  const stampKind = selected && selected.kind !== "proc" ? selected.kind : null;
  const openDrawer: VerdictKind | null =
    selected && (selected.kind === "warn" || selected.kind === "bad" || selected.kind === "ok") ? selected.kind : null;
  const reading = processing > 0;
  const tone = selected ? selected.kind : "ok";

  return (
    <section className="vivo" aria-label="Archivo en vivo">
      {/* Lámpara del archivero: se enciende mientras hay expedientes en análisis (sin texto). */}
      <span className={`vivo__lamp${reading ? " is-on" : ""}`} aria-hidden />

      {/* Se vuelve a montar al cambiar de carpeta: las hojas caen otra vez y el sello golpea de nuevo. */}
      <div className="scene" key={selected?.id ?? "vacio"} aria-hidden>
        {SHEETS.map((s, i) => (
          <div
            key={i}
            className={`sheet${i === 2 ? " sheet--front" : ""}`}
            style={{ "--x0": s.x0, "--r0": s.r0, "--r1": s.r1, "--dx": s.dx, animationDelay: s.delay } as CSSProperties}
          >
            <span className="sheet__lines" />
            {i === 2 && (
              <>
                <span className="sheet__scan" style={{ animationDelay: s.delay }} />
                {stampKind && (
                  <span className={`sheet__stamp tone-${stampKind}`} style={{ animationDelay: s.delay }}>
                    {STAMP[stampKind]}
                  </span>
                )}
              </>
            )}
          </div>
        ))}
        <div className="scene__tray" />
      </div>

      <Cajonera counts={counts} open={openDrawer} peekId={selected?.id ?? null} />

      <div className={`ficha tone-${tone}`} aria-live="polite">
        {selected ? (
          <>
            <span className="ficha__label">Carpeta abierta</span>
            <span className="ficha__id">{selected.id}</span>
            <div className="ficha__lcd">
              <div className="ficha__row">
                <span className="ficha__conf">
                  {selected.conf != null ? (
                    <>
                      {selected.conf}
                      <small>%</small>
                    </>
                  ) : (
                    "--"
                  )}
                </span>
                <span className="ficha__conflabel">confianza</span>
              </div>
              <span className="ficha__meter" aria-hidden>
                {Array.from({ length: 10 }, (_, i) => (
                  <i key={i} className={i < Math.round((selected.conf ?? 0) / 10) ? "on" : ""} />
                ))}
              </span>
            </div>
            <span className="ficha__sum">{summaryText(selected)}</span>
            <button type="button" className="ficha__open" onClick={onOpen}>
              Abrir dictamen →
            </button>
          </>
        ) : (
          <>
            <span className="ficha__label">Archivo</span>
            <span className="ficha__empty">Sin carpetas por revisar</span>
          </>
        )}
      </div>
    </section>
  );
}
