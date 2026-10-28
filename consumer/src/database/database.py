from collections.abc import AsyncGenerator
from datetime import date, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from src.config import config


class Base(DeclarativeBase):
    def __repr__(self):
        cols = []
        for col in self.__table__.columns.keys():
            cols.append(f"{col}={getattr(self, col)}")
        return f"<{self.__class__.__name__} {', '.join(cols)}>"

    def dict(self):
        obj = {}
        for c in self.__table__.columns:
            attr = getattr(self, c.name)
            if isinstance(attr, (datetime, date)):
                attr = attr.isoformat()
            obj[c.name] = attr
        return obj


async_engine = create_async_engine(
    config.database_url,
    pool_pre_ping=True,
)


async_session_fabric = async_sessionmaker(
    async_engine, expire_on_commit=False, class_=AsyncSession
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_fabric() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
