// Sonidito de correlación: se sintetiza con WebAudio (sin archivos). Se desbloquea en el clic de "Analizar".
const KEY = "tiendas3b.sonido";
let ctx: AudioContext | null = null;

export function sonidoActivo(): boolean {
  try {
    return localStorage.getItem(KEY) !== "off";
  } catch {
    return true;
  }
}
export function fijarSonido(on: boolean) {
  try {
    localStorage.setItem(KEY, on ? "on" : "off");
  } catch {
    /* sin almacenamiento */
  }
}

/** Llamar dentro de un gesto del usuario (clic): los navegadores lo exigen. */
export function desbloquearSonido() {
  try {
    const AC = window.AudioContext ?? (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    ctx ??= new AC();
    void ctx.resume();
  } catch {
    /* sin audio */
  }
}

function nota(freq: number, t0: number, dur: number, vol: number, type: OscillatorType = "sine") {
  if (!ctx) return;
  const o = ctx.createOscillator();
  const g = ctx.createGain();
  o.type = type;
  o.frequency.value = freq;
  g.gain.setValueAtTime(0.0001, t0);
  g.gain.exponentialRampToValueAtTime(vol, t0 + 0.012);
  g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
  o.connect(g).connect(ctx.destination);
  o.start(t0);
  o.stop(t0 + dur + 0.02);
}

/** Coincide: campanita que sube con cada cruce. Difiere: tono medio. No coincide: dos golpes graves. */
export function ping(tono: "ok" | "warn" | "bad", i = 0) {
  if (!ctx || !sonidoActivo()) return;
  const t = ctx.currentTime + 0.01;
  if (tono === "ok") {
    const f = 660 * Math.pow(1.0595, Math.min(i, 9) * 2);
    nota(f, t, 0.28, 0.07);
    nota(f * 2, t, 0.18, 0.025);
  } else if (tono === "warn") {
    nota(392, t, 0.22, 0.07, "triangle");
  } else {
    nota(196, t, 0.14, 0.09, "triangle");
    nota(165, t + 0.16, 0.22, 0.09, "triangle");
  }
}
