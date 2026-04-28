"""
自动记忆提取模块

在对话结束后自动分析对话内容，提取需要长期记忆的信息。
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

from backend.config import get_config
from backend.graph.memory_indexer import add_memory_if_new


class MemoryType(Enum):
    """记忆类型"""
    USER_PROFILE = "user_profile"          # 用户画像（偏好、习惯）
    IMPORTANT_EVENT = "important_event"    # 重要事件
    CONVERSATION_SUMMARY = "summary"       # 对话摘要
    TEMPORARY = "temporary"                # 临时信息（不记录）


MEMORY_EXTRACTION_PROMPT = """分析以下对话，提取需要长期记忆的信息。

## 提取规则

**需要记录：**
1. 用户偏好（如"我喜欢简洁的回答"、"我习惯用中文交流"）
2. 重要事件（如"明天我有会议"、"下周要去出差"）
3. 用户明确表示要记住的内容（如"记住这个"、"记下来"）
4. 用户的身份信息（如职业、位置、联系方式）
5. 常用场景（如飞书推送、AI新闻订阅）

**不需要记录：**
1. 简单的问答（如"1+1=2"）
2. 闲聊内容（如"天气真好"）
3. 临时性信息（如"现在几点了"）
4. 已知信息的重复

## 对话内容

{conversation}

## 输出格式

请输出 JSON 格式（仅输出 JSON，不要其他内容）：

```json
{
  "memories": [
    {
      "type": "user_profile|important_event",
      "content": "记忆内容的简明描述（一句话）",
      "importance": 0.0-1.0,
      "tags": ["标签1", "标签2"]
    }
  ],
  "summary": "对话的简短摘要（可选，仅当对话有意义时）",
  "should_remember": true或false
}
```

注意：
- importance 越高表示越重要（0.9+ 为非常关键的信息）
- 如果没有需要记忆的信息，返回 {"memories": [], "should_remember": false}
- 记忆内容要简洁明了，避免冗余
"""


def extract_memories_from_conversation(
    conversation: List[Dict[str, str]],
    llm=None
) -> Dict[str, Any]:
    """从对话中提取记忆
    
    Args:
        conversation: 对话历史 [{"role": "user/assistant", "content": "..."}]
        llm: LLM 实例（可选，如果不提供则使用配置的模型）
    
    Returns:
        提取结果 {"memories": [...], "summary": "...", "should_remember": bool}
    """
    if not conversation or len(conversation) < 2:
        return {"memories": [], "should_remember": False}
    
    # 格式化对话
    conversation_text = ""
    for msg in conversation:
        role = "用户" if msg.get("role") == "user" else "AI"
        content = msg.get("content", "")
        conversation_text += f"{role}: {content}\n\n"
    
    try:
        # 获取 LLM
        if llm is None:
            from backend.graph.agent import get_llm
            llm = get_llm()
        
        # 调用 LLM 提取记忆
        from langchain_core.messages import HumanMessage
        
        prompt = MEMORY_EXTRACTION_PROMPT.format(conversation=conversation_text)
        response = llm.invoke([HumanMessage(content=prompt)])
        
        # 解析结果
        import json
        import re
        
        content = response.content
        
        # 尝试提取 JSON
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', content)
        if json_match:
            json_str = json_match.group(1)
        else:
            # 尝试直接解析
            json_str = content.strip()
        
        # 清理并解析
        json_str = json_str.strip()
        if json_str.startswith('{') and json_str.endswith('}'):
            result = json.loads(json_str)
        else:
            # 尝试找到 JSON 对象
            start = json_str.find('{')
            end = json_str.rfind('}') + 1
            if start >= 0 and end > start:
                result = json.loads(json_str[start:end])
            else:
                return {"memories": [], "should_remember": False}
        
        return result
        
    except Exception as e:
        print(f"提取记忆失败: {str(e)}")
        return {"memories": [], "should_remember": False}


def save_memories_to_file(memories: List[Dict[str, Any]]) -> int:
    """保存记忆到 MEMORY.md
    
    Args:
        memories: 记忆列表
    
    Returns:
        成功保存的记忆数量
    """
    saved_count = 0
    
    for memory in memories:
        memory_type = memory.get("type", "important_event")
        content = memory.get("content", "")
        importance = memory.get("importance", 0.5)
        tags = memory.get("tags", [])
        
        if not content:
            continue
        
        # 格式化记忆条目
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        tag_str = " ".join([f"#{tag}" for tag in tags]) if tags else ""
        
        formatted_content = f"[{memory_type}] {content}"
        if tag_str:
            formatted_content += f" {tag_str}"
        
        # 尝试添加（会自动去重）
        if add_memory_if_new(formatted_content):
            saved_count += 1
            print(f"✓ 已保存记忆: {content[:50]}...")
    
    return saved_count


def process_conversation_for_memory(
    user_message: str,
    assistant_message: str,
    history: List[Dict[str, str]] = None
) -> int:
    """处理对话，提取并保存记忆
    
    Args:
        user_message: 用户消息
        assistant_message: AI 回复
        history: 历史对话（可选）
    
    Returns:
        保存的记忆数量
    """
    # 构建对话列表
    conversation = history or []
    conversation = conversation.copy()  # 避免修改原列表
    conversation.append({"role": "user", "content": user_message})
    conversation.append({"role": "assistant", "content": assistant_message})
    
    # 提取记忆
    result = extract_memories_from_conversation(conversation)
    
    if not result.get("should_remember", False):
        return 0
    
    memories = result.get("memories", [])
    
    # 过滤低重要性的记忆
    memories = [m for m in memories if m.get("importance", 0) >= 0.3]
    
    if not memories:
        return 0
    
    # 保存记忆
    return save_memories_to_file(memories)


def should_extract_memory(user_message: str) -> bool:
    """判断是否需要从用户消息中提取记忆
    
    跳过一些明显不需要提取的场景
    """
    skip_patterns = [
        "你好", "hello", "hi ",  # 简单问候
        "谢谢", "thanks", "thank you",  # 感谢
        "再见", "bye",  # 告别
        "好的", "ok", "嗯",  # 简单确认
        "1+1", "计算",  # 简单计算
        "现在几点", "今天天气",  # 临时信息
    ]
    
    message_lower = user_message.lower().strip()
    
    for pattern in skip_patterns:
        if pattern in message_lower and len(message_lower) < 20:
            return False
    
    return True


__all__ = [
    "extract_memories_from_conversation",
    "save_memories_to_file",
    "process_conversation_for_memory",
    "should_extract_memory",
    "MemoryType",
]
