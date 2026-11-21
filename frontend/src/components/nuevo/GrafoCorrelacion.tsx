import { useEffect, useMemo, useRef, useState } from "react";
import { motion } from "motion/react";
import { Volume2, VolumeX } from "lucide-react";
import type { DocType, Evidence, Report } from "../../types";
import { CROSS_ROWS, DOC_ORDER, DOC_SHORT, fieldLabel } from "../../labels";
import { comparison } from "../../model";
import { useNarrow } from "../../anim";
import { fijarSonido, ping, sonidoActivo } from "./sonido";

type DT = Exclude<DocType, "desconocido">;
type T3 = "ok" | "warn" | "bad";

interface FNode {
  id: string;
  doc: DT;
  name: string;
  label: string;
  value: string;
  x: number;
  y: number;
  ev?: Evidence;
}
interface Edge {
  id: string;
  from: FNode;
  to: FNode;
  tone: T3;
  label?: string;
}

const COLOR: Record<T3, string> = { ok: "#4cc27f", warn: "#f2c14e", bad: "#ff5a64" };
const GOLD = "#F4DA9F";
const R_FIELD = 7;
const R_DOC = 24;

function layout(narrow: boolean) {
  const W = narrow ? 440 : 1100;
  const H = narrow ? 620 : 430;
  const pos: Record<DT, [number, number]> = narrow
    ? { escrituras: [110, 120], predial: [330, 120], alineamiento_y_numero_oficial: [110, 500], uso_de_suelo: [330, 500] }
    : { escrituras: [190, 108], predial: [910, 108], alineamiento_y_numero_oficial: [190, 322], uso_de_suelo: [910, 322] };
  return { W, H, pos, R: narrow ? 58 : 92, hub: [W / 2, H / 2] as [number, number] };
}

function build(report: Report, narrow: boolean) {
  const L = layout(narrow);
  const nodes: FNode[] = [];
  for (const t of DOC_ORDER as DT[]) {
    const a = report.document_analyses.find((x) => x.document_type === t);
    if (!a) continue;
    const crossNames = CROSS_ROWS.map((r) => r.fields[t]).filter(Boolean);
    const withValue = a.extracted_fields.filter((f) => (f.value ?? "").trim());
    const picked = [
      ...withValue.filter((f) => crossNames.includes(f.name)),
      ...withValue.filter((f) => !crossNames.includes(f.name)),
    ].slice(0, narrow ? 4 : 6);
    const [cx, cy] = L.pos[t];
    // Los datos se abren en abanico hacia el centro de la pantalla.
    const toHub = Math.atan2(L.hub[1] - cy, L.hub[0] - cx);
    const spread = Math.min(Math.PI * 1.5, 0.62 * picked.length);
    picked.forEach((f, i) => {
      const ang = picked.length === 1 ? toHub : toHub - spread / 2 + (spread * i) / (picked.length - 1);
      nodes.push({
        id: `${t}:${f.name}`,
        doc: t,
        name: f.name,
        label: fieldLabel(f.name),
        value: (f.value ?? "").trim(),
        x: cx + Math.cos(ang) * L.R,
        y: cy + Math.sin(ang) * L.R,
        ev: f.evidence ?? undefined,
      });
    });
  }
  const edges: Edge[] = [];
  for (const row of comparison(report)) {
    const cr = CROSS_ROWS.find((r) => r.key === row.key)!;
    const ns: FNode[] = [];
    (DOC_ORDER as DT[]).forEach((t, i) => {
      const c = row.cells[i];
      if (!c || !["val", "dev", "doubt"].includes(c.kind)) return;
      const n = nodes.find((x) => x.doc === t && x.name === cr.fields[t]);
      if (n) ns.push(n);
    });
    if (ns.length < 2) continue;
    const tone: T3 = row.tone === "ok" ? "ok" : row.tone === "bad" ? "bad" : "warn";
    ns.slice(1).forEach((n, k) =>
      edges.push({ id: `${row.key}-${k}`, from: ns[0], to: n, tone, label: k === 0 ? row.label : undefined }),
    );
  }
  return { L, nodes, edges };
}

function shorten(a: FNode, b: FNode, ra: number, rb: number) {
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const d = Math.hypot(dx, dy) || 1;
  return { x1: a.x + (dx / d) * ra, y1: a.y + (dy / d) * ra, x2: b.x - (dx / d) * rb, y2: b.y - (dy / d) * rb };
}

const BLOQUES = 12;

/** Barra de progreso del análisis (estilo Windows 2000). El avance es aproximado: el servidor responde de una vez. */
function BarraAnalisis({ paso, pasos, listo }: { paso: number; pasos: string[]; listo: boolean }) {
  const frac = listo ? 1 : Math.min(0.92, (paso + 0.5) / pasos.length);
  const on = Math.round(frac * BLOQUES);
  return (
    <div className="y2k-prog">
      <div className="y2k-prog__row">
        <span>{listo ? "Dictamen listo" : `Analizando · ${pasos[paso]}`}</span>
        <span className="y2k-prog__pct">
          {listo ? "100 %" : `${Math.round(frac * 100)} % · paso ${paso + 1} de ${pasos.length} · aprox.`}
        </span>
      </div>
      <div
        className={`y2k-blocks${listo ? "" : " is-busy"}`}
        role="progressbar"
        aria-label="Avance del análisis"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(frac * 100)}
      >
        {Array.from({ length: BLOQUES }, (_, i) => (
          <span key={i} className={`y2k-block${i < on ? " is-on" : ""}`} style={{ "--i": i } as React.CSSProperties} />
        ))}
      </div>
    </div>
  );
}

/** Grafo de correlaciones: mientras el servidor analiza muestra los cruces que va a evaluar;
    al llegar el dictamen reproduce los reales (datos que salen de cada documento y flechas entre ellos). */
export function GrafoCorrelacion({
  presentes,
  paso,
  pasos,
  report,
  onDone,
  onLocate,
}: {
  presentes: Record<DT, boolean>;
  paso: number;
  pasos: string[];
  report?: Report;
  onDone: () => void;
  onLocate: (e: Evidence) => void;
}) {
  const narrow = useNarrow();
  const reduce = useRef(window.matchMedia("(prefers-reduced-motion: reduce)").matches).current;
  const built = useMemo(() => (report ? build(report, narrow) : null), [report, narrow]);
  const L = built?.L ?? layout(narrow);
  const [eShown, setEShown] = useState(0);
  const [sound, setSound] = useState(sonidoActivo);
  const [sel, setSel] = useState<FNode | null>(null);
  const done = useRef(false);

  // Reproducción: primero salen los datos de cada documento, luego se marca cada cruce con su sonido.
  useEffect(() => {
    done.current = false;
    setEShown(0);
    setSel(null);
    if (!built) return;
    const { nodes, edges } = built;
    if (reduce) {
      setEShown(edges.length);
      const t = setTimeout(() => !done.current && ((done.current = true), onDone()), 700);
      return () => clearTimeout(t);
    }
    const timers: ReturnType<typeof setTimeout>[] = [];
    const start = nodes.length * 70 + 500;
    let oks = 0;
    edges.forEach((e, i) => {
      timers.push(
        setTimeout(() => {
          setEShown(i + 1);
          ping(e.tone, e.tone === "ok" ? oks++ : 0);
        }, start + i * 700),
      );
    });
    timers.push(
      setTimeout(() => {
        if (!done.current) {
          done.current = true;
          onDone();
        }
      }, start + edges.length * 700 + 900),
    );
    return () => timers.forEach(clearTimeout);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [built]);

  const skip = () => {
    if (!built || done.current) return;
    setEShown(built.edges.length);
    done.current = true;
    onDone();
  };

  const nodeTone = (n: FNode): T3 | null => {
    const seen = built?.edges.slice(0, eShown).filter((e) => e.from === n || e.to === n) ?? [];
    if (!seen.length) return null;
    return seen.some((e) => e.tone === "bad") ? "bad" : seen.some((e) => e.tone === "warn") ? "warn" : "ok";
  };

  // Mientras espera: los cruces que se evaluarán (sin resultado todavía).
  const dormant = useMemo(() => {
    const pairs = new Set<string>();
    for (const r of CROSS_ROWS) {
      const ts = (Object.keys(r.fields) as DT[]).filter((t) => presentes[t]);
      for (let i = 0; i < ts.length; i++) for (let j = i + 1; j < ts.length; j++) pairs.add(`${ts[i]}|${ts[j]}`);
    }
    return [...pairs].map((p) => p.split("|") as [DT, DT]);
  }, [presentes]);

  const toggleSound = () => {
    fijarSonido(!sound);
    setSound(!sound);
  };

  return (
    <div className="y2k-graph" role="img" aria-label={report ? "Cruces entre documentos" : `Analizando: ${pasos[paso]}`}>
      <BarraAnalisis paso={paso} pasos={pasos} listo={!!report} />
      <div className="y2k-graph__bar">
        <span className="y2k-graph__tag">
          {report ? `${built?.edges.length ?? 0} cruces · ${built?.nodes.length ?? 0} datos leídos` : `[ ${pasos[paso]} ]`}
        </span>
        <span className="y2k-graph__tools">
          <button type="button" onClick={toggleSound} aria-pressed={sound} aria-label="Sonido de los cruces">
            {sound ? <Volume2 size={16} aria-hidden /> : <VolumeX size={16} aria-hidden />}
            {sound ? "Sonido" : "Mudo"}
          </button>
          {report && (
            <button type="button" onClick={skip}>
              Saltar
            </button>
          )}
        </span>
      </div>
      <div className="y2k-graph__stage">
        <svg viewBox={`0 0 ${L.W} ${L.H}`} preserveAspectRatio="xMidYMid meet" aria-hidden>
          <defs>
            {(Object.keys(COLOR) as T3[]).map((t) => (
              <marker key={t} id={`gf-${t}`} viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
                <path d="M0 0L10 5L0 10z" fill={COLOR[t]} />
              </marker>
            ))}
          </defs>

          {/* Antes del dictamen: cruces por evaluar */}
          {!report &&
            dormant.map(([a, b], i) => {
              const [x1, y1] = L.pos[a];
              const [x2, y2] = L.pos[b];
              return (
                <g key={a + b}>
                  <line x1={x1} y1={y1} x2={x2} y2={y2} className="y2k-graph__dormant" />
                  <circle r="3.5" fill={GOLD} className="y2k-graph__dot">
                    <animateMotion dur={`${2.4 + (i % 3) * 0.4}s`} begin={`${i * 0.35}s`} repeatCount="indefinite" path={`M${x1} ${y1} L${x2} ${y2}`} />
                  </circle>
                </g>
              );
            })}

          {/* Cruces reales */}
          {built?.edges.slice(0, eShown).map((e) => {
            const s = shorten(e.from, e.to, R_FIELD + 2, R_FIELD + 5);
            const mx = (s.x1 + s.x2) / 2;
            const my = (s.y1 + s.y2) / 2;
            return (
              <g key={e.id}>
                <motion.line
                  x1={s.x1}
                  y1={s.y1}
                  x2={s.x2}
                  y2={s.y2}
                  stroke={COLOR[e.tone]}
                  strokeWidth={2}
                  strokeDasharray={e.tone === "ok" ? undefined : "5 4"}
                  markerEnd={`url(#gf-${e.tone})`}
                  initial={{ pathLength: 0, opacity: 0 }}
                  animate={{ pathLength: 1, opacity: 1 }}
                  transition={{ duration: reduce ? 0 : 0.45, ease: "easeOut" }}
                />
                {e.label && (
                  <motion.text
                    x={mx}
                    y={my - 7}
                    textAnchor="middle"
                    className="y2k-graph__edge"
                    fill={COLOR[e.tone]}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: reduce ? 0 : 0.3 }}
                  >
                    {e.label}
                  </motion.text>
                )}
              </g>
            );
          })}

          {/* Documentos */}
          {(DOC_ORDER as DT[]).map((t, i) => {
            const [x, y] = L.pos[t];
            const on = presentes[t];
            return (
              <g key={t} transform={`translate(${x} ${y})`} opacity={on ? 1 : 0.35}>
                {!report && on && <circle r={R_DOC} className="y2k-graph__scan" style={{ animationDelay: `${i * 0.5}s` }} fill="none" stroke={GOLD} />}
                <circle r={R_DOC} fill="#262626" stroke={GOLD} strokeWidth={2.5} strokeDasharray={on ? undefined : "4 4"} />
                <text y={4} textAnchor="middle" className="y2k-graph__n" fill={GOLD}>
                  {String(i + 1).padStart(2, "0")}
                </text>
                <text y={R_DOC + 17} textAnchor="middle" className="y2k-graph__doc" fill="#FBF6EA">
                  {DOC_SHORT[t]}
                </text>
                {!on && (
                  <text y={R_DOC + 31} textAnchor="middle" className="y2k-graph__sub" fill="#D9D2C3">
                    falta
                  </text>
                )}
              </g>
            );
          })}

          {/* Datos leídos */}
          {built?.nodes.map((n, i) => {
            const tone = nodeTone(n);
            const c = tone ? COLOR[tone] : GOLD;
            const [cx] = L.pos[n.doc];
            const left = n.x < cx;
            return (
              <motion.g
                key={n.id}
                className="y2k-graph__field"
                style={{ transformOrigin: `${n.x}px ${n.y}px`, transformBox: "view-box" }}
                initial={{ scale: 0, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ type: "spring", stiffness: 420, damping: 16, delay: reduce ? 0 : i * 0.07 }}
                tabIndex={0}
                role="button"
                aria-label={`${n.label}: ${n.value}`}
                onClick={() => setSel(n)}
                onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && setSel(n)}
              >
                <circle cx={n.x} cy={n.y} r={R_FIELD} fill="#262626" stroke={c} strokeWidth={2.5} />
                <text x={n.x + (left ? -12 : 12)} y={n.y + 4} textAnchor={left ? "end" : "start"} className="y2k-graph__val" fill={c}>
                  {n.value.length > (narrow ? 11 : 18) ? n.value.slice(0, narrow ? 10 : 17) + "…" : n.value}
                </text>
              </motion.g>
            );
          })}
        </svg>

        {sel && (
          <div
            className="y2k-graph__pop"
            style={{ left: `${(sel.x / L.W) * 100}%`, top: `${(sel.y / L.H) * 100}%` }}
          >
            <b>{sel.label}</b>
            <span>{sel.value}</span>
            {sel.ev?.snippet && <q>{sel.ev.snippet.length > 120 ? sel.ev.snippet.slice(0, 118) + "…" : sel.ev.snippet}</q>}
            <span className="y2k-graph__pop-act">
              {sel.ev && (
                <button type="button" onClick={() => onLocate(sel.ev!)}>
                  Ver subrayado en el documento
                </button>
              )}
              <button type="button" onClick={() => setSel(null)}>
                Cerrar
              </button>
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
