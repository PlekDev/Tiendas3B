import { useMemo, useState } from "react";
import { CalendarDays, Plus, Search, X } from "lucide-react";
import type { Entry } from "../types";
import { CountUp } from "./Bits";
import { seconds } from "../labels";
import { ArchivoVivo } from "./archivo/ArchivoVivo";
import { CarpetaExpediente } from "./archivo/CarpetaExpediente";
import { KpiCajon } from "./archivo/KpiCajon";
import {
  FILTER_TITLE,
  KIND_VERDICT,
  sortCarpetas,
  toCarpeta,
  type Filter,
  type VerdictKind,
} from "./archivo/data";

type Quick = "hoy" | "ayer" | "7d";
const QUICK_LABEL: Record<Quick, string> = { hoy: "Hoy", ayer: "Ayer", "7d": "Últimos 7 días" };

/** yyyy-mm-dd en hora local (lo que entrega <input type="date">). */
function dayKey(ms: number): string {
  const d = new Date(ms);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}
function quickRange(q: Quick): [string, string] {
  const day = 86_400_000;
  const now = Date.now();
  if (q === "hoy") return [dayKey(now), dayKey(now)];
  if (q === "ayer") return [dayKey(now - day), dayKey(now - day)];
  return [dayKey(now - 6 * day), dayKey(now)];
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
  const [from, setFrom] = useState(""); // yyyy-mm-dd, vacío = sin límite
  const [to, setTo] = useState("");
  const [selId, setSelId] = useState<string | null>(null);

  const carpetas = useMemo(() => entries.map(toCarpeta), [entries]);
  const byId = useMemo(() => new Map(entries.map((e) => [e.id, e])), [entries]);

  const counts: Record<VerdictKind, number> = {
    warn: carpetas.filter((c) => c.kind === "warn").length,
    bad: carpetas.filter((c) => c.kind === "bad").length,
    ok: carpetas.filter((c) => c.kind === "ok").length,
  };
  const proc = carpetas.filter((c) => c.kind === "proc").length;
  const done = entries.filter((e) => e.report);
  const avg = done.length ? done.reduce((s, e) => s + (e.report?.processing_ms ?? 0), 0) / done.length : 0;

  const rows = useMemo(
    () =>
      carpetas
        .filter((c) => filter === "todos" || c.kind === filter)
        .filter((c) => c.id.toLowerCase().includes(q.trim().toLowerCase()))
        .filter((c) => {
          const day = dayKey(c.createdAt); // yyyy-mm-dd compara bien como texto
          return (!from || day >= from) && (!to || day <= to);
        })
        .sort(sortCarpetas),
    [carpetas, filter, q, from, to],
  );
  const dateOn = !!(from || to);
  const activeQuick = (Object.keys(QUICK_LABEL) as Quick[]).find((k) => {
    const [f, t] = quickRange(k);
    return f === from && t === to;
  });
  const pickQuick = (k: Quick) => {
    const [f, t] = activeQuick === k ? ["", ""] : quickRange(k);
    setFrom(f);
    setTo(t);
  };
  const clearAll = () => {
    setQ("");
    setFrom("");
    setTo("");
    setFilter("todos");
  };

  // Si lo seleccionado ya no está en la lista (filtro, búsqueda, quitado), se muestra la primera carpeta.
  const selected = rows.find((c) => c.id === selId) ?? rows[0] ?? null;
  const open = (id: string) => {
    const e = byId.get(id);
    if (e) onOpen(e);
  };

  const toggle = (f: Filter) => setFilter((cur) => (cur === f ? "todos" : f));
  const today = new Date()
    .toLocaleDateString("es-MX", { day: "numeric", month: "short", year: "numeric" })
    .replace(/\./g, "");
  const n = entries.length;

  return (
    <main className="archivo" data-screen-label="Bandeja">
      <aside className="archivo__side">
        <ArchivoVivo
          selected={selected}
          counts={counts}
          processing={proc}
          onOpen={() => selected && open(selected.id)}
        />
      </aside>

      <div className="archivo__main">
        <div className="ahead">
          <div>
            <p className="ahead__meta">
              {today} · {n} {n === 1 ? "expediente" : "expedientes"}
            </p>
            <h1 className="ahead__h1">Expedientes</h1>
            <p className="ahead__sub">Primero lo que necesita a una persona.</p>
          </div>
          <button type="button" className="ar-new" onClick={onNew}>
            <Plus size={20} strokeWidth={2.6} aria-hidden />
            Nuevo expediente
          </button>
        </div>

        <div className="kpis" role="group" aria-label="Filtrar por cajón">
          <KpiCajon label="Requiere revisión" tone="warn" value={<CountUp value={counts.warn} />} pressed={filter === "warn"} onClick={() => toggle("warn")} />
          <KpiCajon label="No cumple" tone="bad" value={<CountUp value={counts.bad} />} pressed={filter === "bad"} onClick={() => toggle("bad")} />
          <KpiCajon label="Cumple" tone="ok" value={<CountUp value={counts.ok} />} pressed={filter === "ok"} onClick={() => toggle("ok")} />
          <KpiCajon label="En proceso" tone="proc" value={<CountUp value={proc} />} pressed={filter === "proc"} onClick={() => toggle("proc")} />
          <KpiCajon label="Tiempo promedio" tone="na" value={avg ? seconds(Math.round(avg)) : "—"} />
        </div>

        {!n ? (
          <div className="ar-empty">
            <span className="ar-empty__icon" aria-hidden>
              <i />
            </span>
            <h2 className="ar-empty__t">Sin carpetas por revisar</h2>
            <p>
              Revisamos Escrituras, Predial, Alineamiento y Número Oficial y Uso de Suelo, y te decimos si el
              inmueble sigue, con la prueba de cada dato.
            </p>
            <div className="ar-empty__btns">
              <button type="button" className="ar-new" onClick={onNew}>
                Subir expediente
              </button>
              <button type="button" className="ar-ghost" onClick={onExample}>
                Probar con un ejemplo
              </button>
            </div>
          </div>
        ) : (
          <>
            <div className="atool">
              <h2 className="atool__t">
                {FILTER_TITLE[filter]} <span className="atool__n">· {rows.length}</span>
              </h2>
              <label className="asearch">
                <Search size={18} aria-hidden />
                <input
                  value={q}
                  onChange={(e) => setQ(e.target.value)}
                  placeholder="Buscar por ID"
                  aria-label="Buscar por ID"
                />
                {q && (
                  <button type="button" className="asearch__x" onClick={() => setQ("")} aria-label="Borrar búsqueda">
                    <X size={16} aria-hidden />
                  </button>
                )}
              </label>
            </div>

            <div className="adate" role="group" aria-label="Filtrar por fecha de creación">
              <span className="adate__l">
                <CalendarDays size={17} aria-hidden /> Creado
              </span>
              {(Object.keys(QUICK_LABEL) as Quick[]).map((k) => (
                <button
                  key={k}
                  type="button"
                  className="adate__chip"
                  aria-pressed={activeQuick === k}
                  onClick={() => pickQuick(k)}
                >
                  {QUICK_LABEL[k]}
                </button>
              ))}
              <label className="adate__f">
                Desde
                <input type="date" value={from} max={to || undefined} onChange={(e) => setFrom(e.target.value)} />
              </label>
              <label className="adate__f">
                Hasta
                <input type="date" value={to} min={from || undefined} onChange={(e) => setTo(e.target.value)} />
              </label>
              {(dateOn || q || filter !== "todos") && (
                <button type="button" className="adate__clear" onClick={clearAll}>
                  Quitar filtros
                </button>
              )}
            </div>

            {rows.length ? (
              <div className="carpetas">
                {rows.map((c, i) => (
                  <CarpetaExpediente
                    key={c.id}
                    c={c}
                    i={i}
                    selected={selected?.id === c.id}
                    onSelect={() => setSelId(c.id)}
                    onOpen={() => open(c.id)}
                  />
                ))}
              </div>
            ) : (
              <p className="ar-none" role="status">
                {filter !== "todos" && !q && !dateOn
                  ? `No hay carpetas en «${kindLabel(filter)}».`
                  : "No hay expedientes con esa búsqueda, fecha o filtro."}
              </p>
            )}
          </>
        )}
      </div>
    </main>
  );
}

function kindLabel(f: Filter): string {
  return f === "proc" ? "En proceso" : f === "todos" ? "Todos" : KIND_VERDICT[f];
}
