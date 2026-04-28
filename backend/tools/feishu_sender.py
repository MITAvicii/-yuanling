# /home/zyc/源灵AI助手管家/backend/tools/feishu_sender.py
"""
飞书消息发送工具
"""

from typing import Optional
import asyncio
import sys
import os

# 添加项目路径
project_root = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, os.path.abspath(project_root))

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from backend.platforms.feishu import get_feishu_connection, init_feishu


class SendFeishuMessageInput(BaseModel):
    """发送飞书消息的输入参数"""
    open_id: str = Field(..., description="接收消息的用户open_id")
    content: str = Field(..., description="要发送的消息内容")
    msg_type: str = Field(default="text", description="消息类型，默认为text")


@tool("send_feishu_message", args_schema=SendFeishuMessageInput)
def send_feishu_message(open_id: str, content: str, msg_type: str = "text") -> dict:
    """
    发送消息到飞书用户。
    
    Args:
        open_id: 接收消息的用户open_id
        content: 要发送的消息内容
        msg_type: 消息类型，默认为text
        
    Returns:
        发送结果字典
    """
    try:
        # 确保飞书连接已启动
        conn = get_feishu_connection()
        if not conn.is_connected:
            print("飞书未连接，正在启动长连接...")
            init_feishu()

        # 发送消息
        async def _send():
            api_client = conn.api_client
            result = await api_client.send_message(
                receive_id=open_id,
                receive_id_type="open_id",
                content=content,
                msg_type=msg_type
            )
            return result

        # 运行异步函数
        result = asyncio.run(_send())

        return {
            "success": True,
            "message": "消息发送成功",
            "result": result
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"消息发送失败: {str(e)}"
        }


# 导出工具
SEND_FEISHU_MESSAGE_TOOL = send_feishu_message