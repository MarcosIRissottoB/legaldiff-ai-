# Manual de pruebas — LegalDiff AI

## Pre-requisitos

- Docker y Docker Compose instalados
- `.env` en la raiz con valores reales
- `gateway/.env` con la API key real de OpenAI
- Imagenes de test en `data/test_contracts/` (6 JPGs)

## Paso 1 — Verificar archivos

```bash
# Verificar que los .env existen
ls -la .env gateway/.env

# Verificar imagenes de test
ls data/test_contracts/

# Verificar que .env tiene valores (no muestra el contenido por seguridad)
wc -l .env gateway/.env
```

## Paso 2 — Build de la app

```bash
docker compose build
```

Esperado: imagen `legaldiff-ai-app` creada sin errores.

## Paso 3 — Levantar solo PostgreSQL primero

```bash
docker compose up postgres -d
sleep 5
docker compose ps
```

Esperado: servicio `postgres` con status `healthy`.

## Paso 4 — Levantar la app

```bash
docker compose up app -d
sleep 10
docker compose ps
docker compose logs app --tail 20
```

Esperado: ambos servicios `running`. Logs muestran `legaldiff_ai_started`.

## Paso 5 — Health check

```bash
curl http://localhost:8000/health
```

Esperado:
```json
{"status": "ok", "version": "0.1.0", "timestamp": "2026-..."}
```

## Paso 6 — Verificar auth

```bash
# Sin API key -> 401
curl -s http://localhost:8000/analyses | head

# Con API key incorrecta -> 401
curl -s -H "X-API-Key: wrong-key" http://localhost:8000/analyses | head

# Con API key correcta -> 200
curl -s -H "X-API-Key: TU_LEGALDIFF_API_KEY" http://localhost:8000/analyses
```

Esperado: primeros dos retornan 401, tercero retorna `{"items":[],"total":0,"limit":20,"offset":0}`.

## Paso 7 — Analizar Par 1 (Licencia de Software)

```bash
curl -X POST http://localhost:8000/analyze \
  -H "X-API-Key: TU_LEGALDIFF_API_KEY" \
  -F "original_file=@data/test_contracts/documento_1__original.jpg" \
  -F "amendment_file=@data/test_contracts/documento_1__enmienda.jpg"
```

Esperado: JSON con `analysis_id` y `result` conteniendo:
- sections_changed: menciona Plazo, Pago, Soporte, Terminacion, Proteccion de Datos
- topics_touched: categorias legales relevantes
- summary_of_the_change: describe los 5 cambios

Cambios esperados del ADR:
- [ ] Plazo: 12 -> 24 meses
- [ ] Pago: USD 12.000 -> 15.000
- [ ] Soporte: email -> email + chat
- [ ] Terminacion: 30 -> 60 dias
- [ ] Nueva clausula: Proteccion de Datos

## Paso 8 — Analizar Par 2 (Consultoria)

```bash
curl -X POST http://localhost:8000/analyze \
  -H "X-API-Key: TU_LEGALDIFF_API_KEY" \
  -F "original_file=@data/test_contracts/documento_2__original.jpg" \
  -F "amendment_file=@data/test_contracts/documento_2__enmienda.jpg"
```

Cambios esperados:
- [ ] Alcance: agregado analisis regulatorio
- [ ] Duracion: 6 -> 9 meses
- [ ] Honorarios: USD 8.000 -> 9.500
- [ ] Entregables: mensuales -> quincenales
- [ ] Nueva clausula: Propiedad Intelectual

## Paso 9 — Analizar Par 3 (SaaS)

```bash
curl -X POST http://localhost:8000/analyze \
  -H "X-API-Key: TU_LEGALDIFF_API_KEY" \
  -F "original_file=@data/test_contracts/documento_3__original.jpg" \
  -F "amendment_file=@data/test_contracts/documento_3__enmienda.jpg"
```

Cambios esperados:
- [ ] Precio: USD 1.200 -> 1.250
- [ ] Disponibilidad: 99,5% -> 99,9%
- [ ] Soporte: email -> email + tickets

## Paso 10 — Verificar persistencia

```bash
curl -s -H "X-API-Key: TU_LEGALDIFF_API_KEY" \
  "http://localhost:8000/analyses?limit=10" | python3 -m json.tool
```

Esperado: 3 registros con analysis_id, tokens_used y latency_ms.

## Paso 11 — Verificar Langfuse

1. Ir a https://cloud.langfuse.com
2. Abrir el proyecto `legaldiff-ai`
3. En Traces: verificar 3 traces `contract-analysis`
4. Cada trace debe tener llamadas a GPT-4o

## Paso 12 — Limpiar

```bash
docker compose down -v
```

---

## Troubleshooting

**Build falla**: verificar que `requirements.txt` tiene todas las deps.
```bash
docker compose build --no-cache
```

**App no arranca**: ver logs.
```bash
docker compose logs app
```

**401 en todo**: verificar que `LEGALDIFF_API_KEY` en `.env` coincide con lo que pasas en el header.

**500 en /analyze**: probablemente falta `OPENAI_API_KEY` o no tiene credito.
```bash
docker compose logs app --tail 50
```

**Langfuse no muestra traces**: verificar `LANGFUSE_PUBLIC_KEY` y `LANGFUSE_SECRET_KEY` en `.env`.

## Sin Docker (desarrollo local)

Si queres probar sin Docker, necesitas PostgreSQL local:

```bash
# Instalar deps
pip install -r requirements.txt

# Levantar PostgreSQL (si tenes brew)
brew services start postgresql

# Crear la DB
createdb legaldiff

# Correr migraciones
alembic upgrade head

# Levantar la app
uvicorn src.main:app --reload --port 8000
```

Luego los mismos curls del paso 5 en adelante.
