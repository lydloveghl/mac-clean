#!/usr/bin/env python3
import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                              QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
                              QHeaderView, QLabel, QMessageBox, QMenuBar, QMenu,
                              QLineEdit)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QAction

from app_scanner import AppScanner, AppInfo
from uninstaller import Uninstaller
from cache_selector import UninstallConfirmDialog
from progress_dialog import ProgressDialog
from file_cleanup_dialog import FileCleanupDialog
from app_icon_manager import AppIconManager


class ScanThread(QThread):
    """扫描线程 - 边扫描边发送结果"""
    app_found = pyqtSignal(object)  # 单个应用
    finished = pyqtSignal(int)  # 总数
    error = pyqtSignal(str)
    
    def __init__(self, scanner: AppScanner):
        super().__init__()
        self.scanner = scanner
    
    def run(self):
        try:
            # 设置回调，每找到一个应用就发送信号
            self.scanner.set_app_found_callback(
                lambda app: self.app_found.emit(app)
            )
            
            # 快速扫描，不计算大小
            apps = self.scanner.scan_applications_async()
            self.finished.emit(len(apps))
        except Exception as e:
            self.error.emit(str(e))


class SizeCalcThread(QThread):
    """大小计算线程"""
    progress = pyqtSignal(int, int, str)  # 当前, 总数, 应用名
    size_updated = pyqtSignal(int, int)  # 索引, 大小
    finished = pyqtSignal()
    
    def __init__(self, scanner: AppScanner, apps: list):
        super().__init__()
        self.scanner = scanner
        self.apps = apps
    
    def run(self):
        total = len(self.apps)
        for i, app in enumerate(self.apps):
            self.progress.emit(i + 1, total, app.name)
            app.size = self.scanner.calculate_app_size(app)
            self.size_updated.emit(i, app.size)
        self.finished.emit()


class UninstallThread(QThread):
    """卸载线程"""
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(object)
    
    def __init__(self, uninstaller: Uninstaller, app_path: str, 
                 delete_cache: bool, cache_paths: list):
        super().__init__()
        self.uninstaller = uninstaller
        self.app_path = app_path
        self.delete_cache = delete_cache
        self.cache_paths = cache_paths
        
        self.uninstaller.set_progress_callback(self._on_progress)
    
    def _on_progress(self, current: int, total: int, message: str):
        self.progress.emit(current, total, message)
    
    def run(self):
        try:
            result = self.uninstaller.uninstall_application(
                self.app_path,
                self.delete_cache,
                self.cache_paths,
                use_sudo=True
            )
            self.finished.emit(result)
        except Exception as e:
            from uninstaller import UninstallResult
            result = UninstallResult(
                success=False,
                app_removed=False,
                cache_removed=False,
                removed_cache_paths=[],
                errors=[str(e)],
                message=f"卸载失败: {e}"
            )
            self.finished.emit(result)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mac应用卸载工具")
        self.setMinimumSize(900, 650)
        
        self.applications = []
        self.scanner = AppScanner()
        self.uninstaller = Uninstaller()
        self.icon_manager = AppIconManager()
        
        self._init_ui()
        self._connect_signals()
        
    def _init_ui(self):
        """初始化界面"""
        # 创建菜单栏
        self._create_menu_bar()
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # 顶部工具栏
        toolbar_layout = QHBoxLayout()
        
        self.scan_button = QPushButton("扫描已安装应用")
        self.scan_button.setStyleSheet("padding: 8px 16px;")
        toolbar_layout.addWidget(self.scan_button)
        
        self.refresh_button = QPushButton("刷新列表")
        self.refresh_button.setStyleSheet("padding: 8px 16px;")
        self.refresh_button.setEnabled(False)
        toolbar_layout.addWidget(self.refresh_button)
        
        # 文件清理按钮
        self.file_cleanup_button = QPushButton("文件清理工具")
        self.file_cleanup_button.setStyleSheet("padding: 8px 16px; background-color: #2196F3; color: white;")
        self.file_cleanup_button.clicked.connect(self._open_file_cleanup)
        toolbar_layout.addWidget(self.file_cleanup_button)
        
        toolbar_layout.addStretch()
        
        self.app_count_label = QLabel("已安装应用: 0")
        self.app_count_label.setStyleSheet("font-weight: bold;")
        toolbar_layout.addWidget(self.app_count_label)
        
        layout.addLayout(toolbar_layout)

        # 搜索栏
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索应用（名称、Bundle ID、路径）...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._filter_applications)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        # 应用列表表格
        self.app_table = QTableWidget()
        self.app_table.setColumnCount(6)
        self.app_table.setHorizontalHeaderLabels(["", "应用名称", "版本", "大小", "Bundle ID", "路径"])
        self.app_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.app_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.app_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.app_table.setAlternatingRowColors(True)
        self.app_table.setIconSize(QSize(32, 32))
        # 设置图标列宽度
        self.app_table.horizontalHeader().resizeSection(0, 40)
        layout.addWidget(self.app_table)
        
        # 底部操作栏
        bottom_layout = QHBoxLayout()
        
        self.select_all_button = QPushButton("全选")
        self.select_all_button.setEnabled(False)
        bottom_layout.addWidget(self.select_all_button)
        
        self.deselect_button = QPushButton("取消全选")
        self.deselect_button.setEnabled(False)
        bottom_layout.addWidget(self.deselect_button)
        
        bottom_layout.addStretch()
        
        self.uninstall_button = QPushButton("卸载选中应用")
        self.uninstall_button.setStyleSheet("background-color: #ff6b6b; color: white; padding: 8px 16px;")
        self.uninstall_button.setEnabled(False)
        bottom_layout.addWidget(self.uninstall_button)
        
        layout.addLayout(bottom_layout)
        
        # 状态栏
        self.statusBar().showMessage("就绪")
    
    def _create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        scan_action = QAction("扫描已安装应用", self)
        scan_action.triggered.connect(self.scan_applications)
        file_menu.addAction(scan_action)
        
        file_menu.addSeparator()
        
        cleanup_action = QAction("文件清理工具", self)
        cleanup_action.triggered.connect(self._open_file_cleanup)
        file_menu.addAction(cleanup_action)
        
        file_menu.addSeparator()
        
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu("工具")
        
        cache_action = QAction("缓存清理", self)
        cache_action.triggered.connect(lambda: self._open_file_cleanup_tab(0))
        tools_menu.addAction(cache_action)
        
        log_action = QAction("日志清理", self)
        log_action.triggered.connect(lambda: self._open_file_cleanup_tab(1))
        tools_menu.addAction(log_action)
        
        large_file_action = QAction("大文件清理", self)
        large_file_action.triggered.connect(lambda: self._open_file_cleanup_tab(2))
        tools_menu.addAction(large_file_action)
        
        app_analysis_action = QAction("应用文件分析", self)
        app_analysis_action.triggered.connect(lambda: self._open_file_cleanup_tab(3))
        tools_menu.addAction(app_analysis_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        
        about_action = QAction("关于", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _open_file_cleanup(self):
        """打开文件清理对话框"""
        dialog = FileCleanupDialog(self)
        dialog.exec()
    
    def _open_file_cleanup_tab(self, tab_index: int):
        """打开文件清理对话框并切换到指定标签页"""
        dialog = FileCleanupDialog(self)
        dialog.tab_widget.setCurrentIndex(tab_index)
        dialog.exec()
    
    def _show_about(self):
        """显示关于对话框"""
        QMessageBox.about(self, "关于 Mac应用卸载工具",
                         "Mac应用卸载工具 v1.0\n\n"
                         "功能特性:\n"
                         "• 扫描并卸载已安装应用\n"
                         "• 清理缓存、日志等垃圾文件\n"
                         "• 查找和清理大文件\n"
                         "• 分析应用相关文件\n"
                         "• 显示文件从属关系和删除影响\n\n"
                         "⚠️ 删除操作不可撤销，请谨慎操作！")
    
    def _connect_signals(self):
        self.scan_button.clicked.connect(self.scan_applications)
        self.refresh_button.clicked.connect(self.refresh_list)
        self.select_all_button.clicked.connect(self.select_all)
        self.deselect_button.clicked.connect(self.deselect_all)
        self.uninstall_button.clicked.connect(self.uninstall_selected)
        self.app_table.itemSelectionChanged.connect(self._on_selection_changed)
    
    def scan_applications(self):
        """扫描已安装的应用程序"""
        self.scan_button.setEnabled(False)
        self.refresh_button.setEnabled(False)
        self.applications = []
        self.app_table.setRowCount(0)
        self.statusBar().showMessage("正在扫描应用程序...")
        
        # 创建扫描线程
        self.scan_thread = ScanThread(self.scanner)
        self.scan_thread.app_found.connect(self._on_app_found)
        self.scan_thread.finished.connect(self._on_scan_finished)
        self.scan_thread.error.connect(self._on_scan_error)
        self.scan_thread.start()
    
    def _on_app_found(self, app: AppInfo):
        """找到一个应用时立即添加到表格"""
        row = self.app_table.rowCount()
        self.app_table.insertRow(row)
        
        # 获取应用图标
        icon = self.icon_manager.get_app_icon(app.path, app.bundle_identifier)
        
        # 图标列
        icon_item = QTableWidgetItem()
        icon_item.setIcon(icon)
        icon_item.setFlags(icon_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.app_table.setItem(row, 0, icon_item)
        
        # 应用名称
        name_item = QTableWidgetItem(app.name)
        name_item.setData(Qt.ItemDataRole.UserRole, app)
        self.app_table.setItem(row, 1, name_item)
        
        # 版本
        version_item = QTableWidgetItem(f"{app.version} ({app.build_version})")
        self.app_table.setItem(row, 2, version_item)
        
        # 大小（先显示"计算中..."）
        size_item = QTableWidgetItem("计算中...")
        self.app_table.setItem(row, 3, size_item)
        
        # Bundle ID
        bundle_item = QTableWidgetItem(app.bundle_identifier)
        self.app_table.setItem(row, 4, bundle_item)
        
        # 路径
        path_item = QTableWidgetItem(app.path)
        self.app_table.setItem(row, 5, path_item)
        
        self.applications.append(app)
        self.app_count_label.setText(f"已安装应用: {len(self.applications)}")
    
    def _on_scan_finished(self, count: int):
        """扫描完成"""
        self.statusBar().showMessage(f"扫描完成，找到 {count} 个应用程序，正在计算大小...")
        
        # 调整列宽
        self.app_table.resizeColumnsToContents()
        self.app_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        
        self.scan_button.setEnabled(True)
        self.refresh_button.setEnabled(True)
        self.select_all_button.setEnabled(True)
        self.deselect_button.setEnabled(True)
        
        # 后台计算大小
        self._start_size_calculation()
    
    def _start_size_calculation(self):
        """开始后台计算大小"""
        self.size_calc_thread = SizeCalcThread(self.scanner, self.applications)
        self.size_calc_thread.progress.connect(self._on_size_calc_progress)
        self.size_calc_thread.size_updated.connect(self._on_size_updated)
        self.size_calc_thread.finished.connect(self._on_size_calc_finished)
        self.size_calc_thread.start()
    
    def _on_size_calc_progress(self, current: int, total: int, name: str):
        """大小计算进度"""
        self.statusBar().showMessage(f"正在计算大小: {current}/{total} - {name}")
    
    def _on_size_updated(self, index: int, size: int):
        """更新单个应用的大小显示"""
        if index < self.app_table.rowCount():
            app = self.applications[index]
            size_item = QTableWidgetItem(app.size_display)
            size_item.setData(Qt.ItemDataRole.UserRole, size)
            self.app_table.setItem(index, 3, size_item)
    
    def _on_size_calc_finished(self):
        """大小计算完成"""
        self.statusBar().showMessage(f"就绪 - 共 {len(self.applications)} 个应用程序")
    
    def _on_scan_error(self, error_msg: str):
        """扫描出错"""
        self.scan_button.setEnabled(True)
        self.refresh_button.setEnabled(True)
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("扫描错误")
        msg_box.setText(f"扫描应用程序时发生错误:\n{error_msg}")
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.addButton("确定", QMessageBox.ButtonRole.AcceptRole)
        msg_box.exec()
        self.statusBar().showMessage("扫描失败")
    
    def refresh_list(self):
        """刷新应用列表"""
        self.scan_applications()
    
    def select_all(self):
        """全选应用"""
        self.app_table.selectAll()
    
    def deselect_all(self):
        """取消全选"""
        self.app_table.clearSelection()
    
    def _on_selection_changed(self):
        """选择变化时更新按钮状态"""
        has_selection = len(self.app_table.selectedItems()) > 0
        self.uninstall_button.setEnabled(has_selection)

    def _filter_applications(self, text: str):
        """按关键词过滤应用列表"""
        keyword = text.strip().lower()
        for row in range(self.app_table.rowCount()):
            if not keyword:
                self.app_table.setRowHidden(row, False)
                continue
            name_item = self.app_table.item(row, 1)
            bundle_item = self.app_table.item(row, 4)
            path_item = self.app_table.item(row, 5)
            match = False
            for item in (name_item, bundle_item, path_item):
                if item and keyword in item.text().lower():
                    match = True
                    break
            self.app_table.setRowHidden(row, not match)
    
    def uninstall_selected(self):
        """卸载选中的应用"""
        selected_rows = set()
        for item in self.app_table.selectedItems():
            selected_rows.add(item.row())
        
        if not selected_rows:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("提示")
            msg_box.setText("请先选择要卸载的应用")
            msg_box.setIcon(QMessageBox.Icon.Information)
            msg_box.addButton("确定", QMessageBox.ButtonRole.AcceptRole)
            msg_box.exec()
            return
        
        selected_apps = []
        for row in selected_rows:
            name_item = self.app_table.item(row, 1)  # 列1是应用名称
            if name_item:
                app_info = name_item.data(Qt.ItemDataRole.UserRole)
                if app_info:
                    selected_apps.append(app_info)
        
        if not selected_apps:
            return
        
        if len(selected_apps) == 1:
            app = selected_apps[0]
            self._uninstall_single_app(app)
        else:
            self._uninstall_multiple_apps(selected_apps)
    
    def _uninstall_single_app(self, app: AppInfo):
        """卸载单个应用"""
        cache_paths = self.scanner.get_app_cache_paths(app.bundle_identifier)
        
        dialog = UninstallConfirmDialog(app.name, app.path, cache_paths, self)
        if dialog.exec() == UninstallConfirmDialog.DialogCode.Accepted:
            delete_cache, selected_cache_paths = dialog.get_uninstall_options()
            self._execute_uninstall(app, delete_cache, selected_cache_paths)
    
    def _uninstall_multiple_apps(self, apps: list):
        """批量卸载多个应用"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("确认卸载")
        msg_box.setText(f"确定要永久删除选中的 {len(apps)} 个应用吗？\n\n⚠️ 此操作不可撤销！")
        msg_box.setIcon(QMessageBox.Icon.Warning)
        
        yes_button = msg_box.addButton("确定删除", QMessageBox.ButtonRole.YesRole)
        msg_box.addButton("取消", QMessageBox.ButtonRole.NoRole)
        msg_box.setDefaultButton(yes_button)
        
        msg_box.exec()
        
        if msg_box.clickedButton() == yes_button:
            for app in apps:
                self._execute_uninstall(app, False, [])
    
    def _execute_uninstall(self, app: AppInfo, delete_cache: bool, cache_paths: list):
        """执行卸载操作"""
        progress_dialog = ProgressDialog(f"正在卸载 {app.name}", self)
        progress_dialog.show()
        
        self.uninstall_thread = UninstallThread(
            self.uninstaller, app.path, delete_cache, cache_paths
        )
        
        self.uninstall_thread.progress.connect(
            lambda current, total, msg: progress_dialog.update_progress(current, total, msg)
        )
        self.uninstall_thread.finished.connect(
            lambda result: self._on_uninstall_finished(result, app, progress_dialog)
        )
        
        self.uninstall_thread.start()
    
    def _on_uninstall_finished(self, result, app: AppInfo, progress_dialog: ProgressDialog):
        """卸载完成"""
        progress_dialog.set_completed(result.success, result.message)
        
        if result.success:
            # 从表格中移除
            for row in range(self.app_table.rowCount()):
                name_item = self.app_table.item(row, 1)  # 列1是应用名称
                if name_item:
                    stored_app = name_item.data(Qt.ItemDataRole.UserRole)
                    if stored_app and stored_app.path == app.path:
                        self.app_table.removeRow(row)
                        break
            
            # 从列表中移除
            self.applications = [a for a in self.applications if a.path != app.path]
            self.app_count_label.setText(f"已安装应用: {len(self.applications)}")
            
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("卸载成功")
            msg_box.setText(result.message)
            msg_box.setIcon(QMessageBox.Icon.Information)
            msg_box.addButton("确定", QMessageBox.ButtonRole.AcceptRole)
            msg_box.exec()
        else:
            error_msg = "\n".join(result.errors) if result.errors else "未知错误"
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("卸载失败")
            msg_box.setText(f"{result.message}\n\n错误详情:\n{error_msg}")
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.addButton("确定", QMessageBox.ButtonRole.AcceptRole)
            msg_box.exec()
        
        self.statusBar().showMessage(f"已卸载: {app.name}")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()