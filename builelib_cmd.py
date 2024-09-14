# builelib_cmd.py
# -----------------------------------------------------------------------------
# buileibをコマンドラインで実行するプログラム
# -----------------------------------------------------------------------------
# 使用方法
# % python -m builelib_cmd (実行モード) (入力シートファイル名)
#
# 使用例
# % python -m builelib_cmd True ./sample/WEBPRO_inputSheet_sample.xlsm
# -----------------------------------------------------------------------------
import sys

from builelib_run import builelib_run

if len(sys.argv) <= 2:
    raise Exception("引数が適切に指定されていません")
else:
    exec_calculation = bool(sys.argv[1])  # 計算の実行 （True: 計算も行う、 False: 計算は行わない）
    input_file_name = str(sys.argv[2])  # 入力ファイル指定
    # 実行
    builelib_run(exec_calculation, input_file_name)
