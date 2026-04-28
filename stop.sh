#!/bin/bash

# 源灵AI 一键停止脚本
# 停止前后端服务并清理端口

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND_PORT=8002
FRONTEND_PORT=3000

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}       源灵AI 服务停止脚本${NC}"
echo -e "${BLUE}========================================${NC}"

# 通过 PID 文件停止进程
stop_by_pid_file() {
    local pid_file=$1
    local service_name=$2
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 $pid 2>/dev/null; then
            echo -e "${YELLOW}停止 $service_name (PID: $pid)...${NC}"
            kill $pid 2>/dev/null || true
            rm -f "$pid_file"
            echo -e "${GREEN}✓ $service_name 已停止${NC}"
        else
            echo -e "${YELLOW}$service_name 进程不存在，清理 PID 文件${NC}"
            rm -f "$pid_file"
        fi
    fi
}

# 通过端口停止进程
stop_by_port() {
    local port=$1
    local service_name=$2
    
    local pid=$(lsof -ti:$port 2>/dev/null || true)
    
    if [ -n "$pid" ]; then
        echo -e "${YELLOW}停止 $service_name (端口: $port, PID: $pid)...${NC}"
        kill -9 $pid 2>/dev/null || true
        echo -e "${GREEN}✓ $service_name 已停止${NC}"
    fi
}

# 清理端口范围（处理 Next.js 自动切换端口的情况）
stop_port_range() {
    local start_port=$1
    local end_port=$2
    local service_name=$3
    
    for port in $(seq $start_port $end_port); do
        local pid=$(lsof -ti:$port 2>/dev/null || true)
        if [ -n "$pid" ]; then
            echo -e "${YELLOW}清理 $service_name (端口: $port, PID: $pid)...${NC}"
            kill -9 $pid 2>/dev/null || true
        fi
    done
}

# 清理残留的 next-server 进程
kill_next_processes() {
    local pids=$(pgrep -f "next-server" 2>/dev/null || true)
    if [ -n "$pids" ]; then
        echo -e "${YELLOW}清理残留的 Next.js 进程 (PID: $pids)...${NC}"
        echo "$pids" | xargs kill -9 2>/dev/null || true
        echo -e "${GREEN}✓ Next.js 残留进程已清理${NC}"
    fi
}

# 清理残留的 uvicorn 进程
kill_uvicorn_processes() {
    local pids=$(pgrep -f "uvicorn.*app:app" 2>/dev/null || true)
    if [ -n "$pids" ]; then
        echo -e "${YELLOW}清理残留的 uvicorn 进程 (PID: $pids)...${NC}"
        echo "$pids" | xargs kill -9 2>/dev/null || true
        echo -e "${GREEN}✓ uvicorn 残留进程已清理${NC}"
    fi
}

# 先通过 PID 文件停止
stop_by_pid_file "$PROJECT_ROOT/.backend.pid" "后端服务"
stop_by_pid_file "$PROJECT_ROOT/.frontend.pid" "前端服务"

# 再通过端口确保清理干净
stop_by_port $BACKEND_PORT "后端服务"
stop_port_range 3000 3005 "前端服务"

# 清理残留进程
kill_next_processes
kill_uvicorn_processes

# 最终确认端口已释放
sleep 1
for port in $BACKEND_PORT $(seq 3000 3005); do
    if lsof -i:$port >/dev/null 2>&1; then
        echo -e "${RED}⚠ 端口 $port 仍被占用，强制清理${NC}"
        fuser -k $port/tcp 2>/dev/null || true
    fi
done

echo ""
echo -e "${GREEN}✓ 所有服务已停止${NC}"
echo ""
