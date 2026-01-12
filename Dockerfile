# Conflict Genesis - Google Cloud Run Dockerfile
# 使用 Python 3.11 slim 作為基礎映像

FROM python:3.11-slim

# 設置環境變數
ENV PYTHONUNBUFFERED=True
ENV APP_HOME=/app
ENV PORT=8080

# 設置工作目錄
WORKDIR $APP_HOME

# 安裝系統依賴 (pydub 需要 ffmpeg)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 複製 requirements 並安裝依賴 (利用 Docker 緩存)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式代碼
COPY . ./

# 創建必要的目錄
RUN mkdir -p uploads reports generated_images .audio_temp

# 暴露端口
EXPOSE 8080

# 使用 Gunicorn 啟動應用 (適合 Cloud Run)
# --timeout 0 允許長時間請求 (AI 生成需要)
# --workers 1 單一工作進程 (Cloud Run 建議)
# --threads 8 多線程處理並發
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 web_app:app
