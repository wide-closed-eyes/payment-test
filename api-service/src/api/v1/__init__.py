from fastapi import APIRouter, Depends

from src.api.v1.payment import router as payment_router
from src.api.security.api_key import validate_api_key


router = APIRouter(prefix="/api/v1", tags=["v1"], dependencies=[Depends(validate_api_key)])

router.include_router(payment_router)
