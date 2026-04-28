"""
核心工具模块 - 导出所有工具
"""

from backend.tools.terminal import TERMINAL_TOOL
from backend.tools.safe_python_repl import PYTHON_REPL_TOOL, PYTHON_REPL_SAFE_TOOL
from backend.tools.fetch_url import FETCH_URL_TOOL
from backend.tools.file_reader import READ_FILE_TOOL, LIST_FILES_TOOL
from backend.tools.file_writer import WRITE_FILE_TOOL
from backend.tools.rag_search import RAG_SEARCH_TOOL, rebuild_index
from backend.tools.feishu_sender import SEND_FEISHU_MESSAGE_TOOL


def get_all_tools():
    """获取所有核心工具"""
    return [
        TERMINAL_TOOL,
        PYTHON_REPL_TOOL,
        FETCH_URL_TOOL,
        READ_FILE_TOOL,
        WRITE_FILE_TOOL,
        LIST_FILES_TOOL,
        RAG_SEARCH_TOOL,
        SEND_FEISHU_MESSAGE_TOOL,
    ]


def get_tools_by_name(names: list[str]):
    """根据名称获取工具"""
    tool_map = {
        "terminal": TERMINAL_TOOL,
        "python_repl": PYTHON_REPL_TOOL,
        "python_repl_safe": PYTHON_REPL_SAFE_TOOL,
        "fetch_url": FETCH_URL_TOOL,
        "read_file": READ_FILE_TOOL,
        "write_file": WRITE_FILE_TOOL,
        "list_files": LIST_FILES_TOOL,
        "search_knowledge_base": RAG_SEARCH_TOOL,
        "send_feishu_message": SEND_FEISHU_MESSAGE_TOOL,
    }
    
    return [tool_map[name] for name in names if name in tool_map]


__all__ = [
    "TERMINAL_TOOL",
    "PYTHON_REPL_TOOL", 
    "PYTHON_REPL_SAFE_TOOL",
    "FETCH_URL_TOOL",
    "READ_FILE_TOOL",
    "WRITE_FILE_TOOL",
    "LIST_FILES_TOOL",
    "RAG_SEARCH_TOOL",
    "SEND_FEISHU_MESSAGE_TOOL",
    "rebuild_index",
    "get_all_tools",
    "get_tools_by_name",
]