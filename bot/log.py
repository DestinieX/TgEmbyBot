import logging
import os
from logging.handlers import TimedRotatingFileHandler
# 系统日志
# 检查日志目录是否存在，不存在则创建
log_dir = "./log"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

handler = TimedRotatingFileHandler(os.path.join(log_dir, 'rotating_log.log'), when='D', interval=3, backupCount=10,
                                   encoding='utf-8')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
handler.suffix = '%Y%m%d'
logger = logging.getLogger()
logger.addHandler(handler)
logger.setLevel(logging.INFO)
# logging.getLogger("pyrogram.session.session").setLevel(logging.WARNING)




# # sql日志
# # 设置日志级别为DEBUG
# logging.basicConfig()
# logging.getLogger('sqlalchemy.engine').setLevel(logging.DEBUG)
#
#
# # 监听sql生成时间
# @event.listens_for(engine, 'before_cursor_execute')
# def receive_before_cursor_execute(conn, cursor, statement, params, context, executemany):
#     context._query_start_time = time.time()
#
#
# # 监听生成的sql语句
# @event.listens_for(engine, 'after_cursor_execute')
# def receive_after_cursor_execute(conn, cursor, statement, params, context, executemany):
#     total = time.time() - context._query_start_time
#     print(f"{statement} [{params}] took {total} seconds")
