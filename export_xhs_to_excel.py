#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import pandas as pd
from datetime import datetime

# 读取数据
with open('data/xhs/json/search_contents_2026-02-25.json', 'r', encoding='utf-8') as f:
    notes = json.load(f)

# 处理数据
data = []
for note in notes:
    ts = note.get('time', 0)
    if ts:
        ts = ts / 1000 if ts > 1000000000000 else ts
        dt = datetime.fromtimestamp(ts)
        date_str = dt.strftime('%Y-%m-%d %H:%M')
    else:
        date_str = '未知'

    data.append({
        '序号': len(data) + 1,
        '标题': note.get('title', ''),
        '作者': note.get('nickname', ''),
        '发布时间': date_str,
        '点赞数': str(note.get('liked_count', '0')),
        '收藏数': str(note.get('collected_count', '0')),
        '评论数': str(note.get('comment_count', '0')),
        '转发数': str(note.get('share_count', '0')),
        '笔记链接': f"https://www.xiaohongshu.com/explore/{note.get('note_id', '')}",
        '笔记ID': note.get('note_id', '')
    })

df = pd.DataFrame(data)
output_path = 'data/xhs/小红书睡眠关键词_7天_2026-02-25.xlsx'
df.to_excel(output_path, index=False, sheet_name='睡眠内容')

print(f'Excel生成成功: {output_path}')
print(f'共 {len(data)} 条数据')
