import uuid
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.types import JSON, TypeDecorator

from src.database import Base

# --- SQLAlchemy: tipo UUID compatible con PostgreSQL y SQLite ---


class UUIDType(TypeDecorator):
    """UUID que funciona con PostgreSQL (nativo) y SQLite (string)."""

    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value: uuid.UUID | str | None, dialect) -> str | None:
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return str(value)
        return value

    def process_result_value(self, value: str | None, dialect) -> uuid.UUID | None:
        if value is None:
            return None
        return uuid.UUID(value)


# --- Pydantic: output del pipeline ---


class ContractChangeOutput(BaseModel):
    sections_changed: list[str]
    topics_touched: list[str]
    summary_of_the_change: str


# --- Pydantic: response de la API ---


class AnalyzeResponse(BaseModel):
    analysis_id: uuid.UUID
    result: ContractChangeOutput


class AnalysisRecordResponse(BaseModel):
    id: uuid.UUID
    created_at: datetime
    original_filename: str
    amendment_filename: str
    result: ContractChangeOutput
    tokens_used: int
    latency_ms: int

    model_config = {"from_attributes": True}


class PaginatedAnalysesResponse(BaseModel):
    items: list[AnalysisRecordResponse]
    total: int
    limit: int
    offset: int


# --- SQLAlchemy: persistencia ---


class AnalysisRecord(Base):
    __tablename__ = "analysis_records"

    id = Column(UUIDType(), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    original_filename = Column(String, nullable=False)
    amendment_filename = Column(String, nullable=False)
    result = Column(JSON, nullable=False)
    tokens_used = Column(Integer, nullable=False, default=0)
    latency_ms = Column(Integer, nullable=False, default=0)
