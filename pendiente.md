# Pendientes para cumplir con la rubrica

Analisis contra la rubrica de evaluacion. Ordenado por impacto en la nota.

---

## CRITICO (afecta criterios de 15 puntos)

### 1. No hay entry point CLI (afecta 1.1 + 4.1 — hasta 25pts en riesgo)

**Rubrica dice:** "Script principal: src/main.py — Entry point que acepta dos paths de imagenes como argumentos y ejecuta el pipeline completo"

**Estado actual:** Solo existe FastAPI REST API. No hay `if __name__ == "__main__"` ni argparse. El evaluador espera correr algo como:

```bash
python src/main.py data/test_contracts/documento_1__original.jpg data/test_contracts/documento_1__enmienda.jpg
```

**Solucion:** Agregar bloque CLI con argparse al final de `src/main.py` que ejecute el pipeline y muestre el JSON resultado.

> **Puede hacer Claude Code**

---

### 2. LangChain NO esta en el proyecto (afecta 1.2 — 15pts)

**Rubrica dice:** "LangChain para implementar y orquestar los dos agentes colaborativos"

**Estado actual:** Los agentes usan OpenAI SDK directamente. No hay imports de `langchain` en ningun archivo. No esta en `requirements.txt`.

**Opciones:**
- **Opcion A** — Integrar LangChain: wrappear los agentes actuales con `langchain` Chains/Runnables. Minimo: usar `ChatOpenAI` + `RunnableSequence` para la orquestacion.
- **Opcion B** — Defender la decision: argumentar que la orquestacion directa es mas simple, menos overhead, y que LangChain no agrega valor real en un pipeline secuencial de 2 pasos. Riesgo: el evaluador podria penalizarlo si la consigna es explicita.

**Recomendacion:** Opcion A. La consigna es EXPLICITA sobre LangChain. Aunque arquitectonicamente tu enfoque actual es valido, la rubrica lo pide y el evaluador lo va a buscar.

> **Puede hacer Claude Code** (Opcion A)
> **Tarea manual** (Opcion B — preparar argumentos para la defensa)

---

### 3. Langfuse: spans implicitos, no explicitos (afecta 3.1 — 15pts)

**Rubrica dice:** "Traza padre con jerarquia clara de spans. Registra inputs, outputs y metricas relevantes (latencia, tokens) para cada etapa del pipeline."

**Estado actual:**
- `@observe("contract-analysis")` solo en `_run_pipeline()` (traza padre)
- Spans hijos son **implicitos** via `langfuse.openai` drop-in — se crean automaticamente cuando OpenAI SDK hace llamadas
- Los parametros `langfuse_parent` estan declarados pero SIN USAR en los 3 modulos

**Problema para la demo:** En el dashboard de Langfuse vas a ver las generations pero sin nombres claros como "parse_original_contract", "contextualization_agent", etc. El evaluador puede interpretar que no controlaste la instrumentacion.

**Solucion:** Agregar `@observe()` con nombres explicitos en cada funcion del pipeline para que aparezcan como spans hijos con nombre propio.

> **Puede hacer Claude Code**

---

## IMPORTANTE (afecta criterios de 10 puntos)

### 4. `.env.example` esta VACIO (afecta 2.2 — 10pts)

**Rubrica dice:** "Dependencias con versiones fijadas y template de variables de entorno"

**Estado actual:** El archivo existe pero tiene 0 bytes.

**Solucion:** Completar con todas las variables requeridas:
```
OPENAI_API_KEY=sk-your-key-here
LANGFUSE_PUBLIC_KEY=pk-lf-xxx
LANGFUSE_SECRET_KEY=sk-lf-xxx
LANGFUSE_HOST=https://cloud.langfuse.com
DATABASE_URL=postgresql://legaldiff:legaldiff@localhost:5432/legaldiff
LEGALDIFF_API_KEY=your-api-key-here
```

> **Puede hacer Claude Code**

---

### 5. `requirements.txt` sin versiones fijadas (afecta 2.2 — 10pts)

**Rubrica dice:** "Dependencias con versiones fijadas"

**Estado actual:** Todas usan `>=` (ej: `openai>=1.30.0`). No son reproducibles.

**Solucion:** Hacer `pip freeze` y fijar versiones exactas con `==`.

> **Puede hacer Claude Code** (ejecutar pip freeze y actualizar el archivo)

---

### 6. No hay README en `data/test_contracts/` (afecta 4.1 — 10pts)

**Rubrica dice:** "Minimo 2 pares de contratos (4 imagenes) con README explicativo"

**Estado actual:** 3 pares de JPGs existen pero sin README que explique que contiene cada par y que cambios se esperan.

**Solucion:** Crear `data/test_contracts/README.md` describiendo cada par y los cambios esperados (info ya esta en ADR.json).

> **Puede hacer Claude Code**

---

## MENOR (no afecta nota directamente, pero mejora percepcion)

### 7. Extras no pedidos en la consigna

El proyecto tiene funcionalidad EXTRA que la rubrica no pide: FastAPI REST API, PostgreSQL, Docker, auth, migraciones Alembic, structlog, AI Gateway. Esto no resta puntos pero:

- **Cuidado:** El evaluador podria preguntar por que hay tanto mas de lo pedido. Tene una respuesta clara: "es production-ready, no solo un script academico".
- **Riesgo:** Si la parte CLI no funciona, todo el extra no compensa.

> **Tarea manual** — preparar justificacion

---

### 8. Diagrama de arquitectura podria ser mas claro

El README tiene un diagrama ASCII. Para la defensa en vivo, un diagrama visual (Mermaid, draw.io) seria mas impactante.

> **Tarea manual** — preparar diagrama para la presentacion

---

## DEFENSA EN VIVO (10pts — todo manual)

### 9. Preparar demo con 2 casos

**Rubrica dice:** "Demo exitosa con 2 casos: uno con cambios simples y uno con cambios complejos"

- Par 1 (simple): documento_1 — cambios en monto y duracion
- Par 2 (complejo): documento_2 — cambios en alcance, plazos, fees, deliverables + clausula nueva

> **Tarea manual** — ejecutar pipeline, verificar output, tener backup por si falla

### 10. Explicar Langfuse en el dashboard

**Rubrica dice:** "Mostrar en el dashboard de Langfuse como se ve la traza completa"

- Tener al menos 2-3 trazas completas en el dashboard antes de la defensa
- Saber explicar: spans, inputs/outputs, tokens, latencia, jerarquia

> **Tarea manual** — ejecutar pipeline varias veces contra Langfuse Cloud, revisar dashboard

### 11. Responder preguntas tecnicas

Preguntas esperadas:
- Por que 2 agentes en vez de 1?
- Por que GPT-4o para el parsing y no OCR tradicional?
- Como se disenaron los system prompts?
- Como se maneja la validacion de errores?
- (Si integraste LangChain) Por que LangChain y no llamadas directas?

> **Tarea manual** — preparar respuestas concisas con razonamiento tecnico

---

## Resumen por tipo de tarea

### Claude Code puede resolver

| # | Tarea | Impacto |
|---|-------|---------|
| 1 | Agregar CLI entry point en main.py | CRITICO |
| 2 | Integrar LangChain para orquestacion | CRITICO |
| 3 | Agregar @observe explicitos en Langfuse | CRITICO |
| 4 | Completar .env.example | IMPORTANTE |
| 5 | Fijar versiones en requirements.txt | IMPORTANTE |
| 6 | Crear README en data/test_contracts/ | IMPORTANTE |

### Tareas manuales

| # | Tarea | Impacto |
|---|-------|---------|
| 7 | Decidir y preparar argumentos sobre LangChain | CRITICO |
| 8 | Preparar demo con 2 pares de contratos | CRITICO |
| 9 | Ejecutar pipeline contra Langfuse y revisar dashboard | CRITICO |
| 10 | Preparar respuestas para preguntas tecnicas | IMPORTANTE |
| 11 | Crear diagrama visual de arquitectura | MENOR |
| 12 | Preparar justificacion de extras (FastAPI, Docker, etc) | MENOR |
