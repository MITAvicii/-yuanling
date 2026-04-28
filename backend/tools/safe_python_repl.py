"""
安全的 Python REPL 工具 - 真实 Python 代码执行

安全措施：
1. 黑名单模式 - 只禁止危险模块和命令
2. 组合攻击防护 - 检测危险命令执行
3. Subprocess 隔离 - 独立进程执行
4. 超时限制 - 防止无限循环
"""

import ast
import sys
import subprocess
import tempfile
import os
import re
from typing import Optional
from langchain_core.tools import tool
from pydantic import BaseModel, Field


class SafePythonInput(BaseModel):
    """安全 Python REPL 工具输入参数"""
    code: str = Field(
        ...,
        description="要执行的 Python 代码",
        examples=["print(1+1)", "import pandas as pd; print(pd.DataFrame({'a':[1,2,3]}))"]
    )


# ============================================================
# 禁止的模块（直接阻止导入）
# ============================================================
DANGEROUS_MODULES = {
    'pty', 'tty', 'termios',  # 终端控制
    'resource',  # 资源限制
    'signal',    # 信号处理（可能导致进程崩溃）
}


# ============================================================
# 禁止的命令模式（组合攻击防护）
# ============================================================
DANGEROUS_PATTERNS = [
    # 文件删除
    r'rm\s+-rf',
    r'rmdir\s+',
    r'rm\s+-r\s+',
    r'shutil\.rmtree',
    r'shutil\.move.*sys',  # 移动系统文件
    r'shutil\.copy.*sys',
    
    # 权限修改（危险）
    r'chmod\s+-R\s+777',
    r'chmod\s+-R\s+000',
    r'chown\s+',
    
    # 磁盘操作（危险）
    r'mkfs',
    r'dd\s+if=.*of=/dev/',
    r'>\s*/dev/sd',
    r'>\s*/dev/hd',
    
    # Fork bomb
    r'fork\(\)',
    r':\(\{.*:\|:',
    r'while\s*\(\s*1\s*\).*fork',
    
    # 远程下载执行
    r'wget.*\|.*sh',
    r'curl.*\|.*sh',
    r'pip\s+install.*--trusted-host',
    
    # 尝试逃逸到主系统
    r'sys\.exit\(0\)',  # 退出进程
    r'os\.kill\(os\.getpid\(\)\)',  # 杀自己
]


def check_code_safety(code: str) -> tuple[bool, str]:
    """
    检查代码安全性
    
    Returns:
        (is_safe, error_message)
    """
    # 1. 检查危险命令模式
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, code, re.IGNORECASE):
            return False, f"代码包含危险命令: {pattern}"
    
    # 2. AST 分析 - 检查导入
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"语法错误: {e}"
    
    # 3. 检查导入的模块
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_name = alias.name.split('.')[0].lower()
                # 检查是否在禁止列表中
                if module_name in DANGEROUS_MODULES:
                    return False, f"不允许导入危险模块: {module_name}"
        
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                module_name = node.module.split('.')[0].lower()
                # 检查是否在禁止列表中
                if module_name in DANGEROUS_MODULES:
                    return False, f"不允许导入危险模块: {module_name}"
    
    return True, ""


def run_safe_python(code: str, timeout: int = 30, max_output: int = 102400) -> str:
    """
    安全地运行 Python 代码
    
    Args:
        code: 要执行的 Python 代码
        timeout: 超时时间（秒）
        max_output: 最大输出字节数
    
    Returns:
        执行结果
    """
    # 1. 安全检查
    is_safe, error_msg = check_code_safety(code)
    if not is_safe:
        return f"安全检查失败: {error_msg}"
    
    # 2. 清理代码
    code = code.strip()
    
    # 3. 创建临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write("# -*- coding: utf-8 -*-\n")
        # 重置 stdout/stderr 编码
        f.write("import sys\n")
        f.write("sys.stdout.reconfigure(encoding='utf-8', errors='replace')\n")
        f.write("sys.stderr.reconfigure(encoding='utf-8', errors='replace')\n")
        f.write(code)
        temp_file = f.name
    
    try:
        # 4. 使用 subprocess 执行
        result = subprocess.run(
            [sys.executable, '-u', temp_file],
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding='utf-8',
            errors='replace',
        )
        
        # 5. 处理输出
        output = result.stdout
        error = result.stderr
        
        # 限制输出大小
        if len(output) > max_output:
            output = output[:max_output] + f"\n\n... (输出被截断，最大 {max_output} 字节)"
        
        if error and not output:
            return f"错误:\n{error}"
        
        if output:
            return output
        
        if error:
            return f"警告:\n{error}"
        
        return "代码执行完成，无输出"
    
    except subprocess.TimeoutExpired:
        return f"错误: 代码执行超时（{timeout}秒）"
    
    except Exception as e:
        return f"错误: 执行时发生异常 - {str(e)}"
    
    finally:
        # 清理临时文件
        try:
            os.unlink(temp_file)
        except:
            pass


@tool("python_repl", args_schema=SafePythonInput)
def python_repl_tool(code: str) -> str:
    """
    执行 Python 代码。
    
    用于数据处理、计算、脚本执行等任务。
    代码在隔离环境中执行，有超时限制。
    
    允许的操作：
    - 数据处理：pandas, numpy, matplotlib, openpyxl 等
    - 数学计算：math, statistics, random 等
    - 文件读写：open(), pandas.read_excel() 等
    - 网络请求：urllib, requests 等
    
    禁止的操作：
    - 删除系统文件：rm -rf, shutil.rmtree
    - 磁盘写入：dd, mkfs
    - Fork bomb：fork()
    - 远程下载执行：wget|sh, curl|sh
    
    示例：
    - python_repl(code="print(1+1)")
    - python_repl(code="import pandas as pd; print(pd.DataFrame({'a':[1,2,3]}))")
    - python_repl(code="import matplotlib.pyplot as plt; plt.plot([1,2,3]); plt.savefig('chart.png')")
    
    Args:
        code: 要执行的 Python 代码
    
    Returns:
        代码执行结果或错误信息
    """
    return run_safe_python(code)


@tool("python_repl_safe", args_schema=SafePythonInput)
def python_repl_safe_tool(code: str) -> str:
    """
    执行 Python 代码（安全版本）。
    
    功能与 python_repl 相同。
    
    Args:
        code: 要执行的 Python 代码
    
    Returns:
        代码执行结果或错误信息
    """
    return run_safe_python(code)


# 导出工具
PYTHON_REPL_TOOL = python_repl_tool
PYTHON_REPL_SAFE_TOOL = python_repl_safe_tool
