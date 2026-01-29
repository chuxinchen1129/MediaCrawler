#!/usr/bin/env python3
"""
左点小红书数据清洗和分析脚本

功能：
1. 数据概览和清洗
2. 过滤过去一年的笔记
3. 过滤点赞数 >= 50 的笔记
4. 识别发布类型（官方/KOL/普通用户）
5. 生成详细分析报告
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

def convert_chinese_number(value):
    """转换中文数字格式（如'2.4万' → 24000）"""
    if pd.isna(value):
        return 0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        value = value.strip()
        if '万' in value:
            # 处理'2.4万' → 24000
            num_part = value.replace('万', '').strip()
            try:
                return float(num_part) * 10000
            except ValueError:
                return 0
        # 处理纯数字字符串
        try:
            return float(value)
        except ValueError:
            return 0
    return 0

def load_data(file_path):
    """加载 Excel 数据"""
    print(f"正在加载数据: {file_path}")

    # 读取数据
    notes_df = pd.read_excel(file_path, sheet_name='Contents')

    print(f"✅ 数据加载完成")
    print(f"   - 笔记数: {len(notes_df)}")

    return notes_df

def clean_and_filter(notes_df):
    """清洗和过滤数据"""
    print("\n开始数据清洗和过滤...")

    # 1. 转换时间戳
    notes_df['publish_date'] = notes_df['add_time'] = notes_df['time'].apply(timestamp_to_date)

    # 2. 转换数据类型（先处理中文数字格式）
    numeric_cols = ['liked_count', 'collected_count', 'comment_count', 'share_count']
    for col in numeric_cols:
        # 先转换中文数字格式（如'2.4万' → 24000）
        notes_df[col] = notes_df[col].apply(convert_chinese_number)
        # 再确保是数值类型
        notes_df[col] = pd.to_numeric(notes_df[col], errors='coerce').fillna(0)

    # 3. 计算总热度
    notes_df['total_engagement'] = (
        notes_df['liked_count'] +
        notes_df['collected_count'] +
        notes_df['comment_count'] +
        notes_df['share_count']
    )

    # 3. 过滤条件
    # 条件1: 过去一年
    one_year_ago = datetime.now() - timedelta(days=365)
    notes_df['is_within_one_year'] = notes_df['publish_date'] >= one_year_ago

    # 条件2: 点赞数 >= 50
    notes_df['is_likes_above_50'] = notes_df['liked_count'] >= 50

    # 统计原始数据
    print(f"\n✅ 数据统计:")
    print(f"   - 原始笔记数: {len(notes_df)}")
    print(f"   - 过去一年: {notes_df['is_within_one_year'].sum()}")
    print(f"   - 点赞>=50: {notes_df['is_likes_above_50'].sum()}")
    print(f"   - 平均点赞: {notes_df['liked_count'].mean():.1f}")
    print(f"   - 平均收藏: {notes_df['collected_count'].mean():.1f}")
    print(f"   - 平均评论: {notes_df['comment_count'].mean():.1f}")

    return notes_df

def identify_publisher_type(df):
    """识别发布类型"""
    print("\n识别发布类型...")

    # 官方账号关键词
    official_keywords = ['左点', 'zdeer', '官方', '旗舰店']

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

        # 检查点赞数（高赞可能是KOL）
        if row.get('liked_count', 0) >= 500:
            return 'KOL投放'

        return '普通用户'

    df['publisher_type'] = df.apply(get_publisher_type, axis=1)

    # 统计发布类型
    type_counts = df['publisher_type'].value_counts()
    print(f"\n✅ 发布类型识别完成:")
    for pub_type, count in type_counts.items():
        print(f"   - {pub_type}: {count} 条 ({count/len(df)*100:.1f}%)")

    return df

def analyze_time_trend(df):
    """分析时间趋势"""
    print("\n分析发布时间趋势...")

    # 按月统计
    df['publish_month'] = pd.to_datetime(df['publish_date']).dt.to_period('M')
    monthly_stats = df.groupby('publish_month').agg({
        'note_id': 'count',
        'liked_count': 'mean',
        'collected_count': 'mean',
        'comment_count': 'mean',
        'total_engagement': 'mean'
    }).rename(columns={'note_id': '笔记数', 'liked_count': '平均点赞', 'collected_count': '平均收藏',
                      'comment_count': '平均评论', 'total_engagement': '平均热度'})

    print("\n✅ 月度趋势:")
    print(monthly_stats.to_string())

    return monthly_stats

def analyze_by_publisher(df):
    """按发布类型分析"""
    print("\n按发布类型分析...")

    stats = df.groupby('publisher_type').agg({
        'note_id': 'count',
        'liked_count': ['mean', 'median', 'max'],
        'collected_count': 'mean',
        'comment_count': 'mean',
        'total_engagement': 'mean'
    }).round(1)

    print("\n✅ 按发布类型统计:")
    print(stats.to_string())

    return stats

def get_top_notes(df, n=30):
    """获取热门笔记 TOP N"""
    print(f"\n获取热门笔记 TOP {n}...")

    top_df = df.nlargest(n, 'total_engagement')[[
        'title', 'liked_count', 'collected_count', 'comment_count',
        'total_engagement', 'publish_date', 'publisher_type', 'nickname'
    ]].copy()

    return top_df

def analyze_content(df):
    """分析内容特征"""
    print("\n分析内容特征...")

    # 提取关键词
    df['has_video'] = df['video_url'].notna() & (df['video_url'] != '')
    df['has_image'] = df['image_list'].notna() & (df['image_list'] != '')

    print(f"\n✅ 内容形式:")
    print(f"   - 纯图文: {(~df['has_video'] & df['has_image']).sum()} ({(~df['has_video'] & df['has_image']).sum()/len(df)*100:.1f}%)")
    print(f"   - 视频内容: {df['has_video'].sum()} ({df['has_video'].sum()/len(df)*100:.1f}%)")

    # 标题长度分析
    df['title_length'] = df['title'].str.len()
    print(f"\n✅ 标题长度:")
    print(f"   - 平均: {df['title_length'].mean():.1f} 字")
    print(f"   - 最短: {df['title_length'].min()} 字")
    print(f"   - 最长: {df['title_length'].max()} 字")

def save_results(df, top_df, stats, output_file):
    """保存结果"""
    print(f"\n保存结果到: {output_file}")

    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # 原始数据
        df.to_excel(writer, sheet_name='原始数据', index=False)

        # TOP 热门笔记
        top_df.to_excel(writer, sheet_name='TOP30热门笔记', index=False)

        # 统计摘要
        summary_data = {
            '指标': ['总笔记数', '平均点赞', '平均收藏', '平均评论', '平均热度', '最高点赞'],
            '数值': [
                len(df),
                f"{df['liked_count'].mean():.1f}",
                f"{df['collected_count'].mean():.1f}",
                f"{df['comment_count'].mean():.1f}",
                f"{df['total_engagement'].mean():.1f}",
                f"{df['liked_count'].max()}"
            ]
        }
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='统计摘要', index=False)

    print(f"✅ 结果已保存")

def main():
    """主函数"""
    print("="*60)
    print("左点小红书数据分析")
    print("="*60)

    # 1. 查找最新的数据文件
    data_dir = '/Users/echo/MediaCrawler/data/xhs/'
    xhs_files = [f for f in os.listdir(data_dir) if f.startswith('xhs_search_') and f.endswith('.xlsx')]

    if not xhs_files:
        print("\n❌ 错误: 未找到数据文件")
        return

    # 获取最新的文件
    latest_file = sorted(xhs_files)[-1]
    input_file = os.path.join(data_dir, latest_file)

    print(f"\n使用数据文件: {latest_file}")

    # 2. 加载数据
    notes_df = load_data(input_file)

    # 3. 清洗和过滤
    cleaned_df = clean_and_filter(notes_df)

    # 4. 识别发布类型
    cleaned_df = identify_publisher_type(cleaned_df)

    # 5. 时间趋势分析
    monthly_stats = analyze_time_trend(cleaned_df)

    # 6. 按发布类型分析
    publisher_stats = analyze_by_publisher(cleaned_df)

    # 7. 内容分析
    analyze_content(cleaned_df)

    # 8. 获取热门笔记
    top_df = get_top_notes(cleaned_df, n=30)

    # 9. 保存结果
    output_file = os.path.join(data_dir, f'左点小红书分析报告_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx')
    save_results(cleaned_df, top_df, publisher_stats, output_file)

    # 10. 显示 TOP 30
    print("\n" + "="*60)
    print("TOP 30 热门笔记")
    print("="*60)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', 50)
    print(top_df.to_string(index=False))

    print("\n" + "="*60)
    print("✅ 分析完成！")
    print(f"结果文件: {output_file}")
    print("="*60)

if __name__ == "__main__":
    main()
