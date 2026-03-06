"""
database_loader.py
==================
builelibのデータベースJSONファイルを一括で読み込み、管理するモジュール。

設計方針
--------
* database/*.json が「正」のデータソース
* SPシートの追加データはここで一元的にマージする
* 各計算モジュールはこのモジュールが返す辞書を使うだけでよい

使用例
------
    from builelib import database_loader

    # 計算前に一度だけ呼ぶ
    db = database_loader.load_all_databases(inputdata.get("SpecialInputData", {}))

    # 各計算モジュールに渡す
    lighting.calc_energy(inputdata, db=db)
    ventilation.calc_energy(inputdata, db=db)

"""

import json
import os
import copy

# このファイルと同じディレクトリにある database/ フォルダを参照する
_DB_DIR = os.path.dirname(os.path.abspath(__file__)) + "/database/"

# i18n翻訳ファイルの保存場所（将来の多言語対応用）
_I18N_DIR = os.path.dirname(os.path.abspath(__file__)) + "/i18n/"

# データベースファイル名
_db_files = {

    # ---- 共通 ----
    "地域区分": "common_area.json",
    "年間日射地域区分": "common_annual_solar_level.json",
    "構造種別": "common_structure_type.json",
    "基準一次エネルギー消費量": "common_room_standard_value.json",
    "標準室使用スケジュール": "common_room_usage_schedule.json",
    "カレンダー": "common_calendar.json",
    "建物用途エイリアス": "common_building_type_alias.json",
    "室用途エイリアス": "common_room_type_alias.json",

    # ---- 空調：外皮 ----
    "方位": "common_orientation.json",
    "外壁の種類": "ac_wall_type.json",
    "断熱性能の入力方法": "ac_wall_input_method.json",
    "建材番号": "ac_wall_insulation_id.json",
    "建材の種類": "ac_heat_thermal_conductivity.json",
    "建材の種類(モデル)": "ac_heat_thermal_conductivity_model.json",
    "窓性能の入力方法": "ac_window_input_method.json",
    "建具の種類": "ac_window_frame_type.json",
    "ガラスの層数": "ac_window_glass_layers.json",
    "ガラスの種類": "ac_window_heat_transfer.json",
    "ガラス窓性能変換（建具種類）": "ac_glass_to_window.json",
    "ブラインドの有無": "ac_window_blind.json",

    # ---- 空調：設備 ----
    "運転モード": "ac_operation_mode.json",
    "冷暖同時供給の有無": "ac_operation_simultaneous_supply.json",
    "蓄熱の種類": "ac_heat_storage_type.json",
    "熱源機種": "ac_heat_source_performance.json",
    "地盤種類": "ac_gshp_openloop.json",
    "熱源台数制御": "ac_heat_source_number_control.json",
    "熱源運転順位": "ac_heat_source_operation_priority.json",
    "流量制御方式": "ac_flow_control.json",
    "ポンプ台数制御": "ac_pump_number_control.json",
    "ポンプ運転順位": "ac_pump_operation_priority.json",
    "空調機タイプ": "ac_ahu_type.json",
    "送風機の種類": "ac_ahu_fan_type.json",
    "全熱交換器の種別": "ac_ahu_heat_exchanger.json",
    "自動換気切替機能の有無": "ac_ahu_heat_exchanger_control.json",
    "外気冷房の有無": "ac_ahu_outdoor_cooling.json",
    "外気取入制御の有無": "ac_ahu_outdoor_intake_control.json",

    # ---- 空調：負荷計算係数（地域別） ----
    "負荷計算係数(1地域)": "ac_room_heat_gain_area1.json",
    "負荷計算係数(2地域)": "ac_room_heat_gain_area2.json",
    "負荷計算係数(3地域)": "ac_room_heat_gain_area3.json",
    "負荷計算係数(4地域)": "ac_room_heat_gain_area4.json",
    "負荷計算係数(5地域)": "ac_room_heat_gain_area5.json",
    "負荷計算係数(6地域)": "ac_room_heat_gain_area6.json",
    "負荷計算係数(7地域)": "ac_room_heat_gain_area7.json",
    "負荷計算係数(8地域)": "ac_room_heat_gain_area8.json",

    # ---- 換気 ----
    "換気方式": "vt_ventilation_method.json",
    "換気送風機の種類": "vt_fan_type.json",
    "換気代替空調対象室の用途": "vt_pac_room_usage.json",
    "換気送風量制御": "vt_control_air_volume.json",
    "高効率電動機": "vt_control_high_efficiency_motor.json",
    "インバーター制御": "vt_control_inverter.json",

    # ---- 照明 ----
    "照明在室検知制御": "lt_control_occupant_sensing.json",
    "照明明るさ検知制御":  "lt_control_illuminance_sensing.json",
    "照明タイムスケジュール制御": "lt_control_time_schedule.json",
    "照明初期照度補正機能": "lt_control_iumination_correction.json",

    # ---- 給湯 ----
    "燃料種別": "hw_fuel_type.json",
    "燃料種別エイリアス": "hw_fuel_type_alias.json",
    "燃料種別から給湯熱源": "hw_fuel_type_to_heat_source.json",
    "給湯熱源機種": "hw_heat_source_type.json",
    "給湯負荷": "hw_hot_water_usage.json",
    "節湯器具": "hw_water_saving_fixture.json",
    "給湯熱源の用途": "hw_heat_source_purpose.json",
    "配管保温仕様": "hw_pipe_insulation_level.json",
    "配管熱伝導率": "hw_piping_thermal_conductivity.json",

    # ---- 昇降機 ----
    "速度制御方式": "ev_control_type.json",

    # ---- 太陽光発電 ----
    "太陽電池の種類": "pv_solar_cell_type.json",
    "アレイ設置方式": "pv_array_type.json",

    # ---- コジェネ ----
    "排熱利用優先順位": "cgs_heat_recovery_priority.json",
    "24時間運転の有無": "cgs_24hours_operation.json",

}


def load_all_databases(db_files: dict = _db_files) -> dict:
    """
    全データベースJSONを一括で読み込み、SPシートの追加データをマージして返す。

    Returns
    -------
    dict
        キー = DB識別名、値 = マージ済みDB辞書。
    """
    # データベースの読み込み
    db = {}
    for key, filename in db_files.items():
        filepath = _DB_DIR + filename
        with open(filepath, "r", encoding="utf-8") as f:
            db[key] = json.load(f)

    return db


def get_input_options(db: dict) -> dict:

    # 建物用途・室用途：RoomUsageSchedule.json の階層から自動生成
    _buiding_types = list(db["標準室使用スケジュール"].keys())
    _room_types_by_bt  = {
        bt: list(rooms.keys())
        for bt, rooms in db["標準室使用スケジュール"].items()
    }

    # 入力値の選択肢一覧（入力チェック用）
    input_options = {

        # ---- 共通 ----
        "地域区分": [k.replace("地域", "") for k in db["地域区分"].keys()],
        "年間日射地域区分": list(db["年間日射地域区分"].keys()),
        "建物用途": _buiding_types,
        "室用途": _room_types_by_bt,
        
        # ---- 空調：外皮 ----
        "外壁の種類": list(db["外壁の種類"].keys()),
        "建材の種類": list(db["建材の種類"].keys()),
        "建具の種類": list(db["建具の種類"].keys()),
        "ガラスの種類": list(db["ガラスの種類"].keys()),
        "ブラインドの有無": list(db["ブラインドの有無"].keys()),
        "方位": list(db["方位"].keys()),

        # ---- 空調：設備 ----
        "冷暖同時供給の有無": list(db["冷暖同時供給の有無"].keys()),
        "熱源台数制御": list(db["熱源台数制御"].keys()),
        "蓄熱の種類": list(db["蓄熱の種類"].keys()),
        "熱源機種": list(db["熱源機種"].keys()),
        "ポンプ台数制御": list(db["ポンプ台数制御"].keys()),
        "流量制御方式": list(db["流量制御方式"].keys()),
        "空調機タイプ": list(db["空調機タイプ"].keys()),    
        "自動換気切替機能の有無": list(db["自動換気切替機能の有無"].keys()),
        "外気冷房の有無": list(db["外気冷房の有無"].keys()),
        "外気取入制御の有無": list(db["外気取入制御の有無"].keys()),

        "熱源運転順位": list(db["熱源運転順位"].keys()),  # 使われていない
        "ポンプ運転順位": list(db["ポンプ運転順位"].keys()),  # 使われていない
        "全熱交換器の種別": list(db["全熱交換器の種別"].keys()),  # 使われていない

        # ---- 換気 ----
        "換気送風機の種類": list(db["換気送風機の種類"].keys()),
        "高効率電動機": list(db["高効率電動機"].keys()),
        "換気送風量制御": list(db["換気送風量制御"].keys()),
        "インバーター制御": list(db["インバーター制御"].keys()),
        "換気代替空調対象室の用途": list(db["換気代替空調対象室の用途"].keys()),

        # ---- 照明 ----
        "照明在室検知制御": list(db["照明在室検知制御"].keys()),
        "照明明るさ検知制御": list(db["照明明るさ検知制御"].keys()),
        "照明タイムスケジュール制御": list(db["照明タイムスケジュール制御"].keys()),
        "照明初期照度補正機能": list(db["照明初期照度補正機能"].keys()),

        # ---- 給湯 ----
        "節湯器具": list(db["節湯器具"].keys()),
        "配管保温仕様": list(db["配管保温仕様"].keys()),
        "燃料種別": list(db["燃料種別"].keys()),

        # ---- 昇降機 ----
        "速度制御方式": list(db["速度制御方式"].keys()),

        # ---- 太陽光発電 ----
        "太陽電池の種類": list(db["太陽電池の種類"].keys()),
        "アレイ設置方式": list(db["アレイ設置方式"].keys()),

        # ---- コジェネ ----
        "排熱利用優先順位": list(db["排熱利用優先順位"].keys()),
        "24時間運転の有無": list(db["24時間運転の有無"].keys()),

    }

    return input_options


def get_standard_value(special_sheet: dict) -> dict:
    """基準一次エネルギー消費量データベースを読み込み、SPシートの追加室用途をマージして返す。

    Parameters
    ----------
    special_sheet : dict
        inputdata["SpecialInputData"] の内容。
        "room_usage_condition" キーがある場合、追加室用途の基準値をベース室用途からコピーする。

    Returns
    -------
    dict
        建物用途 → 室用途 → 設備種別 の基準一次エネルギー消費量辞書。
    """
    with open(_DB_DIR + "common_room_standard_value.json", "r", encoding="utf-8") as f:
        standard_value = json.load(f)

    if special_sheet and "room_usage_condition" in special_sheet:
        for building_type in special_sheet["room_usage_condition"]:
            for room_type in special_sheet["room_usage_condition"][building_type]:
                base_room_type = special_sheet["room_usage_condition"][building_type][room_type]["ベースとする室用途"]
                standard_value[building_type][room_type] = copy.deepcopy(
                    standard_value[building_type][base_room_type]
                )

    return standard_value


def load_translations(lang: str) -> dict:
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
