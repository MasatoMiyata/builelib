<div align="center">

# 🏢 Builelib

### Building Energy-modeling Library

**非住宅建築物エネルギー消費量計算プログラム**

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-2.1.0-blue.svg)](https://github.com/MasatoMiyata/builelib)
[![uv](https://img.shields.io/badge/managed%20by-uv-7C3AED?logo=astral)](https://docs.astral.sh/uv/)

[English](README.md) | [ウェブサイト](https://builelib.net/) | [マニュアル](https://builelib.net/manual/)

</div>

## 概要

Builelibは、非住宅建築物の年間エネルギー消費量を計算するPythonライブラリです。
建築物省エネ基準に基づくWEBPRO（非住宅版）の計算方法をPythonで再現しています。

Excel入力シートを使用するCLIのほか、Python API、JSONを使用するFastAPI、Dockerによる実行に対応しています。

## 動作環境

- Python 3.12以上
- [uv](https://docs.astral.sh/uv/)
- Git
- Docker（コンテナで実行する場合のみ）

## セットアップ

### 1. uvのインストール

Windows PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

macOS / Linux:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. リポジトリと依存関係の準備

```bash
git clone https://github.com/MasatoMiyata/builelib.git
cd builelib
uv sync --locked
```

`uv sync` により、仮想環境 `.venv` の作成と依存関係のインストールが行われます。`--locked` は、コミットされている `uv.lock` の内容を変更せずに使用します。

## CLIで実行する

### 計算を実行する

```bash
uv run builelib <inputfile>
```

`<inputfile>` は実際の `.xlsx` または `.xlsm` ファイルのパスに置き換えます。括弧 `< >` 自体は入力しません。

リポジトリ付属のサンプルを実行する例:

```bash
uv run builelib ./examples/Builelib_inputSheet_sample_001.xlsx
```

パスに空白が含まれる場合は引用符で囲みます。

```powershell
uv run builelib "C:\path with spaces\input.xlsx"
```

### 入力検証のみ実行する

第2引数に `False` を指定すると、エネルギー計算を行わず、Excelの読み込みと入力検証のみを実行します。

```bash
uv run builelib <inputfile> False
```

入力検証のみの場合も、入力データ、検証結果、設備別結果およびZIPファイルが出力されます。

### 出力ファイル

結果は入力Excelファイルと同じディレクトリに出力されます。既存の同名ファイルは上書きされます。

| 出力名 | 内容 |
|---|---|
| `<name>_input.json` | Excelから変換した入力データ |
| `<name>_validation.json` | 入力検証結果 |
| `<name>_result.json` | BEIなどの計算結果 |
| `<name>_result_*.json` | 設備別の計算結果 |
| `<name>_result_*.csv` | 設備別・時系列などの詳細結果（通常計算時） |
| `<name>.zip` | 主な出力ファイルをまとめたZIP |

## Pythonから実行する

### Excelファイルを計算する

```python
from builelib.runner import calculate

calculate("./examples/Builelib_inputSheet_sample_001.xlsx")
```

`calculate()` は結果を返すのではなく、入力Excelファイルと同じディレクトリへJSON、CSV、ZIPを出力します。入力検証のみを行う場合は、第2引数に `False` を指定します。

```python
calculate("./examples/Builelib_inputSheet_sample_001.xlsx", False)
```

### JSONデータをメモリ上で計算する

`calculate_from_json()` はwebproJsonSchema準拠の辞書を受け取り、ファイルを作成せずに結果を辞書で返します。

```python
from builelib.runner import calculate_from_json

output = calculate_from_json(input_data)
print(output["result"])
print(output["errors"])
```

## Web APIを起動する

ローカル開発サーバーを起動します。

```bash
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

起動後、次のURLでAPI仕様と対話型ドキュメントを確認できます。

- Swagger UI: <http://127.0.0.1:8000/docs>
- ReDoc: <http://127.0.0.1:8000/redoc>

主なエンドポイント:

| メソッド | パス | 内容 |
|---|---|---|
| `GET` | `/` | 稼働確認 |
| `GET` | `/calculate` | サーバー上のExcelファイルを計算 |
| `POST` | `/calculate` | JSON入力データを計算 |
| `POST` | `/validate` | JSON入力データを検証 |
| `GET` | `/schema` | JSONスキーマを取得 |
| `GET` | `/options` | 入力値の選択肢を取得 |
| `POST` | `/project/{project_id}/save` | プロジェクトを保存 |
| `GET` | `/project/{project_id}` | プロジェクトを読み込み |

## Dockerで起動する

`compose.yaml` は外部volumeと外部networkを使用します。初回のみ作成してください。

```bash
docker volume create builelib_data
docker network create mynetwork
```

イメージをビルドして起動します。

```bash
docker compose up --build -d
```

起動後のAPIドキュメントは <http://localhost:8081/docs> です。

停止する場合:

```bash
docker compose down
```

外部volume `builelib_data` は `docker compose down` では削除されません。

## 入力データの作成

建築物仕様の入力にはWEBPROの入力シートを使用します。入力方法はWEBPROと同じです。

WEBPRO入力シートにBuilelib専用の **SPシート（様式SP）** を追加すると、計算条件を詳細に指定できます。サンプルは [`examples`](examples/) にあります。

詳しくは[マニュアル](https://builelib.net/manual/)を参照してください。

## テスト

```bash
uv run python -m pytest tests
```

特定のテストだけを実行する例:

```bash
uv run python -m pytest tests/test_api.py -v
```

## 開発環境の削除

Builelibはリポジトリ内の `.venv` にインストールされます。開発環境が不要になった場合は、リポジトリの親ディレクトリへ移動して `builelib` ディレクトリを削除します。

Windows PowerShell:

```powershell
cd ..
Remove-Item -Recurse -Force .\builelib
```

macOS / Linux:

```bash
cd ..
rm -rf ./builelib
```

## 参考資料

- [WEBPRO（非住宅版）](https://building.app.lowenergy.jp/)
- [計算方法ドキュメント](https://webpro-nr.github.io/BESJP_EngineeringReference/index.html)
- [計算方法ソース](https://github.com/WEBPRO-NR/BESJP_EngineeringReference)

## ライセンス

[MIT License](LICENSE)

© Masato Miyata
