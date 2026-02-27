import os
import json
import csv
import pandas as pd

def get_test_file_path(relative_path):
    """
    テストファイルの絶対パスを取得する。
    testsディレクトリを起点とした相対パスを渡し、絶対パスを返します。
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, relative_path)

def convert2number(x, default):
    """
    空欄やNaNをデフォルト値に変換し、数値をfloat型に変換する
    """
    if x == "" or pd.isna(x):
        return default
    try:
        return float(x)
    except (ValueError, TypeError):
        return default

def read_excel(filename, sheet_name="Sheet1", header=None):
    """
    Excelファイルを読み込む (pandas使用)
    xlrdの代わりにopenpyxlバックエンドを使用するため、.xlsxも同様に読み込めます。
    """
    # header=Noneで読み込み、リストのリストとして返す
    # dtype=objectで読み込むことで、予期せぬ型変換を防ぐ
    df = pd.read_excel(filename, sheet_name=sheet_name, header=header, dtype=object)
    
    # NaNを空文字列に変換して、既存のロジックとの互換性を保つ
    df = df.fillna("")
    return df.values.tolist()

def read_csv(filename, delimiter=',', encoding='shift-jis'):
    """
    CSV/TSVファイルを読み込む
    """
    with open(filename, mode='r', newline='', encoding=encoding) as f:
        reader = csv.reader(f, delimiter=delimiter)
        return [row for row in reader]

def read_json(filename):
    """
    JSONファイルを読み込む
    """
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)
