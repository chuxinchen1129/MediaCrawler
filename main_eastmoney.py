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
from scheduler.eastmoney_scheduler import start_scheduler, stop_scheduler, crawl_eastmoney_reports
from feishu.eastmoney_bot import send_and_notify_reports
from tools import utils
from store.eastmoney.eastmoney_store_media import EastmoneyPdfStorage

# Add MediaCrawler root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config as eastmoney_config


async def manual_crawl(days: int = None):
    """
    手动执行爬取

    Args:
        days: 爬取天数
    """
    utils.logger.info("=" * 50)
    utils.logger.info("东方财富研报爬虫 - 手动执行模式")
    utils.logger.info("=" * 50)

    crawler = EastmoneyCrawler()

    # Set database config to ensure SQLite is used
    import config
    config.SAVE_DATA_OPTION = 'sqlite'

    try:
        # Crawl reports
        new_reports = await crawler.start(days=days)

        if new_reports and eastmoney_config.SEND_LIST_TO_FEISHU:
            # Send to Feishu
            from feishu.eastmoney_bot import send_and_notify_reports
            selected_infocodes = await send_and_notify_reports(new_reports)

            if selected_infocodes is not None and eastmoney_config.DELETE_UNSELECTED:
                # Move selected PDFs to target directory
                result = await crawler.move_selected_pdfs(selected_infocodes)
                utils.logger.info("移动了 " + str(len(result)) + " 份PDF到目标目录")
                utils.logger.info("目标目录: " + eastmoney_config.TARGET_PDF_DIR)

        utils.logger.info("=" * 50)
        utils.logger.info("爬取完成！")

    except KeyboardInterrupt:
        utils.logger.info("\n用户中断，程序退出")
        sys.exit(0)
    except Exception as e:
        utils.logger.error(f"爬取过程中发生错误: {e}", exc_info=True)
        sys.exit(1)


async def run_scheduler():
    """
    启动定时调度器
    """
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


async def run_feishu_listener():
    """
    启动飞书监听器（用于等待用户回复）
    注意：当前实现为演示模式，实际需要配置飞书应用ID和密钥以监听用户回复
    """
    utils.logger.info("=" * 50)
    utils.logger.info("东方财富研报爬虫 - 飞书监听模式")
    utils.logger.info("=" * 50)

    utils.logger.info("警告：当前为演示模式，实际需要配置飞书应用ID和密钥以监听用户回复")
    utils.logger.info("配置以下参数后重新启动：")
    app_id_display = eastmoney_config.FEISHU_APP_ID or "(未配置）"
    app_secret_display = eastmoney_config.FEISHU_APP_SECRET or "(未配置）"
    utils.logger.info(f"   FEISHU_APP_ID: {app_id_display}")
    utils.logger.info(f"   FEISHU_APP_SECRET: {app_secret_display}")

    bot = EastmoneyFeishuBot()

    try:
        # 这里应该是一个持续监听用户的回复
        # 实际实现需要使用飞书事件订阅或webhook
        utils.logger.info("监听器已启动，等待用户通过飞书回复...")

        # 模拟监听（实际应使用飞书SDK的事件监听）
        while True:
            await asyncio.sleep(10)

    except KeyboardInterrupt:
        utils.logger.info("\n用户中断，监听器停止")
        sys.exit(0)
    except Exception as e:
        utils.logger.error(f"监听器运行中发生错误: {e}", exc_info=True)
        sys.exit(1)


def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="东方财富网研报PDF爬取工具",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help=f"爬取天数（默认: {eastmoney_config.DEFAULT_DAYS}）"
    )

    parser.add_argument(
        "--scheduler",
        action="store_true",
        help="启动定时调度器（每日凌晨2点自动执行）"
    )

    parser.add_argument(
        "--listen",
        action="store_true",
        help="启动飞书监听器，等待用户回复选择"
    )

    args = parser.parse_args()

    if args.scheduler:
        # Run in scheduler mode
        asyncio.run(run_scheduler())
    elif args.listen:
        # Run in Feishu listener mode
        asyncio.run(run_feishu_listener())
    else:
        # Default: manual crawl mode
        asyncio.run(manual_crawl(days=args.days))


if __name__ == "__main__":
    main()
