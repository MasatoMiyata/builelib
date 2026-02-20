<div align="center">

# 🏢 Builelib
### Building Energy-modeling Library

**非住宅建築物エネルギー消費量計算ライブラリ**

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)](https://github.com/MasatoMiyata/builelib)
[![uv](https://img.shields.io/badge/managed%20by-uv-7C3AED?logo=astral)](https://docs.astral.sh/uv/)

🌐 **Website / ウェブサイト:** https://builelib.net/

</div>

---

## 📖 What is this? / このライブラリについて

**English:**
Builelib is a Python library for calculating the annual energy consumption of non-residential buildings in accordance with Japan's Building Energy Conservation Standards (WEBPRO).

**日本語:**
非住宅建築物のエネルギー消費量を計算するためのプログラムです。
建築物省エネ基準に基づくエネルギー消費量計算方法を Python で再現しています。

---

### 🔗 References / 参考リンク

| リンク | 説明 |
|--------|------|
| [WEBPRO（非住宅版）](https://building.app.lowenergy.jp/) | 建築物のエネルギー消費量計算プログラム（非住宅版） / Building Energy Consumption Calculation Program |
| [Engineering Reference (HTML)](https://webpro-nr.github.io/BESJP_EngineeringReference/index.html) | 計算方法ドキュメント / Calculation Method Documentation |
| [Engineering Reference (GitHub)](https://github.com/WEBPRO-NR/BESJP_EngineeringReference) | 計算方法ソース / Calculation Method Source |

---

## ⚙️ Requirements

| ツール | バージョン |
|--------|------------|
| 🐍 Python | 3.12+ |
| 📦 [uv](https://docs.astral.sh/uv/) | Latest |

---

## 🚀 How to set up? / セットアップ方法

### 1. Install uv / uv のインストール

```bash
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Clone the repository / リポジトリのクローンと環境構築

```bash
git clone https://github.com/MasatoMiyata/builelib.git
cd builelib

# Install dependencies (virtual environment is created automatically)
# 依存関係のインストール（仮想環境の作成も自動で行われます）
uv sync
```

---

## ▶️ How to run? / 実行方法

**From the command line / コマンドラインから:**

```bash
uv run builelib <inputfile>          # Run calculation / 計算実行（デフォルト）
uv run builelib <inputfile> False    # Validate input only / 入力検証のみ
```

**Example / 実行例:**

```bash
uv run builelib ./examples/Builelib_inputSheet_sample_001.xlsx
```

**From a Python script / Python スクリプトから:**

```python
from builelib.runner import calculate

calculate("./examples/Builelib_inputSheet_sample_001.xlsx")
```

---

## 📝 How to make inputdata? / 入力データの作成方法

**English:**
Building specifications are entered using WEBPRO's input sheet, following the same procedure as WEBPRO.
By adding a Builelib-specific **SP sheet (Form SP)** to the WEBPRO input sheet, you can specify calculation conditions in detail.

**日本語:**
建築物の仕様の入力には、WEBPRO の入力シートを用います。入力方法は WEBPRO と同じです。
WEBPRO の入力シートに Builelib 専用の **SP シート（様式 SP）** を追加することにより、
計算条件を詳細に指定して計算を実行することができます。

📚 **Manual / マニュアル:** https://masatomiyata.github.io/builelib/builelib_manual.html

---

## 🗑️ How to uninstall? / アンインストール方法

```bash
# Delete the repository directory / リポジトリのディレクトリごと削除
rm -rf builelib/
```

---

<div align="center">

**© Masato Miyata** | [MIT License](https://opensource.org/licenses/MIT)

</div>
