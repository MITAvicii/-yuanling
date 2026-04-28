"""
Knowledge API - 知识库管理

功能：
- 列出知识库文件
- 上传/删除文件
- 重建索引
- 搜索测试
- 索引状态统计
"""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Query, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.config import BACKEND_DIR, get_config
# PDF 解析支持
try:
    import pypdf
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False


router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


def _extract_pdf_text(file_path: Path) -> str:
    """从 PDF 文件提取文本"""
    text_parts = []
    
    # 优先使用 pdfplumber（更好支持中文）
    if HAS_PDFPLUMBER:
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            if text_parts:
                return "\n".join(text_parts)
        except Exception as e:
            print(f"pdfplumber 解析失败: {e}")
    
    # 备用 pypdf
    if HAS_PDF:
        try:
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            for page in reader.pages:
                text_parts.append(page.extract_text())
            return "\n".join(text_parts)
        except Exception as e:
            print(f"pypdf 解析失败: {e}")
    
    if not HAS_PDF and not HAS_PDFPLUMBER:
        return "[PDF 解析需要安装 pypdf 或 pdfplumber: pip install pypdf pdfplumber]"
    
    return "[无法解析 PDF 文件]"


# 知识库目录
KNOWLEDGE_DIR = BACKEND_DIR / "knowledge"
STORAGE_DIR = BACKEND_DIR / "storage"

# 允许的文件类型
# 文档类: .md .txt .pdf .doc .docx
# 数据类: .csv .xls .xlsx
# 代码类: .py .js .ts .java .go .rs .c .cpp .h
# 配置类: .json .yaml .yml .xml .toml .ini
# 标记语言: .html .css .sql .sh
ALLOWED_EXTENSIONS = {
    # 文档类
    ".md", ".txt", ".pdf", ".doc", ".docx",
    # 数据类
    ".csv", ".xls", ".xlsx",
    # 代码类
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs", ".c", ".cpp", ".h", ".hpp",
    # 配置类
    ".json", ".yaml", ".yml", ".xml", ".toml", ".ini", ".cfg",
    # 标记语言
    ".html", ".htm", ".css", ".scss", ".sql", ".sh", ".bash", ".mdx",
}



class KnowledgeFile(BaseModel):
    """知识库文件信息"""
    name: str
    path: str
    size: int
    size_str: str
    updated_at: str
    extension: str


class KnowledgeStats(BaseModel):
    """知识库统计"""
    file_count: int
    total_size: int
    total_size_str: str
    index_exists: bool
    index_updated_at: Optional[str]


class SearchTestRequest(BaseModel):
    """搜索测试请求"""
    query: str
    top_k: int = 5


class SearchTestResult(BaseModel):
    """搜索测试结果"""
    text: str
    score: float
    source: str


def format_size(size: int) -> str:
    """格式化文件大小"""
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    else:
        return f"{size / 1024 / 1024:.1f} MB"


def get_file_extension(filename: str) -> str:
    """获取文件扩展名"""
    return Path(filename).suffix.lower()


@router.get("", response_model=List[KnowledgeFile])
async def list_knowledge_files():
    """获取知识库文件列表"""
    if not KNOWLEDGE_DIR.exists():
        KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
        return []
    
    files = []
    for item in KNOWLEDGE_DIR.iterdir():
        if item.is_file() and get_file_extension(item.name) in ALLOWED_EXTENSIONS:
            stat = item.stat()
            files.append(KnowledgeFile(
                name=item.name,
                path=f"backend/knowledge/{item.name}",
                size=stat.st_size,
                size_str=format_size(stat.st_size),
                updated_at=datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                extension=get_file_extension(item.name),
            ))
    
    # 按更新时间倒序
    files.sort(key=lambda x: x.updated_at, reverse=True)
    return files


@router.get("/stats", response_model=KnowledgeStats)
async def get_knowledge_stats():
    """获取知识库统计信息"""
    if not KNOWLEDGE_DIR.exists():
        KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    
    files = [f for f in KNOWLEDGE_DIR.iterdir() 
             if f.is_file() and get_file_extension(f.name) in ALLOWED_EXTENSIONS]
    
    total_size = sum(f.stat().st_size for f in files)
    
    # 检查索引是否存在
    index_file = STORAGE_DIR / "index_store.json"
    index_exists = index_file.exists()
    index_updated_at = None
    
    if index_exists:
        index_updated_at = datetime.fromtimestamp(
            index_file.stat().st_mtime
        ).strftime("%Y-%m-%d %H:%M")
    
    return KnowledgeStats(
        file_count=len(files),
        total_size=total_size,
        total_size_str=format_size(total_size),
        index_exists=index_exists,
        index_updated_at=index_updated_at,
    )


@router.post("/upload")
async def upload_knowledge_file(file: UploadFile = File(...)):
    """上传知识库文件"""
    # 检查文件扩展名
    ext = get_file_extension(file.filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"不支持的文件类型: {ext}。允许的类型: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # 确保目录存在
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    
    # 安全文件名（防止路径遍历）
    safe_filename = Path(file.filename).name
    file_path = KNOWLEDGE_DIR / safe_filename
    
    # 保存文件
    try:
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        return {
            "message": "上传成功",
            "filename": safe_filename,
            "size": len(content),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@router.delete("/{filename}")
async def delete_knowledge_file(filename: str):
    """删除知识库文件"""
    # 安全检查
    safe_filename = Path(filename).name
    if safe_filename != filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="无效的文件名")
    
    file_path = KNOWLEDGE_DIR / safe_filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    
    if not file_path.is_file():
        raise HTTPException(status_code=400, detail="不是文件")
    
    try:
        file_path.unlink()
        return {"message": "删除成功", "filename": safe_filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.post("/rebuild")
async def rebuild_knowledge_index():
    """重建知识库索引"""
    try:
        from backend.tools.rag_search import rebuild_index
        result = rebuild_index()
        return {"message": result}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"重建索引失败: {str(e)}")


@router.post("/search")
async def search_knowledge(request: SearchTestRequest):
    """测试知识库搜索"""
    config = get_config().config
    
    if not config.rag.enabled:
        raise HTTPException(status_code=400, detail="RAG 功能已禁用")
    
    try:
        from backend.tools.rag_search import build_or_load_index, get_reranker, _nodes_cache
        
        index = build_or_load_index()
        
        if index is None:
            raise HTTPException(status_code=404, detail="知识库为空或索引未构建")
        
        # 创建混合检索器
        from backend.tools.rag_search import _create_hybrid_retriever
        retriever = _create_hybrid_retriever(index, _nodes_cache, top_k=request.top_k * 2)
        
        # 检索
        nodes = retriever.retrieve(request.query)
        
        results = []
        for node in nodes:
            results.append({
                "text": node.node.text[:500] + "..." if len(node.node.text) > 500 else node.node.text,
                "score": float(node.score) if node.score else 0.0,
                "source": node.node.metadata.get('file_name', '未知'),
            })
        
        # Rerank 重排序
        if results:
            from backend.tools.rag_search import rerank_results
            results = rerank_results(request.query, results, top_k=request.top_k)
        
        return {
            "query": request.query,
            "count": len(results),
            "results": results,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.get("/content/{filename}")
async def get_knowledge_content(filename: str):
    """获取知识库文件内容"""
    # 安全检查
    safe_filename = Path(filename).name
    if safe_filename != filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="无效的文件名")
    
    file_path = KNOWLEDGE_DIR / safe_filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    
    if not file_path.is_file():
        raise HTTPException(status_code=400, detail="不是文件")
    
    # 检测文件类型
    file_ext = safe_filename.lower().split('.')[-1] if '.' in safe_filename else ''
    
    try:
        # PDF 文件处理
        if file_ext == 'pdf':
            content = _extract_pdf_text(file_path)
            return {
                "filename": safe_filename,
                "content": content,
                "path": f"backend/knowledge/{safe_filename}",
                "type": "pdf",
            }
        else:
            # 文本文件处理
            content = file_path.read_text(encoding='utf-8')
            return {
                "filename": safe_filename,
                "content": content,
                "path": f"backend/knowledge/{safe_filename}",
                "type": "text",
            }
    except UnicodeDecodeError:
        if file_ext != 'pdf':
            raise HTTPException(status_code=400, detail="无法解码文件（可能是二进制文件）")
        raise HTTPException(status_code=500, detail="PDF 解析失败")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取文件失败: {str(e)}")


@router.put("/content/{filename}")
async def update_knowledge_content(filename: str, content: str = Form(...)):
    """更新知识库文件内容"""
    # 安全检查
    safe_filename = Path(filename).name
    if safe_filename != filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="无效的文件名")
    
    file_path = KNOWLEDGE_DIR / safe_filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    
    try:
        file_path.write_text(content, encoding='utf-8')
        return {"message": "保存成功", "filename": safe_filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存失败: {str(e)}")
