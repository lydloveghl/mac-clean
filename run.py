#!/usr/bin/env python3
import sys
import os

def setup_paths():
    """PyInstaller 打包后设置路径"""
    if not getattr(sys, 'frozen', False):
        return

    # sys.executable = .../MacCleaner.app/Contents/MacOS/MacCleaner
    macos_dir = os.path.dirname(os.path.abspath(sys.executable))
    contents_dir = os.path.dirname(macos_dir)

    # src 目录（datas 中的 src -> src 映射到 Contents/MacOS/src）
    src_dir = os.path.join(macos_dir, 'src')
    if os.path.isdir(src_dir):
        sys.path.insert(0, src_dir)

    # 也检查 Resources 下
    src_dir_res = os.path.join(contents_dir, 'Resources', 'src')
    if os.path.isdir(src_dir_res):
        sys.path.insert(0, src_dir_res)

setup_paths()

# 开发模式：添加src目录到Python路径
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, 'src')
if os.path.isdir(src_dir):
    sys.path.insert(0, src_dir)

from main import main

if __name__ == "__main__":
    main()
