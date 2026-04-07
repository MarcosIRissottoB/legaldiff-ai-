import io
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.database import Base, get_db

# SQLite in-memory con StaticPool: todas las conexiones comparten la misma DB
TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(bind=TEST_ENGINE, autocommit=False, autoflush=False)

API_KEY = "test-api-key"


@pytest.fixture(autouse=True)
def _setup_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://localhost:4000")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "test-pub")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "test-secret")
    monkeypatch.setenv("LANGFUSE_HOST", "http://localhost:3000")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("LEGALDIFF_API_KEY", API_KEY)


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """TestClient con SQLite in-memory."""
    import src.config as config
    import src.database as database

    # Patchear config para tests
    config.DATABASE_URL = "sqlite:///:memory:"
    config.LEGALDIFF_API_KEY = API_KEY
    config.OPENAI_API_KEY = "test-key"
    config.LANGFUSE_PUBLIC_KEY = "test-pub"
    config.LANGFUSE_SECRET_KEY = "test-secret"
    config.LANGFUSE_HOST = "http://localhost:3000"

    # Forzar que get_engine() retorne TEST_ENGINE
    database._engine = TEST_ENGINE
    database._session_factory = None

    from src.main import app

    Base.metadata.create_all(bind=TEST_ENGINE)

    def _override_get_db() -> Generator[Session, None, None]:
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=TEST_ENGINE)
    database._engine = None
    database._session_factory = None


def _make_upload(
    filename: str = "contrato.jpg", content: bytes = b"fake jpg"
) -> tuple[str, io.BytesIO, str]:
    return (filename, io.BytesIO(content), "image/jpeg")


class TestAnalyzeEndpoint:
    @patch("src.main._run_pipeline")
    def test_successful_analysis(
        self,
        mock_pipeline: MagicMock,
        client: TestClient,
        contract_image_bytes: bytes,
    ) -> None:
        mock_pipeline.return_value = (
            {
                "sections_changed": ["Cláusula 2"],
                "topics_touched": ["Plazo"],
                "summary_of_the_change": "Plazo extendido.",
            },
            600,
        )

        response = client.post(
            "/analyze",
            headers={"X-API-Key": API_KEY},
            files={
                "original_file": _make_upload("original.jpg", contract_image_bytes),
                "amendment_file": _make_upload("enmienda.jpg", contract_image_bytes),
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "analysis_id" in data
        assert data["result"]["sections_changed"] == ["Cláusula 2"]

    def test_no_api_key(self, client: TestClient) -> None:
        response = client.post(
            "/analyze",
            files={
                "original_file": _make_upload(),
                "amendment_file": _make_upload(),
            },
        )
        assert response.status_code == 401

    def test_wrong_api_key(self, client: TestClient) -> None:
        response = client.post(
            "/analyze",
            headers={"X-API-Key": "wrong-key"},
            files={
                "original_file": _make_upload(),
                "amendment_file": _make_upload(),
            },
        )
        assert response.status_code == 401

    @patch("src.main._run_pipeline")
    def test_invalid_file_extension(
        self, mock_pipeline: MagicMock, client: TestClient
    ) -> None:
        mock_pipeline.side_effect = ValueError("Formato no soportado: .pdf")

        response = client.post(
            "/analyze",
            headers={"X-API-Key": API_KEY},
            files={
                "original_file": (
                    "contrato.pdf",
                    io.BytesIO(b"fake"),
                    "application/pdf",
                ),
                "amendment_file": _make_upload(),
            },
        )
        assert response.status_code == 422

    @patch("src.main._run_pipeline")
    def test_pipeline_error(
        self, mock_pipeline: MagicMock, client: TestClient
    ) -> None:
        mock_pipeline.side_effect = RuntimeError("API timeout")

        response = client.post(
            "/analyze",
            headers={"X-API-Key": API_KEY},
            files={
                "original_file": _make_upload(),
                "amendment_file": _make_upload(),
            },
        )
        assert response.status_code == 500


class TestListAnalyses:
    def test_empty_list(self, client: TestClient) -> None:
        response = client.get("/analyses", headers={"X-API-Key": API_KEY})
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_no_api_key(self, client: TestClient) -> None:
        response = client.get("/analyses")
        assert response.status_code == 401

    def test_limit_exceeds_max(self, client: TestClient) -> None:
        response = client.get("/analyses?limit=200", headers={"X-API-Key": API_KEY})
        assert response.status_code == 422


class TestHealthCheck:
    def test_health_ok(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["version"] == "0.1.0"

    def test_health_no_auth_required(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
