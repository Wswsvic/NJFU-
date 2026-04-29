FROM python:3.11-slim

# 安装 Chrome 依赖
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 设置环境变量
ENV HEADLESS=true
ENV CHROME_BIN=/usr/bin/chromium

CMD ["python", "-m", "src.cli.main"]