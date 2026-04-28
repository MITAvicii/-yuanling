"""
会话存储管理

支持：
- 会话 CRUD 操作
- 消息持久化
- 多段响应存储（工具调用产生的连续 assistant 消息）
- 压缩上下文支持
- LLM 优化的历史加载
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, BaseMessage

from backend.config import BACKEND_DIR


# 会话存储目录
SESSIONS_DIR = BACKEND_DIR / "sessions"

# 归档目录
ARCHIVE_DIR = SESSIONS_DIR / "archive"

# ========== 会话级数据分析缓存 ==========
# 用于在会话期间缓存已加载的数据，避免重复读取
_SESSION_DATA_CACHE: dict = {}  # {session_id: {file_path: dataframe_dict}}


def get_session_data_cache(session_id: str) -> dict:
    """获取会话的数据缓存"""
    if session_id not in _SESSION_DATA_CACHE:
        _SESSION_DATA_CACHE[session_id] = {}
    return _SESSION_DATA_CACHE[session_id]


def set_session_data(session_id: str, file_path: str, data: dict):
    """缓存会话中的数据文件"""
    cache = get_session_data_cache(session_id)
    cache[file_path] = data


def get_session_data(session_id: str, file_path: str) -> Optional[dict]:
    """获取会话中缓存的数据"""
    cache = get_session_data_cache(session_id)
    return cache.get(file_path)


def clear_session_data_cache(session_id: str):
    """清除会话的数据缓存"""
    if session_id in _SESSION_DATA_CACHE:
        del _SESSION_DATA_CACHE[session_id]

def ensure_sessions_dir():
    """确保会话目录存在"""
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)


def generate_session_id() -> str:
    """生成会话 ID"""
    return f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"


def message_to_dict(message: BaseMessage) -> dict:
    """将消息转换为字典"""
    result = {
        "type": message.type,
        "content": message.content,
    }
    
    # 添加工具调用信息
    if hasattr(message, "tool_calls") and message.tool_calls:
        result["tool_calls"] = message.tool_calls
    
    # 添加工具调用 ID
    if hasattr(message, "tool_call_id") and message.tool_call_id:
        result["tool_call_id"] = message.tool_call_id
    
    # 添加名称（用于工具消息）
    if hasattr(message, "name") and message.name:
        result["name"] = message.name
    
    return result


def dict_to_message(data: dict) -> BaseMessage:
    """将字典转换为消息"""
    msg_type = data.get("type", "human")
    content = data.get("content", "")
    
    if msg_type == "human":
        return HumanMessage(content=content)
    elif msg_type == "ai":
        msg = AIMessage(content=content)
        if "tool_calls" in data:
            msg.tool_calls = data["tool_calls"]
        return msg
    elif msg_type == "tool":
        return ToolMessage(
            content=content,
            tool_call_id=data.get("tool_call_id", ""),
            name=data.get("name", "")
        )
    else:
        return HumanMessage(content=content)


class Session:
    """会话类"""
    
    def __init__(self, session_id: str = None, title: str = "新会话"):
        self.session_id = session_id or generate_session_id()
        self.title = title
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
        self.messages: list[BaseMessage] = []
    
    def add_message(self, message: BaseMessage):
        """添加消息"""
        self.messages.append(message)
        self.updated_at = datetime.now().isoformat()
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.session_id,
            "title": self.title,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "messages": [message_to_dict(msg) for msg in self.messages],
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        """从字典创建"""
        session = cls(session_id=data.get("id"), title=data.get("title", "新会话"))
        session.created_at = data.get("created_at", datetime.now().isoformat())
        session.updated_at = data.get("updated_at", datetime.now().isoformat())
        session.messages = [dict_to_message(msg) for msg in data.get("messages", [])]
        return session
    
    def save(self):
        """保存会话到文件"""
        ensure_sessions_dir()
        file_path = SESSIONS_DIR / f"{self.session_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
    
    def delete(self):
        """删除会话文件"""
        file_path = SESSIONS_DIR / f"{self.session_id}.json"
        if file_path.exists():
            file_path.unlink()


def create_session(title: str = "新会话") -> Session:
    """创建新会话"""
    session = Session(title=title)
    session.save()
    return session


def load_session(session_id: str) -> Optional[Session]:
    """加载会话"""
    file_path = SESSIONS_DIR / f"{session_id}.json"
    if not file_path.exists():
        return None
    
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    return Session.from_dict(data)


def list_sessions() -> list[dict]:
    """列出所有会话"""
    ensure_sessions_dir()
    
    sessions = []
    for file_path in sorted(SESSIONS_DIR.glob("*.json"), reverse=True):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # 只返回基本信息，不包含消息
            sessions.append({
                "id": data.get("id"),
                "title": data.get("title"),
                "created_at": data.get("created_at"),
                "updated_at": data.get("updated_at"),
                "message_count": len(data.get("messages", [])),
            })
        except Exception as e:
            print(f"读取会话 {file_path} 时发生错误: {str(e)}")
    
    return sessions


def update_session_title(session_id: str, title: str) -> bool:
    """更新会话标题"""
    session = load_session(session_id)
    if session:
        session.title = title
        session.save()
        return True
    return False


def delete_session(session_id: str) -> bool:
    """删除会话"""
    file_path = SESSIONS_DIR / f"{session_id}.json"
    if file_path.exists():
        file_path.unlink()
        return True
    return False


def get_session_history(session_id: str) -> list[BaseMessage]:
    """获取会话历史消息"""
    session = load_session(session_id)
    if session:
        return session.messages
    return []


def save_session_message(session_id: str, message: BaseMessage):
    """保存消息到会话"""
    session = load_session(session_id)
    if not session:
        session = Session(session_id=session_id)
    
    session.add_message(message)
    session.save()


def save_session_messages(session_id: str, messages: list[BaseMessage]):
    """批量保存消息到会话"""
    session = load_session(session_id)
    if not session:
        session = Session(session_id=session_id)
    
    for message in messages:
        session.add_message(message)
    
    session.save()


def load_session_for_agent(session_id: str) -> list[BaseMessage]:
    """
    为 Agent 加载优化后的会话历史
    
    与 load_session() 的区别：
    1. 合并连续的 assistant 消息（多段响应）
    2. 如果存在 compressed_context，在头部注入虚拟的 assistant 消息
    
    LLM 要求严格的 user/assistant 交替，而实际存储中可能有连续多条
    assistant 消息（工具调用产生的多段响应），此方法将它们合并为单条。
    
    Args:
        session_id: 会话 ID
        
    Returns:
        优化后的消息列表
    """
    session = load_session(session_id)
    if not session:
        return []
    
    messages = session.messages
    if not messages:
        return []
    
    # 获取压缩上下文（如果存在）
    session_data = session.to_dict()
    compressed_context = session_data.get("compressed_context", "")
    
    result = []
    
    # 如果有压缩上下文，在头部注入虚拟的 assistant 消息
    if compressed_context:
        result.append(AIMessage(
            content=f"[以下是之前对话的摘要]\n\n{compressed_context}"
        ))
    
    # 合并连续的 assistant 消息
    i = 0
    while i < len(messages):
        msg = messages[i]
        
        if msg.type == "ai":
            # 收集连续的 assistant 消息
            merged_content = msg.content or ""
            merged_tool_calls = []
            
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                merged_tool_calls = list(msg.tool_calls)
            
            # 查看后续是否还有连续的 assistant 消息
            j = i + 1
            while j < len(messages) and messages[j].type == "ai":
                next_msg = messages[j]
                if next_msg.content:
                    merged_content += "\n" + next_msg.content
                if hasattr(next_msg, "tool_calls") and next_msg.tool_calls:
                    merged_tool_calls.extend(next_msg.tool_calls)
                j += 1
            
            # 创建合并后的消息
            merged_msg = AIMessage(content=merged_content)
            if merged_tool_calls:
                merged_msg.tool_calls = merged_tool_calls
            
            result.append(merged_msg)
            i = j
        else:
            result.append(msg)
            i += 1
    
    return result


def is_first_message(session_id: str) -> bool:
    """
    检查是否是会话的第一条消息
    
    Args:
        session_id: 会话 ID
        
    Returns:
        是否是第一条消息
    """
    session = load_session(session_id)
    if not session:
        return True
    
    # 只计算用户消息数量
    user_messages = [msg for msg in session.messages if msg.type == "human"]
    return len(user_messages) == 0


def get_message_count(session_id: str) -> int:
    """获取会话消息数量"""
    session = load_session(session_id)
    if not session:
        return 0
    return len(session.messages)


def compress_history(session_id: str, summary: str, n: int) -> dict:
    """
    压缩会话历史
    
    将前 n 条消息归档，并写入摘要
    
    Args:
        session_id: 会话 ID
        summary: 压缩摘要
        n: 要归档的消息数量
        
    Returns:
        操作结果 {archived_count, remaining_count}
    """
    session = load_session(session_id)
    if not session:
        return {"archived_count": 0, "remaining_count": 0}
    
    messages = session.messages
    if len(messages) < n:
        return {"archived_count": 0, "remaining_count": len(messages)}
    
    # 归档前 n 条消息
    archived_messages = messages[:n]
    remaining_messages = messages[n:]
    
    # 保存归档文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_file = ARCHIVE_DIR / f"{session_id}_{timestamp}.json"
    
    archive_data = {
        "session_id": session_id,
        "archived_at": datetime.now().isoformat(),
        "messages": [message_to_dict(msg) for msg in archived_messages],
    }
    
    with open(archive_file, "w", encoding="utf-8") as f:
        json.dump(archive_data, f, ensure_ascii=False, indent=2)
    
    # 更新会话
    session.messages = remaining_messages
    
    # 追加压缩上下文（多次压缩用 --- 分隔）
    session_data = session.to_dict()
    existing_context = session_data.get("compressed_context", "")
    
    if existing_context:
        session_data["compressed_context"] = f"{existing_context}\n\n---\n\n{summary}"
    else:
        session_data["compressed_context"] = summary
    
    # 保存会话
    session_file = SESSIONS_DIR / f"{session_id}.json"
    with open(session_file, "w", encoding="utf-8") as f:
        json.dump(session_data, f, ensure_ascii=False, indent=2)
    
    return {
        "archived_count": len(archived_messages),
        "remaining_count": len(remaining_messages),
    }


def get_compressed_context(session_id: str) -> Optional[str]:
    """获取会话的压缩上下文"""
    session = load_session(session_id)
    if not session:
        return None
    
    session_data = session.to_dict()
    return session_data.get("compressed_context")


def get_optimized_history(session_id: str, max_messages: int = 20) -> tuple[list[BaseMessage], Optional[str]]:
    """
    获取优化后的对话历史（方案二 + 方案三）
    
    方案二：历史摘要 - 如果存在压缩上下文，返回摘要
    方案三：滑动窗口 - 只保留最近 N 条消息
    
    Args:
        session_id: 会话 ID
        max_messages: 滑动窗口大小，保留最近 N 条消息
        
    Returns:
        (消息列表, 摘要文本如果有)
    """
    session = load_session(session_id)
    if not session:
        return [], None
    
    messages = session.messages
    if not messages:
        return [], None
    
    # 获取压缩上下文（用于摘要）
    session_data = session.to_dict()
    compressed_context = session_data.get("compressed_context", "")
    
    # 检查是否需要自动压缩
    from backend.config import get_config
    config = get_config()
    compress_threshold = config.config.agent.compress_threshold
    summary_enabled = config.config.agent.summary_enabled
    
    # 如果消息数超过阈值且启用了摘要，且还没有压缩上下文
    if len(messages) >= compress_threshold and summary_enabled and not compressed_context:
        # 触发异步压缩（不阻塞当前请求）
        pass
    
    result = []
    summary_text = None
    
    # 如果有压缩上下文，在头部注入摘要
    if compressed_context:
        summary_text = compressed_context
        result.append(AIMessage(
            content=f"[以下是之前对话的摘要]\n\n{compressed_context}"
        ))
    
    # 合并连续的 assistant 消息
    i = 0
    while i < len(messages):
        msg = messages[i]
        
        if msg.type == "ai":
            # 收集连续的 assistant 消息
            merged_content = msg.content or ""
            merged_tool_calls = []
            
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                merged_tool_calls = list(msg.tool_calls)
            
            # 查看后续是否还有连续的 assistant 消息
            j = i + 1
            while j < len(messages) and messages[j].type == "ai":
                next_msg = messages[j]
                if next_msg.content:
                    merged_content += "\n" + next_msg.content
                if hasattr(next_msg, "tool_calls") and next_msg.tool_calls:
                    merged_tool_calls.extend(next_msg.tool_calls)
                j += 1
            
            # 创建合并后的消息
            merged_msg = AIMessage(content=merged_content)
            if merged_tool_calls:
                merged_msg.tool_calls = merged_tool_calls
            
            result.append(merged_msg)
            i = j
        else:
            result.append(msg)
            i += 1
    
    # 方案三：滑动窗口 - 只保留最近 N 条消息
    has_summary = len(result) > 0 and result[0].content.startswith("[以下是之前对话的摘要]")
    
    if has_summary and len(result) > max_messages:
        result = result[:1] + result[-max_messages+1:]
    elif not has_summary and len(result) > max_messages:
        result = result[-max_messages:]
    
    # 关键修复：检查并移除孤立的 tool_calls
    # 如果 AI 消息有 tool_calls 但后续没有对应的 tool response，需要清除 tool_calls
    result = _remove_orphaned_tool_calls(result)
    
    return result, summary_text


def _remove_orphaned_tool_calls(messages: list[BaseMessage]) -> list[BaseMessage]:
    """
    移除孤立的 tool_calls
    
    如果 AI 消息有 tool_calls 但后续没有对应的 tool response，
    会导致 API 报错。需要清除这些孤立的 tool_calls。
    
    Args:
        messages: 消息列表
        
    Returns:
        处理后的消息列表
    """
    if not messages:
        return messages
    
    # 收集所有有效的 tool_call_id
    valid_tool_call_ids = set()
    for msg in messages:
        if msg.type == "tool":
            tool_call_id = getattr(msg, "tool_call_id", None)
            if tool_call_id:
                valid_tool_call_ids.add(tool_call_id)
    
    # 检查并清理 AI 消息中的孤立 tool_calls
    cleaned_messages = []
    for msg in messages:
        if msg.type == "ai" and hasattr(msg, "tool_calls") and msg.tool_calls:
            # 过滤掉没有对应 tool response 的 tool_calls
            valid_calls = [
                tc for tc in msg.tool_calls
                if tc.get("id") in valid_tool_call_ids
            ]
            
            # 创建新消息，保留有效内容但移除孤立的 tool_calls
            cleaned_msg = AIMessage(content=msg.content)
            if valid_calls:
                cleaned_msg.tool_calls = valid_calls
            
            cleaned_messages.append(cleaned_msg)
        else:
            cleaned_messages.append(msg)
    
    return cleaned_messages


def auto_compress_if_needed(session_id: str) -> Optional[dict]:
    """
    检查并自动压缩会话历史
    
    当消息数超过 compress_threshold 且没有压缩记录时，
    返回需要生成摘要的提示信息。
    
    Args:
        session_id: 会话 ID
        
    Returns:
        压缩信息字典，如果不需要压缩则返回 None
    """
    from backend.config import get_config
    config = get_config()
    
    if not config.config.agent.summary_enabled:
        return None
    
    session = load_session(session_id)
    if not session:
        return None
    
    # 获取压缩上下文（检查是否已经压缩过）
    session_data = session.to_dict()
    compressed_context = session_data.get("compressed_context", "")
    
    # 如果已经有压缩记录，检查最后一条消息是否足够老
    messages = session.messages
    threshold = config.config.agent.compress_threshold
    
    # 如果消息数超过阈值，需要压缩
    if len(messages) >= threshold:
        return {
            "need_compress": True,
            "message_count": len(messages),
            "threshold": threshold,
            "summary_prompt": _generate_summary_prompt(messages),
        }
    
    return None


def _generate_summary_prompt(messages: list[BaseMessage]) -> str:
    """
    生成摘要提示词
    
    Args:
        messages: 消息列表
        
    Returns:
        摘要提示词
    """
    # 提取对话摘要
    user_msgs = []
    ai_msgs = []
    
    for msg in messages:
        if msg.type == "human":
            user_msgs.append(msg.content[:200] if msg.content else "")
        elif msg.type == "ai":
            # 移除工具调用部分，保留主要内容
            content = msg.content or ""
            # 移除 base64 图片等大段内容
            if "data:image" in content:
                content = content[:content.find("data:image")] + "[图表已省略]"
            ai_msgs.append(content[:500])
    
    prompt = "请为以下对话生成一段简短的摘要（200字以内），概括：\n"
    prompt += "1. 用户的主要问题和需求\n"
    prompt += "2. AI 的主要回答和操作\n"
    prompt += "3. 关键的结论或结果\n\n"
    
    for i, (user, ai) in enumerate(zip(user_msgs, ai_msgs)):
        prompt += f"Q{i+1}: {user}\n"
        prompt += f"A{i+1}: {ai}\n\n"
    
    return prompt


# 导出
__all__ = [
    "Session",
    "create_session",
    "load_session",
    "load_session_for_agent",
    "list_sessions",
    "update_session_title",
    "delete_session",
    "get_session_history",
    "save_session_message",
    "save_session_messages",
    "is_first_message",
    "get_message_count",
    "compress_history",
    "get_compressed_context",
    "get_optimized_history",
    "auto_compress_if_needed",
    "SESSIONS_DIR",
    "ARCHIVE_DIR",
]
