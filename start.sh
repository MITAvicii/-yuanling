#!/bin/bash

# 源灵AI 一键启动脚本
# 自动清理端口占用并启动前后端服务

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

BACKEND_PORT=8002
FRONTEND_PORT=3000

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}       源灵AI 服务启动脚本${NC}"
echo -e "${BLUE}========================================${NC}"

# 检查并清理端口占用
kill_port() {
    local port=$1
    local service_name=$2
    
    # 查找占用端口的进程
    local pid=$(lsof -ti:$port 2>/dev/null || true)
    
    if [ -n "$pid" ]; then
        echo -e "${YELLOW}⚠ 端口 $port ($service_name) 被占用，正在清理...${NC}"
        kill -9 $pid 2>/dev/null || true
        sleep 1
        echo -e "${GREEN}✓ 端口 $port 已释放${NC}"
    fi
}

# 清理端口范围（处理 Next.js 自动切换端口的情况）
kill_port_range() {
    local start_port=$1
    local end_port=$2
    local service_name=$3
    
    for port in $(seq $start_port $end_port); do
        local pid=$(lsof -ti:$port 2>/dev/null || true)
        if [ -n "$pid" ]; then
            echo -e "${YELLOW}⚠ 端口 $port ($service_name) 被占用，正在清理...${NC}"
            kill -9 $pid 2>/dev/null || true
        fi
    done
}

# 清理残留的 next-server 进程
kill_next_processes() {
    local pids=$(pgrep -f "next-server" 2>/dev/null || true)
    if [ -n "$pids" ]; then
        echo -e "${YELLOW}⚠ 发现残留的 Next.js 进程，正在清理...${NC}"
        echo "$pids" | xargs kill -9 2>/dev/null || true
        echo -e "${GREEN}✓ Next.js 残留进程已清理${NC}"
    fi
}

# 清理残留的 uvicorn 进程
kill_uvicorn_processes() {
    local pids=$(pgrep -f "uvicorn.*app:app" 2>/dev/null || true)
    if [ -n "$pids" ]; then
        echo -e "${YELLOW}⚠ 发现残留的 uvicorn 进程，正在清理...${NC}"
        echo "$pids" | xargs kill -9 2>/dev/null || true
        echo -e "${GREEN}✓ uvicorn 残留进程已清理${NC}"
    fi
}

# 清理残留进程
kill_next_processes
kill_uvicorn_processes

# 清理端口
kill_port $BACKEND_PORT "后端"
kill_port_range 3000 3005 "前端"

# 再次确认端口可用
sleep 1
for port in $BACKEND_PORT $(seq 3000 3005); do
    if lsof -i:$port >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠ 端口 $port 仍被占用，强制清理${NC}"
        fuser -k $port/tcp 2>/dev/null || true
        sleep 1
    fi
done

echo ""

# 检查 conda 环境
if ! conda info --envs | grep -q "yuanling"; then
    echo -e "${RED}✗ conda 环境 'yuanling' 不存在${NC}"
    echo -e "${YELLOW}  请先创建环境: conda create -n yuanling python=3.10${NC}"
    exit 1
fi

# 检查 .env 文件
if [ ! -f "$BACKEND_DIR/.env" ]; then
    echo -e "${YELLOW}⚠ 未找到 .env 文件，正在从模板创建...${NC}"
    cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
    echo -e "${YELLOW}  请编辑 $BACKEND_DIR/.env 配置 API Key${NC}"
fi

# 检查 node_modules
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo -e "${YELLOW}⚠ 前端依赖未安装，正在安装...${NC}"
    cd "$FRONTEND_DIR"
    npm install --registry=https://registry.npmmirror.com
fi

echo -e "${BLUE}----------------------------------------${NC}"
echo -e "${GREEN}启动后端服务...${NC}"
echo -e "  端口: $BACKEND_PORT"
echo -e "  API 文档: http://localhost:$BACKEND_PORT/docs"
echo -e "${BLUE}----------------------------------------${NC}"
# 取消代理设置（解决飞书 SDK 代理问题）
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY all_proxy ALL_PROXY 2>/dev/null || true
export no_proxy="localhost,127.0.0.1,::1"
export NO_PROXY="localhost,127.0.0.1,::1"

# 启动后端（后台运行）
cd "$BACKEND_DIR"
# 启动后端（后台运行）
cd "$BACKEND_DIR"
# 使用 nohup 和 shell 激活 conda 环境来确保日志正确输出
nohup bash -c "source ~/anaconda3/etc/profile.d/conda.sh && conda activate yuanling && python app.py" > "$PROJECT_ROOT/backend.log" 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > "$PROJECT_ROOT/.backend.pid"
echo -e "${GREEN}✓ 后端服务已启动 (PID: $BACKEND_PID)${NC}"

# 等待后端启动
sleep 3

# 检查后端是否启动成功
if curl -s "http://localhost:$BACKEND_PORT/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ 后端服务运行正常${NC}"
else
    echo -e "${YELLOW}⚠ 后端服务启动中，请稍后检查日志: backend.log${NC}"
fi

echo ""
echo -e "${BLUE}----------------------------------------${NC}"
echo -e "${GREEN}启动前端服务...${NC}"
echo -e "  端口: $FRONTEND_PORT"
echo -e "  访问地址: http://localhost:$FRONTEND_PORT"
echo -e "${BLUE}----------------------------------------${NC}"

# 启动前端（后台运行）
cd "$FRONTEND_DIR"
npm run dev > "$PROJECT_ROOT/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > "$PROJECT_ROOT/.frontend.pid"
echo -e "${GREEN}✓ 前端服务已启动 (PID: $FRONTEND_PID)${NC}"

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✓ 源灵AI 服务启动完成！${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "访问地址:"
echo -e "  前端:  ${GREEN}http://localhost:$FRONTEND_PORT${NC}"
echo -e "  API:   ${GREEN}http://localhost:$BACKEND_PORT/docs${NC}"
echo ""
echo -e "日志文件:"
echo -e "  后端: $PROJECT_ROOT/backend.log"
echo -e "  前端: $PROJECT_ROOT/frontend.log"
echo ""
echo -e "停止服务: ${YELLOW}./stop.sh${NC}"
echo ""
