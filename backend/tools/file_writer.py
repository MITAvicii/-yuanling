"""
File Writer 工具 - 文件写入（带路径白名单）
"""

from pathlib import Path
from typing import Optional, List

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from backend.config import BACKEND_DIR, get_config


class FileWriterInput(BaseModel):
    """File Writer 工具输入参数"""
    file_path: str = Field(
        ...,
        description="要写入的文件路径，可以是相对路径或绝对路径",
        examples=["./backend/memory/MEMORY.md", "./backend/skills/my_skill/SKILL.md"]
    )
    content: str = Field(
        ...,
        description="要写入的文件内容",
        examples=["# 我的技能\n\n这是技能描述..."]
    )


def get_allowed_directories() -> List[Path]:
    """获取允许访问的目录列表"""
    config = get_config().config
    allowed_paths = config.tools.file_reader.allowed_paths
    
    if not allowed_paths:
        # 默认允许项目根目录和 backend 目录
        return [BACKEND_DIR.parent, BACKEND_DIR]
    
    directories = []
    for path in allowed_paths:
        if path == ".":
            directories.append(BACKEND_DIR.parent)
        else:
            directories.append(Path(path).resolve())
    
    return directories


def is_path_allowed(file_path: Path, allowed_dirs: List[Path]) -> tuple[bool, str]:
    """
    检查路径是否在允许的目录内
    
    Args:
        file_path: 要检查的文件路径
        allowed_dirs: 允许的目录列表
        
    Returns:
        (是否允许, 原因)
    """
    try:
        resolved_path = file_path.resolve()
    except Exception as e:
        return False, f"无效的路径: {str(e)}"
    
    for allowed_dir in allowed_dirs:
        try:
            resolved_path.relative_to(allowed_dir)
            return True, ""
        except ValueError:
            continue
    
    return False, f"路径不在允许的目录内"


@tool("write_file", args_schema=FileWriterInput)
def write_file_tool(file_path: str, content: str) -> str:
    """
    写入内容到指定文件。
    
    用于更新记忆文件、创建技能文件、保存配置等。
    只能写入项目目录内的文件。
    
    重要：必须提供 file_path 和 content 参数！
    示例：write_file(file_path="./backend/memory/MEMORY.md", content="# 记忆\n\n用户偏好：...")
    
    Args:
        file_path: 要写入的文件路径（必需参数）
        content: 要写入的内容（必需参数）
        
    Returns:
        操作结果
    """
    # 解析路径
    path = Path(file_path)
    
    # 如果是相对路径，相对于项目根目录解析
    if not path.is_absolute():
        path = BACKEND_DIR.parent / path
    
    # 获取允许的目录
    allowed_dirs = get_allowed_directories()
    
    # 检查路径是否允许
    is_allowed, reason = is_path_allowed(path, allowed_dirs)
    if not is_allowed:
        return f"错误：{reason}"
    
    # 检查文件大小限制
    max_size = 100 * 1024  # 100KB
    if len(content) > max_size:
        return f"错误：内容过大（超过100KB），请减少内容"
    
    try:
        # 确保父目录存在
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # 写入文件
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return f"✅ 文件已成功写入: {file_path}\n📊 写入大小: {len(content)} 字符"
        
    except PermissionError:
        return f"错误：没有权限写入文件 - {file_path}"
    except Exception as e:
        return f"错误：写入文件时发生异常 - {str(e)}"


# 导出工具
WRITE_FILE_TOOL = write_file_tool
