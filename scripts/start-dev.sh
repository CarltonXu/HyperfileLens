#!/bin/bash

# HyperFileLens 服务启动脚本
# 用于开发环境启动所有服务

set -e

echo "=================================================="
echo "   HyperFileLens Development Startup Script"
echo "=================================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="/workspace/projects"
LOG_DIR="/app/work/logs/bypass"

# 创建日志目录
mkdir -p $LOG_DIR

# 停止现有服务
echo -e "${YELLOW}Stopping existing services...${NC}"
pkill -f "runserver" 2>/dev/null || true
pkill -f "node server.cjs" 2>/dev/null || true
pkill -f "uvicorn gateway" 2>/dev/null || true
sleep 2

# 启动Redis服务
redis-server &

# 启动后端服务 (Django)
echo -e "${GREEN}Starting Backend (Django)...${NC}"
cd $PROJECT_ROOT/backend
# USE_POSTGRES=false python manage.py runserver 0.0.0.0:8000 > $LOG_DIR/backend.log 2>&1 &
USE_POSTGRES=false daphne -b 0.0.0.0 -p 8000 core.asgi:application > $LOG_DIR/backend.log 2>&1 &
sleep 3

# 检查后端是否启动
if ss -lptn 'sport = :8000' | grep -q LISTEN; then
    echo -e "${GREEN}✓ Backend running on http://localhost:8000${NC}"
else
    echo -e "${RED}✗ Backend failed to start${NC}"
    cat $LOG_DIR/backend.log | tail -20
fi

# 启动前端服务 (Vue)
echo -e "${GREEN}Building Frontend (Vue)...${NC}"
cd $PROJECT_ROOT/frontend
pnpm run build > $LOG_DIR/frontend-build.log 2>&1

echo -e "${GREEN}Starting Frontend (Vue)...${NC}"
node server.cjs > $LOG_DIR/frontend.log 2>&1 &
sleep 2

# 检查前端是否启动
if ss -lptn 'sport = :5000' | grep -q LISTEN; then
    echo -e "${GREEN}✓ Frontend running on http://localhost:5000${NC}"
else
    echo -e "${RED}✗ Frontend failed to start${NC}"
    cat $LOG_DIR/frontend.log | tail -20
fi

# 启动 Gateway 服务 (FastAPI) - 可选
if [ -d "$PROJECT_ROOT/gateway" ]; then
    echo -e "${GREEN}Starting Gateway (FastAPI)...${NC}"
    cd $PROJECT_ROOT/gateway
    if command -v uvicorn &> /dev/null; then
        uvicorn app.main:app --host 0.0.0.0 --port 8001 > $LOG_DIR/gateway.log 2>&1 &
        sleep 2
        if ss -lptn 'sport = :8001' | grep -q LISTEN; then
            echo -e "${GREEN}✓ Gateway running on http://localhost:8001${NC}"
        else
            echo -e "${YELLOW}⚠ Gateway failed to start (optional)${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ Gateway skipped (uvicorn not installed)${NC}"
    fi
fi

echo ""
echo "=================================================="
echo "   Services Status"
echo "=================================================="

# 显示服务状态
echo ""
echo "| Service    | Port  | Status | URL                     |"
echo "|------------|-------|--------|-------------------------|"

if ss -lptn 'sport = :8000' | grep -q LISTEN; then
    echo "| Backend    | 8000  | ✓      | http://localhost:8000   |"
else
    echo "| Backend    | 8000  | ✗      | -                       |"
fi

if ss -lptn 'sport = :5000' | grep -q LISTEN; then
    echo "| Frontend   | 5000  | ✓      | http://localhost:5000   |"
else
    echo "| Frontend   | 5000  | ✗      | -                       |"
fi

if ss -lptn 'sport = :8001' | grep -q LISTEN; then
    echo "| Gateway    | 8001  | ✓      | http://localhost:8001   |"
else
    echo "| Gateway    | 8001  | -      | (optional)              |"
fi

echo ""
echo "=================================================="
echo "   Login Credentials"
echo "=================================================="
echo "  Email:    admin@hyperfilelens.com"
echo "  Password: admin123"
echo "=================================================="
