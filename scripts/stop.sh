#!/bin/bash

# HyperFileLens 服务停止脚本

echo "=================================================="
echo "   HyperFileLens Stop Script"
echo "=================================================="

# 停止所有服务
echo "Stopping services..."

pkill -f "runserver" 2>/dev/null && echo "✓ Backend stopped" || echo "  Backend was not running"
pkill -f "node server.cjs" 2>/dev/null && echo "✓ Frontend stopped" || echo "  Frontend was not running"
pkill -f "uvicorn gateway" 2>/dev/null && echo "✓ Gateway stopped" || echo "  Gateway was not running"

echo ""
echo "All services stopped."
