#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import time
import requests
import datetime
import webbrowser
import subprocess
import tkinter as tk
import winreg
import os
from tkinter import messagebox, font

while True:
    # 判断当前设备是否可以正常访问网络，解决无法获取北京时间报错的问题。Rabbit 2023年10月23日14:44:16
    fnull = open(os.devnull, 'w')
    return1 = subprocess.call('ping www.baidu.com', shell=True, stdout=fnull, stderr=fnull)
    if return1:
        a = messagebox.askquestion("警告",
                                   "无法连接互联网，继续使用可能会存在非常非常非常非常严重的错误，是否要继续打开？")
        if a == 'yes':
            break
        else:
            sys.exit()
    else:
        # 联网获取北京时间 Rabbit 2023年10月20日20:20:35
        def get_beijing_stamp_from_web(url):
            response = requests.get(url)
            ts = response.headers['date']
            gmt_time_obj = time.strptime(ts[5:25], "%d %b %Y %H:%M:%S")
            gmt_ts = time.mktime(gmt_time_obj)
            bj_internet_ts = int(gmt_ts + 8 * 3600)
            return bj_internet_ts


        url = get_beijing_stamp_from_web('http://www.baidu.com')
        Network_time = time.localtime(url)

        time_now = time.time()
        time_nows = time.localtime(time_now)
        Local_time = time.strftime('%Y-%m-%d %H:%M:%S', time_nows)

        # 判断本地时间是否跟北京时间最多相差超过一分钟 Rabbit 2023年10月20日20:25:20
        while True:
            if Network_time.tm_hour == time_nows.tm_hour and Network_time.tm_min == time_nows.tm_min:
                break
            else:
                messagebox.showinfo("警告", "本机时间与北京时间相差超过一分钟，请校准后再使用本软件")
                webbrowser.open("https://time.tianqi.com/")
                sys.exit()
    break

# 主程序
countdown_tasks = [
    # 这里是一个很神奇的BUG，倒计时超过24H就不倒计时了，今后找到解决办法再修。Rabbit 2023年10月20日21:00:06
    {
        'name': '晚上放学2',
        'target_time': datetime.time(8, 00, 0)
    },
    {
        'name': '第一节课',
        'target_time': datetime.time(8, 45, 0)
    },
    {
        'name': '下课1',
        'target_time': datetime.time(8, 55, 0)
    },
    {
        'name': '第二节课',
        'target_time': datetime.time(9, 40, 0)
    },
    {
        'name': '下课2',
        'target_time': datetime.time(9, 50, 0)
    },
    {
        'name': '第三节课',
        'target_time': datetime.time(10, 35, 0)
    },
    {
        'name': '下课3',
        'target_time': datetime.time(10, 45, 0)
    },
    {
        'name': '第四节课',
        'target_time': datetime.time(11, 30, 0)
    },
    {
        'name': '中午放学',
        'target_time': datetime.time(13, 00, 0)
    },
    {
        'name': '第五节课',
        'target_time': datetime.time(13, 45, 0)
    },
    {
        'name': '下课4',
        'target_time': datetime.time(13, 55, 0)
    },
    {
        'name': '第六节课',
        'target_time': datetime.time(14, 40, 0)
    },
    {
        'name': '下课5',
        'target_time': datetime.time(14, 50, 0)
    },
    {
        'name': '第七节课',
        'target_time': datetime.time(15, 35, 0)
    },
    {
        'name': '下课6',
        'target_time': datetime.time(15, 45, 0)
    },
    {
        'name': '第八节课',
        'target_time': datetime.time(16, 30, 0)
    },
    {
        'name': '下午放学',
        'target_time': datetime.time(18, 00, 0)
    },
    {
        'name': '第九节课',
        'target_time': datetime.time(18, 45, 0)
    },
    {
        'name': '下课7',
        'target_time': datetime.time(18, 55, 0)
    },
    {
        'name': '第十节课',
        'target_time': datetime.time(19, 40, 0)
    },
    {
        'name': '下课8',
        'target_time': datetime.time(19, 50, 0)
    },
    {
        'name': '第十一节课',
        'target_time': datetime.time(20, 30, 0)
    },
    {
        'name': '晚上放学1',
        'target_time': datetime.time(23, 59, 59)
    },
]


def update_time():
    now = datetime.datetime.now().time()
    current_time = now.strftime("%H:%M:%S")
    closest_task = find_closest_task(now)

    label1.config(text="当前时间:")
    label2.config(text=current_time)
    label3.config(text="当前状态:")

    if datetime.time(8, 0, 0) <= now <= datetime.time(8, 45, 0) or \
            datetime.time(8, 55, 0) <= now <= datetime.time(9, 40, 0) or \
            datetime.time(9, 50, 0) <= now <= datetime.time(10, 35, 0) or \
            datetime.time(10, 45, 0) <= now <= datetime.time(11, 30, 0) or \
            datetime.time(13, 0, 0) <= now <= datetime.time(13, 45, 0) or \
            datetime.time(13, 55, 0) <= now <= datetime.time(14, 40, 0) or \
            datetime.time(14, 50, 0) <= now <= datetime.time(15, 35, 0) or \
            datetime.time(15, 45, 0) <= now <= datetime.time(16, 30, 0) or \
            datetime.time(18, 0, 0) <= now <= datetime.time(18, 45, 0) or \
            datetime.time(18, 55, 0) <= now <= datetime.time(19, 40, 0) or \
            datetime.time(19, 50, 0) <= now <= datetime.time(20, 30, 0):
        label4.config(text="上课")
        label5.config(text="当前课程:")
        label6.config(text=closest_task['name'])
        label7.config(text="距离下课还有:")
        label8.config(text=str(closest_task['remaining']))
    elif datetime.time(11, 30, 0) <= now <= datetime.time(13, 00, 0) or \
            datetime.time(16, 30, 0) <= now <= datetime.time(18, 00, 0) or \
            datetime.time(20, 30, 0) <= now <= datetime.time(23, 59, 59) or \
            datetime.time(0, 0, 0) <= now <= datetime.time(8, 00, 0):
        label4.config(text="放学")
        label5.config(text="当前课程:")
        label6.config(text='')
        label7.config(text="距离上课还有:")
        label8.config(text=str(closest_task['remaining']))
    else:
        label4.config(text="下课")
        label5.config(text="当前课程:")
        label6.config(text='')
        label7.config(text="距离上课还有:")
        label8.config(text=str(closest_task['remaining']))

    root.after(1000, update_time)


def find_closest_task(current_time):
    closest_task = {
        'name': '',
        'remaining': datetime.timedelta(hours=0, minutes=0, seconds=0)
    }
    min_remaining = datetime.timedelta(hours=24)

    for task in countdown_tasks:
        task_time = task['target_time']
        task_datetime = datetime.datetime.combine(datetime.date.today(), task_time)
        if task_datetime > datetime.datetime.now():
            remaining_time = task_datetime - datetime.datetime.now()
            if remaining_time < min_remaining:
                min_remaining = remaining_time
                closest_task['name'] = task['name']
                closest_task['remaining'] = remaining_time

    return closest_task


root = tk.Tk()
root.title("时间管理大师")
root.geometry('280x110')


def switch_college():
    messagebox.showinfo("切换学院", "暂未实现，下个版本更新（大概")


# 设置开机自启,该死的360又™报毒。Rabbit 2023年10月22日20:19:34
def self_starting():
    initiate = messagebox.askquestion("开机自启", "是否要设置开机自启动？，点击否即可取消之前设置的开机自启。")

    if initiate:
        def add_to_startup(file_path):
            key = winreg.HKEY_CURRENT_USER
            key_value = "Software\\Microsoft\\Windows\\CurrentVersion\\Run"

            with winreg.OpenKey(key, key_value, 0, winreg.KEY_ALL_ACCESS) as registry_key:
                winreg.SetValueEx(registry_key, "MyApp", 0, winreg.REG_SZ, file_path)

        software_path = os.path.abspath(__file__)

        software_path = f"{software_path}"
        add_to_startup(software_path)
    # 取消开机自启。 Rabbit 2023年10月24日19:11:20
    else:
        key = winreg.HKEY_CURRENT_USER
        key_value = "Software\\Microsoft\\Windows\\CurrentVersion\\Run"
        software_path = os.path.abspath(__file__)

        with winreg.OpenKey(key, key_value, 0, winreg.KEY_ALL_ACCESS) as registry_key:
            try:
                winreg.DeleteValue(registry_key, f"{software_path}")
            except FileNotFoundError:
                pass


def update():
    messagebox.showinfo("更新", "自动更新暂未实现，请手动更新")
    webbrowser.open("https://www.123pan.com/s/yof3jv-7xii.html")


def about():
    messagebox.showinfo("关于",
                        "版本：0.3\n开发者：Rabbit、Wu Chongwen\n特别致谢：Wu Chongwen\n这个软件是摸鱼无聊的时候做的，谁让我总是忘记下课时间啊")


menu_bar = tk.Menu(root)

file_menu = tk.Menu(menu_bar, tearoff=0)
menu_bar.add_cascade(label="设置", menu=file_menu)
file_menu.add_command(label="切换学院", command=switch_college)
file_menu.add_command(label="开机自启", command=self_starting)
file_menu.add_command(label="更新", command=update)

about_menu = tk.Menu(menu_bar, tearoff=0)
menu_bar.add_cascade(label="关于", menu=about_menu)
about_menu.add_command(label="关于", command=about)

root.config(menu=menu_bar)

label1 = tk.Label(root, text="当前时间:")
label1.grid(row=0, column=0, sticky='nw')
label2 = tk.Label(root, text="")
label2.grid(row=0, column=1, sticky='nw')
label3 = tk.Label(root, text="当前状态:")
label3.grid(row=1, column=0, sticky='nw')
label4 = tk.Label(root, text="")
label4.grid(row=1, column=1, sticky='nw')
label5 = tk.Label(root, text="当前课程:")
label5.grid(row=2, column=0, sticky='nw')
label6 = tk.Label(root, text="")
label6.grid(row=2, column=1, sticky='nw')
label7 = tk.Label(root, text="")
label7.grid(row=3, column=0, sticky='nw')
label8 = tk.Label(root, text="")
label8.grid(row=3, column=1, sticky='nw')

update_time()


def update_font_size():
    window_width = root.winfo_width()
    font_size = window_width // 19

    custom_font = font.Font(size=font_size)

    label1['font'] = custom_font
    label2['font'] = custom_font
    label3['font'] = custom_font
    label4['font'] = custom_font
    label5['font'] = custom_font
    label6['font'] = custom_font
    label7['font'] = custom_font
    label8['font'] = custom_font


root.bind('<Configure>', lambda event: update_font_size())

root.mainloop()
# 2023年10月20日 Rabbit & Wu Chongwen
