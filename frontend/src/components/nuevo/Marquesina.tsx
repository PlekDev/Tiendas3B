/** Línea de estado en loop. Decorativa (aria-hidden): los anuncios van en la región aria-live. */
export function Marquesina({ texto }: { texto: string }) {
  const item = <span className="y2k-marq__item">{texto}</span>;
  return (
    <div className="y2k-marq" aria-hidden>
      <div className="y2k-marq__track" key={texto}>
        {item}
        {item}
        {item}
        {item}
      </div>
    </div>
  );
}
