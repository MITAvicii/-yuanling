"""
Skills 加载和管理
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Optional
import yaml

from backend.config import BACKEND_DIR


# Skills 目录
SKILLS_DIR = BACKEND_DIR / "skills"
WORKSPACE_DIR = BACKEND_DIR / "workspace"


class Skill:
    """技能类"""
    
    def __init__(
        self,
        name: str,
        description: str,
        location: str,
        version: str = "1.0.0",
        author: str = "unknown",
    ):
        self.name = name
        self.description = description
        self.location = location
        self.version = version
        self.author = author
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "name": self.name,
            "description": self.description,
            "location": self.location,
            "version": self.version,
            "author": self.author,
        }
    
    @classmethod
    def from_skill_md(cls, file_path: Path) -> Optional["Skill"]:
        """从 SKILL.md 文件解析技能"""
        if not file_path.exists():
            return None
        
        try:
            content = file_path.read_text(encoding='utf-8')
            
            # 解析 frontmatter
            metadata = {}
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    frontmatter = parts[1].strip()
                    try:
                        metadata = yaml.safe_load(frontmatter) or {}
                    except:
                        pass
            
            # 提取名称
            name = metadata.get('name', file_path.parent.name)
            
            # 提取描述：优先从 frontmatter，否则从 Markdown 内容提取
            description = metadata.get('description')
            if not description:
                # 尝试从 "## 技能描述" 或 "# 技能名称" 后提取描述
                desc_match = re.search(r'##\s*技能描述\s*\n+(.+?)(?=\n##|\n#|$)', content, re.DOTALL)
                if desc_match:
                    description = desc_match.group(1).strip().split('\n')[0].strip()
                else:
                    # 尝试从一级标题后提取第一段
                    title_match = re.search(r'#\s*.+\n+(.+?)(?=\n##|\n#|$)', content, re.DOTALL)
                    if title_match:
                        description = title_match.group(1).strip().split('\n')[0].strip()
                    else:
                        description = '无描述'
            
            # 计算相对路径
            relative_path = file_path.relative_to(BACKEND_DIR.parent)
            location = f"./{relative_path}"
            
            return cls(
                name=name,
                description=description,
                location=location,
                version=metadata.get('version', '1.0.0'),
                author=metadata.get('author', 'unknown'),
            )
            
        except Exception as e:
            print(f"解析技能文件 {file_path} 时发生错误: {str(e)}")
            return None


def scan_skills() -> list[Skill]:
    """
    扫描所有技能
    
    扫描 skills 目录下的所有 SKILL.md 文件
    """
    skills = []
    
    if not SKILLS_DIR.exists():
        return skills
    
    for skill_dir in SKILLS_DIR.iterdir():
        if skill_dir.is_dir():
            skill_md = skill_dir / "SKILL.md"
            skill = Skill.from_skill_md(skill_md)
            if skill:
                skills.append(skill)
    
    return skills


def generate_skills_snapshot() -> str:
    """
    生成 SKILLS_SNAPSHOT.md
    
    格式：
    <available_skills>
    <skill>
    <name>skill_name</name>
    <description>技能描述</description>
    <location>./path/to/SKILL.md</location>
    </skill>
    </available_skills>
    """
    skills = scan_skills()
    
    lines = ["<available_skills>"]
    
    for skill in skills:
        lines.append("<skill>")
        lines.append(f"<name>{skill.name}</name>")
        lines.append(f"<description>{skill.description}</description>")
        lines.append(f"<location>{skill.location}</location>")
        lines.append("</skill>")
    
    lines.append("</available_skills>")
    
    return "\n".join(lines)


def save_skills_snapshot():
    """保存 SKILLS_SNAPSHOT.md 到 workspace 目录"""
    snapshot = generate_skills_snapshot()
    snapshot_path = WORKSPACE_DIR / "SKILLS_SNAPSHOT.md"
    
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(snapshot, encoding='utf-8')
    
    return snapshot_path


def get_skills_list() -> list[dict]:
    """获取技能列表（用于 API）"""
    skills = scan_skills()
    return [skill.to_dict() for skill in skills]


def get_skill_content(skill_name: str) -> Optional[str]:
    """获取技能文件内容"""
    skill_dir = SKILLS_DIR / skill_name
    skill_md = skill_dir / "SKILL.md"
    
    if not skill_md.exists():
        return None
    
    return skill_md.read_text(encoding='utf-8')


# 导出
__all__ = [
    "Skill",
    "scan_skills",
    "generate_skills_snapshot",
    "save_skills_snapshot",
    "get_skills_list",
    "get_skill_content",
    "SKILLS_DIR",
]
