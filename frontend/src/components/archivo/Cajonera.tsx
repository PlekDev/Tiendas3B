import { KIND_VERDICT, type VerdictKind } from "./data";

const DRAWERS: { kind: VerdictKind; label: string }[] = [
  { kind: "warn", label: "Revisión" },
  { kind: "bad", label: "No cumple" },
  { kind: "ok", label: "Cumple" },
];

/**
 * Cajonera metálica de 3 cajones. El del veredicto seleccionado se abre y asoma la carpeta.
 * Es decorativa: los conteos y el expediente seleccionado ya están en los KPI y en la ficha.
 */
export function Cajonera({
  counts,
  open,
  peekId,
}: {
  counts: Record<VerdictKind, number>;
  open: VerdictKind | null;
  peekId: string | null;
}) {
  return (
    <div className="cajonera" aria-hidden>
      {DRAWERS.map(({ kind, label }) => {
        const isOpen = open === kind;
        return (
          <div key={kind} className={`drawer tone-${kind}${isOpen ? " is-open" : ""}`} title={KIND_VERDICT[kind]}>
            <div className="drawer__peek">
              <span className="drawer__peektab">{isOpen ? peekId : ""}</span>
            </div>
            <div className="drawer__face">
              <span className="drawer__dot" />
              <span className="drawer__label">
                <b>{label}</b>
                <span>{counts[kind]} exp.</span>
              </span>
              <span className="drawer__handle" />
            </div>
          </div>
        );
      })}
    </div>
  );
}
