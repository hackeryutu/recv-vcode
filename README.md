# Mail Verification Service

基于 FastAPI 的邮件收取与查看服务，提供管理员后台、前端页面以及 REST API，方便在 Web 中快速查阅验证码或通知邮件。

## 功能特性

- **管理员后台**：增删改查邮箱账户，生成唯一 `mail_id` 与访问令牌。
- **邮件查看页面**：终端用户可通过链接查看特定邮箱的最近邮件，可按发件人筛选。
- **REST API**：通过 `/api/mail/messages` 获取邮件列表，便于自动化集成。
- **统一配置**：超时、日志等级和管理员凭证均可通过 `.env` 灵活配置。

## 环境要求

- Python 3.8+
- 依赖包见 `requirements.txt`（FastAPI、SQLAlchemy、python-dotenv 等）
- 默认使用 SQLite，首次启动时会在项目根目录创建 `mail_app.db`

## 快速开始

1. **获取代码**
   ```bash
   git clone <repo-url>
   cd recv-vcode
   ```

2. **创建并激活虚拟环境**

   Windows（PowerShell）：
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\activate
   ```

   macOS / Linux：
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

4. **准备配置文件**
   ```bash
   cp .env.example .env
   ```
   根据实际情况修改 `.env`，应用启动时会自动加载该文件。

## 配置说明 (`.env`)

| 变量名            | 描述                                         | 默认值            |
| ----------------- | -------------------------------------------- | ----------------- |
| `ADMIN_USERNAME`  | 管理后台用户名                               | `admin`           |
| `ADMIN_PASSWORD`  | 管理后台密码                                 | `admin123`        |
| `DEFAULT_TIMEOUT` | 所有外部请求默认超时（秒）                   | `30`              |
| `IMAP_TIMEOUT`    | IMAP 连接/检索超时（秒），未设置时跟随默认值 | `DEFAULT_TIMEOUT` |
| `HTTP_TIMEOUT`    | 其他 HTTP 请求超时（秒）                     | `DEFAULT_TIMEOUT` |
| `LOG_LEVEL`       | 日志等级，`INFO`/`DEBUG`/`WARNING` 等        | `INFO`            |
| `LOG_FORMAT`      | 日志格式字符串                               | `%(asctime)s - %(name)s - %(levelname)s - %(message)s` |

> 修改 `.env` 后重启服务即可生效，无需额外导出环境变量。

## 运行服务

### 开发模式（前台）

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- 管理后台：`http://127.0.0.1:8000/admin`
- 登录凭证来自 `.env` 的 `ADMIN_USERNAME` 和 `ADMIN_PASSWORD`

### 后台运行

**Linux / macOS**
```bash
nohup uvicorn main:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &
```
停止服务：
```bash
ps -ef | grep uvicorn
kill -9 <PID>
```

**Windows**
```powershell
start /B uvicorn main:app --host 0.0.0.0 --port 8000 > server.log 2>&1
```
或自定义 `run.py` 后使用 `pythonw run.py` 在后台运行。

## 使用指南

### 管理员后台
- 地址：`/admin`
- 功能：新增邮箱、编辑现有配置、删除账户。
- 默认发件人过滤支持多个地址，使用逗号或换行分隔；系统会按顺序合并这些发件人的邮件。
- 每个账户会生成一个 `mail_id` 与 `access_token`，供前台和 API 使用。

### 邮件查看页面
- 地址：`/mail?mail_id=<ID>&token=<TOKEN>&sender=<可选>`
- 作用：供最终用户查看最近邮件，可通过 `sender` 限制发件人。

### REST API
- `GET /api/mail/messages`
  - **必填**：`mail_id`、`token`
  - **选填**：`sender`（覆盖账户默认的发件人过滤）
  - **响应**：成功返回邮件列表；错误返回 `{ "error": "..." }`

## 安全与维护建议

- 部署前务必修改 `.env` 中的管理员账号密码。
- 根据 IMAP 服务稳定性适当调整 `DEFAULT_TIMEOUT` / `IMAP_TIMEOUT`。
- 生产环境建议配合 systemd、supervisor 或容器平台托管进程，并妥善管理日志。

## 故障排查

- **连接超时**：确认网络、防火墙或提升 `IMAP_TIMEOUT`。
- **日志仍显示 30 秒超时**：确保 `.env` 已更新并重启过服务，或直接导出环境变量覆盖。
- **邮件为空**：检查管理员后台配置的默认发件人或在请求中显式传入 `sender`。
