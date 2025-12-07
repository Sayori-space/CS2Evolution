import os
import json
import numpy as np
import pandas as pd

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
                             QLabel, QPushButton, QStackedWidget, QSizePolicy, QFrame, QTextBrowser)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from src.utils.path_manager import PathManager

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import seaborn as sns

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.size'] = 14
plt.rcParams['axes.titlesize'] = 18
plt.rcParams['axes.labelsize'] = 16
plt.rcParams['xtick.labelsize'] = 14
plt.rcParams['ytick.labelsize'] = 14


class ChartViewWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.report_dir = PathManager.get_report_dir()
        self.current_data = None
        self.current_pixmap = None
        self.init_descriptions()
        self.init_ui()

    def init_descriptions(self):
        self.chart_descriptions = {
            "evolution": "<b>📈 进化轨迹</b><br>展示每一代算法找到的最佳ROI（红线）和平均ROI（蓝线）。",
            "frontier": "<b>🛡️ 风险-收益前沿</b><br>左上角的点代表低风险高收益的黄金配方。",
            "ridgeline": "<b>⛰️ 收益分布</b><br>波峰越靠右，赚钱概率越大。",
            "heatmap": "<b>🔥 磨损热力图</b><br>颜色越亮代表该磨损区间的配方越赚钱。",
            "pie_Micro": self._get_pie_desc("Micro"),
            "pie_Low": self._get_pie_desc("Low"),
            "pie_Mid": self._get_pie_desc("Mid"),
            "pie_High": self._get_pie_desc("High"),
            "static_sankey": "<b>🌊 资金流向</b><br>左侧为投入成本，右侧为产出价值期望。",
            "static_sunburst": "<b>☀️ 产出旭日图</b><br>内圈为系列，外圈为具体皮肤。",
            "static_treemap": "<b>🔲 价值树状图</b><br>绿色块越大，代表该产出贡献的利润越多。",
            "static_radar": "<b>🕸️ 能力雷达图</b><br>多维度对比配方的综合能力。",
            "static_funnel": "<b>🌪️ 筛选漏斗</b><br>展示从海量配方到最终优选的过程。",
            # ✅ 新增文案
            "static_compare": "<b>🧪 算法效能对比</b><br>红色实线(Guided) vs 灰色虚线(Baseline)。<br>红色区域面积越大，说明网络图论指导对算法的提升越明显。"
        }

    def _get_pie_desc(self, tier):
        return f"<b>🍰 最佳配方产出 ({tier})</b><br>该价位段第一名配方的详细产出概率分布。"

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        top_bar = QHBoxLayout()
        lbl_history = QLabel("📅 历史记录:")
        lbl_history.setStyleSheet("font-weight: bold;")
        top_bar.addWidget(lbl_history)

        self.combo_session = QComboBox()
        self.combo_session.setMinimumWidth(250);
        self.combo_session.setMinimumHeight(40)
        self.combo_session.currentIndexChanged.connect(self.on_session_changed)
        top_bar.addWidget(self.combo_session)

        lbl_chart = QLabel("📊 图表类型:")
        lbl_chart.setStyleSheet("font-weight: bold; margin-left: 20px;")
        top_bar.addWidget(lbl_chart)

        self.combo_chart_type = QComboBox()
        self.combo_chart_type.setMinimumWidth(280);
        self.combo_chart_type.setMinimumHeight(40)

        self.chart_types = {
            "📈 进化轨迹 (交互)": "evolution",
            "🛡️ 风险收益前沿 (交互)": "frontier",
            "⛰️ 收益分布密度 (交互)": "ridgeline",
            "🔥 磨损热力图 (交互)": "heatmap",
            "🧪 算法效能对比 (静态)": "static_compare",  # ✅ 新增选项
            "🌊 资金流向桑基图 (静态)": "static_sankey",
            "☀️ 产出旭日图 (静态)": "static_sunburst",
            "🔲 价值树状图 (静态)": "static_treemap",
            "🕸️ 能力雷达图 (静态)": "static_radar",
            "🌪️ 优选漏斗图 (静态)": "static_funnel"
        }
        self.combo_chart_type.addItems(self.chart_types.keys())
        self.combo_chart_type.currentIndexChanged.connect(self.render_chart)
        top_bar.addWidget(self.combo_chart_type)

        btn_refresh = QPushButton("🔄 刷新")
        btn_refresh.setMinimumHeight(40)
        btn_refresh.clicked.connect(self.refresh_sessions)
        top_bar.addWidget(btn_refresh)
        top_bar.addStretch()
        layout.addLayout(top_bar)

        content_frame = QFrame()
        content_frame.setFrameShape(QFrame.StyledPanel)
        content_frame.setStyleSheet("background-color: white; border-radius: 12px; border: 1px solid #e0e0e0;")
        content_layout = QVBoxLayout(content_frame)

        self.stack = QStackedWidget()

        self.plot_container = QWidget()
        self.plot_layout = QVBoxLayout(self.plot_container)
        self.plot_layout.setContentsMargins(0, 0, 0, 0)
        self.canvas = FigureCanvas(Figure(figsize=(8, 6), dpi=100))
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.toolbar = NavigationToolbar(self.canvas, self.plot_container)
        self.plot_layout.addWidget(self.toolbar)
        self.plot_layout.addWidget(self.canvas)

        self.image_label = QLabel("请选择图表")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background-color: #f9f9f9; border-radius: 5px;")
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.stack.addWidget(self.plot_container)
        self.stack.addWidget(self.image_label)

        content_layout.addWidget(self.stack, 1)

        self.description_area = QTextBrowser()
        self.description_area.setMaximumHeight(100)
        self.description_area.setStyleSheet("""
            QTextBrowser { background-color: #fffcf5; border-top: 1px solid #e0e0e0; padding: 15px; color: #555; font-size: 16px; }
        """)
        content_layout.addWidget(self.description_area)
        layout.addWidget(content_frame)
        self.refresh_sessions()

    def resizeEvent(self, event):
        if self.stack.currentIndex() == 1 and self.current_pixmap: self._rescale_image()
        super().resizeEvent(event)

    def _rescale_image(self):
        if not self.current_pixmap: return
        size = self.image_label.size()
        scaled_pixmap = self.current_pixmap.scaled(size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled_pixmap)

    def refresh_sessions(self):
        self.combo_session.blockSignals(True)
        self.combo_session.clear()
        if not self.report_dir.exists():
            self.combo_session.addItem("无记录")
        else:
            sessions = [d.name for d in self.report_dir.iterdir() if d.is_dir()]
            sessions.sort(reverse=True)
            self.combo_session.addItems(sessions if sessions else ["无记录"])
        self.combo_session.blockSignals(False)
        self.on_session_changed()

    def on_session_changed(self):
        session = self.combo_session.currentText()
        if session == "无记录": return
        json_path = self.report_dir / session / "session_data.json"
        if json_path.exists():
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    self.current_data = json.load(f)
            except:
                self.current_data = None
        else:
            self.current_data = None
        self.render_chart()

    def render_chart(self):
        session = self.combo_session.currentText()
        if session == "无记录": return
        chart_name = self.combo_chart_type.currentText()
        chart_code = self.chart_types.get(chart_name)

        desc = self.chart_descriptions.get(chart_code, "暂无说明")
        if chart_code.startswith("pie_"):
            tier = chart_code.split("_")[1]
            desc = self._get_pie_desc(tier)
        self.description_area.setHtml(desc)

        if not chart_code.startswith("static"):
            self.stack.setCurrentIndex(0)
            if not self.current_data: self._show_msg("未找到源数据"); return
            self.canvas.figure.clear()
            ax = self.canvas.figure.add_subplot(111)
            try:
                if chart_code == "evolution":
                    self._draw_evolution(ax)
                elif chart_code == "frontier":
                    self._draw_frontier(ax)
                elif chart_code == "ridgeline":
                    self._draw_ridgeline(ax)
                elif chart_code == "heatmap":
                    self._draw_heatmap(ax)
                self.canvas.draw()
            except Exception as e:
                self._show_msg(f"绘图错误: {e}")
        else:
            self.stack.setCurrentIndex(1)
            target_file = None
            session_path = self.report_dir / session
            keyword_map = {
                "static_sankey": "sankey", "static_sunburst": "sunburst", "static_treemap": "treemap",
                "static_radar": "radar", "static_funnel": "funnel",
                "static_compare": "convergence_comparison"  # ✅ 关键字匹配
            }
            keyword = keyword_map.get(chart_code, "")
            if session_path.exists():
                for f in session_path.iterdir():
                    if f.suffix == '.png' and keyword in f.name: target_file = str(f); break
            if target_file:
                self.current_pixmap = QPixmap(target_file)
                self._rescale_image()
            else:
                self.current_pixmap = None
                self.image_label.setText(f"未找到该图表图片 ({keyword})\n可能挖掘时未勾选'生成算法效能对比报告'")

    def _show_msg(self, msg):
        self.canvas.figure.clear()
        ax = self.canvas.figure.add_subplot(111)
        ax.text(0.5, 0.5, msg, ha='center', va='center', color='red', fontsize=16)
        ax.axis('off');
        self.canvas.draw()

    def _draw_evolution(self, ax):
        data = self.current_data.get('evolution', [])
        if not data: return self._show_msg("无进化数据")
        df = pd.DataFrame(data)
        ax.plot(df['gen'], df['max_roi'] * 100, label='Max ROI', color='#e74c3c', linewidth=2)
        ax.plot(df['gen'], df['avg_roi'] * 100, label='Avg ROI', linestyle='--', color='#3498db', linewidth=2)
        ax.fill_between(df['gen'], df['avg_roi'] * 100, df['max_roi'] * 100, alpha=0.1, color='#e74c3c')
        ax.set_title("算法进化轨迹", fontweight='bold');
        ax.set_ylabel("ROI (%)");
        ax.set_xlabel("世代");
        ax.legend();
        ax.grid(True, linestyle='--', alpha=0.5)

    def _draw_frontier(self, ax):
        data = self.current_data.get('scatter', [])
        if not data: return self._show_msg("无散点数据")
        df = pd.DataFrame(data)
        df = df[(df['roi'] > -0.5) & (df['roi'] < 5.0)]
        sc = ax.scatter(df['std_dev'], df['roi'] * 100, c=df['cost'], cmap='viridis', alpha=0.7, s=60)
        ax.set_title("风险-收益前沿", fontweight='bold');
        ax.set_xlabel("风险 (StdDev)");
        ax.set_ylabel("ROI (%)");
        cbar = self.canvas.figure.colorbar(sc, ax=ax);
        cbar.set_label('成本 (CNY)');
        ax.grid(True, linestyle='--', alpha=0.5)

    def _draw_ridgeline(self, ax):
        rois = self.current_data.get('roi_list', [])
        if not rois: return self._show_msg("无分布数据")
        clean = [r * 100 for r in rois if -1.0 < r < 3.0]
        sns.histplot(clean, kde=True, ax=ax, color="purple", bins=30)
        ax.set_title("ROI 分布密度", fontweight='bold');
        ax.set_xlabel("ROI (%)");
        ax.axvline(0, color='red', linestyle='--')

    def _draw_heatmap(self, ax):
        data = self.current_data.get('scatter', [])
        if not data: return
        df = pd.DataFrame(data)
        df = df[(df['roi'] > -0.5) & (df['roi'] < 1.5)]
        h = ax.hist2d(df['input_pos'], df['roi'], bins=[20, 20], cmap='inferno')
        ax.set_title("磨损位置 vs ROI", fontweight='bold');
        ax.set_xlabel("平均磨损位置 (0-1)");
        ax.set_ylabel("ROI");
        self.canvas.figure.colorbar(h[3], ax=ax)