# src/ui/styles.py

# ==========================================
# 1. 定义多套配色方案 (THEMES) - 供设置页导入
# ==========================================
THEMES = {
    "商务蓝 (Default)": {
        "bg_main": "#f0f2f5",
        "bg_card": "#ffffff",
        "sidebar_bg": "#001529",
        "sidebar_text": "rgba(255, 255, 255, 0.65)",
        "sidebar_active_bg": "#111d2c",
        "text_pri": "#262626",  # 深灰文字
        "text_sec": "#8c8c8c",  # 浅灰文字
        "accent": "#1890ff",  # 科技蓝
        "accent_hover": "#40a9ff",
        "border": "#d9d9d9",
        "input_bg": "#ffffff",  # 白底输入框
        "input_text": "#262626",
        "group_bg": "#fafafa"  # 分组框浅底
    },
    "暗夜黑 (Dark Mode)": {
        "bg_main": "#121212",  # 极深灰背景
        "bg_card": "#1e1e1e",  # 深灰卡片
        "sidebar_bg": "#000000",  # 纯黑侧边栏
        "sidebar_text": "#a0a0a0",
        "sidebar_active_bg": "#333333",
        "text_pri": "#e0e0e0",  # 亮灰文字 (解决看不清的问题)
        "text_sec": "#a0a0a0",  # 中灰文字
        "accent": "#bb86fc",  # 荧光紫 (深色模式常用强调色)
        "accent_hover": "#d0aaff",
        "border": "#333333",  # 深色边框
        "input_bg": "#2d2d2d",  # 深灰输入框 (解决白底刺眼问题)
        "input_text": "#ffffff",  # 输入框白字
        "group_bg": "#252525"  # 分组框深底
    },
    "森林绿 (Forest)": {
        "bg_main": "#f6ffed",
        "bg_card": "#ffffff",
        "sidebar_bg": "#135200",
        "sidebar_text": "rgba(255, 255, 255, 0.7)",
        "sidebar_active_bg": "#092b00",
        "text_pri": "#262626",
        "text_sec": "#5b8c00",
        "accent": "#52c41a",
        "accent_hover": "#73d13d",
        "border": "#b7eb8f",
        "input_bg": "#ffffff",
        "input_text": "#262626",
        "group_bg": "#f6ffed"
    }
}


def get_app_style(theme_name="商务蓝 (Default)"):
    # 如果找不到对应主题，默认回退到商务蓝
    t = THEMES.get(theme_name, THEMES["商务蓝 (Default)"])

    return f"""
    /* ================= 全局基础 ================= */
    QWidget {{
        font-family: 'Microsoft YaHei', 'Segoe UI', sans-serif;
        font-size: 18px; /* 全局默认字体 */
        color: {t['text_pri']}; /* ✅ 强制所有组件默认文字颜色 */
        background-color: transparent; /* 默认透明，由父容器控制 */
    }}

    QMainWindow {{
        background-color: {t['bg_main']};
    }}

    /* ================= 首页专项优化 (Home Widget) - 巨型字体 ================= */
    QLabel#HomeTitle {{
        font-size: 42px;
        font-weight: bold;
        color: {t['accent']};
        margin-bottom: 25px;
        background-color: transparent;
    }}

    QLabel#HomeSubtitle {{
        font-size: 22px;
        color: {t['text_sec']};
        line-height: 1.6;
        background-color: transparent;
    }}

    /* 首页统计数字 */
    QLabel#StatNumber {{
        font-size: 56px;
        font-weight: bold;
        color: {t['text_pri']};
        background-color: transparent;
    }}

    /* 首页统计标签 */
    QLabel#StatLabel {{
        font-size: 20px;
        color: {t['text_sec']};
        background-color: transparent;
    }}

    /* ================= 侧边栏 (Sidebar) ================= */
    QListWidget {{
        background-color: {t['sidebar_bg']};
        border: none;
        outline: none;
        padding-top: 20px;
    }}

    QListWidget::item {{
        color: {t['sidebar_text']};
        padding: 22px 28px;
        border-left: 6px solid transparent;
        margin-bottom: 5px;
        background-color: transparent;
        font-size: 19px;
    }}

    QListWidget::item:hover {{
        color: #ffffff;
        background-color: rgba(255, 255, 255, 0.1);
    }}

    QListWidget::item:selected {{
        background-color: {t['sidebar_active_bg']};
        color: #ffffff;
        border-left: 6px solid {t['accent']};
        font-weight: bold;
    }}

    /* ================= 卡片容器 (Card) ================= */
    QWidget#ContentCard {{
        background-color: {t['bg_card']}; /* ✅ 卡片背景色 */
        border: 1px solid {t['border']};
        border-radius: 12px;
        border-bottom: 3px solid {t['border']};
    }}

    /* ================= 普通标签 (Label) ================= */
    /* ✅ 强制修复深色模式下标签看不清的问题 */
    QLabel {{
        color: {t['text_pri']};
        background-color: transparent; /* 避免遮挡卡片背景 */
    }}

    /* ================= 按钮 (Buttons) ================= */
    QPushButton {{
        background-color: {t['accent']};
        color: #ffffff; /* 按钮文字永远是白色 */
        border: none;
        border-radius: 8px;
        padding: 14px 28px;
        font-size: 19px;
        font-weight: bold;
    }}
    QPushButton:hover {{
        background-color: {t['accent_hover']};
        margin-top: 2px;
    }}
    QPushButton:pressed {{
        margin-top: 4px;
    }}

    /* 设置页面的主题按钮 */
    QPushButton#ThemeBtn {{
        background-color: {t['bg_card']};
        color: {t['text_pri']}; /*跟随主题色*/
        border: 2px solid {t['border']};
        text-align: left;
        padding: 25px;
        font-size: 22px;
    }}
    QPushButton#ThemeBtn:checked {{
        border: 2px solid {t['accent']};
        background-color: {t['bg_main']};
        color: {t['accent']};
    }}

    /* ================= 输入控件 ================= */
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
        border: 1px solid {t['border']};
        border-radius: 6px;
        padding: 12px 14px;
        background-color: {t['input_bg']}; /* ✅ 修复输入框背景 */
        color: {t['input_text']};       /* ✅ 修复输入框文字颜色 */
        selection-background-color: {t['accent']};
        font-size: 18px;
    }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
        border: 2px solid {t['accent']};
    }}

    /* QComboBox 下拉列表修复 */
    QComboBox QAbstractItemView {{
        background-color: {t['bg_card']}; /* 下拉菜单背景 */
        color: {t['text_pri']};       /* 下拉菜单文字 */
        selection-background-color: {t['accent']};
        selection-color: #ffffff;
        border: 1px solid {t['border']};
    }}

    /* ================= 表格 ================= */
    QTableWidget {{
        border: 1px solid {t['border']};
        background-color: {t['bg_card']};
        gridline-color: {t['bg_main']};
        color: {t['text_pri']};
        font-size: 18px;
    }}
    QHeaderView::section {{
        background-color: {t['bg_main']};
        padding: 16px;
        border: none;
        border-bottom: 2px solid {t['accent']};
        font-weight: bold;
        color: {t['text_pri']}; /* 表头文字跟随主题 */
        font-size: 18px;
    }}
    QTableWidget::item {{
        padding: 10px;
        border-bottom: 1px solid {t['bg_main']};
    }}
    /* 单元格选中状态 */
    QTableWidget::item:selected {{
        background-color: {t['accent']};
        color: #ffffff;
    }}

    /* ================= 分组框 & 标签 ================= */
    QGroupBox {{
        border: 1px solid {t['border']};
        border-radius: 8px;
        margin-top: 30px;
        padding-top: 30px;
        color: {t['text_pri']};
        font-size: 20px;
        background-color: {t['group_bg']}; /* ✅ 分组框背景色 */
    }}
    QGroupBox::title {{
        color: {t['text_sec']};
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 5px;
        background-color: transparent;
    }}

    /* ================= 文本显示区 (Log/TextEdit) ================= */
    QTextEdit, QTextBrowser {{
        background-color: {t['input_bg']};
        color: {t['text_pri']};
        border: 1px solid {t['border']};
        border-radius: 6px;
    }}
    """