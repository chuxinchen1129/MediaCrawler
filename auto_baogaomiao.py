#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动检测今天的PDF文件并触发baogaomiao处理
- 检查报告喵目录今天是否有新PDF
- 如果有新文件：发送飞书通知
- 如果无新文件：发送提醒消息
"""

import os
import json
from datetime import datetime
from pathlib import Path

# 配置
TARGET_DIR = "/Users/echochen/Library/Mobile Documents/com~apple~CloudDocs/家人共享/报告喵"
FEISHU_CONFIG = os.path.expanduser("~/.feishu_user_config.json")


def get_current_files():
    """获取今天修改的PDF文件"""
    target_path = Path(TARGET_DIR)
    if not target_path.exists():
        return []

    today = datetime.now().date()
    pdfs = []

    for f in target_path.glob("*.pdf"):
        if f.name.startswith('.'):
            continue
        # 排除目录
        if not (target_path / f).is_file():
            continue
        # 检查文件修改时间是否为今天
        mod_time = datetime.fromtimestamp((target_path / f).stat().st_mtime).date()
        if mod_time == today:
            pdfs.append(f.name)

    return sorted(pdfs)


def send_feishu_message(text):
    """发送飞书消息"""
    try:
        import requests

        with open(FEISHU_CONFIG, 'r') as f:
            config = json.load(f)
        app_id = config.get('app_id')
        app_secret = config.get('app_secret')
        user_open_id = config.get('user_open_id')
        refresh_token = config.get('refresh_token')

        # 获取 app_access_token
        base_url = "https://open.feishu.cn/open-apis"
        token_url = f"{base_url}/auth/v3/app_access_token/internal"
        payload = {"app_id": app_id, "app_secret": app_secret}
        response = requests.post(token_url, json=payload)
        app_token = response.json().get("app_access_token")

        # 发送消息
        msg_url = f"{base_url}/im/v1/messages?receive_id_type=open_id"
        headers = {
            "Authorization": f"Bearer {app_token}",
            "Content-Type": "application/json"
        }
        msg_payload = {
            "receive_id": user_open_id,
            "msg_type": "text",
            "content": json.dumps({"text": text})
        }
        response = requests.post(msg_url, headers=headers, json=msg_payload)
        return response.json().get("code") == 0
    except Exception as e:
        print(f"发送飞书消息失败: {e}")
        return False


def process_pdf_with_baogaomiao(pdf_file):
    """调用baogaomiao处理PDF"""
    # 这里需要调用baogaomiao skill的逻辑
    # 由于baogaomiao是Claude Code skill，需要通过特定方式触发
    # 这里简化为直接记录到日志和发送消息
    pdf_path = os.path.join(TARGET_DIR, pdf_file)
    print(f"[AutoBaogaomiao] 发现新PDF: {pdf_file}")
    print(f"[AutoBaogaomiao] 路径: {pdf_path}")
    return pdf_path


def main():
    separator = "=" * 60
    print(separator)
    print("自动检测今天的PDF并触发baogaomiao")
    print(f"目标目录: {TARGET_DIR}")
    print(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"检测日期: {datetime.now().date()}")
    print(separator)

    # 获取今天的PDF文件列表
    current_files = get_current_files()
    print(f"今天的PDF文件数: {len(current_files)}")

    if current_files:
        print(f"\n✅ 发现 {len(current_files)} 个今天的PDF文件:")
        for f in current_files:
            print(f"  - {f}")
            process_pdf_with_baogaomiao(f)

        # 发送飞书消息
        msg = f"📚 发现 {len(current_files)} 份今天的研报\n"
        msg += "请手动运行 baogaomiao skill 进行阅读和总结:\n"
        msg += "\n今天的文件:\n"
        msg += "\n".join(f"• {f}" for f in current_files[:5])
        if len(current_files) > 5:
            msg += f"\n... 等 {len(current_files)} 份"

        send_feishu_message(msg)
        print("\n已发送飞书提醒")
    else:
        print(f"\nℹ️  今天没有新的PDF文件")
        msg = "ℹ️  检查完成，报告喵目录今天没有新的PDF文件"
        send_feishu_message(msg)
        print("已发送飞书提醒")


if __name__ == "__main__":
    main()
