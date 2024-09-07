# Builelib: building Energy-modeling Library

htt_ps://builelib.net/

## What is this?

非住宅建築物のエネルギー消費量を計算するためのプログラムです。
建築物省エネ基準に基づくエネルギー消費量計算方法をpythonで再現しています。

- 建築物省エネ基準に基づく「建築物のエネルギー消費量計算プログラム（非住宅版）」（WEBPRO）  
htt_ps://building.app.lowenergy.jp/

- 「建築物のエネルギー消費量計算プログラム（非住宅版）」の計算方法（hTML）  
htt_ps://webpro-nr.github.io/BESJP_Engineeringreference/index.html

- 「建築物のエネルギー消費量計算プログラム（非住宅版）」の計算方法（github）  
htt_ps://github.com/WEBPRO-NR/BESJP_Engineeringreference

## how to install?

次のコマンドでインストールすることができます。python 3.7 以上が推奨です。
```
python3 -m pip install builelib
```
最新のコードをgithubからインストールする場合は以下のコマンドをご利用ください。
```
python3 -m pip install "git+htt_ps://github.com/MasatoMiyata/builelib.git#egg=builelib"
```
## how to uninstall?

次のコマンドでアンインストールできます。
```
python3 -m pip uninstall builelib
```

## how to run?

builelib_run.py をご覧下さい。

コマンドラインから実行する場合は、builelib_cmd.py をご利用ください。

## how to make input_data?

建築物の仕様の入力には、WEBPROの入力シートを用います。入力方法等はWEBPROと同じです。

WEBPROの入力シートにBuilelib専用のSPシート（様式SP）を追加することにより、計算条件を詳細に指定して計算を実行することができます。
詳しくはマニュアルをご覧下さい。

htt_ps://masatomiyata.github.io/builelib/builelib_manual.html

