# MediaCrawler（fork）

用户在 NanmiCoder/MediaCrawler 基础上加了**东方财富研报爬虫**（`main_eastmoney.py` + `media_platform/eastmoney/`）。其余平台（xhs/douyin/bilibili/weibo/zhihu/tieba/kuaishou）是原项目代码，非用户维护重点。

## 运行环境
- **Python 必须用 `/usr/local/bin/python3`**（有 cv2/pymupdf）。`run_eastmoney_weekly.sh` 里写的 `/opt/homebrew/bin/python3` 已过时（无 cv2，import 链断）。
- 飞书配置（报告喵等用）：`~/.feishu_user_config.json`（app_id/secret/chat_id）。

## eastmoney 爬虫关键约定
- **qType=0 = 公司研报**（reportType=2，有 stockCode）；**qType=1 = 行业研报**（reportType=3）。代码多处标注曾标反，2026-08-09 已全项目修正（搜 `公司研报" if q_type == "0"`）。
- **PDF URL**：`https://pdf.dfcfw.com/pdf/H3_{infoCode}_1.pdf`（reportapi 返回的 infoCode 无前缀，统一加 `H3_`；两类研报都适用）。
- **定向抓取**：公司研报用 `industryCode`（数字内码，`config/INDUSTRY_CODE_MAP` 86 个）精确筛；行业研报 API 不支持 industryCode，用本地同义词（`INDUSTRY_KEYWORDS_MAP`）兜底。
- **飞书已从主流程移除**（2026-08-09）：下载后 `core.move_all_pdfs()` 全部移到 `TARGET_PDF_DIR`（当前 `~/Desktop/baogaomiao`），不经飞书选择。`feishu/eastmoney_bot.py` 已删；`move_selected_pdfs` 保留供其他独立工作流（baogaomiao_scheduler 等）用。
- **抓取上限**：`core.start()` 每 q_type 独立 `max_notes = PAGE_SIZE*5 = 250`（曾跨类型累加致行业研报漏抓，已修）。

## 命令
```
python main_eastmoney.py [--days N] [--industry 名] [--keyword 词] \
                         [--source irresearch|frost|cbndata] [--list-industries] [--scheduler]
```

## 辅助脚本
- `_crawl_all_ndays.py N`：全量爬取（绕过过滤，详见 ~/.claude/skills/eastmoney-crawler）
- `eastmoney_keyword_crawler.py` / `eastmoney_search_crawler.py`：定向关键词/搜索

## skill 入口
`~/.claude/skills/eastmoney-crawler/SKILL.md` 是用户操作入口（Claude 触发"爬研报"等词时加载）。
