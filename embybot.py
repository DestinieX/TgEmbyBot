from bot.scheduler import *
import bot.handler.command_handler.common_handler
import bot.handler.command_handler.lib_command_handler
import bot.handler.command_handler.user_command_handler
import bot.handler.command_handler.su_command_handler
import bot.handler.command_handler.admin_command_handler


# 设置定时任务随bot启动
if task_auto_start:
    scheduler_init()

if rank_auto_start:
    rank_init()

if db_backup_auto_start:
    db_backup_init()
# 启动
app.run()
