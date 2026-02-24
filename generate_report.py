#!/usr/bin/env python3
"""
数据分析报告 - 银饰品 白岚 小红书数据
生成详细的数据分析报告
"""

import pandas as pd
import json
from datetime import datetime
from collections import Counter

def load_data():
    """加载清洗后的Excel数据"""
    excel_file = '/Users/echochen/MediaCrawler/data/xhs/银饰品白岚_清洗数据.xlsx'
    df = pd.read_excel(excel_file)
    print(f"✓ 加载了 {len(df)} 条数据")
    # 添加"内容摘要"列，如果不存在
    if '内容摘要' not in df.columns:
        df['内容摘要'] = df['内容摘要'] if '内容摘要' in df.columns else ''
    return df

def analyze_brand_mentions(df):
    """分析品牌提及情况"""
    print("\n" + "="*60)
    print("品牌提及分析")
    print("="*60)

    # 统计标题中包含"白岚"的笔记
    brand_mentions = df[df['标题'].str.contains('白岚', na=False)]
    print(f"标题中直接提及'白岚'的笔记: {len(brand_mentions)} 条")

    # 统计标签中包含"白岚"的笔记
    tag_mentions = df[df['标签'].str.contains('白岚', na=False)]
    print(f"标签中包含'白岚'的笔记: {len(tag_mentions)} 条")

    # 统计内容中包含"白岚"的笔记
    desc_mentions = df[df['内容摘要'].str.contains('白岚', na=False)]
    print(f"内容摘要中包含'白岚'的笔记: {len(desc_mentions)} 条")

    # 任何位置提及白岚
    any_mention = df[
        df['标题'].str.contains('白岚', na=False) |
        df['标签'].str.contains('白岚', na=False) |
        df['内容摘要'].str.contains('白岚', na=False)
    ]
    print(f"任何位置提及'白岚'的笔记: {len(any_mention)} 条 ({len(any_mention)/len(df)*100:.1f}%)")

    return any_mention

def analyze_engagement(df):
    """分析互动数据"""
    print("\n" + "="*60)
    print("互动数据分析")
    print("="*60)

    # 点赞数分布
    print("\n点赞数分布:")
    print(f"  平均点赞数: {df['点赞数'].mean():.1f}")
    print(f"  中位数点赞数: {df['点赞数'].median():.0f}")
    print(f"  最高点赞数: {df['点赞数'].max()}")
    print(f"  最低点赞数: {df['点赞数'].min()}")

    # 高互动笔记（点赞>1000）
    high_engagement = df[df['点赞数'] > 1000]
    print(f"\n高互动笔记（点赞>1000）: {len(high_engagement)} 条")
    if len(high_engagement) > 0:
        print("  TOP 5 高互动笔记:")
        top_liked = high_engagement.nlargest(5, '点赞数')[['标题', '点赞数', '收藏数', '评论数']]
        for idx, row in top_liked.iterrows():
            print(f"    {row['标题'][:40]}... - {row['点赞数']}赞")

    # 收藏数分布
    print(f"\n收藏数分布:")
    print(f"  平均收藏数: {df['收藏数'].mean():.1f}")
    print(f"  最高收藏数: {df['收藏数'].max()}")

def analyze_content_types(df):
    """分析内容类型"""
    print("\n" + "="*60)
    print("内容类型分析")
    print("="*60)

    # 笔记类型
    type_counts = df['类型'].value_counts()
    print(f"\n笔记类型分布:")
    for note_type, count in type_counts.items():
        print(f"  {note_type}: {count} 条 ({count/len(df)*100:.1f}%)")

    # 视频内容
    has_video = df[df['是否有视频'] == '是']
    print(f"\n包含视频的笔记: {len(has_video)} 条 ({len(has_video)/len(df)*100:.1f}%)")

    # 图片数量分布
    print(f"\n图片数量分布:")
    print(f"  平均每条笔记图片数: {df['图片数量'].mean():.1f}")
    print(f"  最多图片数: {df['图片数量'].max()}")

def analyze_time_distribution(df):
    """分析时间分布"""
    print("\n" + "="*60)
    print("时间分布分析")
    print("="*60)

    # 转换发布日期
    df['发布日期'] = pd.to_datetime(df['发布日期'], errors='coerce')

    # 按日期排序
    df_sorted = df.sort_values('发布日期', ascending=False)

    print(f"\n时间跨度:")
    if df_sorted['发布日期'].notna().any():
        print(f"  最早发布: {df_sorted['发布日期'].min().strftime('%Y-%m-%d')}")
        print(f"  最新发布: {df_sorted['发布日期'].max().strftime('%Y-%Y-%m-%d')}")

    # 按年份统计
    df['年份'] = df['发布日期'].dt.year
    year_counts = df['年份'].value_counts().sort_index()
    print(f"\n按年份分布:")
    for year, count in year_counts.items():
        print(f"  {int(year)}年: {count} 条")

def analyze_creators(df):
    """分析创作者"""
    print("\n" + "="*60)
    print("创作者分析")
    print("="*60)

    # Top创作者（按笔记数量）
    creator_counts = df['昵称'].value_counts()
    print(f"\n活跃创作者（TOP 10）:")
    for i, (creator, count) in enumerate(creator_counts.head(10).items(), 1):
        # 获取该创作者的总互动数
        creator_data = df[df['昵称'] == creator]
        total_likes = creator_data['点赞数'].sum()
        print(f"  {i}. {creator}: {count} 条笔记 (总点赞 {total_likes:,})")

def generate_markdown_report(df, output_file):
    """生成Markdown报告"""
    print(f"\n正在生成报告...")

    report = f"""# 银饰品 白岚 - 小红书数据分析报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**数据来源**: 小红书
**关键词**: 银饰品 白岚

---

## 📊 数据概览

### 采集统计
- **总笔记数**: {len(df)} 条
- **图文笔记**: {len(df[df['类型'] == 'normal'])} 条
- **视频笔记**: {len(df[df['类型'] == 'video'])} 条
- **包含视频**: {len(df[df['是否有视频'] == '是'])} 条

### 互动数据汇总
- **总点赞数**: {df['点赞数'].sum():,}
- **总收藏数**: {df['收藏数'].sum():,}
- **总评论数**: {df['评论数'].sum():,}
- **总分享数**: {df['分享数'].sum():,}

### 平均数据
- **平均点赞数**: {df['点赞数'].mean():.1f}
- **平均收藏数**: {df['收藏数'].mean():.1f}
- **平均评论数**: {df['评论数'].mean():.1f}

---

## 📈 内容分析

### 笔记类型分布
"""

    # 笔记类型
    type_counts = df['类型'].value_counts()
    for note_type, count in type_counts.items():
        report += f"- **{note_type}**: {count} 条 ({count/len(df)*100:.1f}%)\n"

    report += f"""
### 媒体内容
- **包含图片的笔记**: {len(df[df['图片数量'] > 0])} 条
- **包含视频的笔记**: {len(df[df['是否有视频'] == '是'])} 条
- **平均图片数**: {df['图片数量'].mean():.1f} 张/条

---

## 🔥 热门内容

### 高互动笔记（点赞TOP 10）
"""

    # TOP 10 点赞笔记
    top_liked = df.nlargest(10, '点赞数')
    for i, row in top_liked.iterrows():
        report += f"\n{i+1}. **{row['标题'][:50]}...**\n"
        report += f"   - 点赞: {row['点赞数']:,} | 收藏: {row['收藏数']:,} | 评论: {row['评论数']:,}\n"
        report += f"   - 作者: {row['昵称']}\n"

    report += f"""
---

## 👥 创作者分析

### 活跃创作者（笔记数量 TOP 10）
"""

    # Top创作者
    creator_counts = df['昵称'].value_counts().head(10)
    for i, (creator, count) in creator_counts.items():
        creator_data = df[df['昵称'] == creator]
        total_likes = creator_data['点赞数'].sum()
        report += f"\n{i+1}. **{creator}**\n"
        report += f"   - 笔记数: {count} 条\n"
        report += f"   - 总点赞: {total_likes:,}\n"

    report += f"""
---

## 📅 时间分布

### 发布年份统计
"""

    # 按年份统计
    df['发布日期'] = pd.to_datetime(df['发布日期'], errors='coerce')
    df['年份'] = df['发布日期'].dt.year
    year_counts = df['年份'].value_counts().sort_index(ascending=False)
    for year, count in year_counts.items():
        report += f"- **{int(year)}年**: {count} 条\n"

    report += f"""
---

## 📁 数据文件

- **Excel文件**: `/Users/echochen/MediaCrawler/data/xhs/银饰品白岚_清洗数据.xlsx`
- **JSON文件**: `/Users/echochen/MediaCrawler/data/xhs/json/search_contents_2026-01-31.json`
- **图片目录**: `/Users/echochen/MediaCrawler/data/xhs/images/`
- **视频目录**: `/Users/echochen/MediaCrawler/data/xhs/videos/`

---

**报告生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**数据采集工具**: MediaCrawler
**分析脚本**: clean_bailan_data.py + generate_report.py
"""

    # 保存报告
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"✓ Markdown报告已保存: {output_file}")

def main():
    """主流程"""
    print("="*60)
    print("银饰品白岚 - 小红书数据分析报告生成")
    print("="*60)

    # 1. 加载数据
    print("\n[1/3] 加载数据...")
    df = load_data()

    # 2. 分析数据
    print("\n[2/3] 分析数据...")
    analyze_brand_mentions(df)
    analyze_engagement(df)
    analyze_content_types(df)
    analyze_time_distribution(df)
    analyze_creators(df)

    # 3. 生成报告
    print("\n[3/3] 生成报告...")
    report_file = '/Users/echochen/MediaCrawler/data/xhs/银饰品白岚_分析报告.md'
    generate_markdown_report(df, report_file)

    print("\n" + "="*60)
    print("✅ 分析报告生成完成！")
    print("="*60)
    print(f"\n报告文件: {report_file}")

if __name__ == "__main__":
    main()
