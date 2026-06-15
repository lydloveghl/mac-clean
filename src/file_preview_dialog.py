#!/usr/bin/env python3
import os
import json
import plistlib
from pathlib import Path
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, 
                              QPushButton, QLabel, QTabWidget, QWidget,
                              QTreeWidget, QTreeWidgetItem, QHeaderView,
                              QMessageBox, QFileDialog)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QTextCursor
from typing import Optional


class FilePreviewDialog(QDialog):
    """文件预览对话框"""
    
    # 可预览的文本文件扩展名
    TEXT_EXTENSIONS = {
        '.txt', '.log', '.plist', '.json', '.xml', '.csv', '.md', 
        '.py', '.js', '.html', '.css', '.sh', '.bash', '.zsh',
        '.conf', '.cfg', '.ini', '.yaml', '.yml', '.toml'
    }
    
    # 可预览的图片扩展名
    IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.icns', '.ico'}
    
    def __init__(self, file_path: str, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.file_name = os.path.basename(file_path)
        
        self.setWindowTitle(f"文件预览 - {self.file_name}")
        self.setMinimumSize(700, 500)
        
        self._init_ui()
        self._load_file()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # 文件信息
        info_layout = QHBoxLayout()
        info_layout.addWidget(QLabel(f"文件路径: {self.file_path}"))
        info_layout.addStretch()
        
        file_size = self._get_file_size()
        info_layout.addWidget(QLabel(f"大小: {file_size}"))
        
        layout.addLayout(info_layout)
        
        # 标签页
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # 内容预览标签页
        self.content_tab = QWidget()
        self.tab_widget.addTab(self.content_tab, "内容预览")
        
        # 文件信息标签页
        self.info_tab = QWidget()
        self.tab_widget.addTab(self.info_tab, "详细信息")
        
        self._init_content_tab()
        self._init_info_tab()
        
        # 底部按钮
        button_layout = QHBoxLayout()
        
        open_btn = QPushButton("用默认程序打开")
        open_btn.clicked.connect(self._open_with_default_app)
        button_layout.addWidget(open_btn)
        
        open_folder_btn = QPushButton("打开所在文件夹")
        open_folder_btn.clicked.connect(self._open_containing_folder)
        button_layout.addWidget(open_folder_btn)
        
        button_layout.addStretch()
        
        copy_path_btn = QPushButton("复制路径")
        copy_path_btn.clicked.connect(self._copy_path)
        button_layout.addWidget(copy_path_btn)
        
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def _init_content_tab(self):
        """初始化内容预览标签页"""
        layout = QVBoxLayout(self.content_tab)
        
        self.content_text = QTextEdit()
        self.content_text.setReadOnly(True)
        self.content_text.setFont(QFont("Menlo", 11))
        layout.addWidget(self.content_text)
    
    def _init_info_tab(self):
        """初始化详细信息标签页"""
        layout = QVBoxLayout(self.info_tab)
        
        self.info_tree = QTreeWidget()
        self.info_tree.setHeaderLabels(["属性", "值"])
        self.info_tree.setRootIsDecorated(False)
        self.info_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.info_tree.header().resizeSection(0, 200)
        layout.addWidget(self.info_tree)
    
    def _load_file(self):
        """加载文件内容"""
        if not os.path.exists(self.file_path):
            self.content_text.setPlainText("文件不存在")
            return
        
        ext = Path(self.file_path).suffix.lower()
        
        # 根据文件类型加载内容
        if ext == '.plist':
            self._load_plist_file()
        elif ext == '.json':
            self._load_json_file()
        elif ext in self.TEXT_EXTENSIONS:
            self._load_text_file()
        elif ext in self.IMAGE_EXTENSIONS:
            self._load_image_info()
        else:
            self._load_file_info_only()
        
        # 加载详细信息
        self._load_file_info()
    
    def _load_text_file(self):
        """加载文本文件"""
        try:
            # 尝试不同的编码
            encodings = ['utf-8', 'latin-1', 'gbk', 'gb2312']
            content = None
            
            for encoding in encodings:
                try:
                    with open(self.file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    break
                except UnicodeDecodeError:
                    continue
            
            if content is not None:
                # 限制显示行数
                lines = content.split('\n')
                if len(lines) > 1000:
                    content = '\n'.join(lines[:1000]) + f"\n\n... (共 {len(lines)} 行，仅显示前 1000 行)"
                
                self.content_text.setPlainText(content)
            else:
                self.content_text.setPlainText("无法读取文件：不支持的编码格式")
        except Exception as e:
            self.content_text.setPlainText(f"读取文件失败: {e}")
    
    def _load_plist_file(self):
        """加载plist文件"""
        try:
            with open(self.file_path, 'rb') as f:
                plist_data = plistlib.load(f)
            
            # 格式化显示
            formatted = self._format_plist(plist_data)
            self.content_text.setPlainText(formatted)
        except Exception as e:
            self.content_text.setPlainText(f"读取plist文件失败: {e}")
    
    def _load_json_file(self):
        """加载JSON文件"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            formatted = json.dumps(data, indent=2, ensure_ascii=False)
            
            # 限制显示大小
            if len(formatted) > 100000:
                formatted = formatted[:100000] + "\n\n... (文件过大，仅显示部分内容)"
            
            self.content_text.setPlainText(formatted)
        except Exception as e:
            self.content_text.setPlainText(f"读取JSON文件失败: {e}")
    
    def _load_image_info(self):
        """加载图片信息"""
        self.content_text.setPlainText('这是一个图片文件。\n\n点击"用默认程序打开"按钮查看图片。')
    
    def _load_file_info_only(self):
        """只显示文件信息"""
        self.content_text.setPlainText('此文件类型不支持预览。\n\n点击"用默认程序打开"按钮查看文件。')
    
    def _load_file_info(self):
        """加载文件详细信息"""
        self.info_tree.clear()
        
        try:
            stat = os.stat(self.file_path)
            
            info_items = [
                ("文件名", self.file_name),
                ("文件路径", self.file_path),
                ("文件大小", self._format_size(stat.st_size)),
                ("文件类型", self._get_file_type()),
                ("创建时间", self._format_time(stat.st_ctime)),
                ("修改时间", self._format_time(stat.st_mtime)),
                ("访问时间", self._format_time(stat.st_atime)),
                ("文件权限", oct(stat.st_mode)[-3:]),
                ("所有者 UID", str(stat.st_uid)),
                ("所属组 GID", str(stat.st_gid)),
                ("文件扩展名", Path(self.file_path).suffix),
                ("是否为符号链接", "是" if os.path.islink(self.file_path) else "否"),
            ]
            
            # 如果是符号链接，显示链接目标
            if os.path.islink(self.file_path):
                link_target = os.readlink(self.file_path)
                info_items.append(("链接目标", link_target))
            
            for attr, value in info_items:
                item = QTreeWidgetItem(self.info_tree)
                item.setText(0, attr)
                item.setText(1, str(value))
        except Exception as e:
            item = QTreeWidgetItem(self.info_tree)
            item.setText(0, "错误")
            item.setText(1, str(e))
    
    def _format_plist(self, data, indent=0) -> str:
        """格式化plist数据"""
        prefix = "  " * indent
        
        if isinstance(data, dict):
            if not data:
                return "{}"
            lines = ["{"]
            for key, value in data.items():
                formatted_value = self._format_plist(value, indent + 1)
                lines.append(f"{prefix}  {key} = {formatted_value};")
            lines.append(f"{prefix}}}")
            return "\n".join(lines)
        elif isinstance(data, list):
            if not data:
                return "()"
            lines = ["("]
            for item in data:
                formatted_item = self._format_plist(item, indent + 1)
                lines.append(f"{prefix}  {formatted_item},")
            lines.append(f"{prefix})")
            return "\n".join(lines)
        elif isinstance(data, bytes):
            return f"<{data.hex()}>"
        elif isinstance(data, str):
            return f'"{data}"'
        elif isinstance(data, bool):
            return "true" if data else "false"
        else:
            return str(data)
    
    def _get_file_size(self) -> str:
        """获取文件大小"""
        try:
            size = os.path.getsize(self.file_path)
            return self._format_size(size)
        except:
            return "未知"
    
    def _format_size(self, size: int) -> str:
        """格式化大小"""
        if size < 1024:
            return f"{size} 字节"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        else:
            return f"{size / (1024 * 1024 * 1024):.2f} GB"
    
    def _format_time(self, timestamp: float) -> str:
        """格式化时间"""
        from datetime import datetime
        return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
    
    def _get_file_type(self) -> str:
        """获取文件类型描述"""
        ext = Path(self.file_path).suffix.lower()
        
        type_map = {
            '.plist': "属性列表文件 (Property List)",
            '.json': "JSON 数据文件",
            '.xml': "XML 文档",
            '.txt': "纯文本文件",
            '.log': "日志文件",
            '.db': "数据库文件",
            '.sqlite': "SQLite 数据库",
            '.png': "PNG 图片",
            '.jpg': "JPEG 图片",
            '.jpeg': "JPEG 图片",
            '.gif': "GIF 图片",
            '.pdf': "PDF 文档",
            '.zip': "ZIP 压缩包",
            '.tar': "TAR 归档文件",
            '.gz': "GZIP 压缩文件",
        }
        
        return type_map.get(ext, f"文件 ({ext})" if ext else "未知类型")
    
    def _open_with_default_app(self):
        """用默认程序打开文件"""
        try:
            subprocess.run(['open', self.file_path], check=True)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法打开文件: {e}")
    
    def _open_containing_folder(self):
        """打开所在文件夹"""
        try:
            subprocess.run(['open', '-R', self.file_path], check=True)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法打开文件夹: {e}")
    
    def _copy_path(self):
        """复制路径到剪贴板"""
        from PyQt6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(self.file_path)
        QMessageBox.information(self, "提示", "路径已复制到剪贴板")


# 需要导入subprocess
import subprocess