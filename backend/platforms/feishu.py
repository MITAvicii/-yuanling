"""
飞书平台集成模块 - 长连接模式

功能：
- 使用 WebSocket 长连接接收事件
- 接收飞书消息并回复
- 主动发送消息到飞书
- 支持 @ 机器人触发
- 支持私聊和群聊

优势：
- 无需公网地址
- 无需配置加密策略
- 无需内网穿透
"""

import json
import time
import asyncio
import threading
from typing import Optional, Dict, Any, Callable

import httpx

# 飞书官方 SDK
try:
    import lark_oapi as lark
    from lark_oapi.api.im.v1 import P2ImMessageReceiveV1
    LARK_SDK_AVAILABLE = True
except ImportError:
    LARK_SDK_AVAILABLE = False
    print("警告: lark-oapi 未安装，飞书长连接功能不可用")

from backend.config import get_config


class FeishuClient:
    """飞书 API 客户端 - 用于主动发送消息"""
    
    BASE_URL = "https://open.feishu.cn/open-apis"
    
    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self._access_token: Optional[str] = None
        self._token_expire: float = 0
    
    async def get_access_token(self) -> str:
        """获取 access_token"""
        if self._access_token and time.time() < self._token_expire:
            return self._access_token
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/auth/v3/tenant_access_token/internal",
                json={
                    "app_id": self.app_id,
                    "app_secret": self.app_secret,
                }
            )
            data = response.json()
            
            if data.get("code") != 0:
                raise Exception(f"获取 access_token 失败: {data}")
            
            self._access_token = data["tenant_access_token"]
            self._token_expire = time.time() + data["expire"] - 300
            
            return self._access_token
    
    async def send_message(
        self,
        receive_id: str,
        receive_id_type: str,
        content: str,
        msg_type: str = "text"
    ) -> Dict[str, Any]:
        """发送消息"""
        token = await self.get_access_token()
        
        if msg_type == "text":
            msg_content = json.dumps({"text": content})
        else:
            msg_content = content
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/im/v1/messages",
                params={"receive_id_type": receive_id_type},
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "receive_id": receive_id,
                    "msg_type": msg_type,
                    "content": msg_content,
                }
            )
            return response.json()
    
    async def reply_message(
        self,
        message_id: str,
        content: str,
        msg_type: str = "text"
    ) -> Dict[str, Any]:
        """回复消息"""
        token = await self.get_access_token()
        
        if msg_type == "text":
            msg_content = json.dumps({"text": content})
        else:
            msg_content = content
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/im/v1/messages/{message_id}/reply",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "msg_type": msg_type,
                    "content": msg_content,
                }
            )
            return response.json()


class FeishuLongConnection:
    """飞书长连接管理器"""
    
    def __init__(self):
        self._client: Optional[lark.ws.Client] = None
        self._api_client: Optional[FeishuClient] = None
        self._message_handler: Optional[Callable] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._app_id: str = ""
        self._app_secret: str = ""
        self._reconnect_delay: int = 5  # 重连延迟（秒）
        self._max_reconnect_delay: int = 60  # 最大重连延迟
        self._current_reconnect_attempts: int = 0
    
    def configure(self, app_id: str, app_secret: str):
        """配置飞书应用"""
        self._app_id = app_id
        self._app_secret = app_secret
        self._api_client = FeishuClient(app_id, app_secret)
    
    def on_message(self, handler: Callable):
        """注册消息处理器"""
        self._message_handler = handler
    
    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        return self._running and self._client is not None
    
    @property
    def api_client(self) -> FeishuClient:
        """获取 API 客户端"""
        if not self._api_client:
            raise RuntimeError("飞书客户端未配置")
        return self._api_client
    
    def start(self) -> bool:
        """启动长连接"""
        if not LARK_SDK_AVAILABLE:
            print("错误: lark-oapi SDK 未安装，请运行: pip install lark-oapi")
            return False
        
        if not self._app_id or not self._app_secret:
            print("错误: 飞书 App ID 或 App Secret 未配置")
            return False
        
        if self._running:
            print("飞书长连接已在运行中")
            return True
        
        try:
            self._running = True
            self._thread = threading.Thread(target=self._run_client_with_reconnect, daemon=True)
            self._thread.start()
            
            print(f"飞书长连接已启动 (App ID: {self._app_id[:8]}...)")
            return True
            
        except Exception as e:
            print(f"启动飞书长连接失败: {e}")
            self._running = False
            return False
    
    def stop(self):
        """停止长连接"""
        self._running = False
        self._client = None
        print("飞书长连接已停止")
    
    def _run_client_with_reconnect(self):
        """运行客户端（带自动重连）"""
        while self._running:
            try:
                # 定义消息处理函数
                def handle_message(data: P2ImMessageReceiveV1):
                    print(f"[DEBUG] 收到原始消息: {data}")
                    self._handle_message_event(data)
                
                # 定义消息已读处理函数
                def handle_message_read(data):
                    print(f"[DEBUG] 消息已读事件: {data}")
                
                # 创建事件处理器 - 注册所有需要的消息事件
                event_handler = lark.EventDispatcherHandler.builder("", "") \
                    .register_p2_im_message_receive_v1(handle_message) \
                    .register_p2_im_message_message_read_v1(handle_message_read) \
                    .build()
                
                # 创建 WebSocket 客户端（启用自动重连）
                self._client = lark.ws.Client(
                    app_id=self._app_id,
                    app_secret=self._app_secret,
                    event_handler=event_handler,
                    log_level=lark.LogLevel.ERROR,
                    auto_reconnect=True,  # 启用自动重连
                )
                
                print("飞书长连接已建立")
                self._current_reconnect_attempts = 0  # 重置重连计数
                
                # 启动客户端（这会阻塞直到断开）
                self._client.start()
                
            except Exception as e:
                if not self._running:
                    break
                    
                self._current_reconnect_attempts += 1
                delay = min(self._reconnect_delay * (2 ** (self._current_reconnect_attempts - 1)), 
                           self._max_reconnect_delay)
                
                print(f"飞书长连接断开: {e}")
                print(f"{delay}秒后尝试重连 (第{self._current_reconnect_attempts}次)...")
                time.sleep(delay)
    
    def _handle_message_event(self, data: P2ImMessageReceiveV1):
        """处理消息事件"""
        try:
            print(f"[FEISHU] 收到飞书消息事件")
            
            # 解析事件数据
            event = data.event
            message = event.message
            
            # 消息内容
            content_str = message.content
            try:
                content = json.loads(content_str)
                text = content.get("text", "")
            except json.JSONDecodeError:
                text = content_str
            
            # 发送者信息
            sender = event.sender
            sender_id = sender.sender_id
            open_id = sender_id.open_id
            
            # 消息类型和聊天类型
            chat_type = message.chat_type  # p2p 或 group
            message_id = message.message_id
            
            print(f"[FEISHU] 解析完成: open_id={open_id}, msg_id={message_id}, text={text[:50]}...")
            
            # 检查是否 @ 机器人
            is_mentioned = False
            if hasattr(message, 'mentions') and message.mentions:
                is_mentioned = True
                # 移除 @ 文本
                for mention in message.mentions:
                    if hasattr(mention, 'key') and mention.key:
                        text = text.replace(mention.key, "").strip()
            
            # 直接调用处理（不等待结果）
            # 注意：不要在回调中等待异步操作，否则会导致超时
            asyncio.create_task(
                self._process_message(
                    text=text,
                    open_id=open_id,
                    chat_type=chat_type,
                    message_id=message_id,
                    is_mentioned=is_mentioned,
                )
            )
                    
        except Exception as e:
            print(f"[FEISHU] 处理飞书消息错误: {e}")
    
    async def _process_message(
        self,
        text: str,
        open_id: str,
        chat_type: str,
        message_id: str,
        is_mentioned: bool
    ):
        """处理消息（异步）"""
        print(f"[FEISHU] 开始处理消息: msg_id={message_id}, text={text[:30]}...")
        try:
            # 调用用户注册的处理器
            reply = None
            if self._message_handler:
                print(f"[FEISHU] 调用消息处理器...")
                reply = await self._message_handler(
                    text=text,
                    sender_open_id=open_id,
                    chat_type=chat_type,
                    message_id=message_id,
                    is_mentioned=is_mentioned,
                )
                print(f"[FEISHU] 处理器返回: reply长度={len(reply) if reply else 0}")
            
            # 发送回复（处理长度限制）
            if reply and self._api_client:
                print(f"[FEISHU] 准备回复消息...")
                # 飞书消息最大长度约4000字符，需要截断
                max_length = 3800  # 留一些余量
                if len(reply) > max_length:
                    reply = reply[:max_length] + "\n\n📎 消息较长，已截断..."
                
                result = await self._api_client.reply_message(message_id, reply)
                print(f"[FEISHU] 回复API结果: code={result.get('code')}, msg={result.get('msg')}")
                if result.get("code") == 0:
                    print(f"✅ 飞书消息回复成功 (长度: {len(reply)})")
                else:
                    print(f"❌ 飞书消息回复失败: code={result.get('code')}, msg={result.get('msg')}")
            elif not self._api_client:
                print(f"[FEISHU] 警告: _api_client 为 None，无法发送回复")
            else:
                print(f"[FEISHU] 处理器返回为空，不发送回复")
                
        except Exception as e:
            print(f"[FEISHU] 处理消息时出错: {e}")


# 全局长连接实例
_feishu_connection: Optional[FeishuLongConnection] = None


def get_feishu_connection() -> FeishuLongConnection:
    """获取飞书长连接实例"""
    global _feishu_connection
    
    if _feishu_connection is None:
        _feishu_connection = FeishuLongConnection()
    
    return _feishu_connection


def init_feishu() -> bool:
    """初始化并启动飞书长连接"""
    config = get_config()
    app_config = config.get_platform_app("feishu")
    
    if not app_config:
        print("飞书应用未配置")
        return False
    
    app_id = app_config.get("app_id", "")
    app_secret = app_config.get("app_secret", "")
    
    if not app_id or not app_secret:
        print("飞书 App ID 或 App Secret 为空")
        return False
    
    conn = get_feishu_connection()
    conn.configure(app_id, app_secret)
    
    return conn.start()


def stop_feishu():
    """停止飞书长连接"""
    global _feishu_connection
    if _feishu_connection:
        _feishu_connection.stop()