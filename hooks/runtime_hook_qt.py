"""
PyInstaller runtime hook - 在 Python 解释器启动时、Qt 库加载之前执行。
设置 Qt 所需的环境变量，确保 Qt 能找到自己的插件和框架。
"""
import os
import sys

if getattr(sys, 'frozen', False):
    # sys.executable = .../MacCleaner.app/Contents/MacOS/MacCleaner
    app_contents = os.path.dirname(os.path.dirname(os.path.abspath(sys.executable)))
    
    # Qt6 插件目录
    qt_plugins = os.path.join(app_contents, 'Frameworks', 'PyQt6', 'Qt6', 'plugins')
    if os.path.isdir(qt_plugins):
        os.environ['QT_PLUGIN_PATH'] = qt_plugins
        os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = os.path.join(qt_plugins, 'platforms')
    
    # Qt6 库目录
    qt_lib = os.path.join(app_contents, 'Frameworks', 'PyQt6', 'Qt6', 'lib')
    if os.path.isdir(qt_lib):
        existing = os.environ.get('DYLD_LIBRARY_PATH', '')
        os.environ['DYLD_LIBRARY_PATH'] = qt_lib + (':' + existing if existing else '')
    
    # 设置 QLibraryInfo 前缀，让 Qt 直接使用打包的路径
    os.environ['QT_PREFIX_PATH'] = os.path.join(app_contents, 'Frameworks', 'PyQt6', 'Qt6')
