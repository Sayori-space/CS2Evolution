import json
import math
import os
from dataclasses import dataclass, field
from typing import List, Dict

import config
from .core_engine import CS2PriceEngine, CS2ConditionMapper


@dataclass
class TradeInputItem:
    collection: str
    name: str
    min_float: float
    max_float: float
    float_value: float
    price: float
    base_price: float = 0.0
    condition: str = ""


@dataclass
class TradeOutcome:
    name: str
    name_cn: str
    collection: str
    rarity: int
    condition: str
    float_value: float
    probability: float
    price: float
    profit: float


@dataclass
class SimulationResult:
    total_cost: float
    expected_value: float
    roi: float
    break_even_prob: float
    std_dev: float
    outcomes: List[TradeOutcome]
    avg_input_percentage: float
    input_rarity: int
    inputs: List[TradeInputItem] = field(default_factory=list)


class CS2TradeUpSimulator:
    def __init__(self, db_path):
        self.db_path = str(db_path)
        self.raw_db = {}
        self.load_local_db()
        self.price_engine = CS2PriceEngine(self.raw_db)
        self.condition_mapper = CS2ConditionMapper()

    def load_local_db(self):
        try:
            with open(self.db_path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
                for col, content in raw_data.items():
                    self.raw_db[col] = {int(k): v for k, v in content.items()}
            print(f"✅ 模拟器数据库已加载")
        except FileNotFoundError:
            raise FileNotFoundError(f"找不到数据库文件: {self.db_path}")

    def update_prices_from_map(self, price_map: Dict[str, float]):
        # 注意：此方法暂未完全适配 Collection 隔离，如需使用外部API更新，
        # 需要确保外部API提供 Collection 信息或接受模糊匹配风险。
        # 当前主要用于手动修正。
        count = 0
        manual_count = 0

        for col_name, tiers in self.raw_db.items():
            for rarity, items in tiers.items():
                for item in items:
                    base_name = item['name']
                    if 'price_dict' not in item: continue

                    for condition in list(item['price_dict'].keys()):
                        full_name = f"{base_name} ({condition})"

                        if hasattr(config, 'MANUAL_PRICE_OVERRIDE') and full_name in config.MANUAL_PRICE_OVERRIDE:
                            cny_price = config.MANUAL_PRICE_OVERRIDE[full_name]
                            item['price_dict'][condition] = cny_price / config.EXCHANGE_RATE
                            manual_count += 1
                            continue

                        if price_map and full_name in price_map:
                            new_price = price_map[full_name]
                            if new_price > 0:
                                item['price_dict'][condition] = new_price
                                count += 1

        self.price_engine = CS2PriceEngine(self.raw_db)
        print(f"✅ 价格引擎已重建 (API更新: {count}, 手动: {manual_count})")

    def get_wear_name(self, float_val: float) -> str:
        return self.condition_mapper.get_condition(float_val).value

    def calculate_new_formula_factor(self, inputs: List[TradeInputItem]) -> float:
        total_percentage = 0.0
        for item in inputs:
            range_span = item.max_float - item.min_float
            if range_span <= 1e-9:
                percentage = 0.0
            else:
                percentage = (item.float_value - item.min_float) / range_span
            percentage = max(0.0, min(1.0, percentage))
            total_percentage += percentage
        return total_percentage / 10.0

    def simulate(self, inputs: List[TradeInputItem], target_rarity: int,
                 price_modifier: float = 1.0) -> SimulationResult:
        if len(inputs) != 10:
            return SimulationResult(0, 0, -1, 0, 0, [], 0, 0)

        current_total_cost = 0.0
        for item in inputs:
            if item.price == float('inf'):
                return SimulationResult(float('inf'), 0, -1.0, 0, 0, [], 0, target_rarity, inputs)
            current_total_cost += item.price

        total_cost = current_total_cost * price_modifier
        avg_percentage = self.calculate_new_formula_factor(inputs)

        col_counts = {}
        for item in inputs:
            col_counts[item.collection] = col_counts.get(item.collection, 0) + 1

        outcomes = []
        expected_value = 0.0
        prob_break_even = 0.0
        outcome_values = []

        for col_name, count in col_counts.items():
            prob_collection = count / 10.0
            next_rarity_items = self.raw_db.get(col_name, {}).get(target_rarity + 1, [])

            if not next_rarity_items: continue
            prob_item = prob_collection / len(next_rarity_items)

            for out_data in next_rarity_items:
                out_min = out_data['min_float']
                out_max = out_data['max_float']

                result_float = (out_max - out_min) * avg_percentage + out_min
                result_float = round(result_float, 9)
                result_float = max(out_min, min(out_max, result_float))

                # ✅ 修复：传入 collection (col_name) 进行精确查询
                raw_price_res = self.price_engine.get_base_price(
                    out_data['name'], result_float, collection=col_name
                )

                if raw_price_res == float('inf') or isinstance(raw_price_res, float):
                    raw_price = 0.0
                    cond_name = self.get_wear_name(result_float)
                else:
                    raw_price, cond_name = raw_price_res

                real_price = raw_price * price_modifier
                cn_name = out_data.get('name_cn', out_data['name'])

                outcome = TradeOutcome(
                    name=out_data['name'], name_cn=cn_name, collection=col_name,
                    rarity=target_rarity + 1, condition=cond_name,
                    float_value=result_float, probability=prob_item,
                    price=real_price, profit=real_price - total_cost
                )
                outcomes.append(outcome)
                expected_value += real_price * prob_item
                outcome_values.append((prob_item, real_price))

                if real_price >= total_cost * 0.99:
                    prob_break_even += prob_item

        roi = (expected_value - total_cost) / total_cost if total_cost > 0 else -1.0

        if not outcome_values:
            std_dev = 0.0
        else:
            variance = sum([prob * ((val - expected_value) ** 2) for prob, val in outcome_values])
            std_dev = math.sqrt(variance)

        return SimulationResult(total_cost, expected_value, roi, prob_break_even, std_dev, outcomes, avg_percentage,
                                target_rarity, inputs)