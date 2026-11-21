import type { CSSProperties, ReactNode } from "react";

export type KpiTone = "warn" | "bad" | "ok" | "proc" | "na";

/** KPI como frente de cajón. Con `onClick` es un botón que filtra; sin él, un dato fijo. */
export function KpiCajon({
  label,
  value,
  tone,
  pressed,
  onClick,
}: {
  label: string;
  value: ReactNode;
  tone: KpiTone;
  pressed?: boolean;
  onClick?: () => void;
}) {
  const style = { "--ar-stripe": `var(--stripe-${tone})` } as CSSProperties;
  const body = (
    <>
      <span className="kpi__label">{label}</span>
      <span className="kpi__n">{value}</span>
      <span className="kpi__handle" aria-hidden />
    </>
  );
  if (!onClick) {
    return (
      <div className="kpi kpi--static" style={style}>
        {body}
      </div>
    );
  }
  return (
    <button type="button" className={`kpi${pressed ? " is-on" : ""}`} style={style} aria-pressed={pressed} onClick={onClick}>
      {body}
    </button>
  );
}
