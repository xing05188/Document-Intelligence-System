# Document Intelligence System · 文档智能系统

<p align="center">
  <em>基于大语言模型的文档理解与多源数据融合系统</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Frontend-Vue%203-4FC08D?logo=vuedotjs" alt="Vue 3">
  <img src="https://img.shields.io/badge/Backend-Python%20FastAPI-009688?logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/LLM-DeepSeek%20%7C%20GLM%20%7C%20OpenAI-FF6F00" alt="LLM">
  <img src="https://img.shields.io/badge/Database-PostgreSQL-4169E1?logo=postgresql" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/License-MIT-yellow" alt="License">
  <img src="https://img.shields.io/badge/Status-Active-brightgreen" alt="Status">
</p>

---

## 目录

- [项目简介](#项目简介)
- [核心特性](#核心特性)
- [技术栈](#技术栈)
- [快速开始](#快速开始)
  - [前置要求](#前置要求)
  - [环境配置](#环境配置)
  - [启动后端](#启动后端)
  - [启动前端](#启动前端)
- [功能模块](#功能模块)
  - [智能对话](#智能对话)
  - [文档库管理](#文档库管理)
  - [工作流编排](#工作流编排)
  - [Agent 能力矩阵](#agent-能力矩阵)
- [项目结构](#项目结构)
- [API 概览](#api-概览)
- [配置参考](#配置参考)
- [开发指南](#开发指南)
- [贡献指南](#贡献指南)
- [许可证](#许可证)

---

## 项目简介

**Document Intelligence System** 是一个基于大语言模型（LLM）构建的智能文档处理平台，融合了文档理解、知识问答、多 Agent 协作工作流编排等核心能力。系统支持多种文档格式（PDF、Word、Excel、Markdown、TXT），提供从文档解析、内容理解到数据结构化、入库管理的全链路解决方案。

无论是构建企业级文档知识库，还是实现复杂的文档自动化处理流程，本项目都能为您提供灵活、可扩展的基础架构。

> **适用场景：** 企业文档管理、智能客服知识库、合同审查自动化、研究报告分析、多步骤文档处理流水线。

---

## 核心特性

- **智能对话** — 支持通用问答与文档理解双模式，基于上传文档进行上下文感知的智能问答
- **文档库管理** — 按空间组织文档集合，支持上传、重命名、删除、在线预览等全生命周期管理
- **工作流编排** — 可视化拖拽画布，多 Agent 协作完成复杂文档处理任务，支持批量执行
- **多 Agent 架构** — 六大 Agent 各司其职，覆盖指令解析、实体提取、数据入库、表格填充等场景
- **流式响应** — 基于 SSE（Server-Sent Events）实现实时的流式对话输出，交互体验流畅
- **多格式支持** — 兼容 PDF、DOCX、XLSX、TXT、Markdown 等多种文档格式的解析与处理
- **灵活部署** — 支持本地文件存储与远程存储（Azure Blob / Supabase Storage），可配置数据库开关
- **多 LLM 兼容** — 支持 DeepSeek、智谱 GLM、OpenAI 兼容接口，无缝切换

---

## 技术栈

| 层次 | 技术选型 |
|------|----------|
| **前端框架** | Vue 3 + Vite + Pinia + Axios |
| **后端框架** | Python FastAPI + Uvicorn |
| **大语言模型** | DeepSeek / 智谱 GLM / OpenAI 兼容接口 |
| **数据库** | PostgreSQL（可选，支持 Supabase 兼容） |
| **文件存储** | 本地文件系统 / Azure Blob / Supabase Storage |
| **文档解析** | PyMuPDF（PDF）、python-docx（Word）、openpyxl（Excel）、docling |

---

## 快速开始

### 前置要求

- Python 3.9+
- Node.js 18+
- PostgreSQL（可选，仅在启用数据库时需要）
- pip（Python 包管理器）
- npm 或 pnpm（Node 包管理器）

### 环境配置

1. 复制环境变量模板：

```bash
cp .env.example .env
```

2. 编辑 `.env` 文件，配置关键参数：

```bash
# =======================
# LLM 配置（二选一）
# =======================

# 选项一：DeepSeek
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-your-deepseek-api-key

# 选项二：智谱 GLM
# LLM_PROVIDER=zhipu
# ZHIPU_API_KEY=your-zhipu-api-key

# =======================
# 数据库（可选）
# =======================
DB_ENABLED=true
DATABASE_URL=postgresql://user:password@host:5432/database?sslmode=require
```

### 启动后端

```bash
cd src
pip install -r ../requirements.txt
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8001
```

> 也可直接双击 `start.bat` 脚本快速启动。

### 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端开发服务器默认运行在 `http://localhost:5173`，Vite 已配置代理将 `/api` 请求转发至后端 `http://localhost:8001`。

---

## 功能模块

### 智能对话

系统提供双模式 AI 对话能力：

| 模式 | 功能说明 |
|------|----------|
| **对话模式** | 通用 AI 问答，适用于日常对话与信息查询 |
| **文档理解模式** | 基于上传文档的智能问答与内容深度分析 |

**支持能力：**
- 上传 docx、pdf、txt、md、xlsx 等常见文档格式作为对话上下文
- 从文档库直接导入已有文档参与对话
- 基于 SSE 的流式实时响应，逐 Token 展示推理过程

### 文档库管理

集中管理所有文档资源的能力：

- **文档空间** — 按空间（Space）组织文档集合，实现逻辑隔离
- **文档操作** — 支持上传、重命名、删除等全生命周期管理
- **在线预览** — 内置文档预览功能，无需下载即可查看内容

### 工作流编排

基于多 Agent 协作的可视化任务编排系统：

- **可视化画布** — 基于 HTML Canvas 的拖拽式工作流设计界面
- **多 Agent 支持** — 集成文档理解、实体提取、填表编辑等多种 Agent
- **任务执行与监控** — 实时查看工作流执行进度与各节点状态
- **批量处理** — 支持批量执行工作流任务，提高处理效率

### Agent 能力矩阵

| Agent | 核心职责 |
|-------|----------|
| **Agent A** | 指令解析与文档编辑（Word、Markdown、TXT 适配器） |
| **Agent B** | 实体提取与数据结构化 |
| **Agent C** | 数据入库与任务状态管理 |
| **Agent D** | 表格填表与模板填充 |
| **Conversation Agent** | 通用对话交互 |
| **Document Understand Agent** | 文档深层理解与领域问答 |

---

## 项目结构

```
document-intelligence-system/
│
├── frontend/                     # Vue 3 前端应用
│   └── src/
│       ├── api/                  # HTTP 接口封装层
│       ├── components/
│       │   ├── chat/             # 智能对话组件（ChatSidebar、ChatView）
│       │   ├── library/          # 文档库组件（LibrarySidebar、DocGrid）
│       │   ├── workflow/         # 工作流组件（WorkflowCanvas、WorkflowConfig）
│       │   ├── AppHeader.vue     # 顶部导航栏
│       │   ├── AppSidebar.vue    # 侧边栏导航
│       │   ├── AuthPanel.vue     # 登录面板
│       │   └── BatchModal.vue    # 批量处理模态框
│       ├── composables/          # 组合式函数（SSE 连接、主题切换）
│       ├── stores/               # Pinia 状态管理
│       └── styles/               # 全局样式
│
├── src/                          # Python 后端服务
│   ├── api/
│   │   ├── main.py               # FastAPI 应用入口与中间件
│   │   └── routers/              # 路由模块
│   │       ├── auth.py           # 认证授权
│   │       ├── sessions.py       # 会话管理
│   │       ├── messages.py       # 消息管理
│   │       ├── files.py          # 文件上传
│   │       ├── agents.py         # Agent 交互
│   │       ├── library.py        # 文档库
│   │       └── workflows.py      # 工作流
│   ├── core/
│   │   ├── agents/               # Agent 智能体实现（A/B/C/D + 对话/文档理解）
│   │   ├── llm/                  # LLM 服务封装（DeepSeek、智谱等）
│   │   ├── orchestrator/         # 任务编排引擎（协调器、执行器）
│   │   └── storage/              # 文件存储适配器（Azure Blob、Supabase）
│   ├── db/                       # 数据库层
│   │   ├── repository/           # 数据访问层（queries、extraction、mutations）
│   │   └── models.py             # 数据模型定义
│   ├── service/                  # 业务服务层（agent_service、document_service）
│   ├── config.py                 # 全局配置管理
│   └── main.py                   # CLI 命令行入口
│
├── scripts/                      # 运维与工具脚本
├── sql/                          # SQL 建表与迁移脚本
├── tests/                        # 集成测试与单元测试
└── docs/                         # 项目文档与设计资料
```

---

## API 概览

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/health` | 服务健康检查 |
| `POST` | `/api/auth/login` | 用户登录 |
| `POST` | `/api/auth/register` | 用户注册 |
| `GET` | `/api/sessions` | 获取会话列表 |
| `POST` | `/api/sessions` | 创建新会话 |
| `GET` | `/api/messages` | 获取消息记录 |
| `POST` | `/api/messages` | 发送消息 |
| `POST` | `/api/files/upload` | 上传文件 |
| `POST` | `/api/agents/chat` | AI 对话（SSE 流式） |
| `GET` | `/api/library/spaces` | 获取文档库空间列表 |
| `POST` | `/api/library/spaces` | 创建文档库空间 |
| `GET` | `/api/library/documents` | 获取文档列表 |
| `POST` | `/api/library/documents` | 上传文档 |
| `GET` | `/api/workflows` | 获取工作流列表 |
| `POST` | `/api/workflows` | 创建工作流 |

---

## 配置参考

以下为核心环境变量，完整配置项请参阅 [`src/config.py`](src/config.py)。

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `LLM_PROVIDER` | `deepseek` | LLM 提供商（deepseek / zhipu / openai） |
| `LLM_MODEL` | `deepseek-chat` | 模型名称 |
| `DEEPSEEK_API_KEY` | — | DeepSeek API 密钥 |
| `ZHIPU_API_KEY` | — | 智谱 GLM API 密钥 |
| `OPENAI_API_KEY` | — | OpenAI API 密钥 |
| `OPENAI_BASE_URL` | — | OpenAI 兼容接口地址 |
| `DB_ENABLED` | `false` | 是否启用数据库持久化 |
| `DATABASE_URL` | — | PostgreSQL 连接字符串 |
| `AUTH_REQUIRE_LOGIN` | `false` | 是否强制登录认证 |
| `STORAGE_PROVIDER` | `local` | 文件存储方式（local / azure / supabase） |
| `STORAGE_ENABLED` | `false` | 是否启用远程存储 |

---

## 开发指南

```bash
# 安装后端依赖
pip install -r requirements.txt

# 安装前端依赖
cd frontend && npm install

# 数据库迁移（首次使用需执行）
python scripts/migrate_and_validate_db.py

# 运行后端测试
pytest

# 运行前端 lint
cd frontend && npm run lint
```

### 代码风格

- **Python 后端**：遵循 PEP 8 规范，建议使用 `black` + `isort` 格式化
- **Vue 前端**：遵循 ESLint + Prettier 配置

---

## 贡献指南

欢迎对本项目贡献代码、提交 Issue 或改进建议！

### 贡献流程

1. **Fork** 本仓库至您的 GitHub 账号
2. **创建特性分支**：`git checkout -b feat/your-feature-name`
3. **提交更改**：`git commit -m "feat: add some feature"`
4. **推送到分支**：`git push origin feat/your-feature-name`
5. **提交 Pull Request**

### 分支命名规范

- `feat/*` — 新功能
- `fix/*` —  Bug 修复
- `docs/*` — 文档更新
- `refactor/*` — 代码重构
- `test/*` — 测试相关

### 提交信息规范

建议遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```
<type>: <简短描述>

<可选详细说明>
```

---

## 许可证

本项目基于 [MIT License](LICENSE) 开源，您可以自由使用、修改和分发，但需保留原始版权声明。