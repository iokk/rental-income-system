# 1) 选择轻量镜像：python:3.11-slim
FROM python:3.11-slim

# 2) 基础系统依赖（证书、时区、常见构建工具）
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates tzdata \
    && rm -rf /var/lib/apt/lists/*

# 可选：设置默认时区（按需修改）
ENV TZ=Asia/Shanghai

# 3) 工作目录
WORKDIR /app

# 4) 复制依赖清单并安装（先拷贝 requirements 有利于缓存）
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 5) 复制项目文件
COPY app.py /app/app.py
COPY .streamlit /app/.streamlit

# 6) 暴露容器内部端口（文档性，Zeabur 会用 $PORT 映射）
EXPOSE 8501

# 7) 健康检查（容器启动后，探测网页可用）
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:${PORT:-8501}/_stcore/health || exit 1

# 8) 启动命令：读取 $PORT，绑定 0.0.0.0
CMD bash -lc 'streamlit run app.py --server.address=0.0.0.0 --server.port ${PORT:-8501}'
