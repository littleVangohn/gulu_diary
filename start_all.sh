#!/bin/bash

echo "🛑 1. 正在清理旧微服务进程..."
pkill -f server.py
pkill -f gunicorn
pkill -f module_validator.py
pkill -f module_writer.py
pkill -f module_logger.py
sleep 2 

echo "🚀 2. 正在启动微服务集群 (启用 Gunicorn 原生多线程网关)..."

# 先启动下游消费者
nohup python3 -u module_logger.py > logger.log 2>&1 &
nohup python3 -u module_writer.py > writer.log 2>&1 &
nohup python3 -u module_validator.py > validator.log 2>&1 &

echo "⏳ 等待下游节点准备就绪 (2秒)..."
sleep 2

# 🌟 核心升级：使用 gthread 原生线程引擎，彻底告别 Zope Bug！
# 🌟 核心升级：使用 Uvicorn 驱动 FastAPI，开启 4 个纯异步进程！
nohup uvicorn server:app --host 0.0.0.0 --port 5000 --workers 4 > gateway.log 2>&1 &

echo "✅ 3. 所有节点已成功启动！工业级高并发网关已上线！"