import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import type { DemoCase, DocType } from "../types";
import { DOC_LABEL, DOC_ORDER, type Tone } from "../labels";
import { getCasos } from "../api";
import { Chip } from "./Bits";

const STEPS = ["Clasificador", "Extractores", "Validador", "Cruces", "Dictamen"];

/** Pista por nombre de archivo. El tipo real lo decide el Clasificador al analizar. */
function guessType(name: string): DocType | null {
  const n = name.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
  if (/escritura/.test(n)) return "escrituras";
  if (/predial/.test(n)) return "predial";
  if (/alineamiento|numero.?oficial|no.?oficial/.test(n)) return "alineamiento_y_numero_oficial";
  if (/uso.?de.?suelo|uso.?suelo|\buso\b/.test(n)) return "uso_de_suelo";
  return null;
}

function size(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

const EXAMPLE_TONE: Record<string, [Tone, string]> = {
  cumple: ["ok", "Cumple"],
  revision: ["warn", "Revisión"],
  no_cumple: ["bad", "No cumple"],
  incompleto: ["miss", "Incompleto"],
};

export function NewExpediente({
  busy,
  aiAvailable,
  initialId,
  error,
  onAnalyze,
  onExample,
  onCancel,
  onDismissError,
}: {
  busy: boolean;
  aiAvailable: boolean;
  initialId?: string;
  error: string | null;
  onAnalyze: (id: string, files: File[], usarLlm: boolean) => void;
  onExample: (caso: string) => void;
  onCancel: () => void;
  onDismissError: () => void;
}) {
  const [id, setId] = useState(initialId ?? "");
  const [files, setFiles] = useState<File[]>([]);
  const [ai, setAi] = useState(true);
  const [casos, setCasos] = useState<DemoCase[] | null>(null);
  const [drag, setDrag] = useState(false);
  const [step, setStep] = useState(0);
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => {
    getCasos().then(setCasos).catch(() => setCasos([]));
  }, []);

  // No hay cola todavía (A4): el avance es indicativo mientras el servidor responde.
  useEffect(() => {
    if (!busy) return setStep(0);
    const t = setInterval(() => setStep((s) => Math.min(s + 1, STEPS.length - 1)), 1200);
    return () => clearInterval(t);
  }, [busy]);

  const add = (list: FileList | null) => {
    if (!list) return;
    const incoming = Array.from(list);
    setFiles((prev) => [...prev, ...incoming.filter((f) => !prev.some((p) => p.name === f.name))]);
  };

  const guessed = files.map((f) => guessType(f.name));
  const missing = DOC_ORDER.filter((t) => !guessed.includes(t));
  const aiOn = aiAvailable && ai;
  const finalId = id.trim() || `EXP-${new Date().toISOString().slice(0, 10)}`;

  return (
    <main className="page page--narrow" data-screen-label="Nuevo expediente">
      <div>
        <button className="back" onClick={onCancel}>
          ← Bandeja
        </button>
        <h1 className="h1" style={{ marginTop: 8 }}>
          Nuevo expediente
        </h1>
      </div>

      <section className="panel-card">
        <label className="field">
          ID del expediente
          <input
            className="input"
            value={id}
            onChange={(e) => setId(e.target.value)}
            placeholder={finalId}
            style={{ fontWeight: 400 }}
          />
        </label>

        <button
          className={`drop${drag ? " is-on" : ""}`}
          onClick={() => input.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setDrag(true);
          }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDrag(false);
            add(e.dataTransfer.files);
          }}
        >
          <span style={{ fontWeight: 600 }}>Arrastra aquí los PDF o imágenes del expediente</span>
          <span className="small muted">o haz clic para elegir archivos · PDF, JPG, PNG</span>
        </button>
        <input
          ref={input}
          type="file"
          multiple
          hidden
          accept=".pdf,.jpg,.jpeg,.png,.tif,.tiff"
          onChange={(e) => {
            add(e.target.files);
            e.target.value = "";
          }}
        />

        {files.length > 0 && (
          <div className="files">
            <AnimatePresence initial={false}>
              {files.map((f, i) => {
                const t = guessed[i];
                return (
                  <motion.div
                    key={f.name}
                    className="file"
                    layout
                    initial={{ opacity: 0, y: -4 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, height: 0, paddingTop: 0, paddingBottom: 0 }}
                  >
                    <span className="file__name">
                      {f.name} <span className="faint" style={{ fontWeight: 400 }}>· {size(f.size)}</span>
                    </span>
                    {t ? (
                      <Chip tone="neutral" icon="~">
                        Parece {DOC_LABEL[t]}
                      </Chip>
                    ) : (
                      <Chip tone="neutral">Se identifica al analizar</Chip>
                    )}
                    <button
                      className="iconbtn"
                      aria-label={`Quitar ${f.name}`}
                      onClick={() => setFiles((p) => p.filter((x) => x.name !== f.name))}
                    >
                      ✕
                    </button>
                  </motion.div>
                );
              })}
            </AnimatePresence>
          </div>
        )}

        {error && (
          <div className="alert" role="alert">
            <div className="alert__row">
              <span style={{ color: "var(--bad)", fontWeight: 600, fontSize: 14 }}>
                No pudimos completar el análisis
              </span>
              <span className="chips">
                <button
                  className="btn btn--bad"
                  disabled={busy || !files.length}
                  onClick={() => onAnalyze(finalId, files, aiOn)}
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
              {!files.length && " Vuelve a elegir los archivos para reintentar."}
            </span>
            <details>
              <summary>Detalle técnico</summary>
              <code>{error}</code>
            </details>
          </div>
        )}

        <div className="sec" style={{ gap: 8 }}>
          <span className="small muted" style={{ fontWeight: 600 }}>
            Lo que esperamos recibir
          </span>
          <div className="chips">
            {DOC_ORDER.map((t) =>
              guessed.includes(t) ? (
                <Chip key={t} tone="ok" size="lg">
                  {DOC_LABEL[t]} · Parece incluido
                </Chip>
              ) : (
                <Chip key={t} tone="miss" size="lg">
                  {DOC_LABEL[t]} · No se ve
                </Chip>
              ),
            )}
          </div>
          <span className="small faint">
            Se adivina por el nombre del archivo; el Clasificador lo confirma al analizar.
          </span>
        </div>

        <div className="switch-row">
          <button
            className="switch"
            role="switch"
            aria-checked={aiOn}
            aria-label="Usar el modelo de IA"
            disabled={!aiAvailable}
            onClick={() => setAi(!ai)}
          >
            <motion.span className="switch__knob" layout transition={{ type: "spring", stiffness: 600, damping: 35 }} />
          </button>
          <div className="sec" style={{ gap: 2 }}>
            <span style={{ fontWeight: 600 }}>Usar el modelo de IA</span>
            <span className="small muted">
              {!aiAvailable
                ? "El modelo no está disponible ahora. Se analizará con reglas y patrones."
                : aiOn
                  ? "Lee los documentos con el modelo de IA y verifica cada dato con reglas."
                  : "Se analizará solo con reglas y patrones."}
            </span>
          </div>
        </div>

        <div className="chips" style={{ alignItems: "center", gap: 12 }}>
          <button
            className="btn btn--primary btn--lg"
            disabled={busy || !files.length}
            onClick={() => onAnalyze(finalId, files, aiOn)}
          >
            {busy ? "Analizando…" : "Analizar"}
          </button>
          <span className="small muted">
            {!files.length
              ? "Agrega al menos un archivo."
              : missing.length
                ? `Parece faltar ${missing.map((t) => DOC_LABEL[t]).join(", ")}. Puedes analizar y subirlo después.`
                : "Listo para analizar."}
          </span>
        </div>

        <AnimatePresence>
          {busy && (
            <motion.div
              className="run"
              aria-live="polite"
              initial={{ opacity: 0, y: -6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
            >
              <div className="alert__row" style={{ background: "none" }}>
                <span style={{ fontWeight: 600 }}>Analizando · {STEPS[step]}</span>
                <span className="small muted">Paso {step + 1} de 5 · avance aproximado</span>
              </div>
              <div className="chips" style={{ gap: 6 }}>
                {STEPS.map((s, i) => (
                  <span key={s} className={`chip step${i < step ? " is-done" : i === step ? " is-now" : ""}`}>
                    <span className="dot dot--ring" aria-hidden>
                      {i < step ? "✓" : i + 1}
                    </span>
                    {s}
                  </span>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </section>

      <section className="sec" style={{ gap: 12 }}>
        <h2 className="h2">O prueba con un ejemplo</h2>
        <div className="examples">
          {casos?.map((c) => {
            const [tone, label] = EXAMPLE_TONE[c.caso] ?? ["neutral", c.esperado];
            return (
              <button key={c.caso} className="example" disabled={busy} onClick={() => onExample(c.caso)}>
                <Chip tone={tone}>{label}</Chip>
                <span className="mono" style={{ fontSize: 13, fontWeight: 500 }}>
                  {c.expediente_id}
                </span>
                <span className="small muted pretty">{c.descripcion}</span>
              </button>
            );
          })}
        </div>
        {casos && !casos.length && (
          <p className="small muted">
            No se pudo cargar la lista de ejemplos. ¿Está corriendo la API (make api)?
          </p>
        )}
      </section>
    </main>
  );
}
