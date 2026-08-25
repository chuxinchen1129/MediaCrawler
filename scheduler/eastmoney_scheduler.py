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
from tools import utils
import config.eastmoney_config as eastmoney_config


scheduler = AsyncIOScheduler()
crawler: EastmoneyCrawler = None


async def crawl_eastmoney_reports(days: int = None):
    """
    爬取东方财富研报，下载后全部移到目标目录（不经飞书选择）。

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
        await crawler.start(days=days)
        result = await crawler.move_all_pdfs()
        utils.logger.info(f"[Scheduler] 移动 {result['moved']} 份 PDF 到 {result['target']}")
        utils.logger.info("[Scheduler] Scheduled crawl completed")

    except Exception as e:
        utils.logger.error(f"[Scheduler] Error during scheduled crawl: {e}", exc_info=True)


async def scheduled_crawl_job():
    """定时爬取任务（每日 09:10 执行）"""
    today = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    utils.logger.info(f"[Scheduler] Scheduled job triggered at {today}")
    await crawl_eastmoney_reports()


async def start_scheduler():
    """启动调度器"""
    if not scheduler.running:
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
