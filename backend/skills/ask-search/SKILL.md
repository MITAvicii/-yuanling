---
name: ask-search
description: "自托管网页搜索工具。基于 SearxNG 聚合 Google、Bing、DuckDuckGo 等 70+ 搜索引擎。无需 API Key，完全隐私。"
---

# ask-search 网络搜索

自托管的网页搜索工具，基于 SearxNG meta 搜索引擎。聚合 Google、Bing、DuckDuckGo、Brave 等 70+ 搜索源。

## 前置条件

确保 SearxNG 服务运行在 `http://localhost:8080`。

## 使用方法

通过 terminal 工具执行命令：

```bash
ask-search "搜索关键词"
```

## 参数说明

| 参数 | 说明 | 示例 |
|------|------|------|
| `--num N` 或 `-n` | 结果数量，默认10 | `ask-search "AI" -n 5` |
| `--lang` 或 `-l` | 语言过滤 | `ask-search "news" -l zh-CN` |
| `--categories` 或 `-c` | 分类筛选 | `ask-search "tech" -c news` |
| `--engines` 或 `-e` | 指定搜索引擎 | `ask-search "test" -e google,brave` |
| `--urls-only` 或 `-u` | 仅返回URL | `ask-search "query" -u` |
| `--json` 或 `-j` | JSON 原始输出 | `ask-search "query" -j` |

## 工作流程

1. **搜索候选**：执行 `ask-search "话题"` 获取 URL 列表和摘要
2. **判断是否足够**：如果摘要已包含足够信息，直接回答
3. **深度抓取**：如果需要完整内容，使用 `web_fetch` 获取 URL 对应页面

## 示例

```bash
# 基本搜索
ask-search "AI news 2026"

# 限制结果数量
ask-search "Python tips" -n 5

# 中文结果
ask-search "最新科技新闻" -l zh-CN

# 新闻分类
ask-search "GPT-5" -c news

# 仅获取URL列表
ask-search "tutorial" -u
```

## 注意事项

- 搜索结果来自搜索引擎索引，部分网站（如 Reddit、知乎）可能无法直接抓取完整内容
- 如需抓取受限网站，可使用 archive.org 缓存或 SOCKS 代理
