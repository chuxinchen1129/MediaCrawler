# -*- coding: utf-8 -*-
"""一次性脚本：不过滤、全量爬取东方财富过去 N 天研报（含「不感兴趣」的短报告/周报点评等）。

绕过 core.py 的 _filter_reports（页数≥15、排除关键词）和 start() 的 max_notes=250 上限，
自己驱动分页循环，抓完所有页、下载所有 PDF。
"""
import asyncio
import sys

from media_platform.eastmoney.core import EastmoneyCrawler
import config.eastmoney_config as cfg

# 关闭下载后的页数自动删除（EastmoneyPdfStorageImpl.__init__ 读取此值并缓存到实例）
# 配合本脚本不调用 _filter_reports，实现"不过滤、全量保留所有研报"
cfg.MIN_PAGE_COUNT = 0


async def main(days: int):
    crawler = EastmoneyCrawler()
    begin_date, end_date = crawler.client.get_date_range(days)
    print(f"[Crawl-ALL] days={days}, range={begin_date} ~ {end_date} (NO filter)")
    total = 0
    for q_type in cfg.Q_TYPE_LIST:
        type_name = "公司研报" if q_type == "0" else "行业研报"
        print(f"=== {type_name} (qType={q_type}) ===")
        page_no = 1
        while True:
            try:
                reports = await crawler.client.fetch_report_list(
                    page_no=page_no, begin_date=begin_date, end_date=end_date, q_type=q_type
                )
            except Exception as e:
                print(f"[Crawl-ALL] fetch {type_name} page {page_no} failed: {e}")
                break
            if not reports:
                print(f"[Crawl-ALL] No more {type_name} on page {page_no}")
                break
            print(f"[Crawl-ALL] {type_name} page {page_no}: {len(reports)} reports (no filter)")
            for r in reports:
                try:
                    await crawler._process_report(r)
                except Exception as e:
                    print(f"[Crawl-ALL] process report failed: {e}")
            total += len(reports)
            page_no += 1
            await asyncio.sleep(cfg.REQUEST_INTERVAL)
    print(f"=== [Crawl-ALL] DONE. Total reports processed: {total} ===")


if __name__ == "__main__":
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    asyncio.run(main(days))
