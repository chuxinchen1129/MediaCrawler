# 东方财富研报爬虫 - 配置说明 v3.0

## 飞书配置

所有飞书相关配置统一存储在：
```
~/.feishu_user_config.json
```

## 配置结构 v3.0

```json
{
  "app_id": "cli_a9d0ce936278dced",
  "app_secret": "OSDjdk36qaGZ0xzD7TXmgb5kmuRneuZy",
  "user_open_id": "ou_55a1ea53df8c6fe203ecb456d0a4db54",
  "chat_id": "oc_3806296430d27d3c4ca63cb88ae3f977",
  "folder_token": "",
  "target_table": {
    "app_token": "Fq2UwBpcIioq9skLNbocGiGKnsc",
    "table_id": "tblYOmRbvsHw5JxZ",
    "name": "默认导入表格"
  }
}
```

## 认证方式变更

### v3.0 (当前) - tenant_access_token

- ✅ 无需 OAuth 扫码授权
- ✅ Token 永不过期（只要 app_secret 不变）
- ✅ 自动获取，无需手动刷新

**工作原理**：
- 使用 `app_access_token/internal` 接口获取 tenant_access_token
- 创建的资源所有者是**应用**，不是用户
- 可以通过 API 完全控制

### v2.x (已废弃) - user_access_token

- ❌ 需要 OAuth 扫码授权
- ❌ refresh_token 30天过期
- ❌ 需要手动重新授权

## 配置加载方式

`config/eastmoney_config.py` 自动从 `~/.feishu_user_config.json` 读取配置：

```python
_feishu_config_path = os.path.expanduser("~/.feishu_user_config.json")
if os.path.exists(_feishu_config_path):
    with open(_feishu_config_path, 'r') as f:
        _feishu_config = json.load(f)
    FEISHU_CHAT_ID = _feishu_config.get('chat_id', _feishu_config.get('user_open_id', ''))
    FEISHU_APP_ID = _feishu_config.get('app_id', '')
    FEISHU_APP_SECRET = _feishu_config.get('app_secret', '')
```

## 文件关联

| 文件 | 飞书配置来源 | 认证方式 |
|------|-------------|----------|
| `config/eastmoney_config.py` | `~/.feishu_user_config.json` | tenant_token |
| `feishu/eastmoney_bot.py` | `eastmoney_config` | tenant_token |
| `feishu_listener.py` | `~/.feishu_user_config.json` | tenant_token |
| `scheduler/eastmoney_scheduler.py` | `eastmoney_config` | tenant_token |

## 日常维护

### 查看配置
```bash
cat ~/.feishu_user_config.json
```

### 测试配置
```bash
cd ~/Desktop/DMS/skills/feishu-universal/scripts
python3 feishu_token_checker.py
```

### 测试飞书通知
```bash
cd ~/Desktop/DMS/skills/feishu-universal/scripts
python3 feishu_bot_notifier.py --message "测试消息"
```

### 测试导入到目标表格
```bash
cd ~/Desktop/DMS/skills/feishu-universal/scripts
python3 feishu_user_auto.py import-to-target --excel /path/to/data.xlsx
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

## 迁移指南 (从 v2.x 到 v3.0)

如果你有旧的配置文件，需要：

1. 删除旧字段：
   - `user_access_token`
   - `refresh_token`
   - `expires_at`
   - `auth_time`

2. 添加新字段（可选）：
   - `chat_id`: 明确的消息接收目标
   - `folder_token`: 创建 Base 时的父文件夹
   - `target_table`: 默认导入目标表格

3. 运行测试：
   ```bash
   python3 feishu_token_checker.py
   ```

## 归档文件

以下文件已移动到 `archive/` 目录：
- `feishu_oauth_setup.py` - OAuth 授权脚本（不再需要）
- `test_feishu_oauth.py` - OAuth 测试脚本（不再需要）
