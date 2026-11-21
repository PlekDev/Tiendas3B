import { useEffect, type RefObject } from "react";

/** Tilt con el cursor: ±8° en X e Y, suavizado y con requestAnimationFrame. Solo transform. */
export function useTilt(
  body: RefObject<HTMLElement | null>,
  glare: RefObject<HTMLElement | null>,
  enabled: boolean,
) {
  useEffect(() => {
    const el = body.current;
    const host = el?.parentElement;
    if (!el || !host || !enabled) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const t = { rx: 0, ry: 0, lift: 0, gx: 0, gy: 0 };
    const c = { ...t };
    let raf = 0;
    let hover = false;

    const tick = () => {
      let moving = false;
      (Object.keys(t) as (keyof typeof t)[]).forEach((k) => {
        const d = t[k] - c[k];
        if (Math.abs(d) > 0.02) moving = true;
        c[k] += d * 0.16;
      });
      el.style.transform = `translate3d(0,${-c.lift}px,0) rotateX(${c.rx}deg) rotateY(${c.ry}deg)`;
      if (glare.current) glare.current.style.transform = `translate3d(${c.gx}px,${c.gy}px,0)`;
      if (!moving && !hover) {
        el.style.willChange = "";
        el.style.transform = "";
        raf = 0;
        return;
      }
      raf = requestAnimationFrame(tick);
    };
    const start = () => {
      el.style.willChange = "transform";
      if (!raf) raf = requestAnimationFrame(tick);
    };
    const move = (e: PointerEvent) => {
      if (e.pointerType === "touch") return;
      const r = host.getBoundingClientRect();
      const px = (e.clientX - r.left) / r.width;
      const py = (e.clientY - r.top) / r.height;
      hover = true;
      t.ry = (px - 0.5) * 16;
      t.rx = -(py - 0.5) * 16;
      t.lift = 8;
      t.gx = px * r.width - 70;
      t.gy = py * r.height - 70;
      host.classList.add("is-hover");
      start();
    };
    const leave = () => {
      hover = false;
      t.rx = t.ry = t.lift = 0;
      host.classList.remove("is-hover");
      start();
    };
    host.addEventListener("pointermove", move);
    host.addEventListener("pointerleave", leave);
    return () => {
      host.removeEventListener("pointermove", move);
      host.removeEventListener("pointerleave", leave);
      cancelAnimationFrame(raf);
    };
  }, [body, glare, enabled]);
}
