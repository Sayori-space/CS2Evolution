from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QFrame)
from PyQt5.QtCore import Qt


class HomeWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)  # 加大外边距

        # === 欢迎卡片 ===
        welcome_card = QWidget()
        welcome_card.setObjectName("ContentCard")
        welcome_layout = QVBoxLayout(welcome_card)
        welcome_layout.setContentsMargins(50, 50, 50, 50)  # 卡片内边距加大

        # 1. 大标题 (CSS #HomeTitle -> 42px)
        title = QLabel("👋 欢迎回来，炼金术师！")
        title.setObjectName("HomeTitle")
        welcome_layout.addWidget(title)

        # 2. 副标题 (CSS #HomeSubtitle -> 22px)
        subtitle = QLabel(
            "CS2 Evolution 智能炼金终端已就绪。\n"
            "选择「智能挖掘」开始探索，或前往「设置」自定义您的界面。"
        )
        subtitle.setObjectName("HomeSubtitle")
        subtitle.setWordWrap(True)
        welcome_layout.addWidget(subtitle)

        welcome_layout.addSpacing(40)

        # 3. 状态统计区
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(40)  # 加大统计块间距

        # 辅助函数：创建统计块
        def create_stat_block(emoji, label, value):
            container = QFrame()
            # 移除背景色，让数字直接浮在卡片上
            l = QVBoxLayout(container)
            l.setContentsMargins(0, 0, 0, 0)
            l.setSpacing(5)

            val_lbl = QLabel(f"{emoji} {value}")
            val_lbl.setObjectName("StatNumber")  # 56px 超大字体

            name_lbl = QLabel(label)
            name_lbl.setObjectName("StatLabel")  # 20px

            l.addWidget(val_lbl)
            l.addWidget(name_lbl)
            return container

        # 模拟数据
        stats_layout.addWidget(create_stat_block("📦", "数据库收录", "25,000+"))
        stats_layout.addWidget(create_stat_block("⚡", "本周挖掘", "12"))
        stats_layout.addWidget(create_stat_block("💎", "发现高利", "3"))

        welcome_layout.addLayout(stats_layout)
        welcome_layout.addStretch()

        layout.addWidget(welcome_card)