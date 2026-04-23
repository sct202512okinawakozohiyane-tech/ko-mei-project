FROM python:3.11-slim

# 作業場所
WORKDIR /workspace

# 最低限のツール
RUN apt-get update && \
    apt-get install -y curl && \
    rm -rf /var/lib/apt/lists/*

# 必要なPythonライブラリ
RUN pip install --no-cache-dir requests flask

# コンテナを落とさない（今まで通り）
CMD ["sleep", "infinity"]
