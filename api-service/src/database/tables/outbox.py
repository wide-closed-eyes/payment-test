import uuid
from datetime import datetime

from sqlalchemy import UUID, String, Text, DateTime, JSON, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column

from src.database.database import Base

class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=uuid.uuid4)
    aggregate_type: Mapped[str] = mapped_column(String(50))  # Тип передаваемой сущность. В данном случае только Payment
    aggregate_id: Mapped[str] = mapped_column(String(50))    # id сущности
    event_type: Mapped[str] = mapped_column(String(50))    # Тип события. В данном случае только payments.new
    payload: Mapped[dict] = mapped_column(JSON)             # Тело сообщения
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    
    # Статусы для обработки воркером
    processed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_log: Mapped[str | None] = mapped_column(Text, nullable=True)
