import logging
import traceback
from datetime import datetime, timedelta

import requests
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from bot.client.emby_client import EmbyClient
from bot.database import engine
from bot.log import logger
from bot.model.user import User
from bot.scheduler.abstract_job import AbstractJob
from config import groupid, embyapi, embyurl, task_init_minute, task_init_hour


class RemoveInactiveUserJob(AbstractJob):

    def __init__(self, app, jobs_dict, scheduler, days_threshold=30, hour=0, minute=0, second=0):
        super().__init__()
        self.app = app
        self.jobs_dict = jobs_dict
        self.scheduler = scheduler
        self.days_threshold = days_threshold
        self.job_name = f"自动删除超过{self.days_threshold}天不活跃用户"
        self.hour = hour
        self.minute = minute
        self.second = second

    # 定时任务(自动删除{days_threshold}天无活动记录的用户)
    async def job_service(self):
        await self.app.send_message(chat_id=groupid,
                                    text=f"定时任务:<code>自动删除{self.days_threshold}天无活动记录的用户</code>\n开始执行")
        # 获取用户列表
        headers = {"X-MediaBrowser-Token": embyapi}
        response = requests.get(f"{embyurl}/emby/Users", headers=headers)
        # 检查请求是否成功
        if response.status_code == 200:
            users = response.json()
            date_threshold = datetime.now() - timedelta(days=self.days_threshold)
            # 查找活动记录大于 {days_threshold} 天的用户
            inactive_users = []
            for user in users:
                # print(f"user['LastActivityDate'] = {user['LastActivityDate']}")
                # 只取秒级精度
                date_str = user.get('LastActivityDate', None)
                if date_str is None:
                    inactive_users.append(user)
                    continue
                last_activity_date = datetime.strptime(date_str[:19], "%Y-%m-%dT%H:%M:%S")
                if last_activity_date < date_threshold:
                    inactive_users.append(user)
            # 遍历不活跃用户列表，判断是否为白名单，根据条件禁用用户emby
            async with AsyncSession(engine) as session:
                # 从数据库中获取所有用户记录
                result = await session.execute(select(User))
                all_users = result.scalars()
                # 将数据库中的用户记录转换为字典，以便快速查找
                user_dict = {user.emby_id: user for user in all_users}
                # 遍历不活跃用户列表
                for user in inactive_users:
                    user_id = user['Id']
                    db_emby_user = user_dict.get(user_id)
                    # 如果不为白名单用户，则进行封禁
                    if db_emby_user is not None:
                        if db_emby_user.is_in_whitelist is False:
                            try:
                                delete_response = await EmbyClient.delete_emby(user_id)
                                tg_user = await self.app.get_users(db_emby_user.tgid)
                                if delete_response:
                                    # 删除数据库记录
                                    await session.delete(db_emby_user)
                                    # 发送请求
                                    username = tg_user.first_name
                                    message_text = f'用户 <a href="tg://user?id={db_emby_user.tgid}">{username}</a> ' \
                                                   f'账号已删除\n原因：从未登陆过或{self.days_threshold}天内无活动记录'
                                    await self.app.send_message(chat_id=groupid, text=message_text)
                                    logger.info(
                                        f"成功：删除账号(自动删除{self.days_threshold}天无活动记录的用户)(定时任务) 用户(tgid='{db_emby_user.tgid}',username={tg_user.username},name={tg_user.first_name} {tg_user.last_name},emby_name={db_emby_user.emby_name},emby_id={db_emby_user.emby_id},reason={user.get('LastActivityDate', None)})")
                                else:
                                    logger.error(
                                        f"失败：删除账号(自动删除{self.days_threshold}天无活动记录的用户)(定时任务) 用户(tgid='{db_emby_user.tgid}',username={tg_user.username},name={tg_user.first_name} {tg_user.last_name},emby_name={db_emby_user.emby_name},emby_id={db_emby_user.emby_id},reason={user.get('LastActivityDate', None)})")

                            except Exception as e:
                                traceback.print_exc()
                        else:
                            print(f"白名单用户{db_emby_user.emby_name}不删除")
                            pass
                    else:
                        print(f"{user['Name']}不在数据库管理")
                        pass
                # print("任务执行完毕")
                await session.commit()
                await self.app.send_message(chat_id=groupid,
                                            text=f"定时任务:<code>自动删除{self.days_threshold}天无活动记录的用户</code>\n执行完毕")
        else:
            logger.error(f"失败：访问emby获取用户列表")
            # print("获取用户列表失败")
