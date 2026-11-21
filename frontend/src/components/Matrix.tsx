import type { Report } from "../types";
import { DOC_SHORT } from "../labels";

/** Matriz documento × regla (adaptación de ComplianceHeatmap). */
export function Matrix({ report }: { report: Report }) {
  const rules = [
    ...new Map(
      report.document_analyses.flatMap((a) => a.rule_evaluations).map((r) => [r.rule_id, r]),
    ).values(),
  ];
  if (!rules.length) return <p className="muted">No hay reglas evaluadas.</p>;
  return (
    <div className="table-wrap">
      <table className="table matrix">
        <thead>
          <tr>
            <th>Documento</th>
            {rules.map((r) => (
              <th key={r.rule_id} title={r.description}>
                {r.rule_id}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {report.document_analyses.map((a) => (
            <tr key={a.document_name}>
              <th scope="row">
                {DOC_SHORT[a.document_type]}
                <div className="muted small">{a.document_name}</div>
              </th>
              {rules.map((r) => {
                const ev = a.rule_evaluations.find((x) => x.rule_id === r.rule_id);
                if (!ev)
                  return (
                    <td key={r.rule_id} className="cell cell--na" title="No aplica">
                      –
                    </td>
                  );
                const cls = ev.passed ? "ok" : ev.severity === "critical" ? "bad" : "warn";
                const label = ev.passed ? "Cumple" : ev.severity === "critical" ? "Bloqueante" : "Revisar";
                return (
                  <td
                    key={r.rule_id}
                    className={`cell cell--${cls}`}
                    title={`${ev.description}\n${ev.details}`}
                  >
                    <span aria-hidden>{ev.passed ? "✓" : ev.severity === "critical" ? "✕" : "!"}</span>
                    <span className="sr">{label}</span>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="muted small">Pasa el cursor sobre una celda para ver la regla y el detalle.</p>
    </div>
  );
}
