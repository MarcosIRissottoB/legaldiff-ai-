## Proyecto

LegalDiff AI — sistema multi-agente de detección de cambios contractuales.
Reemplaza 40hs/semana de revisión manual en LegalMove.

## Entry point

```bash
source .venv/bin/activate
uvicorn src.main:app --reload
```

## Tech stack

- Python 3.11+ (NUNCA usar el python3 del sistema — siempre `.venv`)
- LLM: GPT-4o Vision (gpt-4o) vía OpenAI SDK
- Validación: Pydantic v2 con `model_validate()` explícito
- Observabilidad: Langfuse v4 con `@observe` decorator + `langfuse.openai` drop-in
- API: FastAPI + uvicorn (multipart/form-data upload)
- DB: PostgreSQL + SQLAlchemy + Alembic (migraciones)
- Autenticación: API key via header `X-API-Key`
- Logging: structlog + correlation ID middleware (`X-Request-ID`)
- Prompts: archivos `.txt` en `src/prompts/`
- Testing: pytest con fixtures de contratos reales + mocks de OpenAI
- Linting/Format: ruff
- Entorno: local + Docker
- Gateway: LiteLLM Proxy en `gateway/`

## Pipeline secuencial

```
image_parser(original) ──┐
                         ├──► ContextualizationAgent ──► ExtractionAgent ──► ContractChangeOutput
image_parser(amendment) ─┘
```

- `image_parser`: valida JPEG/PNG, codifica bytes → base64 → GPT-4o Vision → texto legal
- `ContextualizationAgent`: mapea secciones y correspondencias, NO detecta cambios
- `ExtractionAgent`: recibe context_map + ambos textos → ContractChangeOutput JSON
- Langfuse trace: `@observe("contract-analysis")` con tracing automático vía drop-in

## Módulos

- `src/main.py` — FastAPI entry point. POST /analyze (multipart), GET /analyses (paginado), GET /health
- `src/config.py` — Carga .env, valida env vars, exporta constantes. OPENAI_BASE_URL opcional (Gateway)
- `src/database.py` — SQLAlchemy engine (lazy), SessionLocal, Base, get_db()
- `src/models.py` — ContractChangeOutput, AnalyzeResponse, AnalysisRecord, PaginatedAnalysesResponse
- `src/auth.py` — verify_api_key() con secrets.compare_digest()
- `src/logging_config.py` — structlog + RequestIDMiddleware (X-Request-ID)
- `src/image_parser.py` — parse_contract_image(bytes, filename) → (str, int). Retry con tenacity
- `src/agents/contextualization_agent.py` — run(original, amendment) → (str, int). Retry con tenacity
- `src/agents/extraction_agent.py` — run(context_map, original, amendment) → (ContractChangeOutput, int). model_validate() + retry
- `src/prompts/` — system prompts de agentes en archivos separados

## API Endpoints

- `POST /analyze` — multipart/form-data con `original_file` y `amendment_file` (UploadFile). Requiere `X-API-Key`
- `GET /analyses?limit=20&offset=0` — paginado. Requiere `X-API-Key`
- `GET /health` — público, verifica DB con SELECT 1

## AI Gateway

LiteLLM Proxy en `gateway/` — centraliza llamadas a OpenAI con virtual keys por proyecto.

- **Proxy**: `http://localhost:4000`
- **Dashboard**: `http://localhost:4000/ui`
- **Virtual keys**: sk-legaldiff-dev ($10/mes), sk-legaldiff-prod ($50/mes)
- **Bypass dev**: comentar `OPENAI_BASE_URL` en `.env` para ir directo a OpenAI
- **Portabilidad**: copiar `gateway/` a otro proyecto

## Product & Architecture Decisions

- GPT-4o Vision sobre OCR tradicional: un solo modelo para extracción + análisis
- Handoff secuencial sobre paralelo: el ExtractionAgent necesita el contexto del primero para reducir alucinaciones
- `model_validate()` explícito después del LLM call para structured outputs (más control sobre errores de validación)
- System prompts en archivos `.txt` separados (más fácil de iterar sin tocar código)
- Multipart upload: bytes en memoria, no se persisten en disco
- tenacity retry: 3 intentos con exponential backoff para todas las llamadas a OpenAI
- Alembic para migraciones de DB (no create_all en producción)
- Validación al arranque: falla rápido si faltan variables de entorno requeridas
- Imágenes NUNCA se commitean (son documentos de clientes)

## Security

- `OPENAI_API_KEY` es una virtual key del Gateway (no la real de OpenAI)
- La API key real de OpenAI vive SOLO en `gateway/.env`
- `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`, `DATABASE_URL`, `LEGALDIFF_API_KEY` → siempre en `.env`
- `.env` y `gateway/.env` nunca se commitean
- Imágenes de contratos en `data/test_contracts/` → en `.gitignore`
- Nunca loggear contenido de contratos, solo metadata (filename, tokens, latencia, request_id)
- Autenticación via `X-API-Key` header con comparación segura (secrets.compare_digest)

## Langfuse — tracing

```
@observe("contract-analysis")
  ├── parse_contract_image (original) — via langfuse.openai drop-in
  ├── parse_contract_image (amendment) — via langfuse.openai drop-in
  ├── contextualization_agent.run() — via langfuse.openai drop-in
  └── extraction_agent.run() — via langfuse.openai drop-in
```

## General behavior

- Responder siempre en español
- Python tipado estricto, sin `Any` sin justificación
- Commits en inglés en formato convencional (feat:, fix:, chore:)
- Nunca modificar ContractChangeOutput sin actualizar también los tests
- Si un agente falla, Langfuse captura el error automáticamente vía @observe
- Los system prompts de agentes no se cambian sin revisar primero los casos de prueba del ADR
