#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont

from ui import ModernWindow

def main():
    app = QApplication(sys.argv)
    
    # 强制在 Windows 下使用较好的字体渲染
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)
    
    app.setApplicationName("TimeManagementGuru")
    app.setOrganizationName("MyCompany")
    
    window = ModernWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
