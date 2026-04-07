import os

from dotenv import load_dotenv

load_dotenv()

REQUIRED_ENV_VARS: list[str] = [
    "OPENAI_API_KEY",
    "LANGFUSE_PUBLIC_KEY",
    "LANGFUSE_SECRET_KEY",
    "LANGFUSE_HOST",
    "DATABASE_URL",
]


def validate_env() -> None:
    """Valida que todas las variables de entorno requeridas existan. Falla rápido."""
    missing = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
    if missing:
        raise OSError(
            f"Variables de entorno faltantes: {', '.join(missing)}. "
            "Revisar .env.example"
        )


OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL: str | None = os.getenv("OPENAI_BASE_URL")
LANGFUSE_PUBLIC_KEY: str = os.getenv("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY: str = os.getenv("LANGFUSE_SECRET_KEY", "")
LANGFUSE_HOST: str = os.getenv("LANGFUSE_HOST", "")
DATABASE_URL: str = os.getenv("DATABASE_URL", "")
LEGALDIFF_API_KEY: str = os.getenv("LEGALDIFF_API_KEY", "")
