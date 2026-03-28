#!/usr/bin/env python3
"""
数据清洗脚本 - 银饰品 白岚 小红书数据
清洗JSON数据，转换日期格式，生成Excel文件
"""

import json
import pandas as pd
from datetime import datetime
import os
import re

def load_json_data(json_file):
    """加载JSON数据"""
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"✓ 加载了 {len(data)} 条笔记数据")
    return data

def convert_timestamp(timestamp):
    """转换时间戳为可读日期"""
    if timestamp:
        # timestamp是毫秒级时间戳
        dt = datetime.fromtimestamp(timestamp / 1000)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    return ''

def extract_date_from_string(date_str):
    """从日期字符串中提取标准格式"""
    if not date_str:
        return ''

    # 处理格式如 "2023-11-16", "01-23" 等
    match = re.match(r'(\d{4})-(\d{1,2})-(\d{1,2})', date_str)
    if match:
        year, month, day = match.groups()
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"

    # 处理格式如 "01-23" (只有月日)
    match = re.match(r'(\d{1,2})-(\d{1,2})', date_str)
    if match:
        month, day = match.groups()
        # 假设是当年
        year = datetime.now().year
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"

    return date_str

def clean_data(raw_data):
    """清洗数据"""
    print("\n开始清洗数据...")

    cleaned_data = []

    for item in raw_data:
        try:
            # 基础信息
            note_id = item.get('note_id', '')
            title = item.get('title', '')
            note_type = item.get('type', '')
            desc = item.get('desc', '')

            # 用户信息
            user_id = item.get('user_id', '')
            nickname = item.get('nickname', '')
            avatar = item.get('avatar', '')

            # 互动数据
            liked_count = item.get('liked_count', '0')
            collected_count = item.get('collected_count', '0')
            comment_count = item.get('comment_count', '0')
            share_count = item.get('share_count', '0')

            # 时间处理
            timestamp = item.get('time', '')
            publish_time = convert_timestamp(timestamp)

            # 提取发布日期（从时间戳）
            if publish_time:
                publish_date = publish_time.split(' ')[0]
            else:
                publish_date = ''

            # 图片列表
            image_list = item.get('image_list', '')
            image_count = len(image_list.split(',')) if image_list else 0

            # 标签
            tag_list = item.get('tag_list', '')
            tags = tag_list.split(',') if tag_list else []

            # 笔记链接
            note_url = item.get('note_url', '')

            # 视频URL
            video_url = item.get('video_url', '')
            has_video = '是' if video_url else '否'

            cleaned_data.append({
                '笔记ID': note_id,
                '标题': title,
                '类型': note_type,
                '内容摘要': desc[:100] + '...' if len(desc) > 100 else desc,
                '用户ID': user_id,
                '昵称': nickname,
                '头像链接': avatar,
                '点赞数': int(liked_count) if liked_count.isdigit() else 0,
                '收藏数': int(collected_count) if collected_count.isdigit() else 0,
                '评论数': int(comment_count) if comment_count.isdigit() else 0,
                '分享数': int(share_count) if share_count.isdigit() else 0,
                '发布时间': publish_time,
                '发布日期': publish_date,
                '图片数量': image_count,
                '是否有视频': has_video,
                '标签数量': len(tags),
                '标签': ', '.join(tags[:5]),  # 只保留前5个标签
                '笔记链接': note_url,
                '采集时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })

        except Exception as e:
            print(f"✗ 处理笔记 {item.get('note_id', 'unknown')} 时出错: {e}")
            continue

    print(f"✓ 成功清洗 {len(cleaned_data)} 条笔记")
    return cleaned_data

def save_to_excel(data, output_file):
    """保存为Excel文件"""
    print(f"\n正在保存到 Excel: {output_file}")

    df = pd.DataFrame(data)

    # 重新排列列顺序
    columns_order = [
        '笔记ID', '标题', '类型', '发布时间', '发布日期',
        '昵称', '点赞数', '收藏数', '评论数', '分享数',
        '图片数量', '是否有视频', '标签数量', '标签', '笔记链接',
        '采集时间'
    ]

    df = df[columns_order]

    # 保存到Excel
    df.to_excel(output_file, index=False, engine='openpyxl')
    print(f"✓ Excel 文件已保存: {output_file}")

    # 生成统计信息
    print("\n数据统计:")
    print(f"  总笔记数: {len(df)}")
    print(f"  图文笔记: {len(df[df['类型'] == 'normal'])}")
    print(f"  视频笔记: {len(df[df['类型'] == 'video'])}")
    print(f"  有视频笔记: {len(df[df['是否有视频'] == '是'])}")
    print(f"  总点赞数: {df['点赞数'].sum()}")
    print(f"  总收藏数: {df['收藏数'].sum()}")
    print(f"  总评论数: {df['评论数'].sum()}")
    print(f"  平均点赞数: {df['点赞数'].mean():.1f}")
    print(f"  平均收藏数: {df['收藏数'].mean():.1f}")

    return df

def main():
    """主流程"""
    print("=" * 60)
    print("小红书数据清洗 - 银饰品 白岚")
    print("=" * 60)

    # 文件路径
    json_file = '/Users/echochen/MediaCrawler/data/xhs/json/search_contents_2026-01-31.json'
    output_file = '/Users/echochen/MediaCrawler/data/xhs/银饰品白岚_清洗数据.xlsx'

    # 检查文件是否存在
    if not os.path.exists(json_file):
        print(f"✗ 文件不存在: {json_file}")
        return

    # 1. 加载数据
    print("\n[1/4] 加载JSON数据...")
    raw_data = load_json_data(json_file)

    # 2. 清洗数据
    print("\n[2/4] 清洗数据...")
    cleaned_data = clean_data(raw_data)

    # 3. 保存Excel
    print("\n[3/4] 保存Excel文件...")
    df = save_to_excel(cleaned_data, output_file)

    # 4. 完成
    print("\n[4/4] 完成！")
    print("\n" + "=" * 60)
    print("✅ 数据清洗完成！")
    print("=" * 60)
    print(f"\n输出文件:")
    print(f"  📊 Excel: {output_file}")
    print(f"  🖼️  图片: /Users/echochen/MediaCrawler/data/xhs/images/")
    print(f"  🎬 视频: /Users/echochen/MediaCrawler/data/xhs/videos/")

if __name__ == "__main__":
    main()
