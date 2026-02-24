# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/eastmoney/client.py
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
import config.eastmoney_config as eastmoney_config
import json
import random
import re
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from urllib.parse import urlencode

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

import config as eastmoney_config
from tools import utils
from .exception import DataFetchError, APIRequestError, JSONPParseError


class EastmoneyClient:
    """东方财富API客户端"""

    def __init__(self):
        self.api_base_url = eastmoney_config.API_BASE_URL
        self.pdf_base_url = eastmoney_config.PDF_BASE_URL
        self.q_type = eastmoney_config.Q_TYPE
        self.default_cb_prefix = eastmoney_config.DEFAULT_CB_PREFIX
        self.timeout = eastmoney_config.API_REQUEST_TIMEOUT

    def _generate_callback(self) -> str:
        """生成随机JSONP回调参数"""
        random_num = random.randint(100000, 999999)
        return f"{self.default_cb_prefix}{random_num}"

    def _parse_jsonp_response(self, response_text: str) -> dict:
        """解析JSONP响应，提取括号内内容"""
        try:
            # JSONP格式如: datatable123456({...})
            # 找到第一个左括号和对应的右括号
            start_idx = response_text.find('{')
            if start_idx == -1:
                raise JSONPParseError(f"无法找到JSON开始标记: {response_text[:100]}")

            # 从后往前找匹配的右括号
            depth = 0
            for i in range(start_idx, len(response_text)):
                if response_text[i] == '{':
                    depth += 1
                elif response_text[i] == '}':
                    depth -= 1
                    if depth == 0:
                        json_str = response_text[start_idx:i+1]
                        return json.loads(json_str)

            raise JSONPParseError(f"无法找到匹配的JSON结束标记: {response_text[:100]}")
        except json.JSONDecodeError as e:
            raise JSONPParseError(f"JSON解析失败: {e}")

    @retry(stop=stop_after_attempt(eastmoney_config.MAX_RETRIES),
           wait=wait_exponential(multiplier=1, min=2, max=10))
    async def fetch_report_list(
        self,
        page_no: int = 1,
        begin_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page_size: int = 50
    ) -> List[Dict]:
        """
        获取研报列表

        Args:
            page_no: 页码
            begin_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            page_size: 每页数量

        Returns:
            研报列表数据

        Raises:
            APIRequestError: API请求失败
            DataFetchError: 数据获取失败
        """
        # 生成JSONP回调参数
        callback = self._generate_callback()

        # 构造请求参数
        params = {
            "cb": callback,
            "pageNo": page_no,
            "pageSize": page_size,
            "qType": self.q_type,
        }

        # 添加日期范围参数（如果提供）
        if begin_date:
            params["beginTime"] = begin_date
        if end_date:
            params["endTime"] = end_date

        full_url = f"{self.api_base_url}?{urlencode(params)}"

        utils.logger.info(
            f"[EastmoneyClient] Fetching report list: page={page_no}, "
            f"begin={begin_date}, end={end_date}"
        )

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(full_url)
                response.raise_for_status()

                if response.status_code == 500:
                    raise APIRequestError(
                        f"API返回500错误，可能是qType参数缺失或格式错误"
                    )

                response_text = response.text
                utils.logger.debug(f"[EastmoneyClient] Raw response: {response_text[:500]}")

                # 解析JSONP响应
                data = self._parse_jsonp_response(response_text)

                # API实际响应格式: {"hits":9,"size":5,"data":[{...}]}
                # 直接从data获取报告列表
                report_list = data.get("data", [])
                total_count = data.get("hits", 0)

                utils.logger.info(
                    f"[EastmoneyClient] Fetched {len(report_list)} reports "
                    f"(total: {total_count}) for page {page_no}"
                )

                return report_list

        except httpx.HTTPStatusError as e:
            raise APIRequestError(f"HTTP状态错误: {e.response.status_code}")
        except httpx.RequestError as e:
            raise APIRequestError(f"请求错误: {e}")
        except httpx.TimeoutException as e:
            raise APIRequestError(f"请求超时: {e}")

    def get_pdf_url(self, infocode: str) -> str:
        """
        构造PDF下载URL

        Args:
            infocode: 研报唯一标识码

        Returns:
            PDF下载URL
        """
        # 格式: https://pdf.dfcfw.com/pdf/H3_{infocode}_1.pdf
        return f"{self.pdf_base_url}/H3_{infocode}_1.pdf"

    @retry(stop=stop_after_attempt(eastmoney_config.MAX_RETRIES),
           wait=wait_exponential(multiplier=1, min=2, max=10))
    async def download_pdf(
        self,
        infocode: str,
        save_path: str
    ) -> Optional[bytes]:
        """
        下载PDF文件

        Args:
            infocode: 研报唯一标识码
            save_path: 本地保存路径

        Returns:
            PDF文件内容(bytes)，失败返回None

        Raises:
            PDFDownloadError: PDF下载失败
        """
        pdf_url = self.get_pdf_url(infocode)

        utils.logger.info(f"[EastmoneyClient] Downloading PDF: {infocode} from {pdf_url}")

        try:
            async with httpx.AsyncClient(
                timeout=eastmoney_config.PDF_DOWNLOAD_TIMEOUT
            ) as client:
                # 先发送HEAD请求检查文件是否存在
                try:
                    head_response = await client.head(pdf_url)
                    head_response.raise_for_status()
                    content_length = head_response.headers.get("content-length", "0")
                    utils.logger.debug(f"[EastmoneyClient] PDF size: {content_length} bytes")
                except httpx.HTTPStatusError:
                    # HEAD请求失败，直接尝试GET
                    pass

                # 下载PDF
                response = await client.get(pdf_url)
                response.raise_for_status()

                # 检查是否为有效的PDF
                content_type = response.headers.get("content-type", "")
                if "application/pdf" not in content_type and "pdf" not in content_type.lower():
                    utils.logger.warning(
                        f"[EastmoneyClient] 响应可能不是PDF: {content_type}"
                    )

                utils.logger.info(f"[EastmoneyClient] PDF downloaded: {len(response.content)} bytes")

                return response.content

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                utils.logger.error(f"[EastmoneyClient] PDF不存在: {infocode}")
                return None
            raise PDFDownloadError(f"HTTP状态错误: {e.response.status_code}")
        except httpx.RequestError as e:
            raise PDFDownloadError(f"请求错误: {e}")
        except httpx.TimeoutException as e:
            raise PDFDownloadError(f"下载超时: {e}")

    def get_date_range(self, days: int) -> tuple[str, str]:
        """
        获取日期范围

        Args:
            days: 天数

        Returns:
            (开始日期, 结束日期) 格式为YYYY-MM-DD
        """
        today = datetime.now()
        end_date = today
        begin_date = today - timedelta(days=days)

        return (
            begin_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d")
        )
