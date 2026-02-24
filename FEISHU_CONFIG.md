# 东方财富研报爬虫 - 配置说明

## 飞书配置

所有飞书相关配置统一存储在：
```
~/.feishu_user_config.json
```

配置内容包括：
- `app_id`: 飞书应用 ID
- `app_secret`: 飞书应用密钥
- `user_open_id`: 用户 Open ID（用作 chat_id）
- `user_access_token`: 用户访问令牌（自动刷新）
- `refresh_token`: 刷新令牌（用于获取新 token）

## 配置加载方式

### 方式一：自动加载（推荐）
`config/eastmoney_config.py` 会自动从 `~/.feishu_user_config.json` 读取配置：

```python
_feishu_config_path = os.path.expanduser("~/.feishu_user_config.json")
if os.path.exists(_feishu_config_path):
    with open(_feishu_config_path, 'r') as f:
        _feishu_config = json.load(f)
    FEISHU_CHAT_ID = _feishu_config.get('user_open_id', '')
    FEISHU_APP_ID = _feishu_config.get('app_id', '')
    FEISHU_APP_SECRET = _feishu_config.get('app_secret', '')
```

### 方式二：重新授权
如果配置文件过期或丢失，运行授权脚本：
```bash
cd /Users/echochen/.claude/skills/feishu-universal/scripts
python3 feishu_oauth_setup.py
```

## 文件关联

| 文件 | 飞书配置来源 | 说明 |
|------|-------------|------|
| `config/eastmoney_config.py` | `~/.feishu_user_config.json` | 主配置文件，自动加载 |
| `feishu/eastmoney_bot.py` | `eastmoney_config.FEISHU_CHAT_ID` | 飞书机器人 |
| `timed_listener.py` | `~/.feishu_user_config.json` | 监听器 |
| `scheduler/eastmoney_scheduler.py` | `eastmoney_config` | 调度器 |

## 日常维护

### 查看配置
```bash
cat ~/.feishu_user_config.json
```

### 测试配置
```bash
cd /Users/echochen/MediaCrawler
python3 -c "import config; print(f'Chat ID: {config.FEISHU_CHAT_ID}')"
```

### 手动测试飞书通知
```bash
python3 /Users/echochen/.claude/skills/feishu-universal/scripts/feishu_bot_notifier.py --message "测试消息"
```

## 调度器管理

### 查看状态
```bash
ps aux | grep "main_eastmoney.py --scheduler" | grep -v grep
```

### 查看日志
```bash
tail -f /tmp/eastmoney_scheduler.log
```

### 重启调度器
```bash
# 停止旧的
kill $(ps aux | grep "main_eastmoney.py --scheduler" | grep -v grep | awk '{print $2}')

# 启动新的
cd /Users/echochen/MediaCrawler
nohup python3 main_eastmoney.py --scheduler > /tmp/eastmoney_scheduler.log 2>&1 &
```

## 执行时间

- **爬取时间**: 每天早上 8:00
- **监听窗口**: 8:00 - 8:15（15分钟）
- **检查间隔**: 每 5 分钟
- **超时处理**: 自动删除未选中的 PDF
