# Estado de Diego

**Última actualización:** 2026-11-21

- **Listo:** D1 y D2 en la rama `feature/diego-dashboard`. `frontend/` (Vite + React + TS) con el diseño de Claude Design y la paleta de Tiendas 3B: bandeja con contadores y filtros, nuevo expediente, dictamen (veredicto con anillo de confianza, razones con "Ver prueba", 4 documentos, hallazgos con cita, comparación de los 5 cruces, matriz documento × regla, datos extraídos, "Cómo se decidió") y visor de evidencia. Diseño fluido para pantallas grandes y vista de teléfono (barra inferior, tablas como tarjetas, visor como hoja deslizable). Animaciones con `motion` y `@react-spring/web`; íconos con `lucide-react`. Probado contra la API real con los 4 casos de ejemplo, en tema claro y oscuro, a 1680 px y 375 px.
- **Integración con `dev` revisada:** `make check` y 62 pruebas en verde. La UI funciona con el código de todos: los 4 ejemplos dan el veredicto esperado; subir PDFs (los ficticios de `tiendas3b demo-pdfs`) analiza y abre el visor en el PDF real, en escritorio y teléfono. `/trabajos` (A4) y `/bitacora` (V7) responden bien.
- **En curso:** D3 (ya probado con PDFs subidos; falta con expedientes reales, solo en local), D4 y pulido.
- **Siguiente:** D5, conectar la bandeja a `/trabajos` (avance real y fila) y a `/bitacora`. Ya no hay bloqueo. Mientras tanto la bandeja guarda en el navegador solo ids y resultados (nunca documentos) y usa `/analizar` directo.
- **Cambio de interfaz:** ninguno. Solo consumo `/api/v1/status`, `casos`, `ejemplo`, `analizar` y `grafo`. Pendiente A3: decidir con Aaron el idioma del contrato (hoy en inglés).

Arranque: `make api` y en otra terminal `cd frontend && npm install && npm run dev` (http://localhost:5173).
