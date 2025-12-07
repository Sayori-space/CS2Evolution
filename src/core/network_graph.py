import networkx as nx
import json
import os
import matplotlib.colors as mcolors
from pyvis.network import Network
import config


class NetworkAnalyzer:
    """
    负责构建 CS2 饰品交易网络。
    【架构关键】内部 ID 使用 "英文名 (系列)" 以确保唯一性和算法匹配。
    显示时使用 "中文名" 作为 Label。
    """

    def __init__(self, db_path):
        self.db_path = db_path
        self.G = nx.DiGraph()
        self.raw_db = {}
        self.metrics = {}
        self._load_and_build()

    def _load_and_build(self):
        print(f"🕸️ [NetworkAnalyzer] 开始加载数据库...")

        if not os.path.exists(self.db_path):
            print(f"❌ 数据库不存在")
            return

        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                self.raw_db = json.load(f)
        except Exception as e:
            print(f"❌ 读取 JSON 失败: {e}")
            return

        node_count = 0

        # 构建图
        for col_name, tiers in self.raw_db.items():
            tiers_int = {}
            for k, v in tiers.items():
                try:
                    tiers_int[int(k)] = v
                except:
                    pass

            for r in [2, 3, 4, 5]:
                inputs = tiers_int.get(r, [])
                outputs = tiers_int.get(r + 1, [])
                if not inputs or not outputs: continue

                for i_item in inputs:
                    # ✅ 核心修正：ID 使用英文唯一标识，Label 使用中文
                    u_id = f"{i_item['name']} ({col_name})"
                    u_label = i_item.get('name_cn', i_item['name'])

                    price_vals = list(i_item.get('price_dict', {}).values())
                    avg_price = float(sum(price_vals) / len(price_vals)) if price_vals else 0.0

                    if u_id not in self.G:
                        self.G.add_node(u_id, label=u_label, title=f"均价: ¥{avg_price:.2f}", group=int(r),
                                        value=avg_price)
                        node_count += 1

                    for o_item in outputs:
                        v_id = f"{o_item['name']} ({col_name})"
                        v_label = o_item.get('name_cn', o_item['name'])

                        oprice_vals = list(o_item.get('price_dict', {}).values())
                        avg_oprice = float(sum(oprice_vals) / len(oprice_vals)) if oprice_vals else 0.0

                        if v_id not in self.G:
                            self.G.add_node(v_id, label=v_label, title=f"均价: ¥{avg_oprice:.2f}", group=int(r + 1),
                                            value=avg_oprice)
                            node_count += 1

                        safe_price = avg_price if avg_price > 0.1 else 0.1
                        roi = (avg_oprice - safe_price) / safe_price
                        weight = avg_oprice / safe_price

                        self.G.add_edge(u_id, v_id, weight=weight, roi=roi, title=f"ROI: {roi * 100:.1f}%")

        print(f"✅ 网络构建完成: {node_count} 节点 (内部英文ID)")

    def calculate_centrality(self):
        if not self.G.nodes: return {}
        try:
            pagerank = nx.pagerank(self.G, weight='weight')
        except:
            pagerank = nx.degree_centrality(self.G)

        hubs = nx.degree_centrality(self.G)
        self.metrics = {'pagerank': pagerank, 'hubs': hubs}
        return self.metrics

    def get_optimization_weights(self):
        """
        供 SmartOptimizer 使用。
        返回 { "AK-47 | Slate": score, ... }
        """
        if not self.metrics: self.calculate_centrality()
        weights = {}
        pr = self.metrics.get('pagerank', {})
        for node_id, score in pr.items():
            # node_id 是 "Name (Collection)"
            # 我们需要拆分出 Name 给优化器匹配
            clean_name = node_id.split(' (')[0]
            weights[clean_name] = float(score * 100)
        return weights

    def _darken_color(self, hex_color, factor):
        try:
            rgb = mcolors.hex2color(hex_color)
            new_rgb = [max(0, c * factor) for c in rgb]
            return mcolors.to_hex(new_rgb)
        except:
            return hex_color

    def generate_interactive_html(self, output_path, rarity_filter=None, top_n=100, theme_colors=None):
        if not self.G.nodes:
            self._write_empty(output_path, "No Data")
            return output_path

        # 1. 颜色适配
        bg_color = theme_colors.get('bg_main', '#121212') if theme_colors else '#121212'
        is_dark = True
        if bg_color.startswith('#'):
            r, g, b = int(bg_color[1:3], 16), int(bg_color[3:5], 16), int(bg_color[5:7], 16)
            if (r + g + b) / 3 > 128: is_dark = False
        font_color = '#ffffff' if is_dark else '#222222'

        # 2. 筛选
        sub_G = self.G.copy()
        if rarity_filter:
            nodes_to_keep = [n for n, attr in sub_G.nodes(data=True) if attr.get('group') in rarity_filter]
            sub_G = sub_G.subgraph(nodes_to_keep)

        if sub_G.number_of_nodes() > top_n:
            try:
                pr = nx.pagerank(sub_G)
                top_nodes = sorted(pr, key=pr.get, reverse=True)[:top_n]
                sub_G = sub_G.subgraph(top_nodes)
            except:
                deg = nx.degree_centrality(sub_G)
                top_nodes = sorted(deg, key=deg.get, reverse=True)[:top_n]
                sub_G = sub_G.subgraph(top_nodes)

        # 3. 初始化 PyVis
        net = Network(height="800px", width="100%", bgcolor=bg_color, font_color=font_color, select_menu=True,
                      cdn_resources='remote')
        net.from_nx(sub_G)

        # 4. 视觉增强
        base_colors = {1: '#dbeafe', 2: '#93c5fd', 3: '#60a5fa', 4: '#c084fc', 5: '#f472b6', 6: '#f87171'}

        all_prices = [float(n.get('value', 0)) for n in net.nodes]
        max_price = max(all_prices) if all_prices else 1.0
        min_price = min(all_prices) if all_prices else 0.0

        for node in net.nodes:
            group = node.get('group', 1)
            price = float(node.get('value', 0))

            # 颜色加深
            norm_price = (price - min_price) / (max_price - min_price + 0.1)
            darken = 1.0 - (norm_price * 0.5)
            base_c = base_colors.get(group, '#cccccc')
            final_color = self._darken_color(base_c, darken)

            node['color'] = {
                'background': final_color,
                'border': '#fff' if is_dark else '#333',
                'highlight': {'background': '#ffd700', 'border': '#fff'},
                'hover': {'background': '#ffd700', 'border': '#fff'}
            }
            node['size'] = 20 + (norm_price * 30)

            # ✅ 关键：显示时使用中文 Label
            display_label = node.get('label', node.get('id'))
            node['label'] = str(display_label)
            node['title'] = f"<b>{display_label}</b><br>均价: ¥{price:.2f}"
            node['font'] = {'size': 16, 'face': 'Microsoft YaHei'}

        # 边样式
        all_profits = [float(e.get('profit', 0)) for e in net.edges]
        max_prof = max(all_profits) if all_profits else 1.0

        for edge in net.edges:
            profit = float(edge.get('profit', 0))
            width = 1.0 + (profit / (max_prof + 0.1)) * 7.0 if profit > 0 else 1.0
            edge['width'] = min(8.0, width)

            if profit < 0:
                col, op = '#555', 0.2
            elif profit < max_prof * 0.5:
                col, op = '#ff9f43', 0.6
            else:
                col, op = '#ff4757', 0.9

            edge['color'] = {'color': col, 'opacity': op, 'highlight': '#00d2ff', 'hover': '#00d2ff'}
            edge['title'] = f"价值变动: ¥{profit:+.2f}"

        # 5. 物理配置
        options = {
            "nodes": {
                "shape": "dot",
                "scaling": {
                    "min": 10, "max": 50,
                    "label": {"enabled": True, "min": 14, "max": 30},
                    "customScalingFunction": "SCALING_FUNC_PLACEHOLDER"
                }
            },
            "interaction": {
                "hover": True, "hoverConnectedEdges": True,
                "navigationButtons": True, "keyboard": True, "zoomView": True
            },
            "physics": {
                "forceAtlas2Based": {
                    "gravitationalConstant": -100, "centralGravity": 0.01,
                    "springLength": 120, "springConstant": 0.08,
                    "damping": 0.4, "avoidOverlap": 0.6
                },
                "maxVelocity": 40, "minVelocity": 0.1, "solver": "forceAtlas2Based",
                "stabilization": {"enabled": True, "iterations": 600}
            }
        }
        net.set_options(json.dumps(options))

        # 6. 保存
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        try:
            html = net.generate_html()
            # 修复 customScalingFunction 被 json.dumps 转为字符串的问题
            html = html.replace('"SCALING_FUNC_PLACEHOLDER"', "function (min,max,total,value) { if (max === min) return 0.5; var scale = 1.0 / (max - min); return Math.max(0,(value - min)*scale); }")
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html)
        except Exception as e:
            self._write_empty(output_path, str(e))
        return output_path

    def _write_empty(self, p, m):
        try:
            with open(p, 'w', encoding='utf-8') as f:
                f.write(f"<html><body><h3>{m}</h3></body></html>")
        except:
            pass