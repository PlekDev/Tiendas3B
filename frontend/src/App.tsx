import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, LayoutGroup, MotionConfig, motion } from "motion/react";
import { Cpu, FilePlus2, Inbox as InboxIcon, Moon, Sun, WifiOff, Workflow } from "lucide-react";
import type { ApiStatus, Entry, Evidence } from "./types";
import { analizar, getEjemplo, getStatus } from "./api";
import { rememberFiles, useBandeja } from "./store";
import { press, softSpring, spring } from "./anim";
import { Inbox } from "./components/Inbox";
import { NewExpediente } from "./components/NewExpediente";
import { Dictamen } from "./components/Dictamen";

type View = { name: "inbox" } | { name: "new"; id?: string } | { name: "dictamen"; id: string; locate?: Evidence };

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

const NAV = [
  { key: "inbox", label: "Bandeja", Icon: InboxIcon },
  { key: "new", label: "Nuevo expediente", short: "Nuevo", Icon: FilePlus2 },
] as const;

export default function App() {
  const [view, setView] = useState<View>({ name: "inbox" });
  const [status, setStatus] = useState<ApiStatus | null | "error">(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [doneId, setDoneId] = useState<string | null>(null);
  const [theme, toggleTheme] = useTheme();
  const { entries, upsert, remove } = useBandeja();
  const viewRef = useRef(view.name);
  viewRef.current = view.name;

  useEffect(() => {
    const check = () => getStatus().then(setStatus).catch(() => setStatus("error"));
    check();
    const t = setInterval(check, 15000);
    return () => clearInterval(t);
  }, []);

  const go = (v: View) => {
    setDoneId(null);
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
        // En "Nuevo expediente" el resultado se muestra ahí mismo (tarjeta con "Archivar en la bandeja").
        if (viewRef.current === "new") setDoneId(report.expediente_id);
        else go({ name: "dictamen", id: report.expediente_id });
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
  const navTo = (k: "inbox" | "new") => go(k === "inbox" ? { name: "inbox" } : { name: "new" });

  const statusUi = offline
    ? { tone: "bad", Icon: WifiOff, label: "Sin conexión", long: "Sin conexión con la API" }
    : status && status.llm_reachable
      ? { tone: "ok", Icon: Cpu, label: "IA conectada", long: "IA conectada" }
      : status
        ? { tone: "info", Icon: Workflow, label: "Sin IA", long: "Modo sin IA: reglas y patrones" }
        : null;

  return (
    <MotionConfig reducedMotion="user">
      <header className="topbar">
        <motion.button
          className="brand"
          onClick={() => go({ name: "inbox" })}
          aria-label="Tiendas 3B, ir a la bandeja"
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.97 }}
          transition={spring}
        >
          <motion.span
            className="brand__mark"
            aria-hidden
            initial={{ rotate: -90, scale: 0.4, opacity: 0 }}
            animate={{ rotate: 0, scale: 1, opacity: 1 }}
            transition={{ type: "spring", stiffness: 300, damping: 14 }}
          >
            <span>B</span>
            <span>BB</span>
          </motion.span>
          <span className="brand__text">
            <b>Tiendas 3B</b>
            <span>Dictamen de expedientes</span>
          </span>
        </motion.button>

        <LayoutGroup id="topnav">
          <nav className="nav only-wide-flex" aria-label="Secciones">
            {NAV.map(({ key, label, Icon }) => (
              <button
                key={key}
                className={screen === key ? "is-on" : ""}
                aria-current={screen === key ? "page" : undefined}
                onClick={() => navTo(key)}
              >
                {screen === key && <motion.span className="nav__pill" layoutId="nav-pill" transition={spring} />}
                <Icon size={20} strokeWidth={2.2} aria-hidden />
                <span>{label}</span>
              </button>
            ))}
          </nav>
        </LayoutGroup>

        <div className="topbar__right">
          <AnimatePresence mode="popLayout">
            {statusUi && (
              <motion.span
                key={statusUi.tone}
                className={`status t-${statusUi.tone}`}
                title={statusUi.long}
                initial={{ opacity: 0, scale: 0.8, y: -6 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.8 }}
                transition={bouncyStatus}
              >
                <span className="status__icon">
                  <statusUi.Icon size={18} strokeWidth={2.4} aria-hidden />
                  {statusUi.tone === "ok" && <span className="status__pulse" aria-hidden />}
                </span>
                <span className="status__label">{statusUi.label}</span>
              </motion.span>
            )}
          </AnimatePresence>
          <motion.button
            className="iconbtn iconbtn--lg"
            onClick={toggleTheme}
            aria-label={theme === "dark" ? "Cambiar a tema claro" : "Cambiar a tema oscuro"}
            title={theme === "dark" ? "Tema claro" : "Tema oscuro"}
            {...press}
          >
            <AnimatePresence mode="wait" initial={false}>
              <motion.span
                key={theme}
                initial={{ rotate: -120, scale: 0.4, opacity: 0 }}
                animate={{ rotate: 0, scale: 1, opacity: 1 }}
                exit={{ rotate: 120, scale: 0.4, opacity: 0 }}
                transition={{ type: "spring", stiffness: 400, damping: 20 }}
                style={{ display: "inline-flex" }}
              >
                {theme === "dark" ? <Sun size={22} strokeWidth={2.2} /> : <Moon size={22} strokeWidth={2.2} />}
              </motion.span>
            </AnimatePresence>
          </motion.button>
        </div>
      </header>

      <AnimatePresence>
        {offline && (
          <motion.div
            role="status"
            className="banner"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
          >
            <WifiOff size={18} aria-hidden />
            Sin conexión con la API. Inicia el servidor con make api para analizar expedientes.
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence mode="wait">
        <motion.div
          key={view.name === "dictamen" ? `d-${view.id}` : view.name}
          className="view"
          initial={{ opacity: 0, y: 24, scale: 0.985, filter: "blur(4px)" }}
          animate={{ opacity: 1, y: 0, scale: 1, filter: "blur(0px)" }}
          exit={{ opacity: 0, y: -12, scale: 0.99, filter: "blur(2px)", transition: { duration: 0.15 } }}
          transition={softSpring}
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
              offline={offline}
              initialId={view.id}
              error={error}
              result={doneId ? entries.find((e) => e.id === doneId)?.report : undefined}
              onOpenResult={(locate) => doneId && go({ name: "dictamen", id: doneId, locate })}
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
                initialLocate={view.locate}
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

      {/* Teléfono: navegación al alcance del pulgar. */}
      <LayoutGroup id="tabbar">
        <nav className="tabbar only-narrow-flex" aria-label="Secciones">
          {NAV.map(({ key, label, Icon, ...rest }) => {
            const on = screen === key;
            return (
              <motion.button
                key={key}
                className={on ? "is-on" : ""}
                aria-current={on ? "page" : undefined}
                onClick={() => navTo(key)}
                whileTap={{ scale: 0.9 }}
              >
                {on && <motion.span className="tabbar__pill" layoutId="tab-pill" transition={spring} />}
                <motion.span animate={{ y: on ? -2 : 0, scale: on ? 1.12 : 1 }} transition={spring} style={{ display: "inline-flex" }}>
                  <Icon size={24} strokeWidth={on ? 2.4 : 2} aria-hidden />
                </motion.span>
                <span>{"short" in rest ? rest.short : label}</span>
              </motion.button>
            );
          })}
        </nav>
      </LayoutGroup>
    </MotionConfig>
  );
}

const bouncyStatus = { type: "spring", stiffness: 500, damping: 20 } as const;
