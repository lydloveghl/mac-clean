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
    print("\n[1/4] 清理旧构建...")
    for d in [BUILD_DIR, DIST_DIR, f"{DMG_NAME}.dmg"]:
        if os.path.exists(d):
            if os.path.isdir(d):
                shutil.rmtree(d)
            else:
                os.remove(d)
            print(f"  已删除: {d}")

    # 2. PyInstaller 打包 .app
    print("\n[2/4] PyInstaller 打包...")
    spec_file = os.path.join(project_dir, "MacCleaner.spec")
    pyinstaller_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        spec_file
    ]
    run_cmd(" ".join(pyinstaller_cmd), "PyInstaller 构建 .app")

    app_path = os.path.join(DIST_DIR, f"{APP_NAME}.app")
    if not os.path.exists(app_path):
        print(f"  ❌ 未找到 {app_path}")
        sys.exit(1)
    print(f"  ✅ 已生成: {app_path}")

    # 3. 创建 DMG 临时目录
    print("\n[3/4] 创建 DMG...")
    dmg_staging = os.path.join(DIST_DIR, "dmg_staging")
    if os.path.exists(dmg_staging):
        shutil.rmtree(dmg_staging)
    os.makedirs(dmg_staging)

    # 复制 .app 到临时目录
    shutil.copytree(app_path, os.path.join(dmg_staging, f"{APP_NAME}.app"))

    # 创建 Applications 软链接
    os.symlink("/Applications", os.path.join(dmg_staging, "Applications"))

    # 使用 hdiutil 创建 DMG
    dmg_path = os.path.join(project_dir, f"{DMG_NAME}.dmg")
    if os.path.exists(dmg_path):
        os.remove(dmg_path)

    hdiutil_cmd = (
        f'hdiutil create -volname "{APP_NAME}" '
        f'-srcfolder "{dmg_staging}" '
        f'-ov -format UDZO '
        f'"{dmg_path}"'
    )
    run_cmd(hdiutil_cmd, "hdiutil 生成 DMG")

    # 4. 清理
    print("\n[4/4] 清理临时文件...")
    shutil.rmtree(dmg_staging, ignore_errors=True)

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
