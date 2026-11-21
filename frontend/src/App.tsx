import { useCallback, useEffect, useState } from "react";
import { AnimatePresence, MotionConfig, motion } from "motion/react";
import type { ApiStatus, Entry } from "./types";
import { analizar, getEjemplo, getStatus } from "./api";
import { rememberFiles, useBandeja } from "./store";
import { Chip } from "./components/Bits";
import { Inbox } from "./components/Inbox";
import { NewExpediente } from "./components/NewExpediente";
import { Dictamen } from "./components/Dictamen";

type View = { name: "inbox" } | { name: "new"; id?: string } | { name: "dictamen"; id: string };

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
    const check = () => getStatus().then(setStatus).catch(() => setStatus("error"));
    check();
    const t = setInterval(check, 15000);
    return () => clearInterval(t);
  }, []);

  const go = (v: View) => {
    setView(v);
    window.scrollTo({ top: 0 });
  };

  const run = useCallback(
    async (id: string, job: () => ReturnType<typeof getEjemplo>) => {
      setBusy(true);
      setError(null);
      upsert({ id, createdAt: Date.now(), status: "procesando" });
      try {
        const report = await job();
        if (report.expediente_id !== id) remove(id);
        upsert({ id: report.expediente_id, createdAt: Date.now(), status: "listo", report });
        go({ name: "dictamen", id: report.expediente_id });
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

  const openEntry = (e: Entry) => {
    if (e.report) go({ name: "dictamen", id: e.id });
    else {
      setError(e.status === "error" ? (e.error ?? null) : null);
      go({ name: "new", id: e.id });
    }
  };

  const current = view.name === "dictamen" ? entries.find((e) => e.id === view.id) : undefined;
  const offline = status === "error";
  const aiAvailable = !!status && status !== "error" && status.llm_reachable;
  const screen = view.name === "dictamen" ? "inbox" : view.name;

  return (
    <MotionConfig reducedMotion="user">
      <header className="topbar">
        <button className="brand" onClick={() => go({ name: "inbox" })} aria-label="Tiendas 3B, ir a la bandeja">
          <span className="brand__mark" aria-hidden>
            <span>B</span>
            <span>BB</span>
          </span>
          <span className="brand__text">
            <b>Tiendas 3B</b>
            <span>Dictamen de expedientes</span>
          </span>
        </button>
        <nav className="nav">
          <button className={screen === "inbox" ? "is-on" : ""} onClick={() => go({ name: "inbox" })}>
            Bandeja
          </button>
          <button className={screen === "new" ? "is-on" : ""} onClick={() => go({ name: "new" })}>
            Nuevo expediente
          </button>
        </nav>
        <div className="topbar__right">
          {offline ? (
            <Chip tone="bad">Sin conexión con la API</Chip>
          ) : status && status.llm_reachable ? (
            <Chip tone="ok">IA conectada</Chip>
          ) : status ? (
            <span title="El análisis sigue funcionando con reglas y patrones">
              <Chip tone="info">Modo sin IA</Chip>
            </span>
          ) : null}
          <button className="btn" onClick={toggleTheme} aria-label="Cambiar tema">
            <span className="theme-icon" aria-hidden />
            {theme === "dark" ? "Claro" : "Oscuro"}
          </button>
        </div>
      </header>
      {offline && (
        <div role="status" className="banner">
          <span className="dot t-bad" aria-hidden>
            ✕
          </span>
          Sin conexión con la API. Inicia el servidor con make api para analizar expedientes.
        </div>
      )}

      <AnimatePresence mode="wait">
        <motion.div
          key={view.name === "dictamen" ? `d-${view.id}` : view.name}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -4 }}
          transition={{ duration: 0.18, ease: "easeOut" }}
        >
          {view.name === "inbox" && (
            <Inbox
              entries={entries}
              onOpen={openEntry}
              onNew={() => go({ name: "new" })}
              onExample={() => onExample("revision")}
            />
          )}
          {view.name === "new" && (
            <NewExpediente
              busy={busy}
              aiAvailable={aiAvailable}
              initialId={view.id}
              error={error}
              onAnalyze={onAnalyze}
              onExample={onExample}
              onCancel={() => go({ name: "inbox" })}
              onDismissError={() => setError(null)}
            />
          )}
          {view.name === "dictamen" &&
            (current?.report ? (
              <Dictamen
                entry={current}
                onBack={() => go({ name: "inbox" })}
                onRemove={() => {
                  remove(current.id);
                  go({ name: "inbox" });
                }}
                onUpload={() => go({ name: "new", id: current.id })}
              />
            ) : (
              <main className="page">
                <p>
                  Expediente no encontrado.{" "}
                  <button className="linkbtn" onClick={() => go({ name: "inbox" })}>
                    Volver a la bandeja
                  </button>
                </p>
              </main>
            ))}
        </motion.div>
      </AnimatePresence>
    </MotionConfig>
  );
}
