#!/bin/bash
set -e

# 共有ボリュームに全ユーザーの読み書き権限を付与
# （Apache=www-data がファイルを mv するため）
chmod 1777 /usr/src/data 2>/dev/null || true

exec "$@"
