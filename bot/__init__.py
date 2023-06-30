import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pyrogram import Client

from config import *

# (仅Linux支持)启用uvloop作为event loop，可以使异步操作速度提升2-4倍
#import uvloop
#uvloop.install()

app = Client("my_bot", bot_token=bot_token, api_id=api_id, api_hash=api_hash)  # create tg bot
