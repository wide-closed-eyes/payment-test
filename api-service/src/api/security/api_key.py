from secrets import compare_digest

from fastapi import Header
from fastapi.exceptions import HTTPException

from src.config import config


async def validate_api_key(
    api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    if api_key is None or not compare_digest(api_key.encode(), config.api_key.encode()):
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
