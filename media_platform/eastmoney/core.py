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
import config.eastmoney_config as eastmoney_config


class EastmoneyCrawler:
    """东方财富研报爬虫"""

    def __init__(self):
        self.client = EastmoneyClient()
        self.pdf_storage = EastmoneyPdfStorage()

    def _filter_reports(self, reports: List[Dict]) -> List[Dict]:
        """
        筛选报告，只保留符合条件的报告

        筛选逻辑：
        1. 页数 >= MIN_PAGE_COUNT (15页)
        2. 标题不包含 EXCLUDE_KEYWORDS
        3. 如果配置了 FORCE_FILTER_KEYWORDS，则只保留包含这些关键词的报告
        4. 如果总报告数 > REPORT_COUNT_THRESHOLD，则只保留包含 PRIORITY_TOPICS 的报告

        Args:
            reports: 原始报告列表

        Returns:
            筛选后的报告列表
        """
        filtered = []

        for report in reports:
            title = report.get("title", "")
            pages = report.get("attachPages", 0)
            abstract = report.get("abstract", "")

            # 规则1: 页数 >= MIN_PAGE_COUNT
            if pages < eastmoney_config.MIN_PAGE_COUNT:
                utils.logger.debug(f"[EastmoneyCrawler] Filtered out (pages < {eastmoney_config.MIN_PAGE_COUNT}): {title[:50]}")
                continue

            # 规则2: 标题不包含 EXCLUDE_KEYWORDS
            should_exclude = False
            for keyword in eastmoney_config.EXCLUDE_KEYWORDS:
                if keyword in title:
                    utils.logger.debug(f"[EastmoneyCrawler] Filtered out (contains '{keyword}'): {title[:50]}")
                    should_exclude = True
                    break

            if should_exclude:
                continue

            # 规则3: 强制筛选模式（如果配置了 FORCE_FILTER_KEYWORDS）
            if eastmoney_config.FORCE_FILTER_KEYWORDS:
                has_keyword = False
                for keyword in eastmoney_config.FORCE_FILTER_KEYWORDS:
                    if keyword in title or keyword in abstract:
                        has_keyword = True
                        break
                if not has_keyword:
                    utils.logger.debug(f"[EastmoneyCrawler] Filtered out (no force filter keyword): {title[:50]}")
                    continue

            # 通过初步筛选，加入候选列表
            filtered.append(report)

        # 规则4: 如果候选报告数 > 阈值，则按优先主题排序（优先主题排在前面，但保留所有报告）
        if len(filtered) > eastmoney_config.REPORT_COUNT_THRESHOLD:
            utils.logger.info(f"[EastmoneyCrawler] Report count ({len(filtered)}) > threshold ({eastmoney_config.REPORT_COUNT_THRESHOLD}), applying priority topic sort")

            priority_list = []
            other_list = []
            for report in filtered:
                title = report.get("title", "")
                abstract = report.get("abstract", "")

                # 检查是否包含优先主题关键词
                has_priority_topic = False
                for topic in eastmoney_config.PRIORITY_TOPICS:
                    if topic in title or topic in abstract:
                        has_priority_topic = True
                        break

                if has_priority_topic:
                    priority_list.append(report)
                else:
                    other_list.append(report)

            # 优先主题的报告排在前面，其他报告跟在后面
            filtered = priority_list + other_list
            utils.logger.info(f"[EastmoneyCrawler] Sorted: {len(priority_list)} priority + {len(other_list)} other = {len(filtered)} reports")

        return filtered

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

        # 遍历所有研报类型进行爬取
        all_reports = []
        for q_type in eastmoney_config.Q_TYPE_LIST:
            type_name = "行业研报" if q_type == "0" else "公司研报"
            utils.logger.info(f"[EastmoneyCrawler] 开始爬取 {type_name} (qType={q_type})")

            # Fetch all pages
            page_no = 1
            max_notes = eastmoney_config.PAGE_SIZE * 5  # Max 5 pages to avoid infinite loops

            while len(all_reports) < max_notes:
                utils.logger.info(f"[EastmoneyCrawler] Fetching {type_name} page {page_no}...")

                try:
                    reports = await self.client.fetch_report_list(
                        page_no=page_no,
                        begin_date=begin_date,
                        end_date=end_date,
                        q_type=q_type
                    )

                    if not reports:
                        utils.logger.info(f"[EastmoneyCrawler] No more {type_name} on page {page_no}")
                        break

                    # 筛选报告：只保留符合条件的报告
                    filtered_reports = self._filter_reports(reports)
                    utils.logger.info(f"[EastmoneyCrawler] Filtered {len(reports)} -> {len(filtered_reports)} reports")

                    all_reports.extend(filtered_reports)

                    # Process each report
                    for report_data in filtered_reports:
                        await self._process_report(report_data)

                    page_no += 1

                    # Sleep between page requests
                    await asyncio.sleep(eastmoney_config.REQUEST_INTERVAL)

                except DataFetchError as e:
                    utils.logger.error(f"[EastmoneyCrawler] Failed to fetch {type_name} page {page_no}: {e}")
                    break
                except Exception as e:
                    utils.logger.error(f"[EastmoneyCrawler] Unexpected error on {type_name} page {page_no}: {e}")
                    break

            utils.logger.info(f"[EastmoneyCrawler] {type_name} 爬取完成")

        utils.logger.info(f"[EastmoneyCrawler] Overall crawl completed. Total reports: {len(all_reports)}")

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
