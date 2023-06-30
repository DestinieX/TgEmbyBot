from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import declarative_base, DeclarativeBase


class Base(AsyncAttrs,DeclarativeBase):
    pass
