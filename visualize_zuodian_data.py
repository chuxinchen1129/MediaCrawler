#!/usr/bin/env python3
"""
左点小红书数据可视化脚本

功能：
1. 发布类型分布（饼图）
2. 不同发布类型的表现对比（柱状图）
3. 时间趋势分析（折线图）
4. 内容形式分布（饼图）
5. TOP 10热门笔记（条形图）
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns
from datetime import datetime
import os

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 设置图表风格
sns.set_style("whitegrid")
sns.set_palette("husl")

def load_data(file_path):
    """加载清洗后的数据"""
    print(f"正在加载数据: {file_path}")
    df = pd.read_excel(file_path, sheet_name='原始数据')
    print(f"✅ 加载完成，共 {len(df)} 条笔记")
    return df

def plot_publisher_distribution(df):
    """1. 发布类型分布（饼图）"""
    print("\n生成发布类型分布图...")

    type_counts = df['publisher_type'].value_counts()

    fig, ax = plt.subplots(figsize=(10, 8))
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1']
    wedges, texts, autotexts = ax.pie(
        type_counts,
        labels=type_counts.index,
        autopct='%1.1f%%',
        colors=colors,
        startangle=90,
        textprops={'fontsize': 14, 'weight': 'bold'}
    )

    # 设置标题
    ax.set_title('左点小红书发布类型分布\n（总笔记数：199）', fontsize=18, weight='bold', pad=20)

    # 添加图例
    ax.legend(wedges, [f'{l}: {v}条 ({v/len(df)*100:.1f}%)' for l, v in type_counts.items()],
              loc='center left', bbox_to_anchor=(1, 0.5), fontsize=12)

    plt.tight_layout()
    return fig

def plot_publisher_performance(df):
    """2. 不同发布类型的表现对比（柱状图）"""
    print("生成发布类型表现对比图...")

    # 计算各类型平均值
    stats = df.groupby('publisher_type').agg({
        'liked_count': 'mean',
        'collected_count': 'mean',
        'comment_count': 'mean',
        'total_engagement': 'mean'
    }).round(1)

    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('不同发布类型的表现对比', fontsize=18, weight='bold', y=0.995)

    metrics = ['liked_count', 'collected_count', 'comment_count', 'total_engagement']
    metric_names = ['平均点赞数', '平均收藏数', '平均评论数', '平均热度']
    colors_map = ['#FF6B6B', '#4ECDC4', '#45B7D1']

    for idx, (metric, metric_name) in enumerate(zip(metrics, metric_names)):
        ax = axes[idx // 2, idx % 2]

        values = stats[metric]
        bars = ax.bar(range(len(values)), values, color=colors_map[:len(values)])

        # 设置标签
        ax.set_xticks(range(len(values)))
        ax.set_xticklabels(values.index, fontsize=12, weight='bold')
        ax.set_ylabel('数值', fontsize=12)
        ax.set_title(metric_name, fontsize=14, weight='bold', pad=10)

        # 添加数值标签
        for i, (bar, value) in enumerate(zip(bars, values)):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    f'{value:.1f}',
                    ha='center', va='bottom', fontsize=11, weight='bold')

        ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    return fig

def plot_time_trend(df):
    """3. 时间趋势分析（折线图）"""
    print("生成时间趋势图...")

    # 按月统计
    df['publish_month'] = pd.to_datetime(df['publish_date']).dt.to_period('M')
    monthly = df.groupby('publish_month').agg({
        'note_id': 'count',
        'liked_count': 'mean',
        'total_engagement': 'mean'
    }).reset_index()
    monthly['publish_month'] = monthly['publish_month'].astype(str)

    # 筛选2022年以后的数据
    monthly_recent = monthly[monthly['publish_month'] >= '2022-01']

    fig, axes = plt.subplots(2, 1, figsize=(16, 10))
    fig.suptitle('左点小红书发布时间趋势（2022-2026）', fontsize=18, weight='bold', y=0.995)

    # 子图1：笔记数量趋势
    ax1 = axes[0]
    ax1.plot(range(len(monthly_recent)), monthly_recent['note_id'],
             marker='o', markersize=6, linewidth=2.5, color='#FF6B6B')
    ax1.fill_between(range(len(monthly_recent)), monthly_recent['note_id'], alpha=0.3, color='#FF6B6B')
    ax1.set_xticks(range(0, len(monthly_recent), 3))
    ax1.set_xticklabels(monthly_recent['publish_month'][::3], rotation=45, ha='right')
    ax1.set_ylabel('笔记数量', fontsize=12, weight='bold')
    ax1.set_title('每月发布笔记数量', fontsize=14, weight='bold', pad=10)
    ax1.grid(alpha=0.3)

    # 标注峰值
    max_idx = monthly_recent['note_id'].idxmax() - monthly_recent.index[0]
    max_val = monthly_recent['note_id'].max()
    max_month = monthly_recent.loc[max_idx, 'publish_month']
    ax1.annotate(f'峰值: {max_val}条\n{max_month}',
                xy=(max_idx, max_val),
                xytext=(max_idx+2, max_val+10),
                arrowprops=dict(arrowstyle='->', color='red', lw=2),
                fontsize=10, weight='bold',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.7))

    # 子图2：平均热度趋势
    ax2 = axes[1]
    ax2.plot(range(len(monthly_recent)), monthly_recent['liked_count'],
             marker='s', markersize=6, linewidth=2.5, color='#4ECDC4', label='平均点赞')
    ax2.plot(range(len(monthly_recent)), monthly_recent['total_engagement'],
             marker='^', markersize=6, linewidth=2.5, color='#45B7D1', label='平均热度')
    ax2.set_xticks(range(0, len(monthly_recent), 3))
    ax2.set_xticklabels(monthly_recent['publish_month'][::3], rotation=45, ha='right')
    ax2.set_ylabel('数值', fontsize=12, weight='bold')
    ax2.set_title('平均互动趋势', fontsize=14, weight='bold', pad=10)
    ax2.legend(fontsize=12, loc='upper left')
    ax2.grid(alpha=0.3)

    plt.tight_layout()
    return fig

def plot_content_type(df):
    """4. 内容形式分布（饼图+柱状图）"""
    print("生成内容形式分析图...")

    # 统计内容形式
    df['has_video'] = df['video_url'].notna() & (df['video_url'] != '')
    df['has_image'] = df['image_list'].notna() & (df['image_list'] != '')

    content_counts = {
        '纯图文': ((~df['has_video']) & df['has_image']).sum(),
        '视频内容': df['has_video'].sum()
    }

    # 统计不同发布类型的内容形式
    video_by_type = df.groupby('publisher_type')['has_video'].sum()
    image_by_type = df.groupby('publisher_type').apply(
        lambda x: ((~x['has_video']) & x['has_image']).sum(),
        include_groups=False
    )

    content_by_type = pd.DataFrame({
        '视频': video_by_type,
        '纯图文': image_by_type
    })

    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    fig.suptitle('内容形式分析', fontsize=18, weight='bold')

    # 左图：总体分布饼图
    ax1 = axes[0]
    colors = ['#FFD93D', '#6BCB77']
    wedges, texts, autotexts = ax1.pie(
        content_counts.values(),
        labels=content_counts.keys(),
        autopct='%1.1f%%',
        colors=colors,
        startangle=90,
        textprops={'fontsize': 14, 'weight': 'bold'}
    )
    ax1.set_title('总体内容形式分布', fontsize=14, weight='bold', pad=15)

    # 右图：按发布类型分组
    ax2 = axes[1]
    content_by_type.plot(kind='bar', ax=ax2, color=['#FFD93D', '#6BCB77'], rot=0, fontsize=11)
    ax2.set_title('不同发布类型的内容形式', fontsize=14, weight='bold', pad=15)
    ax2.set_ylabel('笔记数量', fontsize=12, weight='bold')
    ax2.set_xlabel('发布类型', fontsize=12, weight='bold')
    ax2.legend(title='内容形式', fontsize=11)
    ax2.grid(axis='y', alpha=0.3)

    # 添加数值标签
    for p in ax2.patches:
        ax2.annotate(f'{int(p.get_height())}',
                    (p.get_x() + p.get_width()/2., p.get_height()),
                    ha='center', va='bottom', fontsize=11, weight='bold')

    plt.tight_layout()
    return fig

def plot_top_notes(df):
    """5. TOP 10热门笔记（横向条形图）"""
    print("生成TOP 10热门笔记图...")

    top10 = df.nlargest(10, 'total_engagement')[['title', 'total_engagement', 'publisher_type', 'liked_count']].copy()
    top10['title_short'] = top10['title'].str[:30] + '...'

    # 截断过长的标题
    top10['title_display'] = top10['title'].apply(lambda x: x[:25] + '...' if len(x) > 25 else x)

    fig, ax = plt.subplots(figsize=(16, 10))

    # 按热度降序排列（最高在上面）
    y_pos = range(len(top10))
    colors = ['#FF6B6B' if t == 'KOL投放' else '#4ECDC4' if t == '官方发布' else '#95E1D3'
               for t in top10['publisher_type']]

    bars = ax.barh(y_pos, top10['total_engagement'], color=colors, alpha=0.8)

    # 设置标签
    ax.set_yticks(y_pos)
    ax.set_yticklabels(top10['title_display'], fontsize=12)
    ax.set_xlabel('总热度（点赞+收藏+评论+分享）', fontsize=13, weight='bold')
    ax.set_title('TOP 10 热门笔记', fontsize=16, weight='bold', pad=15)

    # 添加数值标签
    for i, (bar, value) in enumerate(zip(bars, top10['total_engagement'])):
        width = bar.get_width()
        ax.text(width + 200, bar.get_y() + bar.get_height()/2,
                f'{int(value):,}',
                ha='left', va='center', fontsize=11, weight='bold')

    # 添加图例
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#FF6B6B', label='KOL投放'),
        Patch(facecolor='#4ECDC4', label='官方发布'),
        Patch(facecolor='#95E1D3', label='普通用户')
    ]
    ax.legend(handles=legend_elements, loc='lower right', fontsize=12)

    ax.grid(axis='x', alpha=0.3)
    ax.invert_yaxis()  # 最高热度在最上面

    plt.tight_layout()
    return fig

def plot_engagement_distribution(df):
    """6. 互动数据分布（箱线图）"""
    print("生成互动数据分布图...")

    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('互动数据分布分析', fontsize=18, weight='bold', y=0.995)

    metrics = ['liked_count', 'collected_count', 'comment_count', 'total_engagement']
    metric_names = ['点赞数', '收藏数', '评论数', '总热度']

    for idx, (metric, metric_name) in enumerate(zip(metrics, metric_names)):
        ax = axes[idx // 2, idx % 2]

        # 按发布类型分组
        data_to_plot = [df[df['publisher_type'] == t][metric].values
                         for t in ['KOL投放', '官方发布', '普通用户']]

        bp = ax.boxplot(data_to_plot, labels=['KOL投放', '官方发布', '普通用户'],
                       patch_artist=True, widths=0.6)

        # 设置颜色
        colors_patch = ['#FF6B6B', '#4ECDC4', '#95E1D3']
        for patch, color in zip(bp['boxes'], colors_patch):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)

        ax.set_ylabel('数值', fontsize=11, weight='bold')
        ax.set_title(metric_name, fontsize=13, weight='bold', pad=10)
        ax.grid(axis='y', alpha=0.3)

        # 添加均值线
        means = [df[df['publisher_type'] == t][metric].mean()
                 for t in ['KOL投放', '官方发布', '普通用户']]
        ax.plot(range(1, 4), means, 'r--', marker='D', markersize=8, linewidth=2, label='均值')
        if idx == 0:
            ax.legend(fontsize=10)

    plt.tight_layout()
    return fig

def save_all_figures(figures, output_dir):
    """保存所有图表"""
    print(f"\n保存图表到: {output_dir}")

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    fig_names = [
        '1_发布类型分布.png',
        '2_发布类型表现对比.png',
        '3_时间趋势分析.png',
        '4_内容形式分析.png',
        '5_TOP10热门笔记.png',
        '6_互动数据分布.png'
    ]

    for fig, name in zip(figures, fig_names):
        file_path = os.path.join(output_dir, name)
        fig.savefig(file_path, dpi=300, bbox_inches='tight')
        print(f"   ✅ {name}")

    print(f"\n所有图表已保存到: {output_dir}")

def main():
    """主函数"""
    print("="*60)
    print("左点小红书数据可视化")
    print("="*60)

    # 1. 加载数据
    data_dir = '/Users/echo/MediaCrawler/data/xhs/'
    input_file = os.path.join(data_dir, '左点小红书分析报告_20260129_144110.xlsx')

    if not os.path.exists(input_file):
        print(f"\n❌ 错误: 文件不存在 {input_file}")
        return

    df = load_data(input_file)

    # 2. 生成所有图表
    print("\n开始生成可视化图表...")

    figures = []

    # 图1: 发布类型分布
    fig1 = plot_publisher_distribution(df)
    figures.append(fig1)
    plt.close(fig1)

    # 图2: 发布类型表现对比
    fig2 = plot_publisher_performance(df)
    figures.append(fig2)
    plt.close(fig2)

    # 图3: 时间趋势
    fig3 = plot_time_trend(df)
    figures.append(fig3)
    plt.close(fig3)

    # 图4: 内容形式
    fig4 = plot_content_type(df)
    figures.append(fig4)
    plt.close(fig4)

    # 图5: TOP 10
    fig5 = plot_top_notes(df)
    figures.append(fig5)
    plt.close(fig5)

    # 图6: 互动数据分布
    fig6 = plot_engagement_distribution(df)
    figures.append(fig6)
    plt.close(fig6)

    # 3. 保存图表
    output_dir = os.path.join(data_dir, '可视化图表')
    save_all_figures(figures, output_dir)

    print("\n" + "="*60)
    print("✅ 可视化完成！")
    print(f"图表位置: {output_dir}")
    print("="*60)

if __name__ == "__main__":
    main()
