import { DOC_ORDER, DOC_SHORT } from "../labels";
import type { CompRow, EvTarget } from "../model";
import { Chip } from "./Bits";

/** Una fila por cruce (CROSS_CHECKS), una columna por documento. */
export function Compare({ rows, onEvidence }: { rows: CompRow[]; onEvidence: (t: EvTarget) => void }) {
  return (
    <section className="sec">
      <div className="sec__head">
        <h2 className="h2">Comparación entre documentos</h2>
        <span className="small muted">Toca cualquier valor para ver dónde aparece en el documento.</span>
      </div>
      <div className="card scroll">
        <table className="tbl tbl--comp">
          <thead>
            <tr>
              <th style={{ width: "15%" }}>Dato</th>
              {DOC_ORDER.map((t) => (
                <th key={t}>{DOC_SHORT[t]}</th>
              ))}
              <th style={{ width: "14%" }}>Resultado</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.key} className={r.tone === "warn" ? "row-warn" : r.tone === "bad" ? "row-bad" : ""}>
                <td style={{ fontWeight: 600, padding: "12px 14px" }}>{r.label}</td>
                {r.cells.map((c, i) => (
                  <td key={i} className="cellwrap">
                    <button
                      className={`cmp cmp--${c.kind}${c.kind === "dev" ? ` t-${r.tone}` : ""}`}
                      disabled={!c.target}
                      onClick={() => c.target && onEvidence(c.target)}
                      title={c.target ? "Ver en el documento" : undefined}
                    >
                      {c.kind === "dev" ? `${r.tone === "bad" ? "✕" : "!"} ${c.label}` : c.label}
                    </button>
                  </td>
                ))}
                <td>
                  {r.tone === "na" ? (
                    <span className="small faint">{r.result}</span>
                  ) : (
                    <Chip tone={r.tone}>{r.result}</Chip>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
