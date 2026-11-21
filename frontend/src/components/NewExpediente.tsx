import { useEffect, useRef, useState } from "react";
import { motion } from "motion/react";
import type { DemoCase, DocType, Evidence, Report } from "../types";
import { DOC_LABEL, DOC_ORDER, type Tone } from "../labels";
import { getCasos } from "../api";
import { fadeUp, spring, stagger } from "../anim";
import "../y2k-tokens.css";
import "./nuevo/y2k.css";
import { CarpetaDocumento, type Item, type Slot } from "./nuevo/CarpetaDocumento";
import { CharolaAnexos, EscritorioY2K } from "./nuevo/EscritorioY2K";
import { BotonCromado } from "./nuevo/BotonCromado";
import { GrafoCorrelacion } from "./nuevo/GrafoCorrelacion";
import { desbloquearSonido } from "./nuevo/sonido";
import { HojaVoladora } from "./nuevo/HojaVoladora";
import { Marquesina } from "./nuevo/Marquesina";

const STEPS = ["Clasificador", "Extractores", "Validador", "Cruces", "Dictamen"];
const SLOTS = DOC_ORDER as Slot[];
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

/** Pista por nombre de archivo. El tipo real lo decide el Clasificador al analizar. */
function guessType(name: string): DocType | null {
  const n = name.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
  if (/escritur|titulo.?de.?propiedad|compraventa/.test(n)) return "escrituras";
  if (/predial|boleta.?pred/.test(n)) return "predial";
  if (/alineamiento|alineamiant|alineacion|numero.?oficial|no\.?.?oficial/.test(n)) return "alineamiento_y_numero_oficial";
  if (/uso.?de.?suelo|uso.?suelo|\buso\b|lic.{0,10}suelo/.test(n)) return "uso_de_suelo";
  return null;
}

const EXAMPLE_TONE: Record<string, [Tone, string]> = {
  cumple: ["ok", "Cumple"],
  revision: ["warn", "Revisión"],
  no_cumple: ["bad", "No cumple"],
  incompleto: ["miss", "Incompleto"],
};

type Flight = { id: number; name: string; from: { x: number; y: number }; to: { x: number; y: number }; delay: number; done: () => void };
let flightId = 0;

export function NewExpediente({
  busy,
  aiAvailable,
  offline = false,
  initialId,
  error,
  result,
  onAnalyze,
  onExample,
  onCancel,
  onOpenResult,
  onDismissError,
}: {
  busy: boolean;
  aiAvailable: boolean;
  offline?: boolean;
  initialId?: string;
  error: string | null;
  result?: Report;
  onAnalyze: (id: string, files: File[], usarLlm: boolean) => void;
  onExample: (caso: string) => void;
  onCancel: () => void;
  onOpenResult: (locate?: Evidence) => void;
  onDismissError: () => void;
}) {
  const [id, setId] = useState(initialId ?? "");
  const [slots, setSlots] = useState<Partial<Record<Slot, Item>>>({});
  const [annex, setAnnex] = useState<Item[]>([]);
  const [doubts, setDoubts] = useState<Partial<Record<Slot, Slot>>>({});
  const [flights, setFlights] = useState<Flight[]>([]);
  const [ai, setAi] = useState(true);
  const [casos, setCasos] = useState<DemoCase[] | null>(null);
  const [step, setStep] = useState(0);
  const [filling, setFilling] = useState(false);
  const [announce, setAnnounce] = useState("");
  const [replay, setReplay] = useState<"idle" | "playing" | "done">("idle");
  const [lastExample, setLastExample] = useState<string | null>(null);
  const grid = useRef<HTMLDivElement>(null);
  const bulk = useRef<HTMLLabelElement>(null);
  const [resumen, setResumen] = useState("");
  const alive = useRef(true);

  useEffect(() => {
    alive.current = true;
    getCasos().then(setCasos).catch(() => setCasos([]));
    return () => {
      alive.current = false;
    };
  }, []);

  // No hay cola todavía (A4): el avance es indicativo mientras el servidor responde.
  useEffect(() => {
    if (!busy) return setStep(0);
    const t = setInterval(() => setStep((s) => Math.min(s + 1, STEPS.length - 1)), 1200);
    return () => clearInterval(t);
  }, [busy]);

  // Al llegar el dictamen se reproducen los cruces reales en el grafo; la tarjeta de resultado entra al terminar.
  useEffect(() => {
    if (!result) return setReplay("idle");
    setReplay("playing");
    setAnnounce("Dictamen listo");
  }, [result]);
  // Al terminar el grafo se abre el expediente directamente.
  const replayDone = () => {
    setReplay("done");
    onOpenResult();
  };

  /* ---------- colocar / quitar ---------- */
  const place = (slot: Slot, item: Item) => {
    setSlots((p) => ({ ...p, [slot]: item }));
    const g = guessType(item.name);
    setDoubts((p) => {
      const n = { ...p };
      if (g && g !== "desconocido" && g !== slot) n[slot] = g as Slot;
      else delete n[slot];
      return n;
    });
    setAnnounce(`${DOC_LABEL[slot]} recibida`);
  };
  const addAnnex = (item: Item) => {
    setAnnex((p) => (p.some((a) => a.name === item.name) ? p : [...p, item]));
    setAnnounce(`${item.name} guardado en anexos`);
  };
  const toItem = (f: File): Item => ({ name: f.name, size: f.size, file: f });
  const removeSlot = (s: Slot) => {
    setSlots((p) => {
      const n = { ...p };
      delete n[s];
      return n;
    });
    setDoubts((p) => {
      const n = { ...p };
      delete n[s];
      return n;
    });
    setAnnounce(`${DOC_LABEL[s]} quitada`);
  };
  const moveSlot = (from: Slot) => {
    const to = doubts[from];
    const it = slots[from];
    if (!to || !it) return;
    const other = slots[to];
    removeSlot(from);
    place(to, it);
    if (other) place(from, other);
  };

  /** Soltar varios archivos fuera de una carpeta: cada hoja vuela a su carpeta (o a Anexos), 150 ms entre una y otra. */
  const distribute = (files: File[], from: { x: number; y: number }) => {
    const taken = new Set<Slot>(SLOTS.filter((s) => slots[s]));
    const fl: Flight[] = [];
    {
      const t = new Set(taken);
      let ok = 0;
      files.forEach((f) => {
        const g = guessType(f.name);
        if (g && g !== "desconocido" && !t.has(g as Slot)) {
          t.add(g as Slot);
          ok++;
        }
      });
      const rest = files.length - ok;
      setResumen(
        rest
          ? `Acomodé ${ok} de ${files.length} por nombre. ${rest === 1 ? "1 archivo fue" : `${rest} archivos fueron`} a Anexos y se clasifica${rest === 1 ? "" : "n"} por contenido al analizar.`
          : `Listo: ${ok} ${ok === 1 ? "documento acomodado" : "documentos acomodados"} en su carpeta.`,
      );
    }
    files.forEach((f, i) => {
      const g = guessType(f.name);
      const slot = g && g !== "desconocido" && !taken.has(g as Slot) ? (g as Slot) : null;
      if (slot) taken.add(slot);
      const target = document.querySelector(slot ? `[data-slot="${slot}"] .y2k-carp__back` : "[data-anexos]");
      const r = target?.getBoundingClientRect();
      const to = r ? { x: r.left + r.width / 2, y: r.top + r.height / 2 } : from;
      const item = toItem(f);
      const flight: Flight = {
        id: ++flightId,
        name: f.name,
        from,
        to,
        delay: i * 0.15,
        done: () => {
          if (!alive.current) return;
          setFlights((p) => p.filter((x) => x.id !== flight.id));
          slot ? place(slot, item) : addAnnex(item);
        },
      };
      fl.push(flight);
    });
    setFlights((p) => [...p, ...fl]);
  };

  /** Un archivo en una carpeta: va ahí (decisión de la persona). Varios: se acomodan todos solos. */
  const pickInto = (slot: Slot, files: File[]) => {
    if (!files.length) return;
    if (files.length === 1) return place(slot, toItem(files[0]));
    const r = grid.current?.getBoundingClientRect();
    distribute(files, r ? { x: r.left + r.width / 2, y: r.top + 40 } : { x: 200, y: 200 });
  };

  /** Botón "Elegir los 4 documentos": una sola selección y cada archivo cae en su carpeta. */
  const pickAll = (list: FileList | null) => {
    const f = Array.from(list ?? []);
    if (!f.length) return;
    desbloquearSonido();
    const r = bulk.current?.getBoundingClientRect();
    distribute(f, r ? { x: r.left + r.width / 2, y: r.top + r.height / 2 } : { x: 200, y: 200 });
  };

  /* ---------- ejemplos: se llenan las carpetas una por una ---------- */
  const runExample = async (c: DemoCase) => {
    if (busy || filling) return;
    desbloquearSonido();
    setFilling(true);
    setSlots({});
    setAnnex([]);
    setDoubts({});
    setResumen("");
    setLastExample(c.caso);
    for (const name of c.documentos) {
      await sleep(320);
      if (!alive.current) return;
      const g = guessType(name);
      g && g !== "desconocido" ? place(g as Slot, { name }) : addAnnex({ name });
    }
    await sleep(700);
    if (!alive.current) return;
    setFilling(false);
    onExample(c.caso);
  };

  /* ---------- derivados (misma lógica que antes: un arreglo plano de archivos) ---------- */
  const files = [...SLOTS.map((s) => slots[s]?.file), ...annex.map((a) => a.file)].filter((f): f is File => !!f);
  const llenos = SLOTS.map((s) => !!slots[s]);
  const n = llenos.filter(Boolean).length;
  const faltan = 4 - n;
  const aiOn = aiAvailable && ai;
  const finalId = id.trim() || `EXP-${new Date().toISOString().slice(0, 10)}`;
  const locked = busy || filling || !!result;
  const canRun = files.length > 0 && !locked;

  const mensaje =
    n === 0
      ? "Coloca al menos un documento"
      : faltan > 0
        ? `Faltan ${faltan} carpeta${faltan > 1 ? "s" : ""}; se marcará como incompleto`
        : "Las cuatro carpetas están listas";

  const iaTxt = offline ? "Sin conexión con la API" : aiOn ? "IA conectada" : "Sin IA · reglas y patrones";
  const leyendo = SLOTS.filter((s) => slots[s]).map((s) => DOC_LABEL[s]);
  const marquee = busy
      ? `▸ Leyendo ${leyendo.length ? leyendo.join("… ") + "…" : "expediente…"} · ${STEPS[step]} · ${iaTxt}`
      : result
        ? `▸ Dictamen listo · ${result.recommendation} · ${(result.processing_ms / 1000).toFixed(1)} s · ${iaTxt}`
        : filling
          ? "▸ Cargando ejemplo, carpeta por carpeta…"
          : n === 0
            ? `▸ Esperando 4 documentos · ${iaTxt}`
            : `▸ ${n} de 4 carpetas con documento${annex.length ? ` · ${annex.length} anexo${annex.length > 1 ? "s" : ""}` : ""} · ${iaTxt}`;

  const analyze = () => {
    desbloquearSonido();
    onAnalyze(finalId, files, aiOn);
  };

  return (
    <main className="page new nx" data-screen-label="Nuevo expediente">
      <p className="y2k-sr" aria-live="polite">
        {announce}
      </p>

      <header className="nx-head">
        <div className="nx-head__l">
          <button className="nx-back" onClick={onCancel}>
            [ ← BANDEJA ]
          </button>
          <h1 className="nx-title">
            Cuatro carpetas. <em className="y2k-chrome-text">Un dictamen.</em>
          </h1>
          <p className="nx-lede">Elige los documentos de una vez y se acomodan solos. El Clasificador confirma el tipo al analizar.</p>
        </div>
        <label className="nx-id">
          <span>ID DEL EXPEDIENTE</span>
          <input value={id} onChange={(e) => setId(e.target.value)} placeholder={finalId} autoComplete="off" spellCheck={false} />
        </label>
      </header>

      <EscritorioY2K
        bloqueado={locked}
        onDropFiles={distribute}
        footer={
<Marquesina texto={marquee} />
        }
      >
        {(busy || (result && replay === "playing")) && (
          <GrafoCorrelacion
            presentes={Object.fromEntries(SLOTS.map((s, i) => [s, llenos[i]])) as Record<Slot, boolean>}
            paso={step}
            pasos={STEPS}
            report={busy ? undefined : result}
            onDone={replayDone}
            onLocate={(e) => onOpenResult(e)}
          />
        )}
        <div className="y2k-bulk">
          <label className={`y2k-bulk__btn${locked ? " is-off" : ""}`} ref={bulk}>
            <input
              className="y2k-file"
              type="file"
              multiple
              accept=".pdf,.jpg,.jpeg,.png,.tif,.tiff"
              disabled={locked}
              aria-label="Elegir los documentos del expediente"
              onChange={(e) => {
                pickAll(e.target.files);
                e.target.value = "";
              }}
            />
            [ + ] Elegir los 4 documentos
          </label>
          <span className="y2k-bulk__tip">
            Selecciónalos juntos (Ctrl/⌘ + clic) o arrástralos aquí. Cada uno va solo a su carpeta.
          </span>
          {resumen && (
            <p className="y2k-bulk__sum" role="status">
              {resumen}
            </p>
          )}
        </div>
        <div className="y2k-desk__layout">
          <div className="y2k-grid" ref={grid}>
            {SLOTS.map((s, i) => (
              <CarpetaDocumento
                key={s}
                index={i}
                tipo={s}
                item={slots[s] ?? null}
                duda={doubts[s] ?? null}
                analizando={busy}
                bloqueada={locked}
                onPick={(f) => pickInto(s, f)}
                onRemove={() => removeSlot(s)}
                onMove={() => moveSlot(s)}
              />
            ))}
          </div>
          <CharolaAnexos
            anexos={annex}
            bloqueada={locked}
            onRemove={(i) => setAnnex((p) => p.filter((_, j) => j !== i))}
          />
        </div>
      </EscritorioY2K>

      {flights.map((f) => (
        <HojaVoladora key={f.id} delay={f.delay} vuelo={{ from: f.from, to: f.to, onDone: f.done }} />
      ))}

      <div className="nx-ai">
        <button
          type="button"
          className={`y2k-switch${aiOn ? " is-on" : ""}`}
          role="switch"
          aria-checked={aiOn}
          aria-label="Usar el modelo de IA"
          disabled={!aiAvailable || locked}
          onClick={() => setAi(!ai)}
        >
          <motion.span className="y2k-switch__knob" layout transition={{ type: "spring", stiffness: 600, damping: 26 }} />
        </button>
        <div>
          <b>Usar el modelo de IA</b>
          <span>
            {!aiAvailable
              ? "El modelo no está disponible ahora. Se analizará con reglas y patrones."
              : aiOn
                ? "Lee los documentos con el modelo de IA y verifica cada dato con reglas."
                : "Se analizará solo con reglas y patrones."}
          </span>
        </div>
      </div>

      {error && (
        <div className="alert" role="alert">
          <div className="alert__row">
            <span style={{ color: "var(--bad)", fontWeight: 600, fontSize: 14 }}>No pudimos completar el análisis</span>
            <span className="chips">
              <button
                className="btn btn--bad"
                disabled={locked || (!files.length && !lastExample)}
                onClick={() => (files.length ? analyze() : lastExample && onExample(lastExample))}
              >
                Reintentar
              </button>
              <button className="btn" onClick={onDismissError}>
                Cerrar
              </button>
            </span>
          </div>
          <span className="small muted">
            Revisa que los archivos no estén protegidos o dañados y que la API esté encendida.
            {!files.length && !lastExample && " Vuelve a colocar los archivos para reintentar."}
          </span>
          <details>
            <summary>Detalle técnico</summary>
            <code>{error}</code>
          </details>
        </div>
      )}

      <div className="nx-action">
        <p className="nx-action__msg" aria-live="polite">
          <span className={`nx-dot${n === 4 ? " is-ok" : n > 0 ? " is-part" : ""}`} aria-hidden />
          {mensaje}
        </p>
        <BotonCromado primario disabled={!canRun} onClick={analyze}>
          {busy ? "Analizando…" : `Analizar ${n} de 4 →`}
        </BotonCromado>
      </div>

      <section className="nx-examples">
        <h2 className="nx-sub">
          <span className="mono">[ ✦ ]</span> O prueba con un ejemplo
        </h2>
        <motion.div className="nx-examples__grid" variants={stagger(0.07, 0.1)} initial="hidden" animate={casos ? "show" : "hidden"}>
          {casos?.map((c) => {
            const [tone, label] = EXAMPLE_TONE[c.caso] ?? ["miss", c.esperado];
            const count = new Set(c.documentos.map(guessType).filter(Boolean)).size;
            return (
              <motion.button
                key={c.caso}
                type="button"
                variants={fadeUp}
                className={`y2k-ex t-${tone}`}
                disabled={locked}
                onClick={() => void runExample(c)}
                whileHover={{ y: -4, transition: spring }}
                whileTap={{ scale: 0.97 }}
              >
                <span className="y2k-ex__tab mono">{c.expediente_id}</span>
                <span className="y2k-ex__stamp">{label}</span>
                <span className="y2k-ex__desc">{c.descripcion}</span>
                <span className="y2k-ex__count mono">{count} / 4 documentos</span>
              </motion.button>
            );
          })}
        </motion.div>
        {casos && !casos.length && (
          <p className="small muted">No se pudo cargar la lista de ejemplos. ¿Está corriendo la API (make api)?</p>
        )}
      </section>
    </main>
  );
}
