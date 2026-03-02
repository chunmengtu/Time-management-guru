import os
import sys
import datetime
import webbrowser
import json
import winreg

import pytz

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QLabel, QPushButton, QMenu, QSystemTrayIcon,
                               QDialog, QFormLayout, QComboBox, QTableWidget, QTableWidgetItem, 
                               QHeaderView, QMessageBox, QCheckBox, QGraphicsDropShadowEffect, QGroupBox)
from PySide6.QtCore import Qt, QTimer, Signal, QPoint, QRect
from PySide6.QtGui import QIcon, QFont, QAction, QColor, QPainter, QBrush, QPen, QCursor, QPixmap, QLinearGradient
from PySide6.QtSvg import QSvgRenderer

from core import (APP_NAME, RUN_KEY, SCHEDULE_FILE, DEFAULT_SCHEDULE, Segment,
                  load_schedule, save_schedule, ScheduleManager, AppSettings, get_network_time)

CITY_TZS = [
    ("America/Los_Angeles", 34.05, -118.24),
    ("America/Denver", 39.73, -104.99),
    ("America/Chicago", 41.87, -87.62),
    ("America/New_York", 40.71, -74.00),
    ("America/Caracas", 10.48, -66.90),
    ("America/Sao_Paulo", -23.55, -46.63),
    ("America/Buenos_Aires", -34.60, -58.38),
    ("Europe/London", 51.50, -0.12),
    ("Europe/Paris", 48.85, 2.35),
    ("Europe/Berlin", 52.52, 13.40),
    ("Europe/Moscow", 55.75, 37.61),
    ("Africa/Cairo", 30.04, 31.23),
    ("Africa/Johannesburg", -26.20, 28.04),
    ("Asia/Riyadh", 24.71, 46.67),
    ("Asia/Dubai", 25.20, 55.27),
    ("Asia/Tehran", 35.68, 51.38),
    ("Asia/Kolkata", 28.61, 77.20),
    ("Asia/Bangkok", 13.75, 100.50),
    ("Asia/Shanghai", 31.23, 121.47),
    ("Asia/Tokyo", 35.67, 139.65),
    ("Asia/Singapore", 1.35, 103.81),
    ("Australia/Perth", -31.95, 115.86),
    ("Australia/Sydney", -33.86, 151.20),
    ("Pacific/Auckland", -36.84, 174.76),
    ("Pacific/Honolulu", 21.30, -157.85),
    ("America/Anchorage", 61.21, -149.90)
]

COMBOBOX_STYLE = """
    QComboBox {
        background-color: #ffffff;
        border: 1px solid #dcdde1;
        border-radius: 6px;
        padding: 5px 8px;
        min-height: 28px;
        color: #2d3436;
    }
    QComboBox:hover {
        border: 1px solid #b2bec3;
    }
    QComboBox:focus {
        border: 1px solid #74b9ff;
        background-color: #f8fcff;
    }
    QComboBox QAbstractItemView {
        border: 1px solid #dcdde1;
        outline: none;
        selection-background-color: #dfe6e9;
        selection-color: #2d3436;
    }
"""

class MapWidget(QWidget):
    timezone_selected = Signal(str)

    def __init__(self, current_tz):
        super().__init__()
        self.setFixedSize(760, 380)
        self.current_tz = current_tz
        self.city_tzs = CITY_TZS
        self.city_tz_lookup = {tz: (lat, lon) for tz, lat, lon in self.city_tzs}
        self.map_svg_path = os.path.join(os.path.dirname(__file__), "maps", "World_location_map.svg")
        self.map_svg_renderer = QSvgRenderer(self.map_svg_path)
        self.display_tz = self._resolve_display_tz(self.current_tz)
        
    def set_timezone(self, tz):
        self.current_tz = tz
        self.display_tz = self._resolve_display_tz(tz)
        self.update()

    def _utc_offset_minutes(self, tz_name, now_utc):
        try:
            local_dt = now_utc.astimezone(pytz.timezone(tz_name))
            offset = local_dt.utcoffset()
            if offset is None:
                return 0
            return int(offset.total_seconds() // 60)
        except Exception:
            return None

    def _resolve_display_tz(self, tz_name):
        if tz_name in self.city_tz_lookup:
            return tz_name

        now_utc = datetime.datetime.now(datetime.timezone.utc)
        target_offset = self._utc_offset_minutes(tz_name, now_utc)

        region = tz_name.split('/')[0] if '/' in tz_name else ""
        region_candidates = [item for item in self.city_tzs if item[0].startswith(f"{region}/")]
        candidates = region_candidates if region_candidates else self.city_tzs

        if not candidates:
            return tz_name
        if target_offset is None:
            return candidates[0][0]

        best_tz = candidates[0][0]
        best_diff = float('inf')
        for candidate_tz, _, _ in candidates:
            candidate_offset = self._utc_offset_minutes(candidate_tz, now_utc)
            if candidate_offset is None:
                continue
            diff = abs(candidate_offset - target_offset)
            if diff < best_diff:
                best_diff = diff
                best_tz = candidate_tz
        return best_tz

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self.map_svg_renderer.isValid():
            self.map_svg_renderer.render(painter, self.rect())
            painter.fillRect(self.rect(), QColor(0, 0, 0, 40))
        else:
            grad = QLinearGradient(0, 0, 0, self.height())
            grad.setColorAt(0, QColor("#1e272e"))
            grad.setColorAt(1, QColor("#2f3542"))
            painter.fillRect(self.rect(), grad)
            
            painter.setPen(QPen(QColor(255, 255, 255, 15), 1, Qt.PenStyle.DashLine))
            for i in range(1, 6):
                y = self.height() * i / 6
                painter.drawLine(0, int(y), self.width(), int(y))
            for i in range(1, 12):
                x = self.width() * i / 12
                painter.drawLine(int(x), 0, int(x), self.height())
            
        w, h = self.width(), self.height()
        
        for tz, lat, lon in self.city_tzs:
            x = (lon + 180) / 360 * w
            y = (90 - lat) / 180 * h
            
            is_selected = (tz == self.display_tz)
            if is_selected:
                painter.setBrush(QBrush(QColor("#00d2d3")))
                painter.setPen(QPen(QColor("#ffffff"), 2))
                painter.drawEllipse(QPoint(int(x), int(y)), 6, 6)
                
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.setPen(QPen(QColor(0, 210, 211, 100), 3))
                painter.drawEllipse(QPoint(int(x), int(y)), 12, 12)
                
                painter.setPen(QPen(QColor("#ffffff")))
                font = painter.font()
                font.setBold(True)
                painter.setFont(font)
                city = self.current_tz.split('/')[-1].replace('_', ' ')

                text_x = int(x) + 12
                text_y = int(y) + 4
                fm = painter.fontMetrics()
                text_w = fm.horizontalAdvance(city)
                text_h = fm.height()

                if text_x + text_w > w - 6:
                    text_x = int(x) - 12 - text_w
                text_x = max(6, text_x)
                text_y = max(text_h, min(h - 4, text_y))

                painter.drawText(text_x, text_y, city)
            else:
                painter.setBrush(QBrush(QColor("#54a0ff")))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(QPoint(int(x), int(y)), 3, 3)

    def mousePressEvent(self, event):
        w, h = self.width(), self.height()
        ex, ey = event.pos().x(), event.pos().y()
        
        min_dist = float('inf')
        closest_tz = self.current_tz
        
        for tz, lat, lon in self.city_tzs:
            x = (lon + 180) / 360 * w
            y = (90 - lat) / 180 * h
            dist = (x - ex)**2 + (y - ey)**2
            if dist < min_dist:
                min_dist = dist
                closest_tz = tz
                
        if min_dist < 600:
            self.set_timezone(closest_tz)
            self.timezone_selected.emit(closest_tz)

class TimezoneMapDialog(QDialog):
    def __init__(self, current_tz, parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择时区")
        self.setFixedSize(800, 500)
        self.selected_tz = current_tz
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title_lbl = QLabel("点击地图上的点选择时区，或在下方下拉框中选择")
        title_lbl.setStyleSheet("color: #636e72; font-weight: bold; font-size: 14px;")
        layout.addWidget(title_lbl)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 50))
        shadow.setOffset(0, 5)

        map_container = QWidget()
        map_layout = QVBoxLayout(map_container)
        map_layout.setContentsMargins(0, 0, 0, 0)
        self.map_widget = MapWidget(self.selected_tz)
        map_layout.addWidget(self.map_widget)
        map_container.setGraphicsEffect(shadow)
        
        layout.addWidget(map_container)
        layout.addSpacing(10)

        bottom_layout = QHBoxLayout()
        self.tz_combo = QComboBox()
        self.tz_combo.addItems(pytz.all_timezones)
        self.tz_combo.setStyleSheet(COMBOBOX_STYLE)
        if self.selected_tz in pytz.all_timezones:
            self.tz_combo.setCurrentText(self.selected_tz)
        self.tz_combo.currentTextChanged.connect(self.on_combo_changed)
        self.map_widget.timezone_selected.connect(self.tz_combo.setCurrentText)

        bottom_layout.addWidget(QLabel("选择时区:"))
        bottom_layout.addWidget(self.tz_combo, 1)
        
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("确定")
        ok_btn.setStyleSheet("background-color: #0984e3; color: white; border-radius: 4px; padding: 6px 16px; font-weight: bold;")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet("background-color: #b2bec3; color: white; border-radius: 4px; padding: 6px 16px; font-weight: bold;")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        
        bottom_layout.addLayout(btn_layout)
        layout.addLayout(bottom_layout)
        
    def on_combo_changed(self, tz):
        self.selected_tz = tz
        self.map_widget.set_timezone(tz)

    def get_timezone(self):
        return self.tz_combo.currentText()

class ScheduleEditorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("课表编辑")
        self.setMinimumSize(600, 400)
        self.setup_ui()
        self.load_data()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["开始时间", "结束时间", "状态", "课程名", "下阶段提示"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)
        
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("添加行")
        add_btn.clicked.connect(self.add_row)
        del_btn = QPushButton("删除选中行")
        del_btn.clicked.connect(self.delete_row)
        reset_btn = QPushButton("恢复默认")
        reset_btn.clicked.connect(self.reset_default)
        
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self.save_data)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(del_btn)
        btn_layout.addWidget(reset_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)

    def load_data(self):
        try:
            with open(SCHEDULE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except:
            data = DEFAULT_SCHEDULE
            
        self.table.setRowCount(0)
        for row, item in enumerate(data):
            self.add_row(item)

    def add_row(self, item=None):
        row = self.table.rowCount()
        self.table.insertRow(row)
        if item is None:
            item = {"start": "00:00", "end": "00:00", "state": "", "course_name": "", "next_hint": ""}
            
        self.table.setItem(row, 0, QTableWidgetItem(item['start']))
        self.table.setItem(row, 1, QTableWidgetItem(item['end']))
        self.table.setItem(row, 2, QTableWidgetItem(item['state']))
        self.table.setItem(row, 3, QTableWidgetItem(item.get('course_name', '')))
        self.table.setItem(row, 4, QTableWidgetItem(item.get('next_hint', '')))

    def delete_row(self):
        rows = sorted(set(item.row() for item in self.table.selectedItems()), reverse=True)
        for row in rows:
            self.table.removeRow(row)

    def reset_default(self):
        reply = QMessageBox.question(self, "确认", "确定要恢复默认课表吗？", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.table.setRowCount(0)
            for item in DEFAULT_SCHEDULE:
                self.add_row(item)

    def save_data(self):
        data = []
        for row in range(self.table.rowCount()):
            item = {
                "start": self.table.item(row, 0).text() if self.table.item(row, 0) else "00:00",
                "end": self.table.item(row, 1).text() if self.table.item(row, 1) else "00:00",
                "state": self.table.item(row, 2).text() if self.table.item(row, 2) else "",
                "course_name": self.table.item(row, 3).text() if self.table.item(row, 3) else "",
                "next_hint": self.table.item(row, 4).text() if self.table.item(row, 4) else ""
            }
            try:
                datetime.datetime.strptime(item["start"], "%H:%M")
                datetime.datetime.strptime(item["end"], "%H:%M")
            except ValueError:
                QMessageBox.warning(self, "格式错误", f"第 {row+1} 行的时间格式错误，应为 HH:MM")
                return
            data.append(item)
            
        save_schedule(data)
        self.accept()

class SettingsDialog(QDialog):
    settings_changed = Signal()
    schedule_changed = Signal()

    def __init__(self, app_settings: AppSettings, parent=None):
        super().__init__(parent)
        self.app_settings = app_settings
        self.setWindowTitle("设置 - 时间管理大师")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        self.current_tz = self.app_settings.timezone
        self.setup_ui()
        self.load_current_settings()
        
    def setup_ui(self):
        self.setStyleSheet("""
            QDialog { background-color: #f5f6fa; }
            QGroupBox {
                background-color: white;
                border: 1px solid #dcdde1;
                border-radius: 8px;
                margin-top: 10px;
                font-weight: bold;
                color: #2f3640;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QLabel { color: #2f3640; font-size: 13px; }
            QCheckBox { color: #2f3640; font-size: 13px; }
            QPushButton {
                background-color: #0984e3;
                color: white;
                border-radius: 4px;
                padding: 6px 16px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #74b9ff; }
            QPushButton#CancelBtn { background-color: #b2bec3; }
            QPushButton#CancelBtn:hover { background-color: #dfe6e9; color: #2d3436; }
            QPushButton#ActionBtn {
                background-color: white;
                color: #0984e3;
                border: 1px solid #0984e3;
            }
            QPushButton#ActionBtn:hover {
                background-color: #0984e3;
                color: white;
            }
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        general_group = QGroupBox("常规设置")
        general_layout = QFormLayout(general_group)
        general_layout.setSpacing(15)
        general_layout.setContentsMargins(15, 25, 15, 15)
        
        self.time_format_combo = QComboBox()
        self.time_format_combo.setStyleSheet(COMBOBOX_STYLE)
        self.time_format_combo.addItems(["24小时制", "12小时制"])
        general_layout.addRow("时间格式:", self.time_format_combo)
        
        self.tz_btn = QPushButton("选择时区")
        self.tz_btn.setObjectName("ActionBtn")
        self.tz_btn.clicked.connect(self.open_timezone_map)
        general_layout.addRow("本地时区:", self.tz_btn)
        
        self.sync_time_cb = QCheckBox("启用世界时间校准")
        general_layout.addRow("", self.sync_time_cb)
        
        self.startup_cb = QCheckBox("开机自启动")
        general_layout.addRow("", self.startup_cb)
        
        main_layout.addWidget(general_group)
        
        schedule_group = QGroupBox("课表设置")
        schedule_layout = QVBoxLayout(schedule_group)
        schedule_layout.setContentsMargins(15, 25, 15, 15)
        
        self.edit_schedule_btn = QPushButton("编辑自定义课表")
        self.edit_schedule_btn.setObjectName("ActionBtn")
        self.edit_schedule_btn.clicked.connect(self.open_schedule_editor)
        schedule_layout.addWidget(self.edit_schedule_btn)
        
        main_layout.addWidget(schedule_group)
        
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self.save_settings)
        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("CancelBtn")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        
        main_layout.addStretch()
        main_layout.addLayout(btn_layout)

    def open_timezone_map(self):
        dlg = TimezoneMapDialog(self.current_tz, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.current_tz = dlg.get_timezone()
            self.tz_btn.setText(f"当前: {self.current_tz}")

    def load_current_settings(self):
        self.time_format_combo.setCurrentIndex(0 if self.app_settings.time_format_24h else 1)
        self.current_tz = self.app_settings.timezone
        self.tz_btn.setText(f"当前: {self.current_tz}")
        self.sync_time_cb.setChecked(self.app_settings.sync_world_time)
        self.startup_cb.setChecked(self.check_startup())

    def check_startup(self) -> bool:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ) as key:
                val, _ = winreg.QueryValueEx(key, APP_NAME)
                return True
        except FileNotFoundError:
            return False
            
    def set_startup(self, enable: bool):
        exe_path = os.path.abspath(sys.argv[0])
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_ALL_ACCESS) as key:
                if enable:
                    winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, exe_path)
                else:
                    try:
                        winreg.DeleteValue(key, APP_NAME)
                    except FileNotFoundError:
                        pass
        except Exception as e:
            QMessageBox.warning(self, "错误", f"设置开机自启失败: {e}")

    def save_settings(self):
        self.app_settings.time_format_24h = (self.time_format_combo.currentIndex() == 0)
        if self.current_tz not in pytz.all_timezones:
            QMessageBox.warning(self, "无效时区", f"{self.current_tz} 不是有效的时区格式。")
            return
        self.app_settings.timezone = self.current_tz
        self.app_settings.sync_world_time = self.sync_time_cb.isChecked()
        
        self.set_startup(self.startup_cb.isChecked())
        
        self.settings_changed.emit()
        self.accept()

    def open_schedule_editor(self):
        editor = ScheduleEditorDialog(self)
        if editor.exec() == QDialog.DialogCode.Accepted:
            self.schedule_changed.emit()


class ModernWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.app_settings = AppSettings()
        self.app_settings.settings.setValue("auto_start_handled", True)
        
        self.schedule_manager = ScheduleManager(load_schedule())
        self.time_offset = datetime.timedelta(0)
        
        self.setWindowTitle("时间管理大师")
        self.setMinimumSize(400, 250)
        self.setup_ui()
        self.apply_theme()
        
        self.setup_tray()
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(1000)
        
        if self.app_settings.sync_world_time:
            self.sync_time()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        panel = QWidget()
        panel.setObjectName("MainPanel")
        panel.setStyleSheet("QWidget#MainPanel { background-color: white; border-radius: 12px; }")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(20, 20, 20, 20)
        panel_layout.setSpacing(12)
        
        self.time_label_title = QLabel("当前时间:")
        self.time_label_val = QLabel("--:--:--")
        self.state_label_title = QLabel("当前状态:")
        self.state_label_val = QLabel("--")
        self.course_label_title = QLabel("当前课程:")
        self.course_label_val = QLabel("--")
        self.hint_label_title = QLabel("提示:")
        self.hint_label_val = QLabel("--:--:--")
        
        for lb in [self.time_label_title, self.time_label_val, 
                   self.state_label_title, self.state_label_val,
                   self.course_label_title, self.course_label_val,
                   self.hint_label_title, self.hint_label_val]:
            lb.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            
        def add_row(title, val, layout):
            h_layout = QHBoxLayout()
            h_layout.addWidget(title, 1)
            h_layout.addWidget(val, 3)
            layout.addLayout(h_layout)

        add_row(self.time_label_title, self.time_label_val, panel_layout)
        add_row(self.state_label_title, self.state_label_val, panel_layout)
        add_row(self.course_label_title, self.course_label_val, panel_layout)
        add_row(self.hint_label_title, self.hint_label_val, panel_layout)
        
        main_layout.addWidget(panel)
        
        btn_layout = QHBoxLayout()
        settings_btn = QPushButton("设置")
        settings_btn.setMinimumWidth(120)
        settings_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        settings_btn.clicked.connect(self.open_settings)
        btn_layout.addStretch()
        btn_layout.addWidget(settings_btn)
        main_layout.addLayout(btn_layout)

    def apply_theme(self):
        self.setStyleSheet('''
            QMainWindow { background-color: #f5f6fa; }
            QLabel { font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif; color: #2d3436; }
            QPushButton {
                background-color: #0984e3; color: white; border: none;
                border-radius: 6px; padding: 8px 16px; font-weight: bold; font-size: 14px;
            }
            QPushButton:hover { background-color: #74b9ff; }
            QPushButton:pressed { background-color: #0984e3; }
        ''')
        self.update_fonts()
        
    def update_fonts(self):
        width = self.width()
        base_size = max(10, width // 35)
        font = QFont("Microsoft YaHei", base_size)
        title_font = QFont("Microsoft YaHei", base_size, QFont.Weight.Bold)
        
        self.time_label_title.setFont(title_font)
        self.state_label_title.setFont(title_font)
        self.course_label_title.setFont(title_font)
        self.hint_label_title.setFont(title_font)
        
        self.time_label_val.setFont(font)
        self.state_label_val.setFont(font)
        self.course_label_val.setFont(font)
        self.hint_label_val.setFont(font)
        
        self.time_label_val.setStyleSheet("color: #00b894; font-weight: bold;")
        self.state_label_val.setStyleSheet("color: #e17055; font-weight: bold;")
        self.course_label_val.setStyleSheet("color: #d63031; font-weight: bold;")
        self.hint_label_val.setStyleSheet("color: #0984e3; font-weight: bold;")
        
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_fonts()

    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        icon = self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon)
        if icon.isNull():
            icon = self.style().standardIcon(self.style().StandardPixmap.SP_DriveHDIcon)
        self.tray_icon.setIcon(icon)
        
        tray_menu = QMenu()
        show_action = QAction("显示主界面", self)
        show_action.triggered.connect(self.showNormal)
        settings_action = QAction("设置", self)
        settings_action.triggered.connect(self.open_settings)
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        
        tray_menu.addAction(show_action)
        tray_menu.addAction(settings_action)
        
        def on_update():
            QTimer.singleShot(100, lambda: QMessageBox.information(self, "更新", "自动更新暂未实现，请手动更新。\n链接: https://www.123pan.com/s/yof3jv-7xii.html"))
            QTimer.singleShot(200, lambda: webbrowser.open("https://www.123pan.com/s/yof3jv-7xii.html"))
        
        update_action = QAction("检查更新", self)
        update_action.triggered.connect(on_update)
        tray_menu.addAction(update_action)
        
        def on_about():
            QTimer.singleShot(100, lambda: QMessageBox.information(self, "关于", "时间管理大师 \n版本：0.4\n开发者：Rabbit、Wu Chongwen"))
            
        about_action = QAction("关于", self)
        about_action.triggered.connect(on_about)
        tray_menu.addAction(about_action)
        
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        self.tray_icon.activated.connect(self.tray_activated)

    def tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.showNormal()
            self.activateWindow()

    def closeEvent(self, event):
        if self.tray_icon.isVisible():
            self.hide()
            try:
                if hasattr(QSystemTrayIcon, "MessageIcon"):
                    self.tray_icon.showMessage("时间管理大师", "程序已最小化到托盘运行", QSystemTrayIcon.MessageIcon.Information, 2000)
                else:
                    self.tray_icon.showMessage("时间管理大师", "程序已最小化到托盘运行", QSystemTrayIcon.Information, 2000)
            except Exception:
                pass
            event.ignore()
        else:
            event.accept()

    def sync_time(self):
        try:
            net_time = get_network_time()
            if net_time:
                local_now = datetime.datetime.now(datetime.timezone.utc)
                self.time_offset = net_time - local_now
                print(f"Time synced, offset: {self.time_offset.total_seconds()} seconds")
            else:
                self.time_offset = datetime.timedelta(0)
        except Exception as e:
            print(f"Sync time error: {e}")
            self.time_offset = datetime.timedelta(0)

    def tick(self):
        if self.app_settings.sync_world_time:
            now_utc = datetime.datetime.now(datetime.timezone.utc) + self.time_offset
        else:
            now_utc = datetime.datetime.now(datetime.timezone.utc)
        
        try:
            tz = pytz.timezone(self.app_settings.timezone)
        except pytz.UnknownTimeZoneError:
            tz = pytz.timezone("Asia/Shanghai")
            
        now_local = now_utc.astimezone(tz)
        
        if self.app_settings.time_format_24h:
            time_str = now_local.strftime("%H:%M:%S")
        else:
            am_pm = "上午" if now_local.hour < 12 else "下午"
            time_str = now_local.strftime("%I:%M:%S ") + am_pm
        self.time_label_val.setText(time_str)
        
        try:
            now_naive = now_local.replace(tzinfo=None)
            now_time = now_naive.time()
            
            seg = self.schedule_manager.current_segment(now_time)
            remaining = self.schedule_manager.remaining_to_next_change(now_naive)
            
            if hasattr(seg, 'state'):
                self.state_label_val.setText(seg.state if seg.state else "无状态")
            else:
                self.state_label_val.setText("无状态")
                
            if hasattr(seg, 'course_name') and getattr(seg, 'state', '') == "上课":
                self.course_label_val.setText(seg.course_name)
            else:
                self.course_label_val.setText("无")
            
            if hasattr(seg, 'next_hint'):
                hint_txt = seg.next_hint if seg.next_hint else "提示:"
            else:
                hint_txt = "提示:"
                
            self.hint_label_title.setText(hint_txt)
            
            total_seconds = int(remaining.total_seconds())
            if total_seconds < 0:
                total_seconds = 0
                
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            
            if hours > 0:
                self.hint_label_val.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
            else:
                self.hint_label_val.setText(f"{minutes:02d}:{seconds:02d}")
                
        except Exception as e:
            print(f"Schedule error: {e}")
        
        self.update()

    def open_settings(self):
        if hasattr(self, '_settings_dialog') and self._settings_dialog.isVisible():
            self._settings_dialog.activateWindow()
            return
            
        self._settings_dialog = SettingsDialog(self.app_settings, self)
        self._settings_dialog.settings_changed.connect(self.on_settings_changed)
        self._settings_dialog.schedule_changed.connect(self.on_schedule_changed)
        self._settings_dialog.show()
        
    def on_settings_changed(self):
        if self.app_settings.sync_world_time:
            self.sync_time()
        else:
            self.time_offset = datetime.timedelta(0)
        self.tick()
        
    def on_schedule_changed(self):
        self.schedule_manager.reload(load_schedule())
        self.tick()
