import { useMemo, useState } from "react";
import { Plus, Search } from "lucide-react";
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
        .sort(sortCarpetas),
    [carpetas, filter, q],
  );

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
              </label>
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
                {filter !== "todos" && !q
                  ? `No hay carpetas en «${kindLabel(filter)}».`
                  : "No hay expedientes con ese filtro o ID."}
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
