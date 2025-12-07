import sys
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QListWidget, QListWidgetItem, QStackedWidget, QLabel)
from PyQt5.QtCore import Qt, QSize

from src.ui.home_widget import HomeWidget
from src.ui.workbench_widget import WorkbenchWidget
from src.ui.optimizer_widget import OptimizerWidget
from src.ui.chart_viewer import ChartViewWidget
from src.ui.settings_widget import SettingsWidget
# 引入新模块
from src.ui.network_widget import NetworkWidget
from src.ui.prediction_widget import PredictionWidget
from src.ui.styles import get_app_style


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CS2 智能炼金终端 (Ultimate Edition)")
        self.resize(1400, 950)

        # 默认主题
        self.setStyleSheet(get_app_style("商务蓝 (Default)"))

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        self.main_layout = QHBoxLayout(main_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # === 侧边栏 ===
        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(280)
        self.sidebar.setFocusPolicy(Qt.NoFocus)

        # 导航项配置
        nav_items = [
            "🏠  首页概览 (Home)",
            "🛠️  手动沙盒 (Sandbox)",
            "🚀  智能挖掘 (Auto)",
            "🕸️  网络分析 (Network)",  # ✅ 图论入口
            "🔮  价格预测 (Predict)",  # ✅ AI入口
            "📊  数据图表 (Charts)",
            "⚙️  系统设置 (Settings)"
        ]

        for item_name in nav_items:
            item = QListWidgetItem(item_name)
            item.setSizeHint(QSize(0, 80))
            item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            self.sidebar.addItem(item)

        # === 内容堆栈 ===
        self.pages = QStackedWidget()

        self.home_page = HomeWidget()
        self.pages.addWidget(self.home_page)  # 0

        self.workbench_page = WorkbenchWidget()
        self.pages.addWidget(self.workbench_page)  # 1

        self.optimizer_page = OptimizerWidget()
        self.pages.addWidget(self.optimizer_page)  # 2

        self.network_page = NetworkWidget()  # ✅ 3
        self.pages.addWidget(self.network_page)

        self.predict_page = PredictionWidget()  # ✅ 4
        self.pages.addWidget(self.predict_page)

        self.chart_page = ChartViewWidget()
        self.pages.addWidget(self.chart_page)  # 5

        self.settings_page = SettingsWidget()
        self.settings_page.theme_signal.connect(self.update_theme)
        self.pages.addWidget(self.settings_page)  # 6

        self.main_layout.addWidget(self.sidebar)
        self.main_layout.addWidget(self.pages)

        # 绑定导航事件
        self.sidebar.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.sidebar.setCurrentRow(0)

    def update_theme(self, theme_name):
        """全局主题切换"""
        print(f"🔄 切换主题: {theme_name}")
        # 1. 更新 QSS
        new_style = get_app_style(theme_name)
        self.setStyleSheet(new_style)

        # 2. 通知网络图组件更新背景色
        if hasattr(self, 'network_page'):
            self.network_page.set_theme(theme_name)