#!/usr/bin/env python3
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QProgressBar, QLabel, QPushButton
from PyQt6.QtCore import Qt, QThread, pyqtSignal


class ProgressDialog(QDialog):
    """进度对话框"""
    
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(400)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        
        self._init_ui()
        
    def _init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        
        # 状态标签
        self.status_label = QLabel("准备中...")
        layout.addWidget(self.status_label)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)
        
        # 详细信息标签
        self.detail_label = QLabel("")
        layout.addWidget(self.detail_label)
        
        # 取消按钮
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        layout.addWidget(self.cancel_button)
        
        self.setMinimumHeight(150)
    
    def update_progress(self, current: int, total: int, message: str = ""):
        """更新进度"""
        if total > 0:
            progress = int((current / total) * 100)
            self.progress_bar.setValue(progress)
        
        if message:
            self.detail_label.setText(message)
        
        self.status_label.setText(f"处理中... ({current}/{total})")
    
    def set_completed(self, success: bool, message: str):
        """设置完成状态"""
        self.progress_bar.setValue(100)
        self.status_label.setText("完成" if success else "失败")
        self.detail_label.setText(message)
        self.cancel_button.setText("关闭")