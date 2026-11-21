import type { ReactNode } from "react";
import { animated, useSpring } from "@react-spring/web";
import { motion, useReducedMotion } from "motion/react";
import { TONE_ICON, type Tone } from "../labels";

/** Chip de estado: palabra + color + ícono, nunca solo color. */
export function Chip({
  tone,
  children,
  icon,
  size,
}: {
  tone: Tone;
  children: ReactNode;
  icon?: string;
  size?: "sm" | "lg";
}) {
  return (
    <span className={`chip t-${tone}${size ? ` chip--${size}` : ""}`}>
      <span className="dot" aria-hidden>
        {icon ?? TONE_ICON[tone]}
      </span>
      {children}
    </span>
  );
}

export function Dot({ tone, icon, ring }: { tone: Tone; icon?: string; ring?: boolean }) {
  return (
    <span className={`dot t-${tone}${ring ? " dot--ring" : ""}`} aria-hidden>
      {icon ?? TONE_ICON[tone]}
    </span>
  );
}

/** Número que cuenta hasta su valor (react-spring). */
export function CountUp({ value, suffix = "" }: { value: number; suffix?: string }) {
  const reduce = useReducedMotion();
  const { n } = useSpring({ from: { n: 0 }, to: { n: value }, immediate: !!reduce, config: { tension: 170, friction: 26 } });
  return <animated.span className="num">{n.to((x) => `${Math.round(x)}${suffix}`)}</animated.span>;
}

const R = 40;
const C = 2 * Math.PI * R;

/** Anillo de confianza: color del veredicto, número siempre visible. value: 0–1. */
export function ConfidenceRing({ value, tone }: { value: number; tone: Tone }) {
  const pct = Math.round(value * 100);
  return (
    <div className={`ring t-${tone}`} role="img" aria-label={`Confianza ${pct} por ciento`}>
      <svg width="96" height="96" viewBox="0 0 96 96" aria-hidden>
        <circle cx="48" cy="48" r={R} fill="none" stroke="var(--surface-2)" strokeWidth="9" />
        <motion.circle
          cx="48"
          cy="48"
          r={R}
          fill="none"
          stroke="var(--fg)"
          strokeWidth="9"
          strokeLinecap="round"
          strokeDasharray={C}
          transform="rotate(-90 48 48)"
          initial={{ strokeDashoffset: C }}
          animate={{ strokeDashoffset: C * (1 - value) }}
          transition={{ duration: 0.6, ease: [0.2, 0.8, 0.2, 1] }}
        />
      </svg>
      <span className="ring__num">
        <CountUp value={pct} suffix="%" />
      </span>
    </div>
  );
}

/** Contenedor que se despliega con altura animada. */
export function Collapse({ open, children }: { open: boolean; children: ReactNode }) {
  return (
    <motion.div
      initial={false}
      animate={{ height: open ? "auto" : 0, opacity: open ? 1 : 0 }}
      transition={{ type: "spring", stiffness: 420, damping: 40 }}
      style={{ overflow: "hidden" }}
      aria-hidden={!open}
      inert={!open}
    >
      {children}
    </motion.div>
  );
}
