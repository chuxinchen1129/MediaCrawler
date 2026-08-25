#!/usr/bin/env python3
"""
左点小红书数据可视化脚本 - Plotly Express版本

功能：
1. 发布类型分布（饼图）
2. 不同发布类型的表现对比（柱状图）
3. 时间趋势分析（折线图）
4. 内容形式分布（饼图+柱状图）
5. TOP 10热门笔记（条形图）
6. 互动数据分布（箱线图）
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

def load_data(file_path):
    """加载清洗后的数据"""
    print(f"正在加载数据: {file_path}")
    df = pd.read_excel(file_path, sheet_name='原始数据')
    print(f"✅ 加载完成，共 {len(df)} 条笔记")
    return df

def plot_publisher_distribution(df):
    """1. 发布类型分布（饼图）"""
    print("\n生成发布类型分布图...")

    type_counts = df['publisher_type'].value_counts().reset_index()
    type_counts.columns = ['发布类型', '数量']

    fig = px.pie(type_counts, values='数量', names='发布类型',
                 title='左点小红书发布类型分布（总笔记数：199）',
                 color='发布类型',
                 color_discrete_map={
                     '官方发布': '#4ECDC4',
                     'KOL投放': '#FF6B6B',
                     '普通用户': '#45B7D1'
                 },
                 hole=0.3,  # 甜甜圈图
                 height=800)

    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(
        font=dict(size=16),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

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
    }).reset_index()

    # 转换为长格式
    stats_long = stats.melt(id_vars='publisher_type',
                             value_vars=['liked_count', 'collected_count', 'comment_count', 'total_engagement'],
                             var_name='指标', value_name='平均值')

    # 中文映射
    name_map = {
        'liked_count': '平均点赞数',
        'collected_count': '平均收藏数',
        'comment_count': '平均评论数',
        'total_engagement': '平均热度'
    }
    stats_long['指标'] = stats_long['指标'].map(name_map)

    fig = px.bar(stats_long, x='publisher_type', y='平均值',
                 color='publisher_type',
                 facet_col='指标',
                 title='不同发布类型的表现对比',
                 color_discrete_map={
                     '官方发布': '#4ECDC4',
                     'KOL投放': '#FF6B6B',
                     '普通用户': '#45B7D1'
                 },
                 height=600,
                 text='平均值')

    fig.update_traces(texttemplate='%{y:.1f}')
    fig.update_layout(
        font=dict(size=14),
        xaxis_title_text='发布类型',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig.for_each_annotation(lambda a: a.update(text=a.text.split('=')[-1]))

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
    monthly_recent = monthly[monthly['publish_month'] >= '2022-01']

    # 创建子图
    fig = make_subplots(rows=2, cols=1,
                        subplot_titles=('每月发布笔记数量', '平均互动趋势'),
                        vertical_spacing=0.15)

    # 子图1：笔记数量趋势
    fig.add_trace(
        go.Scatter(x=monthly_recent['publish_month'],
                   y=monthly_recent['note_id'],
                   mode='lines+markers',
                   name='笔记数量',
                   line=dict(color='#FF6B6B', width=3),
                   marker=dict(size=8)),
        row=1, col=1
    )

    # 标注峰值
    max_idx = monthly_recent['note_id'].idxmax() - monthly_recent.index[0]
    max_val = monthly_recent['note_id'].max()
    max_month = monthly_recent.loc[max_idx, 'publish_month']
    fig.add_annotation(
        text=f'峰值: {max_val}条<br>{max_month}',
        x=max_month, y=max_val,
        showarrow=True,
        arrowhead=1,
        arrowcolor='red',
        arrowsize=2,
        arrowwidth=2,
        ax=0,
        ay=40,
        font=dict(size=12, color='red'),
        row=1, col=1
    )

    # 子图2：平均热度趋势
    fig.add_trace(
        go.Scatter(x=monthly_recent['publish_month'],
                   y=monthly_recent['liked_count'],
                   mode='lines+markers',
                   name='平均点赞',
                   line=dict(color='#4ECDC4', width=3),
                   marker=dict(size=8)),
        row=2, col=1
    )

    fig.add_trace(
        go.Scatter(x=monthly_recent['publish_month'],
                   y=monthly_recent['total_engagement'],
                   mode='lines+markers',
                   name='平均热度',
                   line=dict(color='#45B7D1', width=3),
                   marker=dict(size=8, symbol='x')),
        row=2, col=1
    )

    fig.update_layout(
        height=1000,
        title_text='左点小红书发布时间趋势（2022-2026）',
        title_font_size=20,
        title_x=0.5,
        font=dict(size=14),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    fig.update_xaxes(title_text="月份")
    fig.update_yaxes(title_text="笔记数量", row=1, col=1)
    fig.update_yaxes(title_text="数值", row=2, col=1)

    return fig

def plot_content_type(df):
    """4. 内容形式分析（饼图+柱状图）"""
    print("生成内容形式分析图...")

    # 统计内容形式
    df['has_video'] = df['video_url'].notna() & (df['video_url'] != '')
    df['has_image'] = df['image_list'].notna() & (df['image_list'] != '')

    content_counts = {
        '内容形式': ['纯图文', '视频内容'],
        '数量': [
            ((~df['has_video']) & df['has_image']).sum(),
            df['has_video'].sum()
        ]
    }
    content_counts_df = pd.DataFrame(content_counts)

    # 统计不同发布类型的内容形式
    video_by_type = df.groupby('publisher_type')['has_video'].sum()
    image_by_type = df.groupby('publisher_type').apply(
        lambda x: ((~x['has_video']) & x['has_image']).sum(),
        include_groups=False
    )

    content_by_type = pd.DataFrame({
        '视频': video_by_type,
        '纯图文': image_by_type
    }).reset_index()
    content_by_type.columns = ['发布类型', '视频', '纯图文']

    # 创建子图
    fig = make_subplots(rows=1, cols=2,
                        subplot_titles=('总体内容形式分布', '不同发布类型的内容形式'),
                        specs=[[{'type': 'domain'}, {'type': 'xy'}]])

    # 左图：总体分布饼图
    fig.add_trace(
        go.Pie(labels=content_counts_df['内容形式'],
                values=content_counts_df['数量'],
                name='总体分布',
                hole=0.3,
                marker=dict(colors=['#FFD93D', '#6BCB77'])),
        row=1, col=1
    )

    # 右图：按发布类型分组
    fig.add_trace(
        go.Bar(name='视频', x=content_by_type['发布类型'], y=content_by_type['视频'],
               marker=dict(color='#FFD93D')),
        row=1, col=2
    )
    fig.add_trace(
        go.Bar(name='纯图文', x=content_by_type['发布类型'], y=content_by_type['纯图文'],
               marker=dict(color='#6BCB77')),
        row=1, col=2
    )

    fig.update_layout(
        height=700,
        title_text='内容形式分析',
        title_font_size=20,
        title_x=0.5,
        font=dict(size=14),
        showlegend=True,
        barmode='stack'
    )

    fig.update_yaxes(title_text="笔记数量")

    return fig

def plot_top_notes(df):
    """5. TOP 10热门笔记（条形图）"""
    print("生成TOP 10热门笔记图...")

    top10 = df.nlargest(10, 'total_engagement')[['title', 'total_engagement', 'publisher_type', 'liked_count']].copy()
    top10['title_short'] = top10['title'].str[:25]

    fig = px.bar(top10, x='total_engagement', y='title_short',
                 orientation='h',
                 color='publisher_type',
                 title='TOP 10 热门笔记',
                 color_discrete_map={
                     '官方发布': '#4ECDC4',
                     'KOL投放': '#FF6B6B',
                     '普通用户': '#95E1D3'
                 },
                 height=800,
                 text='total_engagement')

    fig.update_traces(texttemplate='%{x:,.0f}')
    fig.update_layout(
        font=dict(size=14),
        xaxis_title='总热度（点赞+收藏+评论+分享）',
        yaxis_title='标题',
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    return fig

def plot_engagement_distribution(df):
    """6. 互动数据分布（箱线图）"""
    print("生成互动数据分布图...")

    metrics = ['liked_count', 'collected_count', 'comment_count', 'total_engagement']
    metric_names = ['点赞数', '收藏数', '评论数', '总热度']

    # 创建子图
    fig = make_subplots(rows=2, cols=2,
                        subplot_titles=metric_names,
                        vertical_spacing=0.15)

    for idx, (metric, metric_name) in enumerate(zip(metrics, metric_names)):
        row = idx // 2 + 1
        col = idx % 2 + 1

        for pub_type in ['KOL投放', '官方发布', '普通用户']:
            data = df[df['publisher_type'] == pub_type][metric]

            color_map = {
                'KOL投放': '#FF6B6B',
                '官方发布': '#4ECDC4',
                '普通用户': '#95E1D3'
            }

            fig.add_trace(
                go.Box(y=data, name=pub_type,
                       marker=dict(color=color_map[pub_type]),
                       boxpoints='outliers'),
                row=row, col=col
            )

    fig.update_layout(
        height=1000,
        title_text='互动数据分布分析',
        title_font_size=20,
        title_x=0.5,
        font=dict(size=12),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    return fig

def save_all_figures(figs, output_dir):
    """保存所有图表"""
    print(f"\n保存图表到: {output_dir}")

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    fig_names = [
        'plotly_1_发布类型分布.html',
        'plotly_1_发布类型分布.png',
        'plotly_2_发布类型表现对比.html',
        'plotly_2_发布类型表现对比.png',
        'plotly_3_时间趋势分析.html',
        'plotly_3_时间趋势分析.png',
        'plotly_4_内容形式分析.html',
        'plotly_4_内容形式分析.png',
        'plotly_5_TOP10热门笔记.html',
        'plotly_5_TOP10热门笔记.png',
        'plotly_6_互动数据分布.html',
        'plotly_6_互动数据分布.png'
    ]

    for fig, name in zip(figs, fig_names):
        file_path = os.path.join(output_dir, name)

        if name.endswith('.html'):
            fig.write_html(file_path)
            print(f"   ✅ {name} (交互式)")
        else:
            fig.write_image(file_path, scale=2, engine='kaleido')
            print(f"   ✅ {name} (静态)")

    print(f"\n所有图表已保存到: {output_dir}")

def main():
    """主函数"""
    print("="*60)
    print("左点小红书数据可视化 - Plotly Express版本")
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

    # 图2: 发布类型表现对比
    fig2 = plot_publisher_performance(df)
    figures.append(fig2)

    # 图3: 时间趋势
    fig3 = plot_time_trend(df)
    figures.append(fig3)

    # 图4: 内容形式
    fig4 = plot_content_type(df)
    figures.append(fig4)

    # 图5: TOP 10
    fig5 = plot_top_notes(df)
    figures.append(fig5)

    # 图6: 互动数据分布
    fig6 = plot_engagement_distribution(df)
    figures.append(fig6)

    # 3. 保存图表
    output_dir = os.path.join(data_dir, 'plotly可视化图表')
    save_all_figures(figures, output_dir)

    print("\n" + "="*60)
    print("✅ 可视化完成！")
    print(f"图表位置: {output_dir}")
    print("\n💡 特点:")
    print("   - 交互式HTML图表（可在浏览器中查看）")
    print("   - 高分辨率PNG图表（适合报告）")
    print("   - 中文完美显示，无需配置字体")
    print("   - 支持缩放、悬停查看详情")
    print("="*60)

if __name__ == "__main__":
    main()
