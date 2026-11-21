import { useState } from "react";
import { motion } from "motion/react";
import { Reveal } from "../anim";
import { TONE_ICON } from "../labels";
import { MATRIX_COLS, type MatrixCell } from "../model";

/** Documento × regla: cada celda agrupa las reglas de ese tema en ese documento. */
export function Matrix({ rows }: { rows: { doc: string; cells: MatrixCell[] }[] }) {
  const [sel, setSel] = useState<{ key: string; text: string } | null>(null);
  return (
    <Reveal className="sec">
      <div className="sec__head">
        <h2 className="h2">Documento × regla</h2>
        <span className="small muted">Cada celda es un tema revisado en un documento.</span>
      </div>
      <div className="card scroll matrix">
        <div className="matrix__grid">
          <div className="matrix__row matrix__row--head">
            <span />
            {MATRIX_COLS.map((c) => (
              <span key={c.key}>{c.label}</span>
            ))}
          </div>
          {rows.map((r, i) => (
            <div key={r.doc} className="matrix__row">
              <span className="small" style={{ fontWeight: 600 }}>
                {r.doc}
              </span>
              {r.cells.map((c, j) => {
                const key = `${i}-${j}`;
                const text = `${r.doc} × ${MATRIX_COLS[j].label}: ${c.detail}`;
                const show = () => setSel({ key, text });
                return (
                  <motion.button
                    key={key}
                    initial={{ opacity: 0, scale: 0.4 }}
                    whileInView={{ opacity: 1, scale: 1 }}
                    viewport={{ once: true }}
                    transition={{ type: "spring", stiffness: 500, damping: 20, delay: (i * 7 + j) * 0.02 }}
                    whileHover={{ scale: 1.12, zIndex: 1 }}
                    whileTap={{ scale: 0.9 }}
                    className={`mcell t-${c.tone}${sel?.key === key ? " is-on" : ""}`}
                    aria-label={text}
                    title={text}
                    onMouseEnter={show}
                    onFocus={show}
                    onClick={show}
                  >
                    {TONE_ICON[c.tone]}
                  </motion.button>
                );
              })}
            </div>
          ))}
          <div className="matrix__detail" aria-live="polite">
            {sel?.text ?? "Pasa el cursor o toca una celda para ver la regla y su detalle."}
          </div>
        </div>
      </div>
    </Reveal>
  );
}
