"""
技能元数据 - 中文名称和分类映射
"""

# 技能中文名称和分类
SKILL_METADATA = {
    # === 后端框架专家 ===
    "django-expert": {
        "cn_name": "Django 专家",
        "category": "后端框架",
        "tags": ["Python", "Django", "Web开发"]
    },
    "django-api-developer": {
        "cn_name": "Django API 开发者",
        "category": "后端框架",
        "tags": ["Python", "Django", "REST API"]
    },
    "django-backend-expert": {
        "cn_name": "Django 后端专家",
        "category": "后端框架",
        "tags": ["Python", "Django", "后端"]
    },
    "django-orm-expert": {
        "cn_name": "Django ORM 专家",
        "category": "后端框架",
        "tags": ["Python", "Django", "数据库", "ORM"]
    },
    "fastapi-expert": {
        "cn_name": "FastAPI 专家",
        "category": "后端框架",
        "tags": ["Python", "FastAPI", "API"]
    },
    "rails-backend-expert": {
        "cn_name": "Rails 后端专家",
        "category": "后端框架",
        "tags": ["Ruby", "Rails", "后端"]
    },
    "rails-api-developer": {
        "cn_name": "Rails API 开发者",
        "category": "后端框架",
        "tags": ["Ruby", "Rails", "REST API"]
    },
    "rails-activerecord-expert": {
        "cn_name": "Rails ActiveRecord 专家",
        "category": "后端框架",
        "tags": ["Ruby", "Rails", "数据库", "ORM"]
    },
    "laravel-backend-expert": {
        "cn_name": "Laravel 后端专家",
        "category": "后端框架",
        "tags": ["PHP", "Laravel", "后端"]
    },
    "laravel-eloquent-expert": {
        "cn_name": "Laravel Eloquent 专家",
        "category": "后端框架",
        "tags": ["PHP", "Laravel", "数据库", "ORM"]
    },
    
    # === 前端框架专家 ===
    "react-nextjs-expert": {
        "cn_name": "React/Next.js 专家",
        "category": "前端框架",
        "tags": ["React", "Next.js", "SSR"]
    },
    "react-component-architect": {
        "cn_name": "React 组件架构师",
        "category": "前端框架",
        "tags": ["React", "组件设计", "架构"]
    },
    "vue-nuxt-expert": {
        "cn_name": "Vue/Nuxt 专家",
        "category": "前端框架",
        "tags": ["Vue", "Nuxt.js", "SSR"]
    },
    "vue-component-architect": {
        "cn_name": "Vue 组件架构师",
        "category": "前端框架",
        "tags": ["Vue", "组件设计", "架构"]
    },
    "tailwind-frontend-expert": {
        "cn_name": "Tailwind 前端专家",
        "category": "前端框架",
        "tags": ["Tailwind", "CSS", "样式"]
    },
    
    # === Python 专项专家 ===
    "python-expert": {
        "cn_name": "Python 专家",
        "category": "Python 专项",
        "tags": ["Python", "通用开发"]
    },
    "Python Testing Expert": {
        "cn_name": "Python 测试专家",
        "category": "Python 专项",
        "tags": ["Python", "测试", "质量保证"]
    },
    "python-testing-expert": {
        "cn_name": "Python 测试专家",
        "category": "Python 专项",
        "tags": ["Python", "测试", "质量保证"]
    },
    "Python Security Expert": {
        "cn_name": "Python 安全专家",
        "category": "Python 专项",
        "tags": ["Python", "安全", "加密"]
    },
    "python-security-expert": {
        "cn_name": "Python 安全专家",
        "category": "Python 专项",
        "tags": ["Python", "安全", "加密"]
    },
    "Python Performance Expert": {
        "cn_name": "Python 性能专家",
        "category": "Python 专项",
        "tags": ["Python", "性能优化", "并发"]
    },
    "python-performance-expert": {
        "cn_name": "Python 性能专家",
        "category": "Python 专项",
        "tags": ["Python", "性能优化", "并发"]
    },
    "Python Web Scraping Expert": {
        "cn_name": "Python 爬虫专家",
        "category": "Python 专项",
        "tags": ["Python", "爬虫", "数据提取"]
    },
    "python-web-scraping-expert": {
        "cn_name": "Python 爬虫专家",
        "category": "Python 专项",
        "tags": ["Python", "爬虫", "数据提取"]
    },
    "ml-data-expert": {
        "cn_name": "机器学习/数据专家",
        "category": "Python 专项",
        "tags": ["Python", "机器学习", "数据科学"]
    },
    
    # === 通用开发 ===
    "backend-developer": {
        "cn_name": "后端开发者",
        "category": "通用开发",
        "tags": ["后端", "通用"]
    },
    "frontend-developer": {
        "cn_name": "前端开发者",
        "category": "通用开发",
        "tags": ["前端", "通用"]
    },
    "api-architect": {
        "cn_name": "API 架构师",
        "category": "通用开发",
        "tags": ["API", "REST", "GraphQL"]
    },
    "performance-optimizer": {
        "cn_name": "性能优化专家",
        "category": "通用开发",
        "tags": ["性能", "优化"]
    },
    
    # === 工具类专家 ===
    "code-reviewer": {
        "cn_name": "代码审查专家",
        "category": "工具类",
        "tags": ["代码审查", "质量"]
    },
    "documentation-specialist": {
        "cn_name": "文档专家",
        "category": "工具类",
        "tags": ["文档", "README"]
    },
    "code-archaeologist": {
        "cn_name": "代码考古学家",
        "category": "工具类",
        "tags": ["代码分析", "遗留代码"]
    },
    
    # === 团队协作 ===
    "tech-lead-orchestrator": {
        "cn_name": "技术负责人",
        "category": "团队协作",
        "tags": ["架构", "技术领导"]
    },
    "team-configurator": {
        "cn_name": "团队配置器",
        "category": "团队协作",
        "tags": ["团队配置", "项目初始化"]
    },
    "project-analyst": {
        "cn_name": "项目分析师",
        "category": "团队协作",
        "tags": ["项目分析", "技术栈检测"]
    },
    
    # === 平台集成 ===
    "feishu": {
        "cn_name": "飞书集成",
        "category": "平台集成",
        "tags": ["飞书", "机器人", "消息"]
    },
    "get_weather": {
        "cn_name": "获取天气",
        "category": "平台集成",
        "tags": ["天气", "API"]
    },
}


# 分类顺序（用于排序显示）
CATEGORY_ORDER = [
    "团队协作",
    "后端框架", 
    "前端框架",
    "Python 专项",
    "通用开发",
    "工具类",
    "平台集成",
]


def get_skill_cn_name(skill_name: str) -> str:
    """获取技能中文名称"""
    metadata = SKILL_METADATA.get(skill_name, {})
    return metadata.get("cn_name", skill_name)


def get_skill_category(skill_name: str) -> str:
    """获取技能分类"""
    metadata = SKILL_METADATA.get(skill_name, {})
    return metadata.get("category", "其他")


def get_skill_tags(skill_name: str) -> list:
    """获取技能标签"""
    metadata = SKILL_METADATA.get(skill_name, {})
    return metadata.get("tags", [])


def get_skills_by_category() -> dict:
    """按分类获取技能"""
    from backend.graph.skills import get_skills_list
    
    skills = get_skills_list()
    categorized = {}
    
    for skill in skills:
        name = skill["name"]
        category = get_skill_category(name)
        
        if category not in categorized:
            categorized[category] = []
        
        categorized[category].append({
            **skill,
            "cn_name": get_skill_cn_name(name),
            "category": category,
            "tags": get_skill_tags(name),
        })
    
    # 按 CATEGORY_ORDER 排序
    sorted_categories = {}
    for cat in CATEGORY_ORDER:
        if cat in categorized:
            sorted_categories[cat] = categorized[cat]
    
    # 添加未在 ORDER 中的分类
    for cat, skills_list in categorized.items():
        if cat not in sorted_categories:
            sorted_categories[cat] = skills_list
    
    return sorted_categories


__all__ = [
    "SKILL_METADATA",
    "CATEGORY_ORDER",
    "get_skill_cn_name",
    "get_skill_category", 
    "get_skill_tags",
    "get_skills_by_category",
]
