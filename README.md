# Document Intelligence System · 文档智能系统

基于大语言模型的**文档理解与多源数据融合系统**，支持文档智能对话、文档库管理、工作流编排等功能。

---

## 技术栈

| 层 | 技术 |
|------|------|
| **前端** | Vue 3 + Vite + Pinia + Axios |
| **后端** | Python FastAPI + Uvicorn |
| **LLM** | DeepSeek / 智谱 GLM / OpenAI 兼容接口 |
| **数据库** | PostgreSQL（可选 Supabase 兼容） |
| **文件存储** | 本地文件系统 / Azure Blob / Supabase Storage |
| **文档解析** | PyMuPDF（PDF）、python-docx（Word）、openpyxl（Excel）、docling |

---

## 项目结构

```
├── frontend/                     # Vue 3 前端
│   └── src/
│       ├── api/                  # HTTP 接口封装
│       ├── components/
│       │   ├── chat/             # 智能对话（ChatSidebar、ChatView）
│       │   ├── library/          # 文档库（LibrarySidebar、DocGrid）
│       │   ├── workflow/         # 工作流（WorkflowCanvas、WorkflowConfig）
│       │   ├── AppHeader.vue     # 顶部导航
│       │   ├── AppSidebar.vue    # 侧边栏导航
│       │   ├── AuthPanel.vue     # 登录面板
│       │   └── BatchModal.vue    # 批量处理模态框
│       ├── composables/          # 组合式函数（SSE、主题）
│       ├── stores/               # Pinia 状态管理
│       └── styles/               # 全局样式
├── src/                          # Python 后端
│   ├── api/
│   │   ├── main.py               # FastAPI 应用入口
│   │   └── routers/              # 路由模块（auth、sessions、messages、files、agents、library、workflows）
│   ├── core/
│   │   ├── agents/               # Agent 智能体（A/B/C/D + 对话/文档理解）
│   │   ├── llm/                  # LLM 服务（支持 DeepSeek、智谱等）
│   │   ├── orchestrator/         # 任务编排（协调器、执行器）
│   │   └── storage/              # 文件存储（Azure Blob、Supabase）
│   ├── db/                       # 数据库层
│   │   ├── repository/           # 数据访问（queries、extraction、mutations 等）
│   │   └── models.py             # 数据模型
│   ├── service/                  # 业务服务（agent_service、document_service）
│   ├── config.py                 # 全局配置
│   └── main.py                   # CLI 入口
├── scripts/                      # 运维脚本（数据库迁移、连接测试）
├── sql/                          # SQL 建表脚本
├── tests/                        # 集成测试
└── docs/                         # 项目文档
```

---

## 快速启动

### 1. 环境配置

复制 `.env.example` 为 `.env`，配置以下关键项：

```bash
# LLM 配置（二选一）
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-xxx

# 或
# LLM_PROVIDER=zhipu
# ZHIPU_API_KEY=xxx

# 数据库（可选）
DB_ENABLED=true
DATABASE_URL=postgresql://user:pass@host:5432/db?sslmode=require
```

### 2. 启动后端

```bash
cd src
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8001
# 或双击 start.bat
```

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

> 前端默认使用 Vite 代理，将 `/api` 请求转发到后端。

---

## 功能模块

### 智能对话

多模式 AI 对话，支持：

- **对话模式** — 通用 AI 问答
- **文档理解模式** — 基于上传文档的智能问答与内容分析
- **文件上传** — 支持 docx、pdf、txt、md、xlsx 等格式
- **从文档库导入** — 直接从文档库选择文件作为对话上下文
- **SSE 流式输出** — 实时流式响应

### 文档库

集中管理文档资源：

- **文档空间** — 按空间组织文档集合
- **文档上传与管理** — 上传、重命名、删除文档
- **文档预览** — 在线查看文档内容

### 工作流编排

多 Agent 协作任务编排：

- **可视化画布** — 拖拽式工作流设计（基于 HTML 画布）
- **多 Agent 支持** — 文档理解、实体提取、填表编辑等
- **任务执行与监控** — 实时查看执行进度与状态
- **批量处理** — 批量执行工作流任务

### Agent 能力

| Agent | 职责 |
|-------|------|
| **Agent A** | 指令解析与文档编辑（Word、Markdown、TXT 适配器） |
| **Agent B** | 实体提取与数据结构化 |
| **Agent C** | 数据入库与任务状态管理 |
| **Agent D** | 表格填表与模板填充 |
| **Conversation Agent** | 通用对话交互 |
| **Document Understand Agent** | 文档深层理解与问答 |

---

## API 概览

| 路径 | 说明 |
|------|------|
| `GET /health` | 服务健康检查 |
| `POST /api/auth/login` | 用户登录 |
| `POST /api/auth/register` | 用户注册 |
| `GET/POST /api/sessions` | 会话管理 |
| `GET/POST /api/messages` | 消息管理 |
| `POST /api/files/upload` | 文件上传 |
| `POST /api/agents/chat` | AI 对话（SSE 流式） |
| `GET/POST /api/library/spaces` | 文档库空间管理 |
| `GET/POST /api/library/documents` | 文档管理 |
| `GET/POST /api/workflows` | 工作流管理 |

---

## 配置参考

核心环境变量（详见 `src/config.py`）：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `LLM_PROVIDER` | `deepseek` | LLM 提供商 |
| `LLM_MODEL` | `deepseek-chat` | 模型名称 |
| `DEEPSEEK_API_KEY` | - | DeepSeek API 密钥 |
| `DB_ENABLED` | `false` | 是否启用数据库 |
| `DATABASE_URL` | - | PostgreSQL 连接串 |
| `AUTH_REQUIRE_LOGIN` | `false` | 是否强制登录 |
| `STORAGE_PROVIDER` | `local` | 文件存储方式 |
| `STORAGE_ENABLED` | `false` | 是否启用远程存储 |

---

## 开发

```bash
# 安装后端依赖
pip install -r requirements.txt

# 安装前端依赖
cd frontend && npm install

# 数据库迁移
python scripts/migrate_and_validate_db.py

# 运行测试
pytest
```