from datetime import datetime
from typing import Literal

from pydantic import AnyUrl, BaseModel, ConfigDict, Field, field_validator


class PaymentCreate(BaseModel):
    amount: float
    currency: Literal["RUB", "USD", "EUR"]
    description: str
    metadata: dict
    webhook_url: str = Field(max_length=255)

    @field_validator("webhook_url")
    def validate_webhook_url(cls, value):
        try:
            AnyUrl(value)
        except ValueError:
            raise ValueError("Webhook URL must be valid URL")
        return value


class PaymentCreateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    payment_id: str = Field(alias="id")
    status: str
    created_at: str

    @field_validator("created_at", mode="before")
    def format_created_at(cls, value):
        if isinstance(value, datetime):
            return value.strftime("%d-%m-%Y %H:%M")
        return value


class PaymentFullResponse(BaseModel):
    payment_id: str = Field(alias="id")
    amount: float
    currency: str
    description: str
    metadata: dict
    status: str
    idempotency_key: str
    webhook_url: str
    created_at: str
    updated_at: str

    @field_validator("created_at", "updated_at", mode="before")
    def format_created_at(cls, value):
        if isinstance(value, datetime):
            return value.strftime("%d-%m-%Y %H:%M")
        return value
