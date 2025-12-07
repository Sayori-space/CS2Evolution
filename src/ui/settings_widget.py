from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel,
                             QGroupBox, QGridLayout, QButtonGroup)
from PyQt5.QtCore import pyqtSignal, Qt

# ✅ 尝试导入 THEMES，如果 styles.py 没更新成功则使用备用方案，防止报错
try:
    from src.ui.styles import THEMES
except ImportError:
    print("⚠️ 警告: 无法从 src.ui.styles 导入 THEMES，使用默认值")
    THEMES = {"商务蓝 (Default)": {}}


class SettingsWidget(QWidget):
    theme_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(30)

        # 卡片容器
        self.card = QWidget()
        self.card.setObjectName("ContentCard")
        main_layout.addWidget(self.card)

        layout = QVBoxLayout(self.card)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(25)

        # 标题 (使用首页大标题样式)
        title = QLabel("⚙️ 系统设置")
        title.setObjectName("HomeTitle")
        layout.addWidget(title)

        subtitle = QLabel("在此处自定义您的工作台外观与偏好。")
        subtitle.setObjectName("HomeSubtitle")
        layout.addWidget(subtitle)

        layout.addSpacing(30)

        # === 主题选择区域 ===
        group = QGroupBox("🎨 界面配色方案 (Color Themes)")
        group_layout = QGridLayout(group)
        group_layout.setSpacing(25)
        group_layout.setContentsMargins(20, 30, 20, 20)

        self.btn_group = QButtonGroup(self)

        row, col = 0, 0
        for name in THEMES.keys():
            # 创建主题按钮
            btn = QPushButton(f"{name}")
            btn.setObjectName("ThemeBtn")  # 应用特殊样式
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)

            # 添加 Emoji 图标
            if "Dark" in name:
                btn.setText(f"🌙  {name}")
            elif "Forest" in name:
                btn.setText(f"🌿  {name}")
            else:
                btn.setText(f"👔  {name}")

            # 绑定点击事件
            btn.clicked.connect(lambda checked, n=name: self.change_theme(n))

            if "商务蓝" in name:
                btn.setChecked(True)

            self.btn_group.addButton(btn)
            group_layout.addWidget(btn, row, col)

            col += 1
            if col > 1:  # 每行显示2个
                col = 0
                row += 1

        layout.addWidget(group)
        layout.addStretch()

    def change_theme(self, theme_name):
        self.theme_signal.emit(theme_name)