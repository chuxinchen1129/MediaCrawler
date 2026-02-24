# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/eastmoney/core.py
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

import asyncio
from typing import List, Dict, Optional

from .client import EastmoneyClient
from .exception import DataFetchError, PDFDownloadError
from store.eastmoney import update_eastmoney_report, update_eastmoney_report_pdf_status, save_pdf_file, get_new_reports_for_feishu
from store.eastmoney._store_impl import EastmoneyPdfStorage
from tools import utils
import config as eastmoney_config


class EastmoneyCrawler:
    """东方财富研报爬虫"""

    def __init__(self):
        self.client = EastmoneyClient()
        self.pdf_storage = EastmoneyPdfStorage()

    async def start(self, days: Optional[int] = None) -> List[Dict]:
        """
        开始爬取研报

        Args:
            days: 爬取天数，默认从配置文件获取

        Returns:
            新下载的研报列表（用于飞书通知）
        """
        if days is None:
            days = eastmoney_config.DEFAULT_DAYS

        utils.logger.info(f"[EastmoneyCrawler] Starting crawl for {days} days")

        # Get date range
        begin_date, end_date = self.client.get_date_range(days)

        # Fetch all pages
        all_reports = []
        page_no = 1
        max_notes = eastmoney_config.PAGE_SIZE * 5  # Max 5 pages to avoid infinite loops

        while len(all_reports) < max_notes:
            utils.logger.info(f"[EastmoneyCrawler] Fetching page {page_no}...")

            try:
                reports = await self.client.fetch_report_list(
                    page_no=page_no,
                    begin_date=begin_date,
                    end_date=end_date
                )

                if not reports:
                    utils.logger.info(f"[EastmoneyCrawler] No more reports on page {page_no}")
                    break

                all_reports.extend(reports)

                # Process each report
                for report_data in reports:
                    await self._process_report(report_data)

                page_no += 1

                # Sleep between page requests
                await asyncio.sleep(eastmoney_config.REQUEST_INTERVAL)

            except DataFetchError as e:
                utils.logger.error(f"[EastmoneyCrawler] Failed to fetch page {page_no}: {e}")
                break
            except Exception as e:
                utils.logger.error(f"[EastmoneyCrawler] Unexpected error on page {page_no}: {e}")
                break

        utils.logger.info(f"[EastmoneyCrawler] Crawl completed. Total reports: {len(all_reports)}")

        # Get newly downloaded reports for Feishu notification
        new_reports = await get_new_reports_for_feishu(days)

        return new_reports

    async def _process_report(self, report_data: Dict) -> Optional[Dict]:
        """
        处理单个研报，包括下载PDF

        Args:
            report_data: 原始报告数据

        Returns:
            处理后的报告数据（用于通知）
        """
        info_code = report_data.get("infoCode", "")
        if not info_code:
            utils.logger.warning(f"[EastmoneyCrawler] Report has no infoCode: {report_data}")
            return None

        # Prepare database record
        db_item = {
            "infocode": info_code,
            "report_title": report_data.get("title", ""),
            "org_name": report_data.get("orgName", ""),
            "analyst": report_data.get("researcher", ""),
            "publish_date": report_data.get("publishDate", ""),
            "industry": report_data.get("indvInduName", ""),
            "stock_code": report_data.get("stockCode", ""),
            "rating": report_data.get("emRatingName", ""),
            "pdf_url": self.client.get_pdf_url(info_code),
            "pdf_size": report_data.get("attachSize", 0),
            "pdf_pages": report_data.get("attachPages", 0),
            "attach_type": report_data.get("attachType", ""),
        }

        # Check if PDF exists
        if report_data.get("attachType") != "0":
            utils.logger.info(f"[EastmoneyCrawler] Report {info_code} has no PDF, skipping download")
            db_item["download_status"] = "no_pdf"
            db_item["error_message"] = "No PDF attachment"
            await update_eastmoney_report(db_item)
            return None

        # Download PDF
        utils.logger.info(f"[EastmoneyCrawler] Downloading PDF for report: {info_code}")

        try:
            pdf_content = await self.client.download_pdf(
                infocode=info_code,
                save_path=""
            )

            if pdf_content:
                # Save PDF to local storage
                pdf_path = await save_pdf_file(
                    infocode=info_code,
                    pdf_content=pdf_content,
                    extension_file_name=".pdf"
                )

                db_item["pdf_path"] = pdf_path
                db_item["download_status"] = "completed"

                utils.logger.info(f"[EastmoneyCrawler] PDF downloaded: {pdf_path}")

            else:
                db_item["download_status"] = "failed"
                db_item["error_message"] = "PDF download returned None"
                utils.logger.warning(f"[EastmoneyCrawler] PDF download returned None for {info_code}")

        except PDFDownloadError as e:
            db_item["download_status"] = "failed"
            db_item["error_message"] = str(e)
            utils.logger.error(f"[EastmoneyCrawler] PDF download failed for {info_code}: {e}")

        # Save to database
        await update_eastmoney_report(db_item)

        return db_item

    async def move_selected_pdfs(self, infocodes: List[str]) -> Dict[str, str]:
        """
        将选中的PDF移动到目标目录，删除未选中的

        Args:
            infocodes: 要保留的infocode列表

        Returns:
            映射 infocode -> 目标文件路径
        """
        return await self.pdf_storage.move_to_target(infocodes)
