"""
Fetch URL 工具 - 网页内容获取
"""

import re
from typing import Optional

import httpx
from bs4 import BeautifulSoup
import html2text
from langchain_core.tools import tool
from pydantic import BaseModel, Field


class FetchURLInput(BaseModel):
    """Fetch URL 工具输入参数"""
    url: str = Field(
        ...,
        description="要获取的网页 URL，必须以 http:// 或 https:// 开头",
        examples=["https://example.com", "https://news.ycombinator.com"]
    )


def clean_html(html_content: str, url: str = "") -> str:
    """
    清洗 HTML 内容，转换为 Markdown 格式
    
    Args:
        html_content: 原始 HTML 内容
        url: 源 URL（用于解析相对链接）
        
    Returns:
        清洗后的 Markdown 文本
    """
    # 使用 BeautifulSoup 解析 HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 移除不需要的标签
    for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
        tag.decompose()
    
    # 移除注释
    for comment in soup.find_all(string=lambda text: isinstance(text, str) and text.strip().startswith('<!--')):
        comment.extract()
    
    # 获取主要内容
    # 尝试找到主要内容区域
    main_content = (
        soup.find('main') or 
        soup.find('article') or 
        soup.find('div', class_=re.compile(r'content|main|article', re.I)) or
        soup.find('body') or
        soup
    )
    
    # 使用 html2text 转换为 Markdown
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = True  # 忽略图片以减少 token
    h.ignore_emphasis = False
    h.body_width = 0  # 不自动换行
    h.unicode_snob = True
    
    markdown = h.handle(str(main_content))
    
    # 清理多余空白
    markdown = re.sub(r'\n{3,}', '\n\n', markdown)
    markdown = markdown.strip()
    
    # 限制长度（防止 token 过多）
    max_length = 10000
    if len(markdown) > max_length:
        markdown = markdown[:max_length] + "\n\n...[内容过长已截断]"
    
    return markdown


@tool("fetch_url", args_schema=FetchURLInput)
def fetch_url_tool(url: str) -> str:
    """
    获取指定 URL 的网页内容，并清洗为 Markdown 格式。
    
    用于获取网页内容、API 数据等。
    自动清洗 HTML，返回可读的文本内容。
    
    重要：必须提供 url 参数！
    示例：fetch_url(url="https://example.com")
    
    Args:
        url: 要获取的网页 URL（必需参数，必须以 http:// 或 https:// 开头）
        
    Returns:
        网页内容（Markdown 格式）或错误信息
    """
    # 验证 URL
    if not url.startswith(('http://', 'https://')):
        return f"错误：无效的 URL，必须以 http:// 或 https:// 开头"
    
    try:
        # 发送请求
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            response = client.get(
                url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            )
            response.raise_for_status()
        
        # 获取内容类型
        content_type = response.headers.get('content-type', '')
        
        # 如果是 JSON API
        if 'application/json' in content_type:
            return f"JSON 响应:\n{response.text}"
        
        # 如果是纯文本
        if 'text/plain' in content_type:
            return f"文本内容:\n{response.text[:10000]}"
        
        # 如果是 HTML
        if 'text/html' in content_type or 'application/xhtml' in content_type:
            markdown = clean_html(response.text, url)
            return f"网页内容 ({url}):\n\n{markdown}"
        
        # 其他类型
        return f"内容类型: {content_type}\n内容长度: {len(response.content)} 字节"
        
    except httpx.TimeoutException:
        return f"错误：请求超时（超过30秒）"
    except httpx.HTTPStatusError as e:
        return f"错误：HTTP 错误 - {e.response.status_code}"
    except Exception as e:
        return f"错误：获取网页时发生异常 - {str(e)}"


# 导出工具
FETCH_URL_TOOL = fetch_url_tool
