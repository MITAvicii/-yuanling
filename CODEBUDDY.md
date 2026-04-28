# CODEBUDDY.md This file provides guidance to CodeBuddy when working with code in this repository.

## 项目概述

源灵AI（Mini-OpenClaw）是一个轻量级、全透明的 AI Agent 系统。核心特点：
- **文件即记忆**：使用 Markdown/JSON 文件系统而非向量数据库
- **技能即插件**：通过文件夹结构管理 Agent 能力
- **透明可控**：所有 System Prompt 拼接、工具调用、记忆读写对开发者完全透明

## 常用命令

### 后端 (backend/)
```bash
# 激活 conda 环境
conda activate yuanling

# 安装依赖（清华源加速）
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 配置 API Key
cp .env.example .env
# 编辑 .env 填入 API Key

# 启动开发服务器 (端口 8002)
uvicorn app:app --host 0.0.0.0 --port 8002 --reload

# 或直接运行
python app.py

# 运行测试
pytest
```

### 前端 (frontend/)
```bash
# 安装依赖（淘宝镜像加速）
npm install --registry=https://registry.npmmirror.com

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build

# 运行 lint
npm run lint
```

## 技术栈

### 后端
- Python 3.10+ (强制 Type Hinting)
- FastAPI (RESTful API + SSE 流式输出)
- LangChain 1.x `create_agent` API (禁用 AgentExecutor)
- LlamaIndex Core (Hybrid Search: BM25 + Vector)
- DeepSeek/兼容 OpenAI API 格式的模型

### 前端
- Next.js 14+ (App Router) + TypeScript
- Shadcn/UI + Tailwind CSS
- Monaco Editor (Light Theme)
- Apple 风格毛玻璃 UI

## 项目结构

```
mini-openclaw/
├── backend/
│   ├── app.py              # FastAPI 入口
│   ├── config.py           # 全局配置
│   ├── api/                # API 路由层
│   │   ├── chat.py         # POST /api/chat (SSE)
│   │   ├── sessions.py     # 会话 CRUD
│   │   ├── files.py        # 文件读写
│   │   └── ...
│   ├── tools/              # 五大核心工具
│   │   ├── terminal.py     # ShellTool 沙箱封装
│   │   ├── python_repl.py  # PythonREPLTool
│   │   ├── fetch_url.py    # RequestsGetTool + HTML清洗
│   │   ├── read_file.py    # ReadFileTool (白名单)
│   │   └── rag_search.py   # LlamaIndex Hybrid Search
│   ├── graph/              # LangGraph 状态机定义
│   ├── skills/             # Agent Skills 文件夹
│   │   └── {skill_name}/SKILL.md
│   ├── memory/             # 记忆存储
│   │   ├── logs/           # Daily logs
│   │   └── MEMORY.md       # 核心长期记忆
│   ├── sessions/           # JSON 会话记录
│   └── workspace/          # System Prompt 组件
│       ├── SOUL.md         # 核心设定
│       ├── IDENTITY.md     # 自我认知
│       ├── USER.md         # 用户画像
│       ├── AGENTS.md       # 行为准则 (必含技能调用协议)
│       └── SKILLS_SNAPSHOT.md
│
├── frontend/
│   └── src/
│       ├── app/            # Next.js App Router
│       ├── components/
│       │   ├── chat/       # 对话流 + 思考链可视化
│       │   └── editor/     # Monaco Editor Wrapper
│       └── lib/api.ts      # Fetch wrapper (端口 8002)
│
└── knowledge/              # RAG 知识库文档 (PDF/MD/TXT)
```

## 核心架构

### Agent Skills 系统 (指令遵循范式)

Skills 是 Markdown 文件，而非 Python 函数。Agent 通过 `read_file` 读取 SKILL.md 学习如何使用基础工具完成任务。

**调用流程**:
1. Agent 在 System Prompt 中看到 `available_skills` 列表
2. 用户请求匹配某技能 → Agent 调用 `read_file` 读取 SKILL.md
3. Agent 理解操作步骤 → 调用 Core Tools (terminal/python_repl/fetch_url) 执行

### System Prompt 组装顺序

1. SKILLS_SNAPSHOT.md (能力列表)
2. SOUL.md (核心设定)
3. IDENTITY.md (自我认知)
4. USER.md (用户画像)
5. AGENTS.md (行为准则 + 记忆操作指南)
6. MEMORY.md (长期记忆)

**截断策略**: 单文件超 20k 字符时截断并标记 `...[truncated]`

### 会话存储格式

路径: `backend/sessions/{session_id}.json`

格式: 标准 JSON 数组，包含 `user`, `assistant`, `tool` 类型消息。多段响应分别存储以保留完整工具调用过程。

## 关键设计决策

| 决策 | 理由 |
|------|------|
| `create_agent()` 而非 `AgentExecutor` | LangChain 1.x 推荐的现代 API，支持原生流式 |
| 每次请求重建 Agent | 确保 System Prompt 反映 workspace 文件的实时编辑 |
| 文件驱动而非数据库 | 降低部署门槛，所有状态透明可查 |
| 技能 = Markdown 指令 | Agent 自主阅读执行，无需注册新 Python 函数 |
| 路径白名单 + 遍历检测 | 双重防护，terminal 和 read_file 均受沙箱约束 |

## API 端点 (端口 8002)

| 路径 | 方法 | 说明 |
|------|------|------|
| `/api/chat` | POST | SSE 流式对话 |
| `/api/sessions` | GET/POST | 会话列表/创建 |
| `/api/sessions/{id}` | PUT/DELETE | 重命名/删除会话 |
| `/api/files?path=...` | GET/POST | 读取/保存文件 |
| `/api/skills` | GET | 列出技能 |
| `/api/config/rag-mode` | GET/PUT | RAG 模式开关 |
