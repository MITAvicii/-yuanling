# AGENTS.md - 源灵AI (Mini-OpenClaw)

Local-first, transparent AI Agent system. File-based memory (Markdown/JSON), skills as plugins (`skills/{name}/SKILL.md`), all prompts/tools/memory fully observable.

## Build & Run Commands

### Backend (Python — conda env `yuanling`)

```bash
conda activate yuanling

# Install deps (Tsinghua mirror)
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# Dev server (port 8002) — run from project root
uvicorn backend.app:app --host 0.0.0.0 --port 8002 --reload

# Tests (pytest with pytest-asyncio)
pytest                                          # all tests
pytest tests/test_file.py                       # single file
pytest tests/test_file.py::test_func -v         # single test function
pytest tests/test_file.py -k "keyword" -v       # by keyword match

# Run with coverage
pytest --cov=backend --cov-reporthtml=coverage
```

### Frontend (Next.js 14 — in `frontend/`)

```bash
cd frontend
npm install --registry=https://registry.npmmirror.com

npm run dev       # dev server (proxies /api/* → localhost:8002)
npm run build     # production build
npm run lint      # ESLint (next lint)
npm run lint -- --fix
```

### Quick Start

```bash
./start.sh   # launches both backend + frontend
./stop.sh    # stops both
```

## Project Structure

```
backend/
├── app.py              # FastAPI entry, CORS, lifespan, global error handler
├── config.py           # Pydantic Settings + ConfigManager singleton
├── api/                # Route modules (chat, sessions, files, config_api, knowledge, platform, tokens)
├── graph/              # LangGraph agent, session mgmt, memory extraction/indexing
│   ├── agent.py        # ReAct agent (StateGraph), build_system_prompt(), get_llm()
│   └── session.py      # Session CRUD (JSON files in sessions/)
├── tools/              # LangChain @tool functions (terminal, python_repl, fetch_url, file_reader, file_writer, rag_search, feishu_sender)
├── platforms/          # Platform integrations (Feishu long-connection)
├── workspace/          # System Prompt components (SOUL.md, IDENTITY.md, USER.md, AGENTS.md, SKILLS_SNAPSHOT.md)
├── memory/             # MEMORY.md long-term memory
├── skills/             # {skill_name}/SKILL.md — markdown instructions, not code
└── models/             # Local embedding models (bge-base-zh-v1.5, bge-reranker-base)

frontend/src/
├── app/                # Next.js App Router (layout.tsx, page.tsx, globals.css)
├── components/         # chat/, sidebar/, editor/, layout/
└── lib/api.ts          # Typed fetch wrapper + all API functions
```

## Code Style — Python

**Imports** (3 groups, blank-line separated):
```python
# 1. stdlib
import os
from pathlib import Path
from typing import Optional, List, Dict, Any

# 2. third-party
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage

# 3. local (always `backend.` prefix — never relative imports)
from backend.config import get_config, BACKEND_DIR
from backend.tools import get_all_tools
```

**Type hints** — mandatory on all functions:
```python
def get_session_history(session_id: str) -> list[BaseMessage]: ...
def run_agent(session_id: str, user_message: str, messages: list[BaseMessage] | None = None) -> list[BaseMessage]: ...
```

**Naming**: `snake_case` functions/vars, `PascalCase` classes, `UPPER_SNAKE_CASE` constants, `_private` prefix for internals.

**Pydantic models** for all request/response schemas:
```python
class ChatRequest(BaseModel):
    """对话请求"""
    message: str
    session_id: Optional[str] = None
    stream: bool = True
```

**Docstrings** — Chinese, on all public functions. Module-level docstrings on every file.

**Async** — FastAPI routes and streaming generators must be `async`. Use `astream_events` for LangGraph streaming. Avoid blocking calls in async functions.

**Error handling** — Global exception handler returns `{"error": str, "message": "..."}`. Tools have 60s timeout. Terminal tool uses command blacklist. Never suppress errors with `as any` or `@ts-ignore`.

## Code Style — TypeScript/React

**Imports** (3 groups):
```typescript
// 1. React / Next.js
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

// 2. Third-party
import { Send, Loader2 } from 'lucide-react';

// 3. Local (use @/ alias → src/)
import { sendMessage, getSession } from '@/lib/api';
```

**Components** — function components with explicit interface props:
```typescript
interface ChatAreaProps {
  session: Session | null;
  onSessionUpdate: (session: Session | null) => void;
}
export function ChatArea({ session, onSessionUpdate }: ChatAreaProps) { ... }
```

**TypeScript config**: `strict: true`, module `esnext`, `@/*` path alias.

**Naming**: `PascalCase` components + files, `camelCase` functions/vars/utility files.

**Styling**: Tailwind CSS utility classes inline. Shadcn/UI components. `clsx` + `tailwind-merge` for conditional classes.

**Error handling**: try/catch around all API calls, `console.error` for logging, always manage loading state in `finally`.

## Skills System

Skills are markdown-based plugins in `backend/skills/{skill_name}/SKILL.md`. Agents load skills via SKILLS_SNAPSHOT.md at runtime.

- **Skill discovery**: Check `backend/skills/` for available skills
- **Skill format**: Each skill has a `SKILL.md` with instructions
- **Using skills**: Read the SKILL.md file, follow its guidelines

## Environment Variables

Backend uses `.env` file (not committed). Key variables:
- `DEEPSEEK_API_KEY` — LLM provider
- `DASHSCOPE_API_KEY` — For embedding models
- `OPENAI_API_KEY` / `OPENAI_BASE_URL` — Optional alternative

See `.env.example` for full list.

## Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| `create_agent()` not `AgentExecutor` | LangChain 1.x modern API with native streaming |
| Rebuild agent per request | System Prompt reflects real-time workspace file edits |
| File-driven, no database | Low deployment barrier, all state inspectable |
| Skills = Markdown instructions | Agent reads SKILL.md via `read_file`, executes with core tools |
| Path whitelist + traversal detection | Dual sandbox for terminal and file_reader tools |

## Critical Rules

1. **API keys** — `.env` only, never hardcode. Backend reads via `pydantic-settings`.
2. **Sandbox security** — terminal and file_reader enforce path restrictions.
3. **SSE protocol** — Chat uses Server-Sent Events: `session → retrieval? → token* → (tool_start → tool_end → new_response → token*)* → done`.
4. **Chinese first** — all docstrings, comments, and user-facing strings in Chinese.
5. **Dependencies** — backend uses Tsinghua PyPI mirror, frontend uses npmmirror.
6. **System Prompt assembly order**: SKILLS_SNAPSHOT → SOUL → IDENTITY → USER → AGENTS → MEMORY (truncate at 20k chars per file).
