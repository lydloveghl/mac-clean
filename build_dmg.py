#!/usr/bin/env python3
"""
Mac Cleaner DMG 打包脚本
用法: python3 build_dmg.py
"""
import os
import sys
import shutil
import subprocess

APP_NAME = "MacCleaner"
DMG_NAME = "MacCleaner"
VERSION = "1.0.0"
DIST_DIR = "dist"
BUILD_DIR = "build"

def run_cmd(cmd, desc=""):
    print(f"  -> {desc or cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ❌ 失败: {result.stderr}")
        sys.exit(1)
    return result

def main():
    project_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_dir)

    print("=" * 50)
    print(f"  打包 {APP_NAME} v{VERSION}")
    print("=" * 50)

    # 1. 清理旧构建
    print("\n[1/5] 清理旧构建...")
    for d in [BUILD_DIR, DIST_DIR, f"{DMG_NAME}.dmg"]:
        if os.path.exists(d):
            if os.path.isdir(d):
                shutil.rmtree(d)
            else:
                os.remove(d)
            print(f"  已删除: {d}")

    # 2. PyInstaller 打包 .app
    print("\n[2/5] PyInstaller 打包...")
    pyinstaller_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", APP_NAME,
        "--windowed",
        "--noconfirm",
        "--clean",
        "--add-data", "src:src",
        "--hidden-import", "PyQt6",
        "--hidden-import", "PyQt6.QtWidgets",
        "--hidden-import", "PyQt6.QtCore",
        "--hidden-import", "PyQt6.QtGui",
        "--hidden-import", "psutil",
        "--hidden-import", "plistlib",
        "--osx-bundle-identifier", "com.maccleaner.app",
        "run.py"
    ]
    run_cmd(" ".join(pyinstaller_cmd), "PyInstaller 构建 .app")

    app_path = os.path.join(DIST_DIR, f"{APP_NAME}.app")
    if not os.path.exists(app_path):
        print(f"  ❌ 未找到 {app_path}")
        sys.exit(1)
    print(f"  ✅ 已生成: {app_path}")

    # 3. 创建 DMG 背景和设置
    print("\n[3/5] 准备 DMG 配置...")

    # 创建 dmgbuild settings 文件
    settings_content = f'''
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

filename = "{DMG_NAME}.dmg"
volume_name = "{APP_NAME}"
format = "UDBZ"
size = "200M"
files = ["{DIST_DIR}/{APP_NAME}.app"]
symlinks = {{"Applications": "/Applications"}}
background = "builtin-retina"
icon_locations = {{
    "{APP_NAME}.app": (140, 150),
    "Applications": (400, 150),
}}
window_rect = ((200, 120), (560, 350))
icon_size = 80
text_size = 14
'''
    with open("dmg_settings.py", "w", encoding="utf-8") as f:
        f.write(settings_content)

    # 4. 构建 DMG
    print("\n[4/5] 构建 DMG...")
    dmg_cmd = f'{sys.executable} -m dmgbuild -s dmg_settings.py "{APP_NAME}" "{DMG_NAME}.dmg"'
    run_cmd(dmg_cmd, "dmgbuild 生成 DMG")

    # 5. 清理临时文件
    print("\n[5/5] 清理临时文件...")
    for f in ["dmg_settings.py"]:
        if os.path.exists(f):
            os.remove(f)

    dmg_path = os.path.join(project_dir, f"{DMG_NAME}.dmg")
    if os.path.exists(dmg_path):
        size_mb = os.path.getsize(dmg_path) / (1024 * 1024)
        print(f"\n{'=' * 50}")
        print(f"  ✅ 打包完成!")
        print(f"  📦 DMG: {dmg_path}")
        print(f"  📏 大小: {size_mb:.1f} MB")
        print(f"{'=' * 50}")
    else:
        print("\n  ❌ DMG 生成失败")
        sys.exit(1)

if __name__ == "__main__":
    main()
