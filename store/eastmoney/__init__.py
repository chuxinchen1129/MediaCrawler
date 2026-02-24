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


async def save_pdf_file(infocode: str, pdf_content: bytes, extension_file_name: str) -> str:
    """
    Save PDF file
    Args:
        infocode: report infocode
        pdf_content: PDF bytes content
        extension_file_name: file extension name
    Returns:
        file path of saved PDF
    """
    return await EastmoneyPdfStorage().store_pdf({"infocode": infocode, "pdf_content": pdf_content, "extension_file_name": extension_file_name})


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

    if days is None:
        import config as eastmoney_config
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

        # Convert to list of dicts
        report_list = []
        for report in reports:
            report_list.append({
                "infocode": report.infocode,
                "title": report.report_title,
                "org_name": report.org_name,
                "publish_date": report.publish_date,
                "pdf_pages": report.pdf_pages,
                "pdf_path": report.pdf_path,
            })

        return report_list
