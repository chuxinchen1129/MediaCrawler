#!/bin/bash
# 每周六晚上8点运行东方财富研报爬虫（过去7天）

# 启动 bot_server
cd /Users/echochen/Desktop/DMS/skills/feishu-bot/scripts
python3 bot_server.py &
BOT_PID=$!
sleep 3

# 运行爬虫
cd /Users/echochen/MediaCrawler
/opt/homebrew/bin/python3 main_eastmoney.py --days 7

# 清理 bot_server 进程
kill $BOT_PID 2>/dev/null
