"""
平台集成模块
"""

from backend.platforms.feishu import (
    FeishuClient,
    FeishuLongConnection,
    get_feishu_connection,
    init_feishu,
    stop_feishu,
    LARK_SDK_AVAILABLE,
)

__all__ = [
    "FeishuClient",
    "FeishuLongConnection",
    "get_feishu_connection",
    "init_feishu",
    "stop_feishu",
    "LARK_SDK_AVAILABLE",
]
