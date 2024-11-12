# 基础镜像
FROM python:3.12.7-bookworm as base

ARG BUILD_DATE

ENV BUILD_DATE ${BUILD_DATE}

# 更新apt包管理器并安装必要的依赖
RUN apt update -y && \
    apt install -y --no-install-recommends bash build-essential libffi-dev libssl-dev && \
    apt clean all && \
    rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制requirements.txt到镜像中
COPY requirements.txt .

# 安装Python依赖
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    # 清理pip缓存以减少镜像大小
    rm -rf /root/.cache/pip

RUN playwright install chromium && \
    playwright install-deps

FROM base

LABEL build_date=${BUILD_DATE}

WORKDIR /app

# 复制目录到镜像中
COPY . .

# 设置工作目录
WORKDIR /app

# 设置入口点
CMD ["sh", "-c", "python MT-AutoCheckIn.py"]
