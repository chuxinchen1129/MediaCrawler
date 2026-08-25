# -*- coding: utf-8 -*-
"""
临时关键词爬虫 - 爬取指定关键词的研报
用法: python eastmoney_keyword_crawler.py
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict

# Add MediaCrawler root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from media_platform.eastmoney.client import EastmoneyClient
from media_platform.eastmoney.exception import DataFetchError, PDFDownloadError
from store.eastmoney import save_pdf_file
from tools import utils

# ==================== 配置 ====================
# 搜索关键词 - 使用API的keyword参数直接搜索
SEARCH_KEYWORD = "量贩"  # API搜索关键词

# 本地二次筛选关键词（可选，留空则不过滤）
FILTER_KEYWORDS = []

# 时间范围：过去4个月（120天）
DAYS = 120

# 最小页数限制（降低以获取更多结果）
MIN_PAGE_COUNT = 5

# PDF保存目录
PDF_SAVE_DIR = "/Users/echochen/Desktop/DMS/01_INFO_COLLECT/采集数据/eastmoney/keyword_pdf"

# 研报类型：0=公司研报, 1=行业研报
Q_TYPE_LIST = ["0", "1"]

# 每页数量
PAGE_SIZE = 50

# 最大页数限制
MAX_PAGES = 20


class KeywordCrawler:
    """关键词爬虫"""

    def __init__(self, keywords: List[str], days: int):
        self.client = EastmoneyClient()
        self.keywords = keywords
        self.days = days
        self.pdf_dir = PDF_SAVE_DIR

        # 确保PDF目录存在
        os.makedirs(self.pdf_dir, exist_ok=True)

    def _matches_keywords(self, title: str, abstract: str = "") -> bool:
        """检查标题或摘要是否包含关键词"""
        text = f"{title} {abstract}".lower()
        for keyword in self.keywords:
            if keyword.lower() in text:
                return True
        return False

    def _filter_reports(self, reports: List[Dict]) -> List[Dict]:
        """筛选报告"""
        filtered = []
        for report in reports:
            title = report.get("title", "")
            abstract = report.get("abstract", "")
            pages = report.get("attachPages", 0)

            # 检查页数
            if pages < MIN_PAGE_COUNT:
                continue

            # 检查关键词
            if self._matches_keywords(title, abstract):
                filtered.append(report)

        return filtered

    async def _download_pdf(self, report: Dict) -> str:
        """下载PDF"""
        info_code = report.get("infoCode", "")
        title = report.get("title", "")
        org_name = report.get("orgName", "")

        if not info_code:
            return None

        try:
            pdf_content = await self.client.download_pdf(
                infocode=info_code,
                save_path=""
            )

            if pdf_content:
                # 生成文件名
                safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_', '（', '）', '，', '。'))[:80]
                safe_org = "".join(c for c in org_name if c.isalnum() or c in (' ', '-', '_'))[:30]
                filename = f"{safe_org}+{safe_title}.pdf"
                filepath = os.path.join(self.pdf_dir, filename)

                # 保存PDF
                with open(filepath, 'wb') as f:
                    f.write(pdf_content)

                utils.logger.info(f"[KeywordCrawler] Downloaded: {filename} ({len(pdf_content)} bytes, {report.get('attachPages', 0)} pages)")
                return filepath

        except Exception as e:
            utils.logger.error(f"[KeywordCrawler] Failed to download {info_code}: {e}")

        return None

    async def start(self):
        """开始爬取"""
        utils.logger.info("=" * 60)
        utils.logger.info("关键词爬虫启动")
        utils.logger.info(f"关键词: {', '.join(self.keywords)}")
        utils.logger.info(f"时间范围: 过去 {self.days} 天")
        utils.logger.info(f"保存目录: {self.pdf_dir}")
        utils.logger.info("=" * 60)

        # 计算日期范围
        begin_date, end_date = self.client.get_date_range(self.days)
        utils.logger.info(f"日期范围: {begin_date} ~ {end_date}")

        all_matched_reports = []

        # 遍历研报类型
        for q_type in Q_TYPE_LIST:
            type_name = "公司研报" if q_type == "0" else "行业研报"
            utils.logger.info(f"\n[KeywordCrawler] 开始搜索 {type_name}...")

            page_no = 1
            type_reports = []

            while page_no <= MAX_PAGES:
                try:
                    reports = await self.client.fetch_report_list(
                        page_no=page_no,
                        begin_date=begin_date,
                        end_date=end_date,
                        page_size=PAGE_SIZE,
                        q_type=q_type
                    )

                    if not reports:
                        utils.logger.info(f"[KeywordCrawler] 第 {page_no} 页无数据，停止")
                        break

                    # 筛选匹配关键词的报告
                    matched = self._filter_reports(reports)
                    if matched:
                        type_reports.extend(matched)
                        utils.logger.info(f"[KeywordCrawler] 第 {page_no} 页: 获取 {len(reports)} 份，匹配 {len(matched)} 份")

                    page_no += 1
                    await asyncio.sleep(1)  # 避免请求过快

                except Exception as e:
                    utils.logger.error(f"[KeywordCrawler] 获取第 {page_no} 页失败: {e}")
                    break

            utils.logger.info(f"[KeywordCrawler] {type_name} 搜索完成，共匹配 {len(type_reports)} 份")
            all_matched_reports.extend(type_reports)

        # 去重（根据infoCode）
        seen_codes = set()
        unique_reports = []
        for report in all_matched_reports:
            code = report.get("infoCode")
            if code and code not in seen_codes:
                seen_codes.add(code)
                unique_reports.append(report)

        utils.logger.info(f"\n[KeywordCrawler] 总共找到 {len(unique_reports)} 份匹配的研报")

        if not unique_reports:
            utils.logger.info("[KeywordCrawler] 没有找到匹配的研报")
            return

        # 下载PDF
        utils.logger.info("\n" + "=" * 60)
        utils.logger.info("开始下载PDF...")
        utils.logger.info("=" * 60)

        downloaded = 0
        for i, report in enumerate(unique_reports, 1):
            title = report.get("title", "")
            utils.logger.info(f"\n[{i}/{len(unique_reports)}] {title}")

            pdf_path = await self._download_pdf(report)
            if pdf_path:
                downloaded += 1

        # 打印摘要
        utils.logger.info("\n" + "=" * 60)
        utils.logger.info("爬取完成！")
        utils.logger.info(f"匹配研报: {len(unique_reports)} 份")
        utils.logger.info(f"成功下载: {downloaded} 份")
        utils.logger.info(f"保存目录: {self.pdf_dir}")
        utils.logger.info("=" * 60)


async def main():
    crawler = KeywordCrawler(keywords=[SEARCH_KEYWORD], days=DAYS)
    await crawler.start()


if __name__ == "__main__":
    asyncio.run(main())
