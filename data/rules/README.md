# Cartuchos de reglas

Un JSON por tipo de documento. El motor (`src/tiendas3b/rules/engine.py`) los lee al
arrancar. **Agregar una regla no requiere tocar código** mientras uses uno de los tipos de
abajo. Si un archivo tiene un error, se reporta y se salta: no tumba el análisis.

```json
{
  "id": "USO-80",
  "tipo": "contiene_alguno",
  "campo": "uso_autorizado",
  "severidad": "warning",
  "activa": true,
  "parametros": {"valores": ["comercial", "servicios"]},
  "descripcion": "El uso autorizado incluye comercio o servicios."
}
```

| Campo | Qué es |
|---|---|
| `id` | Único dentro del cartucho. Aparece en la interfaz y en la matriz documento × regla. |
| `campo` | Debe existir en `REQUIRED_FIELDS_BY_TYPE` (`rules/criteria.py`). La prueba lo verifica. |
| `severidad` | `critical` → No cumple · `warning` → Requiere revisión · `info` → nota, no cambia el veredicto. |
| `activa` | `false` para dejar una regla escrita sin aplicarla (por ejemplo, vigencias sin confirmar). |

## Tipos de regla

| `tipo` | Pasa cuando… | `parametros` |
|---|---|---|
| `campo_presente` | El dato existe y su confianza ≥ `MIN_FIELD_CONFIDENCE` | `confianza_minima` (opcional) |
| `numero_positivo` | El dato tiene un número mayor a 0 | — |
| `contiene_alguno` | El dato menciona al menos un término | `valores` |
| `no_contiene` | El dato no menciona ningún término | `valores` |
| `alerta_si_presente` | No hay condicionantes (si los hay, falla como aviso) | `ignorar` |
| `fecha_vigente` | La fecha más la vigencia no ha pasado | `vigencia_dias` |

¿Necesitas otro tipo? Agrega una función en `RULE_TYPES` de `engine.py` y una prueba en
`tests/test_rules_engine.py`.

## Reglas pendientes de confirmar

- `ALI-90` y `USO-90` (vigencia de un año): están en `activa: false` hasta que la guía
  oficial confirme el plazo.
- Severidades: son provisionales. Las del cruce entre documentos están en `CROSS_CHECKS`
  (`rules/criteria.py`).
