import random
import copy
import networkx as nx
from dataclasses import dataclass
from typing import List, Dict, Callable, Optional

import config
from . import utils
from .simulator import TradeInputItem, CS2TradeUpSimulator
from src.utils import visualization
from src.core.network_graph import NetworkAnalyzer


@dataclass
class CandidateInfo:
    collection: str
    data: dict
    avg_price: float
    max_output: float
    hub_score: float


class SmartOptimizer:
    def __init__(self, simulator: CS2TradeUpSimulator, use_network_guidance: bool = True):
        self.sim = simulator
        self._convert_db_currency()
        self.use_network_guidance = use_network_guidance

        self.network_weights = {}
        if self.use_network_guidance:
            try:
                print("🕸️ 正在初始化网络分析权重...")
                analyzer = NetworkAnalyzer(config.DB_PATH)
                self.network_weights = analyzer.get_optimization_weights()
                print(f"✅ 网络权重加载成功，共 {len(self.network_weights)} 个节点数据")
            except Exception as e:
                print(f"⚠️ 网络分析模块加载失败，将使用默认权重: {e}")
                self.network_weights = {}

        self.scores = self._calculate_network_scores()
        self.premium_scaler = 1.0

    def _convert_db_currency(self):
        for col in self.sim.raw_db.values():
            for tiers in col.values():
                for item in tiers:
                    if 'price_dict' in item:
                        for cond in item['price_dict']:
                            item['price_dict'][cond] *= config.EXCHANGE_RATE
        self.sim.price_engine = self.sim.price_engine.__class__(self.sim.raw_db)

    def _calculate_network_scores(self) -> Dict[str, float]:
        """计算物品权重"""
        final_scores = {}

        # 1. 实验组: 使用高级网络分析结果
        if self.use_network_guidance and self.network_weights:
            max_w = max(self.network_weights.values()) if self.network_weights else 1
            for name, score in self.network_weights.items():
                final_scores[name] = (score / max_w) * 10 + 0.1
            return final_scores

        # 2. 对照组 (Baseline): 纯随机/均匀分布
        print("ℹ️ 使用基础算法计算节点权重...")
        for col_name, tiers in self.sim.raw_db.items():
            for r in [2, 3, 4, 5]:
                for item in tiers.get(r, []):
                    final_scores[item['name']] = 1.0

        return final_scores

    def _load_candidates_for_rarity(self, rarity: int):
        cands = []
        for col, tiers in self.sim.raw_db.items():
            if rarity in tiers and (rarity + 1) in tiers:
                items = [i for i in tiers[rarity] if i.get('price_dict')]
                outputs = tiers[rarity + 1]
                if not items or not outputs: continue
                prices = []
                for item in items: prices.extend([p for p in item['price_dict'].values() if p > 0])
                if not prices: continue
                avg_p = sum(prices) / len(prices)
                out_max = max([o['price_dict'].get('Factory New', 0) for o in outputs])

                score = self.scores.get(items[0]['name'], 1.0)

                cands.append(CandidateInfo(col, items[0], avg_p, out_max, score))

        cands.sort(key=lambda x: x.max_output, reverse=True)
        lim_micro = config.TIER_MICRO_USD * config.EXCHANGE_RATE
        lim_low = config.TIER_LOW_USD * config.EXCHANGE_RATE
        lim_mid = config.TIER_MID_USD * config.EXCHANGE_RATE

        return {
            "all": cands,
            "micro": [c for c in cands if c.avg_price < lim_micro],
            "low": [c for c in cands if lim_micro <= c.avg_price < lim_low],
            "mid": [c for c in cands if lim_low <= c.avg_price < lim_mid],
            "high": [c for c in cands if c.avg_price >= lim_mid],
            "fillers": sorted(cands, key=lambda x: x.avg_price)[:40]
        }

    def _create_item(self, candidate, target_float):
        item_data = candidate.data
        eff_float = max(item_data['min_float'], min(item_data['max_float'], target_float))

        # ✅ 修复点 1：增加 candidate.collection 参数
        res = self.sim.price_engine.get_base_price(item_data['name'], eff_float, candidate.collection)

        if res == float('inf'):
            base_price = 0;
            condition = "Unknown";
            real_price = float('inf')
        else:
            base_price, condition = res
            real_price = utils.estimate_price_at_float(base_price, eff_float, condition, self.premium_scaler)
        return TradeInputItem(candidate.collection, item_data['name'], item_data['min_float'], item_data['max_float'],
                              eff_float, real_price, base_price, condition)

    def generate_initial_population(self, pools, pop_size) -> List[List[TradeInputItem]]:
        pop = []
        templates = config.RECIPE_TEMPLATES
        for _ in range(pop_size):
            if not pools['all']: break
            r = random.random()
            if r < 0.3:
                pool = pools['micro']
            elif r < 0.6:
                pool = pools['low']
            elif r < 0.8:
                pool = pools['mid']
            else:
                pool = pools['high']

            main = self._weighted_choice(pool) or self._weighted_choice(pools['all'])
            filler = self._weighted_choice(pools['fillers'])
            t_main, t_fill = random.choice(templates)
            f_strat = random.choice([0.005, 0.015, 0.035, 0.0699, 0.0701, 0.1499, 0.1501])
            recipe = []
            for _ in range(t_main): recipe.append(self._create_item(main, f_strat))
            for _ in range(t_fill): recipe.append(self._create_item(filler, f_strat))
            pop.append(recipe)
        return pop

    def _weighted_choice(self, cands):
        if not cands: return None
        return random.choices(cands, weights=[c.hub_score for c in cands], k=1)[0]

    def mutate(self, recipe, pools):
        if random.random() < 0.15:
            boundaries = [0.07, 0.15, 0.38, 0.45]
            target = random.choice(boundaries);
            eps = 0.0001 + random.random() * 0.001
            for item in recipe:
                if random.random() < 0.5: self._update_item_float(item, target + eps)
        elif random.random() < 0.4:
            shift = random.choice([-0.01, 0.01, 0.005, -0.005])
            for i in recipe: self._update_item_float(i, i.float_value + shift)
        if random.random() < 0.3:
            idx = random.randint(0, 9)
            pool = pools['fillers'] if random.random() < 0.5 else pools['all']
            cand = self._weighted_choice(pool)
            if cand: recipe[idx] = self._create_item(cand, recipe[idx].float_value)

    def _update_item_float(self, item, new_f):
        new_f = max(item.min_float, min(item.max_float, new_f))

        # ✅ 修复点 2：增加 item.collection 参数
        res = self.sim.price_engine.get_base_price(item.name, new_f, item.collection)

        if res != float('inf'):
            base, cond = res
            item.float_value = new_f;
            item.base_price = base;
            item.condition = cond
            item.price = utils.estimate_price_at_float(base, new_f, cond, self.premium_scaler)

    def run(self, target_rarity_list=None, params=None, progress_callback=None):
        if target_rarity_list is None: target_rarity_list = config.RARITIES_TO_SCAN
        pop_size = params.get('pop_size', config.POPULATION_SIZE)
        generations = params.get('generations', config.GENERATIONS)
        mutation_rate = params.get('mutation_rate', config.MUTATION_RATE)
        save_png = params.get('save_png', True)
        self.premium_scaler = params.get('wear_premium_factor', 1.0)

        session_folder = visualization.init_session_folder()
        all_results_flat = []
        history = []
        total_steps = len(target_rarity_list) * generations;
        current_step = 0

        for target_rarity in target_rarity_list:
            if progress_callback: progress_callback(int(current_step / total_steps * 100),
                                                    f"正在扫描 [{_get_rarity_name(target_rarity)}]...")
            pools = self._load_candidates_for_rarity(target_rarity)
            if not pools['all']: current_step += generations; continue

            pop = self.generate_initial_population(pools, pop_size)
            for gen in range(generations):
                current_step += 1
                if progress_callback: progress_callback(int(current_step / total_steps * 100),
                                                        f"[{_get_rarity_name(target_rarity)}] 进化: {gen + 1}/{generations}")

                scored = []
                for rec in pop:
                    res = self.sim.simulate(rec, target_rarity, config.BUFF_RATIO)
                    if res.total_cost == float('inf'):
                        score = -999999
                    else:
                        score = res.roi * 100 + (res.break_even_prob * 50)
                    if res.std_dev > res.total_cost * 2: score -= 20
                    scored.append((rec, score, res))
                    if res.roi > -0.2 and res.total_cost != float('inf'): all_results_flat.append((res, rec))

                scored.sort(key=lambda x: x[1], reverse=True)
                valid = [x for x in scored if x[1] > -90000]
                best_roi = valid[0][2].roi if valid else -1
                avg_roi = sum(x[2].roi for x in valid) / len(valid) if valid else -1

                history.append({'gen': gen, 'max_roi': best_roi, 'avg_roi': avg_roi})

                new_pop = [copy.deepcopy(scored[i][0]) for i in range(min(len(scored), config.ELITISM_COUNT))]
                while len(new_pop) < pop_size:
                    p1, p2 = random.choices(scored[:40], k=2)
                    split = random.randint(1, 9)
                    child = copy.deepcopy(p1[0][:split]) + copy.deepcopy(p2[0][split:])
                    if random.random() < mutation_rate: self.mutate(child, pools)
                    new_pop.append(child)
                pop = new_pop

        if progress_callback: progress_callback(95, "正在整理数据...")

        tier_top = self._export_results(all_results_flat, session_folder, save_png)
        tier_best_single = {k: v[0] for k, v in tier_top.items() if v}

        visualization.save_raw_data(history, all_results_flat, tier_top, session_folder, self.sim)

        if all_results_flat:
            all_results_flat.sort(key=lambda x: x[0].roi, reverse=True)
            visualization.save_detailed_report_to_excel(tier_best_single, self.sim, session_folder)

        # ✅ 生成雷达图
        visualization.plot_radar_chart(tier_best_single, session_folder)

        if progress_callback: progress_callback(100, "完成")
        return session_folder, tier_top, history

    def _export_results(self, all_results_flat, session_folder, save_png):
        buckets = {'Micro': [], 'Low': [], 'Mid': [], 'High': []}
        L_MICRO = config.TIER_MICRO_USD * config.EXCHANGE_RATE
        L_LOW = config.TIER_LOW_USD * config.EXCHANGE_RATE
        L_MID = config.TIER_MID_USD * config.EXCHANGE_RATE
        for res, rec in all_results_flat:
            if res.total_cost < L_MICRO:
                buckets['Micro'].append((res, rec))
            elif res.total_cost < L_LOW:
                buckets['Low'].append((res, rec))
            elif res.total_cost < L_MID:
                buckets['Mid'].append((res, rec))
            else:
                buckets['High'].append((res, rec))

        tier_top = {}
        for name, lst in buckets.items():
            if not lst:
                tier_top[name] = []
                continue
            lst.sort(key=lambda x: x[0].roi, reverse=True)
            top_3 = lst[:3]
            tier_top[name] = top_3

            # 对每个段位的最佳配方生成高级图表
            best_res, best_rec = top_3[0]
            if save_png:
                visualization.plot_sankey_diagram(best_res, best_rec, session_folder, name)
                visualization.plot_sunburst_chart(best_res, session_folder, name)
                visualization.plot_treemap(best_res, session_folder, name)

        if save_png:
            visualization.plot_efficient_frontier(all_results_flat, session_folder)
            visualization.plot_ridgeline_chart(all_results_flat, session_folder)
            visualization.plot_heatmap_input_vs_profit(all_results_flat, session_folder)
            visualization.plot_funnel_chart(range(config.GENERATIONS), session_folder)

        return tier_top


def _get_rarity_name(tier_num):
    return {1: "消费级", 2: "工业级", 3: "军规级", 4: "受限级", 5: "保密级", 6: "隐秘级"}.get(tier_num, str(tier_num))