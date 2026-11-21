import { useMemo, useState } from "react";
import type { Entry, Verdict } from "../types";
import { VerdictChip } from "./Bits";
import { pct, seconds } from "../labels";

const ORDER: Record<string, number> = { "Requiere revisión": 0, "No cumple": 1, Cumple: 2 };

export function Inbox({
  entries,
  onOpen,
  onNew,
  onRemove,
}: {
  entries: Entry[];
  onOpen: (id: string) => void;
  onNew: () => void;
  onRemove: (id: string) => void;
}) {
  const [filter, setFilter] = useState<Verdict | "todos">("todos");
  const [q, setQ] = useState("");

  const count = (v: Verdict) => entries.filter((e) => e.report?.recommendation === v).length;
  const done = entries.filter((e) => e.report);
  const avg = done.length
    ? done.reduce((s, e) => s + (e.report?.processing_ms ?? 0), 0) / done.length
    : 0;

  const rows = useMemo(
    () =>
      entries
        .filter((e) => filter === "todos" || e.report?.recommendation === filter)
        .filter((e) => e.id.toLowerCase().includes(q.toLowerCase()))
        .sort((a, b) => {
          const ra = a.report ? ORDER[a.report.recommendation] : -1;
          const rb = b.report ? ORDER[b.report.recommendation] : -1;
          return ra - rb || b.createdAt - a.createdAt;
        }),
    [entries, filter, q],
  );

  if (!entries.length) {
    return (
      <div className="empty">
        <h1>Sube un expediente o prueba con un ejemplo</h1>
        <p className="muted">
          El sistema revisa Escrituras, Predial, Alineamiento y Uso de Suelo, y te dice si el
          expediente sigue, se cae o necesita a una persona.
        </p>
        <button className="btn btn--primary" onClick={onNew}>
          Nuevo expediente
        </button>
      </div>
    );
  }

  return (
    <>
      <div className="row row--between">
        <h1>Bandeja</h1>
        <button className="btn btn--primary" onClick={onNew}>
          Nuevo expediente
        </button>
      </div>

      <div className="stats">
        <Stat label="Requiere revisión" n={count("Requiere revisión")} cls="warn" />
        <Stat label="No cumple" n={count("No cumple")} cls="bad" />
        <Stat label="Cumple" n={count("Cumple")} cls="ok" />
        <Stat label="En proceso" n={entries.filter((e) => e.status === "procesando").length} />
        <Stat label="Tiempo promedio" text={avg ? seconds(Math.round(avg)) : "—"} />
      </div>

      <div className="row filters">
        <label>
          <span className="sr">Buscar por ID</span>
          <input
            className="input"
            placeholder="Buscar por ID…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </label>
        {(["todos", "Requiere revisión", "No cumple", "Cumple"] as const).map((v) => (
          <button
            key={v}
            className={`btn btn--tab${filter === v ? " is-on" : ""}`}
            onClick={() => setFilter(v)}
          >
            {v === "todos" ? "Todos" : v}
          </button>
        ))}
      </div>

      <div className="table-wrap">
        <table className="table table--inbox">
          <thead>
            <tr>
              <th>Expediente</th>
              <th>Fecha</th>
              <th>Veredicto</th>
              <th>Confianza</th>
              <th>Bloqueantes</th>
              <th>Estado</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {rows.map((e) => {
              const blocking = e.report
                ? e.report.cross_validation_issues.filter((i) => i.severity === "critical").length +
                  e.report.document_analyses.flatMap((a) =>
                    a.rule_evaluations.filter((r) => !r.passed && r.severity === "critical"),
                  ).length
                : 0;
              return (
                <tr key={e.id}>
                  <th scope="row">
                    {e.report ? (
                      <button className="link" onClick={() => onOpen(e.id)}>
                        {e.id}
                      </button>
                    ) : (
                      e.id
                    )}
                  </th>
                  <td className="muted">{new Date(e.createdAt).toLocaleString("es-MX")}</td>
                  <td>{e.report ? <VerdictChip verdict={e.report.recommendation} /> : "—"}</td>
                  <td>{e.report ? pct(e.report.confidence) : "—"}</td>
                  <td>{e.report ? blocking : "—"}</td>
                  <td>
                    {e.status === "procesando" && <span className="chip chip--info">… Procesando</span>}
                    {e.status === "listo" && <span className="muted">Listo</span>}
                    {e.status === "error" && (
                      <span className="chip chip--bad" title={e.error}>
                        ✕ Error
                      </span>
                    )}
                  </td>
                  <td>
                    <button
                      className="btn btn--ghost"
                      onClick={() => onRemove(e.id)}
                      aria-label={`Quitar ${e.id}`}
                    >
                      Quitar
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </>
  );
}

function Stat({ label, n, text, cls }: { label: string; n?: number; text?: string; cls?: string }) {
  return (
    <div className={`stat${cls ? ` stat--${cls}` : ""}`}>
      <div className="stat__n">{text ?? n}</div>
      <div className="muted small">{label}</div>
    </div>
  );
}
