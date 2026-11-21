import { motion } from "motion/react";

export type SelloTono = "ok" | "warn" | "bad" | "miss";

/** Sello holográfico: cae de scale 2.4 a 0.92 a 1, rotado -12°, con el tono animado. */
export function SelloHolografico({
  children = "RECIBIDO",
  tono = "ok",
  grande = false,
  rotate = -12,
  className = "",
}: {
  children?: React.ReactNode;
  tono?: SelloTono;
  grande?: boolean;
  rotate?: number;
  className?: string;
}) {
  return (
    <motion.span
      className={`y2k-sello t-${tono}${grande ? " is-lg" : ""} ${className}`}
      initial={{ scale: 2.4, opacity: 0, rotate: rotate - 10 }}
      animate={{ scale: [2.4, 0.92, 1], opacity: 1, rotate }}
      transition={{ duration: 0.55, times: [0, 0.65, 1], ease: "easeOut", delay: 0.28 }}
    >
      <span className="y2k-sello__ring" aria-hidden />
      <span className="y2k-sello__txt">{children}</span>
    </motion.span>
  );
}
