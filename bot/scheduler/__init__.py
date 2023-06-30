# 定时任务
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot import app
from bot.scheduler.bot_database_backup import BotDatabaseBackupJob
from bot.scheduler.play_daily_chart import PlayDailyChartJob
from bot.scheduler.play_weekly_chart import PlayWeeklyChartJob
from bot.scheduler.remove_inactive_user import RemoveInactiveUserJob
from bot.scheduler.remove_non_group_users import RemoveNonGroupUsers

from config import days_threshold, task_auto_start, rank_auto_start, db_backup_auto_start, task_init_hour, \
    task_init_minute, rank_init_hour, rank_init_minute, backup_init_hour, backup_init_minute

scheduler = AsyncIOScheduler()
# 任务字典，用于存储任务的引用
jobs = {}
remove_inactivate_job = RemoveInactiveUserJob(app, jobs, scheduler, days_threshold)
remove_non_group_user_job = RemoveNonGroupUsers(app, jobs, scheduler)
play_daily_chart_job = PlayDailyChartJob(app, jobs, scheduler)
play_weekly_chart_job = PlayWeeklyChartJob(app, jobs, scheduler)
bot_database_backup_job = BotDatabaseBackupJob(app, jobs, scheduler)


# 程序启动时初始化定时任务
def scheduler_init():
    remove_non_group_user_job.set_time(hour=task_init_hour, minute=task_init_minute, second=20)
    remove_non_group_user_job.execute()

    remove_inactivate_job.set_time(hour=task_init_hour, minute=task_init_minute)
    remove_inactivate_job.execute()


def rank_init():
    play_daily_chart_job.set_time(hour=rank_init_hour, minute=rank_init_minute)
    play_daily_chart_job.execute()

    play_weekly_chart_job.set_time(day_of_week='sun', hour=rank_init_hour, minute=rank_init_minute, second=20)
    play_weekly_chart_job.execute()


def db_backup_init():
    bot_database_backup_job.set_time(hour=backup_init_hour, minute=backup_init_minute)
    bot_database_backup_job.execute()


# 运行定时任务
scheduler.start()


