import { useMemo, useState } from "react";
import { motion } from "motion/react";
import type { Entry, Verdict } from "../types";
import { Chip, CountUp, Dot } from "./Bits";
import { VERDICT_UI, seconds, type Tone } from "../labels";

type Filter = "todos" | "warn" | "bad" | "ok" | "proc";
const RANK: Record<string, number> = { "No cumple": 1, "Requiere revisión": 2, Cumple: 3 };
const TONE_VERDICT: Record<"warn" | "bad" | "ok", Verdict> = {
  warn: "Requiere revisión",
  bad: "No cumple",
  ok: "Cumple",
};

function blocking(e: Entry): number {
  if (!e.report) return 0;
  return (
    e.report.cross_validation_issues.filter((i) => i.severity === "critical").length +
    e.report.document_analyses.flatMap((a) =>
      a.rule_evaluations.filter((r) => !r.passed && r.severity === "critical"),
    ).length
  );
}

export function Inbox({
  entries,
  onOpen,
  onNew,
  onExample,
}: {
  entries: Entry[];
  onOpen: (e: Entry) => void;
  onNew: () => void;
  onExample: () => void;
}) {
  const [filter, setFilter] = useState<Filter>("todos");
  const [q, setQ] = useState("");

  const count = (v: Verdict) => entries.filter((e) => e.report?.recommendation === v).length;
  const proc = entries.filter((e) => e.status === "procesando").length;
  const done = entries.filter((e) => e.report);
  const avg = done.length
    ? done.reduce((s, e) => s + (e.report?.processing_ms ?? 0), 0) / done.length
    : 0;

  const rows = useMemo(
    () =>
      entries
        .filter((e) => {
          if (filter === "todos") return true;
          if (filter === "proc") return e.status === "procesando";
          return e.report?.recommendation === TONE_VERDICT[filter];
        })
        .filter((e) => e.id.toLowerCase().includes(q.trim().toLowerCase()))
        // Primero lo que necesita a una persona: errores, no cumple, revisión, cumple.
        .sort((a, b) => {
          const ra = a.report ? RANK[a.report.recommendation] : a.status === "error" ? 0 : 1.5;
          const rb = b.report ? RANK[b.report.recommendation] : b.status === "error" ? 0 : 1.5;
          return ra - rb || b.createdAt - a.createdAt;
        }),
    [entries, filter, q],
  );

  const counters: { label: string; n?: number; text?: string; tone: Tone; icon?: string; f?: Filter }[] = [
    { label: "Requiere revisión", n: count("Requiere revisión"), tone: "warn", f: "warn" },
    { label: "No cumple", n: count("No cumple"), tone: "bad", f: "bad" },
    { label: "Cumple", n: count("Cumple"), tone: "ok", f: "ok" },
    { label: "En proceso", n: proc, tone: "info", icon: "…", f: "proc" },
    { label: "Tiempo promedio", text: avg ? seconds(Math.round(avg)) : "—", tone: "na", icon: "·" },
  ];
  const pills: [Filter, string][] = [
    ["todos", "Todos"],
    ["warn", "Requiere revisión"],
    ["bad", "No cumple"],
    ["ok", "Cumple"],
    ["proc", "En proceso"],
  ];

  return (
    <main className="page" data-screen-label="Bandeja">
      <div className="page-head">
        <div>
          <h1 className="h1">Expedientes</h1>
          <p className="muted" style={{ marginTop: 6 }}>
            Primero lo que necesita a una persona.
          </p>
        </div>
        <button className="btn btn--primary" onClick={onNew}>
          <span style={{ fontSize: 18, lineHeight: 1 }}>+</span>Nuevo expediente
        </button>
      </div>

      <div className="counters">
        {counters.map((c) => (
          <button
            key={c.label}
            className={`counter${c.f && filter === c.f ? " is-on" : ""}`}
            disabled={!c.f}
            aria-pressed={c.f ? filter === c.f : undefined}
            onClick={() => c.f && setFilter(filter === c.f ? "todos" : c.f)}
          >
            <span className="counter__label">
              <Dot tone={c.tone} icon={c.icon} />
              {c.label}
            </span>
            <span className="counter__n">{c.text ?? <CountUp value={c.n ?? 0} />}</span>
          </button>
        ))}
      </div>

      {!entries.length ? (
        <div className="empty">
          <div className="h2" style={{ fontSize: 24 }}>
            Sube un expediente o prueba con un ejemplo
          </div>
          <p className="muted pretty">
            Revisamos Escrituras, Predial, Alineamiento y Número Oficial y Uso de Suelo, y te
            decimos si el inmueble sigue, con la prueba de cada dato.
          </p>
          <div className="chips" style={{ justifyContent: "center" }}>
            <button className="btn btn--primary" onClick={onNew}>
              Subir expediente
            </button>
            <button className="btn" style={{ height: 42, padding: "0 18px", fontSize: 14 }} onClick={onExample}>
              Probar con un ejemplo
            </button>
          </div>
        </div>
      ) : (
        <div className="sec" style={{ gap: 12 }}>
          <div className="toolbar">
            <div className="pills" role="group" aria-label="Filtrar">
              {pills.map(([k, label]) => (
                <button
                  key={k}
                  className={`pill${filter === k ? " is-on" : ""}`}
                  aria-pressed={filter === k}
                  onClick={() => setFilter(k)}
                >
                  {label}
                </button>
              ))}
            </div>
            <input
              className="input input--search"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Buscar por ID"
              aria-label="Buscar por ID"
            />
          </div>

          <div className="card inbox">
            <div className="inbox__head" aria-hidden>
              <span>ID</span>
              <span>Fecha</span>
              <span>Veredicto</span>
              <span>Confianza</span>
              <span>Bloqueantes</span>
              <span>Estado</span>
            </div>
            {rows.map((e, i) => {
              const r = e.report;
              const conf = r ? Math.round(r.confidence * 100) : null;
              const doubt = conf != null && conf < 60;
              const b = blocking(e);
              const st =
                e.status === "procesando"
                  ? { tone: "info" as Tone, icon: "…", label: "Procesando", note: "Analizando en el servidor" }
                  : e.status === "error"
                    ? { tone: "bad" as Tone, icon: "✕", label: "Error", note: e.error }
                    : { tone: "na" as Tone, icon: "✓", label: "Listo", note: undefined };
              return (
                <motion.button
                  key={e.id}
                  className="inbox__row"
                  onClick={() => onOpen(e)}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: Math.min(i, 8) * 0.03, duration: 0.2 }}
                >
                  <span className="mono inbox__id" style={{ fontSize: 13, fontWeight: 500 }}>
                    {e.id}
                  </span>
                  <span className="muted">
                    {new Date(e.createdAt).toLocaleDateString("es-MX", { day: "numeric", month: "short", year: "numeric" })}
                  </span>
                  <span className={r ? "" : "inbox__cell--empty"}>
                    {r ? (
                      <Chip tone={VERDICT_UI[r.recommendation].cls}>{r.recommendation}</Chip>
                    ) : (
                      <span className="faint">—</span>
                    )}
                  </span>
                  <span className={`conf${conf == null ? " inbox__cell--empty" : ""}`}>
                    {conf != null ? (
                      <>
                        <span className="inbox__label">Confianza</span>
                        <span className={`bar${doubt ? " bar--doubt" : ""}`}>
                          <span style={{ width: `${conf}%` }} />
                        </span>
                        <span className="num" style={{ fontWeight: 600 }}>
                          {conf} %{doubt ? " ?" : ""}
                        </span>
                      </>
                    ) : (
                      <span className="faint">—</span>
                    )}
                  </span>
                  <span
                    className={`num${r ? "" : " inbox__cell--empty"}`}
                    style={{ fontWeight: 600, color: b ? "var(--bad)" : "var(--ink-3)" }}
                  >
                    <span className="inbox__label">Bloqueantes </span>
                    {r ? b : "—"}
                  </span>
                  <span className={`state t-${st.tone}`}>
                    <span className="state__main">
                      <Dot tone={st.tone} icon={st.icon} ring />
                      {st.label}
                    </span>
                    {st.note && <span className="small faint">{st.note}</span>}
                  </span>
                </motion.button>
              );
            })}
            {!rows.length && (
              <div className="muted" style={{ padding: 32, textAlign: "center" }}>
                No hay expedientes con ese filtro o ID.
              </div>
            )}
          </div>
        </div>
      )}
    </main>
  );
}
