# Estado de Victor

**Última actualización:** 21 nov 2026

- **Listo:**
  - Guía de ambiente y conexión al modelo de Andrés (`docs/AMBIENTE.md`) · rama `feature/victor-ambiente`
  - Logs estructurados + bitácora de auditoría + `GET /api/v1/bitacora` (V6, V7) · rama `feature/victor-logs`
  - `tiendas3b diagnostico` para medir OCR y clasificador (herramienta de V2, V3) · rama `feature/victor-diagnostico`
  - `tiendas3b agrupar` para armar expedientes desde los ZIP (V5) · rama `feature/victor-agrupar`
- **En curso:** correr `diagnostico` y `agrupar` sobre los documentos reales en local (V2, V3, V5)
- **Bloqueado por:** nada. Para probar con el modelo necesito la IP de Andrés (N0)
- **Cambio de interfaz:** nuevo endpoint `GET /api/v1/bitacora` (para la bandeja de Diego, D4/D5). Sin cambios en firmas existentes
