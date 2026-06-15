#!/usr/bin/env python3
import sys
import os
import traceback

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from PyQt6.QtWidgets import QApplication
    from main import MainWindow
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    
    print("应用程序已启动，请查看图形界面。")
    sys.exit(app.exec())
    
except Exception as e:
    print(f"启动错误: {e}")
    traceback.print_exc()
    sys.exit(1)