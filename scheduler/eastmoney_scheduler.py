# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/scheduler/eastmoney_scheduler.py
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
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from media_platform.eastmoney.core import EastmoneyCrawler
from feishu.eastmoney_bot import send_and_notify_reports
from tools import utils
import config as eastmoney_config


scheduler = AsyncIOScheduler()
crawler: EastmoneyCrawler = None


async def crawl_eastmoney_reports(days: int = None):
    """
    爬取东方财富研报并发送到飞书

    Args:
        days: 爬取天数，默认从配置获取
    """
    global crawler

    if days is None:
        days = eastmoney_config.DEFAULT_DAYS

    utils.logger.info(f"[Scheduler] Scheduled crawl started, days={days}")

    if not crawler:
        crawler = EastmoneyCrawler()

    try:
        # Crawl reports
        new_reports = await crawler.start(days=days)

        if new_reports and eastmoney_config.SEND_LIST_TO_FEISHU:
            utils.logger.info(f"[Scheduler] Sending {len(new_reports)} reports to Feishu")

            # Send to Feishu and wait for selection
            selected_infocodes = await send_and_notify_reports(new_reports)

            if selected_infocodes is not None:
                # Move selected PDFs to target directory
                result = await crawler.move_selected_pdfs(selected_infocodes)
                utils.logger.info(f"[Scheduler] Moved {len(result)} PDFs to target directory")
            else:
                utils.logger.info("[Scheduler] No user selection received")

        utils.logger.info("[Scheduler] Scheduled crawl completed")

    except Exception as e:
        utils.logger.error(f"[Scheduler] Error during scheduled crawl: {e}", exc_info=True)


async def scheduled_crawl_job():
    """
    定时爬取任务（每日早上8点执行）
    """
    today = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    utils.logger.info(f"[Scheduler] Scheduled job triggered at {today}")

    # Step 1: Crawl reports
    await crawl_eastmoney_reports()

    # Step 2: Start listening for user response (timeout at 8:15)
    utils.logger.info("[Scheduler] Starting Feishu listener (15 min timeout)")
    utils.logger.info("[Scheduler] Will auto-delete unselected PDFs at 08:15 if no response")

    try:
        # Wait for user response with timeout
        import asyncio
        from feishu.eastmoney_bot import EastmoneyFeishuBot

        bot = EastmoneyFeishuBot()

        # Listen for 15 minutes (900 seconds)
        # In production, this would use actual Feishu webhook/event subscription
        # For now, we use a simple timeout mechanism
        wait_time = 15 * 60  # 15 minutes

        utils.logger.info(f"[Scheduler] Listening for {wait_time} seconds...")

        # TODO: Replace with actual Feishu event listener
        # For now, just wait and then clean up unselected PDFs
        await asyncio.sleep(wait_time)

        utils.logger.info("[Scheduler] Timeout reached, cleaning up unselected PDFs")

        # If no response received, delete all PDFs
        from store.eastmoney._store_impl import EastmoneyPdfStorage
        storage = EastmoneyPdfStorage()
        await storage.move_to_target([])  # Empty selection = delete all

        utils.logger.info("[Scheduler] Auto-cleanup completed")

    except Exception as e:
        utils.logger.error(f"[Scheduler] Error during listener: {e}", exc_info=True)


async def start_scheduler():
    """启动调度器"""
    if not scheduler.running:
        # Add scheduled job: 每天早上7点执行
        scheduler.add_job(
            scheduled_crawl_job,
            CronTrigger(hour=8, minute=0),
            id='eastmoney_daily_crawl',
            name='东方财富研报每日爬取',
            replace_existing=True
        )

        scheduler.start()
        utils.logger.info("[Scheduler] Eastmoney scheduler started")
        utils.logger.info("[Scheduler] Next scheduled run: Daily at 08:00")

        # Run the scheduler
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            utils.logger.info("[Scheduler] Scheduler stopped")
            scheduler.shutdown()
    else:
        utils.logger.warning("[Scheduler] Scheduler is already running")


async def stop_scheduler():
    """停止调度器"""
    if scheduler.running:
        scheduler.shutdown()
        utils.logger.info("[Scheduler] Eastmoney scheduler stopped")
