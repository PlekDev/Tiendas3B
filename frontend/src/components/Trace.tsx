import { useEffect, useState } from "react";
import type { Report } from "../types";
import { getGrafo } from "../api";
import { seconds } from "../labels";

export function Trace({ report }: { report: Report }) {
  const [mermaid, setMermaid] = useState<string | null>(null);
  useEffect(() => {
    getGrafo()
      .then((g) => setMermaid(g.mermaid))
      .catch(() => setMermaid(null));
  }, []);
  const max = Math.max(1, ...report.trace.map((s) => s.ms));
  return (
    <>
      <p className="muted small">
        Cada agente es un paso del grafo. Total: {seconds(report.processing_ms)} ·{" "}
        {report.llm_mode === "heuristico"
          ? "Modo sin IA (reglas y patrones)"
          : `Modelo: ${report.llm_mode}`}
      </p>
      <ol className="trace">
        {report.trace.map((s, i) => (
          <li key={i}>
            <div className="trace__row">
              <strong>{s.agent}</strong>
              <span className="muted">{seconds(s.ms)}</span>
            </div>
            <span className="bar bar--wide" aria-hidden>
              <span style={{ width: `${(s.ms / max) * 100}%` }} />
            </span>
            {s.detail && <div className="small muted">{s.detail}</div>}
          </li>
        ))}
      </ol>
      {mermaid && (
        <details>
          <summary className="muted small">Ver el diagrama del grafo (Mermaid)</summary>
          <pre className="code">{mermaid}</pre>
        </details>
      )}
    </>
  );
}
