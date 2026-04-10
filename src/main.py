import subprocess
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import structlog
from fastapi import Depends, FastAPI, HTTPException, Query, UploadFile
from langfuse import observe
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from src.agents.contextualization_agent import run as run_contextualization
from src.agents.extraction_agent import run as run_extraction
from src.auth import verify_api_key
from src.config import validate_env
from src.database import Base, get_db, get_engine
from src.image_parser import parse_contract_image
from src.logging_config import RequestIDMiddleware, configure_logging, request_id_ctx
from src.models import (
    AnalysisRecord,
    AnalysisRecordResponse,
    AnalyzeResponse,
    PaginatedAnalysesResponse,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: configura logging, corre migraciones, valida entorno."""
    configure_logging()
    validate_env()

    # Correr migraciones con Alembic
    try:
        subprocess.run(
            ["alembic", "upgrade", "head"],
            check=True,
            capture_output=True,
            text=True,
        )
        await logger.ainfo("alembic_migrations_applied")
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Fallback: create_all para SQLite en tests o si Alembic no está disponible
        Base.metadata.create_all(bind=get_engine())
        await logger.awarning("alembic_not_available_using_create_all")

    await logger.ainfo("legaldiff_ai_started")
    yield


app = FastAPI(title="LegalDiff AI", version="0.1.0", lifespan=lifespan)
app.add_middleware(RequestIDMiddleware)


@observe(name="contract-analysis")
def _run_pipeline(
    original_bytes: bytes,
    original_name: str,
    amendment_bytes: bytes,
    amendment_name: str,
) -> tuple[dict, int]:
    """Ejecuta el pipeline secuencial con tracing de Langfuse via @observe."""
    total_tokens = 0

    # Span 1 + 2: parse ambas imágenes
    original_text, tokens_orig = parse_contract_image(original_bytes, original_name)
    total_tokens += tokens_orig

    amendment_text, tokens_amend = parse_contract_image(amendment_bytes, amendment_name)
    total_tokens += tokens_amend

    # Span 3: contextualization
    context_map, tokens_ctx = run_contextualization(original_text, amendment_text)
    total_tokens += tokens_ctx

    # Span 4: extraction
    result, tokens_ext = run_extraction(context_map, original_text, amendment_text)
    total_tokens += tokens_ext

    return result.model_dump(), total_tokens


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    original_file: UploadFile,
    amendment_file: UploadFile,
    db: Session = Depends(get_db),
    _auth: None = Depends(verify_api_key),
) -> AnalyzeResponse:
    """Ejecuta el pipeline completo de análisis de cambios contractuales."""
    start_time = time.time()

    # Leer bytes en memoria — no guardar en disco
    original_bytes = await original_file.read()
    amendment_bytes = await amendment_file.read()
    original_name = original_file.filename or "original.jpg"
    amendment_name = amendment_file.filename or "amendment.jpg"

    try:
        result_dict, total_tokens = _run_pipeline(
            original_bytes, original_name, amendment_bytes, amendment_name
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Error en pipeline de análisis",
                "message": str(e),
                "request_id": request_id_ctx.get(""),
            },
        ) from e

    latency_ms = int((time.time() - start_time) * 1000)

    record = AnalysisRecord(
        original_filename=original_name,
        amendment_filename=amendment_name,
        result=result_dict,
        tokens_used=total_tokens,
        latency_ms=latency_ms,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    from src.models import ContractChangeOutput

    return AnalyzeResponse(
        analysis_id=record.id,
        result=ContractChangeOutput.model_validate(result_dict),
    )


@app.get("/analyses", response_model=PaginatedAnalysesResponse)
def list_analyses(
    limit: int = Query(default=20, le=100, ge=1),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _auth: None = Depends(verify_api_key),
) -> PaginatedAnalysesResponse:
    """Lista análisis anteriores para auditoría con paginación."""
    total = db.query(func.count(AnalysisRecord.id)).scalar() or 0
    records = (
        db.query(AnalysisRecord)
        .order_by(AnalysisRecord.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return PaginatedAnalysesResponse(
        items=[AnalysisRecordResponse.model_validate(r) for r in records],
        total=total,
        limit=limit,
        offset=offset,
    )


@app.get("/health")
def health_check(db: Session = Depends(get_db)) -> dict:
    """Health check con verificación de DB."""
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "ok",
            "version": "0.1.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "version": "0.1.0",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        ) from e


if __name__ == "__main__":
    import argparse
    import json as json_module
    import sys
    from pathlib import Path

    configure_logging()
    validate_env()

    parser = argparse.ArgumentParser(description="LegalDiff AI — Análisis de cambios contractuales")
    parser.add_argument("original", help="Path a la imagen del contrato original (JPEG/PNG)")
    parser.add_argument("amendment", help="Path a la imagen de la enmienda (JPEG/PNG)")
    args = parser.parse_args()

    original_path = Path(args.original)
    amendment_path = Path(args.amendment)

    if not original_path.exists():
        print(f"Error: archivo no encontrado: {original_path}", file=sys.stderr)
        sys.exit(1)
    if not amendment_path.exists():
        print(f"Error: archivo no encontrado: {amendment_path}", file=sys.stderr)
        sys.exit(1)

    result_dict, total_tokens = _run_pipeline(
        original_path.read_bytes(),
        original_path.name,
        amendment_path.read_bytes(),
        amendment_path.name,
    )

    print(json_module.dumps(result_dict, indent=2, ensure_ascii=False))
    print(f"\nTokens totales: {total_tokens}", file=sys.stderr)

    Langfuse().flush()
