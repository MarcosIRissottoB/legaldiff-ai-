# LegalDiff AI

Sistema multi-agente que reemplaza 40 horas semanales de revision manual de contratos en LegalMove. Recibe imagenes escaneadas (JPEG/PNG) de un contrato original y su enmienda, detecta todos los cambios entre ambos documentos, y devuelve un JSON estructurado y validado con trazabilidad completa via Langfuse.

## Que hace

1. Recibe 2 imagenes (contrato original + enmienda) via CLI o API REST
2. Extrae el texto legal de cada imagen usando GPT-4o Vision
3. Un primer agente (ContextualizationAgent) mapea la estructura de ambos documentos — orquestado con LangChain
4. Un segundo agente (ExtractionAgent) detecta todos los cambios entre ambos — orquestado con LangChain
5. Valida el resultado con Pydantic (`model_validate()`) y devuelve un JSON estructurado
6. Registra cada paso en Langfuse con trazabilidad completa (spans jerarquicos)
7. Persiste el resultado en PostgreSQL para auditoria (modo API)

## Arquitectura

```
                         LegalDiff AI (:8000)
                         ==================

  POST /analyze
  (2 imagenes JPG)
        |
        v
  +------------------+     +---------------------------+
  | image_parser     |---->| ContextualizationAgent    |
  | (GPT-4o Vision)  |     | Mapea secciones y         |
  | original + amend.|     | correspondencias.         |
  +------------------+     | NO detecta cambios.       |
                           +---------------------------+
                                      |
                                      v
                           +---------------------------+
                           | ExtractionAgent           |
                           | Recibe mapa + textos.     |
                           | Detecta adiciones,        |
                           | eliminaciones y cambios.  |
                           +---------------------------+
                                      |
                                      v
                           +---------------------------+
                           | ContractChangeOutput      |
                           | - sections_changed        |
                           | - topics_touched          |
                           | - summary_of_the_change   |
                           +---------------------------+
                                      |
                                      v
                              PostgreSQL (auditoria)
```

### Por que handoff secuencial

El ExtractionAgent necesita el contexto estructurado del ContextualizationAgent para reducir alucinaciones. Procesar en paralelo produciria resultados menos precisos en documentos legales complejos.

## Estructura del proyecto

```
legaldiff-ai/
├── src/
│   ├── main.py                  # FastAPI entry point + orquestador
│   ├── config.py                # Variables de entorno + validacion
│   ├── database.py              # SQLAlchemy engine + session
│   ├── models.py                # Pydantic schemas + SQLAlchemy model
│   ├── auth.py                  # Autenticacion X-API-Key
│   ├── logging_config.py        # structlog + middleware X-Request-ID
│   ├── image_parser.py          # GPT-4o Vision: imagen -> texto
│   ├── agents/
│   │   ├── contextualization_agent.py  # Mapea estructura de documentos
│   │   └── extraction_agent.py         # Detecta cambios contractuales
│   └── prompts/
│       ├── image_parser.txt              # Prompt de extraccion de texto
│       ├── contextualization_agent.txt   # Prompt del analista senior
│       └── extraction_agent.txt          # Prompt del auditor legal
├── tests/
│   ├── conftest.py              # Fixtures con contratos reales
│   ├── test_models.py           # Validacion de schemas Pydantic
│   ├── test_image_parser.py     # Parser con bytes reales + mocks OpenAI
│   ├── test_agents.py           # Ambos agentes con mocks
│   └── test_main.py             # Endpoints con TestClient
├── migrations/
│   ├── env.py                   # Config de Alembic
│   └── versions/                # Migraciones de DB
├── gateway/                     # AI Gateway (LiteLLM Proxy)
│   ├── config.yaml              # Modelos, virtual keys, budgets
│   ├── docker-compose.yml       # LiteLLM + PostgreSQL
│   └── README.md                # Documentacion del Gateway
├── data/
│   └── test_contracts/          # JPGs de prueba (gitignored)
├── Dockerfile
├── docker-compose.yml           # App + PostgreSQL
├── alembic.ini
├── requirements.txt
├── ADR.json                     # Architecture Decision Record
└── CLAUDE.md                    # Instrucciones para Claude Code
```

## Requisitos

- Python 3.11+ (**no** usar el `python3` del sistema — en macOS suele ser 3.9 y el código usa sintaxis 3.10+)
- Docker y Docker Compose
- API key de OpenAI con acceso a GPT-4o
- Cuenta en [Langfuse](https://cloud.langfuse.com) (gratis)

## Instalacion

### 1. Clonar y entrar al directorio

```bash
git clone <repo-url>
cd legaldiff-ai
```

### 2. Crear virtualenv con Python 3.11+

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> **Importante**: NO usar `python3` directamente — en macOS es 3.9.x y el codigo usa `str | None` (3.10+). Siempre activar el venv antes de trabajar.

### 3. Configurar variables de entorno

```bash
cp .env.example .env
cp gateway/.env.example gateway/.env
```

Editar `.env` (raiz) con tus valores:

```
OPENAI_API_KEY=sk-legaldiff-dev          # virtual key del Gateway
OPENAI_BASE_URL=http://localhost:4000    # apunta al Gateway
LANGFUSE_PUBLIC_KEY=pk-lf-...           # desde cloud.langfuse.com
LANGFUSE_SECRET_KEY=sk-lf-...           # desde cloud.langfuse.com
LANGFUSE_HOST=https://cloud.langfuse.com
DATABASE_URL=postgresql://legaldiff:legaldiff@localhost:5432/legaldiff
LEGALDIFF_API_KEY=tu-api-key-inventada
```

Editar `gateway/.env`:

```
OPENAI_API_KEY=sk-proj-...              # tu key REAL de OpenAI
LITELLM_MASTER_KEY=sk-master-...        # inventala
DATABASE_URL=postgresql://litellm:litellm@postgres:5432/litellm
LITELLM_LOG=INFO
```

> **Tip**: si no queres usar el Gateway por ahora, comenta `OPENAI_BASE_URL` y pone tu key real de OpenAI directo en `OPENAI_API_KEY` del `.env` raiz.

### 4. Colocar imagenes de prueba

Los JPGs de contratos van en `data/test_contracts/` (estan en .gitignore, nunca se commitean):

```
data/test_contracts/
├── documento_1__original.jpg
├── documento_1__enmienda.jpg
├── documento_2__original.jpg
├── documento_2__enmienda.jpg
├── documento_3__original.jpg
└── documento_3__enmienda.jpg
```

## Levantar con Docker

```bash
# Build
docker compose build

# Levantar (app + postgres)
docker compose up -d

# Verificar
curl http://localhost:8000/health
```

Para levantar tambien el AI Gateway:

```bash
cd gateway && docker compose up -d && cd ..
```

### Verificar que todo esta corriendo

```bash
docker compose ps                              # app + postgres
cd gateway && docker compose ps && cd ..       # gateway
curl http://localhost:8000/health               # app health
curl http://localhost:4000/health               # gateway health
```

## Levantar sin Docker (desarrollo local)

```bash
# Activar venv (creado en paso 2)
source .venv/bin/activate

# PostgreSQL local (si usas brew)
brew services start postgresql
createdb legaldiff

# Correr migraciones
alembic upgrade head

# Levantar
uvicorn src.main:app --reload --port 8000
```

## Stack tecnico

| Componente | Tecnologia |
|-----------|------------|
| LLM | GPT-4o Vision via LangChain (`ChatOpenAI` de `langchain-openai`) |
| Orquestacion de agentes | LangChain (`SystemMessage`, `HumanMessage`, `ChatOpenAI`) |
| Validacion | Pydantic v2 con `model_validate()` explicito |
| Observabilidad | Langfuse v4 con `@observe` decorator + OpenTelemetry |
| API | FastAPI + uvicorn (multipart/form-data upload) |
| DB | PostgreSQL + SQLAlchemy + Alembic |
| Testing | pytest con fixtures de contratos reales + mocks |

## Como usar

### Opcion 1 — CLI (script directo)

```bash
python src/main.py data/test_contracts/documento_1__original.jpg data/test_contracts/documento_1__enmienda.jpg
```

Imprime el JSON resultado en stdout y los tokens usados en stderr.

### Opcion 2 — API REST

```bash
curl -X POST http://localhost:8000/analyze \
  -H "X-API-Key: $LEGALDIFF_API_KEY" \
  -F "original_file=@data/test_contracts/documento_1__original.jpg" \
  -F "amendment_file=@data/test_contracts/documento_1__enmienda.jpg"
```

Respuesta:

```json
{
  "analysis_id": "uuid-del-analisis",
  "result": {
    "sections_changed": ["Clausula 2 - Plazo", "Clausula 3 - Pago", "..."],
    "topics_touched": ["Duracion", "Condiciones economicas", "..."],
    "summary_of_the_change": "Se extiende el plazo de 12 a 24 meses..."
  }
}
```

### Listar analisis anteriores

```bash
curl "http://localhost:8000/analyses?limit=10&offset=0" \
  -H "X-API-Key: $LEGALDIFF_API_KEY"
```

### Health check

```bash
curl http://localhost:8000/health
```

No requiere autenticacion. Retorna `{"status": "ok"}` si la app y la DB estan sanas.

## Como probar

### Tests automatizados (29 tests)

```bash
source .venv/bin/activate
pytest tests/ -v
```

Los tests usan SQLite in-memory y mockean las llamadas a OpenAI. No necesitan Docker, API keys, ni conexion a internet.

### Tests manuales con contratos reales

Ver [MANUAL-TEST.md](MANUAL-TEST.md) para el paso a paso completo con los 3 pares de contratos de prueba.

Los cambios esperados por par:

**Par 1 — Licencia de Software** (TechNova / DataBridge):
- Plazo: 12 -> 24 meses
- Pago: USD 12.000 -> 15.000
- Soporte: email -> email + chat
- Terminacion: 30 -> 60 dias
- Nueva clausula: Proteccion de Datos

**Par 2 — Consultoria** (Orion / GreenWave):
- Alcance: +analisis regulatorio
- Duracion: 6 -> 9 meses
- Honorarios: USD 8.000 -> 9.500
- Entregables: mensuales -> quincenales
- Nueva clausula: Propiedad Intelectual

**Par 3 — SaaS** (CloudMetrics / RetailPulse):
- Precio: USD 1.200 -> 1.250
- Disponibilidad: 99,5% -> 99,9%
- Soporte: email -> email + tickets

## Variables de entorno

### .env (raiz) — LegalDiff AI

| Variable | Requerida | Descripcion |
|----------|-----------|-------------|
| `OPENAI_API_KEY` | Si | Virtual key del Gateway o key real de OpenAI |
| `OPENAI_BASE_URL` | No | URL del AI Gateway. Comentar para bypass |
| `LANGFUSE_PUBLIC_KEY` | Si | Public key de Langfuse |
| `LANGFUSE_SECRET_KEY` | Si | Secret key de Langfuse |
| `LANGFUSE_HOST` | Si | Host de Langfuse |
| `DATABASE_URL` | Si | URL de PostgreSQL |
| `LEGALDIFF_API_KEY` | No | API key para autenticacion de clientes |

### gateway/.env — AI Gateway

| Variable | Requerida | Descripcion |
|----------|-----------|-------------|
| `OPENAI_API_KEY` | Si | Key REAL de OpenAI (la unica copia) |
| `LITELLM_MASTER_KEY` | Si | Key de admin del Gateway |
| `DATABASE_URL` | Si | PostgreSQL del Gateway |
| `LITELLM_LOG` | No | Nivel de log (default: INFO) |

## AI Gateway

LiteLLM Proxy centraliza todas las llamadas a OpenAI. La key real vive solo en el Gateway. Los proyectos usan virtual keys con budgets y rate limits.

- **Proxy**: http://localhost:4000
- **Dashboard**: http://localhost:4000/ui (metricas y costos)
- **Portabilidad**: copiar `gateway/` a otro proyecto

Ver [gateway/README.md](gateway/README.md) para documentacion completa.

## Trazabilidad con Langfuse

Cada ejecucion del pipeline genera una traza jerarquica en Langfuse:

```
contract-analysis (trace raiz — @observe)
  ├── parse_contract_image (span — original)
  │   └── GPT-4o Vision (generation — langfuse.openai drop-in)
  ├── parse_contract_image (span — enmienda)
  │   └── GPT-4o Vision (generation — langfuse.openai drop-in)
  ├── contextualization-agent (span — @observe)
  │   └── ChatOpenAI (generation — LangChain)
  └── extraction-agent (span — @observe)
      └── ChatOpenAI (generation — LangChain)
```

Cada span registra: inputs, outputs, latencia y tokens. Visible en el dashboard de Langfuse (`cloud.langfuse.com`).

## Decisiones de arquitectura

Las decisiones tecnicas estan documentadas en [ADR.json](ADR.json) y [gateway/ADR.json](gateway/ADR.json). Resumen:

- **GPT-4o Vision** sobre OCR tradicional: un solo modelo para extraccion + analisis
- **Handoff secuencial**: el ExtractionAgent necesita contexto del primero para reducir alucinaciones
- **model_validate() explicito**: mas control sobre errores de validacion que response_format directo
- **Prompts en archivos .txt**: el equipo de producto puede iterar sin tocar codigo
- **Multipart upload**: bytes en memoria, no se persisten en disco (max 20MB)
- **tenacity retry**: 3 intentos con exponential backoff para llamadas a OpenAI
- **Alembic**: migraciones de DB en produccion (no create_all)
- **Virtual keys**: la API key real de OpenAI nunca sale del Gateway

## Seguridad

- La API key real de OpenAI vive **solo** en `gateway/.env`
- `.env` y `gateway/.env` estan en `.gitignore` — nunca se commitean
- Las imagenes de contratos en `data/test_contracts/` estan en `.gitignore`
- La app **nunca** loggea contenido de contratos, solo metadata (filename, tokens, latencia, request_id)
- Autenticacion via `X-API-Key` header con comparacion segura (`secrets.compare_digest`)
- Archivos se leen en memoria y se descartan — no se persisten en disco
