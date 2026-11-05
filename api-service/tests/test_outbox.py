from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.dialects import postgresql

from src.database.repository.outbox import OutboxRepository


async def test_select_for_update_filters_unprocessed_events():
    session = AsyncMock()
    session.scalars.return_value = MagicMock(all=MagicMock(return_value=[]))

    await OutboxRepository(session).select_for_update(limit=10)

    query = session.scalars.await_args.args[0]
    sql = str(query.compile(dialect=postgresql.dialect()))
    assert "outbox_events.processed IS false" in sql
    assert "FOR UPDATE SKIP LOCKED" in sql
