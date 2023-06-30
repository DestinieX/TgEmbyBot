from urllib import parse

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine

from config import *

temp_db_password = parse.quote_plus(db_password)
engine = create_async_engine(
    f'mysql+asyncmy://{db_user}:{temp_db_password}@{db_host}:{db_port}/{db_name}?charset=utf8mb4',
    pool_size=20,
    pool_recycle=3600
)