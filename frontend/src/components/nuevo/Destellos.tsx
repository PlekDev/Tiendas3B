import { useEffect, useMemo, useState } from "react";

/** Estrella de 4 puntas. */
export function Estrella({ size = 14 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden focusable="false">
      <path d="M12 0c.9 6.6 4.4 11.1 12 12-7.6.9-11.1 5.4-12 12-.9-6.6-4.4-11.1-12-12C7.6 11.1 11.1 6.6 12 0z" fill="currentColor" />
    </svg>
  );
}

/** Ráfaga de destellos ✦. Se dispara al cambiar `fire` (>0) y desaparece sola: no es decoración permanente. */
export function Destellos({ fire, n = 7, className = "" }: { fire: number; n?: number; className?: string }) {
  const [on, setOn] = useState(false);
  useEffect(() => {
    if (!fire) return;
    setOn(true);
    const t = setTimeout(() => setOn(false), 1000);
    return () => clearTimeout(t);
  }, [fire]);

  const stars = useMemo(
    () =>
      Array.from({ length: n }, (_, i) => {
        const a = (i / n) * Math.PI * 2 + (fire % 5) * 0.4;
        const r = 46 + ((i * 37) % 30);
        return { x: Math.cos(a) * r, y: Math.sin(a) * r, s: 10 + ((i * 7) % 10), d: i * 40 };
      }),
    [n, fire],
  );
  if (!on) return null;
  return (
    <span className={`y2k-sparks ${className}`} aria-hidden>
      {stars.map((s, i) => (
        <span
          key={i}
          className="y2k-spark"
          style={{ "--x": `${s.x}px`, "--y": `${s.y}px`, animationDelay: `${s.d}ms` } as React.CSSProperties}
        >
          <Estrella size={s.s} />
        </span>
      ))}
    </span>
  );
}
