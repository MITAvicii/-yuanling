"""
File Reader 工具 - 文件读取（带路径白名单）
"""

from pathlib import Path
from typing import Optional, List

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from backend.config import BACKEND_DIR, get_config


class FileReaderInput(BaseModel):
    """File Reader 工具输入参数"""
    file_path: str = Field(
        ...,
        description="要读取的文件路径，可以是相对路径或绝对路径",
        examples=["./backend/skills/feishu/SKILL.md", "README.md", "config.json"]
    )


class ListFilesInput(BaseModel):
    """List Files 工具输入参数"""
    directory: str = Field(
        default=".",
        description="要列出的目录路径，默认为项目根目录",
        examples=[".", "./backend", "./frontend/src"]
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


def detect_file_type(file_path: Path) -> str:
    """检测文件类型"""
    suffix = file_path.suffix.lower()
    
    type_mapping = {
        '.md': 'markdown',
        '.txt': 'text',
        '.json': 'json',
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.html': 'html',
        '.css': 'css',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.xml': 'xml',
        '.csv': 'csv',
        '.log': 'log',
    }
    
    return type_mapping.get(suffix, 'unknown')


@tool("read_file", args_schema=FileReaderInput)
def read_file_tool(file_path: str) -> str:
    """
    读取指定文件的内容。
    
    只能读取项目目录内的文件，支持多种文件格式。
    用于读取 SKILL.md 文件、配置文件、代码文件等。
    
    重要：必须提供 file_path 参数！
    示例：read_file(file_path="./backend/skills/feishu/SKILL.md")
    
    Args:
        file_path: 要读取的文件路径（必需参数，相对或绝对路径）
        
    Returns:
        文件内容或错误信息
    """
    config = get_config().config
    
    # 检查工具是否启用
    if not config.tools.file_reader.enabled:
        return "错误：File Reader 工具已被禁用"
    
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
    
    # 检查文件是否存在
    if not path.exists():
        return f"错误：文件不存在 - {file_path}"
    
    # 检查是否是文件
    if not path.is_file():
        return f"错误：路径不是文件 - {file_path}"
    
    # 检查文件大小
    max_size = 100 * 1024  # 100KB
    if path.stat().st_size > max_size:
        return f"错误：文件过大（超过100KB），请使用更具体的路径或分段读取"
    
    try:
        # 读取文件
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检测文件类型
        file_type = detect_file_type(path)
        
        # 格式化输出
        output = f"文件: {file_path}\n"
        output += f"类型: {file_type}\n"
        output += f"大小: {len(content)} 字符\n"
        output += f"{'─' * 40}\n\n"
        output += content
        
        return output
        
    except UnicodeDecodeError:
        return f"错误：无法解码文件（可能是二进制文件）- {file_path}"
    except PermissionError:
        return f"错误：没有权限读取文件 - {file_path}"
    except Exception as e:
        return f"错误：读取文件时发生异常 - {str(e)}"


@tool("list_files", args_schema=ListFilesInput)
def list_files_tool(directory: str = ".") -> str:
    """
    列出指定目录下的文件和子目录。
    
    重要：必须提供 directory 参数！
    示例：list_files(directory="./backend")
    
    Args:
        directory: 目录路径（默认为项目根目录）
        
    Returns:
        目录内容列表
    """
    # 解析路径
    path = Path(directory)
    
    if not path.is_absolute():
        path = BACKEND_DIR.parent / path
    
    # 获取允许的目录
    allowed_dirs = get_allowed_directories()
    
    # 检查路径是否允许
    is_allowed, reason = is_path_allowed(path, allowed_dirs)
    if not is_allowed:
        return f"错误：{reason}"
    
    # 检查目录是否存在
    if not path.exists():
        return f"错误：目录不存在 - {directory}"
    
    # 检查是否是目录
    if not path.is_dir():
        return f"错误：路径不是目录 - {directory}"
    
    try:
        # 列出内容
        items = list(path.iterdir())
        
        # 分类
        directories = sorted([item for item in items if item.is_dir()], key=lambda x: x.name)
        files = sorted([item for item in items if item.is_file()], key=lambda x: x.name)
        
        # 格式化输出
        output = f"目录: {directory}\n"
        output += f"{'─' * 40}\n\n"
        
        if directories:
            output += "📁 目录:\n"
            for d in directories:
                output += f"  {d.name}/\n"
            output += "\n"
        
        if files:
            output += "📄 文件:\n"
            for f in files:
                size = f.stat().st_size
                size_str = f"{size} B" if size < 1024 else f"{size/1024:.1f} KB"
                output += f"  {f.name} ({size_str})\n"
        
        if not directories and not files:
            output += "(空目录)\n"
        
        return output
        
    except PermissionError:
        return f"错误：没有权限访问目录 - {directory}"
    except Exception as e:
        return f"错误：列出目录时发生异常 - {str(e)}"


# 导出工具
READ_FILE_TOOL = read_file_tool
LIST_FILES_TOOL = list_files_tool
