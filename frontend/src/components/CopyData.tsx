import { useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { Check, ClipboardCopy, Copy } from "lucide-react";
import type { Report } from "../types";
import { Reveal, press, spring } from "../anim";
import { type CopyDoc, copyAllText, copyDocText } from "../model";

async function copy(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    // Sin permiso de portapapeles (http, iframe): el truco del textarea sigue funcionando.
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand("copy");
    ta.remove();
    return ok;
  }
}

function CopyBtn({ text, label, big }: { text: string; label: string; big?: boolean }) {
  const [done, setDone] = useState(false);
  return (
    <motion.button
      className={`btn ${big ? "btn--primary" : "copybtn"}`}
      aria-label={label}
      title={label}
      onClick={async () => {
        if (await copy(text)) {
          setDone(true);
          setTimeout(() => setDone(false), 1400);
        }
      }}
      {...press}
    >
      <AnimatePresence mode="wait" initial={false}>
        <motion.span
          key={done ? "ok" : "copy"}
          initial={{ scale: 0.4, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.4, opacity: 0 }}
          transition={spring}
          style={{ display: "inline-flex" }}
        >
          {done ? <Check size={big ? 18 : 15} aria-hidden /> : big ? <ClipboardCopy size={18} aria-hidden /> : <Copy size={15} aria-hidden />}
        </motion.span>
      </AnimatePresence>
      {big ? <span>{done ? "Copiado" : label}</span> : done && <span className="small">Copiado</span>}
    </motion.button>
  );
}

/** Al final del dictamen: los datos principales de cada documento, listos para pegar. */
export function CopyData({ report, docs }: { report: Report; docs: CopyDoc[] }) {
  if (!docs.length) return null;
  return (
    <Reveal className="sec">
      <div className="sec__head sec__head--row">
        <div className="sec__head">
          <h2 className="h2">Datos para copiar</h2>
          <span className="small muted">Lo principal de cada documento, tal como se leyó. Revisa lo marcado en duda.</span>
        </div>
        <CopyBtn big text={copyAllText(report, docs)} label="Copiar todo" />
      </div>
      <div className="cgrid">
        {docs.map((d) => (
          <div key={d.key} className="card cdoc">
            <div className="cdoc__head">
              <span className="sec" style={{ gap: 2, minWidth: 0 }}>
                <b>{d.title}</b>
                <span className="mono small faint" style={{ overflowWrap: "anywhere" }}>
                  {d.file}
                </span>
              </span>
              <CopyBtn text={copyDocText(d)} label={`Copiar ${d.title}`} />
            </div>
            <dl className="cdoc__rows">
              {d.rows.map((r, i) => (
                <div key={i} className={`crow${r.value ? "" : " crow--empty"}${r.doubt ? " crow--doubt" : ""}`}>
                  <dt className="small muted">{r.campo}</dt>
                  <dd>
                    <span className="crow__val">{r.value ?? "No encontrado"}</span>
                    {r.doubt && <span className="small crow__tag">en duda</span>}
                    {r.value && <CopyBtn text={r.value} label={`Copiar ${r.campo}`} />}
                  </dd>
                </div>
              ))}
            </dl>
          </div>
        ))}
      </div>
    </Reveal>
  );
}
