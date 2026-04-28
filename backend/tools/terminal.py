"""
Terminal 工具 - 沙箱化的命令行执行
"""

import os
import subprocess
from pathlib import Path
from typing import Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from backend.config import BACKEND_DIR, get_config


class TerminalInput(BaseModel):
    """Terminal 工具输入参数"""
    command: str = Field(
        ...,
        description="要执行的 Shell 命令，例如: 'ls -la', 'cat file.txt', 'pwd'",
        examples=["ls -la", "cat README.md", "pwd"]
    )


class TerminalOutput(BaseModel):
    """Terminal 工具输出"""
    success: bool
    stdout: str
    stderr: str
    return_code: int


# 危险命令黑名单
DANGEROUS_COMMANDS = [
    "rm -rf /",
    "rm -rf /*",
    "mkfs",
    "dd if=",
    "> /dev/sd",
    ":(){:|:&};:",
    "chmod -R 777 /",
    "chown -R",
    "wget",
    "curl -X POST",
    "nc -l",
    "/etc/passwd",
    "/etc/shadow",
]


def is_command_safe(command: str, blacklist: list[str]) -> tuple[bool, str]:
    """检查命令是否安全"""
    command_lower = command.lower()
    
    for dangerous in blacklist:
        if dangerous.lower() in command_lower:
            return False, f"命令包含危险操作: {dangerous}"
    
    return True, ""


def get_sandbox_dir() -> Path:
    """获取沙箱目录"""
    config = get_config().config
    root_dir = config.tools.terminal.root_dir
    
    if root_dir == ".":
        return BACKEND_DIR.parent  # 项目根目录
    return Path(root_dir).resolve()


@tool("terminal", args_schema=TerminalInput)
def terminal_tool(command: str) -> str:
    """
    在沙箱环境中执行 Shell 命令。
    
    命令将在项目目录内执行，且会拦截危险命令。
    用于文件操作、系统信息查询等任务。
    
    重要：必须提供 command 参数！
    示例：terminal(command="ls -la")
    
    Args:
        command: 要执行的 Shell 命令（必需参数）
        
    Returns:
        命令执行结果，包括 stdout、stderr 和返回码
    """
    config = get_config().config
    
    # 检查工具是否启用
    if not config.tools.terminal.enabled:
        return "错误：Terminal 工具已被禁用"
    
    # 检查命令安全性
    is_safe, reason = is_command_safe(command, config.tools.terminal.blacklist)
    if not is_safe:
        return f"错误：{reason}"
    
    # 获取沙箱目录
    sandbox_dir = get_sandbox_dir()
    
    try:
        # 执行命令
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60,  # 60秒超时
            cwd=str(sandbox_dir),
            env={**os.environ, "PWD": str(sandbox_dir)}
        )
        
        output_parts = []
        
        if result.stdout:
            output_parts.append(f"stdout:\n{result.stdout}")
        
        if result.stderr:
            output_parts.append(f"stderr:\n{result.stderr}")
        
        output_parts.append(f"返回码: {result.returncode}")
        
        return "\n".join(output_parts) if output_parts else "命令执行完成，无输出"
        
    except subprocess.TimeoutExpired:
        return "错误：命令执行超时（超过60秒）"
    except Exception as e:
        return f"错误：执行命令时发生异常 - {str(e)}"


# 导出工具
TERMINAL_TOOL = terminal_tool
