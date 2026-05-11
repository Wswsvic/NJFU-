FROM python:3.11-slim

# 1. 替换为阿里云 apt 源（Debian Bookworm格式）
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources \
    && sed -i 's|security.debian.org/debian-security|mirrors.aliyun.com/debian-security|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
       chromium \
       chromium-driver \
       tini \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com

COPY . .

# 设置环境变量
ENV HEADLESS=true
ENV CHROME_BIN=/usr/bin/chromium

EXPOSE 8000

# 使用 tini 作为 init 进程，它负责收割所有的僵尸孤儿进程
ENTRYPOINT ["/usr/bin/tini", "--"]

CMD ["uvicorn", "web.main:app", "--host", "0.0.0.0", "--port", "8000"]
