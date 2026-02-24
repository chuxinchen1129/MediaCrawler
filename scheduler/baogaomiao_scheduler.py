#!/usr/bin/env python3
"""
报告喵定时调度器 - 每天早上8:30执行
检查报告喵文件夹是否有今天新放入的文件，如果有则触发skill，否则发送飞书通知
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict
import json

import loguru
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import asyncio

# 添加项目根目录到 Python 路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# 配置日志
loguru.logger.remove()
loguru.logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
           "<level>{level: <8}</level> | "
           "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
           "<level>{message}</level>",
    level="INFO"
)
logger = loguru.logger


class BaogaomiaoScheduler:
    """报告喵定时调度器"""

    def __init__(self):
        self.scheduler = None

        # 报告喵文件夹路径（默认）
        self.baogaomiao_dir = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/家人共享/报告喵"

        # 飞书配置路径
        self.feishu_config_path = Path.home() / ".feishu_user_config.json"

        # 飞书配置
        self.feishu_config = self._load_feishu_config()

        logger.info(f"[Baogaomiao Scheduler] 初始化完成")
        logger.info(f"[Baogaomiao Scheduler] 监控文件夹: {self.baogaomiao_dir}")
        logger.info(f"[Baogaomiao Scheduler] 飞书配置已加载: {'是' if self.feishu_config else '否'}")

    def _load_feishu_config(self) -> dict:
        """加载飞书配置"""
        try:
            if self.feishu_config_path.exists():
                with open(self.feishu_config_path, 'r') as f:
                    return json.load(f)
            else:
                logger.warning(f"[Baogaomiao Scheduler] 飞书配置文件不存在: {self.feishu_config_path}")
                return {}
        except Exception as e:
            logger.error(f"[Baogaomiao Scheduler] 加载飞书配置失败: {e}")
            return {}

    def _get_today_files(self) -> List[Path]:
        """获取今天创建/修改的文件"""
        if not self.baogaomiao_dir.exists():
            logger.warning(f"[Baogaomiao Scheduler] 文件夹不存在: {self.baogaomiao_dir}")
            return []

        today = datetime.now().date()
        today_start = datetime.combine(today, datetime.min.time())
        today_files = []

        try:
            # 支持的文件扩展名
            supported_extensions = {'.pdf', '.docx', '.doc', '.pptx', '.ppt', '.xlsx', '.xls', '.txt', '.md'}

            for file_path in self.baogaomiao_dir.rglob('*'):
                if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                    # 获取文件修改时间
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if mtime >= today_start:
                        today_files.append(file_path)
                        logger.debug(f"[Baogaomiao Scheduler] 发现今日文件: {file_path.name} (修改于 {mtime})")

        except Exception as e:
            logger.error(f"[Baogaomiao Scheduler] 扫描文件夹失败: {e}")

        # 按修改时间排序（最新的在前）
        today_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return today_files

    async def _send_feishu_notification(self, message: str) -> bool:
        """发送飞书通知"""
        try:
            if not self.feishu_config:
                logger.warning("[Baogaomiao Scheduler] 飞书配置未加载，无法发送通知")
                return False

            user_open_id = self.feishu_config.get('user_open_id', '')
            app_id = self.feishu_config.get('app_id', '')
            app_secret = self.feishu_config.get('app_secret', '')

            if not user_open_id:
                logger.error("[Baogaomiao Scheduler] 未配置 user_open_id")
                return False

            # 使用飞书MCP工具发送消息
            import subprocess

            # 构造飞书消息
            msg_content = json.dumps({
                "text": message
            })

            # 调用飞书发送脚本
            feishu_notifier = Path.home() / ".claude/skills/feishu-universal/scripts/feishu_bot_notifier.py"

            if feishu_notifier.exists():
                result = subprocess.run(
                    ['python3', str(feishu_notifier), '--message', message],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode == 0:
                    logger.info(f"[Baogaomiao Scheduler] 飞书通知已发送")
                    return True
                else:
                    logger.error(f"[Baogaomiao Scheduler] 飞书通知发送失败: {result.stderr}")
                    return False
            else:
                logger.warning(f"[Baogaomiao Scheduler] 飞书通知脚本不存在: {feishu_notifier}")
                return False

        except Exception as e:
            logger.error(f"[Baogaomiao Scheduler] 发送飞书通知失败: {e}")
            return False

    async def _trigger_baogaomiao_skill(self, files: List[Path]) -> bool:
        """触发报告喵skill处理文件"""
        try:
            logger.info(f"[Baogaomiao Scheduler] 触发报告喵skill处理 {len(files)} 个文件")

            # 获取最新的PDF文件
            pdf_files = [f for f in files if f.suffix.lower() == '.pdf']

            if not pdf_files:
                logger.warning("[Baogaomiao Scheduler] 没有PDF文件，无法触发报告喵skill")
                # 发送飞书通知
                await self._send_feishu_notification(
                    f"📋 报告喵扫描完成\n\n"
                    f"发现 {len(files)} 个今日文件，但都不是PDF格式。\n"
                    f"报告喵目前只支持PDF文件。\n\n"
                    f"文件列表：\n" + "\n".join([f"• {f.name}" for f in files[:5]])
                )
                return False

            latest_pdf = pdf_files[0]
            logger.info(f"[Baogaomiao Scheduler] 使用最新PDF: {latest_pdf.name}")

            # 发送飞书通知：开始处理
            await self._send_feishu_notification(
                f"📊 报告喵开始工作\n\n"
                f"发现 {len(files)} 个今日文件，共 {len(pdf_files)} 个PDF。\n"
                f"正在处理最新文件：{latest_pdf.name}\n\n"
                f"预计处理时间：2-3分钟"
            )

            # 直接调用报告喵skill的PDF提取和处理
            try:
                # 导入报告喵skill的PDF提取器
                baogaomiao_skill_path = Path.home() / ".claude/skills/baogaomiao/scripts"
                sys.path.insert(0, str(baogaomiao_skill_path))

                from pdf_extractor import PDFExtractor

                logger.info(f"[Baogaomiao Scheduler] 开始提取PDF内容: {latest_pdf}")
                extractor = PDFExtractor(str(latest_pdf))
                result = extractor.extract(max_pages=10)

                if not result['success']:
                    logger.error(f"[Baogaomiao Scheduler] PDF提取失败: {result.get('error')}")
                    await self._send_feishu_notification(
                        f"❌ 报告喵处理失败\n\n"
                        f"无法提取PDF内容：{latest_pdf.name}\n"
                        f"错误：{result.get('error', '未知错误')}"
                    )
                    return False

                pdf_content = result['text']
                logger.info(f"[Baogaomiao Scheduler] PDF提取成功，内容长度: {len(pdf_content)} 字符")

                # 保存提取的内容到临时文件
                temp_dir = Path("/tmp/baogaomiao_scheduler")
                temp_dir.mkdir(exist_ok=True)
                temp_content_file = temp_dir / f"{latest_pdf.stem}_content.txt"

                with open(temp_content_file, 'w', encoding='utf-8') as f:
                    f.write(pdf_content)

                logger.info(f"[Baogaomiao Scheduler] PDF内容已保存到: {temp_content_file}")

                # 发送飞书通知：处理完成
                await self._send_feishu_notification(
                    f"✅ 报告喵处理完成\n\n"
                    f"文件：{latest_pdf.name}\n"
                    f"提取页数：{result.get('pages', 'N/A')}\n"
                    f"内容长度：{len(pdf_content)} 字符\n"
                    f"使用库：{result.get('lib', 'N/A')}\n\n"
                    f"内容已保存到：{temp_content_file}\n\n"
                    f"请在Claude Code中说\"报告喵\"来生成小红书笔记"
                )

                return True

            except ImportError as e:
                logger.error(f"[Baogaomiao Scheduler] 导入报告喵模块失败: {e}")
                await self._send_feishu_notification(
                    f"⚠️ 报告喵skill未安装\n\n"
                    f"请先安装报告喵skill：\n"
                    f"在Claude Code中输入：/skills 查看可用技能"
                )
                return False

            except Exception as e:
                logger.error(f"[Baogaomiao Scheduler] 处理PDF时出错: {e}", exc_info=True)
                await self._send_feishu_notification(
                    f"❌ 报告喵处理出错\n\n"
                    f"文件：{latest_pdf.name}\n"
                    f"错误：{str(e)}"
                )
                return False

        except Exception as e:
            logger.error(f"[Baogaomiao Scheduler] 触发报告喵skill失败: {e}", exc_info=True)
            return False

    async def check_and_process(self):
        """检查并处理今日文件"""
        logger.info("=" * 60)
        logger.info("[Baogaomiao Scheduler] 开始执行定时检查")
        logger.info("=" * 60)

        try:
            # 1. 检查文件夹是否存在
            if not self.baogaomiao_dir.exists():
                logger.warning(f"[Baogaomiao Scheduler] 文件夹不存在: {self.baogaomiao_dir}")
                await self._send_feishu_notification(
                    f"⚠️ 报告喵检查失败\n\n"
                    f"文件夹不存在：{self.baogaomiao_dir}\n\n"
                    f"请确认文件夹路径是否正确。"
                )
                return

            # 2. 获取今天的文件
            today_files = self._get_today_files()

            # 3. 判断是否有新文件
            if not today_files:
                logger.info("[Baogaomiao Scheduler] 未发现今日新文件")
                await self._send_feishu_notification(
                    f"📭 报告喵扫描完成\n\n"
                    f"未发现今日新放入的文件。\n"
                    f"扫描时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    f"如需处理文档，请将文件放入：\n{self.baogaomiao_dir}"
                )
                return

            # 4. 有新文件，触发报告喵skill
            logger.info(f"[Baogaomiao Scheduler] 发现 {len(today_files)} 个今日新文件")
            file_list = "\n".join([f"• {f.name}" for f in today_files[:10]])
            if len(today_files) > 10:
                file_list += f"\n... 还有 {len(today_files) - 10} 个文件"

            logger.info(f"[Baogaomiao Scheduler] 文件列表：\n{file_list}")

            # 触发报告喵skill
            success = await self._trigger_baogaomiao_skill(today_files)

            if success:
                logger.info("[Baogaomiao Scheduler] 报告喵skill处理完成")
            else:
                logger.error("[Baogaomiao Scheduler] 报告喵skill处理失败")

        except Exception as e:
            logger.error(f"[Baogaomiao Scheduler] 执行失败: {e}", exc_info=True)

        logger.info("[Baogaomiao Scheduler] 定时检查完成")

    def start(self):
        """启动调度器"""
        if self.scheduler is not None and self.scheduler.running:
            logger.warning("[Baogaomiao Scheduler] 调度器已在运行中")
            return

        self.scheduler = BackgroundScheduler()

        # 添加定时任务：每天早上8:30执行
        self.scheduler.add_job(
            self.check_and_process_sync,
            CronTrigger(hour=8, minute=30),
            id='baogaomiao_daily_check',
            name='报告喵每日检查',
            replace_existing=True
        )

        self.scheduler.start()

        logger.info("[Baogaomiao Scheduler] 调度器已启动")
        logger.info("[Baogaomiao Scheduler] 下次执行: 每天 08:30")

    def check_and_process_sync(self):
        """同步版本的检查方法"""
        asyncio.run(self.check_and_process())

    def run_forever(self):
        """保持调度器运行"""
        try:
            # BackgroundScheduler不需要特殊的事件循环处理
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("[Baogaomiao Scheduler] 收到退出信号")
            self.stop()

    def stop(self):
        """停止调度器"""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("[Baogaomiao Scheduler] 调度器已停止")


async def run_once():
    """手动执行一次检查（用于测试）"""
    scheduler = BaogaomiaoScheduler()
    await scheduler.check_and_process()


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="报告喵定时调度器")
    parser.add_argument('--scheduler', action='store_true', help='启动定时调度模式')
    parser.add_argument('--once', action='store_true', help='执行一次检查后退出')

    args = parser.parse_args()

    if args.scheduler:
        # 启动定时调度
        logger.info("[Baogaomiao Scheduler] 启动定时调度模式")
        scheduler = BaogaomiaoScheduler()
        scheduler.start()

        logger.info("[Baogaomiao Scheduler] 调度器正在运行，按 Ctrl+C 退出")

        try:
            # 保持运行
            scheduler.run_forever()
        except KeyboardInterrupt:
            logger.info("[Baogaomiao Scheduler] 收到退出信号")
            scheduler.stop()

    elif args.once:
        # 执行一次检查
        logger.info("[Baogaomiao Scheduler] 执行单次检查")
        asyncio.run(run_once())

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
