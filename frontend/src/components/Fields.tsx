import type { DocumentAnalysis, Evidence } from "../types";
import { DOC_LABEL, DOUBT_THRESHOLD, fieldLabel, pct } from "../labels";

export function Fields({
  analyses,
  onEvidence,
}: {
  analyses: DocumentAnalysis[];
  onEvidence: (e: Evidence) => void;
}) {
  return (
    <>
      {analyses.map((a) => (
        <div key={a.document_name} className="fields">
          <h3>
            {DOC_LABEL[a.document_type]} <span className="muted">· {a.document_name}</span>
          </h3>
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Campo</th>
                  <th>Valor</th>
                  <th>Pág.</th>
                  <th>Confianza</th>
                  <th>Cómo se obtuvo</th>
                </tr>
              </thead>
              <tbody>
                {a.extracted_fields.map((f) => {
                  const doubt = f.confidence < DOUBT_THRESHOLD;
                  return (
                    <tr key={f.name} className={doubt ? "row--doubt" : ""}>
                      <th scope="row">{fieldLabel(f.name)}</th>
                      <td>
                        {f.value ? (
                          f.evidence ? (
                            <button className="link" onClick={() => onEvidence(f.evidence!)}>
                              {f.value}
                            </button>
                          ) : (
                            f.value
                          )
                        ) : (
                          <span className="muted">No encontrado</span>
                        )}
                        {doubt && f.value && <span className="chip chip--doubt"> ? Dato en duda</span>}
                      </td>
                      <td>{f.evidence?.page ?? "—"}</td>
                      <td>
                        <span className="bar" aria-hidden>
                          <span style={{ width: pct(f.confidence) }} />
                        </span>{" "}
                        {pct(f.confidence)}
                      </td>
                      <td className="muted">
                        {f.method === "llm"
                          ? "Modelo de IA"
                          : f.method === "heuristica"
                            ? "Reglas y patrones"
                            : f.method || "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {a.missing_fields.length > 0 && (
            <p className="small">
              <strong>No se encontró:</strong> {a.missing_fields.map(fieldLabel).join(", ")}.
            </p>
          )}
        </div>
      ))}
    </>
  );
}
