import { useMemo, useState } from "react";
import { AnimatePresence, LayoutGroup, motion } from "motion/react";
import { CircleAlert, CircleCheck, CircleX, LoaderCircle, Plus, Search, Timer, type LucideIcon } from "lucide-react";
import type { Entry, Verdict } from "../types";
import { Chip, CountUp, Dot } from "./Bits";
import { VERDICT_UI, seconds, type Tone } from "../labels";
import { fadeUp, press, spring, stagger } from "../anim";

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

  const counters: { label: string; n?: number; text?: string; tone: Tone; Icon: LucideIcon; f?: Filter; spin?: boolean }[] = [
    { label: "Requiere revisión", n: count("Requiere revisión"), tone: "warn", Icon: CircleAlert, f: "warn" },
    { label: "No cumple", n: count("No cumple"), tone: "bad", Icon: CircleX, f: "bad" },
    { label: "Cumple", n: count("Cumple"), tone: "ok", Icon: CircleCheck, f: "ok" },
    { label: "En proceso", n: proc, tone: "info", Icon: LoaderCircle, f: "proc", spin: proc > 0 },
    { label: "Tiempo promedio", text: avg ? seconds(Math.round(avg)) : "—", tone: "na", Icon: Timer },
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
      <motion.div className="page-head" variants={stagger(0.06)} initial="hidden" animate="show">
        <motion.div variants={fadeUp}>
          <h1 className="h1">Expedientes</h1>
          <p className="muted" style={{ marginTop: 6 }}>
            Primero lo que necesita a una persona.
          </p>
        </motion.div>
        <motion.button variants={fadeUp} className="btn btn--primary btn--cta" onClick={onNew} {...press}>
          <Plus size={20} strokeWidth={2.6} aria-hidden />
          Nuevo expediente
        </motion.button>
      </motion.div>

      <motion.div className="counters" variants={stagger(0.06, 0.08)} initial="hidden" animate="show">
        {counters.map((c) => {
          const on = !!c.f && filter === c.f;
          return (
            <motion.button
              key={c.label}
              variants={fadeUp}
              className={`counter t-${c.tone}${on ? " is-on" : ""}${c.f ? "" : " counter--static"}`}
              disabled={!c.f}
              aria-pressed={c.f ? on : undefined}
              onClick={() => c.f && setFilter(on ? "todos" : c.f)}
              whileHover={c.f ? { y: -4, transition: spring } : undefined}
              whileTap={c.f ? { scale: 0.96 } : undefined}
            >
              <span className="counter__label">
                <motion.span
                  className="counter__icon"
                  animate={c.spin ? { rotate: 360 } : { rotate: 0 }}
                  transition={c.spin ? { repeat: Infinity, duration: 1.2, ease: "linear" } : spring}
                >
                  <c.Icon size={22} strokeWidth={2.3} aria-hidden />
                </motion.span>
                {c.label}
              </span>
              <span className="counter__n">{c.text ?? <CountUp value={c.n ?? 0} />}</span>
              {on && <motion.span className="counter__bar" layoutId="counter-bar" transition={spring} />}
            </motion.button>
          );
        })}
      </motion.div>

      {!entries.length ? (
        <motion.div className="empty" initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }} transition={{ ...spring, delay: 0.2 }}>
          <motion.div
            className="empty__art"
            aria-hidden
            animate={{ y: [0, -8, 0] }}
            transition={{ repeat: Infinity, duration: 3, ease: "easeInOut" }}
          >
            <span className="brand__mark brand__mark--xl">
              <span>B</span>
              <span>BB</span>
            </span>
          </motion.div>
          <div className="h2" style={{ fontSize: 26 }}>
            Sube un expediente o prueba con un ejemplo
          </div>
          <p className="muted pretty">
            Revisamos Escrituras, Predial, Alineamiento y Número Oficial y Uso de Suelo, y te
            decimos si el inmueble sigue, con la prueba de cada dato.
          </p>
          <div className="chips" style={{ justifyContent: "center" }}>
            <motion.button className="btn btn--primary btn--cta" onClick={onNew} {...press}>
              Subir expediente
            </motion.button>
            <motion.button className="btn btn--cta btn--ghostcta" onClick={onExample} {...press}>
              Probar con un ejemplo
            </motion.button>
          </div>
        </motion.div>
      ) : (
        <motion.div className="sec" style={{ gap: 12 }} variants={fadeUp} initial="hidden" animate="show" transition={{ delay: 0.15 }}>
          <div className="toolbar">
            <LayoutGroup id="pills">
              <div className="pills" role="group" aria-label="Filtrar">
                {pills.map(([k, label]) => (
                  <motion.button
                    key={k}
                    className={`pill${filter === k ? " is-on" : ""}`}
                    aria-pressed={filter === k}
                    onClick={() => setFilter(k)}
                    whileTap={{ scale: 0.94 }}
                  >
                    {filter === k && <motion.span className="pill__bg" layoutId="pill-bg" transition={spring} />}
                    <span className="pill__label">{label}</span>
                  </motion.button>
                ))}
              </div>
            </LayoutGroup>
            <label className="search">
              <Search size={18} aria-hidden />
              <input
                className="input input--search"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Buscar por ID"
                aria-label="Buscar por ID"
              />
            </label>
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
            <AnimatePresence initial={true} mode="popLayout">
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
                    layout
                    className={`inbox__row${r ? ` inbox__row--${VERDICT_UI[r.recommendation].cls}` : ""}`}
                    onClick={() => onOpen(e)}
                    initial={{ opacity: 0, x: -24 }}
                    animate={{ opacity: 1, x: 0, transition: { ...spring, delay: Math.min(i, 10) * 0.04 } }}
                    exit={{ opacity: 0, x: 24, transition: { duration: 0.15 } }}
                    whileHover={{ x: 4 }}
                    whileTap={{ scale: 0.99 }}
                  >
                    <span className="mono inbox__id">{e.id}</span>
                    <span className="muted inbox__date">
                      {new Date(e.createdAt).toLocaleDateString("es-MX", { day: "numeric", month: "short", year: "numeric" })}
                    </span>
                    <span className={r ? "inbox__verdict" : "inbox__cell--empty"}>
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
                            <motion.span
                              initial={{ width: 0 }}
                              animate={{ width: `${conf}%` }}
                              transition={{ ...spring, delay: 0.2 + Math.min(i, 10) * 0.04 }}
                            />
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
            </AnimatePresence>
            {!rows.length && (
              <motion.div className="muted" style={{ padding: 32, textAlign: "center" }} initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                No hay expedientes con ese filtro o ID.
              </motion.div>
            )}
          </div>
        </motion.div>
      )}
    </main>
  );
}
