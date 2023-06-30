import requests
from pyrogram import filters
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from bot import app
from bot.database import engine
from bot.model.user import User
from config import ban_channel_id, embyurl, embyapi


# 通过emby用户名密码绑定用户信息
@app.on_message(filters.command("bind"))
async def bind(client, message):
    tgid = message.from_user.id
    # 检查输入的命令格式是否正确
    msg_command = message.command
    if len(msg_command) == 3:
        username = msg_command[1]
        password = msg_command[2]
        # 检查数据库是否已存在该用户
        async with AsyncSession(engine) as session:
            result = await session.execute(select(User).where(User.tgid == tgid))
            user = result.scalar_one_or_none()
            if user is not None:
                await message.reply("用户已绑定，请勿重复绑定")
            # 获取用户信息
            auth_data = {
                "Username": username,
                "Pw": password,
            }
            headers = {
                "X-Emby-Authorization": f"Emby UserId=, Client=Python, Device=Python, DeviceId=, Version=1.0, Token={embyapi}"
            }
            response = requests.post(f"{embyurl}/emby/Users/AuthenticateByName", json=auth_data, headers=headers)
            if response.status_code == 200:
                user_data = response.json()
                emby_name = user_data["User"]["Name"]
                emby_id = user_data["User"]["Id"]
                new_user = User(tgid=tgid, emby_name=emby_name, emby_id=emby_id)
                session.add(new_user)
                await session.commit()
            else:
                await message.reply("用户名密码错误")
    else:
        await message.reply("命令格式错误，请输入：/bind username password")


# 求片(/求片)
@app.on_message(filters.command("求片"))
async def request_item(client, message):
    tgid = message.from_user.id
    msg_command = message.command
    if len(msg_command) != 3:
        await message.reply("命令格式错误，请输入/求片 对应imdb网址 对应影片名称")
        return
    url = msg_command[1]
    name = msg_command[2]
    if url.find('imdb.com') == -1 or url.find('ref') != -1 or url.find('title') == -1:
        await message.reply('链接不符合规范')
    else:
        await message.reply('已发送请求')
        await app.send_message(chat_id=ban_channel_id,
                               text=f'#求片\n影片名 #{name}\nIMDB链接：<code>{url}</code>\nTGID <a href="tg://user?id={tgid}">{tgid}</a>')
