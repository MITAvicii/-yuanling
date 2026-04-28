# 上传项目到 GitHub

将本地项目初始化并推送到 GitHub 仓库。

## 适用场景

- 首次将本地项目上传到 GitHub
- 项目包含大文件需要排除

## 流程

### 1. 分析项目结构

```bash
# 查看项目大小
du -sh 项目目录/*

# 找出大文件/目录
du -sh 项目目录/* | sort -rh | head -20
```

### 2. 配置 .gitignore

排除大文件和不必要上传的内容：

```
# Logs
*.log

# Documents
*.docx
*.pdf

# Environment
.env
.env.local
.env.example
backend/.env*

# Python
__pycache__/
*.py[cod]

# Models (大型模型文件)
backend/models/

# Build outputs
frontend/.next/
frontend/out/

# Node modules
frontend/node_modules/

# Sessions (用户数据)
backend/sessions/

# Memory (用户数据)
backend/memory/
```

### 3. 初始化 Git

```bash
cd 项目目录
git init
git add -A
git commit -m "initial commit"
```

### 4. 推送到 GitHub

```bash
# 添加远程仓库
git remote add origin https://github.com/用户名/仓库名.git

# 推送
git branch -M main
git push -u origin main
```

如需强制覆盖远程：

```bash
git push origin main --force
```

## 注意事项

- 确保 `.env` 文件已添加到 `.gitignore`，避免泄露 API 密钥
- 大型模型文件 (~GB) 应排除
- 用户会话数据应排除以保护隐私