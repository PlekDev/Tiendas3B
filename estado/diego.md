# Estado de Diego

**Última actualización:** 2026-11-21

- **Listo:** D1 y D2 en la rama `dev/dashboard`. `frontend/` (Vite + React + TS) con bandeja, nuevo expediente, dictamen (veredicto, razones, 4 documentos, hallazgos con cita, comparación de los 5 cruces, matriz documento × regla, datos extraídos, "Cómo se decidió") y panel de evidencia. Probado contra la API real con los 4 casos de ejemplo.
- **En curso:** D3 (visor de evidencia con el PDF subido en `#page=N`: ya abre el PDF si se subió en la sesión, falta probarlo con PDFs reales), D4 y pulido.
- **Bloqueado por:** A4 (cola de trabajos) y V7 (bitácora) para D5. Mientras tanto la bandeja guarda en el navegador solo ids y resultados (nunca documentos).
- **Cambio de interfaz:** ninguno. Solo consumo `/api/v1/status`, `casos`, `ejemplo`, `analizar` y `grafo`. Pendiente A3: decidir con Aaron el idioma del contrato (hoy en inglés).

Arranque: `make api` y en otra terminal `cd frontend && npm install && npm run dev` (http://localhost:5173).
