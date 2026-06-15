#!/usr/bin/env python3
import os
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget,
                              QTreeWidgetItem, QPushButton, QLabel, QCheckBox,
                              QDialogButtonBox, QGroupBox)
from PyQt6.QtCore import Qt
from typing import List, Tuple


class CacheSelectorDialog(QDialog):
    """缓存文件选择对话框"""
    
    def __init__(self, app_name: str, cache_paths: List[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"选择要删除的缓存文件 - {app_name}")
        self.setMinimumSize(600, 500)
        
        self.cache_paths = cache_paths
        self.selected_paths = []
        
        self._init_ui()
        
    def _init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        
        # 说明标签
        info_label = QLabel("选择要删除的缓存文件和文件夹：")
        info_label.setStyleSheet("font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(info_label)
        
        # 全选/取消全选
        select_layout = QHBoxLayout()
        self.select_all_cb = QCheckBox("全选")
        self.select_all_cb.stateChanged.connect(self._toggle_select_all)
        select_layout.addWidget(self.select_all_cb)
        select_layout.addStretch()
        
        self.selected_count_label = QLabel("已选择: 0 项")
        select_layout.addWidget(self.selected_count_label)
        layout.addLayout(select_layout)
        
        # 缓存文件树
        self.cache_tree = QTreeWidget()
        self.cache_tree.setHeaderLabels(["路径", "类型", "大小"])
        self.cache_tree.setRootIsDecorated(True)
        self.cache_tree.setAlternatingRowColors(True)
        layout.addWidget(self.cache_tree)
        
        # 加载缓存文件
        self._load_cache_items()
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | 
                                     QDialogButtonBox.StandardButton.Cancel)
        button_box.button(QDialogButtonBox.StandardButton.Ok).setText("确定")
        button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # 连接信号
        self.cache_tree.itemChanged.connect(self._on_item_changed)
        
    def _load_cache_items(self):
        """加载缓存文件项"""
        self.cache_tree.clear()
        
        for path in self.cache_paths:
            item = QTreeWidgetItem(self.cache_tree)
            item.setText(0, path)
            item.setCheckState(0, Qt.CheckState.Unchecked)

            if os.path.isdir(path):
                item.setText(1, "文件夹")
                # 计算文件夹大小
                size = self._get_dir_size(path)
                item.setText(2, self._format_size(size))
            else:
                item.setText(1, "文件")
                try:
                    size = os.path.getsize(path)
                    item.setText(2, self._format_size(size))
                except:
                    item.setText(2, "未知")
            
            # 存储完整路径
            item.setData(0, Qt.ItemDataRole.UserRole, path)
        
        # 展开所有项
        self.cache_tree.expandAll()
        # 调整列宽
        for i in range(3):
            self.cache_tree.resizeColumnToContents(i)
    
    def _get_dir_size(self, path: str) -> int:
        """计算目录大小"""
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(filepath)
                    except:
                        pass
        except:
            pass
        return total_size
    
    def _format_size(self, size: int) -> str:
        """格式化大小显示"""
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        else:
            return f"{size / (1024 * 1024 * 1024):.2f} GB"
    
    def _toggle_select_all(self, state: int):
        """全选/取消全选"""
        check_state = Qt.CheckState.Checked if state == 2 else Qt.CheckState.Unchecked
        for i in range(self.cache_tree.topLevelItemCount()):
            item = self.cache_tree.topLevelItem(i)
            item.setCheckState(0, check_state)
    
    def _on_item_changed(self, item: QTreeWidgetItem, column: int):
        """项目选择状态改变"""
        if column == 0:
            self._update_selected_count()
    
    def _update_selected_count(self):
        """更新已选择数量"""
        count = 0
        for i in range(self.cache_tree.topLevelItemCount()):
            item = self.cache_tree.topLevelItem(i)
            if item.checkState(0) == Qt.CheckState.Checked:
                count += 1
        
        self.selected_count_label.setText(f"已选择: {count} 项")
    
    def get_selected_paths(self) -> List[str]:
        """获取选中的路径"""
        selected = []
        for i in range(self.cache_tree.topLevelItemCount()):
            item = self.cache_tree.topLevelItem(i)
            if item.checkState(0) == Qt.CheckState.Checked:
                path = item.data(0, Qt.ItemDataRole.UserRole)
                selected.append(path)
        return selected


class UninstallConfirmDialog(QDialog):
    """卸载确认对话框"""
    
    def __init__(self, app_name: str, app_path: str, cache_paths: List[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"确认卸载 - {app_name}")
        self.setMinimumSize(500, 400)
        
        self.app_name = app_name
        self.app_path = app_path
        self.cache_paths = cache_paths
        self.delete_cache = False
        self.selected_cache_paths = []
        
        self._init_ui()
        
    def _init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        
        # 应用信息
        info_group = QGroupBox("应用信息")
        info_layout = QVBoxLayout()
        
        info_layout.addWidget(QLabel(f"应用名称: {self.app_name}"))
        info_layout.addWidget(QLabel(f"安装路径: {self.app_path}"))
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # 缓存选项
        cache_group = QGroupBox("缓存文件")
        cache_layout = QVBoxLayout()
        
        self.delete_cache_cb = QCheckBox("同时删除缓存文件")
        self.delete_cache_cb.stateChanged.connect(self._on_cache_option_changed)
        cache_layout.addWidget(self.delete_cache_cb)
        
        if self.cache_paths:
            cache_info = QLabel(f"找到 {len(self.cache_paths)} 个相关缓存文件/文件夹")
            cache_layout.addWidget(cache_info)
            
            self.select_cache_btn = QPushButton("选择要删除的缓存...")
            self.select_cache_btn.clicked.connect(self._select_cache_files)
            self.select_cache_btn.setEnabled(False)
            cache_layout.addWidget(self.select_cache_btn)
        else:
            cache_layout.addWidget(QLabel("未找到相关缓存文件"))
        
        cache_group.setLayout(cache_layout)
        layout.addWidget(cache_group)
        
        # 警告信息
        warning_label = QLabel("⚠️ 警告：应用将被永久删除（非移动到废纸篓），此操作不可撤销！")
        warning_label.setStyleSheet("color: red; font-weight: bold;")
        warning_label.setWordWrap(True)
        layout.addWidget(warning_label)
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | 
                                     QDialogButtonBox.StandardButton.Cancel)
        button_box.button(QDialogButtonBox.StandardButton.Ok).setText("确定卸载")
        button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def _on_cache_option_changed(self, state: int):
        """缓存选项改变"""
        self.delete_cache = state == 2
        if hasattr(self, 'select_cache_btn'):
            self.select_cache_btn.setEnabled(self.delete_cache and len(self.cache_paths) > 0)
    
    def _select_cache_files(self):
        """选择缓存文件"""
        dialog = CacheSelectorDialog(self.app_name, self.cache_paths, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.selected_cache_paths = dialog.get_selected_paths()
    
    def get_uninstall_options(self) -> Tuple[bool, List[str]]:
        """获取卸载选项"""
        return self.delete_cache, self.selected_cache_paths if self.delete_cache else []