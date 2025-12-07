import os
import pandas as pd
import plotly.graph_objects as go
import webbrowser
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QLineEdit, QGroupBox, QFrame, QMessageBox, QSplitter, QSizePolicy, QCompleter)
from PyQt5.QtCore import QUrl, QThread, pyqtSignal, Qt

try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings

    WEB_ENGINE_AVAILABLE = True
except ImportError:
    WEB_ENGINE_AVAILABLE = False

from src.core.price_predictor import DataFetcher, SentimentAnalyzer, PricePredictor, NameTranslator
import config


class PredictWorker(QThread):
    result_signal = pyqtSignal(str, float, str, bool, str)

    def __init__(self, item_name, cookie):
        super().__init__()
        self.item_name = item_name
        self.cookie = cookie

    def run(self):
        try:
            fetcher = DataFetcher(self.cookie)
            df_hist, msg = fetcher.fetch_price_history(self.item_name)

            if df_hist is None:
                self.result_signal.emit("", 0, "", False, msg)
                return

            predictor = PricePredictor(df_hist)
            df_pred, err = predictor.predict()

            if df_pred is None:
                self.result_signal.emit("", 0, "", False, err)
                return

            # 如果 err 不为空（比如是 warning），我们也传递出去
            warning_msg = err if err else "Success"

            sa = SentimentAnalyzer()
            s_score, s_text = sa.get_market_sentiment()

            fig = go.Figure()

            # 历史线
            fig.add_trace(go.Scatter(
                x=df_hist['Date'], y=df_hist['Price'],
                mode='lines', name='历史走势 (1 Year)',
                line=dict(color='#1890ff', width=2),
                hovertemplate="<b>日期:</b> %{x|%Y-%m-%d}<br><b>价格:</b> ¥%{y:.2f}<extra></extra>"
            ))

            # 预测线
            fig.add_trace(go.Scatter(
                x=df_pred['Date'], y=df_pred['Price'],
                mode='lines+markers', name='AI 预测 (7 Days)',
                line=dict(color='#52c41a', width=3, dash='dot'),
                marker=dict(size=6, symbol='circle', color='#52c41a'),
                hovertemplate="<b>日期:</b> %{x|%Y-%m-%d}<br><b>预测价:</b> ¥%{y:.2f}<extra></extra>"
            ))

            # 连接线 (连接历史最后一点和预测第一点)
            last_hist = df_hist.iloc[-1]
            first_pred = df_pred.iloc[0]
            fig.add_trace(go.Scatter(
                x=[last_hist['Date'], first_pred['Date']],
                y=[last_hist['Price'], first_pred['Price']],
                mode='lines', showlegend=False,
                line=dict(color='#52c41a', width=3, dash='dot'),
                hoverinfo='skip'
            ))

            fig.update_layout(
                title=dict(
                    text=f"<b>{self.item_name}</b> 价格走势与预测",
                    font=dict(size=20, family="Microsoft YaHei")
                ),
                template="plotly_white",
                hovermode="x unified",
                xaxis=dict(title="日期", showspikes=True, spikemode="across", spikesnap="cursor", showline=True,
                           showgrid=True, gridcolor='#f0f0f0'),
                yaxis=dict(title="价格 (CNY)", showspikes=True, spikemode="across", tickprefix="¥", showline=True,
                           showgrid=True, gridcolor='#f0f0f0'),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=50, r=30, t=80, b=50),
                plot_bgcolor='white',
                autosize=True
            )

            output_dir = os.path.join(os.getcwd(), "CS2_Reports")
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            html_path = os.path.join(output_dir, "prediction.html")

            # 使用本地 Plotly JS (如果有的话，没有会自动回退CDN)
            html_content = fig.to_html(full_html=True, include_plotlyjs='cdn')

            # 简单优化：隐藏滚动条
            html_content = html_content.replace('<body>', '<body style="margin:0; padding:0; overflow:hidden;">')

            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)

            self.result_signal.emit(html_path, s_score, s_text, True, warning_msg)

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.result_signal.emit("", 0, "", False, str(e))


class PredictionWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.last_html_path = ""
        self.translator = NameTranslator()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # === 顶部搜索栏 ===
        search_frame = QFrame()
        search_frame.setObjectName("ContentCard")
        search_frame.setStyleSheet(
            "QFrame#ContentCard { background-color: white; border: 1px solid #dcdcdc; border-radius: 8px; }")
        search_layout = QHBoxLayout(search_frame)
        search_layout.setContentsMargins(15, 15, 15, 15)

        self.input_name = QLineEdit()
        self.input_name.setPlaceholderText("饰品名称 (如: 墨岩 / Slate)")
        self.input_name.setMinimumWidth(250)
        self.input_name.returnPressed.connect(self.start_predict)

        # 配置自动补全
        all_items = self.translator.get_all_names()
        completer = QCompleter(all_items, self.input_name)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        completer.setMaxVisibleItems(15)

        popup = completer.popup()
        popup.setStyleSheet("""
            QAbstractItemView {
                background-color: #ffffff;
                color: #2c3e50;
                selection-background-color: #1890ff;
                selection-color: #ffffff;
                border: 1px solid #dcdcdc;
                font-size: 14px;
                min-height: 25px;
            }
        """)
        self.input_name.setCompleter(completer)

        self.input_cookie = QLineEdit()
        self.input_cookie.setPlaceholderText("Steam Cookie (steamLoginSecure)")
        self.input_cookie.setEchoMode(QLineEdit.Password)
        self.input_cookie.setMinimumWidth(200)

        self.btn_run = QPushButton("🔮 智能预测")
        self.btn_run.clicked.connect(self.start_predict)
        self.btn_run.setStyleSheet(
            "QPushButton { background-color: #722ed1; color: white; font-weight: bold; border-radius: 6px; padding: 10px 20px; }")

        self.btn_browser = QPushButton("🌐 浏览器打开")
        self.btn_browser.clicked.connect(self.open_in_browser)
        self.btn_browser.setEnabled(False)
        self.btn_browser.setStyleSheet(
            "QPushButton { background-color: #2ecc71; color: white; font-weight: bold; border-radius: 6px; padding: 10px 20px; }")

        search_layout.addWidget(QLabel("🔍 饰品:"))
        search_layout.addWidget(self.input_name)
        search_layout.addWidget(QLabel("🍪 Cookie:"))
        search_layout.addWidget(self.input_cookie)
        search_layout.addSpacing(10)
        search_layout.addWidget(self.btn_run)
        search_layout.addWidget(self.btn_browser)

        layout.addWidget(search_frame)

        # === 内容分割 ===
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        # 左侧面板
        sentiment_container = QWidget()
        sentiment_container.setFixedWidth(300)
        s_layout = QVBoxLayout(sentiment_container)
        s_layout.setContentsMargins(0, 0, 10, 0)

        sentiment_box = QGroupBox("📊 市场情绪 (Sentiment)")
        sentiment_box.setStyleSheet(
            "QGroupBox { background-color: white; border: 1px solid #dcdcdc; border-radius: 8px; font-weight: bold; font-size: 16px; padding-top: 25px; }")
        sb_layout = QVBoxLayout(sentiment_box)
        sb_layout.setSpacing(15)

        self.lbl_score = QLabel("Ready")
        self.lbl_score.setAlignment(Qt.AlignCenter)
        self.lbl_score.setStyleSheet("font-size: 48px; font-weight: bold; color: #d9d9d9;")

        self.lbl_status = QLabel("等待分析...")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        self.lbl_status.setStyleSheet("font-size: 20px; color: #666; font-weight: bold;")

        desc = QLabel(
            "基于全球新闻与社区讨论的情感分析模型。\n\n• > 0.2: 贪婪 (看涨)\n• < -0.2: 恐慌 (看跌)\n• 其他: 中性 (震荡)")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #888; padding: 15px; font-size: 14px; background: #f9f9f9; border-radius: 6px;")

        sb_layout.addStretch()
        sb_layout.addWidget(self.lbl_score)
        sb_layout.addWidget(self.lbl_status)
        sb_layout.addStretch()
        sb_layout.addWidget(desc)
        s_layout.addWidget(sentiment_box)
        splitter.addWidget(sentiment_container)

        # 右侧图表
        chart_container = QWidget()
        chart_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        c_layout = QVBoxLayout(chart_container)
        c_layout.setContentsMargins(0, 0, 0, 0)

        chart_frame = QFrame()
        chart_frame.setStyleSheet("background-color: white; border: 1px solid #dcdcdc; border-radius: 8px;")
        chart_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        cf_layout = QVBoxLayout(chart_frame)
        cf_layout.setContentsMargins(1, 1, 1, 1)

        if WEB_ENGINE_AVAILABLE:
            self.web_view = QWebEngineView()
            self.web_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.web_view.setStyleSheet("background: transparent;")
            self.web_view.settings().setAttribute(QWebEngineSettings.WebGLEnabled, True)
            self.web_view.settings().setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
            self.web_view.setHtml(
                """<div style='display:flex; justify-content:center; align-items:center; height:100vh; color:#aaa; font-family:Microsoft YaHei; background:white;'><div style='text-align:center'><h2 style='margin-bottom:10px; font-size:24px;'>📈 等待数据</h2><p style='font-size:16px;'>请输入饰品名称并点击"智能预测"</p></div></div>""")
            cf_layout.addWidget(self.web_view)
        else:
            cf_layout.addWidget(QLabel("⚠️ 缺少 PyQtWebEngine"))

        c_layout.addWidget(chart_frame)
        splitter.addWidget(chart_container)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        layout.addWidget(splitter)

    def start_predict(self):
        name = self.input_name.text().strip()
        cookie = self.input_cookie.text().strip()
        if not name:
            return QMessageBox.warning(self, "提示", "请输入饰品名称")

        # 允许不输入 Cookie 进行尝试（某些公开 API 可能偶尔可用）
        if not cookie:
            reply = QMessageBox.question(self, "Cookie 缺失",
                                         "未提供 Steam Cookie，可能无法获取精确历史数据。\n是否尝试匿名获取？",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.No:
                return

        self.btn_run.setEnabled(False)
        self.btn_browser.setEnabled(False)
        self.btn_run.setText("⏳ 分析中...")
        self.lbl_status.setText("读取 Steam 数据...")
        self.lbl_score.setText("...")

        self.worker = PredictWorker(name, cookie)
        self.worker.result_signal.connect(self.on_finished)
        self.worker.start()

    def on_finished(self, html_path, score, text, success, msg):
        self.btn_run.setEnabled(True)
        self.btn_run.setText("🔮 智能预测")

        if not success:
            QMessageBox.critical(self, "分析失败", f"错误详情:\n{msg}")
            self.lbl_status.setText("失败")
            return

        # 检查是否降级为线性模式
        if "Linear Mode" in msg:
            QMessageBox.warning(self, "AI 模块未启用",
                                "未检测到 TensorFlow 库或训练出错。\n已自动降级为线性趋势预测（含随机波动）。\n\n如需启用深度学习，请安装: pip install tensorflow scikit-learn")

        self.last_html_path = os.path.abspath(html_path)
        self.btn_browser.setEnabled(True)
        if WEB_ENGINE_AVAILABLE:
            self.web_view.setUrl(QUrl("about:blank"))
            self.web_view.load(QUrl.fromLocalFile(self.last_html_path.replace('\\', '/')))

        self.lbl_score.setText(f"{score:.2f}")
        self.lbl_status.setText(text)
        color = "#52c41a" if score > 0.2 else "#f5222d" if score < -0.2 else "#faad14"
        self.lbl_score.setStyleSheet(f"font-size: 48px; font-weight: bold; color: {color};")

    def open_in_browser(self):
        if self.last_html_path and os.path.exists(self.last_html_path):
            webbrowser.open(f'file:///{self.last_html_path}')