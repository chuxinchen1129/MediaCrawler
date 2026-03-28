# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/feishu/eastmoney_bot.py
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
import requests
from typing import List, Dict, Optional
from datetime import datetime

from tools import utils
import config.eastmoney_config as eastmoney_config


class EastmoneyFeishuBot:
    """东方财富研报飞书交互机器人"""

    def __init__(self):
        self.chat_id = eastmoney_config.FEISHU_CHAT_ID
        self.running = False

    def _format_report_list_message(self, reports: List[Dict]) -> str:
        """
        格式化研报列表消息

        Args:
            reports: 研报列表

        Returns:
            格式化后的消息文本
        """
        lines = [
            "📊 东方财富研报下载完成",
            "",
            f"本周共下载 {len(reports)} 份研报：",
            ""
        ]

        for i, report in enumerate(reports, 1):
            org_name = report.get("org_name", "未知机构")
            title = report.get("title", "无标题")
            pages = report.get("pdf_pages", 0)
            infocode = report.get("infocode", "")

            lines.append(f"{i}. [{org_name}] {title} - {pages}页 ({infocode})")

        lines.extend([
            "",
            "请回复您要保留的研报编号（多个用逗号分隔）：",
            "例如：1,2,3",
            "",
            "或回复：全部保留 / 全部删除"
        ])

        return "\n".join(lines)

    async def process_user_selection(self, selection_text: str, all_infocodes: List[str]) -> List[str]:
        """
        处理用户选择，返回要保留的infocode列表

        Args:
            selection_text: 用户回复的文本
            all_infocodes: 所有可用的infocode列表

        Returns:
            要保留的infocode列表
        """
        selection_text = selection_text.strip().lower()

        # Handle special commands
        if selection_text == "全部保留" or selection_text == "all":
            utils.logger.info("[EastmoneyFeishuBot] User selected: all keep")
            return all_infocodes
        elif selection_text == "全部删除" or selection_text == "all delete" or selection_text == "delete all":
            utils.logger.info("[EastmoneyFeishuBot] User selected: all delete")
            return []
        elif selection_text == "取消" or selection_text == "cancel":
            utils.logger.info("[EastmoneyFeishuBot] User cancelled")
            return []

        # Parse comma-separated indices
        try:
            # Split by comma and extract numbers
            parts = selection_text.replace("，", ",").split(",")
            indices = []

            for part in parts:
                part = part.strip()
                if part.isdigit():
                    idx = int(part) - 1  # Convert to 0-indexed
                    if 0 <= idx < len(all_infocodes):
                        indices.append(idx)

            # Convert indices to infocodes
            selected_infocodes = [all_infocodes[i] for i in indices]

            utils.logger.info(f"[EastmoneyFeishuBot] User selected {len(selected_infocodes)} reports: {selected_infocodes}")
            return selected_infocodes

        except Exception as e:
            utils.logger.error(f"[EastmoneyFeishuBot] Failed to parse selection '{selection_text}': {e}")
            # On parse error, return empty to delete all
            return []

    async def send_report_list(self, reports: List[Dict]) -> bool:
        """
        发送研报列表到飞书

        Args:
            reports: 研报列表

        Returns:
            是否成功发送
        """
        if not eastmoney_config.FEISHU_CHAT_ID:
            utils.logger.warning("[EastmoneyFeishuBot] FEISHU_CHAT_ID not configured, skipping Feishu notification")
            return False

        message_text = self._format_report_list_message(reports)

        utils.logger.info(f"[EastmoneyFeishuBot] Prepared message ({len(message_text)} chars)")
        utils.logger.debug(f"[EastmoneyFeishuBot] Message preview (first 500 chars):\n{message_text[:500]}")

        # 使用 feishu_bot_notifier.py 脚本发送消息
        return await self._send_via_script_notifier(message_text)

    async def _send_via_script_notifier(self, message: str) -> bool:
        """
        使用 feishu_bot_notifier.py 脚本发送消息

        Args:
            message: 消息内容

        Returns:
            是否发送成功
        """
        import subprocess
        from pathlib import Path

        try:
            notifier_script = Path("/Users/echochen/Desktop/DMS/skills/feishu-universal/scripts/feishu_bot_notifier.py")

            if not notifier_script.exists():
                utils.logger.error(f"[EastmoneyFeishuBot] Feishu notifier script not found: {notifier_script}")
                # 回退到打印消息
                print("=" * 60)
                print("【飞书消息】")
                print(message)
                print("=" * 60)
                return False

            # 调用飞书通知脚本
            result = await asyncio.create_subprocess_exec(
                '/opt/homebrew/bin/python3',
                str(notifier_script),
                '--message',
                message,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()

            if result.returncode == 0:
                utils.logger.info("[EastmoneyFeishuBot] Message sent via feishu_bot_notifier.py")
                return True
            else:
                utils.logger.error(f"[EastmoneyFeishuBot] Feishu notifier failed: {stderr.decode()}")
                return False

        except Exception as e:
            utils.logger.error(f"[EastmoneyFeishuBot] Error calling feishu_bot_notifier: {e}")
            return False


async def send_and_notify_reports(reports: List[Dict]) -> Optional[List[str]]:
    """
    发送研报列表到飞书并等待用户选择

    Args:
        reports: 研报列表

    Returns:
        用户选择的infocode列表，或None表示超时/取消
    """
    bot = EastmoneyFeishuBot()
    bot_server_url = "http://localhost:5001"

    # 提取 infocodes
    infocodes = [r.get("infocode", "") for r in reports]

    # 1. 先保存待选择的报告列表到 bot server
    try:
        response = requests.post(
            f"{bot_server_url}/api/eastmoney/save_selection",
            json={
                "total_count": len(reports),
                "infocodes": infocodes
            },
            timeout=5
        )
        if response.status_code != 200:
            utils.logger.error(f"[EastmoneyFeishuBot] Failed to save selection to bot server: {response.text}")
            return None
        utils.logger.info("[EastmoneyFeishuBot] Saved selection data to bot server")
    except requests.RequestException as e:
        utils.logger.error(f"[EastmoneyFeishuBot] Bot server not available: {e}")
        utils.logger.error("[EastmoneyFeishuBot] Please ensure bot server is running: python3 bot_server.py")
        return None

    # 2. 发送报告列表到飞书
    if not await bot.send_report_list(reports):
        utils.logger.warning("[EastmoneyFeishuBot] Failed to send report list to Feishu")
        # 清除 bot server 中的选择数据
        requests.post(f"{bot_server_url}/api/eastmoney/clear_selection", timeout=5)
        return None

    # 3. 轮询等待用户选择（最多15分钟）
    utils.logger.info("[EastmoneyFeishuBot] Waiting for user selection (max 15 minutes)...")

    max_wait_time = 900  # 15分钟 = 900秒
    check_interval = 10  # 每10秒检查一次
    elapsed = 0

    while elapsed < max_wait_time:
        try:
            response = requests.get(f"{bot_server_url}/api/eastmoney/get_selection", timeout=5)
            if response.status_code == 200:
                data = response.json().get("data", {})
                status = data.get("status")
                selection = data.get("selection")

                if status == "ready":
                    utils.logger.info(f"[EastmoneyFeishuBot] User selection received: {selection}")
                    # 清除选择数据
                    requests.post(f"{bot_server_url}/api/eastmoney/clear_selection", timeout=5)
                    return selection
                elif status == "cancelled":
                    utils.logger.info("[EastmoneyFeishuBot] User cancelled selection")
                    # 清除选择数据
                    requests.post(f"{bot_server_url}/api/eastmoney/clear_selection", timeout=5)
                    return []
                elif status == "waiting":
                    # 继续等待
                    pass
                else:
                    utils.logger.warning(f"[EastmoneyFeishuBot] Unknown status: {status}")
        except requests.RequestException as e:
            utils.logger.error(f"[EastmoneyFeishuBot] Error checking selection: {e}")

        # 等待一段时间后再次检查
        await asyncio.sleep(check_interval)
        elapsed += check_interval

        # 每30秒记录一次日志
        if elapsed % 30 == 0:
            utils.logger.info(f"[EastmoneyFeishuBot] Still waiting... ({elapsed}s elapsed)")

    # 超时
    utils.logger.warning("[EastmoneyFeishuBot] User selection timeout after 15 minutes")
    # 清除选择数据
    requests.post(f"{bot_server_url}/api/eastmoney/clear_selection", timeout=5)
    return None
