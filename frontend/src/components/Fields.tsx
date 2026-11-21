import { methodLabel } from "../labels";
import { Reveal } from "../anim";
import type { EvTarget, FieldRow } from "../model";

export function Fields({ rows, onEvidence }: { rows: FieldRow[]; onEvidence: (t: EvTarget) => void }) {
  return (
    <Reveal className="sec">
      <div className="sec__head">
        <h2 className="h2">Datos extraídos</h2>
        <span className="small muted">Los datos con menos de 60 % de seguridad se marcan como en duda.</span>
      </div>
      <div className="mcards only-narrow-flex">
        {rows.map((f) => {
          const pct = Math.round(f.conf * 100);
          return (
            <button
              key={f.key}
              className={`mcard mcard--field${f.doubt ? " mcard--doubt" : ""}`}
              disabled={!f.target}
              onClick={() => f.target && onEvidence(f.target)}
            >
              <span className="mcard__head">
                <b>{f.campo}</b>
                <span className="num small" style={{ fontWeight: 600 }}>
                  {pct} %{f.doubt ? " · en duda" : ""}
                </span>
              </span>
              <span className="mcard__val">{f.valor ? (f.doubt ? `? ${f.valor}` : f.valor) : "No encontrado"}</span>
              <span className="bar bar--full">
                <span style={{ width: `${pct}%`, background: f.doubt ? "var(--warn)" : "var(--ink-3)" }} />
              </span>
              <span className="mono small faint">
                {f.src} · {methodLabel(f.method)}
              </span>
            </button>
          );
        })}
      </div>
      <div className="card scroll only-wide-block">
        <table className="tbl tbl--fields">
          <thead>
            <tr>
              <th>Campo</th>
              <th>Valor</th>
              <th>Documento · pág.</th>
              <th>Confianza</th>
              <th>Cómo se obtuvo</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((f) => {
              const pct = Math.round(f.conf * 100);
              return (
                <tr
                  key={f.key}
                  className={`${f.doubt ? "row-doubt " : ""}${f.target ? "clickable" : ""}`}
                  onClick={() => f.target && onEvidence(f.target)}
                >
                  <td style={{ fontWeight: 600 }}>{f.campo}</td>
                  <td>
                    {f.valor ? (
                      f.target ? (
                        <button
                          className="linkbtn"
                          style={{ color: "var(--ink)", fontWeight: 400, whiteSpace: "normal", textAlign: "left" }}
                          onClick={(e) => {
                            e.stopPropagation();
                            onEvidence(f.target!);
                          }}
                        >
                          {f.doubt ? `? ${f.valor}` : f.valor}
                        </button>
                      ) : (
                        f.valor
                      )
                    ) : (
                      <span className="faint">No encontrado</span>
                    )}
                  </td>
                  <td className="mono" style={{ fontSize: 12, color: "var(--ink-2)" }}>
                    {f.src}
                  </td>
                  <td>
                    <span className="conf">
                      <span className="bar bar--wide">
                        <span style={{ width: `${pct}%`, background: f.doubt ? "var(--warn)" : "var(--ink-3)" }} />
                      </span>
                      <span className="num small" style={{ fontWeight: 600 }}>
                        {pct} %{f.doubt ? " · en duda" : ""}
                      </span>
                    </span>
                  </td>
                  <td className="small muted">{methodLabel(f.method)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Reveal>
  );
}
