# A股全栈数据工具包 (A-Stock-Data) — FastAPI 高性能后端 🚀

本项目是基于 `SKILL.md`（V3.2.3 版）数据意图构建的一个完善、专业的 **Python FastAPI 数据服务**，开箱即用，支持一键部署至 **Railway**。

## 🌟 核心设计模式

本项目采用了标准的 **分层架构设计模式 (Layered Architecture Pattern)**：
1. **Core 层 (核心配置)**: 管理限流节流机制 (`limiter.py` / `em_get` 随机抖动)、连接池会话复用以及 `mootdx` 的 TCP 服务器多重自动探测。
2. **Service 层 (服务层)**: 隔离核心业务逻辑，严格映射 `SKILL.md` 的七层数据架构，包括行情、研报、信号、资金、新闻、基本面和公告，彻底做到零中间冗余依赖。
3. **Router 层 (路由层)**: 暴露标准的 RESTful 接口，对数据输入进行 Pydantic 校验，内置前向估值与 PEG 精准分析模型。

---

## 📂 项目文件结构

```
/python-fastapi
├── Dockerfile                  # Railway 专用的轻量化容器配置
├── railway.json                # Railway 自动构建与健康检查参数
├── requirements.txt            # 项目 Python 依赖声明
├── README.md                   # 部署与使用文档
└── app
    ├── __init__.py
    ├── main.py                 # FastAPI 入口、CORS 与全局异常拦截
    ├── config.py               # Pydantic Settings 配置加载
    ├── core
    │   ├── __init__.py
    │   ├── limiter.py          # 东财防封统一节流阀 (em_get/datacenter)
    │   └── mootdx_client.py    # mootdx TCP 自动测速握手客户端
    ├── services
    │   ├── __init__.py
    │   ├── base.py             #  ticker 格式归一化工具类
    │   ├── market.py           # Layer 1: 行情层 (Mootdx + 腾讯 + 百度)
    │   ├── reports.py          # Layer 2: 研报层 (东财列表 + 一致预期 + iwencai)
    │   ├── signals.py          # Layer 3: 信号层 (同花顺热点/北向 + 东财所属概念板块)
    │   ├── capital.py          # Layer 4: 资金/筹码层 (两融 + 大宗 + 股东 + 分红 + 120日资金流)
    │   ├── news.py             # Layer 5: 新闻层 (个股新闻 + 7x24快讯)
    │   ├── financials.py       # Layer 6: 基础数据层 (财务季报 + 文本F10 + 新浪三表)
    │   └── announcements.py    # Layer 7: 公告层 (巨潮资讯)
    └── routers
        ├── __init__.py
        └── api.py              # 精准映射 28 个端点的路由分发中心
```

---

## 🛠️ 本地开发运行

```bash
# 1. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量 (可创建 .env 文件)
export IWENCAI_API_KEY="your_optional_key"

# 4. 启动服务
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

访问 `http://localhost:8000/docs` 即可进入 Swagger UI 调试 28 个 API 接口。

---

## 🚆 Railway 一键部署步骤

1. **上传代码到 GitHub**：新建一个 GitHub 仓库，将 `/python-fastapi` 下的所有内容提交。
2. **连接 Railway 平台**：
   - 登录 [Railway 官网](https://railway.app/)，点击 **+ New Project**。
   - 选择 **Deploy from GitHub repo**，关联你刚才创建的仓库。
3. **配置环境变量 (Variables)**：
   - `PORT`: 8000（FastAPI 的工作端口，Railway 会自动检测并映射）
   - `IWENCAI_API_KEY`: *(可选)* 如果需要运行 iwencai NLP 语义选股，请填入你的 key。
4. **服务构建与部署**：
   - Railway 会自动识别项目根目录下的 `Dockerfile` 并通过云端 Dockerfile 引擎自动拉取 `python:3.10-slim` 构建镜像。
   - `railway.json` 文件已配置完毕，包含了自动探活健康检查 `/health`，部署完成即进入 online 态。
