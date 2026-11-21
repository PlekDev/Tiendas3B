import { motion } from "motion/react";

const LINES = [92, 78, 86, 58, 80, 66, 88, 48];

/** Hoja blanca con líneas grises que simulan texto.
    - Sin `vuelo`: es la hoja dentro de la carpeta (cae con rebote al llenarse y sale volando al quitarla).
    - Con `vuelo`: viaja en curva desde el escritorio hasta su carpeta (position: fixed). */
export function HojaVoladora({
  scanning = false,
  delay = 0,
  vuelo,
}: {
  scanning?: boolean;
  delay?: number;
  vuelo?: { from: { x: number; y: number }; to: { x: number; y: number }; onDone: () => void };
}) {
  if (vuelo) {
    const dx = vuelo.to.x - vuelo.from.x;
    const dy = vuelo.to.y - vuelo.from.y;
    return (
      <motion.div
        className="y2k-hoja y2k-hoja--vuelo"
        aria-hidden
        style={{ left: vuelo.from.x - 26, top: vuelo.from.y - 34 }}
        initial={{ x: 0, y: 0, rotate: -10, scale: 1.15, opacity: 0 }}
        animate={{
          x: [0, dx * 0.3, dx],
          y: [0, Math.min(dy * 0.5, 0) - 150, dy],
          rotate: [-10, 14, 0],
          scale: [1.15, 1, 0.8],
          opacity: [0, 1, 1],
        }}
        transition={{ duration: 0.8, delay, times: [0, 0.5, 1], ease: "easeInOut" }}
        onAnimationComplete={vuelo.onDone}
      >
        <Rayas />
      </motion.div>
    );
  }
  return (
    <motion.div
      className="y2k-hoja"
      initial={{ y: -240, rotate: -7, opacity: 0 }}
      animate={{ y: 0, rotate: 0, opacity: 1 }}
      exit={{ y: -320, rotate: 9, opacity: 0, transition: { duration: 0.45, ease: "easeIn" } }}
      transition={{ type: "spring", stiffness: 230, damping: 11, mass: 0.9 }}
    >
      <Rayas />
      {scanning && <span className="y2k-hoja__scan" aria-hidden />}
    </motion.div>
  );
}

function Rayas() {
  return (
    <span className="y2k-hoja__lines" aria-hidden>
      {LINES.map((w, i) => (
        <i key={i} style={{ width: `${w}%` }} />
      ))}
    </span>
  );
}
