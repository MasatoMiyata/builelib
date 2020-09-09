# Builelib: Building Energy-modeling Library

## What is this?

非住宅建築物のエネルギー消費量を計算するためのプログラムです。
建築物省エネ基準に基づくエネルギー消費量計算方法をpythonで再現しています。

- 建築物省エネ基準に基づく「建築物のエネルギー消費量計算プログラム（非住宅版）」（WEBPRO）
https://building.app.lowenergy.jp/

- 「建築物のエネルギー消費量計算プログラム（非住宅版）」の計算方法（HTML）
https://webpro-nr.github.io/BESJP_EngineeringReference/index.html

- 「建築物のエネルギー消費量計算プログラム（非住宅版）」の計算方法（github）
https://github.com/WEBPRO-NR/BESJP_EngineeringReference

## How to install?

次のコマンドでインストールすることができます。python 3.7 以上が推奨です。
```
python3 -m pip install builelib
```

## How to run?

付属の Jupyter Notebook（run.ipynb）をご覧下さい。


## How to make inputdata?

建築物の仕様の入力には、WEBPROの入力シートを用います。
入力方法等はWEBPROと同じです。

- WEBPROの入力シート（外皮・設備仕様入力シート_Ver2用）
https://www.kenken.go.jp/becc/index.html#5-2

- 入力シートの作成方法（エネルギー消費性能計算プログラム（非住宅版）Ver.2 の入力マニュアル）
https://www.kenken.go.jp/becc/building.html#1-2

