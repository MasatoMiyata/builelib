# ---- Stage 1: builder ----
FROM python:3.12-slim AS builder

WORKDIR /app

# uv のインストール
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 依存ファイルのコピー（ここまでをキャッシュ層として活用）
# README.md は hatchling のビルドに必要
COPY pyproject.toml uv.lock README.md ./

# 仮想環境を /app/.venv に作成し、プロジェクト本体を除く依存のみインストール
RUN uv sync --frozen --no-dev --no-install-project

# パッケージ本体をコピーしてインストール
COPY src/ ./src/
RUN uv sync --frozen --no-dev

# ---- Stage 2: runtime ----
FROM python:3.12-slim AS runtime

WORKDIR /app

# builder から必要なものだけコピー（uv 自体は含まない）
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY main.py ./

# climatedata は git 管理対象のため、上の COPY src/ で自動的に含まれる

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8080

# エントリポイント（起動時に共有ボリュームの権限を修正）
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
ENTRYPOINT ["docker-entrypoint.sh"]

# Apache と同じ www-data (UID/GID 33) で実行することで、
# 書き出したファイルを Apache 側から mv できるようにする
USER www-data

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
