# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/config/eastmoney_config.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LEARN LICENSE 1.1
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

# ==================== API 配置 ====================
API_BASE_URL = "https://reportapi.eastmoney.com/report/list"
PDF_BASE_URL = "https://pdf.dfcfw.com/pdf"
Q_TYPE_LIST = ["0", "1"]  # 查询类型列表：0=行业研报, 1=公司研报
DEFAULT_CB_PREFIX = "datatable"  # JSONP回调前缀

# ==================== 爬取参数 ====================
PAGE_SIZE = 50          # 每页获取数量
DEFAULT_DAYS = 3        # 默认爬取最近3天（已修改）
REQUEST_INTERVAL = 1    # 请求间隔(秒)
MAX_RETRIES = 3         # 最大重试次数

# ==================== 存储配置 ====================
SAVE_PDF = True
PDF_SAVE_DIR = "./data/eastmoney/pdf"

# ==================== 用户筛选（通过飞书） ====================
SHOW_LIST_AFTER_DOWNLOAD = True  # 下载后显示列表供用户选择
DELETE_UNSELECTED = False        # 自动删除用户未选择的PDF（暂时禁用）

# ==================== 飞书集成 ====================
SEND_LIST_TO_FEISHU = True  # 启用飞书通知（使用群聊 chat_id）

# 飞书配置从 ~/.feishu_user_config.json 读取
import os
import json

_feishu_config_path = os.path.expanduser("~/.feishu_user_config.json")
if os.path.exists(_feishu_config_path):
    with open(_feishu_config_path, 'r') as f:
        _feishu_config = json.load(f)
    FEISHU_CHAT_ID = _feishu_config.get('chat_id', _feishu_config.get('user_open_id', ''))
    FEISHU_APP_ID = _feishu_config.get('app_id', '')
    FEISHU_APP_SECRET = _feishu_config.get('app_secret', '')
else:
    FEISHU_CHAT_ID = ""
    FEISHU_APP_ID = ""
    FEISHU_APP_SECRET = ""

# 用户指定的PDF保留目录
TARGET_PDF_DIR = "/Users/echochen/Library/Mobile Documents/com~apple~CloudDocs/家人共享/待选报告"

# ==================== 超时配置 ====================
PDF_DOWNLOAD_TIMEOUT = 120  # PDF下载超时(秒)
API_REQUEST_TIMEOUT = 30    # API请求超时(秒)

# ==================== PDF 页数过滤 ====================
MIN_PAGE_COUNT = 15  # 最小页数限制（低于此页数的PDF将被自动删除）

# ==================== 报告类型筛选 ====================
# 排除标题中包含以下关键词的报告
EXCLUDE_KEYWORDS = ["周报", "点评", "快讯", "简报", "速评", "更新", "ESG"]

# 当报告数量大于阈值时，优先保留特定主题的报告
REPORT_COUNT_THRESHOLD = 50  # 报告数量阈值（提高到50，避免过度过滤）

# 优先保留的主题（包含以下关键词的报告会被保留）
PRIORITY_TOPICS = [
    "便利店", "食品饮料", "零售", "功能性食品", "功能食品",
    "消费品", "娱乐", "文化旅游", "年轻人", "宠物", "化妆品",
    "机器人", "消费电子", "日用品", "母婴",
    "玩具", "潮玩", "运动服饰", "时尚", "美妆", "服饰", "珠宝",
    "酒店", "餐饮", "旅游", "休闲", "体育", "健身"
]

# 强制筛选模式：只下载包含以下关键词的报告（留空则下载所有）
FORCE_FILTER_KEYWORDS = []
