# src/core/utils.py
import requests
import json
import random
import config

# ✅ 修改：增加 premium_scaler 参数，默认 1.0
def estimate_price_at_float(base_price: float, float_val: float, condition: str, premium_scaler: float = 1.0) -> float:
    """
    【残酷版智能溢价模型 3.2】
    支持动态调整溢价倍数
    """
    if base_price <= 0 or base_price == float('inf'): return float('inf')

    # 定义每个区间的起始点
    ranges = {
        "Factory New": 0.00,
        "Minimal Wear": 0.07,
        "Field-Tested": 0.15,
        "Well-Worn": 0.38,
        "Battle-Scarred": 0.45
    }
    range_min = ranges.get(condition, 0.0)
    delta = max(0, float_val - range_min)
    multiplier = 1.0

    if condition == "Factory New":
        if delta <= 0.005:
            multiplier = 5.0
        elif delta <= 0.015:
            multiplier = 3.0
        elif delta <= 0.035:
            multiplier = 1.5

    elif condition == "Minimal Wear":
        if delta <= 0.005:
            multiplier = 2.0
        elif delta <= 0.015:
            multiplier = 1.4
        elif delta <= 0.03:
            multiplier = 1.1

    elif condition == "Field-Tested":
        if delta <= 0.01:
            multiplier = 2.0
        elif delta <= 0.03:
            multiplier = 1.3
        elif delta <= 0.05:
            multiplier = 1.1

    # ✅ 新增：应用用户设置的溢价系数
    if multiplier > 1.0:
        multiplier = 1.0 + (multiplier - 1.0) * premium_scaler

    # 价格平滑 (维持原逻辑)
    if multiplier > 1.0:
        rate = config.EXCHANGE_RATE
        if base_price > (50.0 * rate):
            multiplier = 1.0 + (multiplier - 1.0) * 0.6

    return base_price * multiplier


def fetch_realtime_prices():
    """获取 Skinport 实时价格"""
    print("☁️  正在尝试联网获取实时价格 (Skinport API)...")
    url = "https://api.skinport.com/v1/items"
    params = {"app_id": 730, "currency": "USD", "tradable": 0}
    headers = {"User-Agent": "CS2_Desktop_App/1.0"}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            price_map = {}
            for item in data:
                name = item.get('market_hash_name')
                price = item.get('min_price')
                if name and price is not None:
                    price_map[name] = float(price)
            print(f"   ✅ 连接成功！获取到 {len(price_map)} 条实时报价")
            return price_map
        return None
    except Exception as e:
        print(f"   ⚠️ 网络连接跳过: {e}")
        return None