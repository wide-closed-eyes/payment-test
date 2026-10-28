from datetime import date, datetime

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    def __repr__(self):
        cols = []
        for col in self.__table__.columns.keys():
            cols.append(f"{col}={getattr(self, col)}")
        return f"<{self.__class__.__name__} {', '.join(cols)}>"

    def dump(self):
        obj = {}
        for c in self.__table__.columns:
            attr = getattr(self, c.name)
            if isinstance(attr, (datetime, date)):
                attr = attr.isoformat()
            obj[c.name] = attr
        return obj
