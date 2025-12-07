from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
                             QComboBox, QDoubleSpinBox, QPushButton, QScrollArea,
                             QLabel, QFrame, QMessageBox, QTableWidget, QTableWidgetItem,
                             QHeaderView, QAbstractItemView)
from PyQt5.QtGui import QColor, QBrush, QFont
from PyQt5.QtCore import Qt
from src.core.simulator import CS2TradeUpSimulator, TradeInputItem
import config


class WorkbenchWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.sim = CS2TradeUpSimulator(config.DB_PATH)
        self.input_rows = []
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # ✅ 白色卡片容器
        card = QWidget()
        card.setObjectName("ContentCard")
        main_layout.addWidget(card)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(30, 30, 30, 30)

        # 标题栏
        header = QHBoxLayout()
        title = QLabel("🛠️ 手动配方模拟器")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #2c3e50;")
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        # 说明文字
        desc = QLabel("手动指定 10 个输入皮肤及其磨损，实时计算产出概率和收益。")
        desc.setStyleSheet("color: #7f8c8d; margin-bottom: 15px;")
        layout.addWidget(desc)

        # 滚动区域 (包裹输入行)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background-color: transparent;")

        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        self.form_layout = QVBoxLayout(container)
        self.form_layout.setSpacing(10)

        self.collections = sorted(self.sim.raw_db.keys())
        for i in range(10):
            row_widget = self.create_input_row(i + 1)
            self.form_layout.addWidget(row_widget)
            self.input_rows.append(row_widget)

        scroll.setWidget(container)
        layout.addWidget(scroll)

        # 分割线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)

        # 结果显示区
        results_container = QWidget()
        results_layout = QVBoxLayout(results_container)
        results_layout.setContentsMargins(0, 0, 0, 0)

        # 1. 摘要信息
        self.summary_label = QLabel("准备就绪...")
        self.summary_label.setAlignment(Qt.AlignCenter)
        self.summary_label.setStyleSheet("""
            background-color: #fdfefe; 
            border: 2px dashed #bdc3c7; 
            border-radius: 8px;
            padding: 15px;
            font-size: 16px;
            color: #34495e;
        """)
        results_layout.addWidget(self.summary_label)

        # 2. 详细列表
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(5)
        self.result_table.setHorizontalHeaderLabels(["饰品名称", "磨损", "概率", "预估价", "收益"])
        self.result_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.result_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.result_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.result_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.result_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.result_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.result_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.result_table.setAlternatingRowColors(True)
        self.result_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #ecf0f1;
                border-radius: 6px;
                background-color: white;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                padding: 4px;
                border: none;
                font-weight: bold;
                color: #7f8c8d;
            }
        """)
        self.result_table.setMinimumHeight(200)
        results_layout.addWidget(self.result_table)

        layout.addWidget(results_container)

        # 底部按钮
        btn_calc = QPushButton("🧪 立即模拟")
        btn_calc.setCursor(Qt.PointingHandCursor)
        btn_calc.setMinimumHeight(50)
        btn_calc.setStyleSheet("""
            QPushButton {
                background-color: #27ae60; 
                font-size: 16px; 
                border-radius: 8px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #2ecc71; }
        """)
        btn_calc.clicked.connect(self.run_simulation)
        layout.addWidget(btn_calc)

    def create_input_row(self, index):
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #ecf0f1;
                border-radius: 6px;
            }
        """)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(10, 5, 10, 5)

        lbl_idx = QLabel(f"#{index}")
        lbl_idx.setStyleSheet("font-weight: bold; color: #95a5a6; border: none;")
        layout.addWidget(lbl_idx)

        combo_col = QComboBox()
        combo_col.addItems(self.collections)
        combo_col.setMinimumWidth(180)

        combo_skin = QComboBox()
        combo_skin.setMinimumWidth(180)

        def update_skins():
            col = combo_col.currentText()
            skins_data = []
            if col in self.sim.raw_db:
                for tier in self.sim.raw_db[col].values():
                    for item in tier:
                        # ✅ 获取中文名，如果不存在则使用英文名
                        cn_name = item.get('name_cn', item['name'])
                        en_name = item['name']
                        # 存储 (显示名称, 内部英文名)
                        skins_data.append((cn_name, en_name))

            # 按显示名称排序方便查找
            skins_data.sort(key=lambda x: x[0])

            combo_skin.clear()
            for display, internal in skins_data:
                # ✅ 核心修改：addItem(text, userData)，显示中文，存储英文供逻辑使用
                combo_skin.addItem(display, internal)

        combo_col.currentIndexChanged.connect(update_skins)
        update_skins()

        spin_float = QDoubleSpinBox()
        spin_float.setRange(0.0, 1.0)
        spin_float.setSingleStep(0.001)
        spin_float.setDecimals(5)
        spin_float.setValue(0.01)
        spin_float.setMinimumWidth(100)

        layout.addWidget(combo_col)
        layout.addWidget(combo_skin)
        layout.addWidget(QLabel("磨损:"))
        layout.addWidget(spin_float)

        frame.combo_col = combo_col
        frame.combo_skin = combo_skin
        frame.spin_float = spin_float

        return frame

    def run_simulation(self):
        inputs = []
        try:
            detected_rarity = None

            for row in self.input_rows:
                col = row.combo_col.currentText()
                # ✅ 从 userData 获取英文原名，用于数据库查询
                name = row.combo_skin.currentData()
                if not name:
                    continue  # 跳过未选择的行

                float_val = row.spin_float.value()

                # ✅ 修复：必须传入 collection 参数
                price_res = self.sim.price_engine.get_base_price(name, float_val, collection=col)

                if price_res == float('inf'):
                    # 尝试查找元数据以确认是否存在
                    # 如果只是价格缺失，我们暂时设为 0 继续模拟，但给予警告
                    base_price = 0.0
                    condition = "Unknown"
                else:
                    base_price, condition = price_res

                # 自动检测稀有度（取第一个有效物品的稀有度）
                if detected_rarity is None:
                    # 通过引擎元数据查找稀有度
                    meta = self.sim.price_engine.metadata_map.get((col, name))
                    if meta:
                        detected_rarity = meta['rarity']

                # 计算 CN 估价 (Workbench 不像 Optimizer 那样预处理过汇率，所以这里要乘)
                est_price = base_price * config.EXCHANGE_RATE

                # 获取元数据中的最大最小磨损
                min_float = 0.0
                max_float = 1.0
                meta = self.sim.price_engine.metadata_map.get((col, name))
                if meta:
                    min_float = meta['min']
                    max_float = meta['max']

                inputs.append(
                    TradeInputItem(col, name, min_float, max_float, float_val, est_price, base_price, condition))

            if not inputs:
                QMessageBox.warning(self, "提示", "请至少添加一个有效的输入饰品。")
                return

            if detected_rarity is None:
                QMessageBox.warning(self, "错误", "无法识别输入饰品的稀有度。")
                return

            # ✅ 目标稀有度通常是输入稀有度 + 1
            target_rarity = detected_rarity

            res = self.sim.simulate(inputs, target_rarity, config.BUFF_RATIO)

            # 使用 HTML 格式美化结果文本
            profit_color = "green" if res.roi > 0 else "red"

            rarity_map = {2: "工业级", 3: "军规级", 4: "受限级", 5: "保密级", 6: "隐秘级"}
            in_r_str = rarity_map.get(detected_rarity, str(detected_rarity))
            out_r_str = rarity_map.get(detected_rarity + 1, str(detected_rarity + 1))

            summary_html = (
                f"📊 方案: <b>{in_r_str} ➔ {out_r_str}</b><br>"
                f"💰 总成本: <b>¥{res.total_cost:.2f}</b> &nbsp;&nbsp;|&nbsp;&nbsp; "
                f"📈 期望收益: <b>¥{res.expected_value:.2f}</b> "
                f"(<span style='color:{profit_color}'>ROI: {res.roi * 100:.2f}%</span>)<br>"
                f"🛡️ 保本概率: <b>{res.break_even_prob * 100:.1f}%</b> &nbsp;&nbsp;|&nbsp;&nbsp; "
                f"📊 平均磨损: {res.avg_input_percentage:.4f}"
            )
            self.summary_label.setText(summary_html)

            # 填充表格
            self.result_table.setRowCount(0)
            sorted_outcomes = sorted(res.outcomes, key=lambda x: x.profit, reverse=True)

            self.result_table.setRowCount(len(sorted_outcomes))
            for row_idx, out in enumerate(sorted_outcomes):
                # 1. 名称 (显示中文名)
                name_item = QTableWidgetItem(f"{out.name_cn}\n{out.collection}")
                name_item.setToolTip(out.name)

                # 2. 磨损
                wear_text = f"{out.float_value:.5f}\n({out.condition})"
                wear_item = QTableWidgetItem(wear_text)
                wear_item.setTextAlignment(Qt.AlignCenter)

                # 3. 概率
                prob_item = QTableWidgetItem(f"{out.probability * 100:.1f}%")
                prob_item.setTextAlignment(Qt.AlignCenter)
                if out.probability < 0.1:
                    prob_item.setForeground(QBrush(QColor("#95a5a6")))
                else:
                    prob_item.setForeground(QBrush(QColor("#2c3e50")))
                    font = QFont()
                    font.setBold(True)
                    prob_item.setFont(font)

                # 4. 价格
                price_item = QTableWidgetItem(f"¥{out.price:.2f}")
                price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

                # 5. 收益
                profit_item = QTableWidgetItem(f"{out.profit:+.2f}")
                profit_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if out.profit > 0:
                    profit_item.setForeground(QBrush(QColor("#27ae60")))
                    profit_item.setBackground(QBrush(QColor("#e8f8f5")))
                else:
                    profit_item.setForeground(QBrush(QColor("#c0392b")))
                    profit_item.setBackground(QBrush(QColor("#fdedec")))

                self.result_table.setItem(row_idx, 0, name_item)
                self.result_table.setItem(row_idx, 1, wear_item)
                self.result_table.setItem(row_idx, 2, prob_item)
                self.result_table.setItem(row_idx, 3, price_item)
                self.result_table.setItem(row_idx, 4, profit_item)

            self.result_table.resizeRowsToContents()

        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "错误", f"模拟失败: {str(e)}")