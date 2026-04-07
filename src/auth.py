import secrets

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

import src.config as _config

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: str | None = Security(_api_key_header)) -> None:
    """Verifica que el header X-API-Key coincida con LEGALDIFF_API_KEY."""
    if api_key is None or not secrets.compare_digest(api_key, _config.LEGALDIFF_API_KEY):
        raise HTTPException(status_code=401, detail="API key inválida o ausente")
