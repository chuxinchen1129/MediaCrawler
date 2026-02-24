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
from typing import List, Dict, Optional
from datetime import datetime

from tools import utils
import config as eastmoney_config


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

        # Check if MCP tools are available
        mcp_available = False
        try:
            # Try to import MCP tools
            from mcp__lark_mcp__im_v1_message_create import MessageParams, MessageContent, MessageCard
            from mcp__lark_mcp__im_v1_message_create import Card, CardElement, CardHeader, ModuleSection, MarkdownElement, TextTag, MessageConfig
            mcp_available = True
        except ImportError:
            utils.logger.warning("[EastmoneyFeishuBot] MCP Lark tools not available, using demo mode")

        if not mcp_available:
            # Demo mode: just print the message
            print("=" * 60)
            print("【飞书消息预览（Demo模式）】")
            print(message_text)
            print("=" * 60)
            return False

        # Create message card using MCP tools
        try:
            # Create card elements
            elements = []
            for i, report in enumerate(reports[:5], 1):  # Limit to 5 reports to avoid message length
                org_name = report.get("org_name", "未知机构")
                title = report.get("title", "无标题")
                pages = report.get("pdf_pages", 0)
                infocode = report.get("infocode", "")

                # Create markdown element for each report
                text = f"{i}. [{org_name}] {title} - {pages}页 ({infocode})"
                elements.append(
                    CardElement(
                        tag=MarkdownElement.markdown,
                        text=text
                    )
                )

            # Add instructions
            elements.extend([
                CardElement(
                    tag=MarkdownElement.markdown,
                    text="\n\n请回复您要保留的研报编号（多个用逗号分隔）：\n例如：1,2,3\n或回复：全部保留 / 全部删除"
                )
            ])

            # Create card
            card = Card(
                config=MessageConfig.wide,
                header=CardHeader(
                    title="📊 东方财富研报通知",
                    template="white"
                ),
                elements=[
                    ModuleSection(
                        text=TextTag.plain,
                        elements=elements
                    )
                ]
            )

            # Create message content
            content = MessageContent(
                receive_id_type="open_id",
                receive_id=self.chat_id,
                msg_type="interactive",
                content=card
            )

            # Create message params
            params = MessageParams(
                receive_id=content.receive_id,
                receive_id_type=content.receive_id_type,
                msg_type=content.msg_type,
                content=content
            )

            # Send message using MCP tool
            result = await mcp__lark_mcp__im_v1_message_create(params=params)

            utils.logger.info(f"[EastmoneyFeishuBot] Message sent successfully. Result: {result}")
            return True

        except Exception as e:
            utils.logger.error(f"[EastmoneyFeishuBot] Failed to send Feishu message: {e}")
            return False


async def send_and_notify_reports(reports: List[Dict]) -> Optional[List[str]]:
    """
    发送研报列表到飞书并等待用户选择

    Args:
        reports: 研报列表

    Returns:
        用户选择的infocode列表，或None表示超时
    """
    bot = EastmoneyFeishuBot()

    # Send report list to Feishu
    if not await bot.send_report_list(reports):
        utils.logger.warning("[EastmoneyFeishuBot] Failed to send report list to Feishu")
        return None

    # Wait for user selection (in demo mode, just skip the actual wait)
    utils.logger.info("[EastmoneyFeishuBot] Demo mode: skipping user wait, using default selection")

    # In production, you would wait for actual Feishu reply here
    # selected_infocodes = await bot.process_user_selection("skip", all_infocodes)

    return []
