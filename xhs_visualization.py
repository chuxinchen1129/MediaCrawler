#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小红书数据可视化分析
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from matplotlib import font_manager
import seaborn as sns

# 设置中文字体
matplotlib.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'STHeiti']
matplotlib.rcParams['axes.unicode_minus'] = False

# 设置绘图风格
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (15, 10)

# 读取数据
df = pd.read_excel('/Users/echo/MediaCrawler/data/xhs/xhs_search_20260126_162338.xlsx')

# 数据类型转换
df['liked_count'] = pd.to_numeric(df['liked_count'], errors='coerce').fillna(0)
df['collected_count'] = pd.to_numeric(df['collected_count'], errors='coerce').fillna(0)
df['comment_count'] = pd.to_numeric(df['comment_count'], errors='coerce').fillna(0)
df['share_count'] = pd.to_numeric(df['share_count'], errors='coerce').fillna(0)
df['heat_score'] = df['liked_count'] + df['collected_count']*2 + df['comment_count']*3 + df['share_count']*4

# 创建图表
fig = plt.figure(figsize=(20, 12))

# 1. 互动数据分布
ax1 = plt.subplot(2, 3, 1)
interaction_data = {
    '点赞': df['liked_count'].sum(),
    '收藏': df['collected_count'].sum(),
    '评论': df['comment_count'].sum(),
    '分享': df['share_count'].sum()
}
colors1 = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A']
bars1 = ax1.bar(interaction_data.keys(), interaction_data.values(), color=colors1)
ax1.set_title('互动数据总量统计', fontsize=14, fontweight='bold', pad=15)
ax1.set_ylabel('数量', fontsize=12)
for bar in bars1:
    height = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2., height,
             f'{height:,.0f}',
             ha='center', va='bottom', fontsize=11)

# 2. 互动数据平均值对比
ax2 = plt.subplot(2, 3, 2)
avg_data = {
    '平均点赞': df['liked_count'].mean(),
    '平均收藏': df['collected_count'].mean(),
    '平均评论': df['comment_count'].mean(),
    '平均分享': df['share_count'].mean()
}
bars2 = ax2.bar(avg_data.keys(), avg_data.values(), color=colors1)
ax2.set_title('每条笔记平均互动数据', fontsize=14, fontweight='bold', pad=15)
ax2.set_ylabel('平均数量', fontsize=12)
for bar in bars2:
    height = bar.get_height()
    ax2.text(bar.get_x() + bar.get_width()/2., height,
             f'{height:.1f}',
             ha='center', va='bottom', fontsize=11)

# 3. 笔记类型分布
ax3 = plt.subplot(2, 3, 3)
type_counts = df['type'].value_counts()
colors3 = ['#FF6B6B', '#4ECDC4']
explode = (0.05, 0.05)
wedges, texts, autotexts = ax3.pie(type_counts.values, labels=type_counts.index,
                                     autopct='%1.1f%%', colors=colors3,
                                     explode=explode, shadow=True, startangle=90)
ax3.set_title('笔记类型分布', fontsize=14, fontweight='bold', pad=15)
for autotext in autotexts:
    autotext.set_color('white')
    autotext.set_fontsize(12)
    autotext.set_fontweight('bold')

# 4. 热度TOP10笔记
ax4 = plt.subplot(2, 3, 4)
top10 = df.nlargest(10, 'heat_score')[['title', 'heat_score']].copy()
top10['short_title'] = top10['title'].apply(lambda x: x[:20] + '...' if len(str(x)) > 20 else str(x))
bars4 = ax4.barh(range(len(top10)), top10['heat_score'], color='#FF6B6B')
ax4.set_yticks(range(len(top10)))
ax4.set_yticklabels(top10['short_title'], fontsize=9)
ax4.set_xlabel('热度分数', fontsize=12)
ax4.set_title('热度TOP10笔记', fontsize=14, fontweight='bold', pad=15)
ax4.invert_yaxis()
for i, bar in enumerate(bars4):
    width = bar.get_width()
    ax4.text(width, bar.get_y() + bar.get_height()/2.,
             f' {width:,.0f}',
             ha='left', va='center', fontsize=9)

# 5. 互动数据分布箱线图
ax5 = plt.subplot(2, 3, 5)
interaction_df = pd.DataFrame({
    '点赞': df['liked_count'],
    '收藏': df['collected_count'],
    '评论': df['comment_count'],
    '分享': df['share_count']
})
bp = ax5.boxplot([interaction_df['点赞'].clip(0, interaction_df['点赞'].quantile(0.95)),
                   interaction_df['收藏'].clip(0, interaction_df['收藏'].quantile(0.95)),
                   interaction_df['评论'].clip(0, interaction_df['评论'].quantile(0.95)),
                   interaction_df['分享'].clip(0, interaction_df['分享'].quantile(0.95))],
                  labels=['点赞', '收藏', '评论', '分享'],
                  patch_artist=True)
for patch, color in zip(bp['boxes'], colors1):
    patch.set_facecolor(color)
ax5.set_title('互动数据分布（截断95%分位数）', fontsize=14, fontweight='bold', pad=15)
ax5.set_ylabel('数量', fontsize=12)

# 6. 热度分数分布
ax6 = plt.subplot(2, 3, 6)
ax6.hist(df['heat_score'], bins=30, color='#FF6B6B', alpha=0.7, edgecolor='black')
ax6.set_title('热度分数分布', fontsize=14, fontweight='bold', pad=15)
ax6.set_xlabel('热度分数', fontsize=12)
ax6.set_ylabel('笔记数量', fontsize=12)
ax6.axvline(df['heat_score'].mean(), color='red', linestyle='--', linewidth=2, label=f'平均值: {df["heat_score"].mean():.0f}')
ax6.legend(fontsize=10)

plt.tight_layout(pad=3.0)
plt.savefig('/Users/echo/MediaCrawler/data/xhs/analysis_charts.png', dpi=300, bbox_inches='tight')
print("图表已保存至: /Users/echo/MediaCrawler/data/xhs/analysis_charts.png")
plt.close()

# 创建第二个图：关键词和品牌分析
fig2 = plt.figure(figsize=(20, 10))

# 准备数据
keywords_data = [
    ('话题', 0.5227), ('啤酒', 0.4347), ('无醇', 0.2818),
    ('山姆', 0.2511), ('酒精', 0.1405), ('黄油', 0.1354),
    ('青岛', 0.1088), ('好喝', 0.0869), ('大卡', 0.0759),
    ('新品', 0.0602)
]

brands_data = [
    ('青岛', 147), ('喜力', 6), ('百威', 5),
    ('德国', 4), ('麒麟', 3), ('法国', 3),
    ('雪花', 2), ('比利时', 2), ('朝日', 1)
]

alcohol_terms_data = [
    ('酒', 901), ('啤酒', 570), ('无醇', 255),
    ('酒精', 181), ('无酒精', 80), ('微醺', 28),
    ('无醇啤酒', 96), ('饮料', 44), ('零酒精', 6),
    ('脱醇', 10)
]

# 1. 热门关键词TOP10
ax1 = plt.subplot(2, 2, 1)
keywords_df = pd.DataFrame(keywords_data, columns=['关键词', '权重'])
bars1 = ax1.barh(keywords_df['关键词'], keywords_df['权重'], color='#FF6B6B')
ax1.set_xlabel('权重', fontsize=12)
ax1.set_title('热门关键词 TOP 10', fontsize=14, fontweight='bold', pad=15)
ax1.invert_yaxis()
for bar in bars1:
    width = bar.get_width()
    ax1.text(width, bar.get_y() + bar.get_height()/2.,
             f' {width:.4f}',
             ha='left', va='center', fontsize=10)

# 2. 品牌提及次数
ax2 = plt.subplot(2, 2, 2)
brands_df = pd.DataFrame(brands_data, columns=['品牌', '提及次数'])
bars2 = ax2.barh(brands_df['品牌'], brands_df['提及次数'], color='#4ECDC4')
ax2.set_xlabel('提及次数', fontsize=12)
ax2.set_title('品牌提及统计', fontsize=14, fontweight='bold', pad=15)
ax2.invert_yaxis()
for bar in bars2:
    width = bar.get_width()
    ax2.text(width, bar.get_y() + bar.get_height()/2.,
             f' {width}',
             ha='left', va='center', fontsize=10)

# 3. 无醇/酒精相关词汇
ax3 = plt.subplot(2, 2, 3)
alcohol_terms_df = pd.DataFrame(alcohol_terms_data, columns=['词汇', '出现次数'])
alcohol_terms_df = alcohol_terms_df.sort_values('出现次数', ascending=True)
bars3 = ax3.barh(alcohol_terms_df['词汇'], alcohol_terms_df['出现次数'], color='#45B7D1')
ax3.set_xlabel('出现次数', fontsize=12)
ax3.set_title('无醇/酒精相关词汇统计', fontsize=14, fontweight='bold', pad=15)
for bar in bars3:
    width = bar.get_width()
    ax3.text(width, bar.get_y() + bar.get_height()/2.,
             f' {width}',
             ha='left', va='center', fontsize=10)

# 4. 内容主题分布
ax4 = plt.subplot(2, 2, 4)
topics_data = [
    ('使用体验', 185), ('社交聚会', 113), ('健康养生', 90),
    ('产品推荐', 81), ('价格讨论', 20), ('科普知识', 13)
]
topics_df = pd.DataFrame(topics_data, columns=['主题', '提及次数'])
colors4 = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8', '#F7DC6F']
wedges, texts, autotexts = ax4.pie(topics_df['提及次数'], labels=topics_df['主题'],
                                     autopct='%1.1f%%', colors=colors4,
                                     explode=[0.05]*len(topics_df), shadow=True, startangle=90)
ax4.set_title('内容主题分布', fontsize=14, fontweight='bold', pad=15)
for autotext in autotexts:
    autotext.set_color('white')
    autotext.set_fontsize(10)
    autotext.set_fontweight('bold')

plt.tight_layout(pad=3.0)
plt.savefig('/Users/echo/MediaCrawler/data/xhs/keywords_charts.png', dpi=300, bbox_inches='tight')
print("关键词图表已保存至: /Users/echo/MediaCrawler/data/xhs/keywords_charts.png")
plt.close()

# 创建第三个图：情感分析
fig3 = plt.figure(figsize=(16, 8))

# 情感分布饼图
ax1 = plt.subplot(1, 2, 1)
sentiment_data = [63.5, 8.0, 28.5]
sentiment_labels = ['正面', '中性', '负面']
colors_sentiment = ['#4ECDC4', '#FFD93D', '#FF6B6B']
wedges, texts, autotexts = ax1.pie(sentiment_data, labels=sentiment_labels,
                                     autopct='%1.1f%%', colors=colors_sentiment,
                                     explode=[0.05, 0.05, 0.05], shadow=True, startangle=90)
ax1.set_title('情感分析分布', fontsize=16, fontweight='bold', pad=15)
for autotext in autotexts:
    autotext.set_color('white')
    autotext.set_fontsize(14)
    autotext.set_fontweight('bold')

# 情感得分分布
ax2 = plt.subplot(1, 2, 2)
from snownlp import SnowNLP

# 重新计算情感得分
all_titles = df['title'].fillna('').tolist()
all_descs = df['desc'].fillna('').tolist()
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

ax2.hist(sentiments, bins=30, color='#4ECDC4', alpha=0.7, edgecolor='black')
ax2.set_title('情感得分分布', fontsize=16, fontweight='bold', pad=15)
ax2.set_xlabel('情感得分 (0=负面, 1=正面)', fontsize=12)
ax2.set_ylabel('内容数量', fontsize=12)
ax2.axvline(np.mean(sentiments), color='red', linestyle='--', linewidth=2,
            label=f'平均得分: {np.mean(sentiments):.3f}')
ax2.legend(fontsize=12)
ax2.text(0.6, max(ax2.get_ylim())*0.9,
         f'正面: {sum(1 for s in sentiments if s > 0.6)}\n'
         f'中性: {sum(1 for s in sentiments if 0.4 <= s <= 0.6)}\n'
         f'负面: {sum(1 for s in sentiments if s < 0.4)}',
         fontsize=12, bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

plt.tight_layout(pad=3.0)
plt.savefig('/Users/echo/MediaCrawler/data/xhs/sentiment_charts.png', dpi=300, bbox_inches='tight')
print("情感分析图表已保存至: /Users/echo/MediaCrawler/data/xhs/sentiment_charts.png")
plt.close()

print("\n所有图表生成完成！")
