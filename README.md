StreamGate  
这是一个基于 FastAPI 开发的后端转发服务，主要用于在高并发场景下为 RAGFlow 提供接口代理与流式传输（SSE）支持。

项目简介  
本项目主要解决在高并发业务场景下，直接请求 RAGFlow 底层服务可能带来的连接数暴涨、流式响应不稳定等问题。通过 FastAPI 的异步架构与 HTTPX 连接池管理，建立一个轻量、高效的转发层，保障接口的响应速度与稳定性。

核心功能  

🔄异步接口转发：基于 async/await 架构，透传 RAGFlow 的 Chat、知识库等核心 API。

⚡流式响应支持：支持 SSE（Server-Sent Events）流式数据转发，确保前端大模型打字机效果流畅。

🛠️连接池优化：全局复用 httpx.AsyncClient，在高并发下复用 TCP 长连接，减少频繁创建/销毁连接的开销。

🛡️异常捕获：内置基础的超时与异常处理逻辑，防止底层服务波动导致前端崩溃。

技术栈  
开发框架：FastAPI

异步客户端：HTTPX

运行环境：Uvicorn

快速启动  
1. 安装依赖
```Bash
pip install fastapi uvicorn httpx python-dotenv
```
2. 配置环境变量  
在项目根目录创建 .env 文件：

代码段
```
RAGFLOW_BASE_URL=http://your-ragflow-server:8000
PORT=8000
```
3. 启动服务  
生产环境建议开启多个 Worker 以利用多核性能：

```Bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```
