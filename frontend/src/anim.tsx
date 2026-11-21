// Animaciones compartidas (motion). MotionConfig reducedMotion="user" las apaga si el sistema lo pide.
import { useEffect, useState, type ReactNode } from "react";
import { motion, type Transition, type Variants } from "motion/react";

export const spring: Transition = { type: "spring", stiffness: 420, damping: 32 };
export const softSpring: Transition = { type: "spring", stiffness: 260, damping: 26 };
export const bouncy: Transition = { type: "spring", stiffness: 520, damping: 18 };

export const fadeUp: Variants = {
  hidden: { opacity: 0, y: 18 },
  show: { opacity: 1, y: 0, transition: softSpring },
};

export const pop: Variants = {
  hidden: { opacity: 0, scale: 0.6 },
  show: { opacity: 1, scale: 1, transition: bouncy },
};

export const stagger = (each = 0.05, delay = 0): Variants => ({
  hidden: {},
  show: { transition: { staggerChildren: each, delayChildren: delay } },
});

/** Aparece al entrar en pantalla (una sola vez). */
export function Reveal({
  children,
  className,
  delay = 0,
  as = "section",
}: {
  children: ReactNode;
  className?: string;
  delay?: number;
  as?: "section" | "div";
}) {
  const C = as === "div" ? motion.div : motion.section;
  return (
    <C
      className={className}
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-40px" }}
      transition={{ ...softSpring, delay }}
    >
      {children}
    </C>
  );
}

/** Props de "presionar" para botones: se hunde un poco al tocar y sube al pasar el cursor. */
export const press = {
  whileHover: { y: -2 },
  whileTap: { scale: 0.96, y: 0 },
  transition: spring,
};

export function useMedia(query: string): boolean {
  const [match, setMatch] = useState(() => window.matchMedia(query).matches);
  useEffect(() => {
    const m = window.matchMedia(query);
    const on = () => setMatch(m.matches);
    m.addEventListener("change", on);
    return () => m.removeEventListener("change", on);
  }, [query]);
  return match;
}

export const useNarrow = () => useMedia("(max-width: 820px)");
