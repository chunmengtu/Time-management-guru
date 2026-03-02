import os
import datetime
import json
import requests
from dataclasses import dataclass
from typing import Optional, List
from PySide6.QtCore import QSettings

import pytz

APP_NAME = "TimeManagementGuru"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
CONFIG_FILE = "config.json"
SCHEDULE_FILE = "schedule.json"

DEFAULT_SCHEDULE = [
    {"start": "08:00", "end": "08:45", "state": "上课", "course_name": "第一节课", "next_hint": "距离下课还有:"},
    {"start": "08:45", "end": "08:55", "state": "下课", "course_name": "", "next_hint": "距离上课还有:"},
    {"start": "08:55", "end": "09:40", "state": "上课", "course_name": "第二节课", "next_hint": "距离下课还有:"},
    {"start": "09:40", "end": "09:50", "state": "下课", "course_name": "", "next_hint": "距离上课还有:"},
    {"start": "09:50", "end": "10:35", "state": "上课", "course_name": "第三节课", "next_hint": "距离下课还有:"},
    {"start": "10:35", "end": "10:45", "state": "下课", "course_name": "", "next_hint": "距离上课还有:"},
    {"start": "10:45", "end": "11:30", "state": "上课", "course_name": "第四节课", "next_hint": "距离下课还有:"},
    {"start": "11:30", "end": "13:00", "state": "放学", "course_name": "", "next_hint": "距离上课还有:"},
    {"start": "13:00", "end": "13:45", "state": "上课", "course_name": "第五节课", "next_hint": "距离下课还有:"},
    {"start": "13:45", "end": "13:55", "state": "下课", "course_name": "", "next_hint": "距离上课还有:"},
    {"start": "13:55", "end": "14:40", "state": "上课", "course_name": "第六节课", "next_hint": "距离下课还有:"},
    {"start": "14:40", "end": "14:50", "state": "下课", "course_name": "", "next_hint": "距离上课还有:"},
    {"start": "14:50", "end": "15:35", "state": "上课", "course_name": "第七节课", "next_hint": "距离下课还有:"},
    {"start": "15:35", "end": "15:45", "state": "下课", "course_name": "", "next_hint": "距离上课还有:"},
    {"start": "15:45", "end": "16:30", "state": "上课", "course_name": "第八节课", "next_hint": "距离下课还有:"},
    {"start": "16:30", "end": "18:00", "state": "放学", "course_name": "", "next_hint": "距离上课还有:"},
    {"start": "18:00", "end": "18:45", "state": "上课", "course_name": "第九节课", "next_hint": "距离下课还有:"},
    {"start": "18:45", "end": "18:55", "state": "下课", "course_name": "", "next_hint": "距离上课还有:"},
    {"start": "18:55", "end": "19:40", "state": "上课", "course_name": "第十节课", "next_hint": "距离下课还有:"},
    {"start": "19:40", "end": "19:50", "state": "下课", "course_name": "", "next_hint": "距离上课还有:"},
    {"start": "19:50", "end": "20:30", "state": "上课", "course_name": "第十一节课", "next_hint": "距离下课还有:"},
    {"start": "20:30", "end": "08:00", "state": "放学", "course_name": "", "next_hint": "距离上课还有:"},
]

@dataclass(frozen=True)
class Segment:
    start: datetime.time
    end: datetime.time
    state: str
    course_name: str = ""
    next_hint: str = ""

def load_schedule() -> List[Segment]:
    try:
        if os.path.exists(SCHEDULE_FILE):
            with open(SCHEDULE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = DEFAULT_SCHEDULE
            save_schedule(data)
            
        segments = []
        for item in data:
            h1, m1 = map(int, item['start'].split(':'))
            h2, m2 = map(int, item['end'].split(':'))
            segments.append(Segment(
                start=datetime.time(hour=h1, minute=m1),
                end=datetime.time(hour=h2, minute=m2),
                state=item['state'],
                course_name=item.get('course_name', ''),
                next_hint=item.get('next_hint', '')
            ))
        return segments
    except Exception as e:
        print(f"Load schedule error: {e}")
        return []

def save_schedule(data: List[dict]):
    try:
        with open(SCHEDULE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Save schedule error: {e}")

class ScheduleManager:
    def __init__(self, segments: List[Segment]):
        self.segments = segments
        self._change_points = sorted({seg.end for seg in segments})

    def reload(self, segments: List[Segment]):
        self.segments = segments
        self._change_points = sorted({seg.end for seg in segments})

    def _time_in_range(self, now: datetime.time, start: datetime.time, end: datetime.time) -> bool:
        if start <= end:
            return start <= now < end
        else:
            return now >= start or now < end

    def current_segment(self, now: datetime.time) -> Segment:
        if not self.segments:
            return Segment(start=datetime.time(0, 0), end=datetime.time(23, 59, 59), state="未知", next_hint="")
            
        for seg in self.segments:
            if self._time_in_range(now, seg.start, seg.end):
                return seg
        return Segment(start=datetime.time(0, 0), end=datetime.time(23, 59, 59), state="未知", next_hint="")

    def next_change_datetime(self, now_dt: datetime.datetime) -> datetime.datetime:
        if not self._change_points:
            return now_dt + datetime.timedelta(days=1)
            
        today = now_dt.date()
        
        for cp in self._change_points:
            cp_dt = datetime.datetime.combine(today, cp)
            if cp_dt > now_dt:
                return cp_dt

        tomorrow = today + datetime.timedelta(days=1)
        if self._change_points:
            first_cp = self._change_points[0]
            return datetime.datetime.combine(tomorrow, first_cp)
        return now_dt

    def remaining_to_next_change(self, now_dt: datetime.datetime) -> datetime.timedelta:
        return self.next_change_datetime(now_dt) - now_dt


class AppSettings:
    def __init__(self):
        self.settings = QSettings("MyCompany", "TimeManagementGuru")
        self._load_defaults()
        
    def _load_defaults(self):
        if not self.settings.contains("time_format_24h"):
            self.settings.setValue("time_format_24h", True)
        if not self.settings.contains("timezone"):
            self.settings.setValue("timezone", "Asia/Shanghai")
        if not self.settings.contains("sync_world_time"):
            self.settings.setValue("sync_world_time", False)
            
    @property
    def time_format_24h(self) -> bool:
        return self.settings.value("time_format_24h", True, type=bool)
        
    @time_format_24h.setter
    def time_format_24h(self, value: bool):
        self.settings.setValue("time_format_24h", value)
        
    @property
    def timezone(self) -> str:
        return self.settings.value("timezone", "Asia/Shanghai", type=str)
        
    @timezone.setter
    def timezone(self, tz: str):
        self.settings.setValue("timezone", tz)
        
    @property
    def sync_world_time(self) -> bool:
        return self.settings.value("sync_world_time", False, type=bool)
        
    @sync_world_time.setter
    def sync_world_time(self, val: bool):
        self.settings.setValue("sync_world_time", val)


def get_network_time() -> Optional[datetime.datetime]:
    try:
        resp = requests.head("https://www.baidu.com", timeout=3.0, allow_redirects=True)
        date_hdr = resp.headers.get("Date") or resp.headers.get("date")
        if not date_hdr:
            return None
        # Format example: 'Tue, 28 Feb 2026 12:00:00 GMT'
        # date_hdr[5:25] gives '28 Feb 2026 12:00:00'
        dt = datetime.datetime.strptime(date_hdr[5:25], "%d %b %Y %H:%M:%S")
        return dt.replace(tzinfo=datetime.timezone.utc)
    except Exception as e:
        print(f"Network time error: {e}")
        return None
