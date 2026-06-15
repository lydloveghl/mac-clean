"""
PyInstaller runtime hook - 在 Python 解释器启动时、Qt 库加载之前执行。
确保 macOS 的 Bundle API 正常工作，并设置 Qt 插件路径。
"""
import os
import sys

if getattr(sys, 'frozen', False) and sys.platform == 'darwin':
    app_contents = os.path.dirname(os.path.dirname(os.path.abspath(sys.executable)))
    macos_dir = os.path.join(app_contents, 'MacOS')

    # 在 Qt 加载之前初始化 CFBundle，防止 CFBundleGetMainBundle() 返回 NULL
    # 这必须在 import PyQt6 之前发生
    try:
        import ctypes
        import ctypes.util
        cf = ctypes.cdll.LoadLibrary(ctypes.util.find_library('CoreFoundation'))
        cf.CFBundleGetMainBundle.restype = ctypes.c_void_p
        cf.CFBundleGetMainBundle.argtypes = []
        bundle = cf.CFBundleGetMainBundle()
        if bundle is None or bundle == 0:
            # 尝试通过 NSBundle 强制初始化
            objc = ctypes.cdll.LoadLibrary(ctypes.util.find_library('objc'))
            objc.objc_getClass.restype = ctypes.c_void_p
            objc.objc_getClass.argtypes = [ctypes.c_char_p]
            objc.sel_registerName.restype = ctypes.c_void_p
            objc.sel_registerName.argtypes = [ctypes.c_char_p]
            objc.objc_msgSend.restype = ctypes.c_void_p
            objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
            NSBundle = objc.objc_getClass(b'NSBundle')
            sel = objc.sel_registerName(b'mainBundle')
            objc.objc_msgSend(NSBundle, sel)
    except Exception:
        pass

    # Qt6 插件目录 — 根据 PyInstaller BUNDLE 实际布局设置
    # 实际路径: Contents/Frameworks/PyQt6/Qt6/plugins/
    frameworks_dir = os.path.join(app_contents, 'Frameworks')
    qt_plugins = os.path.join(frameworks_dir, 'PyQt6', 'Qt6', 'plugins')
    if os.path.isdir(qt_plugins):
        os.environ['QT_PLUGIN_PATH'] = qt_plugins
        os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = os.path.join(qt_plugins, 'platforms')

    # 禁用 Qt 权限插件的自动加载（导致崩溃的直接原因）
    os.environ.setdefault('QT_LOGGING_RULES', '*.debug=false')
