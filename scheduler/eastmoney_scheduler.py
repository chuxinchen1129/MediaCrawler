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
from feishu.eastmoney_bot import send_and_notify_reports, EastmoneyFeishuBot
from tools import utils
import config as eastmoney_config


scheduler = AsyncIOScheduler()
crawler: EastmoneyCrawler = None


async def _send_completion_notification(selected_count: int, total_count: int):
    """发送完成通知到飞书"""
    bot = EastmoneyFeishuBot()
    message = (
        f"✅ 东方财富研报处理完成\n\n"
        f"已保留 {selected_count}/{total_count} 份研报\n\n"
        f"已移动到报告喵文件夹"
    )
    await bot._send_via_script_notifier(message)


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

            # Send to Feishu and wait for selection (15 minute timeout)
            selected_infocodes = await send_and_notify_reports(new_reports, timeout_minutes=15)

            if selected_infocodes is not None:
                # Move selected PDFs to target directory
                result = await crawler.move_selected_pdfs(selected_infocodes)
                utils.logger.info(f"[Scheduler] Moved {len(result)} PDFs to target directory")

                # Send completion notification
                if selected_infocodes:
                    await _send_completion_notification(len(selected_infocodes), len(new_reports))
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

    # Crawl reports and wait for user selection
    await crawl_eastmoney_reports()

async def start_scheduler():
    """启动调度器"""
    if not scheduler.running:
        # Add scheduled job: 每天早上7点执行
        scheduler.add_job(
            scheduled_crawl_job,
            CronTrigger(hour=9, minute=10),
            id='eastmoney_daily_crawl',
            name='东方财富研报每日爬取',
            replace_existing=True
        )

        scheduler.start()
        utils.logger.info("[Scheduler] Eastmoney scheduler started")
        utils.logger.info("[Scheduler] Next scheduled run: Daily at 09:10")

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
