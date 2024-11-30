# ベースイメージ
FROM python:3.12-slim

# 作業ディレクトリを設定
WORKDIR /app

# 必要なパッケージをインストール
RUN apt-get update && apt-get install -y --no-install-recommends \
    # nvidia-utils-530 && \
    procps && \
    rm -rf /var/lib/apt/lists/*

# アプリケーションコードと依存ファイルをコピー
COPY gpu_exporter.py /app/gpu_exporter.py
COPY requirements.txt /app/requirements.txt

# Python依存パッケージをインストール
RUN pip install --no-cache-dir -r requirements.txt

# GPU対応のランタイムを設定
ENV NVIDIA_VISIBLE_DEVICES all
ENV NVIDIA_DRIVER_CAPABILITIES compute,utility

# コンテナ実行時のデフォルトコマンド
CMD ["python", "gpu_exporter.py"]
