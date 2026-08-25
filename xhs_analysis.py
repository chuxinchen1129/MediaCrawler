#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小红书数据分析脚本
"""

import pandas as pd
import numpy as np
import re
from collections import Counter
import jieba
import jieba.analyse
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import matplotlib
from snownlp import SnowNLP

# 设置中文字体
matplotlib.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'STHeiti']
matplotlib.rcParams['axes.unicode_minus'] = False

# 读取数据
df = pd.read_excel('/Users/echo/MediaCrawler/data/xhs/xhs_search_20260126_162338.xlsx')

print("=" * 80)
print("一、数据概览")
print("=" * 80)

# 1. 数据概览
print(f"\n数据总量: {len(df)} 条笔记")
print(f"字段数量: {len(df.columns)} 个")

# 数据类型转换
df['liked_count'] = pd.to_numeric(df['liked_count'], errors='coerce').fillna(0)
df['collected_count'] = pd.to_numeric(df['collected_count'], errors='coerce').fillna(0)
df['comment_count'] = pd.to_numeric(df['comment_count'], errors='coerce').fillna(0)
df['share_count'] = pd.to_numeric(df['share_count'], errors='coerce').fillna(0)

print(f"\n互动数据统计:")
print(f"总点赞数: {df['liked_count'].sum():,.0f}")
print(f"总收藏数: {df['collected_count'].sum():,.0f}")
print(f"总评论数: {df['comment_count'].sum():,.0f}")
print(f"总分享数: {df['share_count'].sum():,.0f}")

print(f"\n互动数据平均值:")
print(f"平均点赞数: {df['liked_count'].mean():.2f}")
print(f"平均收藏数: {df['collected_count'].mean():.2f}")
print(f"平均评论数: {df['comment_count'].mean():.2f}")
print(f"平均分享数: {df['share_count'].mean():.2f}")

# 类型分布
print(f"\n笔记类型分布:")
print(df['type'].value_counts())

print("\n" + "=" * 80)
print("二、文本内容分析")
print("=" * 80)

# 合并所有文本内容
all_titles = df['title'].fillna('').tolist()
all_descs = df['desc'].fillna('').tolist()
all_text = ''.join(all_titles + all_descs)

# 关键词提取
print("\n正在提取关键词...")
keywords = jieba.analyse.extract_tags(all_text, topK=100, withWeight=True)

print("\n热门关键词 TOP 30:")
print("-" * 60)
for word, weight in keywords[:30]:
    print(f"{word:15s} 权重: {weight:.4f}")

# 无醇/无酒精相关关键词
alcohol_keywords = [
    '无醇', '无酒精', '零酒精', '脱醇', '低醇', '微醺',
    '无醇啤酒', '无醇红酒', '无醇白酒', '无醇鸡尾酒',
    '啤酒', '红酒', '白酒', '鸡尾酒', '起泡酒',
    '酒精', '酒', '饮料'
]

print("\n无醇/酒精相关词汇统计:")
print("-" * 60)
for keyword in alcohol_keywords:
    count = all_text.count(keyword)
    if count > 0:
        print(f"{keyword:15s} 出现次数: {count}")

print("\n" + "=" * 80)
print("三、品牌提及分析")
print("=" * 80)

# 常见无醇酒品牌列表
brands = [
    '麒麟', '朝日', '三得利', '青岛', '雪花', '百威',
    '喜力', '科罗娜', '嘉士伯', '健力士',
    '红石', '德国', '比利时', '法国',
    '斐济', '带她', '零度', '零跑',
    '莫斯利安', '农夫山泉', '元气森林',
    '可口可乐', '百事', '星巴克', '瑞幸'
]

brand_mentions = {}
for brand in brands:
    count = all_text.count(brand)
    if count > 0:
        brand_mentions[brand] = count

print("\n品牌提及统计:")
print("-" * 60)
if brand_mentions:
    sorted_brands = sorted(brand_mentions.items(), key=lambda x: x[1], reverse=True)
    for brand, count in sorted_brands:
        print(f"{brand:15s} 提及次数: {count}")
else:
    print("未检测到明确的品牌提及")

print("\n" + "=" * 80)
print("四、情感分析")
print("=" * 80)

# 对标题和描述进行情感分析
print("\n正在进行情感分析...")

sentiments = []
for text in all_titles + all_descs:
    if text.strip():
        try:
            s = SnowNLP(text)
            sentiments.append(s.sentiments)
        except:
            sentiments.append(0.5)
    else:
        sentiments.append(0.5)

# 分类情感
positive = sum(1 for s in sentiments if s > 0.6)
neutral = sum(1 for s in sentiments if 0.4 <= s <= 0.6)
negative = sum(1 for s in sentiments if s < 0.4)
total = len(sentiments)

print(f"\n情感分析结果:")
print(f"正面情感: {positive} ({positive/total*100:.1f}%)")
print(f"中性情感: {neutral} ({neutral/total*100:.1f}%)")
print(f"负面情感: {negative} ({negative/total*100:.1f}%)")
print(f"平均情感得分: {np.mean(sentiments):.3f} (0=负面, 1=正面)")

print("\n" + "=" * 80)
print("五、热门笔记分析")
print("=" * 80)

# 计算热度分数（点赞+收藏+评论+分享）
df['heat_score'] = df['liked_count'] + df['collected_count']*2 + df['comment_count']*3 + df['share_count']*4
df['heat_score'] = pd.to_numeric(df['heat_score'], errors='coerce').fillna(0)

top_notes = df.nlargest(10, 'heat_score')[['title', 'liked_count', 'collected_count', 'comment_count', 'share_count', 'heat_score']]

print("\n热度 TOP 10 笔记:")
print("-" * 100)
for idx, row in top_notes.iterrows():
    print(f"\n标题: {row['title'][:50]}...")
    print(f"点赞: {row['liked_count']:.0f}, 收藏: {row['collected_count']:.0f}, "
          f"评论: {row['comment_count']:.0f}, 分享: {row['share_count']:.0f}, 热度: {row['heat_score']:.0f}")

print("\n" + "=" * 80)
print("六、内容主题分类")
print("=" * 80)

# 定义主题关键词
topics = {
    '产品推荐': ['推荐', '好物', '必买', '种草', '安利', '神器', '好用'],
    '使用体验': ['体验', '口感', '味道', '口感好', '好喝', '尝试', '试喝'],
    '购买渠道': ['哪里买', '购买', '渠道', '店铺', '链接', '淘宝', '京东', '拼多多'],
    '健康养生': ['健康', '养生', '减肥', '低卡', '无糖', '0糖', '0脂'],
    '社交聚会': ['聚会', '派对', '约会', '朋友', '聚餐', '烧烤', '火锅'],
    '科普知识': ['科普', '知识', '原理', '成分', '制作', '工艺'],
    '价格讨论': ['价格', '多少钱', '便宜', '贵', '性价比', '划算']
}

topic_counts = {}
for topic, keywords in topics.items():
    count = sum(all_text.count(kw) for kw in keywords)
    if count > 0:
        topic_counts[topic] = count

print("\n内容主题统计:")
print("-" * 60)
if topic_counts:
    sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
    for topic, count in sorted_topics:
        print(f"{topic:15s} 提及次数: {count}")
else:
    print("未检测到明确的主题分类")

print("\n" + "=" * 80)
print("分析完成！")
print("=" * 80)
