# LegalDiff AI

Multi-agent system designed to replace ~40 hours per week of manual contract review for a legal-services firm. It takes scanned images (JPEG/PNG) of an original contract and its amendment, detects every change between the two documents, and returns a structured, validated JSON with full traceability through Langfuse.

## What it does

1. Receives 2 images (original contract + amendment) via CLI or REST API
2. Extracts the legal text from each image using GPT-4o Vision
3. A first agent (ContextualizationAgent) maps the structure of both documents — orchestrated with LangChain
4. A second agent (ExtractionAgent) detects every change between them — orchestrated with LangChain
5. Validates the result with Pydantic (`model_validate()`) and returns structured JSON
6. Logs every step in Langfuse with full traceability (hierarchical spans)
7. Persists the result in PostgreSQL for auditing (API mode)

## Architecture

```
                         LegalDiff AI (:8000)
                         ==================

  POST /analyze
  (2 JPG images)
        |
        v
  +------------------+     +---------------------------+
  | image_parser     |---->| ContextualizationAgent    |
  | (GPT-4o Vision)  |     | Maps sections and         |
  | original + amend.|     | correspondences.          |
  +------------------+     | Does NOT detect changes.  |
                           +---------------------------+
                                      |
                                      v
                           +---------------------------+
                           | ExtractionAgent           |
                           | Receives map + texts.     |
                           | Detects additions,        |
                           | deletions and changes.    |
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
                              PostgreSQL (audit)
```

### Why a sequential handoff

The ExtractionAgent needs the structured context produced by the ContextualizationAgent to reduce hallucinations. Processing both in parallel would produce less accurate results on complex legal documents.

## Project structure

```
legaldiff-ai/
├── src/
│   ├── main.py                  # FastAPI entry point + orchestrator
│   ├── config.py                # Environment variables + validation
│   ├── database.py              # SQLAlchemy engine + session
│   ├── models.py                # Pydantic schemas + SQLAlchemy model
│   ├── auth.py                  # X-API-Key authentication
│   ├── logging_config.py        # structlog + X-Request-ID middleware
│   ├── image_parser.py          # GPT-4o Vision: image -> text
│   ├── agents/
│   │   ├── contextualization_agent.py  # Maps document structure
│   │   └── extraction_agent.py         # Detects contract changes
│   └── prompts/
│       ├── image_parser.txt              # Text extraction prompt
│       ├── contextualization_agent.txt   # Senior analyst prompt
│       └── extraction_agent.txt          # Legal auditor prompt
├── tests/
│   ├── conftest.py              # Fixtures with real contracts
│   ├── test_models.py           # Pydantic schema validation
│   ├── test_image_parser.py     # Parser with real bytes + OpenAI mocks
│   ├── test_agents.py           # Both agents with mocks
│   └── test_main.py             # Endpoints with TestClient
├── migrations/
│   ├── env.py                   # Alembic config
│   └── versions/                # DB migrations
├── gateway/                     # AI Gateway (LiteLLM Proxy)
│   ├── config.yaml              # Models, virtual keys, budgets
│   ├── docker-compose.yml       # LiteLLM + PostgreSQL
│   └── README.md                # Gateway documentation
├── data/
│   └── test_contracts/          # Test JPGs (gitignored)
├── Dockerfile
├── docker-compose.yml           # App + PostgreSQL
├── alembic.ini
├── requirements.txt
├── ADR.json                     # Architecture Decision Record
└── CLAUDE.md                    # Instructions for Claude Code
```

## Requirements

- Python 3.11+ (do **not** use the system `python3` — on macOS it is usually 3.9 and the code uses 3.10+ syntax)
- Docker and Docker Compose
- OpenAI API key with GPT-4o access
- [Langfuse](https://cloud.langfuse.com) account (free)

## Installation

### 1. Clone and enter the directory

```bash
git clone https://github.com/MarcosIRissottoB/legaldiff-ai-.git
cd legaldiff-ai-
```

### 2. Create a virtualenv with Python 3.11+

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> **Important**: do NOT use `python3` directly — on macOS it is 3.9.x and the code uses `str | None` (3.10+). Always activate the venv before working.

### 3. Configure environment variables

```bash
cp .env.example .env
cp gateway/.env.example gateway/.env
```

Edit `.env` (root) with your values:

```
OPENAI_API_KEY=sk-legaldiff-dev          # Gateway virtual key
OPENAI_BASE_URL=http://localhost:4000    # points to the Gateway
LANGFUSE_PUBLIC_KEY=pk-lf-...           # from cloud.langfuse.com
LANGFUSE_SECRET_KEY=sk-lf-...           # from cloud.langfuse.com
LANGFUSE_HOST=https://cloud.langfuse.com
DATABASE_URL=postgresql://legaldiff:legaldiff@localhost:5432/legaldiff
LEGALDIFF_API_KEY=your-made-up-api-key
```

Edit `gateway/.env`:

```
OPENAI_API_KEY=sk-proj-...              # your REAL OpenAI key
LITELLM_MASTER_KEY=sk-master-...        # make one up
DATABASE_URL=postgresql://litellm:litellm@postgres:5432/litellm
LITELLM_LOG=INFO
```

> **Tip**: if you don't want to use the Gateway yet, comment out `OPENAI_BASE_URL` and put your real OpenAI key directly in `OPENAI_API_KEY` in the root `.env`.

### 4. Add test images

Contract JPGs go in `data/test_contracts/` (they are in .gitignore and are never committed):

```
data/test_contracts/
├── documento_1__original.jpg
├── documento_1__enmienda.jpg
├── documento_2__original.jpg
├── documento_2__enmienda.jpg
├── documento_3__original.jpg
└── documento_3__enmienda.jpg
```

## Run with Docker

```bash
# Build
docker compose build

# Start (app + postgres)
docker compose up -d

# Check
curl http://localhost:8000/health
```

To also start the AI Gateway:

```bash
cd gateway && docker compose up -d && cd ..
```

### Check that everything is running

```bash
docker compose ps                              # app + postgres
cd gateway && docker compose ps && cd ..       # gateway
curl http://localhost:8000/health               # app health
curl http://localhost:4000/health               # gateway health
```

## Run without Docker (local development)

```bash
# Activate the venv (created in step 2)
source .venv/bin/activate

# Local PostgreSQL (if you use brew)
brew services start postgresql
createdb legaldiff

# Run migrations
alembic upgrade head

# Start
uvicorn src.main:app --reload --port 8000
```

## Tech stack

| Component | Technology |
|-----------|------------|
| LLM | GPT-4o Vision via LangChain (`ChatOpenAI` from `langchain-openai`) |
| Agent orchestration | LangChain (`SystemMessage`, `HumanMessage`, `ChatOpenAI`) |
| Validation | Pydantic v2 with explicit `model_validate()` |
| Observability | Langfuse v4 with the `@observe` decorator + OpenTelemetry |
| API | FastAPI + uvicorn (multipart/form-data upload) |
| DB | PostgreSQL + SQLAlchemy + Alembic |
| Testing | pytest with real-contract fixtures + mocks |

## Usage

### Option 1 — CLI (direct script)

```bash
python -m src.main data/test_contracts/documento_1__original.jpg data/test_contracts/documento_1__enmienda.jpg
```

Prints the resulting JSON to stdout and the tokens used to stderr.

### Option 2 — REST API

```bash
curl -X POST http://localhost:8000/analyze \
  -H "X-API-Key: $LEGALDIFF_API_KEY" \
  -F "original_file=@data/test_contracts/documento_1__original.jpg" \
  -F "amendment_file=@data/test_contracts/documento_1__enmienda.jpg"
```

Response:

```json
{
  "analysis_id": "analysis-uuid",
  "result": {
    "sections_changed": ["Clause 2 - Term", "Clause 3 - Payment", "..."],
    "topics_touched": ["Duration", "Economic terms", "..."],
    "summary_of_the_change": "The term is extended from 12 to 24 months..."
  }
}
```

### List previous analyses

```bash
curl "http://localhost:8000/analyses?limit=10&offset=0" \
  -H "X-API-Key: $LEGALDIFF_API_KEY"
```

### Health check

```bash
curl http://localhost:8000/health
```

No authentication required. Returns `{"status": "ok"}` if the app and the DB are healthy.

## Testing

### Automated tests (33 tests)

```bash
source .venv/bin/activate
pytest tests/ -v
```

The tests use in-memory SQLite and mock the OpenAI calls. They need no Docker, API keys or internet connection.

### Manual tests with real contracts

See [MANUAL-TEST.md](MANUAL-TEST.md) for the full step-by-step with the 3 test contract pairs.

Expected changes per pair:

**Pair 1 — Software License** (TechNova / DataBridge):
- Term: 12 -> 24 months
- Payment: USD 12,000 -> 15,000
- Support: email -> email + chat
- Termination: 30 -> 60 days
- New clause: Data Protection

**Pair 2 — Consulting** (Orion / GreenWave):
- Scope: + regulatory analysis
- Duration: 6 -> 9 months
- Fees: USD 8,000 -> 9,500
- Deliverables: monthly -> biweekly
- New clause: Intellectual Property

**Pair 3 — SaaS** (CloudMetrics / RetailPulse):
- Price: USD 1,200 -> 1,250
- Availability: 99.5% -> 99.9%
- Support: email -> email + tickets

## Environment variables

### .env (root) — LegalDiff AI

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | Gateway virtual key or real OpenAI key |
| `OPENAI_BASE_URL` | No | AI Gateway URL. Comment out to bypass |
| `LANGFUSE_PUBLIC_KEY` | Yes | Langfuse public key |
| `LANGFUSE_SECRET_KEY` | Yes | Langfuse secret key |
| `LANGFUSE_HOST` | Yes | Langfuse host |
| `DATABASE_URL` | Yes | PostgreSQL URL |
| `LEGALDIFF_API_KEY` | No | API key for client authentication |

### gateway/.env — AI Gateway

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | REAL OpenAI key (the only copy) |
| `LITELLM_MASTER_KEY` | Yes | Gateway admin key |
| `DATABASE_URL` | Yes | Gateway PostgreSQL |
| `LITELLM_LOG` | No | Log level (default: INFO) |

## AI Gateway

LiteLLM Proxy centralizes every call to OpenAI. The real key lives only in the Gateway. Projects use virtual keys with budgets and rate limits.

- **Proxy**: http://localhost:4000
- **Dashboard**: http://localhost:4000/ui (metrics and costs)
- **Portability**: copy `gateway/` into another project

See [gateway/README.md](gateway/README.md) for the full documentation.

## Traceability with Langfuse

Every pipeline run produces a hierarchical trace in Langfuse:

```
contract-analysis (root trace — @observe)
  ├── parse_contract_image (span — original)
  │   └── GPT-4o Vision (generation — langfuse.openai drop-in)
  ├── parse_contract_image (span — amendment)
  │   └── GPT-4o Vision (generation — langfuse.openai drop-in)
  ├── contextualization-agent (span — @observe)
  │   └── ChatOpenAI (generation — LangChain)
  └── extraction-agent (span — @observe)
      └── ChatOpenAI (generation — LangChain)
```

Each span records inputs, outputs, latency and tokens. Visible in the Langfuse dashboard (`cloud.langfuse.com`).

## Architecture decisions

The technical decisions are documented in [ADR.json](ADR.json) and [gateway/ADR.json](gateway/ADR.json). Summary:

- **GPT-4o Vision** over traditional OCR: a single model for extraction + analysis
- **Sequential handoff**: the ExtractionAgent needs the first agent's context to reduce hallucinations
- **Explicit model_validate()**: more control over validation errors than using response_format directly
- **Prompts in .txt files**: the product team can iterate without touching code
- **Multipart upload**: bytes stay in memory and are never persisted to disk (max 20MB)
- **tenacity retry**: 3 attempts with exponential backoff for OpenAI calls
- **Alembic**: DB migrations in production (no create_all)
- **Virtual keys**: the real OpenAI API key never leaves the Gateway

## Security

- The real OpenAI API key lives **only** in `gateway/.env`
- `.env` and `gateway/.env` are in `.gitignore` — never committed
- Contract images in `data/test_contracts/` are in `.gitignore`
- The app **never** logs contract content, only metadata (filename, tokens, latency, request_id)
- Authentication via the `X-API-Key` header with constant-time comparison (`secrets.compare_digest`)
- Startup check that LEGALDIFF_API_KEY is not empty — prevents a bypass through `compare_digest("", "")`
- Error responses do not expose internal details (they are logged on the server, not sent to the client)
- Files are read into memory and discarded — never persisted to disk

### Production hardening (outside the educational scope)

In a real production environment, we would recommend adding:

- **Magic bytes validation**: check that uploaded files are real JPEG/PNG, not just by extension
- **Rate limiting**: limit requests per IP or API key to prevent abuse
- **Prompt injection defense**: sanitize extracted text before passing it as input to the agents
- **Container hardening**: run Docker as a non-root user, distroless image
- **Automatic key rotation**: integrate with a secrets manager (AWS Secrets Manager, Vault)
- **WAF/API Gateway**: protection against common attacks (OWASP) at the edge
