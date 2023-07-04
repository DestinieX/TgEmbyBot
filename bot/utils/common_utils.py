import asyncio
import json
import os
import random
import re
from datetime import datetime, timedelta

from config import admin_list


class CommonUtils:

    @staticmethod
    def local_time(time=''):
        if time is None:
            return 'None'
        n_last_login = time[0:19]
        utc_format = "%Y-%m-%dT%H:%M:%S"
        utctime_last_login = datetime.strptime(n_last_login, utc_format)
        localtime_last_login = utctime_last_login + timedelta(hours=8)
        return localtime_last_login  # change emby time to Asia/Shanghai time

    @staticmethod
    # 判断是否为超级管理员(是否在配置文件中配置)
    def is_super_admin(tgid=0):
        # 判断当前用户的tgid是否在配置文件中
        for i in range(0, len(admin_list)):
            if tgid == admin_list[i]:
                return True

    @staticmethod
    # 通过json将数据存储到文件
    def save_to_conf(key, value):
        data = {}
        if os.path.exists("data.json"):
            with open("data.json", "r") as json_file:
                data = json.load(json_file)
        data[key] = value
        with open("data.json", "w") as json_file:
            json.dump(data, json_file)

    @staticmethod
    # 通过文件获取对应数据
    def get_from_conf(key):
        if os.path.exists("data.json"):
            with open("data.json", "r") as json_file:
                data = json.load(json_file)
                return data.get(key)
        else:
            return None

    @staticmethod
    # 判断定时任务时间格式是否正确
    def is_valid_hour(time_str):
        time_pattern = re.compile(r'^\d{1,2}:\d{2}$')
        return bool(time_pattern.match(time_str))

    @staticmethod
    # 获取当前时区字符串
    def get_timezone():
        # 获取当前时间和时区
        current_time = datetime.now()
        current_timezone = current_time.astimezone().tzinfo

        # 获取UTC偏移量（以小时为单位），并转换为整数
        utc_offset_hours = int(current_timezone.utcoffset(current_time).total_seconds() / 3600)

        # 格式化为字符串
        utc_offset_str = "UTC{:+}".format(utc_offset_hours)
        return utc_offset_str

    @staticmethod
    # 从文件夹随机选择图片，若文件夹不存在图片，则返回None
    def random_img(img_folder):
        # 如果文件夹不存在，就创建它
        if not os.path.exists(img_folder):
            os.makedirs(img_folder)
        images = [os.path.join(img_folder, img) for img in os.listdir(img_folder) if
                  img.endswith(('.png', '.jpg', '.jpeg'))]
        return random.choice(images) if images else None

    # 判断集合是否为空
    @staticmethod
    def is_empty(collection):
        return collection is None or len(collection) == 0

    # 判断集合是否不为空
    @staticmethod
    def is_not_empty(collection):
        return collection is not None and len(collection) != 0

    # 通过秒数转换为小时和分钟数，如果不满1分钟则返回1分钟
    @staticmethod
    def convert_seconds(seconds):
        hours = seconds // 3600
        remaining_seconds = seconds % 3600
        minutes = remaining_seconds // 60
        if remaining_seconds > 0 and minutes < 1:
            minutes = 1
        return hours, minutes
