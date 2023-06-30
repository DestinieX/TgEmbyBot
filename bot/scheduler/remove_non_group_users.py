import logging

import requests
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from bot.client.emby_client import EmbyClient
from bot.database import engine
from bot.log import logger
from bot.model.user import User
from bot.scheduler.abstract_job import AbstractJob
from config import groupid, embyapi, embyurl


class RemoveNonGroupUsers(AbstractJob):

    def __init__(self, app, jobs_dict, scheduler, hour=0, minute=0, second=0):
        super().__init__()
        self.app = app
        self.jobs_dict = jobs_dict
        self.scheduler = scheduler
        self.job_name = f"自动删除不在群组用户"
        self.hour = hour
        self.minute = minute
        self.second = second

    # 定时任务(自动删除不在群组用户)
    async def job_service(self):
        await self.app.send_message(chat_id=groupid, text="定时任务:<code>自动删除不在群组用户</code>\n开始执行")
        # 获取所有成员的tgid
        all_members_id = []
        async for member in self.app.get_chat_members(groupid):
            all_members_id.append(member.user.id)
        # 从数据库获取所有已注册用户的 tgid
        async with AsyncSession(engine) as session:
            result = await session.execute(select(User))
            registered_users = result.scalars()
            # 数据库 id 存在，群组 tgid 不存在则删号处理(不在群有号)
            for user in registered_users:
                if user.tgid not in all_members_id:
                    delete_response = await EmbyClient.delete_emby(user.emby_id)
                    # 检查响应状态码
                    tg_user = await self.app.get_users(user_ids=user.tgid)
                    if delete_response:
                        # 删除数据库记录
                        await session.delete(user)
                        # 发送请求
                        await self.app.send_message(chat_id=groupid,
                                               text=f'用户 <a href="tg://user?id={tg_user.id}">{tg_user.first_name} {tg_user.last_name}</a> 账号已删除\n原因：不在群组内')
                        logger.info(
                            f"成功：删除账号(自动删除不在群组用户)(定时任务) 用户(tgid='{tg_user.id}',username={tg_user.first_name} {tg_user.last_name},emby_name={user.emby_name},emby_id={user.emby_id})")
                    else:
                        logger.error(
                            f"失败：删除账号(自动删除不在群组用户)(定时任务) 用户(tgid='{tg_user.id}',username={tg_user.username},name={tg_user.first_name} {tg_user.last_name},emby_name={user.emby_name},emby_id={user.emby_id})")
            await session.commit()
            await self.app.send_message(chat_id=groupid, text="定时任务:<code>自动删除不在群组用户</code>\n执行完毕")
