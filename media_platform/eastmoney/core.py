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

import os
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

    def _filter_by_source(self, reports: List[Dict], sources: Optional[List[str]]) -> List[Dict]:
        """按来源机构 orgName 过滤（--source）。sources 为 None/空则不过滤。"""
        if not sources:
            return reports
        keywords = []
        for s in sources:
            keywords.extend(eastmoney_config.SOURCE_ORG_NAMES.get(s, []))
        if not keywords:
            return reports
        return [r for r in reports if any(k in (r.get("orgName") or "") for k in keywords)]

    def _filter_by_keyword(self, reports: List[Dict], keyword: Optional[str]) -> List[Dict]:
        """按关键词过滤标题/摘要（--keyword，AND 语义）。keyword 为 None/空则不过滤。"""
        if not keyword:
            return reports
        return [r for r in reports if keyword in ((r.get("title") or "") + (r.get("abstract") or ""))]

    def _filter_by_keywords_any(self, reports: List[Dict], keywords: Optional[List[str]]) -> List[Dict]:
        """标题含关键词列表中任一词即保留（--industry 行业研报定向兜底）。"""
        if not keywords:
            return reports
        return [r for r in reports if any(k in (r.get("title") or "") for k in keywords)]

    async def start(self, days: Optional[int] = None, industry: Optional[str] = None,
                    keyword: Optional[str] = None, sources: Optional[List[str]] = None) -> List[Dict]:
        """
        开始爬取研报

        Args:
            days: 爬取天数，默认从配置文件获取
            industry: 行业名（须在 INDUSTRY_CODE_MAP）。触发双重抓取：
                      公司研报用 industryCode 精确筛，行业研报用关键词匹配标题
            keyword: 额外关键词（标题/摘要 AND 过滤）
            sources: 来源机构列表（如 ["irresearch"]），按 orgName 过滤

        Returns:
            新下载的研报列表（用于飞书通知）
        """
        if days is None:
            days = eastmoney_config.DEFAULT_DAYS
        if isinstance(sources, str):
            sources = [sources]

        utils.logger.info(
            f"[EastmoneyCrawler] Starting crawl: days={days}, industry={industry}, "
            f"keyword={keyword}, sources={sources}"
        )

        # 行业名校验
        if industry and industry not in eastmoney_config.INDUSTRY_CODE_MAP:
            raise ValueError(
                f"行业 '{industry}' 不在 INDUSTRY_CODE_MAP 中，可用 --list-industries 查看可用行业"
            )

        # Get date range
        begin_date, end_date = self.client.get_date_range(days)

        # 构造抓取任务：(q_type, type_name, extra_kwargs)
        # 注意：qType=0=公司研报(reportType=2)，qType=1=行业研报(reportType=3)
        if industry:
            industry_code = eastmoney_config.INDUSTRY_CODE_MAP[industry]
            # 行业研报 API 不支持 industryCode，keyword 也常失配，用本地同义词兜底
            ind_kws = eastmoney_config.INDUSTRY_KEYWORDS_MAP.get(industry, [industry])
            tasks = [
                ("0", "公司研报", {"industry_code": industry_code}, None),
                # 行业研报：API keyword 对行业研报无效，正常翻页 + 本地同义词过滤
                ("1", "行业研报", {}, ind_kws),
            ]
        else:
            tasks = [
                (q, "公司研报" if q == "0" else "行业研报", {}, None)
                for q in eastmoney_config.Q_TYPE_LIST
            ]

        all_reports = []
        for q_type, type_name, extra, local_kws in tasks:
            utils.logger.info(f"[EastmoneyCrawler] 开始爬取 {type_name} (qType={q_type}) extra={extra}")

            # 每个 q_type 独立计数 + 独立上限，避免跨类型累加导致后一类型被跳过
            type_reports = []
            page_no = 1
            max_notes = eastmoney_config.PAGE_SIZE * 5  # Max 5 pages per type

            while len(type_reports) < max_notes:
                utils.logger.info(f"[EastmoneyCrawler] Fetching {type_name} page {page_no}...")

                try:
                    reports = await self.client.fetch_report_list(
                        page_no=page_no,
                        begin_date=begin_date,
                        end_date=end_date,
                        q_type=q_type,
                        **extra
                    )

                    if not reports:
                        utils.logger.info(f"[EastmoneyCrawler] No more {type_name} on page {page_no}")
                        break

                    # 筛选：页数/排除词 → 来源 → 关键词 → 行业同义词兜底
                    filtered_reports = self._filter_reports(reports)
                    filtered_reports = self._filter_by_source(filtered_reports, sources)
                    filtered_reports = self._filter_by_keyword(filtered_reports, keyword)
                    if local_kws:
                        filtered_reports = self._filter_by_keywords_any(filtered_reports, local_kws)
                    utils.logger.info(
                        f"[EastmoneyCrawler] {type_name} page {page_no}: "
                        f"{len(reports)} -> {len(filtered_reports)} reports"
                    )

                    type_reports.extend(filtered_reports)

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

            utils.logger.info(f"[EastmoneyCrawler] {type_name} 爬取完成: {len(type_reports)} reports")
            all_reports.extend(type_reports)

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
                    extension_file_name=".pdf",
                    report_title=db_item.get("report_title", ""),
                    org_name=db_item.get("org_name", ""),
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

    async def move_all_pdfs(self) -> Dict:
        """移动 PDF_SAVE_DIR 下所有已下载 PDF 到 TARGET_PDF_DIR（不经飞书选择，全部保留）。"""
        import shutil
        src = eastmoney_config.PDF_SAVE_DIR
        dst = eastmoney_config.TARGET_PDF_DIR
        os.makedirs(dst, exist_ok=True)
        moved, skipped = 0, 0
        for f in os.listdir(src):
            if not f.endswith(".pdf"):
                continue
            s = os.path.join(src, f)
            d = os.path.join(dst, f)
            if os.path.exists(d):
                os.remove(s); skipped += 1; continue
            shutil.move(s, d); moved += 1
        utils.logger.info(f"[EastmoneyCrawler] move_all: {moved} moved, {skipped} skipped -> {dst}")
        return {"moved": moved, "skipped": skipped, "target": dst}
