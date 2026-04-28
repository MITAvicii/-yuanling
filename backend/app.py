"""
源灵AI - FastAPI 应用入口

端口: 8002
"""

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from backend.config import get_config, BACKEND_DIR
from backend.api import api_router
from backend.graph.skills import save_skills_snapshot


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    print("=" * 50)
    print("源灵AI 后端服务启动中...")
    print("=" * 50)
    
    # 确保 .env 文件存在
    env_file = BACKEND_DIR / ".env"
    env_example = BACKEND_DIR / ".env.example"
    
    if not env_file.exists() and env_example.exists():
        print(f"提示: 请复制 .env.example 为 .env 并配置 API Key")
    
    # 生成 Skills Snapshot
    save_skills_snapshot()
    print("✓ Skills Snapshot 已生成")
    
    # 检查 API Key 配置
    config = get_config()
    if not config.settings.deepseek_api_key:
        print("⚠ 警告: DEEPSEEK_API_KEY 未配置")
    
    if not config.settings.dashscope_api_key:
        print("⚠ 警告: DASHSCOPE_API_KEY 未配置（Embedding 需要）")
    
    print(f"✓ 服务运行在 http://{config.settings.backend_host}:{config.settings.backend_port}")
    
    # 初始化飞书长连接
    try:
        from backend.platforms.feishu import init_feishu, get_feishu_connection, LARK_SDK_AVAILABLE
        from backend.graph.agent import process_message
        
        if LARK_SDK_AVAILABLE:
            feishu_config = config.get_platform_app("feishu")
            if feishu_config and feishu_config.get("app_id"):
                if init_feishu():
                    print("✓ 飞书长连接已启动")
                    
                    # 记录已知的 open_id（避免重复写入配置文件）
                    _known_feishu_open_ids = set()
                    
                    # 注册消息处理器
                    async def handle_feishu_message(text, sender_open_id, chat_type, message_id, is_mentioned):
                        """处理飞书消息的处理器"""
                        print(f"📥 收到飞书消息 from {sender_open_id}: {text}")
                        print(f"   message_id: {message_id}, chat_type: {chat_type}")
                        
                        # 优化：只在首次发现新 open_id 时更新配置
                        if sender_open_id not in _known_feishu_open_ids:
                            _known_feishu_open_ids.add(sender_open_id)
                            try:
                                import json
                                from pathlib import Path
                                config_path = Path(__file__).parent / "config.json"
                                with open(config_path, 'r', encoding='utf-8') as f:
                                    config_data = json.load(f)
                                if "platform_apps" in config_data and "feishu" in config_data["platform_apps"]:
                                    config_data["platform_apps"]["feishu"]["open_id"] = sender_open_id
                                    with open(config_path, 'w', encoding='utf-8') as f:
                                        json.dump(config_data, f, ensure_ascii=False, indent=2)
                                    print(f"✅ 已更新飞书open_id: {sender_open_id}")
                            except Exception as e:
                                print(f"更新配置时出错: {e}")
                        
                        # 调用AI处理消息
                        try:
                            result = await process_message(
                                message=text,
                                session_id=sender_open_id,
                                context=f"来自飞书({chat_type})的消息"
                            )
                            return result["content"]
                        except Exception as e:
                            print(f"处理消息时出错: {e}")
                            return "抱歉，处理您的消息时出现了错误。"
                    
                    # 注册消息处理器
                    conn = get_feishu_connection()
                    conn.on_message(handle_feishu_message)
                    print("✅ 飞书消息处理器已注册")
        else:
            print("ℹ 飞书 SDK 未安装，跳过长连接初始化")
    except Exception as e:
        print(f"⚠ 飞书长连接初始化失败: {e}")
    
    print("=" * 50)
    
    yield
    
    # 关闭时执行
    from backend.platforms.feishu import stop_feishu
    stop_feishu()
    print("源灵AI 后端服务已关闭")


# 创建应用
app = FastAPI(
    title="源灵AI",
    description="本地优先、透明可控的 AI Agent 系统",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发环境允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(api_router)


# 健康检查
@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "ok", "service": "源灵AI"}


# 根路径
@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "源灵AI",
        "version": "1.0.0",
        "description": "本地优先、透明可控的 AI Agent 系统",
        "docs": "/docs",
        "health": "/health",
    }


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理"""
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "message": "服务器内部错误"},
    )


def main():
    """启动服务"""
    config = get_config()
    
    uvicorn.run(
        "backend.app:app",
        host=config.settings.backend_host,
        port=config.settings.backend_port,
        reload=True,
        reload_dirs=[str(BACKEND_DIR)],
    )


if __name__ == "__main__":
    main()