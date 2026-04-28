"""
LangGraph Agent 定义

包含循环检测和防止无限递归的机制。
"""

import json
import time
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, Optional, Sequence, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from backend.config import BACKEND_DIR, get_config
from backend.tools import get_all_tools


def _get_agent_config():
    """获取 Agent 配置（从 ConfigManager 获取）"""
    return get_config().config.agent


# ============= LLM 缓存 =============
_llm_cache: Optional[Any] = None
_llm_cache_key: str = ""
_llm_cache_time: float = 0
LLM_CACHE_TTL: int = 300  # LLM 缓存有效期（秒）


def get_llm(force_new: bool = False):
    """获取 LLM 实例（带缓存）"""
    global _llm_cache, _llm_cache_key, _llm_cache_time
    
    config = get_config()
    llm_config = config.get_llm_config()
    
    # 生成缓存 key
    cache_key = f"{llm_config['model']}_{llm_config['temperature']}_{llm_config['api_key'][:8] if llm_config.get('api_key') else 'none'}"
    
    # 检查缓存是否有效
    if (not force_new and 
        _llm_cache is not None and 
        cache_key == _llm_cache_key and 
        time.time() - _llm_cache_time < LLM_CACHE_TTL):
        return _llm_cache
    
    # 临时清除代理环境变量
    import os
    original = {
        'HTTP_PROXY': os.environ.get('HTTP_PROXY'),
        'HTTPS_PROXY': os.environ.get('HTTPS_PROXY'),
        'ALL_PROXY': os.environ.get('ALL_PROXY'),
        'http_proxy': os.environ.get('http_proxy'),
        'https_proxy': os.environ.get('https_proxy'),
        'all_proxy': os.environ.get('all_proxy'),
    }
    for key in original:
        os.environ.pop(key, None)
    
    try:
        agent_config = _get_agent_config()
        _llm_cache = ChatOpenAI(
            model=llm_config["model"],
            temperature=llm_config["temperature"],
            max_tokens=llm_config["max_tokens"],
            api_key=llm_config["api_key"],
            base_url=llm_config["base_url"],
            request_timeout=agent_config.request_timeout,
        )
        _llm_cache_key = cache_key
        _llm_cache_time = time.time()
        return _llm_cache
    finally:
        # 恢复代理环境变量
        for key, val in original.items():
            if val:
                os.environ[key] = val


# ============= System Prompt 缓存 =============
_system_prompt_cache: Optional[str] = None
_system_prompt_hash: str = ""


def _get_workspace_hash() -> str:
    """获取 workspace 文件的哈希值，用于检测变更"""
    workspace_dir = BACKEND_DIR / "workspace"
    memory_dir = BACKEND_DIR / "memory"
    
    files_to_check = [
        workspace_dir / "SKILLS_SNAPSHOT.md",
        workspace_dir / "SOUL.md",
        workspace_dir / "IDENTITY.md",
        workspace_dir / "USER.md",
        workspace_dir / "AGENTS.md",
        memory_dir / "MEMORY.md",
    ]
    
    hash_data = []
    for f in files_to_check:
        if f.exists():
            mtime = f.stat().st_mtime
            hash_data.append(f"{f.name}:{mtime}")
    
    return hashlib.md5("|".join(hash_data).encode()).hexdigest()


class AgentState(TypedDict):
    """Agent 状态"""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    session_id: str
    system_prompt: str
    iteration_count: int


def build_system_prompt(force_rebuild: bool = False) -> str:
    """
    构建 System Prompt（带缓存）
    
    按顺序拼接以下组件：
    1. SKILLS_SNAPSHOT.md (技能列表)
    2. SOUL.md (核心设定)
    3. IDENTITY.md (自我认知)
    4. USER.md (用户画像)
    5. AGENTS.md (行为准则)
    6. MEMORY.md (长期记忆)
    """
    global _system_prompt_cache, _system_prompt_hash
    
    # 检查是否需要重新构建
    current_hash = _get_workspace_hash()
    if (not force_rebuild and 
        _system_prompt_cache is not None and 
        current_hash == _system_prompt_hash):
        return _system_prompt_cache
    
    workspace_dir = BACKEND_DIR / "workspace"
    memory_dir = BACKEND_DIR / "memory"
    
    components = [
        ("SKILLS_SNAPSHOT.md", workspace_dir),
        ("SOUL.md", workspace_dir),
        ("IDENTITY.md", workspace_dir),
        ("USER.md", workspace_dir),
        ("AGENTS.md", workspace_dir),
        ("MEMORY.md", memory_dir),
    ]
    
    config = get_config().config
    max_size = config.memory.max_file_size
    truncation_marker = config.memory.truncation_marker
    
    prompt_parts = []
    
    for filename, directory in components:
        file_path = directory / filename
        
        if file_path.exists():
            try:
                content = file_path.read_text(encoding='utf-8')
                
                # 截断过长内容
                if len(content) > max_size:
                    content = content[:max_size] + f"\n\n{truncation_marker}"
                
                prompt_parts.append(f"# {filename.replace('.md', '')}\n\n{content}")
            except Exception as e:
                print(f"读取 {filename} 时发生错误: {str(e)}")
    
    _system_prompt_cache = "\n\n---\n\n".join(prompt_parts)
    _system_prompt_hash = current_hash
    
    return _system_prompt_cache


def _prepare_agent_state(session_id: str, user_message: str, messages: list = None) -> dict:
    """准备 Agent 状态（公共方法）"""
    system_prompt = build_system_prompt()
    
    if messages is None:
        msg_list = []
    else:
        msg_list = list(messages)
    
    msg_list = msg_list + [HumanMessage(content=user_message)]
    
    return {
        "messages": msg_list,
        "session_id": session_id,
        "system_prompt": system_prompt,
        "iteration_count": 0,
    }


def create_agent_graph():
    """
    创建 Agent 图
    
    使用 LangGraph 构建一个简单的 ReAct 风格 Agent
    包含循环检测，防止无限工具调用
    """
    llm = get_llm()
    tools = get_all_tools()
    
    llm_with_tools = llm.bind_tools(tools)
    agent_config = _get_agent_config()
    
    async def agent_node(state: AgentState) -> dict:
        """Agent 节点：生成响应或工具调用"""
        messages = state["messages"]
        system_prompt = state.get("system_prompt", build_system_prompt())
        iteration_count = state.get("iteration_count", 0)
        
        full_messages = [SystemMessage(content=system_prompt)] + list(messages)
        
        response = await llm_with_tools.ainvoke(full_messages)
        
        return {
            "messages": [response],
            "iteration_count": iteration_count + 1,
        }
    
    def should_continue(state: AgentState) -> str:
        """判断是否继续调用工具，包含循环检测"""
        messages = state["messages"]
        iteration_count = state.get("iteration_count", 0)
        last_message = messages[-1]
        
        if iteration_count >= agent_config.max_iterations:
            return END
        
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return END
    
    tool_node = ToolNode(tools)
    
    workflow = StateGraph(AgentState)
    
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)
    
    workflow.set_entry_point("agent")
    
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            END: END
        }
    )
    workflow.add_edge("tools", "agent")
    
    return workflow.compile()


async def run_agent_async(session_id: str, user_message: str, messages: list = None):
    """
    运行 Agent（异步版本）
    """
    graph = create_agent_graph()
    agent_config = _get_agent_config()
    
    state = _prepare_agent_state(session_id, user_message, messages)
    config = {"recursion_limit": agent_config.recursion_limit}
    
    result = await graph.ainvoke(state, config=config)
    
    return result["messages"]


def run_agent(session_id: str, user_message: str, messages: list = None):
    """
    运行 Agent（同步包装器）
    
    注意：在异步上下文中请使用 run_agent_async
    """
    import asyncio
    
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    
    if loop is not None:
        import nest_asyncio
        nest_asyncio.apply()
        return loop.run_until_complete(run_agent_async(session_id, user_message, messages))
    else:
        return asyncio.run(run_agent_async(session_id, user_message, messages))


async def run_agent_astream(session_id: str, user_message: str, messages: list = None):
    """
    流式运行 Agent（token 级别流式输出）
    
    Args:
        session_id: 会话 ID
        user_message: 用户消息
        messages: 历史消息列表
        
    Yields:
        (event_type, data) 元组
        - ("token", str): 文本片段
        - ("tool_call", dict): 工具调用
        - ("message", BaseMessage): 完整消息
    """
    graph = create_agent_graph()
    agent_config = _get_agent_config()
    
    state = _prepare_agent_state(session_id, user_message, messages)
    config = {"recursion_limit": agent_config.recursion_limit}
    tool_result_max_length = agent_config.tool_result_max_length
    
    all_messages = []
    
    async for event in graph.astream_events(state, version="v2", config=config):
        kind = event["event"]
        
        if kind == "on_chat_model_stream":
            content = event["data"]["chunk"].content
            if content:
                yield ("token", content)
        
        elif kind == "on_tool_start":
            tool_name = event["name"]
            tool_input = event["data"].get("input", {})
            yield ("tool_call", {"name": tool_name, "args": tool_input})
        
        elif kind == "on_tool_end":
            tool_output = event["data"].get("output", "")
            yield ("tool_result", str(tool_output)[:tool_result_max_length])
        
        elif kind == "on_chain_end":
            if "messages" in event["data"].get("output", {}):
                output_messages = event["data"]["output"]["messages"]
                for msg in output_messages:
                    if msg not in all_messages:
                        all_messages.append(msg)
                        yield ("message", msg)


async def run_agent_stream(session_id: str, user_message: str, messages: list = None):
    """
    流式运行 Agent（简单版本）
    
    Args:
        session_id: 会话 ID
        user_message: 用户消息
        messages: 历史消息列表
        
    Yields:
        流式输出的消息片段
    """
    # 获取 LLM 和工具
    llm = get_llm()
    tools = get_all_tools()
    llm_with_tools = llm.bind_tools(tools)
    
    # 构建 System Prompt
    system_prompt = build_system_prompt()
    
    # 准备消息
    if messages is None:
        messages = []
    
    full_messages = [SystemMessage(content=system_prompt)] + list(messages) + [HumanMessage(content=user_message)]
    
    # 流式调用 LLM
    async for chunk in llm_with_tools.astream(full_messages):
        yield chunk


async def process_message(
    message: str,
    session_id: str = "default",
    context: str = "",
    messages: list = None
) -> dict:
    """
    处理消息（用于平台集成）
    
    Args:
        message: 用户消息
        session_id: 会话 ID
        context: 上下文信息（如来源平台）
        messages: 历史消息列表
        
    Returns:
        处理结果字典
    """
    # 获取 LLM
    llm = get_llm()
    
    # 构建 System Prompt
    system_prompt = build_system_prompt()
    
    # 添加上下文
    if context:
        message = f"{context}\n\n用户消息：{message}"
    
    # 准备消息
    if messages is None:
        messages = []
    
    full_messages = [SystemMessage(content=system_prompt)] + list(messages) + [HumanMessage(content=message)]
    
    # 调用 LLM
    response = await llm.ainvoke(full_messages)
    
    return {
        "content": response.content,
        "session_id": session_id,
    }


class EnhancedToolNode:
    """
    增强的工具节点，带有循环检测和错误处理功能
    """
    
    def __init__(self, tools: list):
        from langchain_core.tools import BaseTool
        self.tools = {tool.name: tool for tool in tools}
        # 用于跟踪最近的工具调用，以检测循环
        self.call_history = {}
        
    def __call__(self, state: dict) -> dict:
        """
        执行工具调用，带错误处理和循环检测
        """
        messages = state.get("messages", [])
        
        # 获取待处理的工具调用
        tool_calls = []
        if messages:
            last_message = messages[-1]
            if hasattr(last_message, 'tool_calls'):
                tool_calls = last_message.tool_calls
        
        results = []
        
        for tool_call in tool_calls:
            tool_name = tool_call.get('name', '')
            tool_args = tool_call.get('args', {})
            
            # 检测循环：如果连续多次调用相同的错误工具
            call_signature = f"{tool_name}:{str(tool_args)}"
            if call_signature not in self.call_history:
                self.call_history[call_signature] = 0
            self.call_history[call_signature] += 1
            
            # 如果同一错误调用超过3次，提供帮助信息
            if self.call_history[call_signature] >= 3:
                error_msg = f"检测到循环错误：工具 '{tool_name}' 已连续失败3次。"
                if tool_name == "terminal" and ('command' not in tool_args or not tool_args.get('command')):
                    error_msg += f" 提示：terminal工具需要提供'command'参数，例如: {{'command': 'ls'}}"
                
                result = ToolMessage(
                    content=error_msg,
                    tool_call_id=tool_call.get('id', ''),
                )
                results.append(result)
                continue
            
            # 执行工具调用
            try:
                if tool_name in self.tools:
                    tool = self.tools[tool_name]
                    # 检查必需参数
                    if tool_name == "terminal" and ('command' not in tool_args or not tool_args.get('command')):
                        error_content = "Error: terminal工具需要提供'command'参数。正确用法: terminal(command='你的命令')"
                        result = ToolMessage(
                            content=error_content,
                            tool_call_id=tool_call.get('id', ''),
                        )
                    else:
                        # 执行工具
                        observation = tool.invoke(tool_args)
                        result = ToolMessage(
                            content=str(observation),
                            tool_call_id=tool_call.get('id', ''),
                        )
                else:
                    result = ToolMessage(
                        content=f"错误：找不到工具 '{tool_name}'",
                        tool_call_id=tool_call.get('id', ''),
                    )
            except Exception as e:
                # 捕获工具执行错误
                error_content = f"执行工具 '{tool_name}' 时出错: {str(e)}"
                
                # 为常见错误提供额外帮助
                if tool_name == "terminal":
                    error_content += " 提示：terminal工具需要提供'command'参数，例如: terminal(command='ls -la')"
                
                result = ToolMessage(
                    content=error_content,
                    tool_call_id=tool_call.get('id', ''),
                )
            
            results.append(result)
        
        return {"messages": results}


# 导出
__all__ = [
    "AgentState",
    "create_agent_graph",
    "run_agent",
    "run_agent_async",
    "run_agent_stream",
    "run_agent_astream",
    "build_system_prompt",
    "get_llm",
    "process_message",
    "EnhancedToolNode",
]
