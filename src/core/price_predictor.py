import numpy as np
import pandas as pd
import requests
import feedparser
from textblob import TextBlob
from datetime import datetime, timedelta
import urllib.parse
import time
import random
import re
import json
import traceback
import config

# 尝试导入机器学习库
try:
    from sklearn.preprocessing import MinMaxScaler
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Input
    import os

    # 抑制 TensorFlow 的烦人日志
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
    HAS_ML = True
except ImportError as e:
    HAS_ML = False
    print(f"⚠️ 未检测到 TensorFlow/Sklearn，预测模块将运行在简易模式。错误: {e}")


class NameTranslator:
    """中文饰品名转英文 Market Hash Name"""

    def __init__(self):
        self.cn_to_en_items = {}
        self.suggestion_list = []
        self.condition_map = {
            "崭新出厂": "Factory New", "略有磨损": "Minimal Wear",
            "久经沙场": "Field-Tested", "破损不堪": "Well-Worn",
            "战痕累累": "Battle-Scarred", "崭新": "Factory New",
            "略磨": "Minimal Wear", "久经": "Field-Tested",
            "破损": "Well-Worn", "战痕": "Battle-Scarred"
        }
        self.en_cond_to_cn = {
            "Factory New": "崭新出厂", "Minimal Wear": "略有磨损",
            "Field-Tested": "久经沙场", "Well-Worn": "破损不堪",
            "Battle-Scarred": "战痕累累"
        }
        self._load_db()

    def _load_db(self):
        try:
            with open(config.DB_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                standard_conds = ["Factory New", "Minimal Wear", "Field-Tested", "Well-Worn", "Battle-Scarred"]

                for col, tiers in data.items():
                    for tier, items in tiers.items():
                        for item in items:
                            name_en = item.get('name')
                            name_cn = item.get('name_cn')

                            if name_en:
                                if name_cn: self.cn_to_en_items[name_cn] = name_en
                                self.cn_to_en_items[name_en] = name_en

                                for cond in standard_conds:
                                    full_en = f"{name_en} ({cond})"
                                    self.suggestion_list.append(full_en)
                                    if name_cn:
                                        cn_cond = self.en_cond_to_cn.get(cond, "")
                                        full_cn = f"{name_cn} ({cn_cond})"
                                        self.suggestion_list.append(full_cn)
                                self.suggestion_list.append(name_en)
                                if name_cn: self.suggestion_list.append(name_cn)

        except Exception as e:
            print(f"❌ 数据库加载失败: {e}")

    def get_all_names(self):
        return sorted(list(set(self.suggestion_list)))

    def translate(self, user_input):
        user_input = user_input.strip()
        target_cond = ""
        clean_input = user_input

        for cn, en in self.condition_map.items():
            if cn in user_input:
                target_cond = en
                clean_input = clean_input.replace(cn, "").replace("()", "").replace("（）", "").strip()
                break

        if not target_cond:
            ens = ["Factory New", "Minimal Wear", "Field-Tested", "Well-Worn", "Battle-Scarred"]
            for en in ens:
                if en.lower() in user_input.lower():
                    target_cond = en
                    clean_input = re.sub(re.escape(en), "", clean_input, flags=re.IGNORECASE).replace("()", "").replace(
                        "（）", "").strip()
                    break

        clean_input = clean_input.strip(" |")

        real_name = self.cn_to_en_items.get(clean_input)
        if not real_name:
            for cn, en in self.cn_to_en_items.items():
                if clean_input in cn or clean_input.lower() in en.lower():
                    real_name = en
                    break

        if not real_name: real_name = clean_input

        if target_cond:
            return f"{real_name} ({target_cond})"
        return real_name


class DataFetcher:
    def __init__(self, cookie=None):
        self.cookie = cookie
        self.base_url = "https://steamcommunity.com/market/pricehistory/"
        self.translator = NameTranslator()

        # ✅ 修复核心问题：手动月份映射
        # 即使系统是中文，也能正确解析 Steam 的英文月份
        self.month_map = {
            "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
            "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12
        }

    def fetch_price_history(self, user_input_name):
        market_hash_name = self.translator.translate(user_input_name)
        print(f"🔍 解析饰品名: {market_hash_name}")

        encoded_name = urllib.parse.quote(market_hash_name)
        # currency=23 是人民币
        url = f"{self.base_url}?country=CN&currency=23&appid=730&market_hash_name={encoded_name}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://steamcommunity.com/market/",
        }

        if self.cookie:
            headers["Cookie"] = f"steamLoginSecure={self.cookie}"
            print(f"✅ 使用 Cookie (长度: {len(self.cookie)})")
        else:
            print("⚠️ 未提供 Cookie，尝试匿名获取（可能失败）")

        try:
            print(f"📡 请求 Steam API...")
            response = requests.get(url, headers=headers, timeout=15)

            if response.status_code == 200:
                data = response.json()

                if data and 'prices' in data:
                    raw_count = len(data['prices'])
                    print(f"✅ 获取到 {raw_count} 条原始价格数据")
                    if raw_count == 0:
                        return None, "Steam 返回了空数据 (可能物品暂无成交)"
                    return self._process_raw_data(data['prices'])
                else:
                    return None, "API 响应格式错误 (未找到 prices 字段)"

            elif response.status_code == 429:
                return None, "请求过于频繁 (HTTP 429)"
            elif response.status_code == 403:
                return None, "无权访问 (HTTP 403) - Cookie 可能已失效或需要登录"
            else:
                return None, f"请求失败 HTTP {response.status_code}"

        except requests.exceptions.Timeout:
            return None, "请求 Steam 超时，请检查网络代理"
        except Exception as e:
            print(f"❌ 异常: {type(e).__name__}: {str(e)}")
            return None, f"请求异常: {str(e)}"

    def _process_raw_data(self, raw_data):
        clean = []
        parse_errors = 0
        success_count = 0

        # Steam 格式示例: ["Nov 14 2023 01: +0", 1.23, "100"]
        for p in raw_data:
            try:
                date_part = p[0].split(":")[0]  # "Nov 14 2023 01"
                # 手动解析，不使用 strptime 的 %b，避免 locale 问题
                parts = date_part.split()  # ['Nov', '14', '2023', '01']
                if len(parts) >= 3:
                    month_str = parts[0]
                    day = int(parts[1])
                    year = int(parts[2])

                    month = self.month_map.get(month_str, 1)
                    dt = datetime(year, month, day)

                    clean.append({"Date": dt, "Price": float(p[1]), "Volume": int(p[2])})
                    success_count += 1
                else:
                    parse_errors += 1
            except Exception:
                parse_errors += 1

        if parse_errors > 0:
            print(f"⚠️ 解析失败 {parse_errors} 条数据 (成功 {success_count} 条)")

        df = pd.DataFrame(clean)
        if df.empty:
            print("❌ 数据解析后为空")
            return None, "数据解析失败 (日期格式不兼容)"

        # 按日聚合
        df_daily = df.groupby('Date').agg({'Price': 'mean', 'Volume': 'sum'}).reset_index()

        # 过滤最近 365 天
        today = datetime.now()
        one_year_ago = today - timedelta(days=365)
        df_daily = df_daily[(df_daily['Date'] >= one_year_ago) & (df_daily['Date'] <= today)]

        final_count = len(df_daily)
        print(f"✅ 最终有效历史数据: {final_count} 天")

        if final_count < 14:
            return None, f"近期数据不足 (仅 {final_count} 天)，无法进行有效预测"

        return df_daily.sort_values('Date'), "Success"


class SentimentAnalyzer:
    def __init__(self):
        self.sources = [
            "https://news.google.com/rss/search?q=CS2+Counter-Strike+Skins+Market&hl=en-US&gl=US&ceid=US:en",
            "https://www.reddit.com/r/csgomarketforum/new/.rss"
        ]

    def get_market_sentiment(self):
        total_p = 0
        count = 0
        for url in self.sources:
            try:
                feed = feedparser.parse(url)
                if not feed.entries: continue
                for entry in feed.entries[:5]:
                    blob = TextBlob(entry.title)
                    total_p += blob.sentiment.polarity
                    count += 1
            except Exception:
                pass

        if count == 0: return 0.0, "中性 (无数据)"
        score = np.tanh((total_p / count) * 5)

        if score > 0.25:
            status = "贪婪 (Greedy) 🐂"
        elif score < -0.25:
            status = "恐慌 (Fear) 🐻"
        else:
            status = "中性 (Neutral) ⚖️"
        return score, status


class PricePredictor:
    def __init__(self, df):
        self.df = df
        self.look_back = 15  # 观察窗口
        self.forecast_days = 7

    def predict(self):
        if self.df is None or len(self.df) < 30:
            return None, "数据量不足以进行预测"

        if HAS_ML:
            try:
                return self._predict_lstm()
            except Exception as e:
                print("⚠️ LSTM 预测发生严重错误:")
                traceback.print_exc()
                print("👉 自动降级为线性预测")
                return self._predict_linear()
        else:
            print("ℹ️ 未安装 AI 库，使用线性预测")
            return self._predict_linear()

    def _predict_lstm(self):
        # 数据预处理
        data = self.df['Price'].values.reshape(-1, 1)
        scaler = MinMaxScaler(feature_range=(0, 1))
        scaled = scaler.fit_transform(data)

        X, Y = [], []
        for i in range(len(scaled) - self.look_back):
            X.append(scaled[i:i + self.look_back, 0])
            Y.append(scaled[i + self.look_back, 0])

        if len(X) == 0:
            raise ValueError("数据不足以构建 LSTM 序列")

        X = np.reshape(np.array(X), (len(X), self.look_back, 1))
        Y = np.array(Y)

        # 构建模型
        model = Sequential()
        model.add(Input(shape=(self.look_back, 1)))
        # 增加神经元和层数，提高拟合能力
        model.add(LSTM(64, return_sequences=True))
        model.add(LSTM(32, return_sequences=False))
        model.add(Dense(16, activation='relu'))
        model.add(Dense(1))

        # 增加 epoch 数，避免欠拟合导致直线
        model.compile(loss='mse', optimizer='adam')
        model.fit(X, Y, epochs=30, batch_size=8, verbose=0)

        # 递归预测
        preds = []
        curr = scaled[-self.look_back:].reshape(1, self.look_back, 1)

        for _ in range(self.forecast_days):
            p = model.predict(curr, verbose=0)[0]
            preds.append(p)
            # 滑动窗口
            curr = np.append(curr[:, 1:, :], [[p]], axis=1)

        final_prices = scaler.inverse_transform(np.array(preds).reshape(-1, 1)).flatten()
        dates = [self.df['Date'].iloc[-1] + timedelta(days=i) for i in range(1, self.forecast_days + 1)]

        return pd.DataFrame({'Date': dates, 'Price': final_prices}), None

    def _predict_linear(self):
        """
        改进版线性回归
        不再画死板的直线，而是基于历史波动率生成随机游走 (Random Walk with Drift)
        """
        last_p = self.df['Price'].iloc[-1]
        recent = self.df['Price'].iloc[-20:]  # 看最近20天

        # 计算简单趋势
        x = np.arange(len(recent))
        y = recent.values
        z = np.polyfit(x, y, 1)  # 1次多项式拟合
        trend = z[0]  # 斜率

        # 计算历史波动率 (标准差)
        std_dev = recent.std()

        dates = []
        prices = []

        current_p = last_p
        for i in range(1, self.forecast_days + 1):
            # 趋势 + 随机扰动 (模拟市场噪音)
            # 使用高斯分布，标准差取历史的一半，避免波动过大
            noise = random.gauss(0, std_dev * 0.6)
            current_p += trend + noise

            dates.append(self.df['Date'].iloc[-1] + timedelta(days=i))
            prices.append(max(0.01, current_p))  # 价格不能为负

        return pd.DataFrame({'Date': dates, 'Price': prices}), "Warning: Running in Linear Mode (Low Accuracy)"