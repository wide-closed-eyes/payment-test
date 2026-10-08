from typing import Any, Generic, Sequence, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm.interfaces import ORMOption


M = TypeVar("M", bound=DeclarativeBase)


class AsyncRepository(Generic[M]):
    def __init__(
        self,
        model: Type[M],
        session: AsyncSession,
    ) -> None:
        """
        Initialize AsyncRepository with model and session

        :param model: Type[M] | Type[DeclarativeBase] | Type[YourDatabaseModel]
        :param session: AsyncSession
        """

        self._model = model
        self._session = session

    async def get_by_pk(
        self,
        pk: int | str | Any,
        options: Sequence[ORMOption] | None = None,
    ) -> M | None:
        """
        Get record by primary key

        :param pk: int | str | Any
        :param options: Iterable[ORMOption]
        :return: M
        """
        return await self._session.get(self._model, pk, options=options)

    async def get_one(
        self,
        filter: list[Any],
        order_by: Any | str | None = None,
        options: Sequence[ORMOption] | None = None,
    ) -> M | None:
        query = select(self._model).filter(*filter)

        if order_by:
            query = query.order_by(order_by)
        if options:
            query = query.options(*options)
        return (await self._session.scalars(query)).first()

    async def get_all(
        self,
        options: Sequence[ORMOption] | None = None,
        extra_columns: list[str] | None = None,
        order_by: Any | str | None = None,
        filter: list[Any] | None = None,
        is_for_update: bool = False,
        limit: int | None = None
    ) -> list[M]:
        """
        Get all records

        :param options: Iterable[Any]
        :param order_by: _ColumnExpressionOrStrLabelArgument
        :param extra_columns: list[str]
        :return: list[M]
        """
        query = select(self._model)

        if order_by:
            query = query.order_by(order_by)

        if options:
            query = query.options(*options)

        if filter:
            query = query.filter(*filter)

        if extra_columns:
            query = query.add_columns(*extra_columns)

        if is_for_update:
            query = query.with_for_update(skip_locked=True)

        if limit:
            query = query.limit(limit)

        return (await self._session.scalars(query)).all()

    async def create(self, record: M, with_commit: bool = True) -> M:
        """
        Create new record

        :param record: M
        :return: M
        """
        self._session.add(record)
        await self._session.flush()
        if with_commit:
            await self.commit()
        return record

    async def bulk_create(self, records: list[M], with_commit: bool = True) -> list[M]:
        """
        Create new records

        :param records: list[M]
        :return: list[M]
        """
        self._session.add_all(records)
        await self._session.flush()
        if with_commit:
            await self.commit()
        return records

    async def update(self, record: M, with_commit: bool = True) -> M:
        """
        Update record

        :param record: M
        :return: M
        """
        self._session.add(record)
        await self._session.flush()

        if with_commit:
            await self.commit()

        return record

    async def update_from_dict(
        self, data: dict[str, Any], record: M, with_commit: bool = True
    ) -> M:
        """
        Update record from dict

        :param data: dict[str, Any]
        :param record: M
        :return: M
        """

        for k, v in data.items():
            if not hasattr(record, k):
                raise AttributeError(f"Field {k} does not exist in record {record}")

            setattr(record, k, v)

        return await self.update(record, with_commit)

    async def delete(self, record: M, with_commit: bool = True) -> M:
        """
        Delete record

        :param record: M
        :return: M
        """
        await self._session.delete(record)

        if with_commit:
            await self.commit()

        return record

    async def commit(self) -> None:
        """
        Commit changes
        """
        await self._session.commit()
