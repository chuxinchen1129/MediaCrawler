# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/config/base_config.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#

# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。

# 基础配置
PLATFORM = "xhs"  # 平台，xhs | dy | ks | bili | wb | tieba | zhihu
KEYWORDS = "悟昕睡眠仪"  # 关键词搜索配置，以英文逗号分隔
# Basic configuration
# [merge] 上游默认值已注释，本地值为准: PLATFORM = "xhs"  # Platform, xhs | dy | ks | bili | wb | tieba | zhihu

# 是否使用海外版小红书 (rednote.com)
# 开启后 API 走 webapi.rednote.com，cookie 域使用 .rednote.com
XHS_INTERNATIONAL = False

# [merge] 上游默认值已注释，本地值为准: KEYWORDS = "编程副业,编程兼职"  # Keyword search configuration, separated by English commas
LOGIN_TYPE = "qrcode"  # qrcode or phone or cookie
COOKIES = "web_session=040069b31731c1120aa4027cb93b4b82718165; webId=19a9240e438x03lbfqdkpnaj5l0nzywqnk9wt0nkw30000401735; a1=5b310803aa8816d20c03fba77e990c7a; webBuild=5.11.0"
CRAWLER_TYPE = "detail"  # search(搜索) | detail(帖子详情) | creator(创作者主页数据)
# 是否开启 IP 代理
ENABLE_IP_PROXY = False

# Number of proxy IP pools
IP_PROXY_POOL_COUNT = 2

# Proxy IP provider name
IP_PROXY_PROVIDER_NAME = "kuaidaili"  # kuaidaili | wandouhttp | static

# Static proxy configuration (used when IP_PROXY_PROVIDER_NAME is set to "static")
# Format: "http://your_home_domain:port" or "http://user:password@your_home_domain:port"
STATIC_PROXY_URL = ""

# Setting to True will not open the browser (headless browser)
# Setting False will open a browser
# If Xiaohongshu keeps scanning the code to log in but fails, open the browser and manually pass the sliding verification code.
# If Douyin keeps prompting failure, open the browser and see if mobile phone number verification appears after scanning the QR code to log in. If it does, manually go through it and try again.
HEADLESS = False

# Whether to save login status
SAVE_LOGIN_STATE = True

# ==================== CDP (Chrome DevTools Protocol) 配置 ====================
# 是否启用 CDP 模式 - 使用用户本地的 Chrome/Edge 浏览器进行爬取，具有更好的反检测能力
# 开启后，会自动检测并启动用户的 Chrome/Edge 浏览器，通过 CDP 协议进行控制
# 该方式使用真实浏览器环境，包括用户的扩展、Cookie 和设置，大幅降低被风控检测的风险
ENABLE_CDP_MODE = True

# CDP 调试端口，用于与浏览器通信
# 如果端口被占用，系统会自动尝试下一个可用端口
CDP_DEBUG_PORT = 9222

# 自定义浏览器路径（可选）
# 如果为空，系统会自动检测 Chrome/Edge 的安装路径
# Windows 示例: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
# macOS 示例: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
CUSTOM_BROWSER_PATH = ""

# 是否在 CDP 模式下启用无头模式
# 注意：即使设置为 True，某些反检测功能在无头模式下可能无法正常工作
CDP_HEADLESS = False

# 浏览器启动超时时间（秒）
BROWSER_LAUNCH_TIMEOUT = 120

# 是否在程序结束时自动关闭浏览器
# 设置为False可以保持浏览器运行，便于调试
AUTO_CLOSE_BROWSER = False
BROWSER_LAUNCH_TIMEOUT = 60

# 是否连接用户已打开的浏览器，而不是启动新的浏览器
# 开启后，程序会连接一个已经启用了远程调试的浏览器
# 用户需要在 Chrome 中开启远程调试：chrome://inspect/#remote-debugging
# 或者使用命令行参数启动 Chrome：--remote-debugging-port=9222
# 这种方式反检测效果最好，因为直接使用用户真实浏览器的所有 Cookie、扩展和浏览历史
CDP_CONNECT_EXISTING = True

# 程序结束时是否自动关闭浏览器
# 设置为 False 可以保持浏览器运行，方便调试
AUTO_CLOSE_BROWSER = True

# Data saving type option configuration, supports: csv, db, json, jsonl, sqlite, excel, postgres. It is best to save to DB, with deduplication function.
SAVE_DATA_OPTION = "jsonl"  # csv or db or json or jsonl or sqlite or excel or postgres

# Data saving path, if not specified by default, it will be saved to the data folder.
SAVE_DATA_PATH = ""

# Browser file configuration cached by the user's browser
USER_DATA_DIR = "%s_user_data_dir"  # %s will be replaced by platform name

# The number of pages to start crawling starts from the first page by default
START_PAGE = 1

# 爬取视频/帖子的数量控制
CRAWLER_MAX_NOTES_COUNT = 20

# Controlling the number of concurrent crawlers
MAX_CONCURRENCY_NUM = 1

# 是否开启爬媒体模式（包含图片或视频资源），默认不开启爬媒体
ENABLE_GET_MEIDAS = True

# Whether to enable comment crawling mode. Comment crawling is enabled by default.
ENABLE_GET_COMMENTS = True

# Control the number of crawled first-level comments (single video/post)
CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES = 10

# Whether to enable the mode of crawling second-level comments. By default, crawling of second-level comments is not enabled.
# If the old version of the project uses db, you need to refer to schema/tables.sql line 287 to add table fields.
ENABLE_GET_SUB_COMMENTS = False

# word cloud related
# Whether to enable generating comment word clouds
ENABLE_GET_WORDCLOUD = False
# Custom words and their groups
# Add rule: xx:yy where xx is a custom-added phrase, and yy is the group name to which the phrase xx is assigned.
CUSTOM_WORDS = {
    "零几": "年份",  # Recognize "zero points" as a whole
    "高频词": "专业术语",  # Example custom words
}

# Deactivate (disabled) word file path
STOP_WORDS_FILE = "./docs/hit_stopwords.txt"

# Chinese font file path
FONT_PATH = "./docs/STZHONGS.TTF"

# Crawl interval
CRAWLER_MAX_SLEEP_SEC = 2

# 是否禁用 SSL 证书验证。仅在使用企业代理、Burp Suite、mitmproxy 等会注入自签名证书的中间人代理时设为 True。
# 警告：禁用 SSL 验证将使所有流量暴露于中间人攻击风险，请勿在生产环境中开启。
DISABLE_SSL_VERIFY = False

from .bilibili_config import *
from .xhs_config import *
from .dy_config import *
from .ks_config import *
from .weibo_config import *
from .tieba_config import *
from .zhihu_config import *
