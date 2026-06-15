#!/usr/bin/env python3
import os
import plistlib
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
from enum import Enum
import subprocess


class FileType(Enum):
    """文件类型"""
    CACHE = "缓存"
    LOG = "日志"
    TEMP = "临时文件"
    PREFERENCE = "偏好设置"
    APPLICATION_SUPPORT = "应用支持"
    CONTAINER = "容器数据"
    DOWNLOAD = "下载"
    LARGE_FILE = "大文件"
    UNKNOWN = "未知"


class ImpactLevel(Enum):
    """影响级别"""
    SAFE = "安全"
    LOW = "低风险"
    MEDIUM = "中风险"
    HIGH = "高风险"
    CRITICAL = "危险"


@dataclass
class FileItem:
    """文件项"""
    path: str
    name: str
    size: int
    file_type: FileType
    owner_app: Optional[str] = None
    owner_bundle_id: Optional[str] = None
    impact_level: ImpactLevel = ImpactLevel.SAFE
    impact_description: str = ""
    last_modified: Optional[str] = None
    is_directory: bool = False
    
    @property
    def size_display(self) -> str:
        if self.size < 1024:
            return f"{self.size} B"
        elif self.size < 1024 * 1024:
            return f"{self.size / 1024:.1f} KB"
        elif self.size < 1024 * 1024 * 1024:
            return f"{self.size / (1024 * 1024):.1f} MB"
        else:
            return f"{self.size / (1024 * 1024 * 1024):.2f} GB"


@dataclass
class AppFileInfo:
    """应用文件信息"""
    app_name: str
    bundle_id: str
    app_path: str
    cache_files: List[FileItem] = field(default_factory=list)
    log_files: List[FileItem] = field(default_factory=list)
    preference_files: List[FileItem] = field(default_factory=list)
    support_files: List[FileItem] = field(default_factory=list)
    container_files: List[FileItem] = field(default_factory=list)
    other_files: List[FileItem] = field(default_factory=list)
    
    @property
    def total_size(self) -> int:
        all_files = (self.cache_files + self.log_files + self.preference_files + 
                    self.support_files + self.container_files + self.other_files)
        return sum(f.size for f in all_files)
    
    @property
    def total_size_display(self) -> str:
        size = self.total_size
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        else:
            return f"{size / (1024 * 1024 * 1024):.2f} GB"


class FileAnalyzer:
    """文件分析器"""
    
    CACHE_DIRS = [
        Path.home() / "Library" / "Caches",
        Path("/Library/Caches"),
    ]
    
    LOG_DIRS = [
        Path.home() / "Library" / "Logs",
        Path("/Library/Logs"),
    ]
    
    PREFERENCE_DIRS = [
        Path.home() / "Library" / "Preferences",
        Path("/Library/Preferences"),
    ]
    
    SUPPORT_DIRS = [
        Path.home() / "Library" / "Application Support",
        Path("/Library/Application Support"),
    ]
    
    CONTAINER_DIRS = [
        Path.home() / "Library" / "Containers",
    ]
    
    TEMP_DIRS = [
        Path("/tmp"),
        Path.home() / ".Trash",
    ]
    
    def __init__(self):
        self._installed_apps: Dict[str, str] = {}
        self._app_paths: Dict[str, str] = {}
        self._scan_installed_apps()
    
    def _scan_installed_apps(self):
        """扫描已安装应用"""
        app_dirs = ["/Applications", str(Path.home() / "Applications"), "/System/Applications"]
        
        for app_dir in app_dirs:
            if not os.path.exists(app_dir):
                continue
            try:
                for item in os.listdir(app_dir):
                    if item.endswith('.app'):
                        app_path = os.path.join(app_dir, item)
                        plist_path = os.path.join(app_path, "Contents", "Info.plist")
                        if os.path.exists(plist_path):
                            try:
                                with open(plist_path, 'rb') as f:
                                    plist = plistlib.load(f)
                                bundle_id = plist.get('CFBundleIdentifier', '')
                                app_name = plist.get('CFBundleDisplayName') or plist.get('CFBundleName') or os.path.splitext(item)[0]
                                if bundle_id:
                                    self._installed_apps[bundle_id] = app_name
                                    self._app_paths[bundle_id] = app_path
                            except:
                                pass
            except PermissionError:
                pass
    
    def get_app_path(self, bundle_id: str) -> str:
        """获取应用路径"""
        return self._app_paths.get(bundle_id, "")
    
    def get_app_name_from_path(self, path: str) -> Tuple[Optional[str], Optional[str]]:
        """从文件路径推断所属应用"""
        path_lower = path.lower()
        
        for bundle_id, app_name in self._installed_apps.items():
            if bundle_id.lower() in path_lower:
                return app_name, bundle_id
        
        parts = Path(path).parts
        for part in parts:
            part_lower = part.lower()
            for bundle_id, app_name in self._installed_apps.items():
                if app_name.lower() in part_lower or bundle_id.split('.')[-1].lower() in part_lower:
                    return app_name, bundle_id
        
        return None, None
    
    def analyze_file_impact(self, file_item: FileItem) -> FileItem:
        """分析删除文件的影响"""
        path = file_item.path
        file_type = file_item.file_type
        
        if not file_item.owner_app:
            app_name, bundle_id = self.get_app_name_from_path(path)
            file_item.owner_app = app_name
            file_item.owner_bundle_id = bundle_id
        
        if file_type == FileType.CACHE:
            file_item.impact_level = ImpactLevel.SAFE
            file_item.impact_description = "缓存文件，删除后应用会自动重新生成"
        elif file_type == FileType.LOG:
            file_item.impact_level = ImpactLevel.SAFE
            file_item.impact_description = "日志文件，删除不影响应用运行"
        elif file_type == FileType.TEMP:
            file_item.impact_level = ImpactLevel.SAFE
            file_item.impact_description = "临时文件，可以安全删除"
        elif file_type == FileType.PREFERENCE:
            file_item.impact_level = ImpactLevel.LOW
            file_item.impact_description = "偏好设置文件，删除后应用将恢复默认设置"
        elif file_type == FileType.APPLICATION_SUPPORT:
            if any(ext in path.lower() for ext in ['.db', '.sqlite', '.plist', '.json']):
                file_item.impact_level = ImpactLevel.MEDIUM
                file_item.impact_description = "可能包含用户数据，删除后数据将丢失"
            else:
                file_item.impact_level = ImpactLevel.LOW
                file_item.impact_description = "应用支持文件，删除后应用可能需要重新下载或配置"
        elif file_type == FileType.CONTAINER:
            file_item.impact_level = ImpactLevel.MEDIUM
            file_item.impact_description = "应用容器数据，删除后应用数据将完全丢失"
        
        # 特殊文件检查
        if 'keychain' in path.lower():
            file_item.impact_level = ImpactLevel.CRITICAL
            file_item.impact_description = "钥匙串文件，删除将导致密码和证书丢失"
        elif 'mail' in path.lower() and ('envelope' in path.lower() or 'index' in path.lower()):
            file_item.impact_level = ImpactLevel.HIGH
            file_item.impact_description = "邮件索引文件，删除后邮件需要重新索引"
        elif 'safari' in path.lower() and 'history' in path.lower():
            file_item.impact_level = ImpactLevel.MEDIUM
            file_item.impact_description = "Safari浏览历史，删除后无法恢复"
        
        return file_item
    
    def _get_dir_size_fast(self, path: str) -> int:
        """快速计算目录大小（使用du命令）"""
        try:
            result = subprocess.run(['du', '-sk', path], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                # du输出格式: "大小\t路径"
                size_kb = int(result.stdout.split('\t')[0])
                return size_kb * 1024
        except:
            pass
        return 0
    
    def _get_file_size(self, path: str) -> int:
        """获取文件大小"""
        try:
            if os.path.isdir(path):
                return self._get_dir_size_fast(path)
            return os.path.getsize(path)
        except:
            return 0
    
    def _get_last_modified(self, path: str) -> Optional[str]:
        """获取最后修改时间"""
        try:
            mtime = os.path.getmtime(path)
            from datetime import datetime
            return datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
        except:
            return None
    
    def _classify_file(self, path: str) -> FileType:
        """分类文件类型"""
        path_str = str(path)
        path_lower = path_str.lower()
        
        # 检查是否在容器目录
        for container_dir in self.CONTAINER_DIRS:
            if path_str.startswith(str(container_dir)):
                return FileType.CONTAINER
        
        # 检查是否在缓存目录
        for cache_dir in self.CACHE_DIRS:
            if path_str.startswith(str(cache_dir)):
                return FileType.CACHE
        
        # 检查是否在日志目录
        for log_dir in self.LOG_DIRS:
            if path_str.startswith(str(log_dir)):
                return FileType.LOG
        
        # 检查是否在偏好设置目录
        for pref_dir in self.PREFERENCE_DIRS:
            if path_str.startswith(str(pref_dir)):
                return FileType.PREFERENCE
        
        # 检查是否在应用支持目录
        for support_dir in self.SUPPORT_DIRS:
            if path_str.startswith(str(support_dir)):
                return FileType.APPLICATION_SUPPORT
        
        # 检查是否是临时文件
        for temp_dir in self.TEMP_DIRS:
            if path_str.startswith(str(temp_dir)):
                return FileType.TEMP
        
        # 检查文件扩展名
        ext = Path(path).suffix.lower()
        if ext in ['.log', '.crash']:
            return FileType.LOG
        elif ext in ['.plist', '.pref']:
            return FileType.PREFERENCE
        elif ext in ['.cache', '.tmp']:
            return FileType.CACHE
        
        return FileType.UNKNOWN
    
    def scan_cache_files(self, progress_callback=None) -> List[FileItem]:
        """扫描缓存文件 - 优化版本，先快速列出，大小延迟计算"""
        results = []
        
        for cache_dir in self.CACHE_DIRS:
            if not cache_dir.exists():
                continue
            
            try:
                for item in cache_dir.iterdir():
                    try:
                        # 快速获取大小（不递归计算目录）
                        if item.is_dir():
                            size = 0  # 目录大小延迟计算
                        else:
                            size = item.stat().st_size
                        
                        file_item = FileItem(
                            path=str(item),
                            name=item.name,
                            size=size,
                            file_type=FileType.CACHE,
                            is_directory=item.is_dir(),
                            last_modified=self._get_last_modified(str(item))
                        )
                        file_item = self.analyze_file_impact(file_item)
                        results.append(file_item)
                        
                        if progress_callback:
                            progress_callback(f"扫描缓存: {item.name}")
                    except PermissionError:
                        pass
            except PermissionError:
                pass
        
        return results
    
    def scan_log_files(self, progress_callback=None) -> List[FileItem]:
        """扫描日志文件"""
        results = []
        
        for log_dir in self.LOG_DIRS:
            if not log_dir.exists():
                continue
            
            try:
                for item in log_dir.rglob('*'):
                    if item.is_file():
                        try:
                            size = item.stat().st_size
                            if size > 0:
                                file_item = FileItem(
                                    path=str(item),
                                    name=item.name,
                                    size=size,
                                    file_type=FileType.LOG,
                                    is_directory=False,
                                    last_modified=self._get_last_modified(str(item))
                                )
                                file_item = self.analyze_file_impact(file_item)
                                results.append(file_item)
                                
                                if progress_callback:
                                    progress_callback(f"扫描日志: {item.name}")
                        except PermissionError:
                            pass
            except PermissionError:
                pass
        
        return results
    
    def scan_large_files(self, min_size_mb: int = 100, 
                        scan_paths: Optional[List[str]] = None,
                        progress_callback=None) -> List[FileItem]:
        """扫描大文件"""
        if scan_paths is None:
            scan_paths = [
                str(Path.home()),
                "/Applications",
            ]
        
        results = []
        min_size = min_size_mb * 1024 * 1024
        
        for scan_path in scan_paths:
            if not os.path.exists(scan_path):
                continue
            
            try:
                for dirpath, dirnames, filenames in os.walk(scan_path):
                    dirnames[:] = [d for d in dirnames if not d.startswith('.') and 
                                   d not in ['node_modules', '.git', '__pycache__', 'venv', 'Library']]
                    
                    for filename in filenames:
                        filepath = os.path.join(dirpath, filename)
                        try:
                            size = os.path.getsize(filepath)
                            if size >= min_size:
                                file_item = FileItem(
                                    path=filepath,
                                    name=filename,
                                    size=size,
                                    file_type=FileType.LARGE_FILE,
                                    is_directory=False,
                                    last_modified=self._get_last_modified(filepath)
                                )
                                file_item = self.analyze_file_impact(file_item)
                                results.append(file_item)
                                
                                if progress_callback:
                                    progress_callback(f"发现大文件: {filename} ({file_item.size_display})")
                        except (PermissionError, OSError):
                            pass
            except PermissionError:
                pass
        
        results.sort(key=lambda x: x.size, reverse=True)
        return results
    
    def calculate_dir_size_async(self, path: str, callback=None) -> int:
        """异步计算目录大小"""
        total = 0
        try:
            for dirpath, dirnames, filenames in os.walk(path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    try:
                        total += os.path.getsize(fp)
                    except:
                        pass
                if callback:
                    callback(f"计算大小: {dirpath}")
        except:
            pass
        return total
    
    def analyze_app_files(self, bundle_id: str, app_name: str, 
                         progress_callback=None) -> AppFileInfo:
        """分析特定应用的所有相关文件"""
        app_info = AppFileInfo(
            app_name=app_name,
            bundle_id=bundle_id,
            app_path=self.get_app_path(bundle_id)
        )
        
        search_dirs = [
            Path.home() / "Library" / "Caches",
            Path.home() / "Library" / "Preferences",
            Path.home() / "Library" / "Application Support",
            Path.home() / "Library" / "Containers",
            Path.home() / "Library" / "Logs",
            Path.home() / "Library" / "Saved Application State",
            Path.home() / "Library" / "WebKit",
        ]
        
        patterns = [
            bundle_id,
            bundle_id.split('.')[-1],
            app_name,
        ]
        
        for search_dir in search_dirs:
            if not search_dir.exists():
                continue
            
            try:
                for item in search_dir.iterdir():
                    item_name = item.name.lower()
                    
                    matched = False
                    for pattern in patterns:
                        if pattern.lower() in item_name:
                            matched = True
                            break
                    
                    if matched:
                        try:
                            if item.is_dir():
                                size = 0  # 目录大小延迟计算
                            else:
                                size = item.stat().st_size
                            
                            file_type = self._classify_file(str(item))
                            file_item = FileItem(
                                path=str(item),
                                name=item.name,
                                size=size,
                                file_type=file_type,
                                owner_app=app_name,
                                owner_bundle_id=bundle_id,
                                is_directory=item.is_dir(),
                                last_modified=self._get_last_modified(str(item))
                            )
                            file_item = self.analyze_file_impact(file_item)
                            
                            if file_type == FileType.CACHE:
                                app_info.cache_files.append(file_item)
                            elif file_type == FileType.LOG:
                                app_info.log_files.append(file_item)
                            elif file_type == FileType.PREFERENCE:
                                app_info.preference_files.append(file_item)
                            elif file_type == FileType.APPLICATION_SUPPORT:
                                app_info.support_files.append(file_item)
                            elif file_type == FileType.CONTAINER:
                                app_info.container_files.append(file_item)
                            else:
                                app_info.other_files.append(file_item)
                            
                            if progress_callback:
                                progress_callback(f"分析文件: {item.name}")
                        except PermissionError:
                            pass
            except PermissionError:
                pass
        
        # VSCode 特殊处理：扫描已安装的扩展
        if bundle_id == 'com.microsoft.VSCode':
            self._scan_vscode_extensions(app_info, progress_callback)

        return app_info

    def _scan_vscode_extensions(self, app_info: AppFileInfo, progress_callback=None):
        """扫描 VSCode 已安装的扩展"""
        extensions_dir = Path.home() / ".vscode" / "extensions"
        if not extensions_dir.exists():
            return

        try:
            for item in extensions_dir.iterdir():
                if not item.is_dir():
                    continue
                try:
                    size = self._get_dir_size_fast(str(item))
                    file_item = FileItem(
                        path=str(item),
                        name=f"[扩展] {item.name}",
                        size=size,
                        file_type=FileType.APPLICATION_SUPPORT,
                        owner_app=app_info.app_name,
                        owner_bundle_id=app_info.bundle_id,
                        is_directory=True,
                        last_modified=self._get_last_modified(str(item)),
                        impact_level=ImpactLevel.LOW,
                        impact_description="VSCode 扩展，删除后可从扩展市场重新安装"
                    )
                    app_info.support_files.append(file_item)

                    if progress_callback:
                        progress_callback(f"扫描扩展: {item.name}")
                except PermissionError:
                    pass
        except PermissionError:
            pass

    def get_all_installed_apps(self) -> List[Tuple[str, str]]:
        """获取所有已安装应用"""
        return list(self._installed_apps.items())