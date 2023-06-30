from pyrogram import Client
from pyrogram.types import Message

from bot.utils.app_utils import AppUtils


# 获取匿名管理员tgid
async def get_anonymous_tgid(client: Client, message: Message):
    tgid = None
    if await AppUtils.is_anonymous_admin(message):
        if await AppUtils.has_author_signature(message):
            tgid = await AppUtils.get_anonymous_admin_tgid(client, message)
        else:
            await message.reply('匿名管理员设置头衔后可使用')
    return tgid
