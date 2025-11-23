# Mail Verification Service

这是一个基于 FastAPI 的邮件验证服务，支持邮件账户管理和邮件查看功能。

## 功能特性

- **管理员后台**：管理邮箱账户（增删改查）。
- **邮件查看**：通过 Web 界面查看指定账户的邮件。
- **API 支持**：提供 RESTful API 获取邮件列表。
- **异步获取**：邮件列表异步加载，提升用户体验。

## 环境要求

- Python 3.8+
- 依赖包见 `requirements.txt`

## 安装说明

1. 克隆或下载本项目到本地。
2. 安装依赖：

```bash
pip install -r requirements.txt
```

## 运行服务

### 1. 开发模式（前台运行）

在开发调试阶段，可以使用以下命令启动服务（支持代码热重载）：

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

启动后访问：
- 管理后台：`http://<服务器IP>:8000/admin`
  - 默认账号：`admin`
  - 默认密码：`admin123`

### 2. 服务器后台启动

#### Linux / macOS (推荐)

使用 `nohup` 命令让服务在后台运行，并将日志输出到 `server.log`：

```bash
nohup uvicorn main:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &
```

- **停止服务**：
  先找到进程 ID (PID)，然后 kill 掉：
  ```bash
  ps -ef | grep uvicorn
  kill -9 <PID>
  ```

#### Windows

使用 `start` 命令在后台启动：

```powershell
start /B uvicorn main:app --host 0.0.0.0 --port 8000 > server.log 2>&1
```

或者使用 Python 脚本启动（需创建一个 `run.py`）：

```python
# run.py
import uvicorn
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, log_level="info")
```
然后使用 `pythonw` (无窗口模式) 运行：
```powershell
pythonw run.py
```

## 访问与使用

服务启动后，可以通过浏览器访问以下地址：

### 1. 管理员后台
用于管理邮箱账户，包括创建新账户和查看现有账户信息。

- **访问地址**: `http://<服务器IP>:8000/admin`
  - 本地测试：`http://127.0.0.1:8000/admin`
- **登录认证**:
  - 默认账号：`admin`
  - 默认密码：`admin123`

### 2. 邮件查看页面
用户查看特定邮箱的邮件列表。需要使用管理员后台分配的 `mail_id` 和 `token`。

- **地址格式**: 
  ```
  http://<服务器IP>:8000/mail?mail_id=<邮箱ID>&token=<访问令牌>
  ```
- **示例**: 
  `http://<服务器IP>:8000/mail?mail_id=1001&token=8f4b2e1...`
- **参数说明**:
  - `mail_id`: 邮箱唯一标识 ID
  - `token`: 安全访问令牌 (Access Token)
  - `sender`: (可选) 仅显示指定发件人的邮件

## API 接口说明

- `GET /api/mail/messages`: 获取邮件列表数据 (JSON)
  - 参数: `mail_id`, `token`, `sender`

## 修改管理员密码

默认的管理员账号密码配置在 `main.py` 文件中。为了安全起见，建议在部署前修改。

1. 打开 `main.py` 文件。
2. 找到 `get_current_username` 函数（约第 20 行）。
3. 修改 `secrets.compare_digest` 中的第二个参数：

```python
# 修改用户名
correct_username = secrets.compare_digest(credentials.username, "你的新用户名")
# 修改密码
correct_password = secrets.compare_digest(credentials.password, "你的新密码")
```

4. 保存文件并重启服务即可生效。
