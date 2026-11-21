import { useEffect, useState } from "react";
import { Estrella } from "./Destellos";

function useClock() {
  const fmt = () => new Date().toLocaleTimeString("es-MX", { hour: "2-digit", minute: "2-digit", hour12: false });
  const [t, setT] = useState(fmt);
  useEffect(() => {
    const i = setInterval(() => setT(fmt()), 15000);
    return () => clearInterval(i);
  }, []);
  return t;
}

/** Barra de progreso estilo Windows 2000: un bloque por carpeta. */
export function BarraBloques({ llenos, total = 4, activa }: { llenos: boolean[]; total?: number; activa: boolean }) {
  return (
    <div
      className={`y2k-blocks${activa ? " is-busy" : ""}`}
      role="progressbar"
      aria-label="Carpetas con documento"
      aria-valuemin={0}
      aria-valuemax={total}
      aria-valuenow={llenos.filter(Boolean).length}
    >
      {Array.from({ length: total }, (_, i) => (
        <span key={i} className={`y2k-block${llenos[i] ? " is-on" : ""}`} style={{ "--i": i } as React.CSSProperties} />
      ))}
    </div>
  );
}

/** Charola de anexos: lo que no se reconoce por nombre. */
export function CharolaAnexos({
  anexos,
  onRemove,
  bloqueada,
}: {
  anexos: { name: string }[];
  onRemove: (i: number) => void;
  bloqueada: boolean;
}) {
  return (
    <aside className="y2k-tray" data-anexos aria-label="Anexos">
      <span className="y2k-tray__tag">[ + ] ANEXOS</span>
      {anexos.length === 0 ? (
        <span className="y2k-tray__empty">Lo que no se reconozca por nombre cae aquí.</span>
      ) : (
        <ul>
          {anexos.map((a, i) => (
            <li key={a.name + i}>
              <span title={a.name}>{a.name}</span>
              <button type="button" disabled={bloqueada} aria-label={`Quitar anexo ${a.name}`} onClick={() => onRemove(i)}>
                ✕
              </button>
            </li>
          ))}
        </ul>
      )}
    </aside>
  );
}

/** Ventana de vidrio oscuro con barra de título del 2000, piso Tron en perspectiva y manchas flotantes.
    Soltar archivos aquí (fuera de una carpeta) los reparte por nombre. */
export function EscritorioY2K({
  children,
  footer,
  onDropFiles,
  bloqueado,
  destello = false,
}: {
  children: React.ReactNode;
  footer: React.ReactNode;
  onDropFiles: (files: File[], point: { x: number; y: number }) => void;
  bloqueado: boolean;
  destello?: boolean;
}) {
  const hora = useClock();
  const [over, setOver] = useState(false);
  return (
    <section
      className={`y2k-desk${over ? " is-over" : ""}`}
      aria-label="Escritorio de carpetas. También puedes soltar varios archivos aquí."
      onDragOver={(e) => {
        if (bloqueado) return;
        e.preventDefault();
        setOver(true);
      }}
      onDragLeave={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget as Node)) setOver(false);
      }}
      onDrop={(e) => {
        e.preventDefault();
        setOver(false);
        if (!bloqueado) onDropFiles(Array.from(e.dataTransfer.files), { x: e.clientX, y: e.clientY });
      }}
    >
      <div className="y2k-desk__bg" aria-hidden>
        <span className="y2k-blob y2k-blob--a" />
        <span className="y2k-blob y2k-blob--b" />
        <span className="y2k-blob y2k-blob--c" />
        <div className="y2k-floor">
          <div className="y2k-floor__grid" />
        </div>
      </div>
      <header className="y2k-titlebar">
        <span className="y2k-dots" aria-hidden>
          <i />
          <i />
          <i />
        </span>
        <span className="y2k-titlebar__name">ARCHIVO_3B.exe</span>
        <span className="y2k-titlebar__clock">{hora}</span>
      </header>
      <div className="y2k-desk__body">
        {children}
        {destello && (
          <span className="y2k-desk__star" aria-hidden>
            <Estrella size={28} />
          </span>
        )}
      </div>
      <footer className="y2k-desk__foot">{footer}</footer>
    </section>
  );
}
