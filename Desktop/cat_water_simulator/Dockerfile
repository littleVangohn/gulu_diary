# Dockerfile
FROM python:3.10-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY core/ ./core/
COPY run_headless.py .

# 设置默认命令
CMD ["python", "run_headless.py"]