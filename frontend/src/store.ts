import { useCallback, useEffect, useState } from "react";
import type { Entry } from "./types";

const KEY = "tiendas3b.bandeja.v1";

/** URLs locales de los PDFs subidos: viven solo en memoria del navegador. */
const fileUrls = new Map<string, string>();

export function rememberFiles(expedienteId: string, files: File[]): void {
  for (const f of files) fileUrls.set(`${expedienteId}/${f.name}`, URL.createObjectURL(f));
}

export function fileUrl(expedienteId: string, name: string): string | undefined {
  return fileUrls.get(`${expedienteId}/${name}`);
}

function load(): Entry[] {
  try {
    const raw = JSON.parse(localStorage.getItem(KEY) ?? "[]") as Entry[];
    // Lo que quedó "procesando" al cerrar la pestaña ya no va a terminar.
    return raw.map((e) =>
      e.status === "procesando" ? { ...e, status: "error", error: "Se interrumpió el análisis." } : e,
    );
  } catch {
    return [];
  }
}

/** Bandeja en el navegador (solo ids y resultados) hasta que existan la cola y la bitácora. */
export function useBandeja() {
  const [entries, setEntries] = useState<Entry[]>(load);

  useEffect(() => {
    try {
      localStorage.setItem(KEY, JSON.stringify(entries));
    } catch {
      /* almacenamiento lleno o bloqueado: la bandeja sigue en memoria */
    }
  }, [entries]);

  const upsert = useCallback((entry: Entry) => {
    setEntries((prev) => [entry, ...prev.filter((e) => e.id !== entry.id)]);
  }, []);

  const remove = useCallback((id: string) => {
    setEntries((prev) => prev.filter((e) => e.id !== id));
  }, []);

  return { entries, upsert, remove };
}
