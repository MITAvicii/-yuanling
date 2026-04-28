"""
Sessions API - 会话管理
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.graph import (
    create_session,
    load_session,
    list_sessions,
    update_session_title,
    delete_session,
    get_session_history,
    SESSIONS_DIR,
)
from backend.graph.agent import get_llm


router = APIRouter(prefix="/api/sessions", tags=["sessions"])


class SessionCreate(BaseModel):
    """创建会话请求"""
    title: Optional[str] = "新会话"


class SessionUpdate(BaseModel):
    """更新会话请求"""
    title: str


class SessionResponse(BaseModel):
    """会话响应"""
    id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int


class SessionDetail(BaseModel):
    """会话详情"""
    id: str
    title: str
    created_at: str
    updated_at: str
    messages: list


@router.get("", response_model=list[SessionResponse])
async def get_sessions():
    """获取所有会话列表"""
    sessions = list_sessions()
    return sessions


@router.post("", response_model=SessionResponse)
async def create_new_session(request: SessionCreate):
    """创建新会话"""
    session = create_session(title=request.title)
    return SessionResponse(
        id=session.session_id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=0,
    )


@router.get("/{session_id}")
async def get_session(session_id: str):
    """获取会话详情"""
    session = load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    from backend.graph.session import message_to_dict
    
    return SessionDetail(
        id=session.session_id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
        messages=[message_to_dict(msg) for msg in session.messages],
    )


@router.put("/{session_id}")
async def update_session(session_id: str, request: SessionUpdate):
    """更新会话标题"""
    success = update_session_title(session_id, request.title)
    if not success:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    return {"message": "更新成功"}


@router.delete("/{session_id}")
async def delete_session_by_id(session_id: str):
    """删除会话"""
    success = delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    return {"message": "删除成功"}


@router.get("/{session_id}/messages")
async def get_messages(session_id: str):
    """获取会话消息历史"""
    session = load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    from backend.graph.session import message_to_dict
    
    return {
        "session_id": session_id,
        "messages": [message_to_dict(msg) for msg in session.messages],
    }


@router.get("/{session_id}/history")
async def get_history(session_id: str):
    """获取对话历史（用于 Agent 输入）"""
    messages = get_session_history(session_id)
    
    from backend.graph.session import message_to_dict
    
    return {
        "session_id": session_id,
        "messages": [message_to_dict(msg) for msg in messages],
    }


@router.post("/{session_id}/generate-title")
async def generate_title(session_id: str):
    """AI 生成会话标题"""
    session = load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    # 获取前几条消息
    messages = session.messages[:5]
    if not messages:
        return {"title": "新会话"}
    
    # 构建摘要
    content_summary = "\n".join([
        f"{msg.type}: {msg.content[:100]}..."
        for msg in messages
        if hasattr(msg, 'content') and msg.content
    ])
    
    # 使用 LLM 生成标题
    try:
        llm = get_llm()
        response = llm.invoke([
            {"role": "system", "content": "请根据以下对话内容生成一个简短的标题（不超过10个字），只返回标题本身，不要其他内容。"},
            {"role": "user", "content": content_summary},
        ])
        
        title = response.content.strip().strip('"').strip('"')
        
        # 更新标题
        update_session_title(session_id, title)
        
        return {"title": title}
        
    except Exception as e:
        return {"title": session.title}


@router.post("/{session_id}/compress")
async def compress_session(session_id: str):
    """压缩会话历史"""
    session = load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    # 获取消息
    messages = session.messages
    if len(messages) < 10:
        return {"message": "消息数量不足，无需压缩"}
    
    # 构建摘要请求
    content_summary = "\n".join([
        f"{msg.type}: {msg.content[:200]}"
        for msg in messages[:-5]  # 保留最后 5 条消息
        if hasattr(msg, 'content') and msg.content
    ])
    
    try:
        llm = get_llm()
        response = llm.invoke([
            {"role": "system", "content": "请总结以下对话内容，保留重要信息，生成一个简明的摘要。"},
            {"role": "user", "content": content_summary},
        ])
        
        summary = response.content
        
        # 保存压缩后的会话（保留最后 5 条消息）
        session.messages = messages[-5:]
        session.save()
        
        return {
            "message": "压缩成功",
            "summary": summary,
            "remaining_messages": len(session.messages),
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"压缩失败: {str(e)}")
