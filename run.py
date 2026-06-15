#!/usr/bin/env python3
import sys
import os

def setup_qt_paths():
    """PyInstaller 打包后设置 Qt 插件路径"""
    if not getattr(sys, 'frozen', False):
        return
    
    # 获取 .app 包的根目录
    # sys.executable 在 MacCleaner.app/Contents/MacOS/MacCleaner
    app_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(sys.executable))))
    
    # Qt 插件目录
    qt_plugin_dir = os.path.join(app_dir, 'Contents', 'Frameworks', 'PyQt6', 'Qt6', 'plugins')
    if os.path.isdir(qt_plugin_dir):
        os.environ['QT_PLUGIN_PATH'] = qt_plugin_dir
        os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = os.path.join(qt_plugin_dir, 'platforms')
    
    # Qt 库目录
    qt_lib_dir = os.path.join(app_dir, 'Contents', 'Frameworks', 'PyQt6', 'Qt6', 'lib')
    if os.path.isdir(qt_lib_dir):
        os.environ['DYLD_LIBRARY_PATH'] = qt_lib_dir + ':' + os.environ.get('DYLD_LIBRARY_PATH', '')
    
    # src 目录
    src_dir = os.path.join(app_dir, 'Contents', 'Resources', 'src')
    if os.path.isdir(src_dir):
        sys.path.insert(0, src_dir)

setup_qt_paths()

# 添加src目录到Python路径
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, 'src')
if os.path.isdir(src_dir):
    sys.path.insert(0, src_dir)

from main import main

if __name__ == "__main__":
    main()
