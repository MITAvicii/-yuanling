# 源灵AI 产品规格文档

## 一、产品定位

**一句话定位**：本地优先、透明可控的 AI Agent 系统，让用户拥有"真实记忆"的数字副手。

**解决什么问题**：
- 现有 AI Agent 系统多为"黑盒"，用户无法理解 Agent 的决策过程
- 向量数据库不透明，用户难以直接查看和编辑记忆
- 技能扩展需要编写代码，门槛高

**核心差异化**：
- 文件即记忆：Markdown/JSON 取代向量数据库
- 技能即插件：通过文件夹结构管理能力，Agent 自主阅读执行
- 透明可控：所有 System Prompt、工具调用、记忆读写完全透明

## 二、目标用户

**主要用户**：
- AI 爱好者、开发者
- 需要个人 AI 助手的用户
- 对数据隐私有要求的用户

**使用场景**：
1. 日常任务自动化（天气查询、信息检索）
2. 知识库问答（RAG 检索本地文档）
3. 代码辅助（执行 Python 脚本、Shell 命令）
4. 个人记忆管理（长期记忆、对话历史）

## 三、核心功能

### 后端功能

| 功能 | 描述 | 优先级 |
|------|------|--------|
| Agent 对话 | SSE 流式对话，支持工具调用 | P0 |
| 会话管理 | 创建、删除、重命名、压缩会话 | P0 |
| 文件记忆 | Markdown/JSON 格式的记忆存储 | P0 |
| 技能系统 | SKILL.md 指令遵循范式 | P0 |
| 五大核心工具 | terminal/python_repl/fetch_url/read_file/rag_search | P0 |
| System Prompt 组装 | 6 段动态拼接 + 截断策略 | P0 |
| RAG 检索 | LlamaIndex Hybrid Search | P1 |
| 配置管理 | config.json 持久化 | P1 |

### 前端功能

| 功能 | 描述 | 优先级 |
|------|------|--------|
| 三栏 IDE 布局 | Sidebar + Stage + Inspector | P0 |
| 对话流 | 消息展示 + 思考链可视化 | P0 |
| Monaco Editor | 实时编辑 Memory/Skill 文件 | P0 |
| 会话列表 | 创建、切换、删除会话 | P0 |
| Token 统计 | 实时显示 token 消耗 | P1 |
| RAG 模式开关 | 启用/禁用知识库检索 | P1 |

## 四、用户流程

### 核心流程

```
打开应用 → 选择/创建会话 → 发送消息
    ↓
Agent 读取 System Prompt（含技能列表、记忆）
    ↓
Agent 决策：直接回答 OR 调用工具
    ↓
工具执行结果返回 → Agent 生成回复
    ↓
用户查看回复 + 思考链
    ↓
可选：编辑 Memory/Skill 文件
```

### 技能调用流程

```
用户请求 → Agent 识别匹配技能
    ↓
调用 read_file 读取 SKILL.md
    ↓
理解操作步骤 → 调用 Core Tools 执行
    ↓
返回结果
```

## 五、AI 能力需求

| 能力类型 | 用途 | 默认模型 | 备注 |
|---------|------|---------|------|
| 对话生成 | Agent 主对话 | deepseek-chat | OpenAI API 格式兼容 |
| Embedding | RAG 向量检索 | qwen3-vl-embedding | 阿里云 |
| 标题生成 | 会话标题自动生成 | deepseek-chat | - |
| 对话压缩 | 长对话摘要 | deepseek-chat | - |

### 多 API 提供商支持

系统支持自定义接入多个 API 提供商：

| 提供商 | Base URL | 模型示例 |
|--------|----------|---------|
| DeepSeek | https://api.deepseek.com | deepseek-chat |
| 阿里云 | https://dashscope.aliyuncs.com/compatible-mode/v1 | qwen-turbo, qwen3-vl-embedding |
| NVIDIA | https://integrate.api.nvidia.com/v1 | meta/llama-3.1-8b-instruct |
| OpenRouter | https://openrouter.ai/api/v1 | 多模型代理 |

**配置方式**：通过 config.json 或前端界面配置 API Key 和 Base URL

## 六、UI 布局

### 三栏布局

```
┌─────────────────────────────────────────────────────────────┐
│  mini OpenClaw                              赋范空间         │
├──────────┬──────────────────────────────┬──────────────────┤
│ Sidebar  │           Stage              │    Inspector     │
│          │                              │                  │
│ [Chat]   │  User: 查询北京天气          │  ┌────────────┐  │
│ [Memory] │  ┌─ 思考 ─────────────┐      │  │ MEMORY.md  │  │
│ [Skills] │  │ 发现 get_weather   │      │  │            │  │
│          │  │ 技能匹配...        │      │  │ # 长期记忆 │  │
│ 会话列表 │  └────────────────────┘      │  │            │  │
│ ├ 会话1  │  Assistant: 北京今天...      │  │ 用户偏好...│  │
│ ├ 会话2  │                              │  │            │  │
│ └ +新建  │  [输入框]                    │  └────────────┘  │
│          │                              │  [Monaco Editor] │
├──────────┴──────────────────────────────┴──────────────────┤
│ Token: 1,234  │  RAG: ON/OFF                              │
└─────────────────────────────────────────────────────────────┘
```

### 视觉风格

- **色调**：浅色 Apple 风格（Frosty Glass）
- **背景**：纯白/极浅灰 (#fafafa)
- **强调色**：克莱因蓝或活力橙
- **导航栏**：顶部固定，半透明毛玻璃效果

## 七、技术栈

### 后端

| 技术 | 版本 | 说明 |
|------|------|------|
| Python | 3.10+ | 强制 Type Hinting |
| FastAPI | Latest | RESTful + SSE |
| LangChain | 1.x | create_agent API |
| LlamaIndex | Latest | Hybrid Search |
| DeepSeek | - | 主模型 |

### 前端

| 技术 | 版本 | 说明 |
|------|------|------|
| Next.js | 14+ | App Router |
| TypeScript | 5.x | - |
| Tailwind CSS | 3.x | - |
| Shadcn/UI | Latest | - |
| Monaco Editor | Latest | Light Theme |

## 八、数据模型

### 会话文件结构

```json
{
  "id": "session_001",
  "title": "天气查询",
  "created_at": "2024-01-01T00:00:00Z",
  "messages": [
    {"role": "user", "content": "查询北京天气"},
    {"role": "assistant", "content": "...", "tool_calls": [...]}
  ]
}
```

### System Prompt 组件

| 文件 | 用途 | 最大长度 |
|------|------|---------|
| SKILLS_SNAPSHOT.md | 技能列表 | - |
| SOUL.md | 核心设定 | 20k 字符 |
| IDENTITY.md | 自我认知 | 20k 字符 |
| USER.md | 用户画像 | 20k 字符 |
| AGENTS.md | 行为准则 | 20k 字符 |
| MEMORY.md | 长期记忆 | 20k 字符 |

## 九、API 接口

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/chat` | POST | SSE 流式对话 |
| `/api/sessions` | GET/POST | 会话列表/创建 |
| `/api/sessions/{id}` | PUT/DELETE | 更新/删除会话 |
| `/api/files` | GET/POST | 文件读写 |
| `/api/skills` | GET | 技能列表 |
| `/api/tokens/session/{id}` | GET | Token 统计 |
| `/api/config/rag-mode` | GET/PUT | RAG 模式开关 |

## 十、安全要求

- **沙箱隔离**：terminal 和 read_file 工具限制操作范围
- **路径白名单**：禁止访问项目目录外的文件
- **高危指令拦截**：黑名单拦截 rm -rf / 等
- **敏感信息**：API Key 通过环境变量管理

## 十一、质量门槛

- [ ] 主路径可用（对话、工具调用、技能执行）
- [ ] 异常路径清晰（错误提示、重试机制）
- [ ] Loading 状态（流式输出的实时反馈）
- [ ] 空状态处理（无会话、无技能时的提示）
- [ ] 基础输入校验（必填项、格式验证）
- [ ] 敏感信息不写入代码
- [ ] 有对应的测试用例

## 十二、多平台唤醒架构（后续迭代）

为支持飞书、微信等平台唤醒源灵 AI，采用消息适配层架构：

```
┌─────────────────────────────────────────────────────────┐
│                    消息来源层                            │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │
│  │  Web    │ │  飞书   │ │  微信   │ │  API   │        │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘       │
└───────┼──────────┼──────────┼──────────┼───────────────┘
        │          │          │          │
        ▼          ▼          ▼          ▼
┌─────────────────────────────────────────────────────────┐
│                  消息适配层 (Adapters)                   │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 统一消息格式: {source, user_id, content, ...}    │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                    核心引擎层                            │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Agent (LangGraph) + Memory + Skills + Tools    │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

**实现路径**：
1. Phase 1-4：完成 Web 端核心功能
2. Phase 5：添加消息适配层抽象
3. Phase 6：实现飞书 Bot 集成
4. Phase 7：实现微信 Bot 集成

## 十三、里程碑

### Phase 1: 后端核心 (Week 1)

- [ ] 项目结构初始化
- [ ] FastAPI 应用入口
- [ ] 配置管理（多 API 支持）
- [ ] 五大核心工具
- [ ] LangGraph Agent 定义
- [ ] 会话存储

### Phase 2: 前端基础 (Week 2)

- [ ] Next.js 项目初始化
- [ ] 三栏布局
- [ ] 对话流组件
- [ ] API 集成

### Phase 3: 技能系统 (Week 3)

- [ ] Skills 加载机制
- [ ] System Prompt 组装
- [ ] 技能文件编辑器

### Phase 4: RAG & 优化 (Week 4)

- [ ] LlamaIndex 集成
- [ ] Hybrid Search
- [ ] 预制知识库文档
- [ ] 对话压缩
- [ ] Token 统计

### Phase 5+: 多平台扩展 (后续)

- [ ] 消息适配层抽象
- [ ] 飞书 Bot 集成
- [ ] 微信 Bot 集成
