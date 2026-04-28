"""
源灵AI 配置管理模块
支持多 API 提供商配置和动态切换
"""

import json
import os
from pathlib import Path
from typing import Any, Optional, Dict, List

from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_settings import BaseSettings

# 加载环境变量
load_dotenv()

# 项目根目录
BACKEND_DIR = Path(__file__).parent
PROJECT_ROOT = BACKEND_DIR.parent


class ProviderConfig(BaseModel):
    """API 提供商配置"""
    base_url: str
    api_key_env: str = ""
    models: List[str] = []


class RAGConfig(BaseModel):
    """RAG 配置"""
    enabled: bool = True
    knowledge_dir: str = "knowledge"
    storage_dir: str = "storage"
    chunk_size: int = 512
    chunk_overlap: int = 50
    rerank_threshold: float = 0.0  # rerank 分数阈值


class MemoryConfig(BaseModel):
    """记忆配置"""
    max_file_size: int = 20000
    truncation_marker: str = "...[truncated]"


class TerminalToolConfig(BaseModel):
    """终端工具配置"""
    enabled: bool = True
    root_dir: str = "."
    blacklist: List[str] = []


class FileReaderToolConfig(BaseModel):
    """文件读取工具配置"""
    enabled: bool = True
    allowed_paths: List[str] = []


class ToolsConfig(BaseModel):
    """工具配置"""
    terminal: TerminalToolConfig = TerminalToolConfig()
    file_reader: FileReaderToolConfig = FileReaderToolConfig()


class AgentConfig(BaseModel):
    """Agent 配置"""
    max_iterations: int = 15  # Agent 最大迭代次数
    recursion_limit: int = 100  # LangGraph 递归限制
    request_timeout: int = 180  # LLM 请求超时（秒）
    tool_result_max_length: int = 500  # 工具结果最大长度
    
    # ========== 上下文优化配置 ==========
    max_history_messages: int = 20  # 滑动窗口大小，保留最近 N 条消息
    compress_threshold: int = 15  # 触发压缩的消息数量阈值
    summary_enabled: bool = True  # 是否启用历史摘要功能


class AppConfig(BaseModel):
    """应用配置"""
    # 模型配置
    chat_provider: str = "deepseek"
    chat_model: str = "deepseek-chat"
    temperature: float = 0.7
    max_tokens: int = 4096
    embedding_model: str = "bge-base-zh-v1.5"
    
    # 提供商配置
    providers: Dict[str, ProviderConfig] = {}
    custom_models: Dict[str, List[str]] = {}
    provider_models: Dict[str, str] = {}
    
    # 平台应用配置
    platform_apps: Optional[Dict[str, Dict[str, Any]]] = None
    
    # RAG 配置
    rag_enabled: bool = True
    rag: RAGConfig = RAGConfig()
    
    # 记忆配置
    memory: MemoryConfig = MemoryConfig()
    
    # 工具配置
    tools: ToolsConfig = ToolsConfig()
    
    # Agent 配置
    agent: AgentConfig = AgentConfig()


class Settings(BaseSettings):
    """全局设置"""
    # 服务配置
    backend_host: str = "0.0.0.0"
    backend_port: int = 8002
    
    # API Keys (从环境变量读取)
    deepseek_api_key: Optional[str] = None
    deepseek_base_url: str = "https://api.deepseek.com"
    
    dashscope_api_key: Optional[str] = None
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    
    openai_api_key: Optional[str] = None
    openai_base_url: str = "https://api.openai.com/v1"
    
    nvidia_api_key: Optional[str] = None
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    
    class Config:
        env_file = str(BACKEND_DIR / ".env")
        env_file_encoding = "utf-8"


class ConfigManager:
    """配置管理器"""
    
    _instance: Optional["ConfigManager"] = None
    _config: Optional[AppConfig] = None
    _settings: Optional[Settings] = None
    
    def __new__(cls) -> "ConfigManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._config is None:
            self._load_config()
        if self._settings is None:
            self._settings = Settings()
    
    def _load_config(self) -> None:
        """从 config.json 加载配置"""
        config_path = BACKEND_DIR / "config.json"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._config = AppConfig(**data)
        else:
            self._config = AppConfig()
    
    def save_config(self) -> None:
        """保存配置到 config.json"""
        config_path = BACKEND_DIR / "config.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(self._config.model_dump(), f, indent=2, ensure_ascii=False)
    
    @property
    def config(self) -> AppConfig:
        """获取应用配置"""
        return self._config
    
    @property
    def settings(self) -> Settings:
        """获取全局设置"""
        return self._settings
    
    def get_api_key(self, provider: str) -> Optional[str]:
        """获取指定提供商的 API Key"""
        key_mapping = {
            "deepseek": self._settings.deepseek_api_key,
            "dashscope": self._settings.dashscope_api_key,
            "openai": self._settings.openai_api_key,
            "nvidia": self._settings.nvidia_api_key,
        }
        
        if provider in key_mapping:
            return key_mapping[provider]
        
        # 自定义提供商 - 从环境变量动态获取
        env_key = f"{provider.upper()}_API_KEY"
        return os.environ.get(env_key)
    
    def get_base_url(self, provider: str) -> str:
        """获取指定提供商的 Base URL"""
        # 优先从 config.json 的 providers 配置读取
        if provider in self._config.providers:
            return self._config.providers[provider].base_url
        
        # 内置提供商
        url_mapping = {
            "deepseek": self._settings.deepseek_base_url,
            "dashscope": self._settings.dashscope_base_url,
            "openai": self._settings.openai_base_url,
            "nvidia": self._settings.nvidia_base_url,
        }
        
        if provider in url_mapping:
            return url_mapping[provider]
        
        # 从环境变量获取自定义提供商的 base_url
        env_url = f"{provider.upper()}_BASE_URL"
        return os.environ.get(env_url, "")
    
    def get_llm_config(self) -> dict[str, Any]:
        """获取当前 LLM 配置"""
        provider = self._config.chat_provider
        return {
            "provider": provider,
            "model": self._config.chat_model,
            "temperature": self._config.temperature,
            "max_tokens": self._config.max_tokens,
            "api_key": self.get_api_key(provider),
            "base_url": self.get_base_url(provider),
        }
    
    def get_platform_app(self, platform: str) -> Optional[Dict[str, Any]]:
        """获取平台应用配置"""
        if self._config.platform_apps and platform in self._config.platform_apps:
            return self._config.platform_apps[platform]
        return None
    
    def update_llm_provider(self, provider: str, model: Optional[str] = None) -> None:
        """更新 LLM 提供商"""
        self._config.chat_provider = provider
        if model:
            self._config.chat_model = model
        self.save_config()
    
    def add_provider(self, name: str, base_url: str, api_key_env: str = "", models: List[str] = None) -> None:
        """添加新的 API 提供商"""
        self._config.providers[name] = ProviderConfig(
            base_url=base_url,
            api_key_env=api_key_env,
            models=models or []
        )
        self.save_config()


# 全局配置管理器实例
config_manager = ConfigManager()


def get_config() -> ConfigManager:
    """获取配置管理器"""
    return config_manager
