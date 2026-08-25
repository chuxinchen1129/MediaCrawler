# -*- coding: utf-8 -*-
"""共享 PDF 下载器。

用 curl 子进程下载 PDF，绕过东方财富等站点的 JS 防护/TLS 指纹检测。
被 eastmoney、cbndata 等爬虫复用，避免下载逻辑分叉。
"""
import asyncio
from typing import Optional

from tools import utils
import config.eastmoney_config as eastmoney_config

_DEFAULT_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
               "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


async def download_pdf_bytes(
    pdf_url: str,
    referer: str = "https://data.eastmoney.com/",
    timeout: Optional[int] = None,
    user_agent: str = _DEFAULT_UA,
) -> Optional[bytes]:
    """下载 PDF，返回 bytes；失败（curl 错误/超时/非 PDF）返回 None。

    Args:
        pdf_url: PDF 直链
        referer: 请求 Referer 头（不同来源需要不同 Referer）
        timeout: 下载超时秒数，默认取 eastmoney_config.PDF_DOWNLOAD_TIMEOUT
        user_agent: UA
    """
    if timeout is None:
        timeout = eastmoney_config.PDF_DOWNLOAD_TIMEOUT

    try:
        proc = await asyncio.create_subprocess_exec(
            "curl", "-sL",
            "-H", f"User-Agent: {user_agent}",
            "-H", f"Referer: {referer}",
            "-o", "-",
            pdf_url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)

        if proc.returncode != 0:
            utils.logger.error(f"[pdf_downloader] curl 失败 ({pdf_url}): {stderr.decode()}")
            return None

        if not stdout[:5].startswith(b"%PDF"):
            utils.logger.warning(f"[pdf_downloader] 响应非有效PDF ({pdf_url})，前20字节: {stdout[:20]}")
            return None

        utils.logger.info(f"[pdf_downloader] 下载完成: {len(stdout)} bytes  {pdf_url}")
        return stdout

    except asyncio.TimeoutError:
        utils.logger.error(f"[pdf_downloader] 下载超时 ({timeout}s): {pdf_url}")
        return None
    except Exception as e:
        utils.logger.error(f"[pdf_downloader] 下载错误 ({pdf_url}): {e}")
        return None
