# Plan de Implementación — LegalDiff AI + AI Gateway v2.0

## Contexto

Proyecto skeleton con toda la configuración lista (pyproject.toml, requirements.txt, CLAUDE.md, hooks) pero **cero código fuente**. Se implementa:

1. **LegalDiff AI** — sistema multi-agente que reemplaza 40hs/semana de revisión manual de contratos en LegalMove. Pipeline secuencial: image_parser → ContextualizationAgent → ExtractionAgent → ContractChangeOutput JSON validado.
2. **AI Gateway** — gateway centralizado con LiteLLM Proxy para todas las llamadas a LLMs. La API key real de OpenAI vive únicamente en el Gateway. Los proyectos consumen via virtual keys. Vive en `gateway/` como componente autocontenido y portable.

**Discrepancia resuelta**: CLAUDE.md dice `src/api.py`, ADR dice `src/main.py`. Se usa `src/main.py` (ADR autoritativo).

**Impacto del Gateway en LegalDiff**: Cero cambios en código (OpenAI SDK 100% compatible). Solo cambia `.env`: se agrega `OPENAI_BASE_URL=http://localhost:4000` y `OPENAI_API_KEY` pasa a ser una virtual key (`sk-legaldiff-dev`).

## Cambios vs v1.0

- TASK-16 rediseñada: POST /analyze ahora recibe multipart/form-data (2 archivos), no paths
- TASK-09 actualizada: parse_contract_image recibe bytes en memoria, no path del filesystem
- TASK-10 actualizada: tests de image_parser usan bytes reales de data/test_contracts/ + mocks de OpenAI
- TASK-17 actualizada: tests de /analyze usan multipart upload
- TASK-27 nueva: Alembic — migraciones de base de datos
- TASK-28 nueva: Autenticación con API key (X-API-Key header)
- TASK-29 nueva: Logging estructurado + correlation ID middleware
- TASK-30 nueva: Health check endpoint con verificación de DB
- TASK-31 nueva: Paginación en GET /analyses
- TASK-32 nueva: README.md del proyecto principal
- CORS eliminado: server-to-server no lo requiere

## Decisiones resueltas

1. **`validate_env()` en `lifespan`** — sí, usar lifespan de FastAPI (patrón actual, on_event deprecado). Sigue fallando rápido al arranque pero facilita testing.
2. **SQLite in-memory para unit tests** — sí. Los unit tests usan SQLite (rápido, sin dependencias). E2E con Docker usa PostgreSQL real.
3. **`response_format=json_object`** — solo en ExtractionAgent. El ContextualizationAgent devuelve texto estructurado intermedio, no un schema Pydantic final.
4. **Langfuse parent spans** — verificar la API exacta de `langfuse.openai` >= 2.0.0 al implementar TASK-09. Si `langfuse_parent` no es el parámetro correcto, adaptar según docs.

---

```json
{
  "project": "LegalDiff AI + AI Gateway",
  "version": "2.0",
  "total_tasks": 32,
  "tasks": [
    {
      "id": "TASK-01",
      "title": "Package init files",
      "description": "Crear los archivos __init__.py necesarios para que src/ y src/agents/ sean paquetes Python importables, y tests/ sea descubrible por pytest.",
      "files": ["src/__init__.py", "src/agents/__init__.py", "tests/__init__.py"],
      "inputs": "Directorios src/, src/agents/, tests/ ya existen",
      "outputs": "Tres archivos __init__.py vacíos",
      "acceptance_criteria": [
        "python -c 'import src' no lanza ImportError",
        "python -c 'import src.agents' no lanza ImportError",
        "pytest --collect-only no falla por imports"
      ],
      "depends_on": []
    },
    {
      "id": "TASK-02",
      "title": "Configuración de entorno (config.py)",
      "description": "Crear src/config.py que cargue variables de entorno con python-dotenv, valide que todas las requeridas existan, y exporte constantes tipadas. Debe fallar rápido listando TODAS las variables faltantes en un solo mensaje. OPENAI_BASE_URL y LEGALDIFF_API_KEY son opcionales con defaults.",
      "files": ["src/config.py"],
      "inputs": ".env con OPENAI_API_KEY, OPENAI_BASE_URL (opcional), LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST, DATABASE_URL, LEGALDIFF_API_KEY",
      "outputs": "validate_env() + constantes exportadas tipadas",
      "acceptance_criteria": [
        "validate_env() lanza EnvironmentError si falta OPENAI_API_KEY",
        "validate_env() lista TODAS las variables faltantes en un solo mensaje, no una por una",
        "OPENAI_BASE_URL es opcional — no falla si no existe",
        "LEGALDIFF_API_KEY exportado como constante str",
        "Todas las constantes tienen tipo str",
        "Usa load_dotenv() para cargar .env",
        "ruff check src/config.py sin errores"
      ],
      "depends_on": ["TASK-01"]
    },
    {
      "id": "TASK-03",
      "title": "Setup de base de datos (database.py)",
      "description": "Crear src/database.py con SQLAlchemy engine, SessionLocal, clase Base declarativa, y función get_db() como dependency de FastAPI. create_all() SOLO para tests — en producción usa Alembic (TASK-27).",
      "files": ["src/database.py"],
      "inputs": "DATABASE_URL desde src/config.py",
      "outputs": "engine, SessionLocal, Base, get_db() listos para importar",
      "acceptance_criteria": [
        "engine se crea con DATABASE_URL de config",
        "SessionLocal tiene autocommit=False, autoflush=False",
        "Base hereda de DeclarativeBase",
        "get_db() es un generator que yield session y cierra en finally",
        "NO hay llamada a create_all() en este archivo — eso es responsabilidad de Alembic y los tests",
        "ruff check src/database.py sin errores"
      ],
      "depends_on": ["TASK-02"]
    },
    {
      "id": "TASK-04",
      "title": "Modelos Pydantic y SQLAlchemy (models.py)",
      "description": "Crear src/models.py con: (1) ContractChangeOutput — schema Pydantic del output del pipeline. (2) AnalyzeResponse — schema de respuesta de la API. (3) AnalysisRecord — modelo SQLAlchemy. (4) AnalysisRecordResponse — schema para serializar registros. Nota: AnalyzeRequest desaparece — el endpoint ahora recibe multipart/form-data, no JSON.",
      "files": ["src/models.py"],
      "inputs": "Base desde src/database.py",
      "outputs": "ContractChangeOutput, AnalyzeResponse, AnalysisRecord, AnalysisRecordResponse",
      "acceptance_criteria": [
        "ContractChangeOutput tiene exactamente 3 campos: sections_changed (list[str]), topics_touched (list[str]), summary_of_the_change (str)",
        "Los 3 campos son obligatorios — ValidationError si falta alguno",
        "AnalysisRecord.id es UUID auto-generado",
        "AnalysisRecord.result es Column(JSON)",
        "AnalysisRecord NUNCA almacena contenido de contratos, solo metadata",
        "AnalysisRecordResponse tiene model_config = {'from_attributes': True}",
        "AnalyzeResponse tiene analysis_id: UUID y result: ContractChangeOutput",
        "NO existe AnalyzeRequest — fue reemplazado por UploadFile en el endpoint",
        "ruff check src/models.py sin errores"
      ],
      "depends_on": ["TASK-03"]
    },
    {
      "id": "TASK-05",
      "title": "Agregar dependencias a requirements.txt",
      "description": "Agregar httpx>=0.27.0 (TestClient de FastAPI), python-multipart>=0.0.9 (necesario para UploadFile en FastAPI), tenacity>=8.2.0 (retry con backoff para llamadas a OpenAI), structlog>=24.0.0 (logging estructurado), y alembic>=1.13.0 (migraciones de DB).",
      "files": ["requirements.txt"],
      "inputs": "requirements.txt existente",
      "outputs": "requirements.txt con 5 dependencias nuevas agregadas",
      "acceptance_criteria": [
        "httpx>=0.27.0 existe en requirements.txt",
        "python-multipart>=0.0.9 existe en requirements.txt",
        "tenacity>=8.2.0 existe en requirements.txt",
        "structlog>=24.0.0 existe en requirements.txt",
        "alembic>=1.13.0 existe en requirements.txt",
        "No se modificaron versiones de dependencias existentes",
        "pip install -r requirements.txt no falla"
      ],
      "depends_on": []
    },
    {
      "id": "TASK-06",
      "title": "Fixtures compartidos (conftest.py)",
      "description": "Crear tests/conftest.py con fixtures basados en los 3 pares de contratos reales de data/test_contracts/ (6 archivos JPG). Fixtures: contract_pairs (paths a los 3 pares de imágenes reales), contract_image_bytes (lee bytes reales de un JPG de test_contracts/), valid_change_output, expected_changes_pair1/pair2/pair3 (cambios esperados de cada par según el ADR y el docx de referencia), sample_original_text y sample_amendment_text (texto legal del Par 1 extraído del docx), mock_env, test_client (TestClient con SQLite in-memory + API key de test).",
      "files": ["tests/conftest.py"],
      "inputs": "ContractChangeOutput desde src/models.py. Texto de contratos del docx de referencia. PRECONDICIÓN: los 6 JPGs deben estar en data/test_contracts/ (copiados manualmente — no los genera ninguna tarea del plan).",
      "outputs": "10+ fixtures basados en datos reales de test_contracts/",
      "acceptance_criteria": [
        "contract_pairs retorna dict con 3 pares: {1: {original: 'data/test_contracts/documento_1__original.jpg', amendment: 'data/test_contracts/documento_1__enmienda.jpg'}, 2: {...}, 3: {...}}",
        "contract_image_bytes lee bytes reales desde documento_1__original.jpg (no bytes sintéticos)",
        "valid_change_output devuelve ContractChangeOutput con los 3 campos poblados",
        "sample_original_text contiene el texto real del contrato Par 1 (TechNova/DataBridge): cláusulas Plazo 12 meses, Pago USD 12.000, Soporte email, Terminación 30 días, Confidencialidad",
        "sample_amendment_text contiene el texto real de la enmienda Par 1: Plazo 24 meses, Pago USD 15.000, Soporte email+chat, Terminación 60 días, Confidencialidad, nueva Protección de Datos",
        "expected_changes_pair1: Plazo 12→24, Pago 12k→15k, Soporte email→email+chat, Terminación 30→60, nueva Protección de Datos",
        "expected_changes_pair2: Alcance +regulatorio, Duración 6→9, Honorarios 8k→9.5k, Entregables mensuales→quincenales, nueva Propiedad Intelectual",
        "expected_changes_pair3: Precio 1.200→1.250, Disponibilidad 99.5%→99.9%, Soporte email→email+tickets",
        "mock_env setea las 7 env vars con valores de test via monkeypatch (incluye OPENAI_BASE_URL y LEGALDIFF_API_KEY)",
        "test_client usa SQLite in-memory y X-API-Key: test-key en headers",
        "ruff check tests/conftest.py sin errores"
      ],
      "depends_on": ["TASK-01", "TASK-04"]
    },
    {
      "id": "TASK-07",
      "title": "Tests de modelos Pydantic (test_models.py)",
      "description": "Crear tests/test_models.py que valide ContractChangeOutput: campos requeridos, ValidationError con mensaje claro, listas vacías válidas, serialización roundtrip.",
      "files": ["tests/test_models.py"],
      "inputs": "Fixtures de conftest.py. ContractChangeOutput desde src/models.py",
      "outputs": "Suite de tests que valida integridad de los schemas Pydantic",
      "acceptance_criteria": [
        "Test: ContractChangeOutput con 3 campos → no lanza error",
        "Test: falta sections_changed → ValidationError mencionando el campo",
        "Test: falta topics_touched → ValidationError mencionando el campo",
        "Test: falta summary_of_the_change → ValidationError mencionando el campo",
        "Test: listas vacías son válidas",
        "Test: model_dump() → model_validate() produce objeto idéntico",
        "Test: model_validate(dict) desde diccionario crudo funciona",
        "pytest tests/test_models.py -v → todos pasan"
      ],
      "depends_on": ["TASK-06"]
    },
    {
      "id": "TASK-08",
      "title": "System prompt del image parser",
      "description": "Crear src/prompts/image_parser.txt con el system prompt para GPT-4o Vision. Instruye a extraer texto legal completo preservando estructura, devolver texto plano sin markdown, marcar [ILEGIBLE] secciones no legibles. Prohíbe interpretar o resumir.",
      "files": ["src/prompts/image_parser.txt"],
      "inputs": "ADR: GPT-4o Vision para extracción de texto desde imágenes escaneadas",
      "outputs": "Archivo .txt con system prompt listo para cargar en runtime",
      "acceptance_criteria": [
        "El archivo existe en src/prompts/image_parser.txt",
        "Instruye a preservar estructura original (cláusulas, numeración)",
        "Pide texto plano sin markdown",
        "Indica marcar [ILEGIBLE] las secciones no legibles",
        "Prohíbe interpretar o resumir — solo transcribir",
        "No contiene variables de entorno ni código"
      ],
      "depends_on": []
    },
    {
      "id": "TASK-09",
      "title": "Image parser (image_parser.py) — recibe bytes",
      "description": "Crear src/image_parser.py con parse_contract_image(image_bytes: bytes, filename: str, langfuse_parent?). Cambio clave vs v1: recibe bytes en memoria (desde UploadFile), no path del filesystem. Debe: (1) Validar extensión desde filename (.jpg/.jpeg/.png). (2) Validar tamaño máximo 20MB. (3) Codificar bytes en base64. (4) Llamar GPT-4o Vision. (5) Retry con tenacity (3 intentos, exponential backoff). Retorna tuple[str, int].",
      "files": ["src/image_parser.py"],
      "inputs": "image_bytes: bytes, filename: str, prompt desde TASK-08",
      "outputs": "Función parse_contract_image(bytes, str) → tuple[str, int]",
      "acceptance_criteria": [
        "Firma: parse_contract_image(image_bytes: bytes, filename: str, langfuse_parent=None)",
        "ValueError si extensión de filename no es .jpg, .jpeg o .png",
        "ValueError si len(image_bytes) > 20 * 1024 * 1024 (20MB)",
        "Codifica bytes en base64 correctamente",
        "Usa from langfuse.openai import openai como drop-in",
        "Crea OpenAI client con base_url=OPENAI_BASE_URL si existe",
        "tenacity: @retry con stop_after_attempt(3) y wait_exponential(min=1, max=10)",
        "Retorna (texto.strip(), total_tokens)",
        "RuntimeError si la API falla después de 3 intentos",
        "NO acepta paths de filesystem — solo bytes",
        "ruff check src/image_parser.py sin errores"
      ],
      "depends_on": ["TASK-02", "TASK-08"]
    },
    {
      "id": "TASK-10",
      "title": "Tests del image parser (test_image_parser.py)",
      "description": "Crear tests/test_image_parser.py usando bytes reales de data/test_contracts/ para validación de input (via fixture contract_image_bytes) y mocks de OpenAI para las llamadas al LLM. Validar extensión inválida, tamaño excedido, parse exitoso con bytes reales, error de API con retry.",
      "files": ["tests/test_image_parser.py"],
      "inputs": "parse_contract_image desde src/image_parser.py, contract_image_bytes de conftest (bytes reales de JPG)",
      "outputs": "Suite de tests con bytes reales + mocks de OpenAI",
      "acceptance_criteria": [
        "Test: filename 'contrato.pdf' → ValueError con 'Formato no soportado'",
        "Test: filename 'contrato.jpeg' → validación exitosa",
        "Test: filename 'contrato.png' → validación exitosa",
        "Test: bytes > 20MB → ValueError con 'excede el límite'",
        "Test: bytes reales de documento_1__original.jpg + mock de OpenAI → retorna (texto, tokens)",
        "Test: mock lanza Exception → RuntimeError después de retries",
        "Las llamadas a OpenAI se mockean con @patch — NINGUNA llamada real al LLM",
        "Los bytes de entrada son REALES (leídos de data/test_contracts/), no sintéticos",
        "pytest tests/test_image_parser.py -v → todos pasan"
      ],
      "depends_on": ["TASK-09", "TASK-06"]
    },
    {
      "id": "TASK-11",
      "title": "System prompt del ContextualizationAgent",
      "description": "Crear src/prompts/contextualization_agent.txt. Rol: Analista Senior de Contratos Legales. Mapea secciones y correspondencias entre original y enmienda. NO detecta cambios. Output JSON con estructura de secciones.",
      "files": ["src/prompts/contextualization_agent.txt"],
      "inputs": "ADR: rol del agente, responsabilidad de mapeo sin detección de cambios",
      "outputs": "Archivo .txt con system prompt del ContextualizationAgent",
      "acceptance_criteria": [
        "Define rol como Analista Senior de Contratos Legales",
        "Instruye a mapear secciones y correspondencias entre ambos documentos",
        "Explicita que NO debe detectar cambios",
        "Pide identificar secciones nuevas y eliminadas",
        "Define formato de output como JSON con estructura de secciones"
      ],
      "depends_on": []
    },
    {
      "id": "TASK-12",
      "title": "ContextualizationAgent (contextualization_agent.py)",
      "description": "Crear src/agents/contextualization_agent.py con run(original_text, amendment_text, langfuse_parent?). Retry con tenacity. Retorna tuple[str, int].",
      "files": ["src/agents/contextualization_agent.py"],
      "inputs": "original_text: str, amendment_text: str, prompt desde TASK-11",
      "outputs": "Función run() → tuple[str, int]",
      "acceptance_criteria": [
        "Carga system prompt desde src/prompts/contextualization_agent.txt",
        "Usa from langfuse.openai import openai como drop-in",
        "Crea OpenAI client con base_url si OPENAI_BASE_URL existe",
        "Construye user message con ambos textos etiquetados",
        "tenacity: @retry con stop_after_attempt(3) y wait_exponential",
        "Retorna (context_map.strip(), total_tokens)",
        "RuntimeError con mensaje claro si la API falla después de retries",
        "ruff check sin errores"
      ],
      "depends_on": ["TASK-02", "TASK-11"]
    },
    {
      "id": "TASK-13",
      "title": "System prompt del ExtractionAgent",
      "description": "Crear src/prompts/extraction_agent.txt. Rol: Auditor Legal especializado. Output JSON con exactamente los 3 campos de ContractChangeOutput. Énfasis en exhaustividad.",
      "files": ["src/prompts/extraction_agent.txt"],
      "inputs": "ADR: rol, schema ContractChangeOutput, casos de prueba con cambios esperados",
      "outputs": "Archivo .txt con system prompt del ExtractionAgent",
      "acceptance_criteria": [
        "Define rol como Auditor Legal especializado en detección de cambios",
        "Instruye a usar el mapa de contexto para comparar sección por sección",
        "Pide identificar adiciones, eliminaciones Y modificaciones",
        "Define output JSON con exactamente sections_changed, topics_touched, summary_of_the_change",
        "Enfatiza ser exhaustivo — un cambio no reportado tiene consecuencias legales"
      ],
      "depends_on": []
    },
    {
      "id": "TASK-14",
      "title": "ExtractionAgent (extraction_agent.py)",
      "description": "Crear src/agents/extraction_agent.py con run(context_map, original_text, amendment_text, langfuse_parent?). response_format=json_object. model_validate() explícito. Retry con tenacity. Retorna tuple[ContractChangeOutput, int].",
      "files": ["src/agents/extraction_agent.py"],
      "inputs": "context_map: str, original_text: str, amendment_text: str, ContractChangeOutput desde TASK-04",
      "outputs": "Función run() → tuple[ContractChangeOutput, int]",
      "acceptance_criteria": [
        "Usa response_format={'type': 'json_object'}",
        "Parsea con json.loads() — NO usa .parse() de OpenAI SDK",
        "Valida con ContractChangeOutput.model_validate(raw_data)",
        "tenacity: @retry con stop_after_attempt(3) y wait_exponential",
        "json.JSONDecodeError si respuesta no es JSON válido",
        "ValidationError de Pydantic si falta campo requerido",
        "RuntimeError si API falla después de retries",
        "ruff check sin errores"
      ],
      "depends_on": ["TASK-02", "TASK-04", "TASK-13"]
    },
    {
      "id": "TASK-15",
      "title": "Tests de agentes (test_agents.py)",
      "description": "Tests para ambos agentes con mocks de OpenAI. ContextualizationAgent: éxito y error de API. ExtractionAgent: éxito, JSON inválido, campo faltante, error de API.",
      "files": ["tests/test_agents.py"],
      "inputs": "run() de ambos agentes, ContractChangeOutput, fixtures de conftest.py",
      "outputs": "Suite de tests con mocks para ambos agentes",
      "acceptance_criteria": [
        "Test: ContextualizationAgent mock exitoso → (context_map, tokens)",
        "Test: ContextualizationAgent API error → RuntimeError",
        "Test: ExtractionAgent mock exitoso → (ContractChangeOutput, tokens)",
        "Test: ExtractionAgent resultado es instancia de ContractChangeOutput",
        "Test: ExtractionAgent JSON inválido del LLM → Exception",
        "Test: ExtractionAgent campo faltante → ValidationError",
        "Test: ExtractionAgent API error → RuntimeError",
        "Todos los tests usan @patch, NINGUNO hace llamadas reales",
        "pytest tests/test_agents.py -v → todos pasan"
      ],
      "depends_on": ["TASK-12", "TASK-14", "TASK-06"]
    },
    {
      "id": "TASK-27",
      "title": "Migraciones de base de datos (Alembic)",
      "description": "Configurar Alembic para manejo de migraciones. alembic init migrations. Configurar alembic.ini y migrations/env.py para leer DATABASE_URL desde config.py y autodescubrir los modelos de src/models.py. Crear migración inicial con la tabla analysis_records.",
      "files": ["alembic.ini", "migrations/env.py", "migrations/versions/0001_initial_analysis_records.py"],
      "inputs": "AnalysisRecord desde src/models.py, DATABASE_URL desde config.py",
      "outputs": "Alembic configurado con migración inicial lista para aplicar",
      "acceptance_criteria": [
        "alembic.ini tiene sqlalchemy.url = (vacío — se sobreescribe en env.py)",
        "migrations/env.py importa Base desde src.database y lee DATABASE_URL desde config",
        "migrations/env.py usa target_metadata = Base.metadata para autogenerate",
        "La migración 0001 crea tabla analysis_records con todos los campos de AnalysisRecord",
        "alembic upgrade head aplica la migración sin errores contra PostgreSQL",
        "alembic downgrade -1 revierte la migración sin errores",
        "ruff check migrations/env.py sin errores"
      ],
      "depends_on": ["TASK-04"]
    },
    {
      "id": "TASK-28",
      "title": "Autenticación con API key (auth.py)",
      "description": "Crear src/auth.py con dependency de FastAPI verify_api_key(). Lee el header X-API-Key del request y lo compara contra LEGALDIFF_API_KEY de config usando secrets.compare_digest() (previene timing attacks). HTTP 401 si falta o es inválida.",
      "files": ["src/auth.py"],
      "inputs": "LEGALDIFF_API_KEY desde src/config.py",
      "outputs": "Dependency verify_api_key lista para usar en endpoints",
      "acceptance_criteria": [
        "Función verify_api_key usa APIKeyHeader(name='X-API-Key')",
        "Usa secrets.compare_digest() para comparación segura",
        "HTTP 401 con mensaje 'API key inválida o ausente' si no coincide",
        "HTTP 401 si el header X-API-Key no está presente",
        "La key correcta → retorna sin error",
        "LEGALDIFF_API_KEY se lee desde config, no hardcodeada",
        "ruff check src/auth.py sin errores"
      ],
      "depends_on": ["TASK-02"]
    },
    {
      "id": "TASK-29",
      "title": "Logging estructurado + correlation ID (logging_config.py)",
      "description": "Crear src/logging_config.py que configure structlog con JSON formatter para producción y ConsoleRenderer para desarrollo (según ENV var). Crear middleware RequestIDMiddleware que genera UUID por request, lo agrega a logs y lo retorna en header X-Request-ID.",
      "files": ["src/logging_config.py"],
      "inputs": "structlog desde requirements.txt, ENV variable (development/production)",
      "outputs": "configure_logging() + RequestIDMiddleware listos para registrar en main.py",
      "acceptance_criteria": [
        "configure_logging() configura structlog con JSONRenderer si ENV=production",
        "configure_logging() configura structlog con ConsoleRenderer si ENV=development (default)",
        "RequestIDMiddleware genera UUID v4 por request",
        "El request_id se incluye en todos los logs del request via contextvars",
        "La respuesta incluye header X-Request-ID con el UUID",
        "Los logs incluyen: timestamp, level, request_id, method, path, status_code, duration_ms",
        "NUNCA loggea body del request (contiene contratos)",
        "ruff check src/logging_config.py sin errores"
      ],
      "depends_on": ["TASK-02"]
    },
    {
      "id": "TASK-16",
      "title": "FastAPI orchestrator (main.py) — multipart upload",
      "description": "Crear src/main.py como entry point FastAPI. POST /analyze recibe dos UploadFile (original y amendment) via multipart/form-data. Lee bytes en memoria, los pasa a image_parser. Requiere X-API-Key. Langfuse trace raíz con 4 spans. Persiste AnalysisRecord. El lifespan ejecuta configure_logging() + alembic upgrade head.",
      "files": ["src/main.py"],
      "inputs": "config, database, models, auth, logging_config, image_parser, ambos agentes, alembic",
      "outputs": "App FastAPI con POST /analyze (multipart), GET /analyses, Langfuse tracing",
      "acceptance_criteria": [
        "FastAPI app con title='LegalDiff AI'",
        "lifespan: configure_logging() + alembic upgrade head + startup log",
        "POST /analyze: Form params original_file: UploadFile y amendment_file: UploadFile",
        "POST /analyze: Depends(verify_api_key) — HTTP 401 sin key válida",
        "Lee bytes con await file.read() — no guarda en disco",
        "Pipeline: parse_original → parse_amendment → contextualization → extraction",
        "Langfuse trace 'contract-analysis' con 4 spans hijos en orden",
        "Persiste AnalysisRecord con tokens_used total y latency_ms",
        "Retorna AnalyzeResponse con analysis_id + ContractChangeOutput",
        "GET /analyses: Depends(verify_api_key)",
        "ValueError → HTTP 422",
        "Errores de pipeline → HTTP 500 con request_id en body",
        "Span Langfuse con status='error' antes de re-raise",
        "NUNCA loggea contenido de contratos",
        "ruff check src/main.py sin errores"
      ],
      "depends_on": ["TASK-04", "TASK-09", "TASK-12", "TASK-14", "TASK-27", "TASK-28", "TASK-29"]
    },
    {
      "id": "TASK-30",
      "title": "Health check endpoint (GET /health)",
      "description": "Agregar GET /health a main.py. Verifica: (1) La app está levantada. (2) La DB responde (SELECT 1). (3) Retorna status, versión y timestamp. No requiere autenticación.",
      "files": ["src/main.py"],
      "inputs": "get_db() desde src/database.py",
      "outputs": "Endpoint GET /health funcional",
      "acceptance_criteria": [
        "GET /health retorna 200 con {status: 'ok', version: '0.1.0', timestamp: ISO8601}",
        "GET /health ejecuta SELECT 1 contra la DB — si falla retorna 503",
        "GET /health NO requiere X-API-Key",
        "curl http://localhost:8000/health → 200 con la app levantada"
      ],
      "depends_on": ["TASK-16"]
    },
    {
      "id": "TASK-31",
      "title": "Paginación en GET /analyses",
      "description": "Actualizar GET /analyses para soportar paginación con query params limit y offset. Retornar también total_count para que el cliente sepa cuántos registros hay en total.",
      "files": ["src/main.py"],
      "inputs": "GET /analyses existente desde TASK-16",
      "outputs": "GET /analyses paginado con limit, offset y total_count",
      "acceptance_criteria": [
        "Query params: limit: int = 20 y offset: int = 0",
        "limit máximo permitido: 100 — HTTP 422 si se excede",
        "Response body: {items: List[AnalysisRecordResponse], total: int, limit: int, offset: int}",
        "Query SQL usa .limit() y .offset() — no carga todos los registros en memoria",
        "total_count viene de SELECT COUNT(*), no de len(results)",
        "Ordenado por created_at DESC",
        "Test: GET /analyses?limit=2&offset=0 con 5 registros → 2 items, total=5",
        "Test: GET /analyses?limit=200 → 422"
      ],
      "depends_on": ["TASK-16"]
    },
    {
      "id": "TASK-17",
      "title": "Tests del orchestrator (test_main.py) — multipart con imágenes reales",
      "description": "Crear tests/test_main.py con TestClient. POST /analyze usa multipart upload con bytes reales de data/test_contracts/ (via fixture contract_image_bytes). Las llamadas a OpenAI y Langfuse se mockean. Tests: upload exitoso con JPG real, sin API key → 401, archivo PDF → 422, pipeline error → 500, health check, paginación.",
      "files": ["tests/test_main.py"],
      "inputs": "FastAPI app, TestClient, contract_image_bytes y contract_pairs de conftest",
      "outputs": "Suite de tests de integración con imágenes reales + mocks de LLM",
      "acceptance_criteria": [
        "Test: POST /analyze con bytes reales de documento_1__original.jpg y documento_1__enmienda.jpg + mocks de OpenAI → 200 con analysis_id y result",
        "Test: POST /analyze sin X-API-Key → 401",
        "Test: POST /analyze con X-API-Key incorrecta → 401",
        "Test: POST /analyze con archivo .pdf → 422",
        "Test: POST /analyze con pipeline error mockeado → 500 con request_id",
        "Test: GET /analyses sin key → 401",
        "Test: GET /analyses vacío → {items: [], total: 0}",
        "Test: GET /analyses?limit=200 → 422",
        "Test: GET /health sin key → 200",
        "Usa SQLite in-memory, mockea Langfuse y OpenAI (NO mockea los bytes de imagen)",
        "pytest tests/test_main.py -v → todos pasan"
      ],
      "depends_on": ["TASK-16", "TASK-06", "TASK-30", "TASK-31"]
    },
    {
      "id": "TASK-18",
      "title": "Actualizar CLAUDE.md",
      "description": "Actualizar CLAUDE.md con entry point correcto, módulos completos (config, database, auth, logging_config), sección AI Gateway, nota sobre multipart upload en POST /analyze, y autenticación X-API-Key.",
      "files": ["CLAUDE.md"],
      "inputs": "CLAUDE.md actual, ADRs de LegalDiff y Gateway",
      "outputs": "CLAUDE.md completamente actualizado",
      "acceptance_criteria": [
        "Entry point: uvicorn src.main:app --reload",
        "Sin referencias a src/api.py",
        "Módulos incluyen src/config.py, src/database.py, src/auth.py, src/logging_config.py",
        "POST /analyze documentado como multipart/form-data con 2 archivos + X-API-Key",
        "Sección AI Gateway documenta LiteLLM, virtual keys, bypass dev",
        "Security menciona que API key real de OpenAI vive solo en Gateway"
      ],
      "depends_on": ["TASK-16", "TASK-21"]
    },
    {
      "id": "TASK-19",
      "title": "Dockerfile de LegalDiff AI",
      "description": "Crear Dockerfile con Python 3.10-slim. Instala dependencias, copia src/ y migrations/. Expone 8000.",
      "files": ["Dockerfile"],
      "inputs": "requirements.txt, src/, migrations/",
      "outputs": "Imagen Docker lista para build",
      "acceptance_criteria": [
        "Base image: python:3.10-slim",
        "WORKDIR /app",
        "Copia requirements.txt primero (cache de layers)",
        "RUN pip install --no-cache-dir",
        "Copia src/ y migrations/ después de instalar deps",
        "Copia alembic.ini",
        "EXPOSE 8000",
        "CMD uvicorn src.main:app --host 0.0.0.0 --port 8000",
        "docker build -t legaldiff-ai . exitoso"
      ],
      "depends_on": ["TASK-16", "TASK-27"]
    },
    {
      "id": "TASK-20",
      "title": "Docker Compose raíz (app + postgres)",
      "description": "Crear docker-compose.yml con servicios app y postgres. Healthcheck en ambos. app depends_on postgres con condition: service_healthy.",
      "files": ["docker-compose.yml"],
      "inputs": "Dockerfile de TASK-19",
      "outputs": "Stack completo levantable con docker compose up",
      "acceptance_criteria": [
        "Servicio app: puerto 8000:8000, env_file .env",
        "Servicio app: depends_on postgres con condition: service_healthy",
        "Servicio app: healthcheck con curl /health",
        "Servicio postgres: imagen postgres:16-alpine, healthcheck con pg_isready",
        "Volume pgdata para persistencia",
        "docker compose up levanta ambos servicios en orden correcto",
        "curl http://localhost:8000/health → 200"
      ],
      "depends_on": ["TASK-19", "TASK-30"]
    },
    {
      "id": "TASK-21",
      "title": "AI Gateway — config.yaml",
      "description": "Crear gateway/config.yaml con modelo primario gpt-4o, fallback gpt-4o-mini, virtual keys con budgets, rate limiting y alertas al 80%.",
      "files": ["gateway/config.yaml"],
      "inputs": "ADR del AI Gateway",
      "outputs": "config.yaml completo para LiteLLM Proxy",
      "acceptance_criteria": [
        "model_list incluye gpt-4o como primario y gpt-4o-mini como fallback",
        "litellm_settings.fallbacks configurado",
        "Virtual key sk-legaldiff-dev con max_budget $10",
        "Virtual key sk-legaldiff-prod con max_budget $50",
        "Rate limiting RPM/TPM por key",
        "Alertas al 80% de budget",
        "YAML válido"
      ],
      "depends_on": []
    },
    {
      "id": "TASK-22",
      "title": "AI Gateway — docker-compose.yml",
      "description": "Crear gateway/docker-compose.yml con servicios litellm y postgres dedicado. Puerto 4000 accesible desde host.",
      "files": ["gateway/docker-compose.yml"],
      "inputs": "gateway/config.yaml de TASK-21",
      "outputs": "Stack del Gateway levantable desde gateway/",
      "acceptance_criteria": [
        "Servicio litellm: ghcr.io/berriai/litellm, puerto 4000:4000",
        "Monta config.yaml como volumen",
        "depends_on postgres con healthcheck",
        "curl http://localhost:4000/health → OK"
      ],
      "depends_on": ["TASK-21"]
    },
    {
      "id": "TASK-23",
      "title": "AI Gateway — .env.example",
      "description": "Crear gateway/.env.example con variables requeridas sin valores reales.",
      "files": ["gateway/.env.example"],
      "inputs": "ADR del Gateway",
      "outputs": "Template .env para el Gateway — se commitea",
      "acceptance_criteria": [
        "Contiene OPENAI_API_KEY= (vacío)",
        "Contiene LITELLM_MASTER_KEY= (vacío)",
        "Contiene DATABASE_URL=postgresql://litellm:litellm@postgres:5432/litellm",
        "Contiene LITELLM_LOG=INFO",
        "Sin valores reales — seguro para commitear"
      ],
      "depends_on": []
    },
    {
      "id": "TASK-24",
      "title": "AI Gateway — README.md",
      "description": "Crear gateway/README.md con propósito, setup en 3 pasos, cómo agregar proyectos, rotación de keys, bypass dev, endpoints y portabilidad.",
      "files": ["gateway/README.md"],
      "inputs": "ADR del Gateway completo",
      "outputs": "Documentación completa del Gateway",
      "acceptance_criteria": [
        "Propósito en 2-3 frases",
        "Setup en máximo 3 pasos",
        "Documenta cómo agregar proyecto consumidor",
        "Documenta rotación de virtual keys",
        "Documenta bypass para dev",
        "Lista 3 endpoints: proxy :4000, dashboard :4000/ui, health :4000/health",
        "Explica portabilidad: copiar gateway/"
      ],
      "depends_on": ["TASK-22"]
    },
    {
      "id": "TASK-25",
      "title": "Actualizar .env.example de LegalDiff",
      "description": "Actualizar .env.example raíz con OPENAI_BASE_URL apuntando al Gateway, OPENAI_API_KEY como virtual key, y LEGALDIFF_API_KEY. Comentarios explicando bypass.",
      "files": [".env.example"],
      "inputs": ".env.example actual, ADR del Gateway",
      "outputs": ".env.example actualizado",
      "acceptance_criteria": [
        "OPENAI_API_KEY=sk-legaldiff-dev",
        "OPENAI_BASE_URL=http://localhost:4000",
        "LEGALDIFF_API_KEY= (vacío — el usuario pone su key)",
        "Comentario: para bypass comentar OPENAI_BASE_URL",
        "Sin API keys reales"
      ],
      "depends_on": ["TASK-21"]
    },
    {
      "id": "TASK-26",
      "title": "Actualizar .gitignore con Gateway",
      "description": "Agregar gateway/.env al .gitignore. Verificar que gateway/.env.example NO esté ignorado.",
      "files": [".gitignore"],
      "inputs": ".gitignore actual",
      "outputs": ".gitignore con regla para gateway/.env",
      "acceptance_criteria": [
        "gateway/.env está ignorado",
        "gateway/.env.example NO está ignorado",
        ".env raíz sigue ignorado",
        "No se eliminaron reglas existentes"
      ],
      "depends_on": []
    },
    {
      "id": "TASK-32",
      "title": "README.md del proyecto principal",
      "description": "Crear README.md raíz con: qué es LegalDiff AI, diagrama ASCII del pipeline, requisitos previos (Docker, Python 3.10+), setup local en 5 pasos, endpoints con ejemplos de curl usando multipart upload y X-API-Key, link a gateway/README.md, y tabla de variables de entorno.",
      "files": ["README.md"],
      "inputs": "ADRs completos, endpoints implementados",
      "outputs": "README.md completo y usable por un developer nuevo",
      "acceptance_criteria": [
        "Describe el proyecto en 3 frases",
        "Diagrama ASCII del pipeline: image_parser → ctx_agent → extraction_agent",
        "Setup local en máximo 5 pasos desde cero",
        "Ejemplo de curl para POST /analyze con multipart (--form) y X-API-Key",
        "Ejemplo de curl para GET /analyses con X-API-Key",
        "Ejemplo de curl para GET /health",
        "Link a gateway/README.md",
        "Tabla de variables de entorno requeridas"
      ],
      "depends_on": ["TASK-17", "TASK-24"]
    }
  ]
}
```

## Grafo de dependencias

```
════════════════════════════════════════════════════════════════════════
                    SIN DEPENDENCIAS (Paralelo 1) — 8 tareas
════════════════════════════════════════════════════════════════════════
TASK-01 (inits)           TASK-05 (deps)          TASK-08 (prompt parser)
TASK-11 (prompt ctx)      TASK-13 (prompt ext)    TASK-21 (gw config)
TASK-23 (gw .env.example) TASK-26 (gitignore gw)

════════════════════════════════════════════════════════════════════════
                    LEGALDIFF AI — cadena principal
════════════════════════════════════════════════════════════════════════
TASK-01 → TASK-02 (config) ──┬── TASK-28 (auth)
                             ├── TASK-29 (logging)
                             └── TASK-03 (database) → TASK-04 (models)
                                                          │
                    ┌─────────────────────────────────────┤
                    ▼                                     ▼
              TASK-06 (conftest)                    TASK-14 (ext agent)
                    │                               TASK-27 (alembic)
                    ▼
              TASK-07 (test_models)

TASK-02 + TASK-08 → TASK-09 (image_parser bytes) ───────┐
TASK-02 + TASK-11 → TASK-12 (ctx agent) ─────────────────┤
                                                          │
TASK-09 + TASK-06 → TASK-10 (test_image_parser)          │
TASK-12 + TASK-14 + TASK-06 → TASK-15 (test_agents)      │
                                                          │
TASK-04 + TASK-09 + TASK-12 + TASK-14                     │
     + TASK-27 + TASK-28 + TASK-29 → TASK-16 (main.py) ──┤
                                          │               │
                    ┌──────────┬──────────┤               │
                    ▼          ▼          ▼               │
              TASK-30      TASK-31    TASK-19 (Dockerfile) │
              (health)     (paginación)   │               │
                    │          │          ▼               │
                    └──────────┴── TASK-17 (test_main)    │
                                         │               │
                                   TASK-20 (docker-compose)
                                         │
              TASK-18 (CLAUDE.md) ◄── TASK-16 + TASK-21   │
                                                          │
                              TASK-32 (README) ◄── TASK-17 + TASK-24

════════════════════════════════════════════════════════════════════════
                    AI GATEWAY — cadena independiente
════════════════════════════════════════════════════════════════════════
TASK-21 (config.yaml) → TASK-22 (gw docker-compose) → TASK-24 (gw README)
TASK-21 → TASK-25 (actualizar .env.example LegalDiff)
TASK-23 (gw .env.example) ── independiente
TASK-26 (gitignore gw) ── independiente
```

## Caminos críticos

**LegalDiff AI** (más largo):
```
TASK-01 → 02 → 03 → 04 → 27 (alembic) ─┐
                     02 → 28 (auth) ─────┤
                     02 → 29 (logging) ──┤
                                         └→ TASK-16 → 30 + 31 → 17 → 32
```

**AI Gateway**:
```
TASK-21 → 22 → 24 → 32 (README depende de ambos)
```

## Tareas paralelizables

- **Paralelo 1** (sin deps): TASK-01, 05, 08, 11, 13, 21, 23, 26
- **Paralelo 2** (después de TASK-02): TASK-09 ∥ TASK-12 ∥ TASK-28 ∥ TASK-29
- **Paralelo 3** (después de TASK-04): TASK-06 ∥ TASK-14 ∥ TASK-27
- **Paralelo 4** (después de TASK-16): TASK-17 ∥ TASK-18 ∥ TASK-19 ∥ TASK-30 ∥ TASK-31
- **Gateway paralelo** (independiente): TASK-21 → 22 → 24, TASK-23, TASK-25, TASK-26

## Datos de prueba

Los 3 pares de contratos de prueba están en `data/test_contracts/` (en .gitignore — nunca se commitean):

| Par | Original | Enmienda | Tipo | Cambios esperados |
|-----|----------|----------|------|-------------------|
| 1 | `documento_1__original.jpg` | `documento_1__enmienda.jpg` | Licencia Software (TechNova/DataBridge) | Plazo 12→24, Pago 12k→15k, Soporte email→email+chat, Terminación 30→60, nueva Protección de Datos |
| 2 | `documento_2__original.jpg` | `documento_2__enmienda.jpg` | Consultoría (Orion/GreenWave) | Alcance +regulatorio, Duración 6→9, Honorarios 8k→9.5k, Entregables mensuales→quincenales, nueva Propiedad Intelectual |
| 3 | `documento_3__original.jpg` | `documento_3__enmienda.jpg` | SaaS (CloudMetrics/RetailPulse) | Precio 1.200→1.250, Disponibilidad 99.5%→99.9%, Soporte email→email+tickets |

**Nota**: Los nombres de archivo usan doble guion bajo (`__`) entre el número y el tipo.

## Verificación end-to-end (después de TODAS las tareas)

1. Levantar Gateway: `cd gateway && docker compose up -d`
2. Verificar health: `curl http://localhost:4000/health`
3. Levantar LegalDiff: `docker compose up -d` (raíz)
4. Verificar health: `curl http://localhost:8000/health`
5. POST /analyze — **Par 1** (Licencia Software):
   ```bash
   curl -X POST http://localhost:8000/analyze \
     -H "X-API-Key: $LEGALDIFF_API_KEY" \
     -F "original_file=@data/test_contracts/documento_1__original.jpg" \
     -F "amendment_file=@data/test_contracts/documento_1__enmienda.jpg"
   ```
6. Verificar Par 1 incluye: Plazo 12→24, Pago 12k→15k, Soporte email→email+chat, Terminación 30→60, nueva Protección de Datos
7. POST /analyze — **Par 2** (Consultoría):
   ```bash
   curl -X POST http://localhost:8000/analyze \
     -H "X-API-Key: $LEGALDIFF_API_KEY" \
     -F "original_file=@data/test_contracts/documento_2__original.jpg" \
     -F "amendment_file=@data/test_contracts/documento_2__enmienda.jpg"
   ```
8. Verificar Par 2 incluye: Alcance +regulatorio, Duración 6→9, Honorarios 8k→9.5k, Entregables mensuales→quincenales, nueva Propiedad Intelectual
9. POST /analyze — **Par 3** (SaaS):
   ```bash
   curl -X POST http://localhost:8000/analyze \
     -H "X-API-Key: $LEGALDIFF_API_KEY" \
     -F "original_file=@data/test_contracts/documento_3__original.jpg" \
     -F "amendment_file=@data/test_contracts/documento_3__enmienda.jpg"
   ```
10. Verificar Par 3 incluye: Precio 1.200→1.250, Disponibilidad 99.5%→99.9%, Soporte email→email+tickets
11. GET /analyses → 3 registros persistidos con paginación
12. Dashboard Langfuse → 3 traces "contract-analysis" con 4 spans cada uno
13. Dashboard LiteLLM (:4000/ui) → logs de uso por virtual key
14. Verificar X-Request-ID en response headers
