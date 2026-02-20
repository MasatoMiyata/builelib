# Builelib: Building Energy-modeling Library

https://builelib.net/

## What is this?

非住宅建築物のエネルギー消費量を計算するためのプログラムです。
建築物省エネ基準に基づくエネルギー消費量計算方法を Python で再現しています。

- 建築物省エネ基準に基づく「建築物のエネルギー消費量計算プログラム（非住宅版）」（WEBPRO）
  https://building.app.lowenergy.jp/

- 「建築物のエネルギー消費量計算プログラム（非住宅版）」の計算方法（HTML）
  https://webpro-nr.github.io/BESJP_EngineeringReference/index.html

- 「建築物のエネルギー消費量計算プログラム（非住宅版）」の計算方法（github）
  https://github.com/WEBPRO-NR/BESJP_EngineeringReference

## Requirements

- Python 3.12
- [uv](https://docs.astral.sh/uv/)

## How to set up?

### 1. uv のインストール

```bash
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. リポジトリのクローンと環境構築

```bash
git clone https://github.com/MasatoMiyata/builelib.git
cd builelib

# 依存関係のインストール（仮想環境の作成も自動で行われます）
uv sync
```

## How to run?

コマンドラインから実行する場合:

```bash
uv run builelib <inputfile>              # 計算あり（デフォルト）
uv run builelib <inputfile> False        # 計算なし（入力検証のみ）
```

例:

```bash
uv run builelib ./examples/Builelib_inputSheet_sample_001.xlsx
```

Python スクリプトから呼び出す場合:

```python
from builelib.runner import calculate

calculate("./examples/Builelib_inputSheet_sample_001.xlsx")
```

## How to make inputdata?

建築物の仕様の入力には、WEBPRO の入力シートを用います。入力方法等は WEBPRO と同じです。

WEBPRO の入力シートに Builelib 専用の SP シート（様式 SP）を追加することにより、
計算条件を詳細に指定して計算を実行することができます。
詳しくはマニュアルをご覧下さい。

https://masatomiyata.github.io/builelib/builelib_manual.html


## How to uninstall?

```bash
# リポジトリのディレクトリごと削除してください
rm -rf builelib/
```
