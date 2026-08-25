# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/main_eastmoney.py
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

import argparse
import asyncio
import sys
import os

from media_platform.eastmoney.core import EastmoneyCrawler
from scheduler.eastmoney_scheduler import start_scheduler, stop_scheduler
from tools import utils

# Add MediaCrawler root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config.eastmoney_config as eastmoney_config


async def manual_crawl(days: int = None, industry: str = None, keyword: str = None, sources: list = None):
    """
    手动执行爬取，下载后全部 PDF 移到目标目录（不经飞书选择）。

    Args:
        days: 爬取天数
        industry: 行业名（定向抓取，须在 INDUSTRY_CODE_MAP）
        keyword: 关键词（标题/摘要过滤）
        sources: 来源机构列表（irresearch/frost/cbndata）
    """
    utils.logger.info("=" * 50)
    utils.logger.info("东方财富研报爬虫 - 手动执行模式")
    utils.logger.info("=" * 50)

    crawler = EastmoneyCrawler()

    # Set database config to ensure SQLite is used
    import config
    config.SAVE_DATA_OPTION = 'sqlite'

    try:
        # Crawl reports（cbndata 走独立提示，不传给东方财富 orgName 过滤）
        eastmoney_sources = [s for s in (sources or []) if s != "cbndata"]
        await crawler.start(
            days=days, industry=industry, keyword=keyword, sources=eastmoney_sources
        )

        # 下载后全部移到目标目录（不经飞书选择）
        result = await crawler.move_all_pdfs()
        utils.logger.info(f"移动 {result['moved']} 份 PDF 到目标目录（跳过已存在 {result['skipped']} 份）")
        utils.logger.info("目标目录: " + eastmoney_config.TARGET_PDF_DIR)

        # CBNData：cbndata.com 报告为图片翻页预览+登录下载，无公开PDF直链，不支持自动抓取
        if sources and "cbndata" in sources:
            utils.logger.warning(
                "[main] --source cbndata 暂不支持自动抓取：CBNData 报告为图片预览+登录下载，无公开PDF直链。"
                "请手动访问 https://www.cbndata.com/report"
            )

        utils.logger.info("=" * 50)
        utils.logger.info("爬取完成！")

    except KeyboardInterrupt:
        utils.logger.info("\n用户中断，程序退出")
        sys.exit(0)
    except Exception as e:
        utils.logger.error(f"爬取过程中发生错误: {e}", exc_info=True)
        sys.exit(1)


async def run_scheduler():
    """启动定时调度器"""
    utils.logger.info("=" * 50)
    utils.logger.info("东方财富研报爬虫 - 定时调度模式")
    utils.logger.info("=" * 50)
    try:
        await start_scheduler()
    except KeyboardInterrupt:
        utils.logger.info("\n用户中断，正在停止调度器...")
        await stop_scheduler()
        sys.exit(0)
    except Exception as e:
        utils.logger.error(f"调度器运行中发生错误: {e}", exc_info=True)
        sys.exit(1)


def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="东方财富网研报PDF爬取工具",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("--days", type=int, default=None,
                        help=f"爬取天数（默认: {eastmoney_config.DEFAULT_DAYS}）")
    parser.add_argument("--industry", type=str, default=None,
                        help="定向抓取某行业（如 服装家纺）：公司研报用 industryCode 精确筛、行业研报用关键词。须在 INDUSTRY_CODE_MAP 中")
    parser.add_argument("--keyword", type=str, default=None,
                        help="额外关键词，按标题/摘要过滤（与 --industry 叠加为 AND）")
    parser.add_argument("--source", action="append", default=None,
                        help="来源机构，可重复：irresearch(艾瑞) / frost(头豹) / cbndata(CBNData，无公开PDF仅提示)")
    parser.add_argument("--list-industries", action="store_true",
                        help="打印 INDUSTRY_CODE_MAP 可用行业并退出")
    parser.add_argument("--scheduler", action="store_true",
                        help="启动定时调度器（每日 09:10 自动执行）")

    args = parser.parse_args()

    if args.list_industries:
        print("可用行业（INDUSTRY_CODE_MAP）：")
        for name in sorted(eastmoney_config.INDUSTRY_CODE_MAP):
            print(f"  {name} -> {eastmoney_config.INDUSTRY_CODE_MAP[name]}")
        return

    if args.scheduler:
        asyncio.run(run_scheduler())
    else:
        asyncio.run(manual_crawl(days=args.days, industry=args.industry,
                                 keyword=args.keyword, sources=args.source))


if __name__ == "__main__":
    main()
