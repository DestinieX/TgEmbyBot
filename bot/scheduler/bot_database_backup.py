from abc import ABC

from pyrogram.errors import PeerIdInvalid

from bot.scheduler.abstract_job import AbstractJob
from bot.utils.db_backup_utils import DbBackupUtils
from config import db_docker_mode, groupid, db_container_name, db_user, db_password, db_name, db_backup_dir, \
    max_backups, db_host, log_channel_id


class BotDatabaseBackupJob(AbstractJob):

    def __init__(self, app, jobs_dict, scheduler, hour=0, minute=0, second=0):
        super().__init__()
        self.app = app
        self.jobs_dict = jobs_dict
        self.scheduler = scheduler
        self.job_name = f"BOT数据库自动备份"
        self.hour = hour
        self.minute = minute
        self.second = second

    # 定时任务(BOT数据库备份)
    async def job_service(self):
        await self.app.send_message(chat_id=groupid, text='定时任务:<code>BOT数据库自动备份</code>\n开始执行')
        backup_file = None
        if db_docker_mode:
            backup_file = await DbBackupUtils.backup_mysql_db_docker(
                container_name=db_container_name,
                user=db_user,
                password=db_password,
                database_name=db_name,
                backup_dir=db_backup_dir,
                max_backup_count=max_backups
            )
        else:
            backup_file = await DbBackupUtils.backup_mysql_db(
                host=db_host,
                user=db_user,
                password=db_password,
                database_name=db_name,
                backup_dir=db_backup_dir,
                max_backup_count=max_backups
            )
        if backup_file is not None:
            try:
                await self.app.send_document(
                    chat_id=log_channel_id,
                    document=backup_file,
                    caption=f'BOT数据库备份完毕'
                )
            except PeerIdInvalid:
                await self.app.send_message(chat_id=groupid, text='配置错误，备份文件仅保存在本地')
            await self.app.send_message(chat_id=groupid, text='定时任务:<code>BOT数据库自动备份</code>\n执行完毕')
        else:
            try:
                await self.app.send_message(chat_id=log_channel_id, text="BOT数据库自动备份失败，请尽快检查相关配置")
            finally:
                await self.app.send_message(chat_id=groupid, text='BOT数据库自动备份失败，请尽快检查相关配置')
