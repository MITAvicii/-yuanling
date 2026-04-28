# 源灵AI助手管家

基于 LangGraph + LangChain + Next.js 的本地 AI Agent 系统，提供透明的 AI 辅助能力。

## 功能特性

- 🤖 **AI Agent** - 基于 ReAct 架构的智能助手，支持流式响应
- 💬 **实时对话** - Server-Sent Events (SSE) 实时推送
- 📁 **文件工具** - 安全受限的文件读写、Terminal 执行
- 🔍 **RAG 知识检索** - 本地 Embedding + BM25 混合检索
- 🔌 **平台集成** - 飞书 Webhook 集成
- 🧠 **Skills 插件** - Markdown 编写的技能扩展

## 环境要求

- **Python**: 3.10+ (via conda)
- **Node.js**: 18+
- **API 密钥**: DeepSeek API Key

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
└── README.md            # 说明文档
```

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/MITAvicii/-yuanling.git
cd 源灵AI助手管家
```

### 2. 配置环境

**创建 conda 环境：**

```bash
conda create -n yuanling python=3.11 -y
conda activate yuanling
```

**安装后端依赖：**

```bash
pip install -r backend/requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

**安装前端依赖：**

```bash
cd frontend
npm install --registry=https://registry.npmmirror.com
```

**配置 API 密钥：**

在 `backend/` 目录下创建 `.env` 文件：

```env
DEEPSEEK_API_KEY=your-api-key-here
```

### 3. 启动服务

```bash
./start.sh
```

服务启动后：
- 后端: http://localhost:8002
- 前端: http://localhost:3000

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
| LLM | DeepSeek |
| Embedding | BGE-base-zh-v1.5 |

## 注意事项

- **模型文件**：本地 Embedding 模型 (~400MB) 在 .gitignore 中排除，首次使用需自行下载到 `backend/models/`
- **会话数据**：`backend/sessions/` 包含用户会话，已排除以保护隐私
- **API 密钥**：必须配置 `.env` 文件中的 DEEPSEEK_API_KEY 才能使用 LLM

## 开发相关

### 测试

```bash
pytest
```

### 代码规范

- 后端遵循 AGENTS.md 中的 Python 代码风格
- 前端运行 `npm run lint` 检查

## License

MIT