from datetime import datetime

from bot.client.emby_client import EmbyClient
from bot.enum.playback_rank_type import PlayBackRankType
from bot.scheduler.abstract_job import AbstractJob
from bot.utils.common_utils import CommonUtils
from config import rank_img_dir, groupid, rank_pin, rank_sort_by, rank_playback_time_show


class PlayWeeklyChartJob(AbstractJob):
    def __init__(self, app, jobs_dict, scheduler, day_of_week='sun', hour=0, minute=0, second=0):
        super().__init__()
        self.app = app
        self.jobs_dict = jobs_dict
        self.scheduler = scheduler
        self.job_name = f"播放周榜"
        self.day_of_week = day_of_week
        self.hour = hour
        self.minute = minute
        self.second = second

    def execute(self):
        # 如果存在旧任务，则先取消旧任务
        if self.job_name in self.jobs_dict:
            self.scheduler.remove_job(self.jobs_dict[self.job_name])
        job_id = self.scheduler.add_job(self.job_service, 'cron', day_of_week=self.day_of_week, hour=self.hour,
                                        minute=self.minute, second=self.second).id
        self.jobs_dict[self.job_name] = job_id

    def set_time(self, day_of_week='sun',hour=0,
                 minute=0, second=0):
        self.day_of_week = day_of_week
        self.hour = hour
        self.minute = minute
        self.second = second

    # 定时任务(播放周榜)
    async def job_service(self):
        tv_data = await EmbyClient.get_emby_rank(8, PlayBackRankType.TV)
        tv_sorted_data = sorted(tv_data, key=lambda x: x[rank_sort_by], reverse=True)[:10]
        movie_data = await EmbyClient.get_emby_rank(8, PlayBackRankType.MOVIES)
        movie_sorted_data = sorted(movie_data, key=lambda x: x[rank_sort_by], reverse=True)[:10]
        photo = CommonUtils.random_img(rank_img_dir + '/weekly')
        if photo is None:
            photo = CommonUtils.random_img(rank_img_dir)
        sort_by = '播放次数' if rank_sort_by == 'count' else '播放时长'
        result_tv = ''
        result_movie = ''
        result_tv_title = f"[播放周榜]  #TV\n#周榜  {datetime.today().strftime('%Y-%m-%d')}   排序方式: #{sort_by}\n"
        result_movie_title = f"[播放周榜]  #MOVIE\n#周榜  {datetime.today().strftime('%Y-%m-%d')}   排序方式: #{sort_by}\n"
        result_tv += result_tv_title
        result_tv += '[TV]\n'
        for i, item in enumerate(tv_sorted_data):
            hour, minute = CommonUtils.convert_seconds(item['time'])
            playback_time_str = ''
            if rank_playback_time_show:
                playback_time_str = f"播放时长:<code>{str(hour) + '小时' if hour != 0 else ''}{minute}分钟</code>"
            result_tv += f"TOP{(i + 1):<3} <code>{item['label']}</code>\n" \
                         f"   播放次数: <code>{item['count']:<3}</code>{playback_time_str}\n"
        result_movie += result_movie_title
        result_movie += '[Movie]\n'
        for i, item in enumerate(movie_sorted_data):
            hour, minute = CommonUtils.convert_seconds(item['time'])
            playback_time_str = ''
            if rank_playback_time_show:
                playback_time_str = f"播放时长:<code>{str(hour) + '小时' if hour != 0 else ''}{minute}分钟</code>"
            result_movie += f"TOP{(i + 1):<3} <code>{item['label']}</code>\n" \
                            f"   播放次数: <code>{item['count']:<3}</code>{playback_time_str}\n"
        message_tv = None
        message_movie = None
        if photo is not None:
            message_tv = await self.app.send_photo(
                chat_id=groupid,
                photo=photo,
                caption=result_tv
            )
            message_movie = await self.app.send_photo(
                chat_id=groupid,
                photo=photo,
                caption=result_movie
            )
        else:
            message_tv = await self.app.send_message(chat_id=groupid, text=result_tv)
            message_movie = await self.app.send_message(chat_id=groupid, text=result_movie)
        if message_tv is not None and rank_pin:
            # 获取id并取消pin
            weekly_id = CommonUtils.get_from_conf('weekly_id')
            if weekly_id is not None:
                await self.app.unpin_chat_message(chat_id=groupid, message_id=int(weekly_id))
            # 存储id
            CommonUtils.save_to_conf('weekly_id', message_tv.id)
            await self.app.pin_chat_message(chat_id=groupid, message_id=message_tv.id, disable_notification=True)
