import { useEffect, useRef, useState } from "react";
import type { DemoCase } from "../types";
import { DOC_LABEL, DOC_ORDER } from "../labels";
import { getCasos } from "../api";

const STEPS = ["Clasificador", "Extractores", "Validador", "Cruces", "Dictamen"];

export function NewExpediente({
  busy,
  onAnalyze,
  onExample,
  onCancel,
}: {
  busy: boolean;
  onAnalyze: (id: string, files: File[], usarLlm: boolean) => void;
  onExample: (caso: string) => void;
  onCancel: () => void;
}) {
  const [id, setId] = useState(`EXP-${new Date().toISOString().slice(0, 10)}`);
  const [files, setFiles] = useState<File[]>([]);
  const [usarLlm, setUsarLlm] = useState(true);
  const [casos, setCasos] = useState<DemoCase[]>([]);
  const [drag, setDrag] = useState(false);
  const [step, setStep] = useState(0);
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => {
    getCasos().then(setCasos).catch(() => setCasos([]));
  }, []);

  // Mientras no exista la cola, el avance es indicativo: el análisis corre en el servidor.
  useEffect(() => {
    if (!busy) return setStep(0);
    const t = setInterval(() => setStep((s) => Math.min(s + 1, STEPS.length - 1)), 1500);
    return () => clearInterval(t);
  }, [busy]);

  const add = (list: FileList | null) => {
    if (!list) return;
    setFiles((prev) => [...prev, ...Array.from(list)]);
  };

  return (
    <div className="narrow">
      <button className="btn btn--ghost" onClick={onCancel}>
        ← Bandeja
      </button>
      <h1>Nuevo expediente</h1>

      <label className="field">
        <span>ID del expediente</span>
        <input className="input" value={id} onChange={(e) => setId(e.target.value)} />
      </label>

      <div
        className={`drop${drag ? " drop--on" : ""}`}
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
        <p>Arrastra los PDFs o imágenes del expediente</p>
        <button className="btn" onClick={() => input.current?.click()}>
          Elegir archivos
        </button>
        <input
          ref={input}
          type="file"
          multiple
          hidden
          accept=".pdf,.jpg,.jpeg,.png,.tif,.tiff"
          onChange={(e) => add(e.target.files)}
        />
      </div>

      {files.length > 0 && (
        <ul className="files">
          {files.map((f, i) => (
            <li key={`${f.name}-${i}`}>
              {f.name}{" "}
              <button
                className="link"
                onClick={() => setFiles((p) => p.filter((_, j) => j !== i))}
                aria-label={`Quitar ${f.name}`}
              >
                Quitar
              </button>
            </li>
          ))}
        </ul>
      )}

      <div className="expected">
        <div className="muted small">Se espera:</div>
        {DOC_ORDER.map((t) => (
          <span key={t} className="chip">
            {DOC_LABEL[t]}
          </span>
        ))}
      </div>

      <label className="check">
        <input type="checkbox" checked={usarLlm} onChange={(e) => setUsarLlm(e.target.checked)} />
        Usar el modelo de IA (si no está disponible, se usan reglas y patrones)
      </label>

      {busy && (
        <ol className="steps" aria-live="polite">
          {STEPS.map((s, i) => (
            <li key={s} className={i < step ? "done" : i === step ? "now" : ""}>
              {i < step ? "✓" : i === step ? "…" : "○"} {s}
            </li>
          ))}
        </ol>
      )}

      <div className="row">
        <button
          className="btn btn--primary"
          disabled={busy || !files.length || !id.trim()}
          onClick={() => onAnalyze(id.trim(), files, usarLlm)}
        >
          {busy ? "Analizando…" : "Analizar"}
        </button>
      </div>

      <h2>O prueba con un ejemplo</h2>
      <p className="muted small">No necesita documentos reales ni modelo de IA.</p>
      <div className="cards">
        {casos.map((c) => (
          <article key={c.caso} className="card">
            <h3>{c.expediente_id}</h3>
            <p className="small">{c.descripcion}</p>
            <button className="btn" disabled={busy} onClick={() => onExample(c.caso)}>
              Abrir ejemplo
            </button>
          </article>
        ))}
        {!casos.length && (
          <p className="muted small">
            No se pudo cargar la lista de ejemplos. ¿Está corriendo la API (make api)?
          </p>
        )}
      </div>
    </div>
  );
}
