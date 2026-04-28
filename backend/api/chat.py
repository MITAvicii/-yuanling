"""
Chat API - SSE 流式对话

SSE 事件类型：
- session: 会话 ID
- retrieval: RAG 检索结果
- token: LLM 输出的 token
- tool_start: 工具调用开始
- tool_end: 工具调用结束
- new_response: 工具执行完毕，Agent 开始新一轮文本生成
- done: 整轮响应结束
- title: 自动生成的标题
- error: 错误信息
"""

import json
import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from backend.graph import (
    run_agent,
    run_agent_astream,
    get_optimized_history,
    auto_compress_if_needed,
    save_session_messages,
    create_session,
    load_session,
    build_system_prompt,
    is_first_message,
    update_session_title,
    get_rag_context,
)
from backend.graph.skills import save_skills_snapshot
from backend.config import get_config
from backend.tools.rag_search import retrieve_knowledge, get_knowledge_context, get_knowledge_dir
from backend.graph.memory_indexer import retrieve as retrieve_memory



router = APIRouter(prefix="/api", tags=["chat"])


# ============= 数据模型 =============

class ChatRequest(BaseModel):
    """对话请求"""
    message: str
    session_id: Optional[str] = None
    stream: bool = True
    rag_enabled: Optional[bool] = None  # 是否启用 RAG（null 时使用全局配置）


class ChatResponse(BaseModel):
    """对话响应"""
    session_id: str
    response: str
    tool_calls: list = []


# ============= 辅助函数 =============

def format_sse(data: dict) -> str:
    """格式化 SSE 数据"""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _perform_rag_retrieval(message: str, config) -> Optional[dict]:
    """
    执行 RAG 检索（记忆 + 知识库）
    
    Args:
        message: 用户消息
        config: 应用配置
        
    Returns:
        RAG 结果字典，包含检索到的上下文和信息
    """
    try:
        threshold = config.rag.rerank_threshold
        
        # 1. 检索记忆
        memory_results = retrieve_memory(message, top_k=3)
        
        # 2. 检索知识库
        knowledge_results = retrieve_knowledge(message, top_k=3)
        
        # 3. 合并结果
        all_results = []
        if memory_results:
            for r in memory_results:
                all_results.append({**r, "source_type": "memory"})
        if knowledge_results:
            for r in knowledge_results:
                all_results.append({**r, "source_type": "knowledge"})
        
        # 4. 判断是否超过阈值
        if all_results:
            max_rerank = max((r.get("rerank_score", r.get("score", 0)) for r in all_results), default=0)
            above_threshold = threshold <= 0 or max_rerank >= threshold
        else:
            above_threshold = False
        
        # 5. 构建上下文
        context_parts = []
        
        if above_threshold:
            if memory_results:
                mc = get_rag_context(message, top_k=3)
                if mc:
                    context_parts.append(mc)
            
            if knowledge_results:
                kc = get_knowledge_context(message, top_k=3)
                if kc:
                    context_parts.append(kc)
        
        context_text = "\n\n".join(context_parts)
        
        return {
            "query": message,
            "context": context_text,
            "results": all_results,
            "above_threshold": above_threshold,
            "memory_results": memory_results,
            "knowledge_results": knowledge_results,
        }
        
    except Exception as e:
        print(f"RAG 检索失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


async def generate_title(session_id: str, first_message: str) -> str:
    """
    为新会话生成标题
    
    使用 LLM 生成 ≤10 字的中文标题
    """
    try:
        from backend.graph.agent import get_llm
        
        llm = get_llm()
        
        prompt = f"""请为以下对话生成一个简短的标题（不超过10个中文字符）。
只返回标题，不要其他内容。

用户消息：{first_message}

标题："""
        
        response = await llm.ainvoke(prompt)
        title = response.content.strip()[:20]
        
        update_session_title(session_id, title)
        
        return title
        
    except Exception as e:
        print(f"生成标题失败: {str(e)}")
        return "新对话"


async def _async_compress_session(session_id: str, summary_prompt: str, message_count: int):
    """
    异步压缩会话历史
    
    1. 调用 LLM 生成摘要
    2. 调用 compress_history 保存摘要
    
    Args:
        session_id: 会话 ID
        summary_prompt: 摘要提示词
        message_count: 当前消息数量
    """
    try:
        from backend.graph.agent import get_llm
        from backend.graph.session import compress_history
        
        llm = get_llm()
        
        # 调用 LLM 生成摘要
        response = await llm.ainvoke(summary_prompt)
        summary = response.content.strip()
        
        # 保留最近的消息数量（留一些给滑动窗口）
        from backend.config import get_config
        config = get_config()
        max_messages = config.config.agent.max_history_messages
        compress_count = message_count - max_messages
        
        if compress_count > 0:
            # 执行压缩
            result = compress_history(session_id, summary, compress_count)
            print(f"会话 {session_id} 已压缩：归档 {result['archived_count']} 条消息，保留 {result['remaining_count']} 条")
        else:
            print(f"会话 {session_id} 消息不足压缩")
            
    except Exception as e:
        print(f"自动压缩失败: {str(e)}")
        import traceback
        traceback.print_exc()


# ============= API 路由 =============

@router.post("/chat")
async def chat(request: ChatRequest):
    """
    对话接口
    
    始终使用流式输出（SSE）
    
    SSE 事件序列：
    [RAG模式] retrieval → token... → tool_start → tool_end → new_response → token... → done
    [普通模式]             token... → tool_start → tool_end → new_response → token... → done
    """
    # 确保 Skills Snapshot 已生成
    save_skills_snapshot()
    
    # 获取或创建会话
    session_id = request.session_id
    is_new_session = False
    
    if not session_id:
        session = create_session()
        session_id = session.session_id
        is_new_session = True
    
    # 检查是否是第一条消息
    is_first = is_first_message(session_id)
    
    # 获取配置
    app_config = get_config().config
    agent_config = app_config.agent
    
    # 获取优化后的历史消息（滑动窗口 + 摘要）
    history, summary_text = get_optimized_history(
        session_id, 
        max_messages=agent_config.max_history_messages
    )
    
    # 检查是否需要压缩（异步触发，不阻塞当前请求）
    compress_info = auto_compress_if_needed(session_id)
    if compress_info:
        # 异步执行压缩，不阻塞当前请求
        import asyncio
        asyncio.create_task(_async_compress_session(
            session_id, 
            compress_info["summary_prompt"],
            compress_info["message_count"]
        ))
    
    # RAG 模式检索
    use_rag = request.rag_enabled if request.rag_enabled is not None else app_config.rag.enabled
    
    rag_results = None
    if use_rag and request.message:
        rag_results = _perform_rag_retrieval(request.message, app_config)
    
    # 始终使用流式输出
    return StreamingResponse(
        stream_chat(
            session_id=session_id,
            user_message=request.message,
            history=history,
            rag_results=rag_results,
            is_first_msg=is_first,
            first_message_text=request.message if is_first else None,
            use_rag=use_rag,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Session-Id": session_id,
        }
    )


async def stream_chat(
    session_id: str,
    user_message: str,
    history: list,
    rag_results: Optional[dict] = None,
    is_first_msg: bool = False,
    first_message_text: Optional[str] = None,
    use_rag: bool = False,
):
    """
    流式对话生成器（token 级别流式输出）
    
    按段（segment）追踪响应：
    - 每次工具执行后 Agent 重新生成文本时开启新段
    - 前端据此创建新的助手消息气泡
    
    Yields:
        SSE 格式的数据
    """
    try:
        # 1. 发送会话 ID
        yield format_sse({"type": "session", "session_id": session_id})
        
        # 2. 只有当检索结果超过阈值（LLM可能使用）时才发送 retrieval 事件
        if use_rag and rag_results and rag_results.get("above_threshold", False):
            yield format_sse({
                "type": "retrieval",
                "query": rag_results["query"] if rag_results else user_message,
                "context": (rag_results["context"][:500] if rag_results and rag_results.get("context") else "") if rag_results else "",
                "results": [
                    {
                        "text": r["text"][:300] if r.get("text") else "",
                        "score": round(r.get("score", 0), 4),
                        "rerank_score": round(r.get("rerank_score", 0), 4) if r.get("rerank_score") else None,
                        "source": r.get("source", "未知"),
                        "source_type": r.get("source_type", "memory"),
                    }
                    for r in (rag_results.get("results", [])[:5] if rag_results else [])
                ],
                "above_threshold": rag_results.get("above_threshold", False) if rag_results else False,
            })
        
        # 3. 准备消息（包含 RAG 上下文）
        messages_to_save = [HumanMessage(content=user_message)]
        
        # 如果有 RAG 结果，追加到历史
        effective_history = list(history)
        if rag_results:
            effective_history.append(HumanMessage(
                content=f"[检索到的记忆]\n{rag_results['context']}"
            ))
        
        # 4. 流式运行 Agent
        tool_calls = []
        current_content = ""
        response_segments = []
        current_segment = {"content": "", "tool_calls": []}
        
        async for event_type, data in run_agent_astream(
            session_id, 
            user_message, 
            effective_history
        ):
            if event_type == "token":
                current_content += data
                current_segment["content"] += data
                yield format_sse({
                    "type": "token",
                    "content": data
                })
            
            elif event_type == "tool_call":
                tool_info = {
                    "name": data.get("name", "unknown"),
                    "args": data.get("args", {}),
                }
                tool_calls.append(tool_info)
                current_segment["tool_calls"].append(tool_info)
                
                yield format_sse({
                    "type": "tool_start",
                    "tool": tool_info["name"],
                    "input": tool_info["args"]
                })
            
            elif event_type == "tool_result":
                yield format_sse({
                    "type": "tool_end",
                    "tool": tool_calls[-1]["name"] if tool_calls else "unknown",
                    "output": str(data)[:1000]
                })
                
                if current_segment["content"]:
                    response_segments.append(current_segment)
                
                yield format_sse({"type": "new_response"})
                
                current_segment = {"content": "", "tool_calls": []}
            
            elif event_type == "message":
                msg = data
                
                if isinstance(msg, AIMessage):
                    messages_to_save.append(msg)
                elif isinstance(msg, ToolMessage):
                    messages_to_save.append(msg)
        
        # 保存最后的响应段
        if current_segment["content"]:
            response_segments.append(current_segment)
        
        # 5. 保存消息到会话
        save_session_messages(session_id, messages_to_save)
        
        # 5.5 对话结束后检查压缩（确保用户消息已包含在历史中）
        try:
            import asyncio
            from backend.graph.session import auto_compress_if_needed
            compress_info = auto_compress_if_needed(session_id)
            if compress_info:
                asyncio.create_task(_async_compress_session(
                    session_id,
                    compress_info["summary_prompt"],
                    compress_info["message_count"]
                ))
        except Exception as e:
            print(f"压缩检查失败（非阻塞）: {str(e)}")
        
        # 5.6 自动记忆提取（异步，不阻塞响应）
        try:
            from backend.graph.memory_extractor import (
                process_conversation_for_memory,
                should_extract_memory
            )
            
            if should_extract_memory(user_message):
                assistant_content = current_content or ""
                if not assistant_content and messages_to_save:
                    for msg in reversed(messages_to_save):
                        if isinstance(msg, AIMessage) and msg.content:
                            assistant_content = msg.content
                            break
                
                if assistant_content:
                    import asyncio
                    asyncio.create_task(
                        asyncio.to_thread(
                            process_conversation_for_memory,
                            user_message,
                            assistant_content
                        )
                    )
        except Exception as e:
            print(f"记忆提取失败（非阻塞）: {str(e)}")
        
        # 6. 如果是第一条消息，生成标题
        if is_first_msg and first_message_text:
            title = await generate_title(session_id, first_message_text)
            yield format_sse({
                "type": "title",
                "session_id": session_id,
                "title": title
            })
        
        # 7. 发送完成信号
        yield format_sse({
            "type": "done",
            "session_id": session_id,
            "tool_calls": tool_calls,
            "segments": len(response_segments)
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        yield format_sse({
            "type": "error",
            "message": str(e)
        })


@router.get("/system-prompt")
async def get_system_prompt():
    """获取当前的 System Prompt"""
    prompt = build_system_prompt()
    return {"system_prompt": prompt}
