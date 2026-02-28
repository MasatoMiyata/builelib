"""
database_loader.py
==================
builelibのデータベースJSONファイルを一括で読み込み、管理するモジュール。

設計方針
--------
* database/*.json が「正」のデータソース（Single Source of Truth）
* SPシートの追加データはここで一元的にマージする
* 多言語対応のインターフェース（get_valid_options）を将来の拡張用に用意する
* 各計算モジュールはこのモジュールが返す辞書を使うだけでよい

使用例
------
    from builelib import database_loader

    # 計算前に一度だけ呼ぶ
    db = database_loader.load_all_databases(inputdata.get("SpecialInputData", {}))

    # 各計算モジュールに渡す
    lighting.calc_energy(inputdata, db=db)
    ventilation.calc_energy(inputdata, db=db)

    # 有効な選択肢を取得（UI向け）
    options = database_loader.get_valid_options(db, "FLOWCONTROL")
"""

import json
import os
import copy

# このファイルと同じディレクトリにある database/ フォルダを参照する
_DB_DIR = os.path.dirname(os.path.abspath(__file__)) + "/database/"

# i18n翻訳ファイルの保存場所（将来の多言語対応用）
_I18N_DIR = os.path.dirname(os.path.abspath(__file__)) + "/i18n/"


# ---------------------------------------------------------------------------
# 公開インターフェース
# ---------------------------------------------------------------------------

def load_all_databases(special_input_data: dict = None) -> dict:
    """
    全データベースJSONを一括で読み込み、SPシートの追加データをマージして返す。

    Parameters
    ----------
    special_input_data : dict, optional
        inputdata["SpecialInputData"] の内容。
        SPシートで定義したカスタムデータ（flow_control, room_usage_condition 等）を含む。
        None または空辞書の場合は標準DBのみ返す。

    Returns
    -------
    dict
        キー = DB識別名、値 = マージ済みDB辞書。
        以下のキーを持つ:
            "FLOWCONTROL"           - 風量・流量制御特性（多項式係数）
            "HeatSourcePerformance" - 熱源機器の性能データ
            "lightingControl"       - 照明制御効果率
            "ventilationControl"    - 換気制御効果率
            "RoomUsageSchedule"     - 室使用スケジュール
            "ROOM_STANDARDVALUE"    - 室の基準値
            "CALENDAR"              - カレンダーパターン
    """
    if special_input_data is None:
        special_input_data = {}

    db = _load_base_databases()
    _apply_special_inputs(db, special_input_data)
    return db


def get_valid_options(db: dict, db_name: str, lang: str = "ja") -> list:
    """
    指定したデータベースのトップレベルキーを有効な選択肢リストとして返す。

    lang="ja"（デフォルト）ではDBのキー（日本語識別子）をそのまま返す。
    lang="en" 等では、各エントリの "label_{lang}" フィールドの値を返す。
    対応するラベルが存在しない場合は日本語キーをフォールバックとして使用する。

    翻訳は各DB JSONファイルのエントリ内に直接埋め込む方式（Single Source of Truth）。
    例: FLOWCONTROL.json の各エントリに "label_en": "..." を追加することで対応。

    Parameters
    ----------
    db : dict
        load_all_databases() の戻り値。
    db_name : str
        対象のDB識別名（例: "FLOWCONTROL", "lightingControl"）。
    lang : str, optional
        返す言語コード（デフォルト: "ja"）。
        "en" を指定すると各エントリの "label_en" フィールドを返す。

    Returns
    -------
    list[str]
        有効な選択肢の文字列リスト。

    Examples
    --------
        flow_options = get_valid_options(db, "FLOWCONTROL")
        # → ["定風量制御", "回転数制御", "回転数制御_2乗", "回転数制御_3乗", "定流量制御"]

        flow_options_en = get_valid_options(db, "FLOWCONTROL", lang="en")
        # → ["Constant Air Volume", "Variable Speed Drive", ...]
    """
    if db_name not in db:
        raise KeyError(f"DB '{db_name}' が database_loader に登録されていません。")

    entries = db[db_name]

    if lang == "ja":
        return list(entries.keys())

    # lang != "ja": 各エントリの label_{lang} を返す（なければキーをフォールバック）
    label_key = f"label_{lang}"
    return [
        v.get(label_key, k) if isinstance(v, dict) else k
        for k, v in entries.items()
    ]


def get_standard_value(special_input_data: dict) -> dict:
    """
    室の基準値データベースを読み込み、SPシートの室用途追加を適用して返す。

    commons.py の get_standard_value() を置き換えるもの。
    commons.py からはこの関数を呼ぶ形に移行する。

    Parameters
    ----------
    special_input_data : dict
        inputdata["SpecialInputData"] の内容。
        "room_usage_condition" キーを含む場合、カスタム室用途の基準値を追加する。

    Returns
    -------
    dict
        マージ済みの室基準値辞書。
    """
    with open(_DB_DIR + "common_room_standard_value.json", "r", encoding="utf-8") as f:
        standard_value = json.load(f)

    if special_input_data and "room_usage_condition" in special_input_data:
        for building_type in special_input_data["room_usage_condition"]:
            for room_type in special_input_data["room_usage_condition"][building_type]:
                base_room_type = special_input_data["room_usage_condition"][building_type][room_type]["ベースとする室用途"]
                standard_value[building_type][room_type] = copy.deepcopy(
                    standard_value[building_type][base_room_type]
                )

    return standard_value


# ---------------------------------------------------------------------------
# 内部実装
# ---------------------------------------------------------------------------

def _load_base_databases() -> dict:
    """
    標準のデータベースJSONファイルを全て読み込む（内部関数）。

    Returns
    -------
    dict
        キー = DB識別名、値 = JSONから読み込んだ辞書。
    """
    db_files = {
        "FLOWCONTROL":            "ac_flow_control.json",
        "HeatSourcePerformance":  "ac_heat_source_performance.json",
        "lightingControl":        "lt_lighting_control.json",
        "ventilationControl":     "vt_ventilation_control.json",
        "RoomUsageSchedule":      "common_room_usage_schedule.json",
        "ROOM_STANDARDVALUE":     "common_room_standard_value.json",
        "CALENDAR":               "common_calendar.json",
    }

    db = {}
    for key, filename in db_files.items():
        filepath = _DB_DIR + filename
        with open(filepath, "r", encoding="utf-8") as f:
            db[key] = json.load(f)

    return db


def _apply_special_inputs(db: dict, special_input_data: dict) -> None:
    """
    SPシート由来の追加データをDBにマージする（in-place）。

    各計算モジュールが個別に行っていたSP追加処理を、ここに集約する。
    新しいSP種別が増えた場合はこの関数を修正する。

    Parameters
    ----------
    db : dict
        _load_base_databases() が返した辞書（in-placeで変更される）。
    special_input_data : dict
        inputdata["SpecialInputData"] の内容。
    """

    # SP-AC-FC: 変風量・変流量制御特性（ac_flow_control.json に追加）
    # make_inputdata.py の行963-972 と同等の処理
    for control_name, params in special_input_data.get("flow_control", {}).items():
        db["FLOWCONTROL"][control_name] = params

    # SP-RT-UC: 室使用条件（common_room_usage_schedule.json に追加）
    # 各計算モジュールの calc_energy() 冒頭で行っていた処理と同等
    if "room_usage_condition" in special_input_data:
        for building_type in special_input_data["room_usage_condition"]:
            for room_type in special_input_data["room_usage_condition"][building_type]:
                db["RoomUsageSchedule"][building_type][room_type] = \
                    special_input_data["room_usage_condition"][building_type][room_type]

    # SP カレンダー（common_calendar.json に追加）
    # 各計算モジュールの calc_energy() 冒頭で行っていた処理と同等
    for pattern_name, pattern_data in special_input_data.get("calender", {}).items():
        db["CALENDAR"][pattern_name] = pattern_data


def _load_translations(lang: str) -> dict:
    """
    指定言語の翻訳テーブルを読み込む（内部関数）。

    Phase B（DBキー英語化）以降に本格活用する。
    翻訳ファイルが存在しない場合は空辞書を返す。

    Parameters
    ----------
    lang : str
        言語コード（例: "en", "ja"）。

    Returns
    -------
    dict
        翻訳テーブル辞書。ファイルがなければ空辞書。
    """
    filepath = _I18N_DIR + f"{lang}.json"
    if not os.path.exists(filepath):
        return {}
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)
