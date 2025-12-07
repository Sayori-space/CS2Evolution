import bisect
from enum import Enum
from typing import Dict, Optional, Tuple


class SkinCondition(Enum):
    FN = "Factory New"
    MW = "Minimal Wear"
    FT = "Field-Tested"
    WW = "Well-Worn"
    BS = "Battle-Scarred"


class CS2ConditionMapper:
    """
    负责处理CS2磨损区间的精确映射。
    """

    def __init__(self):
        self.upper_bounds = [0.07, 0.15, 0.38, 0.45]
        self.conditions = [
            SkinCondition.FN,
            SkinCondition.MW,
            SkinCondition.FT,
            SkinCondition.WW,
            SkinCondition.BS
        ]

    def get_condition(self, float_value: float) -> SkinCondition:
        clamped_float = max(0.0, min(1.0, float_value))
        index = bisect.bisect_right(self.upper_bounds, clamped_float)
        return self.conditions[index]


class CS2PriceEngine:
    """
    集成磨损锁定检查与防御性定价查询。
    ✅ 修复：现在使用 (Collection, Name, Condition) 作为唯一键，防止同名物品价格污染。
    """

    def __init__(self, raw_db: dict):
        self.raw_db = raw_db
        self.mapper = CS2ConditionMapper()

        # 键结构: (collection, name, condition_str) -> price
        self.price_map: Dict[Tuple[str, str, str], float] = {}
        # 键结构: (collection, name) -> metadata
        self.metadata_map: Dict[Tuple[str, str], dict] = {}

        self._flatten_database()

    def _flatten_database(self):
        """将复杂的层级DB展平，支持 Collection 隔离"""
        for col, tiers in self.raw_db.items():
            for rarity, items in tiers.items():
                for item in items:
                    name = item['name']
                    # 组合键：(收藏品, 名称)
                    meta_key = (col, name)

                    self.metadata_map[meta_key] = {
                        'min': item['min_float'],
                        'max': item['max_float'],
                        'rarity': int(rarity)
                    }

                    if 'price_dict' in item:
                        for cond_name, price in item['price_dict'].items():
                            # 组合键：(收藏品, 名称, 磨损状况)
                            full_key = (col, name, cond_name)
                            self.price_map[full_key] = price

    def get_base_price(self, name: str, float_val: float, collection: str) -> float:
        """
        获取基准价格。
        ✅ 必须提供 collection 以精确定位。
        """
        # 1. 物理存在性验证 (Physics Check)
        meta = self.metadata_map.get((collection, name))
        if not meta:
            # 尝试回退：如果找不到特定 Collection，可能数据源有误，暂时返回 inf 避免错误估值
            return float('inf')

        epsilon = 1e-9
        if not (meta['min'] - epsilon <= float_val <= meta['max'] + epsilon):
            return float('inf')

        # 2. 映射条件
        condition_enum = self.mapper.get_condition(float_val)
        condition_str = condition_enum.value

        # 3. 构造查询键
        query_key = (collection, name, condition_str)

        # 4. 价格查询
        price = self.price_map.get(query_key)

        # 缺失处理
        if price is None or price <= 0:
            return float('inf')

        return price, condition_str