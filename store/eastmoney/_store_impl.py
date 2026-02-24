# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/store/eastmoney/_store_impl.py
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
from datetime import datetime
from typing import Dict, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from base.base_crawler import AbstractStore
from database.db_session import get_session
from database.models import EastmoneyReport
from tools.time_util import get_current_timestamp
from tools.async_file_writer import AsyncFileWriter
from tools import utils
from var import source_keyword_var
from database.mongodb_store_base import MongoDBStoreBase
from store.excel_store_base import ExcelStoreBase
import config as eastmoney_config


class EastmoneyCsvStoreImplement(AbstractStore):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.writer = AsyncFileWriter(platform="eastmoney", crawler_type="eastmoney")

    async def store_content(self, content_item: Dict):
        """
        store content data to csv file
        :param content_item:
        :return:
        """
        await self.writer.write_to_csv(item_type="reports", item=content_item)

    def flush(self):
        pass

    async def store_comment(self, comment_item: Dict):
        """Eastmoney doesn't support comments"""
        pass

    async def store_creator(self, creator: Dict):
        """Eastmoney doesn't support creator storage"""
        pass


class EastmoneyJsonStoreImplement(AbstractStore):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.writer = AsyncFileWriter(platform="eastmoney", crawler_type="eastmoney")

    async def store_content(self, content_item: Dict):
        """
        store content data to json file
        :param content_item:
        :return:
        """
        await self.writer.write_single_item_to_json(item_type="reports", item=content_item)

    def flush(self):
        pass

    async def store_comment(self, comment_item: Dict):
        """Eastmoney doesn't support comments"""
        pass

    async def store_creator(self, creator: Dict):
        """Eastmoney doesn't support creator storage"""
        pass


class EastmoneySqliteStoreImplement(AbstractStore):
    async def store_content(self, content_item: Dict):
        """
        store content data to sqlite database
        :param content_item:
        :return:
        """
        infocode = content_item.get("infocode")
        if not infocode:
            return

        async with get_session() as session:
            if await self.report_is_exist(session, infocode):
                await self.update_report(session, content_item)
            else:
                await self.add_report(session, content_item)

    async def add_report(self, session: AsyncSession, content_item: Dict):
        """Add a new report to database"""
        current_time = int(get_current_timestamp())
        report = EastmoneyReport(
            infocode=content_item.get("infocode"),
            report_title=content_item.get("report_title", ""),
            org_name=content_item.get("org_name", ""),
            analyst=content_item.get("analyst", ""),
            publish_date=content_item.get("publish_date", ""),
            industry=content_item.get("industry", ""),
            stock_code=content_item.get("stock_code", ""),
            rating=content_item.get("rating", ""),
            pdf_url=content_item.get("pdf_url", ""),
            pdf_path=content_item.get("pdf_path", ""),
            pdf_size=content_item.get("pdf_size", 0),
            pdf_pages=content_item.get("pdf_pages", 0),
            attach_type=content_item.get("attach_type", ""),
            download_status=content_item.get("download_status", "pending"),
            error_message=content_item.get("error_message", ""),
            create_time=current_time,
            update_time=current_time,
        )
        session.add(report)
        utils.logger.info(f"[EastmoneyStore] Added report: {content_item.get('infocode')}")

    async def update_report(self, session: AsyncSession, content_item: Dict):
        """Update an existing report"""
        current_time = int(get_current_timestamp())
        update_data = {
            "update_time": current_time,
        }

        # Only update specific fields if provided
        if "pdf_path" in content_item:
            update_data["pdf_path"] = content_item["pdf_path"]
        if "download_status" in content_item:
            update_data["download_status"] = content_item["download_status"]
        if "error_message" in content_item:
            update_data["error_message"] = content_item["error_message"]
        if "pdf_size" in content_item:
            update_data["pdf_size"] = content_item["pdf_size"]
        if "pdf_pages" in content_item:
            update_data["pdf_pages"] = content_item["pdf_pages"]

        infocode = content_item.get("infocode")
        stmt = update(EastmoneyReport).where(EastmoneyReport.infocode == infocode).values(**update_data)
        await session.execute(stmt)
        utils.logger.info(f"[EastmoneyStore] Updated report: {infocode}")

    async def update_pdf_status(self, infocode: str, status: str, pdf_path: str = "", error_message: str = ""):
        """Update PDF download status"""
        async with get_session() as session:
            current_time = int(get_current_timestamp())
            update_data = {
                "download_status": status,
                "update_time": current_time,
            }

            if pdf_path:
                update_data["pdf_path"] = pdf_path
            if error_message:
                update_data["error_message"] = error_message

            stmt = update(EastmoneyReport).where(EastmoneyReport.infocode == infocode).values(**update_data)
            await session.execute(stmt)
            utils.logger.info(f"[EastmoneyStore] Updated PDF status for {infocode}: {status}")

    async def report_is_exist(self, session: AsyncSession, infocode: str) -> bool:
        """Check if report exists"""
        stmt = select(EastmoneyReport).where(EastmoneyReport.infocode == infocode)
        result = await session.execute(stmt)
        return result.first() is not None

    def flush(self):
        pass

    async def store_comment(self, comment_item: Dict):
        """Eastmoney doesn't support comments"""
        pass

    async def store_creator(self, creator: Dict):
        """Eastmoney doesn't support creator storage"""
        pass


class EastmoneyMongoStoreImplement(MongoDBStoreBase):
    pass


class EastmoneyExcelStoreImplement(ExcelStoreBase):
    pass


class EastmoneyPdfStorage:
    """PDF file storage handler"""

    def __init__(self):
        self.pdf_save_dir = eastmoney_config.PDF_SAVE_DIR
        self.target_dir = eastmoney_config.TARGET_PDF_DIR

    def _ensure_dir(self, path: str):
        """Ensure directory exists"""
        os.makedirs(path, exist_ok=True)

    async def store_pdf(self, pdf_data: dict) -> str:
        """
        Save PDF file to storage directory

        Args:
            pdf_data: dict with keys "infocode", "pdf_content", "extension_file_name"

        Returns:
            saved file path
        """
        infocode = pdf_data.get("infocode")
        pdf_content = pdf_data.get("pdf_content")
        extension = pdf_data.get("extension_file_name", ".pdf")

        if not pdf_content or not infocode:
            return ""

        # Ensure save directory exists
        self._ensure_dir(self.pdf_save_dir)

        # Save to temp directory first
        file_path = os.path.join(self.pdf_save_dir, f"{infocode}{extension}")
        with open(file_path, "wb") as f:
            f.write(pdf_content)

        utils.logger.info(f"[EastmoneyPdfStorage] Saved PDF to: {file_path}")

        return file_path

    async def move_to_target(self, infocodes: list[str]) -> dict[str, str]:
        """
        Move selected PDFs to target directory and delete others

        Args:
            infocodes: list of infocodes to keep

        Returns:
            dict mapping infocode -> target file path
        """
        self._ensure_dir(self.target_dir)

        # Get all PDF files in save directory
        all_files = [f for f in os.listdir(self.pdf_save_dir) if f.endswith(".pdf")]

        result = {}

        for filename in all_files:
            infocode = filename.replace(".pdf", "")

            if infocode in infocodes:
                # Move to target directory
                src_path = os.path.join(self.pdf_save_dir, filename)
                target_path = os.path.join(self.target_dir, f"{infocode}.pdf")

                try:
                    os.rename(src_path, target_path)
                    result[infocode] = target_path
                    utils.logger.info(f"[EastmoneyPdfStorage] Moved {filename} to target directory")
                except FileExistsError:
                    # Target file already exists, try to overwrite
                    os.remove(target_path)
                    os.rename(src_path, target_path)
                    result[infocode] = target_path
                    utils.logger.warning(f"[EastmoneyPdfStorage] Overwrote existing file: {target_path}")
            else:
                # Delete unselected file
                src_path = os.path.join(self.pdf_save_dir, filename)
                try:
                    os.remove(src_path)
                    utils.logger.info(f"[EastmoneyPdfStorage] Deleted unselected: {filename}")
                except OSError as e:
                    utils.logger.error(f"[EastmoneyPdfStorage] Failed to delete {filename}: {e}")

        return result
