#!/usr/bin/env python3
"""
左点睡眠仪小红书数据清洗和分析脚本

功能：
1. 过滤过去一年的笔记
2. 过滤点赞数 >= 50 的笔记
3. 识别官方发布 vs KOL 投放
4. 生成分析报告
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os

def timestamp_to_date(ts):
    """将毫秒时间戳转换为日期"""
    if pd.isna(ts) or ts == 0:
        return None
    return datetime.fromtimestamp(ts / 1000)

def load_data(file_path):
    """加载 Excel 数据"""
    print(f"正在加载数据: {file_path}")

    # 读取所有 sheet
    notes_df = pd.read_excel(file_path, sheet_name='Contents')
    comments_df = pd.read_excel(file_path, sheet_name='Comments') if 'Comments' in pd.ExcelFile(file_path).sheet_names else pd.DataFrame()
    creators_df = pd.read_excel(file_path, sheet_name='Creators') if 'Creators' in pd.ExcelFile(file_path).sheet_names else pd.DataFrame()

    print(f"✅ 数据加载完成")
    print(f"   - 笔记数: {len(notes_df)}")
    print(f"   - 评论数: {len(comments_df) if not comments_df.empty else 0}")
    print(f"   - 作者数: {len(creators_df) if not creators_df.empty else 0}")

    return notes_df, comments_df, creators_df

def clean_and_filter(notes_df, creators_df):
    """清洗和过滤数据"""
    print("\n开始数据清洗和过滤...")

    # 1. 转换时间戳
    notes_df['publish_date'] = notes_df['add_time'].apply(timestamp_to_date)

    # 2. 计算总热度
    notes_df['total_engagement'] = (
        notes_df['liked_count'].fillna(0) +
        notes_df['collected_count'].fillna(0) +
        notes_df['comment_count'].fillna(0) +
        notes_df['share_count'].fillna(0)
    )

    # 3. 过滤条件
    # 条件1: 过去一年
    one_year_ago = datetime.now() - timedelta(days=365)
    notes_df['is_within_one_year'] = notes_df['publish_date'] >= one_year_ago

    # 条件2: 点赞数 >= 50
    notes_df['is_likes_above_50'] = notes_df['liked_count'] >= 50

    # 应用过滤
    filtered_df = notes_df[
        (notes_df['is_within_one_year']) &
        (notes_df['is_likes_above_50'])
    ].copy()

    print(f"\n✅ 过滤完成")
    print(f"   - 原始笔记数: {len(notes_df)}")
    print(f"   - 过滤后笔记数: {len(filtered_df)}")
    print(f"   - 过滤掉: {len(notes_df) - len(filtered_df)} 条")

    # 4. 识别发布类型（官方 vs KOL）
    filtered_df = identify_publisher_type(filtered_df)

    return filtered_df

def identify_publisher_type(df):
    """识别发布类型"""
    print("\n识别发布类型...")

    # 官方账号关键词
    official_keywords = ['官方', '左点', 'ZEROP', '悟昕']

    # 判断逻辑
    def get_publisher_type(row):
        note_id = str(row.get('note_id', ''))
        title = str(row.get('title', ''))
        desc = str(row.get('desc', ''))
        nickname = str(row.get('nickname', ''))

        # 检查是否为官方
        for keyword in official_keywords:
            if keyword in nickname or keyword in title or keyword in desc:
                return '官方发布'

        # 检查是否为 KOL（粉丝数 >= 10000）
        follower_count = row.get('follower_count', 0)
        if follower_count >= 10000:
            return 'KOL投放'

        # 检查是否有明显的广告标识
        ad_keywords = ['广告', '推广', '合作', '赞助']
        for keyword in ad_keywords:
            if keyword in title or keyword in desc:
                return 'KOL投放'

        return '普通用户'

    df['publisher_type'] = df.apply(get_publisher_type, axis=1)

    # 统计发布类型
    type_counts = df['publisher_type'].value_counts()
    print(f"✅ 发布类型识别完成")
    for pub_type, count in type_counts.items():
        print(f"   - {pub_type}: {count} 条")

    return df

def generate_statistics(df):
    """生成统计信息"""
    print("\n生成统计信息...")

    stats = {
        '总笔记数': len(df),
        '官方发布数': len(df[df['publisher_type'] == '官方发布']),
        'KOL投放数': len(df[df['publisher_type'] == 'KOL投放']),
        '普通用户数': len(df[df['publisher_type'] == '普通用户']),
        '平均点赞数': df['liked_count'].mean(),
        '平均收藏数': df['collected_count'].mean(),
        '平均评论数': df['comment_count'].mean(),
        '平均总热度': df['total_engagement'].mean(),
        '最高点赞数': df['liked_count'].max(),
        '最高总热度': df['total_engagement'].max(),
    }

    print("\n✅ 统计信息:")
    for key, value in stats.items():
        if isinstance(value, (int, float)):
            print(f"   - {key}: {value:.1f}" if isinstance(value, float) else f"   - {key}: {value}")
        else:
            print(f"   - {key}: {value}")

    return stats

def get_top_notes(df, n=20):
    """获取热门笔记 TOP N"""
    print(f"\n获取热门笔记 TOP {n}...")

    top_df = df.nlargest(n, 'total_engagement')[[
        'title', 'liked_count', 'collected_count', 'comment_count',
        'total_engagement', 'publish_date', 'publisher_type', 'nickname'
    ]].copy()

    return top_df

def analyze_time_trend(df):
    """分析时间趋势"""
    print("\n分析发布时间趋势...")

    # 按月统计
    df['publish_month'] = pd.to_datetime(df['publish_date']).dt.to_period('M')
    monthly_stats = df.groupby('publish_month').agg({
        'note_id': 'count',
        'liked_count': 'mean',
        'total_engagement': 'mean'
    }).rename(columns={'note_id': '笔记数', 'liked_count': '平均点赞', 'total_engagement': '平均热度'})

    print("\n✅ 月度趋势:")
    print(monthly_stats.to_string())

    return monthly_stats

def save_results(filtered_df, top_df, stats, output_file):
    """保存结果"""
    print(f"\n保存结果到: {output_file}")

    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # 过滤后的数据
        filtered_df.to_excel(writer, sheet_name='过滤后数据', index=False)

        # TOP 热门笔记
        top_df.to_excel(writer, sheet_name='TOP20热门笔记', index=False)

        # 统计信息
        stats_df = pd.DataFrame(list(stats.items()), columns=['指标', '数值'])
        stats_df.to_excel(writer, sheet_name='统计信息', index=False)

    print(f"✅ 结果已保存")

def main():
    """主函数"""
    print("="*60)
    print("左点睡眠仪小红书数据分析")
    print("="*60)

    # 1. 查找最新的数据文件
    data_dir = '/Users/echo/MediaCrawler/data/xhs/'
    xhs_files = [f for f in os.listdir(data_dir) if f.startswith('xhs_search_') and f.endswith('.xlsx')]

    if not xhs_files:
        print("\n❌ 错误: 未找到数据文件")
        print(f"请确保数据文件存在于: {data_dir}")
        return

    # 获取最新的文件
    latest_file = sorted(xhs_files)[-1]
    input_file = os.path.join(data_dir, latest_file)

    print(f"\n使用数据文件: {latest_file}")

    # 2. 加载数据
    notes_df, comments_df, creators_df = load_data(input_file)

    # 3. 清洗和过滤
    filtered_df = clean_and_filter(notes_df, creators_df)

    if len(filtered_df) == 0:
        print("\n❌ 没有符合条件的数据")
        return

    # 4. 生成统计信息
    stats = generate_statistics(filtered_df)

    # 5. 获取热门笔记
    top_df = get_top_notes(filtered_df, n=20)

    # 6. 分析时间趋势
    monthly_stats = analyze_time_trend(filtered_df)

    # 7. 保存结果
    output_file = os.path.join(data_dir, f'左点睡眠仪_分析结果_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx')
    save_results(filtered_df, top_df, stats, output_file)

    # 8. 显示 TOP 20
    print("\n" + "="*60)
    print("TOP 20 热门笔记")
    print("="*60)
    print(top_df.to_string(index=False))

    print("\n" + "="*60)
    print("✅ 分析完成！")
    print(f"结果文件: {output_file}")
    print("="*60)

if __name__ == "__main__":
    main()
