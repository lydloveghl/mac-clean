#!/usr/bin/env python3
import os
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget,
                              QTreeWidgetItem, QPushButton, QLabel, QCheckBox,
                              QHeaderView, QSpinBox, QComboBox, QTabWidget,
                              QWidget, QMessageBox, QMenu, QApplication,
                              QLineEdit)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QBrush, QIcon, QAction
from typing import List, Optional, Dict
from file_analyzer import FileItem, FileType, ImpactLevel, FileAnalyzer, AppFileInfo
from app_icon_manager import AppIconManager
from file_preview_dialog import FilePreviewDialog


class ScanThread(QThread):
    """扫描线程"""
    progress = pyqtSignal(str)
    item_found = pyqtSignal(object)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def __init__(self, analyzer: FileAnalyzer, scan_type: str, **kwargs):
        super().__init__()
        self.analyzer = analyzer
        self.scan_type = scan_type
        self.kwargs = kwargs
    
    def run(self):
        try:
            results = []
            if self.scan_type == "cache":
                results = self.analyzer.scan_cache_files(
                    progress_callback=lambda msg: self.progress.emit(msg)
                )
            elif self.scan_type == "logs":
                results = self.analyzer.scan_log_files(
                    progress_callback=lambda msg: self.progress.emit(msg)
                )
            elif self.scan_type == "large_files":
                results = self.analyzer.scan_large_files(
                    min_size_mb=self.kwargs.get('min_size', 100),
                    progress_callback=lambda msg: self.progress.emit(msg)
                )
            
            for item in results:
                self.item_found.emit(item)
            
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))


class AppAnalysisThread(QThread):
    """应用分析线程"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(object)
    
    def __init__(self, analyzer: FileAnalyzer, bundle_id: str, app_name: str):
        super().__init__()
        self.analyzer = analyzer
        self.bundle_id = bundle_id
        self.app_name = app_name
    
    def run(self):
        try:
            result = self.analyzer.analyze_app_files(
                self.bundle_id,
                self.app_name,
                progress_callback=lambda msg: self.progress.emit(msg)
            )
            self.finished.emit(result)
        except Exception as e:
            self.finished.emit(None)


def get_impact_color(level: ImpactLevel) -> QColor:
    colors = {
        ImpactLevel.SAFE: QColor(76, 175, 80),
        ImpactLevel.LOW: QColor(255, 193, 7),
        ImpactLevel.MEDIUM: QColor(255, 152, 0),
        ImpactLevel.HIGH: QColor(244, 67, 54),
        ImpactLevel.CRITICAL: QColor(156, 39, 176),
    }
    return colors.get(level, QColor(158, 158, 158))


def get_impact_emoji(level: ImpactLevel) -> str:
    emojis = {
        ImpactLevel.SAFE: "✅",
        ImpactLevel.LOW: "⚠️",
        ImpactLevel.MEDIUM: "🟠",
        ImpactLevel.HIGH: "🔴",
        ImpactLevel.CRITICAL: "⛔",
    }
    return emojis.get(level, "❓")


class FileCleanupDialog(QDialog):
    """文件清理对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("文件清理工具")
        self.setMinimumSize(1100, 800)
        
        self.analyzer = FileAnalyzer()
        self.icon_manager = AppIconManager()
        self.scan_results: Dict[str, List[FileItem]] = {}
        
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # 缓存清理
        self.cache_tab = self._create_cleanup_tab("cache", "扫描缓存文件")
        self.tab_widget.addTab(self.cache_tab, "缓存清理")
        
        # 日志清理
        self.log_tab = self._create_cleanup_tab("logs", "扫描日志文件")
        self.tab_widget.addTab(self.log_tab, "日志清理")
        
        # 大文件清理
        self.large_file_tab = self._create_large_file_tab()
        self.tab_widget.addTab(self.large_file_tab, "大文件清理")
        
        # 应用文件分析
        self.app_analysis_tab = self._create_app_analysis_tab()
        self.tab_widget.addTab(self.app_analysis_tab, "应用文件分析")
        
        # 底部按钮
        button_layout = QHBoxLayout()
        
        self.preview_btn = QPushButton("预览选中文件")
        self.preview_btn.setStyleSheet("padding: 8px 16px;")
        self.preview_btn.clicked.connect(self._preview_selected)
        self.preview_btn.setEnabled(False)
        button_layout.addWidget(self.preview_btn)
        
        button_layout.addStretch()
        
        self.delete_selected_btn = QPushButton("删除勾选的文件")
        self.delete_selected_btn.setStyleSheet("background-color: #f44336; color: white; padding: 10px 20px; font-weight: bold;")
        self.delete_selected_btn.clicked.connect(self._delete_selected)
        self.delete_selected_btn.setEnabled(False)
        button_layout.addWidget(self.delete_selected_btn)
        
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def _create_cleanup_tab(self, scan_type: str, button_text: str) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 顶部控制栏
        control_layout = QHBoxLayout()
        
        scan_btn = QPushButton(button_text)
        scan_btn.setStyleSheet("padding: 8px 16px; font-weight: bold;")
        scan_btn.clicked.connect(lambda: self._start_scan(scan_type))
        control_layout.addWidget(scan_btn)
        
        control_layout.addWidget(QLabel("  视图:"))
        view_combo = QComboBox()
        view_combo.addItems(["按目录分类", "按应用分类"])
        view_combo.currentIndexChanged.connect(lambda idx: self._change_view(scan_type, idx))
        control_layout.addWidget(view_combo)
        
        if scan_type == "cache":
            self.cache_view_combo = view_combo
        else:
            self.log_view_combo = view_combo
        
        control_layout.addStretch()
        
        status_label = QLabel("就绪")
        control_layout.addWidget(status_label)
        
        if scan_type == "cache":
            self.cache_status_label = status_label
        else:
            self.log_status_label = status_label
        
        layout.addLayout(control_layout)

        # 搜索栏
        search_input = QLineEdit()
        search_input.setPlaceholderText("搜索文件（名称、路径、应用名）...")
        search_input.setClearButtonEnabled(True)
        search_input.textChanged.connect(lambda text: self._filter_tree(file_tree, text))
        layout.addWidget(search_input)

        if scan_type == "cache":
            self.cache_search = search_input
        else:
            self.log_search = search_input

        # 文件树
        file_tree = QTreeWidget()
        file_tree.setHeaderLabels(["", "文件/目录", "大小", "影响级别", "所属应用", "影响说明", "修改时间"])
        file_tree.setRootIsDecorated(True)
        file_tree.setAlternatingRowColors(True)
        file_tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        file_tree.setSelectionBehavior(QTreeWidget.SelectionBehavior.SelectRows)
        file_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        file_tree.setIconSize(QSize(24, 24))
        file_tree.itemDoubleClicked.connect(lambda item, col: self._on_item_double_clicked(item))
        file_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        file_tree.customContextMenuRequested.connect(lambda pos: self._show_context_menu(file_tree, pos))
        
        # 设置列宽 - 复选框列需要足够宽
        file_tree.header().resizeSection(0, 60)
        file_tree.header().setMinimumSectionSize(60)
        
        # 连接信号
        file_tree.itemChanged.connect(self._on_item_changed)
        file_tree.itemSelectionChanged.connect(self._update_delete_button)
        
        if scan_type == "cache":
            self.cache_tree = file_tree
        else:
            self.log_tree = file_tree
        
        layout.addWidget(file_tree)
        
        # 统计和操作栏
        stats_layout = QHBoxLayout()
        stats_label = QLabel("共 0 个文件，总大小: 0 B")
        stats_layout.addWidget(stats_label)
        
        if scan_type == "cache":
            self.cache_stats_label = stats_label
        else:
            self.log_stats_label = stats_label
        
        stats_layout.addStretch()
        
        select_all_btn = QPushButton("全选")
        select_all_btn.clicked.connect(lambda: self._toggle_all(file_tree, True))
        stats_layout.addWidget(select_all_btn)
        
        deselect_all_btn = QPushButton("取消全选")
        deselect_all_btn.clicked.connect(lambda: self._toggle_all(file_tree, False))
        stats_layout.addWidget(deselect_all_btn)
        
        hint_label = QLabel("Ctrl/Shift多选 | 勾选☑ | 点击「删除」需输入密码")
        hint_label.setStyleSheet("color: #666; font-style: italic;")
        stats_layout.addWidget(hint_label)
        
        layout.addLayout(stats_layout)
        
        return widget
    
    def _create_large_file_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        control_layout = QHBoxLayout()
        control_layout.addWidget(QLabel("最小文件大小:"))
        
        self.size_spinbox = QSpinBox()
        self.size_spinbox.setRange(10, 10000)
        self.size_spinbox.setValue(100)
        self.size_spinbox.setSuffix(" MB")
        control_layout.addWidget(self.size_spinbox)
        
        scan_btn = QPushButton("扫描大文件")
        scan_btn.setStyleSheet("padding: 8px 16px; font-weight: bold;")
        scan_btn.clicked.connect(self._scan_large_files)
        control_layout.addWidget(scan_btn)
        
        control_layout.addStretch()
        
        self.large_file_status = QLabel("就绪")
        control_layout.addWidget(self.large_file_status)
        
        layout.addLayout(control_layout)

        # 搜索栏
        self.large_file_search = QLineEdit()
        self.large_file_search.setPlaceholderText("搜索文件（名称、路径）...")
        self.large_file_search.setClearButtonEnabled(True)
        self.large_file_search.textChanged.connect(lambda text: self._filter_tree(self.large_file_tree, text))
        layout.addWidget(self.large_file_search)

        self.large_file_tree = QTreeWidget()
        self.large_file_tree.setHeaderLabels(["", "文件路径", "大小", "影响级别", "所属应用", "最后修改"])
        self.large_file_tree.setRootIsDecorated(True)
        self.large_file_tree.setAlternatingRowColors(True)
        self.large_file_tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self.large_file_tree.setSelectionBehavior(QTreeWidget.SelectionBehavior.SelectRows)
        self.large_file_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.large_file_tree.setIconSize(QSize(24, 24))
        self.large_file_tree.itemDoubleClicked.connect(lambda item, col: self._on_item_double_clicked(item))
        self.large_file_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.large_file_tree.customContextMenuRequested.connect(lambda pos: self._show_context_menu(self.large_file_tree, pos))
        self.large_file_tree.header().resizeSection(0, 60)
        self.large_file_tree.header().setMinimumSectionSize(60)
        self.large_file_tree.itemChanged.connect(self._on_item_changed)
        self.large_file_tree.itemSelectionChanged.connect(self._update_delete_button)
        
        layout.addWidget(self.large_file_tree)
        
        stats_layout = QHBoxLayout()
        self.large_file_stats = QLabel("共 0 个大文件，总大小: 0 B")
        stats_layout.addWidget(self.large_file_stats)
        stats_layout.addStretch()
        
        select_all_btn = QPushButton("全选")
        select_all_btn.clicked.connect(lambda: self._toggle_all(self.large_file_tree, True))
        stats_layout.addWidget(select_all_btn)
        
        deselect_all_btn = QPushButton("取消全选")
        deselect_all_btn.clicked.connect(lambda: self._toggle_all(self.large_file_tree, False))
        stats_layout.addWidget(deselect_all_btn)
        
        hint_label = QLabel("Ctrl/Shift多选 | 勾选☑ | 点击「删除」需输入密码")
        hint_label.setStyleSheet("color: #666; font-style: italic;")
        stats_layout.addWidget(hint_label)
        
        layout.addLayout(stats_layout)
        
        return widget
    
    def _create_app_analysis_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        app_layout = QHBoxLayout()
        app_layout.addWidget(QLabel("选择应用:"))
        
        self.app_combo = QComboBox()
        self.app_combo.setMinimumWidth(400)
        app_layout.addWidget(self.app_combo)
        
        analyze_btn = QPushButton("分析文件")
        analyze_btn.setStyleSheet("padding: 8px 16px; font-weight: bold;")
        analyze_btn.clicked.connect(self._analyze_app)
        app_layout.addWidget(analyze_btn)
        
        app_layout.addStretch()
        
        self.app_analysis_status = QLabel("就绪")
        app_layout.addWidget(self.app_analysis_status)
        
        layout.addLayout(app_layout)

        # 搜索栏
        self.app_file_search = QLineEdit()
        self.app_file_search.setPlaceholderText("搜索文件（名称、路径）...")
        self.app_file_search.setClearButtonEnabled(True)
        self.app_file_search.textChanged.connect(lambda text: self._filter_tree(self.app_file_tree, text))
        layout.addWidget(self.app_file_search)

        self.app_file_tree = QTreeWidget()
        self.app_file_tree.setHeaderLabels(["", "文件/目录", "大小", "文件类型", "影响级别", "影响说明"])
        self.app_file_tree.setRootIsDecorated(True)
        self.app_file_tree.setAlternatingRowColors(True)
        self.app_file_tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self.app_file_tree.setSelectionBehavior(QTreeWidget.SelectionBehavior.SelectRows)
        self.app_file_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.app_file_tree.setIconSize(QSize(24, 24))
        self.app_file_tree.itemDoubleClicked.connect(lambda item, col: self._on_item_double_clicked(item))
        self.app_file_tree.header().resizeSection(0, 60)
        self.app_file_tree.header().setMinimumSectionSize(60)
        self.app_file_tree.itemChanged.connect(self._on_item_changed)
        self.app_file_tree.itemSelectionChanged.connect(self._update_delete_button)
        
        layout.addWidget(self.app_file_tree)
        
        stats_layout = QHBoxLayout()
        self.app_stats_label = QLabel("选择应用后点击分析")
        stats_layout.addWidget(self.app_stats_label)
        stats_layout.addStretch()
        
        select_all_btn = QPushButton("全选")
        select_all_btn.clicked.connect(lambda: self._toggle_all(self.app_file_tree, True))
        stats_layout.addWidget(select_all_btn)
        
        deselect_all_btn = QPushButton("取消全选")
        deselect_all_btn.clicked.connect(lambda: self._toggle_all(self.app_file_tree, False))
        stats_layout.addWidget(deselect_all_btn)
        
        layout.addLayout(stats_layout)
        
        self._populate_app_list()
        
        return widget
    
    def _populate_app_list(self):
        apps = self.analyzer.get_all_installed_apps()
        apps.sort(key=lambda x: x[1].lower())
        
        self.app_combo.clear()
        self.app_combo.addItem("请选择应用...", None)
        
        for bundle_id, app_name in apps:
            app_path = self.analyzer.get_app_path(bundle_id)
            icon = self.icon_manager.get_app_icon(app_path, bundle_id)
            self.app_combo.addItem(icon, f"{app_name} ({bundle_id})", (bundle_id, app_name, app_path))
    
    def _start_scan(self, scan_type: str):
        self.scan_thread = ScanThread(self.analyzer, scan_type)
        
        if scan_type == "cache":
            self.scan_thread.progress.connect(lambda msg: self.cache_status_label.setText(msg))
            self.scan_thread.item_found.connect(lambda item: self._on_item_found(item, self.cache_tree))
            self.scan_thread.finished.connect(lambda results: self._on_scan_finished(results, "cache"))
            self.scan_thread.error.connect(lambda msg: self.cache_status_label.setText(f"错误: {msg}"))
            self.cache_tree.clear()
            self.cache_tree.blockSignals(True)  # 阻止信号避免闪烁
        else:
            self.scan_thread.progress.connect(lambda msg: self.log_status_label.setText(msg))
            self.scan_thread.item_found.connect(lambda item: self._on_item_found(item, self.log_tree))
            self.scan_thread.finished.connect(lambda results: self._on_scan_finished(results, "logs"))
            self.scan_thread.error.connect(lambda msg: self.log_status_label.setText(f"错误: {msg}"))
            self.log_tree.clear()
            self.log_tree.blockSignals(True)
        
        self.scan_results[scan_type] = []
        self.scan_thread.start()
    
    def _scan_large_files(self):
        min_size = self.size_spinbox.value()
        
        self.scan_thread = ScanThread(self.analyzer, "large_files", min_size=min_size)
        self.scan_thread.progress.connect(lambda msg: self.large_file_status.setText(msg))
        self.scan_thread.item_found.connect(lambda item: self._on_item_found(item, self.large_file_tree))
        self.scan_thread.finished.connect(lambda results: self._on_scan_finished(results, "large_files"))
        self.scan_thread.error.connect(lambda msg: self.large_file_status.setText(f"错误: {msg}"))
        
        self.large_file_tree.clear()
        self.large_file_tree.blockSignals(True)
        self.scan_results["large_files"] = []
        
        self.scan_thread.start()
    
    def _analyze_app(self):
        current_data = self.app_combo.currentData()
        if not current_data:
            QMessageBox.information(self, "提示", "请先选择一个应用")
            return
        
        bundle_id, app_name, app_path = current_data
        
        self.app_file_tree.clear()
        self.app_file_tree.blockSignals(True)
        self.app_analysis_status.setText("正在分析...")
        
        self.app_analysis_thread = AppAnalysisThread(self.analyzer, bundle_id, app_name)
        self.app_analysis_thread.progress.connect(lambda msg: self.app_analysis_status.setText(msg))
        self.app_analysis_thread.finished.connect(self._on_app_analysis_finished)
        self.app_analysis_thread.start()
    
    def _on_item_found(self, item: FileItem, tree: QTreeWidget):
        self._add_item_to_tree(tree, item)
    
    def _on_scan_finished(self, results: list, scan_type: str):
        self.scan_results[scan_type] = results
        total_size = sum(item.size for item in results)
        
        if scan_type == "cache":
            self.cache_tree.blockSignals(False)
            self.cache_stats_label.setText(f"共 {len(results)} 个文件，总大小: {self._format_size(total_size)}")
            self.cache_status_label.setText("扫描完成")
            self._change_view("cache", self.cache_view_combo.currentIndex())
        elif scan_type == "logs":
            self.log_tree.blockSignals(False)
            self.log_stats_label.setText(f"共 {len(results)} 个文件，总大小: {self._format_size(total_size)}")
            self.log_status_label.setText("扫描完成")
            self._change_view("logs", self.log_view_combo.currentIndex())
        else:
            self.large_file_tree.blockSignals(False)
            self.large_file_stats.setText(f"共 {len(results)} 个大文件，总大小: {self._format_size(total_size)}")
            self.large_file_status.setText("扫描完成")
    
    def _change_view(self, scan_type: str, view_mode: int):
        results = self.scan_results.get(scan_type, [])
        if not results:
            return
        
        if scan_type == "cache":
            tree = self.cache_tree
        else:
            tree = self.log_tree
        
        tree.blockSignals(True)
        tree.clear()
        
        if view_mode == 0:
            self._populate_by_directory(tree, results)
        else:
            self._populate_by_app(tree, results)
        
        tree.blockSignals(False)
        self._update_delete_button()
    
    def _populate_by_directory(self, tree: QTreeWidget, items: List[FileItem]):
        dir_groups: Dict[str, List[FileItem]] = {}
        
        for item in items:
            parent_dir = os.path.dirname(item.path)
            parts = parent_dir.split('/')
            if len(parts) > 5:
                group_key = '/'.join(parts[:6])
            else:
                group_key = parent_dir
            
            dir_groups.setdefault(group_key, []).append(item)
        
        for dir_path, dir_items in sorted(dir_groups.items()):
            dir_node = QTreeWidgetItem(tree)
            dir_node.setText(1, f"📁 {dir_path} ({len(dir_items)} 个)")
            dir_node.setIcon(1, QIcon.fromTheme("folder"))
            dir_node.setExpanded(True)
            dir_node.setFlags(dir_node.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            dir_node.setCheckState(0, Qt.CheckState.Unchecked)
            
            for item in sorted(dir_items, key=lambda x: x.name):
                self._add_item_to_tree(dir_node, item)
    
    def _populate_by_app(self, tree: QTreeWidget, items: List[FileItem]):
        app_groups: Dict[str, List[FileItem]] = {}
        
        for item in items:
            app_name = item.owner_app or "未知应用"
            app_groups.setdefault(app_name, []).append(item)
        
        for app_name, app_items in sorted(app_groups.items()):
            if app_items and app_items[0].owner_bundle_id:
                app_path = self.analyzer.get_app_path(app_items[0].owner_bundle_id)
                icon = self.icon_manager.get_app_icon(app_path, app_items[0].owner_bundle_id)
            else:
                icon = QIcon.fromTheme("application-x-executable")
            
            app_node = QTreeWidgetItem(tree)
            app_node.setText(1, f"{app_name} ({len(app_items)} 个)")
            app_node.setIcon(1, icon)
            app_node.setExpanded(True)
            app_node.setFlags(app_node.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            app_node.setCheckState(0, Qt.CheckState.Unchecked)
            
            for item in sorted(app_items, key=lambda x: x.name):
                self._add_item_to_tree(app_node, item)
    
    def _on_app_analysis_finished(self, app_info: Optional[AppFileInfo]):
        if not app_info:
            self.app_analysis_status.setText("分析失败")
            return
        
        self.app_file_tree.clear()
        self.app_file_tree.blockSignals(True)
        
        current_data = self.app_combo.currentData()
        app_icon = QIcon()
        if current_data:
            _, _, app_path = current_data
            app_icon = self.icon_manager.get_app_icon(app_path)
        
        file_groups = [
            (app_info.cache_files, "缓存文件"),
            (app_info.log_files, "日志文件"),
            (app_info.preference_files, "偏好设置"),
            (app_info.support_files, "应用支持文件"),
            (app_info.container_files, "容器数据"),
            (app_info.other_files, "其他文件"),
        ]
        
        for file_list, group_name in file_groups:
            if file_list:
                node = QTreeWidgetItem(self.app_file_tree)
                node.setText(1, f"{group_name} ({len(file_list)} 个)")
                node.setIcon(1, QIcon.fromTheme("folder"))
                node.setExpanded(True)
                node.setFlags(node.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                node.setCheckState(0, Qt.CheckState.Unchecked)
                for item in file_list:
                    child = self._add_item_to_tree(node, item)
                    child.setIcon(1, app_icon)
        
        self.app_file_tree.blockSignals(False)
        
        total_count = sum(len(f) for f, _ in file_groups)
        self.app_stats_label.setText(
            f"应用: {app_info.app_name} | "
            f"相关文件: {total_count} 个 | "
            f"总大小: {app_info.total_size_display}"
        )
        self.app_analysis_status.setText("分析完成")
    
    def _add_item_to_tree(self, parent, item: FileItem) -> QTreeWidgetItem:
        tree_item = QTreeWidgetItem(parent)
        tree_item.setFlags(tree_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        tree_item.setCheckState(0, Qt.CheckState.Unchecked)
        
        # 获取文件图标
        if item.owner_app and item.owner_bundle_id:
            app_path = self.analyzer.get_app_path(item.owner_bundle_id)
            icon = self.icon_manager.get_app_icon(app_path, item.owner_bundle_id)
        else:
            icon = self.icon_manager.get_icon_for_file_type(item.path, item.is_directory)
        
        tree_item.setIcon(1, icon)
        tree_item.setText(1, item.name)
        tree_item.setText(2, item.size_display)
        tree_item.setText(3, f"{get_impact_emoji(item.impact_level)} {item.impact_level.value}")
        tree_item.setText(4, item.owner_app or "未知")
        tree_item.setText(5, item.impact_description)
        tree_item.setText(6, item.last_modified or "")
        
        tree_item.setData(2, Qt.ItemDataRole.UserRole, item.size)
        tree_item.setForeground(3, QBrush(get_impact_color(item.impact_level)))
        tree_item.setData(0, Qt.ItemDataRole.UserRole, item)
        
        if item.impact_level == ImpactLevel.CRITICAL:
            tree_item.setBackground(0, QBrush(QColor(255, 205, 210)))
        elif item.impact_level == ImpactLevel.HIGH:
            tree_item.setBackground(0, QBrush(QColor(255, 235, 238)))
        
        return tree_item
    
    def _on_item_changed(self, item: QTreeWidgetItem, column: int):
        """复选框状态变化时，实现父子节点联动"""
        if column != 0:
            return
        
        # 阻止信号避免递归
        tree = item.treeWidget()
        if not tree:
            return
        
        tree.blockSignals(True)
        
        # 如果是父节点变化，同步所有子节点
        if item.childCount() > 0:
            state = item.checkState(0)
            for i in range(item.childCount()):
                item.child(i).setCheckState(0, state)
        else:
            # 如果是子节点变化，更新父节点状态
            parent = item.parent()
            if parent:
                self._update_parent_check_state(parent)
        
        tree.blockSignals(False)
        self._update_delete_button()
    
    def _update_parent_check_state(self, parent: QTreeWidgetItem):
        """更新父节点的复选框状态"""
        if parent.childCount() == 0:
            return
        
        checked_count = 0
        partial_count = 0
        
        for i in range(parent.childCount()):
            state = parent.child(i).checkState(0)
            if state == Qt.CheckState.Checked:
                checked_count += 1
            elif state == Qt.CheckState.PartiallyChecked:
                partial_count += 1
        
        if checked_count == parent.childCount():
            parent.setCheckState(0, Qt.CheckState.Checked)
        elif checked_count > 0 or partial_count > 0:
            parent.setCheckState(0, Qt.CheckState.PartiallyChecked)
        else:
            parent.setCheckState(0, Qt.CheckState.Unchecked)
    
    def _update_delete_button(self):
        """更新删除按钮状态"""
        current_tree = self._get_current_tree()
        if not current_tree:
            return
        
        checked_files = self._get_checked_files(current_tree)
        selected_files = self._get_selected_files(current_tree)
        
        # 合并，按路径去重
        seen_paths = set()
        all_files = []
        for f in checked_files + selected_files:
            if f.path not in seen_paths:
                seen_paths.add(f.path)
                all_files.append(f)
        
        has_files = len(all_files) > 0
        self.delete_selected_btn.setEnabled(has_files)
        self.preview_btn.setEnabled(len(selected_files) > 0)
        
        if checked_files:
            self.delete_selected_btn.setText(f"删除勾选的文件 ({len(checked_files)} 个)")
        elif selected_files:
            self.delete_selected_btn.setText(f"删除选中的文件 ({len(selected_files)} 个)")
        else:
            self.delete_selected_btn.setText("删除勾选的文件")

    def _filter_tree(self, tree: QTreeWidget, text: str):
        """按关键词过滤树中的文件项"""
        keyword = text.strip().lower()
        for i in range(tree.topLevelItemCount()):
            top_item = tree.topLevelItem(i)
            if not keyword:
                top_item.setHidden(False)
                for j in range(top_item.childCount()):
                    top_item.child(j).setHidden(False)
                continue

            visible_children = 0
            for j in range(top_item.childCount()):
                child = top_item.child(j)
                child_text = child.text(1).lower()
                owner_text = child.text(4).lower() if child.columnCount() > 4 else ""
                file_item = child.data(0, Qt.ItemDataRole.UserRole)
                path_text = file_item.path.lower() if file_item and isinstance(file_item, FileItem) else ""
                match = keyword in child_text or keyword in owner_text or keyword in path_text
                child.setHidden(not match)
                if match:
                    visible_children += 1

            # 父节点：如果组名匹配也全部显示
            top_text = top_item.text(1).lower()
            if keyword in top_text:
                top_item.setHidden(False)
                for j in range(top_item.childCount()):
                    top_item.child(j).setHidden(False)
            else:
                top_item.setHidden(visible_children == 0)

    def _get_checked_files(self, tree: QTreeWidget) -> List[FileItem]:
        """获取所有勾选的文件"""
        files = []
        for i in range(tree.topLevelItemCount()):
            top_item = tree.topLevelItem(i)
            # 如果父节点被勾选，获取所有子节点
            if top_item.checkState(0) == Qt.CheckState.Checked:
                for j in range(top_item.childCount()):
                    child = top_item.child(j)
                    file_item = child.data(0, Qt.ItemDataRole.UserRole)
                    if file_item and isinstance(file_item, FileItem):
                        files.append(file_item)
            else:
                # 否则只获取勾选的子节点
                for j in range(top_item.childCount()):
                    child = top_item.child(j)
                    if child.checkState(0) == Qt.CheckState.Checked:
                        file_item = child.data(0, Qt.ItemDataRole.UserRole)
                        if file_item and isinstance(file_item, FileItem):
                            files.append(file_item)
        return files
    
    def _get_selected_files(self, tree: QTreeWidget) -> List[FileItem]:
        """获取当前选中的文件（通过点击行选中）"""
        files = []
        for item in tree.selectedItems():
            file_item = item.data(0, Qt.ItemDataRole.UserRole)
            if file_item and isinstance(file_item, FileItem):
                files.append(file_item)
        return files
    
    def _toggle_all(self, tree: QTreeWidget, checked: bool):
        """全选/取消全选"""
        tree.blockSignals(True)
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        
        for i in range(tree.topLevelItemCount()):
            top_item = tree.topLevelItem(i)
            top_item.setCheckState(0, state)
            for j in range(top_item.childCount()):
                child = top_item.child(j)
                child.setCheckState(0, state)
        
        tree.blockSignals(False)
        self._update_delete_button()
    
    def _show_context_menu(self, tree: QTreeWidget, pos):
        item = tree.itemAt(pos)
        if not item:
            return
        
        file_item = item.data(0, Qt.ItemDataRole.UserRole)
        if not file_item or not isinstance(file_item, FileItem):
            return
        
        menu = QMenu(self)
        
        preview_action = QAction("预览文件", self)
        preview_action.triggered.connect(lambda: self._preview_file(file_item))
        menu.addAction(preview_action)
        
        open_action = QAction("用默认程序打开", self)
        open_action.triggered.connect(lambda: self._open_file(file_item.path))
        menu.addAction(open_action)
        
        open_folder_action = QAction("打开所在文件夹", self)
        open_folder_action.triggered.connect(lambda: self._open_containing_folder(file_item.path))
        menu.addAction(open_folder_action)
        
        menu.addSeparator()
        
        copy_path_action = QAction("复制路径", self)
        copy_path_action.triggered.connect(lambda: self._copy_path(file_item.path))
        menu.addAction(copy_path_action)
        
        menu.exec(tree.viewport().mapToGlobal(pos))
    
    def _on_item_double_clicked(self, item: QTreeWidgetItem):
        file_item = item.data(0, Qt.ItemDataRole.UserRole)
        if file_item and isinstance(file_item, FileItem):
            if os.path.exists(file_item.path):
                if file_item.is_directory:
                    self._open_file(file_item.path)
                else:
                    self._preview_file(file_item)
            else:
                QMessageBox.warning(self, "提示", "文件不存在或已被删除")
    
    def _preview_file(self, file_item: FileItem):
        if os.path.exists(file_item.path):
            dialog = FilePreviewDialog(file_item.path, self)
            dialog.exec()
        else:
            QMessageBox.warning(self, "提示", "文件不存在或已被删除")
    
    def _preview_selected(self):
        current_tree = self._get_current_tree()
        if not current_tree:
            return
        
        selected_items = current_tree.selectedItems()
        if not selected_items:
            return
        
        item = selected_items[0]
        file_item = item.data(0, Qt.ItemDataRole.UserRole)
        if file_item and isinstance(file_item, FileItem):
            self._preview_file(file_item)
    
    def _open_file(self, path: str):
        try:
            import subprocess
            subprocess.run(['open', path], check=True)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法打开: {e}")
    
    def _open_containing_folder(self, path: str):
        try:
            import subprocess
            subprocess.run(['open', '-R', path], check=True)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法打开文件夹: {e}")
    
    def _copy_path(self, path: str):
        clipboard = QApplication.clipboard()
        clipboard.setText(path)
    
    def _get_current_tree(self) -> Optional[QTreeWidget]:
        current_tab = self.tab_widget.currentIndex()
        if current_tab == 0:
            return self.cache_tree
        elif current_tab == 1:
            return self.log_tree
        elif current_tab == 2:
            return self.large_file_tree
        elif current_tab == 3:
            return self.app_file_tree
        return None
    
    def _delete_selected(self):
        current_tree = self._get_current_tree()
        if not current_tree:
            return
        
        # 获取勾选的文件
        checked_files = self._get_checked_files(current_tree)
        # 获取选中的文件（点击行选中）
        selected_files = self._get_selected_files(current_tree)
        
        # 合并，按路径去重
        seen_paths = set()
        selected = []
        for f in checked_files + selected_files:
            if f.path not in seen_paths:
                seen_paths.add(f.path)
                selected.append(f)
        
        if not selected:
            QMessageBox.information(self, "提示", 
                "请先选择要删除的文件：\n\n"
                "• 点击左侧复选框 ☑ 勾选文件\n"
                "• 点击分类节点可勾选该分类下所有文件\n"
                "• Ctrl/Shift + 点击可多选文件\n"
                "• 删除时会弹出系统密码框确认权限")
            return
        
        # 检查高风险文件
        high_risk = [f for f in selected if f.impact_level in [ImpactLevel.HIGH, ImpactLevel.CRITICAL]]
        if high_risk:
            warning_msg = "⚠️ 以下文件删除可能影响系统或应用正常运行:\n\n"
            for f in high_risk[:5]:
                warning_msg += f"• {f.name} ({f.impact_level.value})\n"
            if len(high_risk) > 5:
                warning_msg += f"\n...共 {len(high_risk)} 个高风险文件"
            warning_msg += "\n\n确定要继续删除吗？"
            
            reply = QMessageBox.warning(self, "警告", warning_msg,
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        # 确认删除
        total_size = sum(f.size for f in selected)
        reply = QMessageBox.question(self, "确认删除",
                                    f"确定要删除选中的 {len(selected)} 个文件吗？\n\n"
                                    f"总大小: {self._format_size(total_size)}\n\n"
                                    "⚠️ 此操作不可撤销！",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self._perform_delete(selected)
    
    def _perform_delete(self, files: List[FileItem]):
        import subprocess

        # 构建要删除的路径列表
        paths_to_delete = []
        for file_item in files:
            if os.path.exists(file_item.path):
                paths_to_delete.append(file_item.path)

        if not paths_to_delete:
            QMessageBox.information(self, "提示", "所选文件均已不存在。")
            return

        # 先尝试普通权限删除
        success_items = []
        need_admin_paths = []

        for file_item in files:
            if not os.path.exists(file_item.path):
                continue
            try:
                import shutil
                if os.path.isdir(file_item.path):
                    shutil.rmtree(file_item.path)
                else:
                    os.remove(file_item.path)
                success_items.append(file_item)
            except PermissionError:
                need_admin_paths.append(file_item)
            except Exception:
                need_admin_paths.append(file_item)

        # 需要管理员权限的文件，通过 osascript 一次性删除
        admin_success = []
        admin_errors = []
        if need_admin_paths:
            admin_success, admin_errors = self._delete_with_admin(need_admin_paths)
            success_items.extend(admin_success)

        # 从树中移除已删除的项
        current_tree = self._get_current_tree()
        if current_tree and success_items:
            self._remove_items_from_tree(current_tree, success_items)

        # 从 scan_results 中移除
        current_tab = self.tab_widget.currentIndex()
        scan_type_map = {0: "cache", 1: "logs", 2: "large_files"}
        if current_tab in scan_type_map:
            key = scan_type_map[current_tab]
            if key in self.scan_results:
                deleted_paths = {f.path for f in success_items}
                self.scan_results[key] = [f for f in self.scan_results[key] if f.path not in deleted_paths]

        # 更新统计
        self._update_stats()

        fail_count = len(admin_errors)
        result_msg = f"删除完成\n\n成功: {len(success_items)} 个文件"
        if fail_count > 0:
            result_msg += f"\n失败: {fail_count} 个文件"
            if admin_errors:
                result_msg += "\n\n失败文件:\n" + "\n".join(admin_errors[:10])

        QMessageBox.information(self, "删除结果", result_msg)

    def _delete_with_admin(self, files: List[FileItem]) -> tuple:
        """通过 osascript 以管理员权限删除文件（单次验证，支持 Touch ID）"""
        import subprocess
        import tempfile
        import stat

        # 将所有路径写入临时文件，避免命令行长度限制，且只需验证一次
        paths = [f.path for f in files if os.path.exists(f.path)]
        if not paths:
            return [], []

        tmp_path = ''
        script_path = ''
        try:
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
                f'with prompt "Mac卸载工具需要权限来删除文件"'
            )
            result = subprocess.run(
                ['osascript', '-e', applescript],
                capture_output=True, text=True, timeout=300
            )

            if result.returncode == 0:
                return files, []
            else:
                success = []
                errors = []
                for file_item in files:
                    if not os.path.exists(file_item.path):
                        success.append(file_item)
                    else:
                        errors.append(file_item.name)
                return success, errors
        except subprocess.TimeoutExpired:
            self._cleanup_temp_files(tmp_path, script_path)
            return [], [f.name for f in files]
        except Exception:
            self._cleanup_temp_files(tmp_path, script_path)
            return [], [f.name for f in files]

    @staticmethod
    def _cleanup_temp_files(*paths):
        for p in paths:
            if p:
                try:
                    os.unlink(p)
                except Exception:
                    pass
    
    def _remove_items_from_tree(self, tree: QTreeWidget, deleted_files: List[FileItem]):
        """从树中移除已删除的文件项"""
        deleted_paths = {f.path for f in deleted_files}
        
        tree.blockSignals(True)
        
        # 收集需要移除的顶层节点
        top_to_remove = []
        
        for i in range(tree.topLevelItemCount()):
            top_item = tree.topLevelItem(i)
            # 移除匹配的子节点
            children_to_remove = []
            for j in range(top_item.childCount()):
                child = top_item.child(j)
                file_item = child.data(0, Qt.ItemDataRole.UserRole)
                if file_item and isinstance(file_item, FileItem) and file_item.path in deleted_paths:
                    children_to_remove.append(j)
            
            # 从后往前移除子节点
            for j in reversed(children_to_remove):
                top_item.removeChild(top_item.child(j))
            
            # 更新父节点文本
            remaining = top_item.childCount()
            text = top_item.text(1)
            # 更新数量显示
            import re
            new_text = re.sub(r'\(\d+ 个\)', f'({remaining} 个)', text)
            if remaining == 0:
                top_to_remove.append(i)
            else:
                top_item.setText(1, new_text)
        
        # 从后往前移除空的顶层节点
        for i in reversed(top_to_remove):
            tree.takeTopLevelItem(i)
        
        tree.blockSignals(False)
    
    def _update_stats(self):
        """更新统计标签"""
        current_tab = self.tab_widget.currentIndex()
        if current_tab == 0:
            results = self.scan_results.get("cache", [])
            self.cache_stats_label.setText(f"共 {len(results)} 个文件，总大小: {self._format_size(sum(f.size for f in results))}")
        elif current_tab == 1:
            results = self.scan_results.get("logs", [])
            self.log_stats_label.setText(f"共 {len(results)} 个文件，总大小: {self._format_size(sum(f.size for f in results))}")
        elif current_tab == 2:
            results = self.scan_results.get("large_files", [])
            self.large_file_stats.setText(f"共 {len(results)} 个大文件，总大小: {self._format_size(sum(f.size for f in results))}")
        
        self._update_delete_button()
    
    def _format_size(self, size: int) -> str:
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        else:
            return f"{size / (1024 * 1024 * 1024):.2f} GB"