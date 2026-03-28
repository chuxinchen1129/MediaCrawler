# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
#

import os
import asyncio
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

import config.eastmoney_config as eastmoney_config
from tools import utils
from database.db_session import get_session
from database.models import EastmoneyReport
from sqlalchemy import select

# PDF页数检测库
PDF_LIB = None
try:
    import fitz  # pymupdf
    PDF_LIB = 'pymupdf'
except ImportError:
    pass

if not PDF_LIB:
    try:
        import PyPDF2
        PDF_LIB = 'pypdf2'
    except ImportError:
        pass

if not PDF_LIB:
    try:
        import pdfplumber
        PDF_LIB = 'pdfplumber'
    except ImportError:
        pass

def get_pdf_page_count(pdf_path: str) -> int:
    """
    获取PDF页数

    Args:
        pdf_path: PDF文件路径

    Returns:
        PDF页数，如果无法读取返回0
    """
    try:
        if PDF_LIB == 'pymupdf':
            import fitz
            doc = fitz.open(pdf_path)
            return doc.page_count
        elif PDF_LIB == 'pypdf2':
            import PyPDF2
            with open(pdf_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                return len(reader.pages)
        elif PDF_LIB == 'pdfplumber':
            import pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                return len(pdf.pages)
        return 0
    except Exception as e:
        utils.logger.warning(f"[EastmoneyPdfStorage] Failed to get page count for {pdf_path}: {e}")
        return 0


class EastmoneyPdfStorageImpl:
    """PDF file storage handler implementation"""

    def __init__(self):
        # Ensure we use sqlite for database queries
        import config
        config.SAVE_DATA_OPTION = 'sqlite'

        self.pdf_save_dir = eastmoney_config.PDF_SAVE_DIR
        self.target_dir = eastmoney_config.TARGET_PDF_DIR
        self.min_page_count = getattr(eastmoney_config, 'MIN_PAGE_COUNT', 10)

    def _ensure_dir(self, path: str):
        """Ensure directory exists"""
        os.makedirs(path, exist_ok=True)

    def _sanitize_filename_part(self, value: str, max_length: int) -> str:
        cleaned = re.sub(r'[\\/:*?"<>|\n\r\t]', '_', value or "")
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" ._")
        return cleaned[:max_length]

    def _build_filename(self, org_name: str, report_title: str, infocode: str, extension: str) -> str:
        safe_org = self._sanitize_filename_part(org_name, 40)
        safe_title = self._sanitize_filename_part(report_title, 120)

        if safe_org and safe_title:
            return f"{safe_org}+{safe_title}{extension}"
        if safe_title:
            return f"{safe_title}{extension}"
        if safe_org:
            return f"{safe_org}+{infocode}{extension}"
        return f"{infocode}{extension}"

    async def store_pdf(self, pdf_data: dict) -> str:
        """
        Save PDF file to storage directory and check page count

        Args:
            pdf_data: dict with keys "infocode", "pdf_content", "extension_file_name"

        Returns:
            saved file path (empty if deleted due to low page count)
        """
        infocode = pdf_data.get("infocode")
        pdf_content = pdf_data.get("pdf_content")
        extension = pdf_data.get("extension_file_name", ".pdf")
        report_title = pdf_data.get("report_title", "")
        org_name = pdf_data.get("org_name", "")

        if not pdf_content or not infocode:
            return ""

        # Ensure save directory exists
        self._ensure_dir(self.pdf_save_dir)

        filename = self._build_filename(org_name, report_title, infocode, extension)

        # Ensure filename is unique
        file_path = os.path.join(self.pdf_save_dir, filename)
        if os.path.exists(file_path):
            base, ext = os.path.splitext(filename)
            file_path = os.path.join(self.pdf_save_dir, f"{base}_{infocode[:8]}{ext}")
        with open(file_path, "wb") as f:
            f.write(pdf_content)

        # Check page count
        page_count = get_pdf_page_count(file_path)

        if page_count < self.min_page_count:
            # Auto-delete PDFs with less than MIN_PAGE_COUNT pages
            try:
                os.remove(file_path)
                utils.logger.info(f"[EastmoneyPdfStorage] Deleted {infocode} (only {page_count} pages, < {self.min_page_count} pages)")
                return ""  # Return empty to indicate deleted
            except OSError as e:
                utils.logger.error(f"[EastmoneyPdfStorage] Failed to delete {file_path}: {e}")
                return file_path

        utils.logger.info(f"[EastmoneyPdfStorage] Saved PDF to: {file_path} ({page_count} pages)")
        return file_path

    async def move_to_target(self, infocodes: list[str]) -> dict:
        """
        Move selected PDFs to target directory with auto renaming

        Args:
            infocodes: list of infocodes to keep

        Returns:
            dict with structure: {
                'success': bool,
                'moved_paths': [{'infocode': str, 'source_path': str, 'target_path': str}],
                'moved_count': int,
                'deleted_count': int
            }
        """
        self._ensure_dir(self.target_dir)

        # Get all PDF files in save directory
        all_files = [f for f in os.listdir(self.pdf_save_dir) if f.endswith(".pdf")]

        moved_paths = []
        deleted_count = 0
        result = {}
        selected_reports = {}

        try:
            async with get_session() as session:
                if session is not None and infocodes:
                    stmt = select(EastmoneyReport).where(EastmoneyReport.infocode.in_(infocodes))
                    db_result = await session.execute(stmt)
                    for report in db_result.scalars().all():
                        pdf_basename = os.path.basename(report.pdf_path or "")
                        if pdf_basename:
                            selected_reports[pdf_basename] = report
        except Exception as e:
            utils.logger.warning(f"[EastmoneyPdfStorage] Failed to preload selected reports: {e}")

        for filename in all_files:
            report = selected_reports.get(filename)
            infocode = report.infocode if report else filename.replace(".pdf", "")

            if report is not None:
                # Check page count before moving
                file_path = os.path.join(self.pdf_save_dir, filename)
                page_count = get_pdf_page_count(file_path)

                if page_count >= self.min_page_count:
                    org_name = report.org_name or ""
                    report_title = report.report_title or ""
                    new_filename = self._build_filename(org_name, report_title, infocode, ".pdf")

                    # Move to target directory with new name
                    src_path = os.path.join(self.pdf_save_dir, filename)
                    target_path = os.path.join(self.target_dir, new_filename)

                    try:
                        shutil.move(src_path, target_path)
                        result[infocode] = target_path
                        moved_paths.append({
                            'infocode': infocode,
                            'source_path': src_path,
                            'target_path': target_path
                        })
                        utils.logger.info(f"[EastmoneyPdfStorage] Moved & renamed: {filename} -> {new_filename}")
                    except FileExistsError:
                        # Target file already exists, try to overwrite
                        os.remove(target_path)
                        shutil.move(src_path, target_path)
                        result[infocode] = target_path
                        moved_paths.append({
                            'infocode': infocode,
                            'source_path': src_path,
                            'target_path': target_path
                        })
                        utils.logger.warning(f"[EastmoneyPdfStorage] Overwrote existing file: {new_filename}")
                else:
                    # Delete file with low page count
                    src_path = os.path.join(self.pdf_save_dir, filename)
                    try:
                        os.remove(src_path)
                        deleted_count += 1
                        utils.logger.info(f"[EastmoneyPdfStorage] Deleted low-page PDF: {filename} ({page_count} pages)")
                    except OSError as e:
                        utils.logger.error(f"[EastmoneyPdfStorage] Failed to delete {filename}: {e}")
            else:
                # Delete unselected file
                src_path = os.path.join(self.pdf_save_dir, filename)
                try:
                    os.remove(src_path)
                    deleted_count += 1
                    utils.logger.info(f"[EastmoneyPdfStorage] Deleted unselected: {filename}")
                except OSError as e:
                    utils.logger.error(f"[EastmoneyPdfStorage] Failed to delete {filename}: {e}")

        return {
            'success': True,
            'moved_paths': moved_paths,
            'moved_count': len(moved_paths),
            'deleted_count': deleted_count
        }
