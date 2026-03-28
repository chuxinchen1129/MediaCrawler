# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/store/eastmoney/__init__.py
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

# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2025/2/24 14:34
# @Desc    :

from typing import List

import config
from var import source_keyword_var
from .eastmoney_store_media import *
from ._store_impl import *


class EastmoneyStoreFactory:
    STORES = {
        "csv": EastmoneyCsvStoreImplement,
        "db": EastmoneySqliteStoreImplement,  # db uses sqlite as default
        "json": EastmoneyJsonStoreImplement,
        "sqlite": EastmoneySqliteStoreImplement,
        "excel": EastmoneyExcelStoreImplement,
    }

    @staticmethod
    def create_store():
        store_class = EastmoneyStoreFactory.STORES.get(config.SAVE_DATA_OPTION)
        if not store_class:
            raise ValueError("[EastmoneyStoreFactory.create_store] Invalid save option, only supported: csv, db, json, sqlite, excel")
        return store_class()


async def update_eastmoney_report(report_item: dict):
    """
    Update Eastmoney report
    Args:
        report_item: report data dict
    Returns:
    """
    await EastmoneyStoreFactory.create_store().store_content(report_item)


async def update_eastmoney_report_pdf_status(infocode: str, status: str, pdf_path: str = "", error_message: str = ""):
    """
    Update Eastmoney report PDF status
    Args:
        infocode: report infocode
        status: download status
        pdf_path: local file path
        error_message: error message
    Returns:
    """
    await EastmoneyStoreFactory.create_store().update_pdf_status(infocode, status, pdf_path, error_message)


async def save_pdf_file(infocode: str, pdf_content: bytes, extension_file_name: str, report_title: str = "", org_name: str = "") -> str:
    """
    Save PDF file
    Args:
        infocode: report infocode
        pdf_content: PDF bytes content
        extension_file_name: file extension name
        report_title: report title for naming
        org_name: organization name for naming
    Returns:
        file path of saved PDF
    """
    return await EastmoneyPdfStorage().store_pdf({"infocode": infocode, "pdf_content": pdf_content, "extension_file_name": extension_file_name, "report_title": report_title, "org_name": org_name})


async def get_new_reports_for_feishu(days: int = None) -> List[dict]:
    """
    Get new reports for Feishu notification
    Args:
        days: number of days to look back
    Returns:
        list of report dicts for Feishu message
    """
    import time
    from sqlalchemy import select
    from database.db_session import get_session
    from database.models import EastmoneyReport
    import config.eastmoney_config as eastmoney_config

    if days is None:
        days = eastmoney_config.DEFAULT_DAYS

    # Calculate timestamp threshold
    threshold_timestamp = int(time.time()) - (days * 24 * 60 * 60)

    async with get_session() as session:
        stmt = select(EastmoneyReport).where(
            EastmoneyReport.create_time >= threshold_timestamp,
            EastmoneyReport.download_status == "completed"
        ).order_by(EastmoneyReport.create_time.desc())
        result = await session.execute(stmt)
        reports = result.scalars().all()

        # Convert to list of dicts with filtering
        report_list = []
        for report in reports:
            # 筛选条件1: 页数 >= MIN_PAGE_COUNT
            if report.pdf_pages and report.pdf_pages < eastmoney_config.MIN_PAGE_COUNT:
                continue

            # 筛选条件2: 标题不包含 EXCLUDE_KEYWORDS
            title = report.report_title or ""
            should_exclude = False
            for keyword in eastmoney_config.EXCLUDE_KEYWORDS:
                if keyword in title:
                    should_exclude = True
                    break

            if should_exclude:
                continue

            # 筛选条件3: 如果报告数 > 阈值，检查是否包含优先主题（这里简化处理，返回所有符合条件的）
            report_list.append({
                "infocode": report.infocode,
                "title": report.report_title,
                "org_name": report.org_name,
                "publish_date": report.publish_date,
                "pdf_pages": report.pdf_pages,
                "pdf_path": report.pdf_path,
            })

        # 如果报告数 > 阈值，按优先主题排序（优先主题排在前面，但保留所有报告）
        if len(report_list) > eastmoney_config.REPORT_COUNT_THRESHOLD:
            utils.logger.info(f"[get_new_reports_for_feishu] Applying priority topic sort: {len(report_list)} reports")

            # 按是否包含优先主题分组
            priority_list = []
            other_list = []
            for report in report_list:
                title = report["title"]
                has_priority_topic = False
                for topic in eastmoney_config.PRIORITY_TOPICS:
                    if topic in title:
                        has_priority_topic = True
                        break
                if has_priority_topic:
                    priority_list.append(report)
                else:
                    other_list.append(report)

            # 优先主题的报告排在前面，其他报告跟在后面
            report_list = priority_list + other_list
            utils.logger.info(f"[get_new_reports_for_feishu] Sorted: {len(priority_list)} priority + {len(other_list)} other = {len(report_list)} total")

        return report_list
