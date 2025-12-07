from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QProgressBar,
                             QTextEdit, QLabel, QComboBox, QGroupBox, QFormLayout,
                             QSpinBox, QDoubleSpinBox, QCheckBox, QHBoxLayout,
                             QTableWidget, QTableWidgetItem, QHeaderView, QSplitter)
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QColor, QBrush
from src.core.simulator import CS2TradeUpSimulator
from src.core.optimizer import SmartOptimizer
from src.utils import visualization
import config
import time


class MiningWorker(QThread):
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(object)

    def __init__(self, simulator, rarity, params):
        super().__init__()
        self.sim = simulator
        self.rarity = rarity
        self.params = params
        self.do_compare = params.get('do_compare', False)  # 获取对比标志

    def run(self):
        # ==========================================
        # 阶段 1: 核心挖掘 (Guided / 实验组)
        # ==========================================
        self.log_signal.emit(f"🚀 [阶段 1] 启动网络指导挖掘 (Network Guided)...")

        # 初始化带网络指导的优化器
        opt_guided = SmartOptimizer(self.sim, use_network_guidance=True)

        # 检查池子是否为空
        pools = opt_guided._load_candidates_for_rarity(self.rarity)
        if not pools['all']:
            self.log_signal.emit("❌ 候选池为空，请检查数据库或筛选条件！")
            self.finished_signal.emit({})
            return

        # 定义进度回调
        def progress_callback_guided(percent, msg):
            # 如果要跑两轮，第一轮进度条只走 0-50%
            factor = 0.5 if self.do_compare else 1.0
            self.progress_signal.emit(int(percent * factor))
            if msg: self.log_signal.emit(f"[Guided] {msg}")

        try:
            # 运行 Guided 算法
            session_folder, tier_top_recipes, history_guided = opt_guided.run(
                target_rarity_list=[self.rarity],
                params=self.params,
                progress_callback=progress_callback_guided
            )

            # ==========================================
            # 阶段 2: 对照组挖掘 (Baseline / 控制组) - 可选
            # ==========================================
            if self.do_compare:
                self.log_signal.emit(f"🔬 [阶段 2] 启动基准对照挖掘 (Random Baseline)...")

                # 初始化无指导的优化器 (use_network_guidance=False)
                opt_baseline = SmartOptimizer(self.sim, use_network_guidance=False)

                def progress_callback_baseline(percent, msg):
                    # 第二轮进度条走 50-90%
                    base = 50
                    factor = 0.4
                    self.progress_signal.emit(base + int(percent * factor))
                    if msg and percent % 20 == 0:  # 减少日志刷屏
                        self.log_signal.emit(f"[Baseline] {msg}")

                _, _, history_baseline = opt_baseline.run(
                    target_rarity_list=[self.rarity],
                    params=self.params,
                    progress_callback=progress_callback_baseline
                )

                # ==========================================
                # 阶段 3: 生成对比图表
                # ==========================================
                self.log_signal.emit("📊 正在绘制算法效能对比图...")
                self.progress_signal.emit(95)

                print(f"DEBUG: do_compare = {self.do_compare}")
                print(f"DEBUG: Guided History Length = {len(history_guided) if history_guided else 0}")
                print(
                    f"DEBUG: Baseline History Length = {len(history_baseline) if 'history_baseline' in locals() and history_baseline else 0}")
                try:
                    visualization.plot_convergence_comparison(
                        history_baseline,
                        history_guided,
                        session_folder
                    )
                    self.log_signal.emit(f"✅ 对比图已生成: convergence_comparison.png")
                except Exception as e:
                    self.log_signal.emit(f"⚠️ 对比图生成失败: {e}")

            self.progress_signal.emit(100)
            self.log_signal.emit(f"✅ 全部任务完成！报告路径: {session_folder}")
            self.finished_signal.emit(tier_top_recipes)

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.log_signal.emit(f"❌ 严重错误: {str(e)}")
            self.finished_signal.emit({})


class OptimizerWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.sim = CS2TradeUpSimulator(config.DB_PATH)
        self.current_results = {}
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)

        self.card = QWidget()
        self.card.setObjectName("ContentCard")
        main_layout.addWidget(self.card)

        layout = QVBoxLayout(self.card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = QLabel("🚀 智能配方进化引擎")
        title.setObjectName("HomeTitle")
        layout.addWidget(title)

        # 参数区域
        param_group = QGroupBox("⚙️ 核心参数配置")
        param_inner = QHBoxLayout(param_group)

        form_left = QFormLayout()
        self.combo_rarity = QComboBox()
        self.combo_rarity.addItems(["军规级 (3)", "受限级 (4)", "保密级 (5)"])
        form_left.addRow("目标品质:", self.combo_rarity)

        self.spin_pop = QSpinBox()
        self.spin_pop.setRange(50, 2000)
        self.spin_pop.setValue(config.POPULATION_SIZE)
        self.spin_pop.setSingleStep(50)
        form_left.addRow("种群大小:", self.spin_pop)

        self.spin_premium = QDoubleSpinBox()
        self.spin_premium.setRange(0.0, 3.0)
        self.spin_premium.setSingleStep(0.1)
        self.spin_premium.setValue(1.0)
        form_left.addRow("磨损溢价系数:", self.spin_premium)

        param_inner.addLayout(form_left)

        form_right = QFormLayout()
        self.spin_gen = QSpinBox()
        self.spin_gen.setRange(10, 500)
        self.spin_gen.setValue(config.GENERATIONS)
        form_right.addRow("进化代数:", self.spin_gen)

        self.spin_mutation = QDoubleSpinBox()
        self.spin_mutation.setRange(0.0, 1.0)
        self.spin_mutation.setSingleStep(0.05)
        self.spin_mutation.setValue(config.MUTATION_RATE)
        form_right.addRow("变异概率:", self.spin_mutation)

        param_inner.addLayout(form_right)
        layout.addWidget(param_group)

        # 选项栏
        opts_layout = QHBoxLayout()
        self.check_save_png = QCheckBox("保存基础图表 (PNG)")
        self.check_save_png.setChecked(True)

        # ✅ 关键：对比选项
        self.check_compare = QCheckBox("生成算法效能对比报告 (耗时 x2)")
        self.check_compare.setToolTip("勾选后将运行两轮算法（有/无网络指导），并生成对比曲线图。")
        self.check_compare.setStyleSheet("QCheckBox { color: #e74c3c; font-weight: bold; }")

        opts_layout.addWidget(self.check_save_png)
        opts_layout.addWidget(self.check_compare)
        opts_layout.addStretch()
        layout.addLayout(opts_layout)

        # 按钮与进度
        self.btn_start = QPushButton("开始挖掘任务")
        self.btn_start.setCursor(Qt.PointingHandCursor)
        self.btn_start.clicked.connect(self.start_mining)
        layout.addWidget(self.btn_start)

        self.progress = QProgressBar()
        layout.addWidget(self.progress)

        # 结果展示区域 (默认隐藏)
        self.result_container = QGroupBox("🏆 最佳配方详情")
        self.result_container.setVisible(False)
        result_layout = QVBoxLayout(self.result_container)

        select_layout = QHBoxLayout()
        select_layout.addWidget(QLabel("选择查看配方:"))
        self.combo_result_select = QComboBox()
        self.combo_result_select.currentIndexChanged.connect(self.update_recipe_view)
        select_layout.addWidget(self.combo_result_select, 1)
        result_layout.addLayout(select_layout)

        self.stats_label = QLabel()
        self.stats_label.setStyleSheet(
            "padding: 10px; border-radius: 5px; font-weight: bold; background-color: #f8f9fa;")
        result_layout.addWidget(self.stats_label)

        splitter = QSplitter(Qt.Horizontal)
        input_group = QGroupBox("📦 投入材料")
        ig_layout = QVBoxLayout(input_group)
        self.table_inputs = QTableWidget()
        self.table_inputs.setColumnCount(4)
        self.table_inputs.setHorizontalHeaderLabels(["名称", "磨损", "单价", "溢价"])
        self.table_inputs.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table_inputs.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        ig_layout.addWidget(self.table_inputs)
        splitter.addWidget(input_group)

        output_group = QGroupBox("🎲 可能产出")
        og_layout = QVBoxLayout(output_group)
        self.table_outputs = QTableWidget()
        self.table_outputs.setColumnCount(4)
        self.table_outputs.setHorizontalHeaderLabels(["名称", "概率", "价值", "盈亏"])
        self.table_outputs.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table_outputs.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        og_layout.addWidget(self.table_outputs)
        splitter.addWidget(output_group)

        result_layout.addWidget(splitter, 1)
        layout.addWidget(self.result_container, 1)

        self.log_area = QTextEdit()
        self.log_area.setMaximumHeight(100)
        self.log_area.setReadOnly(True)
        layout.addWidget(self.log_area)

    def start_mining(self):
        idx = self.combo_rarity.currentIndex()
        target_rarity = [3, 4, 5][idx]

        params = {
            'pop_size': self.spin_pop.value(),
            'generations': self.spin_gen.value(),
            'mutation_rate': self.spin_mutation.value(),
            'save_png': self.check_save_png.isChecked(),
            'wear_premium_factor': self.spin_premium.value(),
            'do_compare': self.check_compare.isChecked()  # ✅ 传递对比参数
        }

        self.btn_start.setEnabled(False)
        self.btn_start.setText("🔥 正在挖掘中...")
        self.log_area.clear()
        self.result_container.setVisible(False)
        self.progress.setValue(0)

        self.worker = MiningWorker(self.sim, target_rarity, params)
        self.worker.log_signal.connect(self.log_area.append)
        self.worker.progress_signal.connect(self.progress.setValue)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.start()

    def on_finished(self, results):
        self.btn_start.setEnabled(True)
        self.btn_start.setText("开始挖掘任务")

        if not results: return

        self.current_results = results
        self.populate_result_dropdown()
        self.result_container.setVisible(True)

    def get_cn_name(self, col, name, rarity):
        try:
            if col in self.sim.raw_db and rarity in self.sim.raw_db[col]:
                items = self.sim.raw_db[col][rarity]
                for i in items:
                    if i['name'] == name: return i.get('name_cn', name)
        except:
            pass
        return name

    def populate_result_dropdown(self):
        self.combo_result_select.blockSignals(True)
        self.combo_result_select.clear()
        tier_order = ['High', 'Mid', 'Low', 'Micro']
        has_data = False
        for tier in tier_order:
            recipes = self.current_results.get(tier, [])
            for i, (res, rec) in enumerate(recipes):
                roi_pct = res.roi * 100
                text = f"【{tier}】 第 {i + 1} 名 | ROI: {roi_pct:.2f}% | 成本: ¥{res.total_cost:.2f}"
                self.combo_result_select.addItem(text, (tier, i))
                has_data = True
        self.combo_result_select.blockSignals(False)
        if has_data:
            self.combo_result_select.setCurrentIndex(0)
            self.update_recipe_view()

    def update_recipe_view(self):
        data = self.combo_result_select.currentData()
        if not data: return
        tier, idx = data
        res, rec = self.current_results[tier][idx]

        roi_val = res.roi * 100
        roi_color = "#27ae60" if roi_val > 0 else "#c0392b"

        self.stats_label.setText(
            f"💰 成本: ¥{res.total_cost:.2f}  |  "
            f"📈 期望: ¥{res.expected_value:.2f}  |  "
            f"📊 ROI: <span style='color:{roi_color}'>{roi_val:.2f}%</span>  |  "
            f"🛡️ 保本: {res.break_even_prob * 100:.1f}%"
        )

        self.table_inputs.setRowCount(len(rec))
        for row, item in enumerate(rec):
            cn = self.get_cn_name(item.collection, item.name, res.input_rarity)
            self.table_inputs.setItem(row, 0, QTableWidgetItem(f"{item.collection} | {cn}"))
            self.table_inputs.setItem(row, 1, QTableWidgetItem(f"{item.float_value:.5f}"))
            self.table_inputs.setItem(row, 2, QTableWidgetItem(f"¥{item.price:.2f}"))
            prem = item.price - item.base_price
            p_item = QTableWidgetItem(f"{prem:+.2f}")
            if prem > 0: p_item.setForeground(QBrush(QColor("#c0392b")))
            self.table_inputs.setItem(row, 3, p_item)

        outcomes = sorted(res.outcomes, key=lambda x: x.price, reverse=True)
        self.table_outputs.setRowCount(len(outcomes))
        for row, out in enumerate(outcomes):
            nm = QTableWidgetItem(out.name_cn or out.name)
            if out.profit > 0: nm.setForeground(QBrush(QColor("#27ae60")))
            self.table_outputs.setItem(row, 0, nm)
            self.table_outputs.setItem(row, 1, QTableWidgetItem(f"{out.probability * 100:.1f}%"))
            self.table_outputs.setItem(row, 2, QTableWidgetItem(f"¥{out.price:.2f}"))
            pl = QTableWidgetItem(f"{out.profit:+.2f}")
            if out.profit > 0:
                pl.setForeground(QBrush(QColor("#27ae60")))
            else:
                pl.setForeground(QBrush(QColor("#c0392b")))
            self.table_outputs.setItem(row, 3, pl)