# Sistema Multiagente para Análisis Inteligente de Documentos

> **Hackatón Tiendas 3B · Talento que Hackea el Futuro**  
> **Reto 1 · Expedientes (Expedientes de Nuevas Tiendas)**

Prototipo de sistema multiagente construido sobre **LangChain** para automatizar la revisión inicial de expedientes legales y administrativos de inmuebles candidatos a nuevas tiendas o centros de distribución de Tiendas 3B, detectando información faltante, inconsistencias cruzadas y generando una recomendación inicial sustentada en evidencia.

---

## 📋 Resumen del Reto

| Aspecto | Descripción |
| :--- | :--- |
| **Dominio** | Documentación legal y administrativa de inmuebles |
| **Insumo** | Expediente con 4 tipos documentales mínimos (PDF) |
| **Salida** | Análisis del expediente con recomendación inicial y evidencia trazable |
| **Stack obligatorio** | Arquitectura multiagente sobre **LangChain** |

---

## 🎯 El Problema

Uno de los principales retos para el crecimiento de Tiendas 3B es identificar y habilitar locales comerciales e industriales que cumplan los requisitos para operar como nuevas tiendas o centros de distribución.

Actualmente, gran parte de la revisión de la documentación legal y administrativa es manual: leer documentos, localizar información relevante, validar requisitos e identificar problemas antes de decidir si un expediente continúa. Esto consume tiempo de personal especializado y limita la capacidad de procesamiento.

> **Objetivo:** No se busca sustituir la decisión del equipo legal, sino permitirle revisar más expedientes en menos tiempo, detectar temprano los que claramente no cumplen y priorizar la intervención humana donde sí se necesita.

---

## 📂 Insumos del Expediente

Cada expediente incluye, como mínimo, **4 tipos documentales**, acompañados de una guía con la información a localizar y las reglas definitivas de evaluación:

### 1. Escrituras (`Escrituras.zip` · 12 PDFs · 52.3 MB)
- Identificación del propietario o titular
- Dirección e identificación del inmueble
- Superficie del terreno
- Datos relevantes del inmueble
- Información que lo relaciona con el resto del expediente

### 2. Predial (`Predial.zip` · 16 PDFs · 11.6 MB)
- Propietario o contribuyente
- Dirección del inmueble
- Cuenta o clave predial
- Superficie registrada
- Información que lo relaciona con los demás documentos

### 3. Alineamiento y Número Oficial (`Alineamiento_y_Numero_Oficial.zip` · 18 PDFs · 9.6 MB)
- Dirección oficial del inmueble
- Número oficial asignado
- Identificación del predio
- Alineamiento determinado por la autoridad
- Fecha de emisión y vigencia, cuando corresponda
- Autoridad emisora

### 4. Uso de Suelo (`Uso_de_suelo.zip` · 16 PDFs · 19.4 MB)
- Dirección e identificación del inmueble
- Uso de suelo autorizado
- Compatibilidad con el uso comercial requerido
- Restricciones o condicionantes
- Superficie aplicable
- Fecha de emisión y vigencia, cuando corresponda
- Autoridad emisora

---

## ⚙️ Capacidades Requeridas de la Solución

El sistema multiagente debe demostrar la colaboración entre agentes especializados para:

1. **Clasificación automática:** Identificar y clasificar el tipo de cada documento recibido.
2. **Extracción estructurada:** Extraer la información relevante definida para cada tipo documental.
3. **Validación normativa:** Evaluar la información extraída contra los criterios y reglas proporcionados.
4. **Detección de omisiones y riesgos:** Identificar documentos incompletos, información faltante, condicionantes o riesgos.
5. **Validaciones cruzadas:** Contrastar el expediente completo entre documentos del mismo inmueble para detectar:
   - Diferencias en la dirección del inmueble.
   - Diferencias en propietario o titular.
   - Diferencias relevantes en superficies.
   - Diferencias en número oficial.
   - Información de identificación del predio que no coincide.
   - Documentos que posiblemente correspondan a inmuebles diferentes.
   - Documentos faltantes o que requieran revisión adicional.
6. **Trazabilidad con evidencia:** Anotar cada hallazgo indicando qué documentos presentan discrepancias, qué información se encontró en cada uno y en qué fragmento está la evidencia.
7. **Dictamen inicial:** Emitir una recomendación (`Cumple`, `Requiere revisión` o `No cumple`) explicando con claridad las razones para facilitar la revisión del equipo legal.

---

## 📦 Entregables del Prototipo

El prototipo funcional debe permitir ingresar un expediente, ejecutar automáticamente su análisis y presentar al usuario:

- Documentos recibidos y documentos faltantes
- Datos relevantes extraídos
- Criterios y validaciones realizadas
- Inconsistencias detectadas entre documentos
- Requisitos cumplidos y no cumplidos
- Evidencia que sustenta cada hallazgo (documento y fragmento)
- Nivel de confianza del análisis
- Recomendación inicial: **`Cumple`** · **`Requiere revisión`** · **`No cumple`**

Además, se presentará un **pitch de 3 minutos** ante el jurado.

---

## 📊 Criterios de Evaluación

| Criterio | Qué evalúa el jurado | Evidencia que lo demuestra | Peso |
| :--- | :--- | :--- | :---: |
| **Precisión del análisis** | Extracción, validación contra reglas y validaciones cruzadas correctas, sin descartar expedientes que sí podían continuar. | Corrida sobre expedientes de prueba y comparación contra el dictamen de referencia. | **30%** |
| **Explicabilidad y trazabilidad** | Cada hallazgo cita la evidencia del documento original y las razones de la recomendación se entienden sin abrir el expediente. | Anotaciones con referencia al documento y fragmento que las sustenta. | **20%** |
| **Arquitectura multiagente y prototipo** | Problema dividido en agentes especializados que contrastan y validan resultados entre sí, con flujo ejecutable de principio a fin. | Diagrama de agentes y demostración en vivo con un expediente cargado durante la sesión. | **25%** |
| **Pitch** | Claridad para explicar el problema, cómo funciona la solución, cómo llega a su recomendación y el valor para el equipo legal. | Presentación de 3 minutos ante el jurado. | **25%** |

---

## 📜 Reglas y Restricciones

- La solución **debe** apoyarse en una arquitectura multiagente construida con **LangChain**.
- Todas las conclusiones deben ser **trazables** y estar sustentadas en evidencia proveniente de los documentos originales.
- **Confidencialidad:** Los documentos del reto se usan únicamente dentro del reto; no deben subirse a otros servicios ni compartirse fuera del equipo.
- Ante cualquier diferencia en criterios o listas, mandan los documentos oficiales entregados por el comité organizador junto con los datos de arranque.
