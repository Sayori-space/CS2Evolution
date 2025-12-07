import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
import os
import datetime
import json
from pathlib import Path
from src.utils.path_manager import PathManager

# 尝试导入 Plotly
try:
    import plotly.graph_objects as go
    import plotly.express as px

    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    print("⚠️ 警告: 未检测到 Plotly，高级交互图表将不可用。")

# 全局绘图配置
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False
sns.set_style("whitegrid", {'font.sans-serif': ['Microsoft YaHei', 'SimHei']})


def init_session_folder():
    root_dir = PathManager.get_report_dir()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    session_path = root_dir / timestamp
    session_path.mkdir(parents=True, exist_ok=True)
    return str(session_path)


def save_plot(filename, folder_path):
    full_path = os.path.join(folder_path, filename)
    try:
        plt.savefig(full_path, dpi=300, bbox_inches='tight')
        plt.close()
    except Exception as e:
        print(f"❌ 保存图片失败 {filename}: {e}")


def save_raw_data(history_data, all_results, buckets, folder_path, simulator):
    """保存原始数据到 JSON"""
    data_path = os.path.join(folder_path, "session_data.json")
    evolution_data = history_data if history_data else []

    scatter_data = []
    roi_distribution = []
    for r, rec in all_results:
        scatter_data.append({
            "roi": r.roi, "cost": r.total_cost, "std_dev": r.std_dev,
            "rarity": r.input_rarity, "input_pos": r.avg_input_percentage
        })
        roi_distribution.append(r.roi)

    # 简单提取各段位 Top 5
    top_recipes = {}
    for tier, lst in buckets.items():
        top_n = lst[:5]
        tier_data = []
        for rank, (res, rec) in enumerate(top_n):
            tier_data.append({
                "rank": rank + 1,
                "roi": res.roi,
                "cost": res.total_cost,
                "expected": res.expected_value
            })
        top_recipes[tier] = tier_data

    payload = {
        "evolution": evolution_data,
        "scatter": scatter_data,
        "roi_list": roi_distribution,
        "top_recipes": top_recipes
    }

    try:
        with open(data_path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2)
    except:
        pass


def save_detailed_report_to_excel(best_recipes, simulator, folder_path):
    pass  # 暂留空


# ==========================================
# 1. 算法效能对比图 (Convergence Comparison)
# ==========================================
def plot_convergence_comparison(history_baseline, history_guided, folder_path):
    if not history_baseline or not history_guided:
        print("⚠️ 缺少对比数据，跳过绘制对比图")
        return
    df_base = pd.DataFrame(history_baseline)
    df_guide = pd.DataFrame(history_guided)
    min_len = min(len(df_base), len(df_guide))
    df_base = df_base.iloc[:min_len]
    df_guide = df_guide.iloc[:min_len]

    plt.figure(figsize=(12, 7))

    # 绘制曲线
    plt.plot(df_base['gen'], df_base['max_roi'] * 100, label='原始算法 (Baseline)', linestyle='--', color='gray',
             alpha=0.8)
    plt.plot(df_guide['gen'], df_guide['max_roi'] * 100, label='网络指导 (Guided)', color='#e74c3c', linewidth=2.5)

    # 填充差异
    plt.fill_between(df_base['gen'], df_base['max_roi'] * 100, df_guide['max_roi'] * 100,
                     where=(df_guide['max_roi'] > df_base['max_roi']),
                     interpolate=True, color='#e74c3c', alpha=0.1, label='效能提升')

    plt.title('算法收敛效能对比: 网络图论 vs 随机搜索', fontsize=16, fontweight='bold')
    plt.xlabel('进化代数', fontsize=12)
    plt.ylabel('最佳 ROI (%)', fontsize=12)
    plt.legend(fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.5)

    save_plot("convergence_comparison.png", folder_path)


# ==========================================
# 2. 桑基图 (Sankey)
# ==========================================
def plot_sankey_diagram(best_res, rec, folder_path, tier_name):
    if not PLOTLY_AVAILABLE: return
    try:
        # 构建节点和流向
        # Inputs -> Furnace -> Outputs
        input_map = {}
        for item in rec:
            name = f"{item.collection}\n{item.name}"
            input_map[name] = input_map.get(name, 0) + item.price

        output_map = {}
        for out in best_res.outcomes:
            name = f"{out.collection}\n{out.name}"
            val = out.probability * out.price
            output_map[name] = output_map.get(name, 0) + val

        labels = list(input_map.keys()) + ["炼金炉"] + list(output_map.keys())
        furnace_idx = len(input_map)

        sources, targets, values = [], [], []

        # In -> Furnace
        for i, val in enumerate(input_map.values()):
            sources.append(i)
            targets.append(furnace_idx)
            values.append(val)

        # Furnace -> Out
        for i, val in enumerate(output_map.values()):
            sources.append(furnace_idx)
            targets.append(furnace_idx + 1 + i)
            values.append(val)

        fig = go.Figure(data=[go.Sankey(
            node=dict(
                pad=15, thickness=20, line=dict(color="black", width=0.5),
                label=labels, color=["#3498db"] * len(input_map) + ["#e74c3c"] + ["#2ecc71"] * len(output_map)
            ),
            link=dict(source=sources, target=targets, value=values)
        )])

        fig.update_layout(title_text=f"资金流向桑基图 ({tier_name})", font_size=12)
        _save_plotly_fig(fig, folder_path, f"sankey_{tier_name}")

    except Exception as e:
        print(f"⚠️ Sankey 绘制失败: {e}")


# ==========================================
# 3. 旭日图 (Sunburst)
# ==========================================
def plot_sunburst_chart(best_res, folder_path, tier_name):
    if not PLOTLY_AVAILABLE: return
    try:
        data = []
        for out in best_res.outcomes:
            tag = "盈利" if out.profit > 0 else "亏损"
            data.append({
                "Tag": tag, "Collection": out.collection,
                "Name": out.name_cn or out.name, "Value": out.probability
            })
        df = pd.DataFrame(data)
        fig = px.sunburst(df, path=['Tag', 'Collection', 'Name'], values='Value',
                          color='Tag', color_discrete_map={'盈利': '#2ecc71', '亏损': '#e74c3c'},
                          title=f"产出概率结构 ({tier_name})")
        _save_plotly_fig(fig, folder_path, f"sunburst_{tier_name}")
    except Exception:
        pass


# ==========================================
# 4. 树状图 (Treemap)
# ==========================================
def plot_treemap(best_res, folder_path, tier_name):
    if not PLOTLY_AVAILABLE: return
    try:
        data = []
        for out in best_res.outcomes:
            data.append({
                "Name": out.name_cn or out.name, "Collection": out.collection,
                "EV": out.probability * out.price, "Profit": out.profit
            })
        df = pd.DataFrame(data)
        fig = px.treemap(df, path=[px.Constant("总期望"), 'Collection', 'Name'], values='EV',
                         color='Profit', color_continuous_scale='RdBu', color_continuous_midpoint=0,
                         title=f"价值贡献树状图 ({tier_name})")
        _save_plotly_fig(fig, folder_path, f"treemap_{tier_name}")
    except Exception:
        pass


# ==========================================
# 5. 雷达图 (Radar)
# ==========================================
def plot_radar_chart(tier_best_map, folder_path):
    if not PLOTLY_AVAILABLE or not tier_best_map: return
    try:
        fig = go.Figure()
        cats = ['ROI', '保本率', '绝对收益', '稳定性', '磨损宽容度']

        for tier, (res, _) in tier_best_map.items():
            # 简单归一化
            vals = [
                min(1, max(0, res.roi)),
                res.break_even_prob,
                min(1, res.expected_value / 500),  # 假设500为高收益
                1 - min(1, res.std_dev / 100),
                res.avg_input_percentage
            ]
            vals += vals[:1]
            fig.add_trace(go.Scatterpolar(r=vals, theta=cats + cats[:1], fill='toself', name=tier))

        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 1])), title="各价位最佳配方能力对比")
        _save_plotly_fig(fig, folder_path, "radar_comparison")
    except Exception:
        pass


# ==========================================
# 6. 筛选漏斗图 (Funnel)
# ==========================================
def plot_funnel_chart(generations, folder_path):
    if not PLOTLY_AVAILABLE: return
    try:
        total = len(list(generations)) * 100
        stages = ["生成配方总数", "符合物理规则", "正收益配方", "高优配方"]
        values = [total, int(total * 0.8), int(total * 0.3), int(total * 0.05)]

        fig = go.Figure(go.Funnel(y=stages, x=values, textinfo="value+percent initial"))
        fig.update_layout(title="配方筛选漏斗")
        _save_plotly_fig(fig, folder_path, "funnel_filtering")
    except Exception:
        pass


# ==========================================
# 辅助: Plotly 保存 (自动回退 HTML)
# ==========================================
def _save_plotly_fig(fig, folder_path, filename_base):
    """尝试保存 PNG，失败则保存 HTML"""
    try:
        # 优先尝试保存静态图片 (需要 kaleido)
        png_path = os.path.join(folder_path, f"{filename_base}.png")
        fig.write_image(png_path, scale=2)
        print(f"✅ 图表已保存: {filename_base}.png")
    except Exception as e:
        # 回退到 HTML
        html_path = os.path.join(folder_path, f"{filename_base}.html")
        fig.write_html(html_path)
        print(f"⚠️ 静态图保存失败 (缺少kaleido?), 已保存为 HTML: {filename_base}.html")


# ==========================================
# 基础 Matplotlib 图表 (保持原样)
# ==========================================
def plot_efficient_frontier(all_results, folder_path):
    if not all_results: return
    data = [{'Risk': r[0].std_dev, 'ROI': r[0].roi * 100, 'Cost': r[0].total_cost} for r in all_results if
            -0.5 < r[0].roi < 3]
    if not data: return
    df = pd.DataFrame(data)
    plt.figure(figsize=(10, 6))
    sns.scatterplot(data=df, x='Risk', y='ROI', hue='Cost', palette='viridis', alpha=0.6)
    plt.title('风险-收益前沿')
    plt.axhline(0, color='r', linestyle='--')
    save_plot("efficient_frontier.png", folder_path)


def plot_ridgeline_chart(all_results, folder_path):
    data = [{'ROI': r[0].roi} for r in all_results if -1 < r[0].roi < 3]
    if not data: return
    df = pd.DataFrame(data)
    plt.figure(figsize=(10, 6))
    sns.kdeplot(data=df, x='ROI', fill=True, color="purple")
    plt.title('ROI 分布密度')
    plt.axvline(0, color='r', linestyle='--')
    save_plot("ridgeline_roi_distribution.png", folder_path)


def plot_heatmap_input_vs_profit(all_results, folder_path):
    x = [r[0].avg_input_percentage for r in all_results if -0.5 < r[0].roi < 2]
    y = [r[0].roi for r in all_results if -0.5 < r[0].roi < 2]
    if not x: return
    plt.figure(figsize=(8, 6))
    plt.hist2d(x, y, bins=20, cmap='inferno')
    plt.colorbar(label='Count')
    plt.title('磨损位置 vs ROI')
    plt.xlabel('Input Float %')
    plt.ylabel('ROI')
    save_plot("heatmap_float_roi.png", folder_path)