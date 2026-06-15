#!/usr/bin/env python3
import os
import plistlib
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Callable
import subprocess


@dataclass
class AppInfo:
    """应用程序信息"""
    name: str
    bundle_identifier: str
    version: str
    build_version: str
    size: int  # 字节
    path: str
    install_date: Optional[str] = None
    
    @property
    def size_display(self) -> str:
        """格式化显示大小"""
        if self.size < 1024:
            return f"{self.size} B"
        elif self.size < 1024 * 1024:
            return f"{self.size / 1024:.1f} KB"
        elif self.size < 1024 * 1024 * 1024:
            return f"{self.size / (1024 * 1024):.1f} MB"
        else:
            return f"{self.size / (1024 * 1024 * 1024):.2f} GB"


class AppScanner:
    """应用程序扫描器"""
    
    def __init__(self):
        self.applications: List[AppInfo] = []
        self._app_found_callback: Optional[Callable[[AppInfo], None]] = None
        self._size_update_callback: Optional[Callable[[int, int, str], None]] = None
        
    def set_app_found_callback(self, callback: Callable[[AppInfo], None]):
        """设置找到应用时的回调"""
        self._app_found_callback = callback
    
    def set_size_update_callback(self, callback: Callable[[int, int, str], None]):
        """设置大小更新回调"""
        self._size_update_callback = callback
        
    def scan_applications(self, scan_paths: Optional[List[str]] = None,
                         calculate_size: bool = True) -> List[AppInfo]:
        """扫描指定路径下的应用程序"""
        if scan_paths is None:
            scan_paths = [
                "/Applications",
                str(Path.home() / "Applications"),
                "/System/Applications"
            ]

        self.applications = []
        self._scanned_paths = set()

        # 第一阶段：快速扫描标准目录
        for scan_path in scan_paths:
            if os.path.exists(scan_path):
                self._scan_directory_fast(scan_path)

        # Spotlight 补充扫描
        self._scan_with_spotlight()

        # 按名称排序
        self.applications.sort(key=lambda x: x.name.lower())

        # 第二阶段：后台计算大小（可选）
        if calculate_size:
            self._calculate_all_sizes()

        return self.applications
    
    def scan_applications_async(self, scan_paths: Optional[List[str]] = None):
        """异步扫描，每找到一个应用就回调"""
        if scan_paths is None:
            scan_paths = [
                "/Applications",
                str(Path.home() / "Applications"),
                "/System/Applications"
            ]

        self.applications = []
        self._scanned_paths = set()

        # 快速扫描标准目录
        for scan_path in scan_paths:
            if os.path.exists(scan_path):
                self._scan_directory_fast(scan_path)

        # 使用 mdfind 补充扫描（发现非标准位置的应用）
        self._scan_with_spotlight()

        # 按名称排序
        self.applications.sort(key=lambda x: x.name.lower())

        return self.applications

    def _scan_with_spotlight(self):
        """使用 Spotlight (mdfind) 发现非标准位置安装的应用"""
        try:
            result = subprocess.run(
                ['mdfind', 'kMDItemContentType == "com.apple.application-bundle"'],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    app_path = line.strip()
                    if not app_path or not app_path.endswith('.app'):
                        continue
                    if app_path in self._scanned_paths:
                        continue
                    # 排除系统内置框架中的 .app
                    if '/System/Library/' in app_path or '/Library/Apple/' in app_path:
                        continue
                    if os.path.isdir(app_path):
                        app_info = self._get_app_info_fast(app_path)
                        if app_info:
                            self._scanned_paths.add(app_path)
                            self.applications.append(app_info)
                            if self._app_found_callback:
                                self._app_found_callback(app_info)
        except (subprocess.TimeoutExpired, Exception):
            pass
    
    def _scan_directory_fast(self, directory: str):
        """快速扫描目录，不计算大小"""
        try:
            items = os.listdir(directory)
            for item in items:
                if item.endswith('.app'):
                    app_path = os.path.join(directory, item)
                    if app_path in self._scanned_paths:
                        continue
                    if os.path.isdir(app_path):
                        app_info = self._get_app_info_fast(app_path)
                        if app_info:
                            self._scanned_paths.add(app_path)
                            self.applications.append(app_info)
                            if self._app_found_callback:
                                self._app_found_callback(app_info)
        except PermissionError:
            pass
    
    def _get_app_info_fast(self, app_path: str) -> Optional[AppInfo]:
        """快速获取应用程序信息（不计算大小）"""
        try:
            plist_path = os.path.join(app_path, "Contents", "Info.plist")
            if not os.path.exists(plist_path):
                return None
            
            with open(plist_path, 'rb') as f:
                plist_data = plistlib.load(f)
            
            app_name = os.path.splitext(os.path.basename(app_path))[0]
            if 'CFBundleDisplayName' in plist_data:
                app_name = plist_data['CFBundleDisplayName']
            elif 'CFBundleName' in plist_data:
                app_name = plist_data['CFBundleName']
            
            version = plist_data.get('CFBundleShortVersionString', '1.0.0')
            build_version = plist_data.get('CFBundleVersion', '1')
            bundle_id = plist_data.get('CFBundleIdentifier', '')
            
            return AppInfo(
                name=app_name,
                bundle_identifier=bundle_id,
                version=version,
                build_version=build_version,
                size=0,  # 先不计算大小
                path=app_path,
                install_date=None
            )
        except Exception:
            return None
    
    def _calculate_all_sizes(self):
        """计算所有应用的大小"""
        total = len(self.applications)
        for i, app in enumerate(self.applications):
            if self._size_update_callback:
                self._size_update_callback(i + 1, total, app.name)
            app.size = self._calculate_size(app.path)
    
    def calculate_app_size(self, app: AppInfo) -> int:
        """计算单个应用的大小"""
        return self._calculate_size(app.path)
    
    def _calculate_size(self, path: str) -> int:
        """计算目录大小"""
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(filepath)
                    except (OSError, IOError):
                        pass
        except (OSError, IOError):
            pass
        return total_size
    
    def get_app_cache_paths(self, bundle_identifier: str) -> List[str]:
        """获取应用相关的缓存文件路径"""
        if not bundle_identifier:
            return []
        
        cache_paths = []
        
        # 常见缓存目录
        cache_dirs = [
            Path.home() / "Library" / "Caches",
            Path.home() / "Library" / "Preferences",
            Path.home() / "Library" / "Application Support",
            Path.home() / "Library" / "Containers",
            Path.home() / "Library" / "Logs",
            Path.home() / "Library" / "Saved Application State",
            Path.home() / "Library" / "WebKit",
            Path("/Library/Caches"),
            Path("/Library/Preferences"),
            Path("/Library/Application Support"),
        ]
        
        # 获取Bundle ID的各部分
        bundle_parts = bundle_identifier.split('.')
        if len(bundle_parts) >= 2:
            # 尝试不同的匹配模式
            patterns = [
                bundle_identifier,  # 完整Bundle ID
                f"{bundle_parts[0]}.{bundle_parts[1]}",  # 前两部分
                bundle_parts[-1],  # 最后一部分（应用名）
            ]

            for cache_dir in cache_dirs:
                if not cache_dir.exists():
                    continue

                try:
                    for item in cache_dir.iterdir():
                        item_name = item.name.lower()
                        for pattern in patterns:
                            if pattern.lower() in item_name:
                                cache_paths.append(str(item))
                                break
                except PermissionError:
                    pass

        # VSCode 特殊处理：将 ~/.vscode/ 也纳入缓存搜索
        if bundle_identifier == 'com.microsoft.VSCode':
            vscode_dir = Path.home() / ".vscode"
            if vscode_dir.exists():
                cache_paths.append(str(vscode_dir))

        return cache_paths