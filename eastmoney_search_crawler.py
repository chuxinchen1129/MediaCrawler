# -*- coding: utf-8 -*-
"""
东方财富关键词搜索爬虫 - 使用API的keyword参数直接搜索
用法: python eastmoney_search_crawler.py
"""

import asyncio
import sys
import os
import json
import random
import httpx
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from urllib.parse import urlencode

# Add MediaCrawler root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import utils

# ==================== 配置 ====================
# 搜索关键词 - 使用API的keyword参数
SEARCH_KEYWORDS = ["万辰", "零食量贩", "折扣店"]

# 时间范围：过去4个月（120天）
DAYS = 120

# 最小页数限制
MIN_PAGE_COUNT = 5

# PDF保存目录
PDF_SAVE_DIR = "/Users/echochen/Desktop/DMS/01_INFO_COLLECT/采集数据/eastmoney/keyword_pdf"

# 每页数量
PAGE_SIZE = 50

# 最大页数限制
MAX_PAGES = 10

# API配置
API_BASE_URL = "https://reportapi.eastmoney.com/report/list"
PDF_BASE_URL = "https://pdf.dfcfw.com/pdf"


class SearchCrawler:
    """关键词搜索爬虫"""

    def __init__(self, keywords: List[str], days: int):
        self.keywords = keywords
        self.days = days
        self.pdf_dir = PDF_SAVE_DIR
        self.timeout = 30

        # 确保PDF目录存在
        os.makedirs(self.pdf_dir, exist_ok=True)

    def _generate_callback(self) -> str:
        """生成随机JSONP回调参数"""
        random_num = random.randint(100000, 999999)
        return f"datatable{random_num}"

    def _parse_jsonp_response(self, response_text: str) -> dict:
        """解析JSONP响应"""
        try:
            start_idx = response_text.find('{')
            if start_idx == -1:
                raise ValueError(f"无法找到JSON开始标记")

            depth = 0
            for i in range(start_idx, len(response_text)):
                if response_text[i] == '{':
                    depth += 1
                elif response_text[i] == '}':
                    depth -= 1
                    if depth == 0:
                        json_str = response_text[start_idx:i+1]
                        return json.loads(json_str)

            raise ValueError(f"无法找到匹配的JSON结束标记")
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON解析失败: {e}")

    def get_date_range(self) -> tuple:
        """获取日期范围"""
        today = datetime.now()
        end_date = today
        begin_date = today - timedelta(days=self.days)
        return (
            begin_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d")
        )

    async def search_reports(self, keyword: str, page_no: int = 1, q_type: str = "0") -> List[Dict]:
        """搜索研报"""
        callback = self._generate_callback()
        begin_date, end_date = self.get_date_range()

        params = {
            "cb": callback,
            "pageNo": page_no,
            "pageSize": PAGE_SIZE,
            "qType": q_type,
            "beginTime": begin_date,
            "endTime": end_date,
            "keyword": keyword,
        }

        full_url = f"{API_BASE_URL}?{urlencode(params)}"

        utils.logger.info(f"[SearchCrawler] 搜索关键词 '{keyword}' 第 {page_no} 页...")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(full_url)
            response.raise_for_status()
            data = self._parse_jsonp_response(response.text)
            reports = data.get("data", [])
            total = data.get("hits", 0)
            utils.logger.info(f"[SearchCrawler] 获取 {len(reports)} 份 (总计: {total})")
            return reports

    def _filter_reports(self, reports: List[Dict]) -> List[Dict]:
        """筛选报告"""
        filtered = []
        for report in reports:
            pages = report.get("attachPages", 0)
            if pages >= MIN_PAGE_COUNT:
                filtered.append(report)
        return filtered

    async def _download_pdf(self, report: Dict) -> str:
        """下载PDF"""
        info_code = report.get("infoCode", "")
        title = report.get("title", "")
        org_name = report.get("orgName", "")

        if not info_code:
            return None

        pdf_url = f"{PDF_BASE_URL}/H3_{info_code}_1.pdf"
        utils.logger.info(f"[SearchCrawler] 下载: {info_code}")

        try:
            proc = await asyncio.create_subprocess_exec(
                "curl", "-sL",
                "-H", "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "-H", "Referer: https://data.eastmoney.com/",
                "-o", "-",
                pdf_url,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)

            if proc.returncode != 0:
                utils.logger.error(f"[SearchCrawler] curl下载失败: {stderr.decode()}")
                return None

            if stdout[:5].startswith(b"%PDF"):
                # 生成文件名
                safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_', '（', '）', '，', '。'))[:80]
                safe_org = "".join(c for c in org_name if c.isalnum() or c in (' ', '-', '_'))[:30]
                filename = f"{safe_org}+{safe_title}.pdf"
                filepath = os.path.join(self.pdf_dir, filename)

                with open(filepath, 'wb') as f:
                    f.write(stdout)

                utils.logger.info(f"[SearchCrawler] Downloaded: {filename} ({len(stdout)} bytes, {report.get('attachPages', 0)} pages)")
                return filepath
            else:
                utils.logger.warning(f"[SearchCrawler] 响应不是有效PDF")
                return None

        except Exception as e:
            utils.logger.error(f"[SearchCrawler] 下载失败 {info_code}: {e}")
            return None

    async def start(self):
        """开始爬取"""
        utils.logger.info("=" * 60)
        utils.logger.info("关键词搜索爬虫启动")
        utils.logger.info(f"搜索关键词: {', '.join(self.keywords)}")
        utils.logger.info(f"时间范围: 过去 {self.days} 天")
        utils.logger.info(f"保存目录: {self.pdf_dir}")
        utils.logger.info("=" * 60)

        begin_date, end_date = self.get_date_range()
        utils.logger.info(f"日期范围: {begin_date} ~ {end_date}")

        all_reports = {}  # infoCode -> report

        # 对每个关键词进行搜索
        for keyword in self.keywords:
            utils.logger.info(f"\n[SearchCrawler] ===== 搜索关键词: {keyword} =====")

            # 搜索行业研报和公司研报
            for q_type in ["0", "1"]:
                type_name = "公司研报" if q_type == "0" else "行业研报"
                utils.logger.info(f"\n[SearchCrawler] --- {type_name} ---")

                page_no = 1
                while page_no <= MAX_PAGES:
                    try:
                        reports = await self.search_reports(keyword, page_no, q_type)

                        if not reports:
                            utils.logger.info(f"[SearchCrawler] 第 {page_no} 页无数据，停止")
                            break

                        # 筛选
                        filtered = self._filter_reports(reports)

                        # 添加到总集合（去重）
                        new_count = 0
                        for report in filtered:
                            info_code = report.get("infoCode")
                            if info_code and info_code not in all_reports:
                                all_reports[info_code] = report
                                new_count += 1

                        utils.logger.info(f"[SearchCrawler] 第 {page_no} 页: {len(filtered)} 份有效，{new_count} 份新研报")

                        page_no += 1
                        await asyncio.sleep(1)

                    except Exception as e:
                        utils.logger.error(f"[SearchCrawler] 获取第 {page_no} 页失败: {e}")
                        break

        utils.logger.info(f"\n[SearchCrawler] 总共找到 {len(all_reports)} 份唯一研报")

        if not all_reports:
            utils.logger.info("[SearchCrawler] 没有找到匹配的研报")
            return

        # 下载PDF
        utils.logger.info("\n" + "=" * 60)
        utils.logger.info("开始下载PDF...")
        utils.logger.info("=" * 60)

        downloaded = 0
        reports_list = list(all_reports.values())

        for i, report in enumerate(reports_list, 1):
            title = report.get("title", "")
            utils.logger.info(f"\n[{i}/{len(reports_list)}] {title}")

            pdf_path = await self._download_pdf(report)
            if pdf_path:
                downloaded += 1

        # 打印摘要
        utils.logger.info("\n" + "=" * 60)
        utils.logger.info("爬取完成！")
        utils.logger.info(f"匹配研报: {len(all_reports)} 份")
        utils.logger.info(f"成功下载: {downloaded} 份")
        utils.logger.info(f"保存目录: {self.pdf_dir}")
        utils.logger.info("=" * 60)


async def main():
    crawler = SearchCrawler(keywords=SEARCH_KEYWORDS, days=DAYS)
    await crawler.start()


if __name__ == "__main__":
    asyncio.run(main())
