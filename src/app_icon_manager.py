#!/usr/bin/env python3
import os
import subprocess
from pathlib import Path
from PyQt6.QtGui import QIcon, QPixmap, QImage
from PyQt6.QtCore import QSize, Qt
from typing import Optional, Dict
import hashlib


class AppIconManager:
    """应用图标管理器"""
    
    _instance = None
    _icon_cache: Dict[str, QIcon] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._icon_cache = {}
        return cls._instance
    
    def get_app_icon(self, app_path: str, bundle_id: str = "") -> QIcon:
        """获取应用图标"""
        # 检查缓存
        cache_key = app_path or bundle_id
        if cache_key in self._icon_cache:
            return self._icon_cache[cache_key]
        
        icon = self._extract_icon(app_path, bundle_id)
        self._icon_cache[cache_key] = icon
        return icon
    
    def _extract_icon(self, app_path: str, bundle_id: str = "") -> QIcon:
        """从应用包中提取图标"""
        if not app_path:
            return self._get_default_icon()
        
        # 尝试从应用包中读取图标
        try:
            plist_path = os.path.join(app_path, "Contents", "Info.plist")
            if os.path.exists(plist_path):
                with open(plist_path, 'rb') as f:
                    plist = plistlib.load(f)
                
                icon_name = plist.get('CFBundleIconFile', '')
                if icon_name:
                    # 尝试不同的图标路径
                    icon_paths = [
                        os.path.join(app_path, "Contents", "Resources", icon_name),
                        os.path.join(app_path, "Contents", "Resources", f"{icon_name}.icns"),
                    ]
                    
                    for icon_path in icon_paths:
                        if os.path.exists(icon_path):
                            icon = QIcon(icon_path)
                            if not icon.isNull():
                                return icon
                    
                    # 尝试在Resources目录中查找icns文件
                    resources_dir = os.path.join(app_path, "Contents", "Resources")
                    if os.path.exists(resources_dir):
                        for file in os.listdir(resources_dir):
                            if file.endswith('.icns'):
                                icon = QIcon(os.path.join(resources_dir, file))
                                if not icon.isNull():
                                    return icon
        except:
            pass
        
        # 尝试使用mdls获取图标
        try:
            result = subprocess.run(
                ['mdls', '-name', 'kMDItemCFBundleIdentifier', app_path],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                # 使用系统API获取图标
                icon = QIcon.fromTheme(bundle_id)
                if not icon.isNull():
                    return icon
        except:
            pass
        
        return self._get_default_icon()
    
    def _get_default_icon(self) -> QIcon:
        """获取默认图标"""
        # 创建一个简单的默认图标
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.gray)
        return QIcon(pixmap)
    
    def get_icon_for_file_type(self, file_path: str, is_directory: bool = False) -> QIcon:
        """根据文件类型获取图标"""
        if is_directory:
            return QIcon.fromTheme("folder")
        
        ext = Path(file_path).suffix.lower()
        
        # 常见文件类型的图标映射
        type_icons = {
            '.plist': "text-x-generic",
            '.log': "text-x-generic",
            '.txt': "text-x-generic",
            '.json': "text-x-generic",
            '.xml': "text-x-generic",
            '.db': "application-x-executable",
            '.sqlite': "application-x-executable",
            '.png': "image-x-generic",
            '.jpg': "image-x-generic",
            '.jpeg': "image-x-generic",
            '.gif': "image-x-generic",
            '.icns': "image-x-generic",
            '.pdf': "application-pdf",
            '.zip': "application-x-archive",
            '.tar': "application-x-archive",
            '.gz': "application-x-archive",
        }
        
        icon_name = type_icons.get(ext, "text-x-generic")
        return QIcon.fromTheme(icon_name)


# 需要导入plistlib
import plistlib