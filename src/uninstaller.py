#!/usr/bin/env python3
import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Callable, Optional
from dataclasses import dataclass


@dataclass
class UninstallResult:
    """卸载结果"""
    success: bool
    app_removed: bool
    cache_removed: bool
    removed_cache_paths: List[str]
    errors: List[str]
    message: str


class Uninstaller:
    """卸载管理器"""
    
    def __init__(self):
        self.progress_callback: Optional[Callable[[int, int, str], None]] = None
        
    def set_progress_callback(self, callback: Callable[[int, int, str], None]):
        """设置进度回调函数"""
        self.progress_callback = callback
    
    def uninstall_application(self, app_path: str,
                            delete_cache: bool = False,
                            cache_paths: Optional[List[str]] = None,
                            use_sudo: bool = True) -> UninstallResult:
        """
        卸载应用程序（直接删除）

        Args:
            app_path: 应用程序路径
            delete_cache: 是否删除缓存
            cache_paths: 要删除的缓存路径列表
            use_sudo: 是否使用sudo获取权限

        Returns:
            UninstallResult: 卸载结果
        """
        errors = []
        app_removed = False
        cache_removed = False
        removed_cache_paths = []

        # 检查应用是否存在
        if not os.path.exists(app_path):
            return UninstallResult(
                success=False,
                app_removed=False,
                cache_removed=False,
                removed_cache_paths=[],
                errors=[f"应用不存在: {app_path}"],
                message="应用不存在"
            )

        # 收集所有需要删除的路径，统一用一次权限验证完成
        all_paths = [app_path]
        if delete_cache and cache_paths:
            all_paths.extend([p for p in cache_paths if os.path.exists(p)])

        # 先尝试普通权限删除
        need_admin = []
        for path in all_paths:
            if not os.path.exists(path):
                if path == app_path:
                    app_removed = True
                else:
                    removed_cache_paths.append(path)
                continue
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
                if path == app_path:
                    app_removed = True
                else:
                    removed_cache_paths.append(path)
            except PermissionError:
                need_admin.append(path)
            except Exception as e:
                errors.append(f"删除失败 {path}: {e}")

        # 需要管理员权限的路径，单次验证批量删除
        if need_admin and use_sudo:
            if self.progress_callback:
                self.progress_callback(0, len(need_admin), "请求管理员权限...")

            admin_success, admin_errors = self._delete_paths_with_admin(need_admin)

            for path in admin_success:
                if path == app_path:
                    app_removed = True
                else:
                    removed_cache_paths.append(path)
            errors.extend(admin_errors)

        if delete_cache and cache_paths:
            cache_removed = len(removed_cache_paths) > 0

        # 确定成功状态
        success = app_removed and (not delete_cache or cache_removed or not cache_paths)

        # 生成消息
        if success:
            if delete_cache and removed_cache_paths:
                message = f"成功卸载应用并删除 {len(removed_cache_paths)} 个缓存文件"
            else:
                message = "成功卸载应用"
        else:
            if not app_removed:
                message = "卸载失败：无法删除应用"
            elif delete_cache and not cache_removed:
                message = "卸载部分成功：应用已删除，但缓存删除失败"
            else:
                message = "卸载过程中发生错误"

        return UninstallResult(
            success=success,
            app_removed=app_removed,
            cache_removed=cache_removed,
            removed_cache_paths=removed_cache_paths,
            errors=errors,
            message=message
        )

    def _delete_paths_with_admin(self, paths: List[str]) -> tuple[List[str], List[str]]:
        """批量以管理员权限删除路径（单次验证，支持 Touch ID）"""
        import tempfile
        import stat

        try:
            # 将待删除路径写入临时文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
                tmp.write('\n'.join(paths))
                tmp_path = tmp.name

            # 创建临时 shell 脚本，避免嵌套引号转义问题
            with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as script:
                script.write('#!/bin/bash\n')
                script.write(f'while IFS= read -r p; do rm -rf "$p"; done < "{tmp_path}"\n')
                script.write(f'rm -f "{tmp_path}"\n')
                script.write(f'rm -f "{script.name}"\n')
                script_path = script.name

            os.chmod(script_path, stat.S_IRWXU)

            applescript = (
                f'do shell script "{script_path}" '
                f'with administrator privileges '
                f'with prompt "Mac卸载工具需要权限来删除应用"'
            )
            result = subprocess.run(
                ['osascript', '-e', applescript],
                capture_output=True, text=True, timeout=120
            )

            if result.returncode == 0:
                return paths, []
            else:
                success = [p for p in paths if not os.path.exists(p)]
                errors = [f"删除失败: {p}" for p in paths if os.path.exists(p)]
                return success, errors
        except subprocess.TimeoutExpired:
            self._cleanup_temp_files(tmp_path, script_path)
            return [], [f"删除超时: {p}" for p in paths]
        except Exception as e:
            self._cleanup_temp_files(
                locals().get('tmp_path', ''),
                locals().get('script_path', '')
            )
            return [], [f"删除异常: {e}"]

    @staticmethod
    def _cleanup_temp_files(*paths):
        for p in paths:
            if p:
                try:
                    os.unlink(p)
                except Exception:
                    pass

    def move_to_trash(self, path: str) -> bool:
        """将文件移动到废纸篓"""
        try:
            script = f'''
            tell application "Finder"
                set theFile to POSIX file "{path}" as alias
                delete theFile
            end tell
            '''
            subprocess.run(['osascript', '-e', script], check=True, timeout=30)
            return True
        except:
            try:
                trash_dir = Path.home() / ".Trash"
                if os.path.isdir(path):
                    dest = trash_dir / os.path.basename(path)
                    if dest.exists():
                        import time
                        timestamp = int(time.time())
                        dest = trash_dir / f"{os.path.basename(path)} {timestamp}"
                    shutil.move(path, dest)
                else:
                    dest = trash_dir / os.path.basename(path)
                    if dest.exists():
                        import time
                        timestamp = int(time.time())
                        name, ext = os.path.splitext(os.path.basename(path))
                        dest = trash_dir / f"{name} {timestamp}{ext}"
                    shutil.move(path, dest)
                return True
            except Exception as e:
                print(f"移动到废纸篓失败: {e}")
                return False