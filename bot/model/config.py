import datetime

from sqlalchemy import String, Integer, BigInteger
from sqlalchemy.orm import mapped_column, Mapped

from bot.model import *


# # config类
# class Config(Base):
#     __tablename__ = 'config'
#     id: Mapped[int] = mapped_column(Integer, primary_key=True)
#     register_method: Mapped[str] = mapped_column(String(50))
#     register_public: Mapped[str] = mapped_column(String(50))
#     register_public_user: Mapped[int] = mapped_column(Integer)
#     register_public_time: Mapped[int] = mapped_column(BigInteger)


class Config(Base):
    __tablename__ = 'config'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    register_method: Mapped[str] = mapped_column(String(50))
    register_public: Mapped[str] = mapped_column(String(50))
    register_public_user: Mapped[int] = mapped_column(Integer)
    register_public_time: Mapped[datetime.datetime] = mapped_column(default=None)
