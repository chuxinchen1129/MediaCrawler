#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书消息监听器 v3.0 - 持续监听用户回复并处理研报选择
使用 tenant_access_token，无需 OAuth 流程
"""

import asyncio
import json
import os
import re
import time
from datetime import datetime
from typing import Optional, List
from pathlib import Path

import requests

# Import MediaCrawler utils for logging
import sys
sys.path.insert(0, '/Users/echochen/MediaCrawler')
from tools import utils


class FeishuMessageListener:
    """飞书消息监听器"""

    def __init__(self):
        self.config_path = os.path.expanduser("~/.feishu_user_config.json")
        self.base_url = "https://open.feishu.cn/open-apis"
        self.user_open_id = None
        self.chat_id = None
        self.tenant_access_token = None
        self.last_message_time = None
        self.last_processed_content = None

        # Load config and get token
        self._load_config()
        self._get_tenant_token()

    def _load_config(self):
        """加载配置"""
        with open(self.config_path, 'r') as f:
            config = json.load(f)
        self.app_id = config.get('app_id')
        self.app_secret = config.get('app_secret')
        self.user_open_id = config.get('user_open_id')
        self.chat_id = config.get('chat_id', self.user_open_id)  # 兼容旧配置

    def _get_tenant_token(self):
        """获取 tenant_access_token"""
        url = f"{self.base_url}/auth/v3/app_access_token/internal"
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        response = requests.post(url, json=payload)
        data = response.json()
        if data.get("code") == 0:
            self.tenant_access_token = data.get("app_access_token")
        else:
            raise Exception(f"获取 tenant_access_token 失败: {data}")

    def get_chat_id(self) -> str:
        """获取与机器人的私聊 chat_id"""
        # 如果配置中已有 chat_id，直接使用
        if self.chat_id and self.chat_id != self.user_open_id:
            return self.chat_id

        # 否则通过 API 获取
        url = f"{self.base_url}/im/v1/chats"
        headers = {
            "Authorization": f"Bearer {self.tenant_access_token}",
            "Content-Type": "application/json"
        }
        params = {
            "user_id_type": "open_id"
        }

        response = requests.get(url, headers=headers, params=params)
        data = response.json()

        if data.get("code") == 0:
            # 查找用户的私聊
            for chat in data.get('data', {}).get('items', []):
                chat_id = chat.get('chat_id')
                owner = chat.get('owner_id')
                name = chat.get('name', '')

                # 使用用户拥有的聊天
                if owner == self.user_open_id:
                    print(f"使用用户聊天: {name} (chat_id: {chat_id})")
                    return chat_id

            # 最后使用第一个聊天
            items = data.get('data', {}).get('items', [])
            if items:
                chat_id = items[0].get('chat_id')
                print(f"使用第一个聊天: {items[0].get('name')} (chat_id: {chat_id})")
                return chat_id

        raise Exception(f"获取 chat_id 失败: {data}")

    def get_messages(self, chat_id: str, limit: int = 20) -> List[dict]:
        """获取聊天消息"""
        url = f"{self.base_url}/im/v1/messages"
        headers = {
            "Authorization": f"Bearer {self.tenant_access_token}",
            "Content-Type": "application/json"
        }
        params = {
            "container_id": chat_id,
            "container_id_type": "chat",
            "page_size": limit,
            "sort_type": "ByCreateTimeDesc"
        }

        response = requests.get(url, headers=headers, params=params)
        data = response.json()

        if data.get("code") == 0:
            return data.get('data', {}).get('items', [])

        raise Exception(f"获取消息失败: {data}")

    def send_message(self, content: str) -> bool:
        """发送消息到飞书"""
        url = f"{self.base_url}/im/v1/messages?receive_id_type=open_id"
        headers = {
            "Authorization": f"Bearer {self.tenant_access_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "receive_id": self.user_open_id,
            "msg_type": "text",
            "content": json.dumps({"text": content})
        }

        response = requests.post(url, headers=headers, json=payload)
        data = response.json()

        return data.get("code") == 0

    def _create_baogaomiao_task(self, pdf_path: str) -> str:
        """创建报告喵任务文件

        Args:
            pdf_path: PDF文件路径

        Returns:
            任务文件路径
        """
        task_dir = Path("~/.claude/skills/feishu-bot/data/baogaomiao_tasks").expanduser()
        task_dir.mkdir(parents=True, exist_ok=True)

        task_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        task_file = task_dir / f"task_{task_id}.json"

        task_data = {
            "task_type": "baogaomiao_generate",
            "pdf_path": pdf_path,
            "task_id": task_id,
            "created_at": datetime.now().isoformat(),
            "status": "pending",
            "source": "feishu_listener"
        }

        with open(task_file, 'w', encoding='utf-8') as f:
            json.dump(task_data, f, ensure_ascii=False, indent=2)

        return str(task_file)

    def parse_user_selection(self, text: str) -> Optional[List[int]]:
        """解析用户选择"""
        text = text.strip().lower()

        # Special commands
        if text in ["全部保留", "all", "全部"]:
            return "all"
        if text in ["全部删除", "delete all", "all delete"]:
            return "delete_all"

        # Parse numbers
        numbers = re.findall(r'\d+', text)
        if numbers:
            return [int(n) for n in numbers]

        return None


async def process_selection(selected_indices: List[int]) -> dict:
    """处理用户选择，移动 PDF

    Args:
        selected_indices: 用户选择的索引列表（从1开始）

    Returns:
        dict with structure: {
            'success': bool,
            'moved': int,  # 移动的文件数
            'total': int,  # 总文件数
            'infocodes': list[str],  # infocode列表
            'moved_pdf_paths': list[str]  # 移动后的PDF路径列表
        }
    """
    import sys
    sys.path.insert(0, '/Users/echochen/MediaCrawler')

    import config
    config.SAVE_DATA_OPTION = 'sqlite'

    from media_platform.eastmoney.core import EastmoneyCrawler

    # Get recent reports from database
    import time
    from sqlalchemy import select
    from database.db_session import get_session
    from database.models import EastmoneyReport

    threshold_timestamp = int(time.time()) - (1 * 24 * 60 * 60)  # Last 1 day

    async with get_session() as session:
        stmt = select(EastmoneyReport).where(
            EastmoneyReport.create_time >= threshold_timestamp,
            EastmoneyReport.download_status == "completed"
        ).order_by(EastmoneyReport.create_time.desc())
        result = await session.execute(stmt)
        reports = result.scalars().all()

        # Map indices to infocodes
        selected_infocodes = []
        for idx in selected_indices:
            if 1 <= idx <= len(reports):
                selected_infocodes.append(reports[idx - 1].infocode)

        if not selected_infocodes:
            return {"success": False, "error": "无效的选择"}

        # Move PDFs
        crawler = EastmoneyCrawler()
        move_result = await crawler.move_selected_pdfs(selected_infocodes)

        # Extract moved paths
        moved_pdf_paths = [p['target_path'] for p in move_result.get('moved_paths', [])]

        return {
            "success": True,
            "moved": move_result.get('moved_count', len(move_result)),
            "total": len(reports),
            "infocodes": selected_infocodes,
            "moved_pdf_paths": moved_pdf_paths
        }


async def listen_loop():
    """监听循环 - 监听所有聊天中的用户消息"""
    listener = FeishuMessageListener()

    print("=" * 60)
    print("飞书消息监听器 v3.2 已启动")
    print("=" * 60)
    print(f"User Open ID: {listener.user_open_id}")
    print("使用 tenant_access_token，监听所有聊天")
    print("正在监听用户回复...")
    print("按 Ctrl+C 停止监听")
    print("=" * 60)

    # Track last processed message time per chat
    last_message_times = {}  # chat_id -> last_time

    # Initialize: get current latest message time for each chat
    try:
        import requests
        url = f'{listener.base_url}/im/v1/chats'
        headers = {
            'Authorization': f'Bearer {listener.tenant_access_token}',
            'Content-Type': 'application/json'
        }
        params = {'user_id_type': 'open_id', 'page_size': 50}

        response = requests.get(url, headers=headers, params=params)
        data = response.json()

        if data.get('code') == 0:
            chats = data.get('data', {}).get('items', [])
            for chat in chats:
                chat_id = chat.get('chat_id')
                messages = listener.get_messages(chat_id, limit=5)
                if messages:
                    # Record the latest message time for this chat
                    latest_msg = messages[0]
                    msg_time = latest_msg.get('update_time') or latest_msg.get('create_time')
                    if msg_time:
                        last_message_times[chat_id] = msg_time
            print(f"初始化完成，跟踪 {len(last_message_times)} 个聊天")
    except Exception as e:
        print(f"初始化失败: {e}")

    while True:
        try:
            await asyncio.sleep(60)  # Check every minute

            # Get all chats
            url = f'{listener.base_url}/im/v1/chats'
            headers = {
                'Authorization': f'Bearer {listener.tenant_access_token}',
                'Content-Type': 'application/json'
            }
            params = {'user_id_type': 'open_id', 'page_size': 50}

            try:
                response = requests.get(url, headers=headers, params=params, timeout=30)
                data = response.json()
            except requests.exceptions.SSLError as e:
                utils.logger.error(f"[FeishuListener] SSL Error: {e}, refreshing token...")
                # 刷新 token
                listener._get_tenant_token()
                await asyncio.sleep(5)
                continue
            except requests.exceptions.RequestException as e:
                utils.logger.error(f"[FeishuListener] Request Error: {e}")
                await asyncio.sleep(10)
                continue

            if data.get('code') != 0:
                utils.logger.warning(f"[FeishuListener] API Error: {data.get('msg')}")
                await asyncio.sleep(60)
                continue

            chats = data.get('data', {}).get('items', [])

            # Check each chat for new user messages
            for chat in chats:
                chat_id = chat.get('chat_id')
                chat_name = chat.get('name', 'Unknown')

                try:
                    # Get messages from this chat
                    messages = listener.get_messages(chat_id, limit=10)

                    if not messages:
                        continue

                    # Track if we found any new message in this chat
                    chat_has_new = False

                    for msg in messages:
                        sender = msg.get('sender', {}).get('id', '')
                        msg_time = msg.get('update_time') or msg.get('create_time')
                        msg_content = msg.get('body', {}).get('content', '')

                        # Skip if not from user
                        if sender != listener.user_open_id:
                            continue

                        # Skip if this message is older than or equal to last processed time
                        if chat_id in last_message_times:
                            last_time = last_message_times[chat_id]
                            if msg_time <= last_time:
                                continue

                        # This is a new message
                        chat_has_new = True

                        # Parse content
                        try:
                            content_dict = json.loads(msg_content)
                            text = content_dict.get('text', '')
                        except:
                            text = msg_content

                        if not text:
                            continue

                        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 收到用户消息 [{chat_name}]: {text}")

                        # Parse selection
                        selection = listener.parse_user_selection(text)

                        if selection is None:
                            print("无法解析用户选择")
                            # Update last message time even if we can't parse
                            last_message_times[chat_id] = msg_time
                            continue

                        print(f"解析结果: {selection}")

                        # Also write to selection file for crawler integration
                        try:
                            selection_file = "/tmp/eastmoney_selection.txt"
                            with open(selection_file, 'w', encoding='utf-8') as f:
                                # Write comma-separated indices
                                if isinstance(selection, list):
                                    f.write(','.join(str(idx) for idx in selection))
                                elif selection == "all":
                                    f.write("all")
                                elif selection == "delete_all":
                                    f.write("delete_all")
                                else:
                                    f.write(str(selection))
                            print(f"已写入选择文件: {selection_file}")
                        except Exception as e:
                            print(f"写入选择文件失败: {e}")

                        # Process selection
                        try:
                            if selection == "all":
                                # Get all infocodes
                                result = await process_selection(list(range(1, 100)))  # Will get all available
                                listener.send_message(f"✅ 已保留所有研报\n共 {result.get('moved', 0)} 份")

                                # Create baogaomiao tasks for moved PDFs
                                for pdf_path in result.get('moved_pdf_paths', []):
                                    task_file = listener._create_baogaomiao_task(pdf_path)
                                    print(f"已创建baogaomiao任务: {task_file}")
                            elif selection == "delete_all":
                                # Delete all (empty selection)
                                result = await process_selection([])
                                listener.send_message(f"✅ 已删除所有研报")
                            elif isinstance(selection, list):
                                result = await process_selection(selection)
                                if result.get('success'):
                                    moved_count = result.get('moved', 0)
                                    deleted_count = result.get('total', 0) - moved_count
                                    listener.send_message(f"✅ 已处理您的选择！\n保留 {moved_count} 份研报\n删除 {deleted_count} 份")

                                    # Create baogaomiao tasks for moved PDFs
                                    moved_pdf_paths = result.get('moved_pdf_paths', [])
                                    if moved_pdf_paths:
                                        if len(moved_pdf_paths) == 1:
                                            listener.send_message(f"🔄 正在生成小红书笔记...")
                                        else:
                                            listener.send_message(f"🔄 正在生成 {len(moved_pdf_paths)} 份小红书笔记...")

                                        for pdf_path in moved_pdf_paths:
                                            task_file = listener._create_baogaomiao_task(pdf_path)
                                            print(f"已创建baogaomiao任务: {task_file}")
                                else:
                                    listener.send_message(f"❌ {result.get('error', '处理失败')}")
                        except Exception as e:
                            print(f"处理选择时出错: {e}")
                            import traceback
                            traceback.print_exc()

                        # Update last message time for this chat
                        last_message_times[chat_id] = msg_time

                        # Only process the first new message per chat per cycle
                        break

                except Exception as e:
                    print(f"处理聊天 {chat_name} 时出错: {e}")
                    continue

        except KeyboardInterrupt:
            print("\n\n监听器已停止")
            break
        except Exception as e:
            print(f"\n错误: {e}")
            import traceback
            traceback.print_exc()
            await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(listen_loop())
