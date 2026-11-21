import type { DocType, DocumentAnalysis, Evidence, Report } from "../types";
import { CROSS_ROWS, DOC_ORDER, DOC_SHORT, fieldLabel } from "../labels";
import { SeverityChip } from "./Bits";

function valueOf(a: DocumentAnalysis | undefined, field: string | undefined) {
  if (!a || !field) return undefined;
  return a.extracted_fields.find((f) => f.name === field && (f.value ?? "").trim());
}

/** Una fila por cruce, una columna por documento (los 5 cruces de CROSS_CHECKS). */
export function Compare({
  report,
  onEvidence,
}: {
  report: Report;
  onEvidence: (e: Evidence) => void;
}) {
  const byType = new Map<DocType, DocumentAnalysis>();
  report.document_analyses.forEach((a) => {
    if (!byType.has(a.document_type)) byType.set(a.document_type, a);
  });

  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>
            <th>Dato</th>
            {DOC_ORDER.map((t) => (
              <th key={t}>{DOC_SHORT[t]}</th>
            ))}
            <th>Resultado</th>
          </tr>
        </thead>
        <tbody>
          {CROSS_ROWS.map((row) => {
            const issue = report.cross_validation_issues.find((i) => i.field_name === row.key);
            const found = DOC_ORDER.filter((t) => valueOf(byType.get(t), row.fields[t]));
            return (
              <tr key={row.key} className={issue ? "row--flag" : ""}>
                <th scope="row">{row.label}</th>
                {DOC_ORDER.map((t) => {
                  const f = valueOf(byType.get(t), row.fields[t]);
                  if (!row.fields[t]) return <td key={t} className="muted">—</td>;
                  if (!f) return <td key={t} className="muted">No encontrado</td>;
                  return (
                    <td key={t}>
                      {f.evidence ? (
                        <button
                          className="link"
                          onClick={() => onEvidence(f.evidence!)}
                          title="Ver en el documento"
                        >
                          {f.value}
                        </button>
                      ) : (
                        f.value
                      )}
                    </td>
                  );
                })}
                <td>
                  {issue ? (
                    <>
                      <SeverityChip severity={issue.severity} />
                      <div className="small">{issue.description}</div>
                    </>
                  ) : found.length >= 2 ? (
                    <span className="chip chip--ok">✓ Coincide</span>
                  ) : (
                    <span className="muted small">
                      Sin datos suficientes para comparar ({fieldLabel(row.key)})
                    </span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
