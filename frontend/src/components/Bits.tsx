import type { Severity, Verdict } from "../types";
import { SEVERITY_UI, VERDICT_UI } from "../labels";

/** Veredicto: palabra + color + ícono (nunca solo color). */
export function VerdictChip({ verdict, big }: { verdict: Verdict; big?: boolean }) {
  const ui = VERDICT_UI[verdict];
  return (
    <span className={`chip chip--${ui.cls}${big ? " chip--big" : ""}`}>
      <span aria-hidden>{ui.icon}</span> {ui.short}
    </span>
  );
}

export function SeverityChip({ severity }: { severity: Severity }) {
  const ui = SEVERITY_UI[severity] ?? SEVERITY_UI.warning;
  return (
    <span className={`chip chip--${ui.cls}`}>
      <span aria-hidden>{ui.icon}</span> {ui.label}
    </span>
  );
}

const R = 54;
const C = 2 * Math.PI * R;

/** Anillo de confianza (adaptado de ScoreRing de TrustNode). value: 0–1. */
export function ConfidenceRing({ value }: { value: number }) {
  const cls = value >= 0.8 ? "ok" : value >= 0.6 ? "warn" : "bad";
  return (
    <div className="ring" role="img" aria-label={`Confianza ${Math.round(value * 100)} por ciento`}>
      <svg viewBox="0 0 120 120" aria-hidden>
        <circle className="ring__track" cx="60" cy="60" r={R} />
        <circle
          className={`ring__fill ring__fill--${cls}`}
          cx="60"
          cy="60"
          r={R}
          strokeDasharray={C}
          strokeDashoffset={C - value * C}
        />
      </svg>
      <span className="ring__num">{Math.round(value * 100)}%</span>
    </div>
  );
}

export function Section({
  title,
  hint,
  children,
  open = true,
  count,
}: {
  title: string;
  hint?: string;
  children: React.ReactNode;
  open?: boolean;
  count?: number;
}) {
  return (
    <details className="section" open={open}>
      <summary>
        <h2>{title}</h2>
        {count !== undefined && <span className="muted">{count}</span>}
        {hint && <span className="muted section__hint">{hint}</span>}
      </summary>
      <div className="section__body">{children}</div>
    </details>
  );
}
