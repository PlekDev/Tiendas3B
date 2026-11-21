import { useEffect, useState } from "react";
import { motion } from "motion/react";
import type { Report } from "../types";
import { getGrafo } from "../api";
import { seconds } from "../labels";
import type { AgentRow } from "../model";
import { Collapse } from "./Bits";
import { Reveal } from "../anim";

const fmt = (ms: number) => `${ms.toLocaleString("es-MX")} ms`;

export function Trace({ report, rows }: { report: Report; rows: AgentRow[] }) {
  const [open, setOpen] = useState(false);
  const [mermaid, setMermaid] = useState<string | null>(null);
  useEffect(() => {
    if (open && mermaid === null) getGrafo().then((g) => setMermaid(g.mermaid)).catch(() => setMermaid(""));
  }, [open, mermaid]);
  const max = Math.max(1, ...rows.map((a) => a.ms));
  const heur = report.llm_mode === "heuristico";

  return (
    <Reveal className="card trace-card">
      <button className="how__head" aria-expanded={open} onClick={() => setOpen(!open)}>
        <span className="sec" style={{ gap: 2 }}>
          <span className="h2" style={{ fontSize: 20 }}>
            Cómo se decidió
          </span>
          <span className="small muted">Para auditoría: qué revisó cada agente y cuánto tardó.</span>
        </span>
        <motion.span className="chev" animate={{ rotate: open ? 180 : 0 }} transition={{ type: "spring", stiffness: 520, damping: 18 }}>
          ▾
        </motion.span>
      </button>
      <Collapse open={open}>
        <div className="how__body">
          <div className="chain">
            {rows.map((a, i) => (
              <div key={a.key} className="chain__item">
                <div className="chain__box">
                  <b style={{ fontSize: 14 }}>{a.label}</b>
                  <span className="mono" style={{ fontSize: 12, color: "var(--ink-2)" }}>
                    {fmt(a.ms)}
                  </span>
                </div>
                {i < rows.length - 1 && <span className="faint">→</span>}
              </div>
            ))}
          </div>
          <ol className="trace">
            {rows.map((a) => (
              <li key={a.key}>
                <span className="trace__check">✓</span>
                <div className="sec" style={{ gap: 6 }}>
                  <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", gap: 8 }}>
                    <span>
                      <strong>{a.label}</strong>
                      {a.desc && <span className="muted"> · {a.desc}</span>}
                    </span>
                    <span className="mono small">{fmt(a.ms)}</span>
                  </div>
                  <div className="trace__bar">
                    <div style={{ width: `${Math.max(2, (a.ms / max) * 100)}%` }} />
                  </div>
                  {a.out && <span className="small muted" style={{ overflowWrap: "anywhere" }}>{a.out}</span>}
                </div>
              </li>
            ))}
          </ol>
          <span className="small muted">
            Total <span className="mono" style={{ color: "var(--ink)" }}>{seconds(report.processing_ms)}</span> ·{" "}
            {heur
              ? "Modo sin IA: extracción con reglas y patrones."
              : `Extracción con modelo de IA (${report.llm_mode}); validación y cruces con reglas.`}
          </span>
          {mermaid && (
            <details>
              <summary className="small muted">Ver el grafo de agentes (Mermaid)</summary>
              <pre className="code">{mermaid}</pre>
            </details>
          )}
        </div>
      </Collapse>
    </Reveal>
  );
}
