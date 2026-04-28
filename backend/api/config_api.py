"""
配置管理 API
"""

from typing import Optional, Dict, List, Any
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

from backend.config import get_config, BACKEND_DIR

router = APIRouter(prefix="/api/config", tags=["config"])


class AddPlatformAppRequest(BaseModel):
    platform: str
    app_id: str
    app_secret: str
    encrypt_key: Optional[str] = None
    verification_token: Optional[str] = None


class SetConfigRequest(BaseModel):
    chat_provider: Optional[str] = None
    chat_model: Optional[str] = None
    temperature: Optional[float] = None
    embedding_model: Optional[str] = None
    provider_api_keys: Optional[Dict[str, str]] = None
    custom_models: Optional[Dict[str, List[str]]] = None
    provider_models: Optional[Dict[str, str]] = None  # 每个提供商最后使用的模型


# ========== Config API ==========

@router.get("")
async def get_full_config():
    """获取完整配置信息"""
    config = get_config()
    
    # 获取所有 API Keys（脱敏）
    provider_api_keys = {}
    for provider_id in ["deepseek", "dashscope", "openai", "nvidia", "ollama"]:
        key = config.get_api_key(provider_id)
        if key:
            provider_api_keys[provider_id] = key
    
    # 添加自定义提供商
    for provider_id in config.config.providers:
        key = config.get_api_key(provider_id)
        if key:
            provider_api_keys[provider_id] = key
    
    # 获取每个提供商最后使用的模型
    provider_models = getattr(config.config, 'provider_models', {}) or {}
    
    return {
        "chat_provider": config.config.chat_provider,
        "chat_model": config.config.chat_model,
        "temperature": config.config.temperature,
        "embedding_model": config.config.embedding_model,
        "rag_enabled": config.config.rag_enabled,
        "providers": {k: v.dict() if hasattr(v, 'dict') else v for k, v in config.config.providers.items()},
        "provider_api_keys": provider_api_keys,
        "provider_models": provider_models,
    }


@router.put("")
async def set_full_config(request: SetConfigRequest):
    """更新配置"""
    config = get_config()
    
    if request.chat_provider is not None:
        config.config.chat_provider = request.chat_provider
    if request.chat_model is not None:
        config.config.chat_model = request.chat_model
    if request.temperature is not None:
        config.config.temperature = request.temperature
    if request.embedding_model is not None:
        config.config.embedding_model = request.embedding_model
    
    # 保存每个提供商最后使用的模型
    if request.provider_models:
        if not hasattr(config.config, 'provider_models') or config.config.provider_models is None:
            config.config.provider_models = {}
        config.config.provider_models.update(request.provider_models)
    
    config.save_config()
    
    # 更新 API Keys
    if request.provider_api_keys:
        _save_api_keys(request.provider_api_keys)
    
    return {"message": "配置已更新"}


def _save_api_keys(api_keys: Dict[str, str]):
    """保存 API Keys 到 .env 文件"""
    env_path = BACKEND_DIR / ".env"
    
    env_content = ""
    if env_path.exists():
        env_content = env_path.read_text(encoding='utf-8')
    
    lines = env_content.split('\n')
    
    for provider_id, api_key in api_keys.items():
        if not api_key:
            continue
            
        key_name = f"{provider_id.upper()}_API_KEY"
        found = False
        
        for i, line in enumerate(lines):
            if line.startswith(f"{key_name}="):
                lines[i] = f"{key_name}={api_key}"
                found = True
                break
        
        if not found:
            lines.append(f"{key_name}={api_key}")
    
    env_path.write_text('\n'.join(lines), encoding='utf-8')
    
    # 重新加载环境变量
    from dotenv import load_dotenv
    load_dotenv(env_path, override=True)


# ========== RAG Mode ==========

@router.get("/rag-mode")
async def get_rag_mode():
    """获取 RAG 模式状态"""
    config = get_config()
    return {"enabled": config.config.rag_enabled}


@router.put("/rag-mode")
async def set_rag_mode(enabled: bool = True):
    """设置 RAG 模式"""
    config = get_config()
    config.config.rag_enabled = enabled
    config.save_config()
    return {"enabled": enabled}


# ========== Providers ==========

@router.get("/providers")
async def get_providers():
    """获取所有提供商"""
    config = get_config()
    
    providers = [
        {"id": "deepseek", "name": "DeepSeek", "base_url": "https://api.deepseek.com", "models": ["deepseek-chat", "deepseek-reasoner"]},
        {"id": "openai", "name": "OpenAI", "base_url": "https://api.openai.com/v1", "models": ["gpt-4o", "gpt-4-turbo"]},
        {"id": "dashscope", "name": "阿里云", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "models": ["qwen-turbo", "qwen-plus"]},
        {"id": "nvidia", "name": "NVIDIA", "base_url": "https://integrate.api.nvidia.com/v1", "models": ["meta/llama-3.1-8b-instruct"]},
        {"id": "ollama", "name": "Ollama (本地)", "base_url": "http://localhost:11434/v1", "models": ["llama3.1", "qwen2.5"]},
    ]
    
    # 添加自定义提供商
    for provider_id, provider_config in config.config.providers.items():
        providers.append({
            "id": provider_id,
            "name": provider_id,
            "base_url": provider_config.base_url,
            "models": provider_config.models or [],
            "is_custom": True,
        })
    
    return {"providers": providers}


# ========== Platform Apps ==========

@router.get("/platforms")
async def get_platform_apps():
    """获取已配置的平台应用"""
    config = get_config()
    apps = config.config.platform_apps or {}
    
    result = []
    for platform, app_config in apps.items():
        result.append({
            "platform": platform,
            "app_id": app_config.get("app_id", ""),
            "enabled": app_config.get("enabled", True),
        })
    
    return {"apps": result}


@router.post("/platforms")
async def add_platform_app(request: AddPlatformAppRequest):
    """添加平台应用"""
    config = get_config()
    
    if config.config.platform_apps is None:
        config.config.platform_apps = {}
    
    config.config.platform_apps[request.platform] = {
        "app_id": request.app_id,
        "app_secret": request.app_secret,
        "encrypt_key": request.encrypt_key,
        "verification_token": request.verification_token,
        "enabled": True,
    }
    
    config.save_config()
    
    return {
        "message": f"平台应用 {request.platform} 已添加",
        "platform": request.platform,
        "app_id": request.app_id,
    }


@router.delete("/platforms/{platform}")
async def delete_platform_app(platform: str):
    """删除平台应用"""
    config = get_config()
    
    if not config.config.platform_apps or platform not in config.config.platform_apps:
        raise HTTPException(status_code=404, detail="平台应用不存在")
    
    del config.config.platform_apps[platform]
    config.save_config()
    
    return {"message": f"平台应用 {platform} 已删除"}
