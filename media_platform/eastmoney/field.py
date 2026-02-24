# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/eastmoney/field.py
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

from dataclasses import dataclass
from typing import Optional
from enum import Enum


class ReportType(str, Enum):
    """研报类型"""
    INDUSTRY = "industry"  # 行业研报
    COMPANY = "company"    # 公司研报
    STRATEGY = "strategy"  # 策略研报


class DownloadStatus(str, Enum):
    """PDF下载状态"""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    NO_PDF = "no_pdf"


@dataclass
class EastmoneyReport:
    """东方财富研报数据模型"""
    infocode: str                    # 研报唯一标识码
    report_title: str                 # 研报标题
    org_name: str                     # 机构名称
    analyst: str                       # 分析师
    publish_date: str                  # 发布日期
    industry: str                      # 行业
    stock_code: Optional[str] = None   # 股票代码
    rating: Optional[str] = None       # 评级

    # PDF相关
    pdf_url: str = ""                  # PDF下载URL
    pdf_path: str = ""                 # 本地保存路径
    pdf_size: int = 0                 # PDF文件大小(字节)
    pdf_pages: int = 0                 # PDF页数
    attach_type: str = ""               # 附件类型，"0"表示有PDF

    # 状态
    download_status: str = DownloadStatus.PENDING.value
    error_message: str = ""             # 错误信息

    # 元数据
    create_time: int = 0              # 创建时间戳
    update_time: int = 0              # 更新时间戳

    def has_pdf(self) -> bool:
        """判断是否有PDF附件"""
        return self.attach_type == "0"


@dataclass
class APIResponse:
    """API响应数据模型"""
    success: bool
    data: Optional[dict] = None
    message: str = ""
    total_count: int = 0


@dataclass
class ReportListItem:
    """研报列表项数据模型"""
    info_code: str                # infocode
    title: str                    # 研报标题
    org_name: str                 # 机构名称
    publish_date: str             # 发布日期
    attach_size: int              # 附件大小(字节)
    attach_pages: int             # 附件页数
    attach_type: str              # 附件类型
    industry: Optional[str] = None # 行业
    analyst: Optional[str] = None  # 分析师
