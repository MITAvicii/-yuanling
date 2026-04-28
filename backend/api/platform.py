"""
平台集成 API

包含飞书、微信等平台的 Webhook 接口和管理接口
"""

from fastapi import APIRouter, Request

from backend.platforms.feishu import (
    get_feishu_connection,
    init_feishu,
    stop_feishu,
    LARK_SDK_AVAILABLE,
)
from backend.graph.agent import process_message

router = APIRouter(prefix="/api/platform", tags=["platform"])


# ==================== 飞书相关 API ====================


@router.post("/feishu/webhook")
async def feishu_webhook(request: Request):
    """
    飞书 Webhook 回调（兼容模式）
    
    注意：推荐使用长连接模式，无需配置 Webhook
    此接口仅用于兼容 Webhook 模式
    """
    return {
        "code": 0,
        "message": "请使用长连接模式，无需配置 Webhook"
    }


@router.get("/feishu/status")
async def feishu_status():
    """获取飞书集成状态"""
    conn = get_feishu_connection()
    
    return {
        "mode": "long_connection",
        "sdk_available": LARK_SDK_AVAILABLE,
        "connected": conn.is_connected,
        "message": "已连接" if conn.is_connected else "未连接",
    }


@router.post("/feishu/connect")
async def feishu_connect():
    """启动飞书长连接"""
    if not LARK_SDK_AVAILABLE:
        return {
            "success": False,
            "message": "lark-oapi SDK 未安装，请运行: pip install lark-oapi"
        }
    
    success = init_feishu()
    
    return {
        "success": success,
        "message": "连接成功" if success else "连接失败"
    }


@router.post("/feishu/disconnect")
async def feishu_disconnect():
    """断开飞书长连接"""
    stop_feishu()
    return {
        "success": True,
        "message": "已断开连接"
    }


@router.get("/feishu/test")
async def test_feishu():
    """测试飞书配置"""
    from backend.config import get_config
    
    config = get_config()
    app_config = config.get_platform_app("feishu")
    
    return {
        "status": "ok",
        "sdk_available": LARK_SDK_AVAILABLE,
        "config": {
            "enabled": bool(app_config),
            "app_id": app_config.get("app_id", "")[:8] + "..." if app_config else None,
        },
        "mode": "long_connection",
        "instructions": {
            "step1": "在飞书开放平台创建企业自建应用",
            "step2": "获取 App ID 和 App Secret",
            "step3": "在设置中配置飞书应用",
            "step4": "在飞书开放平台切换为「使用长连接接收事件」",
            "step5": "添加事件订阅: im.message.receive_v1",
            "step6": "配置权限: im:message, im:message:send_as_bot",
        }
    }


# ==================== 消息处理 ====================


async def handle_feishu_message(
    text: str,
    sender_open_id: str,
    chat_type: str,
    message_id: str,
    is_mentioned: bool
) -> str:
    """
    处理飞书消息
    
    Args:
        text: 消息文本
        sender_open_id: 发送者 Open ID
        chat_type: 聊天类型 (p2p/group)
        message_id: 消息 ID
        is_mentioned: 是否 @ 机器人
    
    Returns:
        回复内容
    """
    # 构建上下文
    context = f"[飞书{'群聊' if chat_type == 'group' else '私聊'}]"
    if is_mentioned:
        context = "[飞书群聊@]"
    
    try:
        # 使用特殊会话 ID 区分平台消息
        session_id = f"feishu_{sender_open_id}"
        
        # 调用 Agent 处理消息
        result = await process_message(
            message=text,
            session_id=session_id,
            context=context,
        )
        
        return result.get("content", "处理完成")
        
    except Exception as e:
        print(f"处理飞书消息错误: {e}")
        return "抱歉，处理您的请求时出现错误。"
