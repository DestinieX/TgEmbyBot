from abc import ABC, abstractmethod


class AbstractJob(ABC):
    def __init__(self):
        self.scheduler = None
        self.jobs_dict = None
        self.job_name = None
        self.second = 0
        self.minute = 0
        self.hour = 0

    @abstractmethod
    def job_service(self):
        pass

    def set_time(self, hour=0,
                 minute=0, second=0):
        self.hour = hour
        self.minute = minute
        self.second = second

    def execute(self):
        # 如果存在旧任务，则先取消旧任务
        if self.job_name in self.jobs_dict:
            self.scheduler.remove_job(self.jobs_dict[self.job_name])
        job_id = self.scheduler.add_job(self.job_service, 'cron', hour=self.hour,
                                        minute=self.minute, second=self.second).id
        self.jobs_dict[self.job_name] = job_id

    def cancel(self):
        # 如果存在旧任务，则先取消旧任务
        self.scheduler.remove_job(self.jobs_dict[self.job_name])
        del self.jobs_dict[self.job_name]
