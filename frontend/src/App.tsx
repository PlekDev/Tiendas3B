import { useCallback, useEffect, useState } from "react";
import type { ApiStatus } from "./types";
import { analizar, getEjemplo, getStatus } from "./api";
import { rememberFiles, useBandeja } from "./store";
import { Inbox } from "./components/Inbox";
import { NewExpediente } from "./components/NewExpediente";
import { Dictamen } from "./components/Dictamen";

type View = { name: "inbox" } | { name: "new" } | { name: "dictamen"; id: string };

function useTheme() {
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    try {
      const saved = localStorage.getItem("tiendas3b.theme");
      if (saved === "light" || saved === "dark") return saved;
    } catch {
      /* sin almacenamiento */
    }
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  });
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try {
      localStorage.setItem("tiendas3b.theme", theme);
    } catch {
      /* sin almacenamiento */
    }
  }, [theme]);
  return [theme, () => setTheme((t) => (t === "dark" ? "light" : "dark"))] as const;
}

export default function App() {
  const [view, setView] = useState<View>({ name: "inbox" });
  const [status, setStatus] = useState<ApiStatus | null | "error">(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [theme, toggleTheme] = useTheme();
  const { entries, upsert, remove } = useBandeja();

  useEffect(() => {
    getStatus().then(setStatus).catch(() => setStatus("error"));
  }, []);

  const run = useCallback(
    async (id: string, job: () => ReturnType<typeof getEjemplo>) => {
      setBusy(true);
      setError(null);
      upsert({ id, createdAt: Date.now(), status: "procesando" });
      try {
        const report = await job();
        upsert({ id: report.expediente_id, createdAt: Date.now(), status: "listo", report });
        if (report.expediente_id !== id) remove(id);
        setView({ name: "dictamen", id: report.expediente_id });
      } catch (e) {
        const msg = e instanceof Error ? e.message : "Error desconocido";
        upsert({ id, createdAt: Date.now(), status: "error", error: msg });
        setError(msg);
      } finally {
        setBusy(false);
      }
    },
    [upsert, remove],
  );

  const onAnalyze = (id: string, files: File[], usarLlm: boolean) => {
    rememberFiles(id, files);
    void run(id, () => analizar(id, files, usarLlm));
  };
  const onExample = (caso: string) => void run(`ejemplo-${caso}`, () => getEjemplo(caso));

  const current = view.name === "dictamen" ? entries.find((e) => e.id === view.id) : undefined;

  return (
    <>
      <header className="topbar">
        <button className="brand" onClick={() => setView({ name: "inbox" })}>
          Tiendas 3B <span className="muted">· Dictamen de expedientes</span>
        </button>
        <div className="row">
          {status === "error" ? (
            <span className="chip chip--bad" title="Inicia la API con make api">
              ✕ Sin conexión con la API
            </span>
          ) : status && status.llm_reachable ? (
            <span className="chip chip--ok">✓ IA conectada: {status.llm_mode}</span>
          ) : status ? (
            <span className="chip chip--info" title="El análisis sigue funcionando">
              i Modo sin IA (reglas y patrones)
            </span>
          ) : null}
          <button className="btn btn--ghost" onClick={toggleTheme}>
            {theme === "dark" ? "Modo claro" : "Modo oscuro"}
          </button>
        </div>
      </header>

      <main className="page">
        {error && (
          <div className="alert" role="alert">
            <strong>No pudimos completar el análisis.</strong> Revisa los archivos e inténtalo de
            nuevo.
            <details>
              <summary className="small">Detalle técnico</summary>
              <code>{error}</code>
            </details>
            <button className="btn" onClick={() => setError(null)}>
              Cerrar
            </button>
          </div>
        )}
        {view.name === "inbox" && (
          <Inbox
            entries={entries}
            onOpen={(id) => setView({ name: "dictamen", id })}
            onNew={() => setView({ name: "new" })}
            onRemove={remove}
          />
        )}
        {view.name === "new" && (
          <NewExpediente
            busy={busy}
            onAnalyze={onAnalyze}
            onExample={onExample}
            onCancel={() => setView({ name: "inbox" })}
          />
        )}
        {view.name === "dictamen" &&
          (current?.report ? (
            <Dictamen report={current.report} onBack={() => setView({ name: "inbox" })} />
          ) : (
            <p>
              Expediente no encontrado.{" "}
              <button className="link" onClick={() => setView({ name: "inbox" })}>
                Volver a la bandeja
              </button>
            </p>
          ))}
      </main>
    </>
  );
}
