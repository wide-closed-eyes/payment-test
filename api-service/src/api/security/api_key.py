from fastapi import Header
from fastapi.exceptions import HTTPException

from src.config import config


async def validate_api_key(api_key: str = Header(alias="X-API-Key")):
    if api_key != config.api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")
