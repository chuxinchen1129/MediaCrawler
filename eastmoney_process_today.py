#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
东方财富研报处理脚本 - 自动过滤少于10页的PDF
"""

import os
import sys
import json
from pathlib import Path

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import shutil
from datetime import datetime

# 自动检测PDF库
PDF_LIB = None
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

if not PDF_LIB:
    try:
        import fitz  # pymupdf
        PDF_LIB = 'pymupdf'
    except ImportError:
        pass

if not PDF_LIB:
    print("❌ 没有找到可用的PDF解析库，请安装：pip install PyPDF2 或 pip install pdfplumber")
    sys.exit(1)

print(f"✅ 使用PDF库: {PDF_LIB}")

# 配置
PDF_DIR = "/Users/echochen/Desktop/DMS/01_INFO_COLLECT/采集数据/eastmoney/pdf"
TARGET_DIR = "/Users/echochen/Library/Mobile Documents/com~apple~CloudDocs/家人共享/报告喵"
MIN_PAGE_COUNT = 10  # 最少页数阈值


def get_pdf_page_count(pdf_path):
    """获取PDF页数"""
    try:
        if PDF_LIB == 'pypdf2':
            import PyPDF2
            with open(pdf_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                return len(reader.pages)
        elif PDF_LIB == 'pdfplumber':
            import pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                return len(pdf.pages)
        elif PDF_LIB == 'pymupdf':
            import fitz
            doc = fitz.open(pdf_path)
            return doc.page_count
    except Exception as e:
        print(f"⚠️ 无法读取 {pdf_path}: {e}")
        return 0


def process_pdfs():
    """处理PDF文件"""
    pdf_dir = Path(PDF_DIR)
    target_dir = Path(TARGET_DIR)

    # 确保目标目录存在
    target_dir.mkdir(parents=True, exist_ok=True)

    # 获取今天（03-02）的PDF
    today_pdfs = list(pdf_dir.glob("AP202603*.pdf"))
    today_pdfs.extend(list(pdf_dir.glob("*2017*.pdf")))  # 3月2日的其他命名格式

    print("=" * 60)
    print(f"东方财富研报处理 - 页数过滤（{MIN_PAGE_COUNT}页以上）")
    print("=" * 60)
    print(f"找到 {len(today_pdfs)} 份今日研报\n")

    kept = []
    deleted = []

    for pdf_path in sorted(today_pdfs):
        if not pdf_path.exists():
            continue

        filename = pdf_path.name
        page_count = get_pdf_page_count(pdf_path)

        print(f"📄 {filename}")
        print(f"   页数: {page_count}")

        if page_count >= MIN_PAGE_COUNT:
            # 保留
            target_path = target_dir / filename
            shutil.copy2(pdf_path, target_path)
            kept.append(filename)
            print(f"   ✅ 保留 → {target_path}")
        else:
            # 删除
            pdf_path.unlink()
            deleted.append(filename)
            print(f"   ❌ 删除（少于{MIN_PAGE_COUNT}页）")
        print()

    # 总结
    print("=" * 60)
    print("处理完成！")
    print(f"✅ 保留: {len(kept)} 份")
    print(f"❌ 删除: {len(deleted)} 份")
    print("=" * 60)

    # 发送飞书通知
    try:
        sys.path.insert(0, '/Users/echochen/Desktop/DMS/skills/feishu-universal/scripts')
        from feishu_bot_notifier import FeishuBotNotifier

        notifier = FeishuBotNotifier()
        message = f"""📊 东方财富研报处理完成

今日研报（{datetime.now().strftime('%Y-%m-%d')}）：
✅ 保留 {len(kept)} 份（{MIN_PAGE_COUNT}页以上）
❌ 删除 {len(deleted)} 份（少于{MIN_PAGE_COUNT}页）

保留的文件已复制到：报告喵"""

        notifier.send_message(message)
        print("\n📱 通知已发送到飞书")

    except Exception as e:
        print(f"\n⚠️ 发送飞书通知失败: {e}")


if __name__ == "__main__":
    process_pdfs()
