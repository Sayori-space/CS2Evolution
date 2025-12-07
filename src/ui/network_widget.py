import os
import webbrowser
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QComboBox, QCheckBox, QProgressBar, QFrame, QMessageBox)
from PyQt5.QtCore import QUrl, QThread, pyqtSignal, Qt

try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings

    WEB_ENGINE_AVAILABLE = True
except ImportError:
    WEB_ENGINE_AVAILABLE = False

from src.core.network_graph import NetworkAnalyzer
from src.ui.styles import THEMES
import config


class NetworkWorker(QThread):
    finished_signal = pyqtSignal(str, dict, str)

    def __init__(self, db_path, filters, theme_colors):
        super().__init__()
        self.db_path = db_path
        self.filters = filters
        self.theme_colors = theme_colors

    def run(self):
        try:
            analyzer = NetworkAnalyzer(self.db_path)
            metrics = analyzer.calculate_centrality()

            output_dir = os.path.join(os.getcwd(), "CS2_Reports", "network_viz")
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            html_path = os.path.join(output_dir, "network.html")
            rarity_filter = self.filters.get('rarities')
            top_n = self.filters.get('top_n', 100)

            # 传递主题颜色
            final_path = analyzer.generate_interactive_html(html_path, rarity_filter, top_n, self.theme_colors)

            self.finished_signal.emit(final_path, metrics, "")

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.finished_signal.emit("", {}, str(e))


class NetworkWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.current_theme = "商务蓝 (Default)"
        self.last_html_path = ""
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # === 顶部控制栏 ===
        ctrl_panel = QWidget()
        ctrl_panel.setStyleSheet("background-color: #ffffff; border-bottom: 1px solid #dcdcdc;")
        ctrl_panel.setFixedHeight(80)

        ctrl_layout = QHBoxLayout(ctrl_panel)
        ctrl_layout.setContentsMargins(20, 10, 20, 10)

        lbl_title = QLabel("🕸️ 网络分析")
        lbl_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #2c3e50;")
        ctrl_layout.addWidget(lbl_title)

        ctrl_layout.addSpacing(20)
        ctrl_layout.addWidget(QLabel("展示层级:"))
        self.combo_rarity = QComboBox()
        self.combo_rarity.addItems(["全部层级", "工业 -> 军规", "军规 -> 受限", "受限 -> 保密"])
        self.combo_rarity.setCurrentIndex(2)
        ctrl_layout.addWidget(self.combo_rarity)

        ctrl_layout.addSpacing(10)
        ctrl_layout.addWidget(QLabel("Top节点:"))
        self.combo_topn = QComboBox()
        self.combo_topn.addItems(["50", "100", "200", "500"])
        self.combo_topn.setCurrentIndex(1)
        ctrl_layout.addWidget(self.combo_topn)

        ctrl_layout.addSpacing(20)
        self.btn_analyze = QPushButton("🚀 生成图谱")
        self.btn_analyze.clicked.connect(self.start_analysis)
        self.btn_analyze.setStyleSheet("""
            QPushButton { background-color: #1890ff; color: white; border-radius: 4px; padding: 8px 16px; font-size: 14px;}
            QPushButton:hover { background-color: #40a9ff; }
        """)
        ctrl_layout.addWidget(self.btn_analyze)

        # 浏览器打开按钮
        self.btn_browser = QPushButton("🌐 浏览器打开")
        self.btn_browser.clicked.connect(self.open_in_browser)
        self.btn_browser.setEnabled(False)
        self.btn_browser.setStyleSheet("""
            QPushButton { background-color: #52c41a; color: white; border-radius: 4px; padding: 8px 16px; font-size: 14px;}
            QPushButton:hover { background-color: #73d13d; }
        """)
        ctrl_layout.addWidget(self.btn_browser)

        ctrl_layout.addStretch()

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setFixedWidth(150)
        self.progress.setRange(0, 0)
        ctrl_layout.addWidget(self.progress)

        layout.addWidget(ctrl_panel)

        # === Web 视图 ===
        if WEB_ENGINE_AVAILABLE:
            self.web_view = QWebEngineView()
            self.web_view.setStyleSheet("background-color: #121212;")
            self.web_view.setHtml(self._get_placeholder_html())
            layout.addWidget(self.web_view)
        else:
            err_label = QLabel("⚠️ 缺少 PyQtWebEngine 库，请使用“浏览器打开”功能。")
            err_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(err_label)

        self.info_frame = QFrame()
        self.info_frame.setStyleSheet("background-color: #f0f2f5; border-top: 1px solid #dcdcdc;")
        self.info_frame.setFixedHeight(40)
        info_layout = QHBoxLayout(self.info_frame)
        info_layout.setContentsMargins(20, 0, 20, 0)

        self.info_label = QLabel("ℹ️ 提示: 悬停节点可查看详情。如果下方空白，请点击“浏览器打开”。")
        self.info_label.setStyleSheet("color: #666; font-size: 13px;")
        info_layout.addWidget(self.info_label)

        layout.addWidget(self.info_frame)

    def set_theme(self, theme_name):
        self.current_theme = theme_name
        if WEB_ENGINE_AVAILABLE:
            self.web_view.setHtml(self._get_placeholder_html())

    def _get_placeholder_html(self):
        t = THEMES.get(self.current_theme, THEMES["商务蓝 (Default)"])
        bg = t.get('bg_main', '#121212')
        fg = t.get('text_sec', '#555')
        return f"""
            <body style="background-color:{bg}; color:{fg}; display:flex; justify-content:center; align-items:center; height:100vh; margin:0; font-family:sans-serif;">
                <div style="text-align:center;">
                    <h1>🕸️ 等待生成网络图谱</h1>
                    <p>当前主题: {self.current_theme}<br>点击“生成图谱”以渲染。</p>
                </div>
            </body>
        """

    def start_analysis(self):
        self.btn_analyze.setEnabled(False)
        self.btn_browser.setEnabled(False)
        self.progress.setVisible(True)
        self.info_label.setText("⏳ 正在构建复杂网络拓扑...")

        idx = self.combo_rarity.currentIndex()
        rarities = None
        if idx == 1:
            rarities = [2, 3]
        elif idx == 2:
            rarities = [3, 4]
        elif idx == 3:
            rarities = [4, 5]

        top_n = int(self.combo_topn.currentText())
        filters = {'rarities': rarities, 'top_n': top_n}
        theme_colors = THEMES.get(self.current_theme, THEMES["商务蓝 (Default)"])

        self.worker = NetworkWorker(config.DB_PATH, filters, theme_colors)
        self.worker.finished_signal.connect(self.on_analysis_finished)
        self.worker.start()

    def on_analysis_finished(self, html_path, metrics, error_msg):
        self.btn_analyze.setEnabled(True)
        self.progress.setVisible(False)

        if error_msg:
            QMessageBox.critical(self, "生成失败", f"错误:\n{error_msg}")
            self.info_label.setText("❌ 生成失败")
            return

        if os.path.exists(html_path):
            self.last_html_path = os.path.abspath(html_path)
            self.btn_browser.setEnabled(True)

            # 检查文件大小，如果太小说明可能还是空的
            fsize = os.path.getsize(self.last_html_path)
            if fsize < 100:
                self.info_label.setText(f"⚠️ 生成的文件过小 ({fsize} bytes)，可能为空")
                return

            if WEB_ENGINE_AVAILABLE:
                # 使用绝对路径 + 正斜杠
                path_str = self.last_html_path.replace('\\', '/')
                local_url = QUrl.fromLocalFile(path_str)
                print(f"🌍 加载 URL: {local_url.toString()}")
                self.web_view.load(local_url)

            node_count = len(metrics.get('pagerank', {}))
            top_node = "None"
            if node_count > 0:
                top_node = max(metrics['pagerank'], key=metrics['pagerank'].get)

            msg = f"✅ 分析完成！全网节点数: {node_count} | 核心节点: {top_node}"
            self.info_label.setText(msg)
        else:
            self.info_label.setText("⚠️ 未找到生成的 HTML 文件")

    def open_in_browser(self):
        if self.last_html_path and os.path.exists(self.last_html_path):
            webbrowser.open(f'file:///{self.last_html_path}')