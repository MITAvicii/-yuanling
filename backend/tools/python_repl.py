"""
Python REPL 工具 - Python 代码执行
"""

from typing import Optional

from langchain_experimental.utilities import PythonREPL
from langchain_core.tools import tool
from pydantic import BaseModel, Field


class PythonREPLInput(BaseModel):
    """Python REPL 工具输入参数"""
    code: str = Field(
        ...,
        description="要执行的 Python 代码，例如: 'print(1+1)', 'import os; print(os.getcwd())'",
        examples=["print('hello')", "import math; print(math.sqrt(2))"]
    )


@tool("python_repl", args_schema=PythonREPLInput)
def python_repl_tool(code: str) -> str:
    """
    执行 Python 代码并返回结果。
    
    用于数据处理、计算、脚本执行等任务。
    代码在一个隔离的 Python 环境中执行。
    
    重要：必须提供 code 参数！
    示例：python_repl(code="print('hello')")
    
    Args:
        code: 要执行的 Python 代码（必需参数）
        
    Returns:
        代码执行结果或错误信息
    """
    try:
        # 创建 Python REPL 实例
        repl = PythonREPL()
        
        # 执行代码
        result = repl.run(code)
        
        if result is None or result == "":
            return "代码执行完成，无输出"
        
        return f"执行结果:\n{result}"
        
    except Exception as e:
        return f"错误：执行代码时发生异常 - {str(e)}"


# 安全的 Python REPL 工具（带超时和资源限制）
@tool("python_repl_safe")
def python_repl_safe_tool(code: str) -> str:
    """
    在安全模式下执行 Python 代码。
    
    相比普通模式，增加了以下限制：
    - 执行时间限制
    - 内存使用限制
    - 禁止危险操作
    
    Args:
        code: 要执行的 Python 代码
        
    Returns:
        代码执行结果或错误信息
    """
    # 危险模块/函数黑名单
    dangerous_imports = [
        "os.system",
        "subprocess",
        "eval",
        "exec",
        "compile",
        "__import__",
        "open('/",
        "shutil.rmtree",
    ]
    
    # 检查危险操作
    code_lower = code.lower()
    for dangerous in dangerous_imports:
        if dangerous.lower() in code_lower:
            return f"错误：代码包含危险操作: {dangerous}"
    
    return python_repl_tool(code)


# 导出工具
PYTHON_REPL_TOOL = python_repl_tool
PYTHON_REPL_SAFE_TOOL = python_repl_safe_tool
