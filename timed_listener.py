#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书监听器 - 短期监听模式（15分钟）
用于在发送研报清单后监听用户回复

使用方法:
  python3 timed_listener.py

监听 15 分钟后自动停止，超时则删除所有未选中的 PDF
"""

import asyncio
import json
import os
import re
import time
from datetime import datetime

import requests


class TimedFeishuListener:
    """带超时的飞书监听器"""

    def __init__(self, timeout_minutes=15):
        self.config_path = os.path.expanduser("~/.feishu_user_config.json")
        self.base_url = "https://open.feishu.cn/open-apis"
        self.timeout_seconds = timeout_minutes * 60
        self.start_time = time.time()
        self.user_open_id = None
        self.access_token = None
        self.chat_id = None
        self.last_message_time = None

        self._load_config()
        self._refresh_access_token()

    def _load_config(self):
        """加载配置"""
        with open(self.config_path, 'r') as f:
            config = json.load(f)
        self.app_id = config.get('app_id')
        self.app_secret = config.get('app_secret')
        self.user_open_id = config.get('user_open_id')

    def _get_app_access_token(self):
        """获取 app_access_token"""
        url = f"{self.base_url}/auth/v3/app_access_token/internal"
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        response = requests.post(url, json=payload)
        data = response.json()
        if data.get("code") == 0:
            return data.get("app_access_token")
        raise Exception(f"获取 app_access_token 失败: {data}")

    def _get_user_access_token(self):
        """获取 user_access_token (使用 refresh_token)"""
        with open(self.config_path, 'r') as f:
            config = json.load(f)
        refresh_token = config.get('refresh_token')

        url = f"{self.base_url}/authen/v1/refresh"
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }
        headers = {
            "Authorization": f"Bearer {self._get_app_access_token()}",
            "Content-Type": "application/json"
        }
        response = requests.post(url, headers=headers, json=payload)
        data = response.json()

        if data.get("code") == 0:
            # Update config
            new_config = config.copy()
            new_config['user_access_token'] = data.get('user_access_token')
            new_config['refresh_token'] = data.get('refresh_token')
            new_config['expires_at'] = time.time() + data.get('expires_in', 7200)

            with open(self.config_path, 'w') as f:
                json.dump(new_config, f, indent=2)

            return data.get('user_access_token')

        raise Exception(f"获取 user_access_token 失败: {data}")

    def _refresh_access_token(self):
        """刷新 access_token"""
        with open(self.config_path, 'r') as f:
            config = json.load(f)

        expires_at = config.get('expires_at', 0)
        if time.time() > expires_at:
            self.access_token = self._get_user_access_token()
        else:
            self.access_token = config.get('user_access_token')

    def get_user_chat_id(self) -> str:
        """获取用户的聊天 ID"""
        url = f"{self.base_url}/im/v1/chats"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        params = {"user_id_type": "open_id"}

        response = requests.get(url, headers=headers, params=params)
        data = response.json()

        if data.get("code") == 0:
            # Find user's own chat
            for chat in data.get('data', {}).get('items', []):
                if chat.get('name') == 'chenchuxin':
                    return chat.get('chat_id')
            # Fallback: first chat owned by user
            for chat in data.get('data', {}).get('items', []):
                if chat.get('owner_id') == self.user_open_id:
                    return chat.get('chat_id')

        raise Exception(f"获取 chat_id 失败: {data}")

    def get_latest_message(self, chat_id: str) -> dict:
        """获取最新消息"""
        url = f"{self.base_url}/im/v1/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        params = {
            "container_id": chat_id,
            "container_id_type": "chat",
            "page_size": 10,
            "sort_type": "ByCreateTimeDesc"
        }

        response = requests.get(url, headers=headers, params=params)
        data = response.json()

        if data.get("code") == 0:
            items = data.get('data', {}).get('items', [])
            if items:
                return items[0]

        return None

    def send_message(self, content: str) -> bool:
        """发送消息到飞书"""
        url = f"{self.base_url}/im/v1/messages?receive_id_type=open_id"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "receive_id": self.user_open_id,
            "msg_type": "text",
            "content": json.dumps({"text": content})
        }

        response = requests.post(url, headers=headers, json=payload)
        data = response.json()

        if data.get("code") != 0:
            print(f"发送消息失败: {data}")
        return data.get("code") == 0

    def parse_user_selection(self, text: str):
        """解析用户选择"""
        text = text.strip().lower()

        # Special commands
        if text in ["全部保留", "all", "全部"]:
            return "all"
        if text in ["全部删除", "delete", "delete all"]:
            return "delete_all"

        # Parse numbers
        numbers = re.findall(r'\d+', text)
        if numbers:
            return [int(n) for n in numbers]

        return None


async def listen_and_process(timeout_minutes=15):
    """监听并处理用户选择"""
    import sys
    sys.path.insert(0, '/Users/echochen/MediaCrawler')

    listener = TimedFeishuListener(timeout_minutes)

    # Get user's chat ID
    try:
        listener.chat_id = listener.get_user_chat_id()
        print(f"Chat ID: {listener.chat_id}")
    except Exception as e:
        print(f"获取聊天ID失败: {e}")
        return

    remaining_time = listener.timeout_seconds

    print("=" * 60)
    print(f"飞书监听器已启动（超时: {timeout_minutes} 分钟）")
    print("=" * 60)
    print(f"开始时间: {datetime.now().strftime('%H:%M:%S')}")
    print(f"结束时间: {(datetime.fromtimestamp(time.time() + remaining_time)).strftime('%H:%M:%S')}")
    print("=" * 60)

    # Send start notification
    listener.send_message(f"⏰ 监听器已启动\n请在 {timeout_minutes} 分钟内回复要保留的研报编号\n例如: 1,2,3 或 全部保留")

    last_check_time = time.time()
    check_interval = 300  # Check every 5 minutes (300 seconds)
    last_message_id = None

    while remaining_time > 0:
        try:
            await asyncio.sleep(min(check_interval, remaining_time))

            # Update remaining time
            elapsed = time.time() - listener.start_time
            remaining_time = listener.timeout_seconds - elapsed

            # Refresh token if needed
            listener._refresh_access_token()

            # Check for new messages
            if time.time() - last_check_time >= check_interval:
                last_check_time = time.time()

                # Get latest message
                latest_msg = listener.get_latest_message(listener.chat_id)

                if latest_msg:
                    msg_id = latest_msg.get('message_id')
                    msg_time = latest_msg.get('create_time')
                    sender_id = latest_msg.get('sender', {}).get('id', '')
                    msg_content = latest_msg.get('body', {}).get('content', '')

                    # Parse content
                    try:
                        content_dict = json.loads(msg_content)
                        text = content_dict.get('text', '')
                    except:
                        text = msg_content

                    # Check if this is a new message from user
                    if msg_id != last_message_id and sender_id == listener.user_open_id:
                        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 收到用户消息: {text}")

                        # Parse selection
                        selection = listener.parse_user_selection(text)

                        if selection is not None:
                            print(f"解析结果: {selection}")

                            # Process selection
                            import config
                            config.SAVE_DATA_OPTION = 'sqlite'

                            import time
                            from sqlalchemy import select
                            from database.db_session import get_session
                            from database.models import EastmoneyReport
                            from media_platform.eastmoney.core import EastmoneyCrawler

                            async def process_and_notify():
                                threshold_timestamp = int(time.time()) - (1 * 24 * 60 * 60)

                                async with get_session() as session:
                                    stmt = select(EastmoneyReport).where(
                                        EastmoneyReport.create_time >= threshold_timestamp,
                                        EastmoneyReport.download_status == "completed"
                                    ).order_by(EastmoneyReport.create_time.desc())
                                    result = await session.execute(stmt)
                                    reports = result.scalars().all()

                                    # Map selection to infocodes
                                    if selection == "all":
                                        selected_infocodes = [r.infocode for r in reports]
                                    elif selection == "delete_all":
                                        selected_infocodes = []
                                    elif isinstance(selection, list):
                                        selected_infocodes = []
                                        for idx in selection:
                                            if 1 <= idx <= len(reports):
                                                selected_infocodes.append(reports[idx - 1].infocode)

                                    # Process
                                    crawler = EastmoneyCrawler()
                                    result = await crawler.move_selected_pdfs(selected_infocodes)

                                    # Send confirmation
                                    kept = len(result)
                                    total = len(reports)
                                    listener.send_message(
                                        f"✅ 已处理您的选择！\n"
                                        f"保留: {kept} 份\n"
                                        f"删除: {total - kept} 份\n"
                                        f"监听器已停止"
                                    )

                                    return kept, total

                            kept, total = await process_and_notify()
                            print(f"\n✅ 处理完成！保留 {kept} 份，删除 {total - kept} 份")
                            print("=" * 60)
                            return  # Exit listener immediately

                    last_message_id = msg_id

                # Display remaining time
                mins_left = int(remaining_time // 60)
                secs_left = int(remaining_time % 60)
                print(f"\r剩余时间: {mins_left:02d}:{secs_left:02d} | 等待用户回复...", end="", flush=True)

        except KeyboardInterrupt:
            print("\n\n用户中断监听")
            break
        except Exception as e:
            print(f"\n错误: {e}")
            import traceback
            traceback.print_exc()
            await asyncio.sleep(60)

    print("\n\n" + "=" * 60)
    print("监听超时！")
    print("=" * 60)

    # Handle timeout
    import config
    config.SAVE_DATA_OPTION = 'sqlite'

    from store.eastmoney._store_impl import EastmoneyPdfStorage
    storage = EastmoneyPdfStorage()
    result = await storage.move_to_target([])  # Empty = delete all

    print(f"✅ 已删除所有PDF（未收到用户回复）")
    listener.send_message("⏰ 监听超时\n已删除所有未选择的PDF")


if __name__ == "__main__":
    import sys

    timeout = 15
    if len(sys.argv) > 1:
        timeout = int(sys.argv[1])

    asyncio.run(listen_and_process(timeout))
