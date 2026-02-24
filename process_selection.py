#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
处理用户选择的研报
使用方法: python3 process_selection.py "1,2,3" 或 python3 process_selection.py "all"
"""

import asyncio
import sys
import os

sys.path.insert(0, '/Users/echochen/MediaCrawler')

import config
config.SAVE_DATA_OPTION = 'sqlite'

from media_platform.eastmoney.core import EastmoneyCrawler
import time
from sqlalchemy import select
from database.db_session import get_session
from database.models import EastmoneyReport


async def get_recent_reports():
    """获取最近的研报列表"""
    threshold_timestamp = int(time.time()) - (1 * 24 * 60 * 60)  # Last 1 day

    async with get_session() as session:
        stmt = select(EastmoneyReport).where(
            EastmoneyReport.create_time >= threshold_timestamp,
            EastmoneyReport.download_status == "completed"
        ).order_by(EastmoneyReport.create_time.desc())
        result = await session.execute(stmt)
        reports = result.scalars().all()

        return reports


async def process_selection(selection_text: str):
    """处理用户选择"""
    selection_text = selection_text.strip().lower()

    # Get recent reports
    reports = await get_recent_reports()

    if not reports:
        print("❌ 没有找到最近的研报")
        return

    # Display current reports
    print("=" * 60)
    print("最近的研报列表：")
    print("=" * 60)
    for i, report in enumerate(reports, 1):
        print(f"{i}. [{report.org_name}] {report.report_title} - {report.pdf_pages}页")
    print("=" * 60)

    # Parse selection
    if selection_text in ["all", "全部", "全部保留"]:
        selected_indices = list(range(1, len(reports) + 1))
    elif selection_text in ["delete", "全部删除", "delete all"]:
        selected_indices = []
    else:
        # Parse comma-separated numbers
        parts = selection_text.replace("，", ",").split(",")
        selected_indices = []
        for part in parts:
            part = part.strip()
            if part.isdigit():
                idx = int(part)
                if 1 <= idx <= len(reports):
                    selected_indices.append(idx)

    if not selected_indices:
        print("⚠️  未选择任何研报，将删除所有PDF")
        confirm = input("确认删除所有? (yes/no): ")
        if confirm.lower() != 'yes':
            print("已取消")
            return
        selected_infocodes = []
    else:
        print(f"\n将保留以下研报: {selected_indices}")
        confirm = input("确认? (yes/no): ")
        if confirm.lower() != 'yes':
            print("已取消")
            return

        # Map indices to infocodes
        selected_infocodes = []
        for idx in selected_indices:
            selected_infocodes.append(reports[idx - 1].infocode)

    # Process
    print(f"\n处理中...")
    crawler = EastmoneyCrawler()
    result = await crawler.move_selected_pdfs(selected_infocodes)

    print(f"\n✅ 处理完成！")
    print(f"保留: {len(result)} 份")
    print(f"删除: {len(reports) - len(result)} 份")
    print(f"\n目标目录: {config.TARGET_PDF_DIR}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python3 process_selection.py \"1,2,3\"  - 保留第1,2,3份")
        print("  python3 process_selection.py \"all\"     - 保留所有")
        print("  python3 process_selection.py \"delete\"  - 删除所有")
        sys.exit(1)

    asyncio.run(process_selection(sys.argv[1]))
