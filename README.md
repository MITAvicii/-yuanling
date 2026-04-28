# 源灵AI助手管家

基于 LangGraph + LangChain + Next.js 的本地 AI Agent 系统，提供透明的 AI 辅助能力。

## 功能特性

- 🤖 **AI Agent** - 基于 ReAct 架构的智能助手，支持流式响应
- 💬 **实时对话** - Server-Sent Events (SSE) 实时推送
- 📁 **文件工具** - 安全受限的文件读写、Terminal 执行
- 🔍 **RAG 知识检索** - 本地 Embedding + BM25 混合检索
- 🔌 **平台集成** - 飞书 Webhook 集成
- 🧠 **Skills 插件** - Markdown 编写的技能扩展

## 项目结构

```
源灵AI助手管家/
├── backend/              # Python FastAPI 后端
│   ├── api/             # API 路由
│   ├── graph/           # LangGraph Agent
│   ├── tools/           # LangChain 工具函数
│   ├── platforms/       # 平台集成
│   ├── workspace/       # 系统 Prompt 组件
│   ├── skills/          # 技能插件
│   └── models/          # 本地 Embedding 模型
├── frontend/            # Next.js 14 前端
│   └── src/
│       └── app/         # App Router
├── start.sh             # 启动脚本
├── stop.sh              # 停止脚本
└── AGENTS.md            # Agent 配置说明
```

## 快速开始

### 1. 克隆项目

```bash
git clone <your-repo-url>
cd 源灵AI助手管家
```

### 2. 配置环境变量

在 `backend/` 目录下创建 `.env` 文件：

```bash
cp backend/.env.example backend/.env
```

编辑 `backend/.env`，填入你的 API 密钥：

```env
DEEPSEEK_API_KEY=your-api-key-here
DASHSCOPE_API_KEY=your-aliyun-api-key  # 可选，用于Embedding
```

### 3. 启动服务（推荐方式）

```bash
./start.sh
```

这将同时启动：
- 后端服务: http://localhost:8002
- 前端服务: http://localhost:3000

### 4. 手动启动

如需分别启动：

**后端：**
```bash
conda activate yuanling
cd 源灵AI助手管家
uvicorn backend.app:app --host 0.0.0.0 --port 8002 --reload
```

**前端：**
```bash
cd frontend
npm run dev
```

## 使用说明

### 与 AI 对话

打开浏览器访问 http://localhost:3000 ，在输入框中发送消息即可开始对话。

### 可用工具

Agent 可以自动使用以下工具：
- `terminal` - 执行终端命令
- `python_repl` - 运行 Python 代码
- `read_file` / `write_file` - 文件读写
- `rag_search` - 知识检索
- `fetch_url` - 获取网页内容
- `feishu_sender` - 发送飞书消息

### 添加技能

将技能说明写入 `backend/skills/<skill_name>/SKILL.md`，Agent 会自动加载。

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | FastAPI, LangGraph, LangChain, LlamaIndex |
| 前端 | Next.js 14, React, Tailwind CSS |
| LLM | DeepSeek (默认) |
| Embedding | BGE-base-zh-v1.5 |

## 注意事项

- **模型文件**：本地 Embedding 模型 (~400MB) 已在 .gitignore 中排除，首次使用需自行下载
- **会话数据**：`backend/sessions/` 包含用户会话，已排除以保护隐私
- **API 密钥**：必须配置 `.env` 文件中的 API 密钥才能使用 LLM

## 开发相关

### 安装依赖

```bash
# 后端
conda activate yuanling
pip install -r backend/requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 前端
cd frontend
npm install --registry=https://registry.npmmirror.com
```

### 测试

```bash
pytest
```

### 代码规范

- 后端遵循 AGENTS.md 中的 Python 代码风格
- 前端运行 `npm run lint` 检查

## License

MIT