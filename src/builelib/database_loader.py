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
            "AnnualSolarLevel"      - 日射地域区分と気象ファイル名の対応
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
    lang="en" 等では、i18n/{lang}.json の翻訳テーブルを参照して英語表示名を返す。
    対応する翻訳が存在しない場合は日本語キーをフォールバックとして使用する。

    翻訳は i18n/en.json に集中管理する（Single Source of Truth は database/*.json、
    翻訳テーブルは i18n/*.json）。

    Parameters
    ----------
    db : dict
        load_all_databases() の戻り値。
    db_name : str
        対象のDB識別名（例: "FLOWCONTROL", "RoomUsageSchedule"）。
    lang : str, optional
        返す言語コード（デフォルト: "ja"）。

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

    keys = list(db[db_name].keys())

    if lang == "ja":
        return keys

    # lang != "ja": i18n/{lang}.json を参照して翻訳
    translations = _load_translations(lang)
    # DBの識別名と en.json のカテゴリ名のマッピング
    en_category = _DB_NAME_TO_EN_CATEGORY.get(db_name, db_name)
    category_map = translations.get(en_category, {})
    return [category_map.get(k, k) for k in keys]  # 翻訳なければ日本語のまま


# DB識別名（load_all_databases のキー）→ en.json カテゴリ名のマッピング
_DB_NAME_TO_EN_CATEGORY = {
    "RoomUsageSchedule":     "buildingType",
    "FLOWCONTROL":           "FLOWCONTROL",
    "HeatSourcePerformance": "heatSourceType",   # 将来対応（現在は未翻訳）
    "lightingControl":       "lightingControl",  # トップキーは既に英語
    "ventilationControl":    "ventilationControl",
}

# input_options の日本語キー → en.json カテゴリ名のマッピング
# 翻訳対象外（数値コード・熱源機種等）はここに含まない
_INPUT_OPTIONS_KEY_TO_EN_CATEGORY: dict = {
    "有無":                     "yesNo",
    "建物用途":                 "buildingType",
    "室用途":                   "roomType",           # 特殊: ネスト構造
    "方位":                     "orientation",
    "外壁の種類":               "wallType",
    "外壁の種類(WEBPRO)":       "wallTypeWebpro",
    "構造種別":                 "structureType",
    "断熱性能の入力方法":       "insulationInputMethod",
    "窓性能の入力方法":         "windowInputMethod",
    "建具の種類":               "frameType",
    "ガラスの層数":             "glassLayers",
    "冷暖同時供給の有無":       "simultaneousSupply",
    "蓄熱の種類":               "heatStorageType",
    "流量制御方式":             "FLOWCONTROL",
    "風量制御方式":             "FLOWCONTROL",
    "空調機タイプ":             "acUnitType",
    "送風機の種類":             "fanType",
    "換気方式":                 "ventilationMethod",
    "換気送風機の種類":         "ventilationFanType",
    "換気送風量制御":           "AirVolumeControl",
    "換気代替空調対象室の用途": "ventilationSubstituteRoomUsage",
    "照明在室検知制御":         "OccupantSensingCTRL",
    "照明明るさ検知制御":       "IlluminanceSensingCTRL",
    "照明タイムスケジュール制御": "TimeScheduleCTRL",
    "照明初期照度補正機能":     "InitialIlluminationCorrectionCTRL",
    "給湯負荷":                 "hotwaterLoad",
    "節湯器具":                 "waterSavingFixture",
    "給湯熱源の用途":           "hotwaterHeatSourcePurpose",
    "給湯熱源機種":             "hotwaterHeatSourceType",
    "配管保温仕様":             "pipeInsulationSpec",
    "速度制御方式":             "elevatorSpeedControl",
    "太陽電池の種類":           "solarCellType",
    "アレイ設置方式":           "arrayInstallationType",
    "排熱利用優先順位":         "heatRecoveryPriority",
}


def normalize_input(inputdata: dict) -> dict:
    """
    inputdata 内の英語表示値を日本語DBキーに変換する。

    en.json の逆引きマップを使用する。知らない値はそのまま通す（日本語入力も動作する）。
    inputdata を in-place で変更して返す。

    対象フィールド（Phase 4a）:
        Rooms[*].buildingType
        Rooms[*].roomType  （buildingType に応じた逆引き）
        AirHandlingSystem[*].AirHandlingUnit[*].FanControlType
        SecondaryPumpSystem[*].SecondaryPump[*].ContolType   ← タイポは既存仕様通り
        LightingSystems[*].LightingSystem[*].OccupantSensingCTRL
        LightingSystems[*].LightingSystem[*].IlluminanceSensingCTRL
        LightingSystems[*].LightingSystem[*].TimeScheduleCTRL
        LightingSystems[*].LightingSystem[*].InitialIlluminationCorrectionCTRL
        VentilationRoom[*].VentilationUnitRef[*].AirVolumeControl

    Parameters
    ----------
    inputdata : dict
        webproJsonSchema 準拠の入力データ辞書。

    Returns
    -------
    dict
        変換後の inputdata（in-place 変更、同一オブジェクトを返す）。
    """
    en = _load_translations("en")

    # 各カテゴリの逆引きマップを構築（英語表示名 → 日本語DBキー）
    rev = {}
    for cat, mapping in en.items():
        if isinstance(mapping, dict) and cat != "roomType":
            rev[cat] = {v: k for k, v in mapping.items()}

    # Rooms: buildingType と roomType を変換
    for room in inputdata.get("Rooms", {}).values():
        if not isinstance(room, dict):
            continue
        _translate_field(room, "buildingType", rev.get("buildingType", {}))
        # roomType は変換後の日本語 buildingType を使って逆引き
        bt_ja = room.get("buildingType", "")
        rt_rev = {v: k for k, v in en.get("roomType", {}).get(bt_ja, {}).items()}
        _translate_field(room, "roomType", rt_rev)

    # AirHandlingSystem: FanControlType
    fc_rev = rev.get("FLOWCONTROL", {})
    for sys_dict in inputdata.get("AirHandlingSystem", {}).values():
        if not isinstance(sys_dict, dict):
            continue
        for ahu in sys_dict.get("AirHandlingUnit", []):
            if isinstance(ahu, dict):
                _translate_field(ahu, "FanControlType", fc_rev)

    # SecondaryPumpSystem: ContolType（タイポ "Contol" は既存仕様通り）
    for sys_dict in inputdata.get("SecondaryPumpSystem", {}).values():
        if not isinstance(sys_dict, dict):
            continue
        for pump in sys_dict.get("SecondaryPump", []):
            if isinstance(pump, dict):
                _translate_field(pump, "ContolType", fc_rev)

    # LightingSystems: 照明制御4種
    for ls_dict in inputdata.get("LightingSystems", {}).values():
        if not isinstance(ls_dict, dict):
            continue
        for ls in ls_dict.get("LightingSystem", []):
            if not isinstance(ls, dict):
                continue
            for ctrl_key in ("OccupantSensingCTRL", "IlluminanceSensingCTRL",
                             "TimeScheduleCTRL", "InitialIlluminationCorrectionCTRL"):
                _translate_field(ls, ctrl_key, rev.get(ctrl_key, {}))

    # VentilationRoom: 換気風量制御
    av_rev = rev.get("AirVolumeControl", {})
    for vu_ref_list in inputdata.get("VentilationRoom", {}).values():
        if not isinstance(vu_ref_list, dict):
            continue
        for ref in vu_ref_list.get("VentilationUnitRef", []):
            if isinstance(ref, dict):
                _translate_field(ref, "AirVolumeControl", av_rev)

    return inputdata


def translate_input_options(options: dict, lang: str = "en") -> dict:
    """
    input_options の日本語値を指定言語に翻訳して返す。

    make_inputdata.get_input_options() の戻り値を受け取り、
    各選択肢値を en.json の翻訳テーブルで変換する。
    翻訳対象外の項目（地域区分・断熱材番号等の数値コード）はそのまま返す。

    Parameters
    ----------
    options : dict
        make_inputdata.get_input_options() の戻り値（日本語値）。
    lang : str
        翻訳先言語コード（"en" 等）。"ja" の場合はそのまま返す。

    Returns
    -------
    dict
        翻訳後の options（新しい dict オブジェクト）。
    """
    if lang == "ja":
        return options

    en = _load_translations(lang)
    result = {}

    for key, values in options.items():
        cat = _INPUT_OPTIONS_KEY_TO_EN_CATEGORY.get(key)

        if cat is None:
            # 翻訳対象外（地域区分・断熱材番号・ガラスの種類・熱源機種 等）
            result[key] = values
        elif cat == "roomType" and isinstance(values, dict):
            # 室用途: {建物用途_ja: [室用途_ja, ...]} → 建物用途・室用途ともに翻訳
            bt_map = en.get("buildingType", {})
            rt_map = en.get("roomType", {})
            result[key] = {
                bt_map.get(bt, bt): [rt_map.get(bt, {}).get(rt, rt) for rt in rooms]
                for bt, rooms in values.items()
            }
        elif isinstance(values, list):
            cat_map = en.get(cat, {})
            result[key] = [cat_map.get(v, v) for v in values]
        else:
            result[key] = values

    return result


def _translate_field(obj: dict, key: str, rev_map: dict) -> None:
    """
    obj[key] の値が rev_map にあれば日本語に置き換える（内部ヘルパー）。
    rev_map にない値はそのまま通す（日本語直接入力にも対応）。
    """
    if key in obj and isinstance(obj[key], str) and obj[key] in rev_map:
        obj[key] = rev_map[obj[key]]


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
        "AnnualSolarLevel":       "common_annual_solar_level.json",
    }

    db = {}
    for key, filename in db_files.items():
        filepath = _DB_DIR + filename
        with open(filepath, "r", encoding="utf-8") as f:
            db[key] = json.load(f)

    # common_options.json の各カテゴリをトップレベルキーとして展開
    with open(_DB_DIR + "common_options.json", "r", encoding="utf-8") as f:
        common_opts = json.load(f)
    for key, val in common_opts.items():
        if not key.startswith("_"):
            db[key] = val

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
