from fastapi import APIRouter, Header, HTTPException

from src.api.schemas.payment import PaymentCreate, PaymentCreateResponse, PaymentFullResponse
from src.database.repository import PaymentRepositoryGetter, OutboxRepositoryGetter


router = APIRouter(
    prefix="/payments",
    tags=["payments"],
)


@router.post("", response_model=PaymentCreateResponse, status_code=202)
async def get_status(
    body: PaymentCreate,
    payment_repository: PaymentRepositoryGetter,
    outbox_repository: OutboxRepositoryGetter,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    ):
    try:
        payment_db = await payment_repository.create_from_request(body=body.model_dump(), idempotency_key=idempotency_key)
    except Exception as e:
        raise HTTPException(status_code=409, detail=str(e))
    
    await outbox_repository.create_payment_event(payment_db)
    
    return payment_db

@router.get("/{payment_id}", response_model=PaymentFullResponse, status_code=200)
async def get_payment(
    payment_id: str,
    payment_repository: PaymentRepositoryGetter,
    ):
    payment_db = await payment_repository.get_full_payment(payment_id=payment_id)
    if not payment_db:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment_db
