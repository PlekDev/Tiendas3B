import { motion } from "motion/react";
import { press } from "../../anim";

/** Botón pastilla con brillo superior, sombra interna y resplandor en hover.
    `primario` = rojo cromado con destello diagonal cada 3 s (solo habilitado). */
export function BotonCromado({
  primario = false,
  className = "",
  children,
  ...rest
}: { primario?: boolean } & Omit<React.ComponentProps<typeof motion.button>, "children"> & {
    children: React.ReactNode;
  }) {
  return (
    <motion.button
      type="button"
      className={`y2k-btn${primario ? " is-primary" : ""} ${className}`}
      {...press}
      {...rest}
    >
      <span className="y2k-btn__txt">{children}</span>
      {primario && <span className="y2k-btn__flash" aria-hidden />}
    </motion.button>
  );
}
