import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import type { DocType } from "../../types";
import { DOC_LABEL } from "../../labels";
import { Destellos } from "./Destellos";
import { HojaVoladora } from "./HojaVoladora";
import { SelloHolografico } from "./SelloHolografico";
import { useTilt } from "./useTilt";

export type Slot = Exclude<DocType, "desconocido">;
export interface Item {
  name: string;
  size?: number;
  file?: File;
}

const ACCEPT = ".pdf,.jpg,.jpeg,.png,.tif,.tiff";
const ARTICULO: Record<Slot, string> = {
  escrituras: "unas Escrituras",
  predial: "un Predial",
  alineamiento_y_numero_oficial: "un Alineamiento y Número Oficial",
  uso_de_suelo: "un Uso de Suelo",
};

/** Una carpeta física por documento. Es un <label> con un <input type="file"> real (oculto, accesible). */
export function CarpetaDocumento({
  index,
  tipo,
  item,
  duda,
  analizando,
  bloqueada,
  archivando = false,
  onPick,
  onRemove,
  onMove,
}: {
  index: number;
  tipo: Slot;
  item: Item | null;
  duda: Slot | null;
  analizando: boolean;
  bloqueada: boolean;
  archivando?: boolean;
  onPick: (files: File[]) => void;
  onRemove: () => void;
  onMove: () => void;
}) {
  const label = DOC_LABEL[tipo];
  const [over, setOver] = useState(false);
  const [burst, setBurst] = useState(0);
  const [shake, setShake] = useState(false);
  const body = useRef<HTMLDivElement>(null);
  const glare = useRef<HTMLSpanElement>(null);
  const was = useRef<string | null>(null);
  useTilt(body, glare, !bloqueada);

  // Destellos al llenarse (no al montar con la carpeta ya llena).
  useEffect(() => {
    const now = item?.name ?? null;
    if (now && now !== was.current) setBurst((b) => b + 1);
    was.current = now;
  }, [item?.name]);

  // Tipo dudoso: la carpeta tiembla 300 ms.
  useEffect(() => {
    if (!duda) return;
    setShake(true);
    const t = setTimeout(() => setShake(false), 320);
    return () => clearTimeout(t);
  }, [duda, item?.name]);

  const full = !!item;
  const estado = over ? "SUÉLTALO" : full ? "EN LA CARPETA" : "VACÍA";
  const tabTone = duda ? "doubt" : over ? "over" : full ? "full" : "empty";

  return (
    <div className={`y2k-slot${archivando ? " is-archiving" : ""}`} data-slot={tipo} style={{ "--i": index } as React.CSSProperties}>
      <label
        className={`y2k-carp${over ? " is-over" : ""}${full ? " is-full" : ""}${shake ? " is-shake" : ""}${duda ? " is-doubt" : ""}${analizando && full ? " is-scan" : ""}`}
        onDragOver={(e) => {
          if (bloqueada) return;
          e.preventDefault();
          e.stopPropagation();
          setOver(true);
        }}
        onDragLeave={(e) => {
          if (!e.currentTarget.contains(e.relatedTarget as Node)) setOver(false);
        }}
        onDrop={(e) => {
          e.preventDefault();
          e.stopPropagation();
          setOver(false);
          if (!bloqueada) onPick(Array.from(e.dataTransfer.files));
        }}
      >
        <input
          className="y2k-file"
          type="file"
          multiple
          accept={ACCEPT}
          aria-label={`Subir ${label}`}
          disabled={bloqueada}
          onChange={(e) => {
            const f = Array.from(e.target.files ?? []);
            e.target.value = "";
            if (f.length) onPick(f);
          }}
        />
        <div className="y2k-carp__body" ref={body}>
          <span className="y2k-carp__back" aria-hidden />
          <span className={`y2k-carp__tab is-${tabTone}`} aria-hidden>
            [ {String(index + 1).padStart(2, "0")} ]
          </span>

          {!full && (
            <span className="y2k-ghost" aria-hidden>
              {over ? "↓ AQUÍ" : "+ DOCUMENTO"}
            </span>
          )}
          <AnimatePresence>{full && <HojaVoladora key={item.name} scanning={analizando} />}</AnimatePresence>

          <motion.div
            className="y2k-carp__front"
            initial={false}
            animate={{ rotateX: over ? -38 : full ? 0 : -20 }}
            transition={full && !over ? { type: "spring", stiffness: 240, damping: 13 } : { type: "spring", stiffness: 300, damping: 24 }}
          >
            <span className="y2k-carp__state">{estado}</span>
            <span className="y2k-carp__name">{label}</span>
            <span className="y2k-carp__file" title={item?.name}>
              {item ? item.name : "PDF, JPG o PNG"}
            </span>
          </motion.div>

          {full && <SelloHolografico key={item.name}>RECIBIDO</SelloHolografico>}
          <span className="y2k-carp__glow" aria-hidden />
          <span className="y2k-carp__clip" aria-hidden>
            <span className="y2k-carp__glare" ref={glare} />
          </span>
          <Destellos fire={burst} className="y2k-sparks--carp" />
        </div>
      </label>

      {full && (
        <button type="button" className="y2k-slot__remove" onClick={onRemove} disabled={bloqueada} aria-label={`Quitar ${label}`}>
          Quitar
        </button>
      )}
      {duda && (
        <p className="y2k-slot__doubt" role="status">
          Parece {ARTICULO[duda]}, ¿moverlo?{" "}
          <button type="button" onClick={onMove}>
            Mover
          </button>
        </p>
      )}
    </div>
  );
}
