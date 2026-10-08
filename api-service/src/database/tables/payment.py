from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, String, DECIMAL, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from src.database.database import Base


class PaymentStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "succeeded"
    FAILED = "failed"

class Currency(str, Enum):
    RUB = "RUB"
    USD = "USD"
    EUR = "EUR"

class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=func.gen_random_uuid()
    )
    amount: Mapped[float] = mapped_column(DECIMAL(precision=10, scale=2))
    currency: Mapped[Currency] = mapped_column(String(3))
    description: Mapped[str] = mapped_column(Text())
    metadata: Mapped[dict] = mapped_column(JSONB())
    status: Mapped[PaymentStatus] = mapped_column(String(10), default=PaymentStatus.PENDING)
    idempotency_key: Mapped[str] = mapped_column(String(length=64), unique=True)
    webhook_url: Mapped[str] = mapped_column(String(255))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
