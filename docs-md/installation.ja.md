
Builelibはpythonでコーディングされています。コマンドラインで実行することも可能です。

<BR>
次のコマンドでインストールすることができます。python 3.12 以上が推奨です。
```
python3 -m pip install "git+https://github.com/MasatoMiyata/builelib.git#egg=builelib"
```

<BR>
pythonスクリプト上で次のように記せば、計算を実行できます。

```
# ファイル名の指定
file_name = "./sample/Builelib_inputSheet_sample_001.xlsx"

# 計算の実行
builelib_run(True, file_name)
```

<BR>
コマンドラインから実行する場合は、builelib_cmd.py をご利用ください。
```
python -m builelib_cmd True ./sample/Builelib_inputSheet_sample_001.xlsm
```

