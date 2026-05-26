# StreamGate

StreamGate 是一个基于 FastAPI 的 RAGFlow 流式网关服务，用于在前端和 RAGFlow 之间提供统一的会话创建、用户分组路由、SSE 流式问答转发、并发控制和请求追踪能力。

## 功能特性

- 按用户分组和业务类型选择不同的 RAGFlow Chat ID
- 支持知识库问答和文件总结两类 Chat 场景
- 自动创建或复用 RAGFlow session
- 通过 Server-Sent Events 转发 RAGFlow 流式回答
- 为每个请求生成或透传 `X-Request-Id`
- 内置全局并发和 RAGFlow 并发限制
- 提供安全的 RAGFlow 配置诊断接口
- 使用 loguru 输出控制台日志和文件日志

## 技术栈

- Python 3.13+
- FastAPI
- httpx
- Pydantic / pydantic-settings
- loguru
- uvicorn

## 目录结构

```text
.
├── app
│   ├── api              # HTTP API 路由
│   ├── core             # 配置、日志、错误、SSE 和并发控制
│   ├── middleware       # 请求中间件
│   ├── schemas          # 请求和响应数据模型
│   ├── services         # RAGFlow、用户和流式编排服务
│   └── main.py          # FastAPI 应用入口
├── tests                # pytest 测试
├── logs                 # 运行日志目录
├── pyproject.toml       # 项目依赖和 Python 版本要求
├── uv.lock              # uv 锁定文件
└── README.md
```

## 环境准备

项目使用 `uv` 管理依赖。首次运行前请先同步依赖：

```bash
uv sync
```

复制 `.env.example` 为 `.env`，并按实际 RAGFlow 环境填写配置：

```env
APP_NAME=StreamGate
RAGFLOW_BASE_URL=http://your-ragflow-host
RAGFLOW_API_KEY=your-ragflow-api-key

RAGFLOW_OFFICE_LEADER_KB_CHAT_ID=your-office-leader-kb-chat-id
RAGFLOW_OFFICE_LEADER_SUMMARY_CHAT_ID=your-office-leader-summary-chat-id
RAGFLOW_DEPARTMENT_LEADER_KB_CHAT_ID=your-department-leader-kb-chat-id
RAGFLOW_DEPARTMENT_LEADER_SUMMARY_CHAT_ID=your-department-leader-summary-chat-id

RAGFLOW_CONNECT_TIMEOUT=10
RAGFLOW_READ_TIMEOUT=180
RAGFLOW_WRITE_TIMEOUT=10
RAGFLOW_POOL_TIMEOUT=10

HTTP_MAX_CONNECTIONS=200
HTTP_MAX_KEEPALIVE_CONNECTIONS=50
GLOBAL_CONCURRENCY=100
RAGFLOW_CONCURRENCY=30
```

## 启动服务

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

启动后可访问：

- 健康检查：`GET http://localhost:8000/health`
- RAGFlow 配置诊断：`GET http://localhost:8000/diagnostics/ragflow`
- OpenAPI 文档：`http://localhost:8000/docs`

## 用户分组

当前开发阶段通过请求头 `X-User-Id` 识别用户分组：

| X-User-Id | 用户分组 |
| --- | --- |
| `office_test` | `office_leader` |
| `department_test` | `department_leader` |

后续可以在 `app/services/user_service.py` 中替换为数据库、JWT、统一身份认证或 OA 用户体系。

## API 说明

### 健康检查

```http
GET /health
```

响应示例：

```json
{
  "status": "ok",
  "app": "StreamGate"
}
```

### 创建会话

```http
POST /api/chat/session
Content-Type: application/json
X-User-Id: office_test
```

请求体：

```json
{
  "chat_type": "kb",
  "session_name": "示例会话"
}
```

字段说明：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `chat_type` | string | 是 | `kb` 表示知识库问答，`summary` 表示文件总结 |
| `session_name` | string | 否 | 会话名称，不传时后端使用默认名称 |

响应示例：

```json
{
  "code": 0,
  "message": "",
  "data": {
    "request_id": "9c2f4d6c0c8b4b40a07e6cb0cf4a7fd3",
    "session_id": "ragflow-session-id",
    "chat_type": "kb",
    "session_create_time": 0.236
  }
}
```

### 流式问答

```http
POST /api/chat/stream
Content-Type: application/json
X-User-Id: office_test
Accept: text/event-stream
```

请求体：

```json
{
  "chat_type": "kb",
  "question": "请介绍一下这个知识库的主要内容",
  "session_id": "ragflow-session-id",
  "session_name": "示例会话"
}
```

字段说明：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `chat_type` | string | 是 | `kb` 表示知识库问答，`summary` 表示文件总结 |
| `question` | string | 是 | 用户问题 |
| `session_id` | string | 否 | 已有 RAGFlow 会话 ID；不传时自动创建新会话 |
| `session_name` | string | 否 | 自动创建新会话时使用的名称 |

SSE 事件示例：

```text
data: {"type":"start","request_id":"..."}

data: {"type":"session","request_id":"...","session_id":"...","session_create_time":0.212,"is_new_session":true}

data: {"type":"answer","answer":"回答内容","session_id":"...","message_id":"...","request_id":"..."}

data: {"type":"reference","reference":{},"request_id":"..."}

data: {"type":"done","request_id":"..."}

data: {"type":"end","request_id":"...","total_time":3.482}
```

错误也会通过 SSE 返回：

```text
data: {"type":"error","request_id":"...","message":"RAGFlow 调用失败"}
```

### RAGFlow 配置诊断

```http
GET /diagnostics/ragflow
```

该接口只返回安全的配置摘要，用于检查 RAGFlow 地址、API Key 是否已配置、各用户分组和 Chat 类型的映射是否存在、超时和并发参数。接口不会返回 API Key 原文或 Chat ID 原文。

## 请求追踪与日志

客户端可以传入 `X-Request-Id`，服务端会复用该值；如果未传入，服务端会自动生成。响应头也会返回 `X-Request-Id`，便于前端、测试脚本和服务端日志关联排查。

日志默认输出到：

- 控制台
- `logs/streamgate.log`

## 并发控制

`app/core/limiter.py` 提供两层并发限制：

- `GLOBAL_CONCURRENCY`：限制 StreamGate 整体并发
- `RAGFLOW_CONCURRENCY`：限制同时调用 RAGFlow 的并发

可以根据 RAGFlow 服务能力和部署资源在 `.env` 中调整。

## 开发命令

```bash
# 安装或同步依赖
uv sync

# 启动开发服务
uv run uvicorn app.main:app --reload

# 运行测试
uv run pytest -v

# 查看 OpenAPI 文档
# http://localhost:8000/docs
```

## 注意事项

- `.env` 中包含 API Key 和 Chat ID，请勿提交到代码仓库。
- 当前用户识别逻辑仍是开发阶段映射表，生产环境应替换为正式认证体系。
- RAGFlow 流式返回的 `answer` 当前按原始内容透传，不在网关层做差分处理。
