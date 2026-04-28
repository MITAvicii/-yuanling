"""
Files API - 文件读写

路径白名单机制：
- 允许的目录前缀：workspace/、memory/、skills/、knowledge/
- 包含路径遍历检测（.. 攻击防护）
- 保存 memory/MEMORY.md 时会自动触发 memory_indexer.rebuild_index()
"""

from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.config import BACKEND_DIR, get_config
from backend.graph.skills import get_skills_list, get_skill_content, save_skills_snapshot
from backend.graph.skill_metadata import get_skill_cn_name, get_skill_category, get_skill_tags, get_skills_by_category, CATEGORY_ORDER


router = APIRouter(prefix="/api/files", tags=["files"])


# 允许访问的目录
ALLOWED_DIRS = [
    BACKEND_DIR / "workspace",
    BACKEND_DIR / "memory",
    BACKEND_DIR / "skills",
    BACKEND_DIR / "knowledge",
]

# MEMORY.md 文件名
MEMORY_FILENAME = "MEMORY.md"


def resolve_path(file_path: str) -> Path:
    """解析并验证路径"""
    path = Path(file_path)
    
    # 路径遍历检测
    if ".." in str(path):
        raise HTTPException(status_code=403, detail="路径遍历攻击被拦截")
    
    # 如果是相对路径，相对于项目根目录
    if not path.is_absolute():
        path = BACKEND_DIR.parent / path
    
    # 验证路径是否在允许的目录内
    resolved = path.resolve()
    
    for allowed_dir in ALLOWED_DIRS:
        try:
            resolved.relative_to(allowed_dir.resolve())
            return resolved
        except ValueError:
            continue
    
    raise HTTPException(status_code=403, detail="无权访问此路径")


class FileContent(BaseModel):
    """文件内容"""
    path: str
    content: str


class FileSave(BaseModel):
    """保存文件请求"""
    path: str
    content: str


@router.get("")
async def read_file(path: str = Query(..., description="文件路径")):
    """读取文件内容"""
    try:
        file_path = resolve_path(path)
    except HTTPException:
        raise
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    
    if not file_path.is_file():
        raise HTTPException(status_code=400, detail="路径不是文件")
    
    try:
        content = file_path.read_text(encoding='utf-8')
        return FileContent(path=str(file_path.relative_to(BACKEND_DIR.parent)), content=content)
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="无法解码文件（可能是二进制文件）")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取文件失败: {str(e)}")


@router.post("")
async def save_file(request: FileSave):
    """保存文件内容"""
    try:
        file_path = resolve_path(request.path)
    except HTTPException:
        raise
    
    # 确保父目录存在
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        file_path.write_text(request.content, encoding='utf-8')
        
        # 如果保存的是技能文件，更新 snapshot
        if "skills" in str(file_path) and file_path.name == "SKILL.md":
            save_skills_snapshot()
        
        # 如果保存的是 MEMORY.md，触发索引重建
        if file_path.name == MEMORY_FILENAME:
            try:
                from backend.graph.memory_indexer import rebuild_index
                rebuild_index()
                print("✓ MEMORY.md 索引已重建")
            except Exception as e:
                print(f"重建 MEMORY.md 索引失败: {str(e)}")
        
        return {"message": "保存成功", "path": str(file_path.relative_to(BACKEND_DIR.parent))}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存文件失败: {str(e)}")


@router.get("/list")
async def list_files(directory: str = Query("", description="目录路径")):
    """列出目录内容"""
    if not directory:
        # 返回允许访问的目录列表
        return {
            "directories": [
                {"name": "workspace", "path": "backend/workspace"},
                {"name": "memory", "path": "backend/memory"},
                {"name": "skills", "path": "backend/skills"},
                {"name": "knowledge", "path": "backend/knowledge"},
            ]
        }
    
    try:
        dir_path = resolve_path(directory)
    except HTTPException:
        raise
    
    if not dir_path.exists():
        raise HTTPException(status_code=404, detail="目录不存在")
    
    if not dir_path.is_dir():
        raise HTTPException(status_code=400, detail="路径不是目录")
    
    items = []
    for item in sorted(dir_path.iterdir(), key=lambda x: (not x.is_dir(), x.name)):
        items.append({
            "name": item.name,
            "type": "directory" if item.is_dir() else "file",
            "path": str(item.relative_to(BACKEND_DIR.parent)),
        })
    
    return {
        "directory": directory,
        "items": items,
    }


# Skills 专用接口

@router.get("/skills")
async def list_skills():
    """获取技能列表（带中文和分类）"""
    return {
        "categories": CATEGORY_ORDER,
        "skills_by_category": get_skills_by_category(),
        "skills": [
            {
                **skill,
                "cn_name": get_skill_cn_name(skill["name"]),
                "category": get_skill_category(skill["name"]),
                "tags": get_skill_tags(skill["name"]),
            }
            for skill in get_skills_list()
        ],
    }






@router.get("/skills/{skill_name}")
async def get_skill(skill_name: str):
    """获取技能详情"""
    content = get_skill_content(skill_name)
    if not content:
        raise HTTPException(status_code=404, detail="技能不存在")
    
    return {
        "name": skill_name,
        "content": content,
        "path": f"backend/skills/{skill_name}/SKILL.md",
    }
