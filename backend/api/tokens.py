"""
Tokens API - Token 统计
"""

import tiktoken
from fastapi import APIRouter, HTTPException

from backend.graph import load_session
from backend.config import BACKEND_DIR, get_config


router = APIRouter(prefix="/api/tokens", tags=["tokens"])


def count_tokens(text: str, model: str = "cl100k_base") -> int:
    """计算文本的 token 数量"""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        # 使用默认编码
        encoding = tiktoken.get_encoding("cl100k_base")
    
    return len(encoding.encode(text))


@router.get("/session/{session_id}")
async def get_session_tokens(session_id: str):
    """获取会话的 token 统计"""
    session = load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    total_tokens = 0
    message_tokens = []
    
    for msg in session.messages:
        content = msg.content or ""
        tokens = count_tokens(content)
        total_tokens += tokens
        message_tokens.append({
            "type": msg.type,
            "tokens": tokens,
        })
    
    return {
        "session_id": session_id,
        "total_tokens": total_tokens,
        "message_count": len(session.messages),
        "messages": message_tokens,
    }


@router.post("/text")
async def count_text_tokens(text: str):
    """计算文本的 token 数量"""
    tokens = count_tokens(text)
    return {"tokens": tokens, "characters": len(text)}


@router.post("/files")
async def count_file_tokens(files: list[str]):
    """计算多个文件的 token 总数"""
    total_tokens = 0
    file_stats = []
    
    for file_path in files:
        path = BACKEND_DIR.parent / file_path
        if path.exists() and path.is_file():
            try:
                content = path.read_text(encoding='utf-8')
                tokens = count_tokens(content)
                total_tokens += tokens
                file_stats.append({
                    "path": file_path,
                    "tokens": tokens,
                    "characters": len(content),
                })
            except Exception as e:
                file_stats.append({
                    "path": file_path,
                    "error": str(e),
                })
        else:
            file_stats.append({
                "path": file_path,
                "error": "文件不存在",
            })
    
    return {
        "total_tokens": total_tokens,
        "files": file_stats,
    }
