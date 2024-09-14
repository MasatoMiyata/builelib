# 平成28年基準における空調設備の基準一次エネルギー消費量を求めるプログラム

import json

import numpy as np
import pandas as pd

from builelib import airconditioning_webpro


# json.dump用のクラス
class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, set):
            return list(obj)
        else:
            return super(MyEncoder, self).default(obj)


def convert_heat_source_name(name):
    """熱源機種の読み替え
    Args:
        name: H25基準Webプログラムの機種名
    Returns:
        builelib_name: Builelibの機種名
    """
    if name == "空冷ヒートポンプ（スクロール，圧縮機台数制御）":
        builelib_name = "ウォータチリングユニット(空冷式)"
    elif name == "空冷ヒートポンプ":
        builelib_name = "ウォータチリングユニット(空冷式)"
    elif name == "電気式ビル用マルチ" or name == "ビル用マルチエアコン(電気式)":
        builelib_name = "パッケージエアコンディショナ(空冷式)"
    elif name == "ガス式ビル用マルチ":
        builelib_name = "ガスヒートポンプ冷暖房機(都市ガス)"
    elif name == "FF式暖房機(灯油)" or name == "FF式暖房機（灯油）":
        builelib_name = "FF式石油暖房機"
    else:
        print(name)
        raise Exception("熱源機種名称が不正です")

    return builelib_name


def convert_heat_source_energy(name, energy):
    """熱源機種ごとにエネルギー消費量を算出
    Args:
        name: 機種名
        energy: 入力されたエネルギー消費量
    Returns:
        E: 電力消費量
        G: 燃料消費量
    """
    if name == "空冷ヒートポンプ（スクロール，圧縮機台数制御）":
        E = energy
        G = 0
    elif name == "空冷ヒートポンプ":
        E = energy
        G = 0
    elif name == "電気式ビル用マルチ" or name == "ビル用マルチエアコン(電気式)":
        E = energy
        G = 0
    elif name == "ガス式ビル用マルチ":
        E = 0
        G = energy
    elif name == "FF式暖房機(灯油)" or name == "FF式暖房機（灯油）":
        E = 0
        G = energy
    else:
        print(name)
        raise Exception("熱源機種名称が不正です")

    return E, G


# 設定ファイル
setting_filename = "./standard_spec/基準値計算設定ファイル_20150904.xlsx"
# テンプレートファイル
template_filename = "./standard_spec/template.json"

# ---------------------------------------------------------------------
# 計算開始
# ---------------------------------------------------------------------
for iRESION in [1, 2, 3, 4, 5, 6, 7, 8]:

    if iRESION in [1, 2]:
        sheetname = "地域1_2"
    elif iRESION in [3, 4]:
        sheetname = "地域3_4"
    elif iRESION in [5, 6, 7]:
        sheetname = "地域5_6_7"
    elif iRESION in [8]:
        sheetname = "地域8"

    # 設定ファイルの読み込み
    df_spec = pd.read_excel(setting_filename, sheet_name=sheetname, header=0, index_col=0)

    result = []

    for case_id in df_spec:

        df = df_spec[case_id].copy()
        result_room_type = []

        for iBLDG in ["中間階", "最上階", "オールインテリア"]:  # 形状（中間階、最上階、オールインテリア）

            for iMODEL in ["5m", "10m", "20m"]:  # 奥行き（5m, 10m, 20m）

                # 床面積 [m2] = 10m×奥行き
                if iMODEL == "5m":
                    Sf = 50
                elif iMODEL == "10m":
                    Sf = 100
                elif iMODEL == "20m":
                    Sf = 200

                # 方位
                for direction in ["北", "東", "南", "西"]:

                    # ---------------------------
                    # テンプレートファイルの読み込み
                    # ---------------------------
                    with open(template_filename, 'r', encoding='utf-8') as f:
                        bldgdata = json.load(f)

                    # ---------------------------
                    # 地域
                    # ---------------------------
                    bldgdata["building"]["region"] = str(iRESION)

                    # ---------------------------
                    # 建物用途・室用途、階高、天井高、床面積
                    # ---------------------------
                    bldgdata["rooms"]["室"]["building_type"] = df["建物用途大分類"]
                    bldgdata["rooms"]["室"]["room_type"] = df["建物用途小分類"]
                    bldgdata["rooms"]["室"]["floor_height"] = df["階高"]
                    bldgdata["rooms"]["室"]["ceiling_height"] = df["階高"] - 1
                    bldgdata["rooms"]["室"]["room_area"] = Sf

                    # ---------------------------
                    # 外皮
                    # ---------------------------
                    # 外皮面積[m2] (幅を10mとする)
                    St = 10 * df["階高"]

                    if iBLDG == "中間階":

                        bldgdata["envelope_set"]["室"]["wall_list"][0]["direction"] = direction
                        bldgdata["envelope_set"]["室"]["wall_list"][0]["envelope_area"] = St
                        bldgdata["envelope_set"]["室"]["wall_list"][0]["wall_spec"] = df["外壁材質構成（WCON）"]

                        if df["窓ガラス種類、厚さ、ブラインドの有無（WIND）"] == "複層_空気層6mm":
                            u_value = 4.11
                            Mvalue = 0.63
                            layer_type = "複層"
                        elif df["窓ガラス種類、厚さ、ブラインドの有無（WIND）"] == "複層_空気層6mm_ブラインド":
                            u_value = 3.68
                            Mvalue = 0.46
                            layer_type = "複層"
                        elif df["窓ガラス種類、厚さ、ブラインドの有無（WIND）"] == "複層_空気層6mm_lowE":
                            u_value = 3.65
                            Mvalue = 0.32
                            layer_type = "複層"
                        elif df["窓ガラス種類、厚さ、ブラインドの有無（WIND）"] == "単板ガラス":
                            u_value = 6.09
                            Mvalue = 0.70
                            layer_type = "単層"
                        elif df["窓ガラス種類、厚さ、ブラインドの有無（WIND）"] == "単板ガラス_ブラインド":
                            u_value = 5.27
                            Mvalue = 0.50
                            layer_type = "単層"

                        bldgdata["window_configure"]["WIND"] = {
                            "window_area": St * df["窓面積率"],
                            "window_width": None,
                            "window_height": None,
                            "input_method": "性能値を入力",
                            "windowu_value": u_value,
                            "windowi_value": Mvalue,
                            "layer_type": layer_type,
                            "glassu_value": None,
                            "glassi_value": None,
                            "info": ""
                        }

                    elif iBLDG == "最上階":

                        bldgdata["envelope_set"]["室"]["wall_list"][0]["direction"] = direction
                        bldgdata["envelope_set"]["室"]["wall_list"][0]["envelope_area"] = St
                        bldgdata["envelope_set"]["室"]["wall_list"][0]["wall_spec"] = df["外壁材質構成（WCON）"]

                        if df["窓ガラス種類、厚さ、ブラインドの有無（WIND）"] == "複層_空気層6mm":
                            u_value = 4.11
                            Mvalue = 0.63
                        elif df["窓ガラス種類、厚さ、ブラインドの有無（WIND）"] == "複層_空気層6mm_ブラインド":
                            u_value = 3.68
                            Mvalue = 0.46
                        elif df["窓ガラス種類、厚さ、ブラインドの有無（WIND）"] == "複層_空気層6mm_lowE":
                            u_value = 3.65
                            Mvalue = 0.32
                        elif df["窓ガラス種類、厚さ、ブラインドの有無（WIND）"] == "単板ガラス":
                            u_value = 6.09
                            Mvalue = 0.70
                        elif df["窓ガラス種類、厚さ、ブラインドの有無（WIND）"] == "単板ガラス_ブラインド":
                            u_value = 5.27
                            Mvalue = 0.50

                        bldgdata["window_configure"]["WIND"] = {
                            "window_area": St * df["窓面積率"],
                            "window_width": None,
                            "window_height": None,
                            "input_method": "性能値を入力",
                            "windowu_value": u_value,
                            "windowi_value": Mvalue,
                            "layer_type": "単層",
                            "glassu_value": None,
                            "glassi_value": None,
                            "info": ""
                        }

                        bldgdata["envelope_set"]["室"]["wall_list"].append(
                            {
                                "direction": "水平",
                                "envelope_area": Sf,
                                "envelope_width": None,
                                "envelope_height": None,
                                "wall_spec": df["屋根材質構成（WCON）"],
                                "wall_type": "日の当たる外壁",
                                "window_list": [
                                ]
                            }
                        )

                    elif iBLDG == "オールインテリア":
                        bldgdata["envelope_set"]["室"]["wall_list"] = []

                    # ---------------------------
                    # 熱源仕様（冷熱）
                    # ---------------------------
                    if df["台数制御（冷熱）"] == "有":
                        bldgdata["heat_source_system"]["RCH"]["冷房"]["is_staging_control"] = "有"
                    elif df["台数制御（冷熱）"] == "無":
                        bldgdata["heat_source_system"]["RCH"]["冷房"]["is_staging_control"] = "無"

                    if df["一次ポンプWTF（冷熱1台目）"] == 0:
                        primary_pump_power_consumption = 0
                    else:
                        primary_pump_power_consumption = df["床面積あたりの熱源容量（冷熱1台目）"] * Sf / df[
                            "一次ポンプWTF（冷熱1台目）"]

                    bldgdata["heat_source_system"]["RCH"]["冷房"]["heat_source"].append({
                        "heat_source_type": convert_heat_source_name(df["熱源種類（冷熱1台目）"]),
                        "number": 1.0,
                        "supply_water_temp_summer": 7,
                        "supply_water_temp_middle": 7,
                        "supply_water_temp_winter": 7,
                        "heat_source_rated_capacity": df["床面積あたりの熱源容量（冷熱1台目）"] * Sf,
                        "heat_source_rated_power_consumption": convert_heat_source_energy(df["熱源種類（冷熱1台目）"], df[
                            "床面積あたりの主機定格エネルギー消費量（冷熱1台目）"] * Sf)[0],
                        "heat_source_rated_fuel_consumption": convert_heat_source_energy(df["熱源種類（冷熱1台目）"], df[
                            "床面積あたりの主機定格エネルギー消費量（冷熱1台目）"] * Sf)[1],
                        "heat_source_sub_rated_power_consumption": df["床面積あたりの補機定格消費電力（冷熱1台目）"] * Sf,
                        "primary_pump_power_consumption": primary_pump_power_consumption,
                        "primary_pump_control_type": "無",
                        "cooling_tower_capacity": df["床面積あたりの熱源容量（冷熱1台目）"] * Sf,
                        "cooling_tower_fan_power_consumption": df["冷却塔ファン定格消費電力（冷熱1台目）"] * Sf,
                        "cooling_tower_pump_power_consumption": df["冷却水ポンプ定格消費電力（冷熱1台目）"] * Sf,
                        "cooling_tower_control_type": "無",
                        "info": ""
                    }
                    )

                    if pd.isna(df["熱源種類（冷熱2台目）"]) == False:

                        if df["一次ポンプWTF（冷熱2台目）"] == 0:
                            primary_pump_power_consumption = 0
                        else:
                            primary_pump_power_consumption = df["床面積あたりの熱源容量（冷熱2台目）"] * Sf / df[
                                "一次ポンプWTF（冷熱2台目）"]

                        bldgdata["heat_source_system"]["RCH"]["冷房"]["heat_source"].append({
                            "heat_source_type": convert_heat_source_name(df["熱源種類（冷熱2台目）"]),
                            "number": 1.0,
                            "supply_water_temp_summer": 7,
                            "supply_water_temp_middle": 7,
                            "supply_water_temp_winter": 7,
                            "heat_source_rated_capacity": df["床面積あたりの熱源容量（冷熱2台目）"] * Sf,
                            "heat_source_rated_power_consumption": convert_heat_source_energy(df["熱源種類（冷熱2台目）"], df[
                                "床面積あたりの主機定格エネルギー消費量（冷熱2台目）"] * Sf)[0],
                            "heat_source_rated_fuel_consumption": convert_heat_source_energy(df["熱源種類（冷熱2台目）"], df[
                                "床面積あたりの主機定格エネルギー消費量（冷熱2台目）"] * Sf)[1],
                            "heat_source_sub_rated_power_consumption": df["床面積あたりの補機定格消費電力（冷熱2台目）"] * Sf,
                            "primary_pump_power_consumption": primary_pump_power_consumption,
                            "primary_pump_control_type": "無",
                            "cooling_tower_capacity": df["床面積あたりの熱源容量（冷熱2台目）"] * Sf,
                            "cooling_tower_fan_power_consumption": df["冷却塔ファン定格消費電力（冷熱2台目）"] * Sf,
                            "cooling_tower_pump_power_consumption": df["冷却水ポンプ定格消費電力（冷熱2台目）"] * Sf,
                            "cooling_tower_control_type": "無",
                            "info": ""
                        }
                        )

                    if pd.isna(df["熱源種類（冷熱3台目）"]) == False:

                        if df["一次ポンプWTF（冷熱3台目）"] == 0:
                            primary_pump_power_consumption = 0
                        else:
                            primary_pump_power_consumption = df["床面積あたりの熱源容量（冷熱3台目）"] * Sf / df[
                                "一次ポンプWTF（冷熱3台目）"]

                        bldgdata["heat_source_system"]["RCH"]["冷房"]["heat_source"].append({
                            "heat_source_type": convert_heat_source_name(df["熱源種類（冷熱3台目）"]),
                            "number": 1.0,
                            "supply_water_temp_summer": 7,
                            "supply_water_temp_middle": 7,
                            "supply_water_temp_winter": 7,
                            "heat_source_rated_capacity": df["床面積あたりの熱源容量（冷熱3台目）"] * Sf,
                            "heat_source_rated_power_consumption": convert_heat_source_energy(df["熱源種類（冷熱3台目）"], df[
                                "床面積あたりの主機定格エネルギー消費量（冷熱3台目）"] * Sf)[0],
                            "heat_source_rated_fuel_consumption": convert_heat_source_energy(df["熱源種類（冷熱3台目）"], df[
                                "床面積あたりの主機定格エネルギー消費量（冷熱3台目）"] * Sf)[1],
                            "heat_source_sub_rated_power_consumption": df["床面積あたりの補機定格消費電力（冷熱3台目）"] * Sf,
                            "primary_pump_power_consumption": primary_pump_power_consumption,
                            "primary_pump_control_type": "無",
                            "cooling_tower_capacity": df["床面積あたりの熱源容量（冷熱3台目）"] * Sf,
                            "cooling_tower_fan_power_consumption": df["冷却塔ファン定格消費電力（冷熱3台目）"] * Sf,
                            "cooling_tower_pump_power_consumption": df["冷却水ポンプ定格消費電力（冷熱3台目）"] * Sf,
                            "cooling_tower_control_type": "無",
                            "info": ""
                        }
                        )

                    # ---------------------------
                    # 熱源仕様（温熱）
                    # ---------------------------
                    if df["台数制御（温熱）"] == "有":
                        bldgdata["heat_source_system"]["RCH"]["暖房"]["is_staging_control"] = "有"
                    elif df["台数制御（温熱）"] == "無":
                        bldgdata["heat_source_system"]["RCH"]["暖房"]["is_staging_control"] = "無"

                    if df["一次ポンプWTF（温熱1台目）"] == 0:
                        primary_pump_power_consumption = 0
                    else:
                        primary_pump_power_consumption = df["床面積あたりの熱源容量（温熱1台目）"] * Sf / df[
                            "一次ポンプWTF（温熱1台目）"]

                    bldgdata["heat_source_system"]["RCH"]["暖房"]["heat_source"].append({
                        "heat_source_type": convert_heat_source_name(df["熱源種類（温熱1台目）"]),
                        "number": 1.0,
                        "supply_water_temp_summer": 42,
                        "supply_water_temp_middle": 42,
                        "supply_water_temp_winter": 42,
                        "heat_source_rated_capacity": df["床面積あたりの熱源容量（温熱1台目）"] * Sf,
                        "heat_source_rated_power_consumption": convert_heat_source_energy(df["熱源種類（温熱1台目）"], df[
                            "床面積あたりの主機定格エネルギー消費量（温熱1台目）"] * Sf)[0],
                        "heat_source_rated_fuel_consumption": convert_heat_source_energy(df["熱源種類（温熱1台目）"], df[
                            "床面積あたりの主機定格エネルギー消費量（温熱1台目）"] * Sf)[1],
                        "heat_source_sub_rated_power_consumption": df["床面積あたりの補機定格消費電力（温熱1台目）"] * Sf,
                        "primary_pump_power_consumption": primary_pump_power_consumption,
                        "primary_pump_control_type": "無",
                        "cooling_tower_capacity": 0,
                        "cooling_tower_fan_power_consumption": 0,
                        "cooling_tower_pump_power_consumption": 0,
                        "cooling_tower_control_type": "無",
                        "info": ""
                    }
                    )

                    if pd.isna(df["熱源種類（温熱2台目）"]) == False:

                        if df["一次ポンプWTF（温熱2台目）"] == 0:
                            primary_pump_power_consumption = 0
                        else:
                            primary_pump_power_consumption = df["床面積あたりの熱源容量（温熱2台目）"] * Sf / df[
                                "一次ポンプWTF（温熱2台目）"]

                        bldgdata["heat_source_system"]["RCH"]["暖房"]["heat_source"].append({
                            "heat_source_type": convert_heat_source_name(df["熱源種類（温熱2台目）"]),
                            "number": 1.0,
                            "supply_water_temp_summer": 42,
                            "supply_water_temp_middle": 42,
                            "supply_water_temp_winter": 42,
                            "heat_source_rated_capacity": df["床面積あたりの熱源容量（温熱2台目）"] * Sf,
                            "heat_source_rated_power_consumption": convert_heat_source_energy(df["熱源種類（温熱2台目）"], df[
                                "床面積あたりの主機定格エネルギー消費量（温熱2台目）"] * Sf)[0],
                            "heat_source_rated_fuel_consumption": convert_heat_source_energy(df["熱源種類（温熱2台目）"], df[
                                "床面積あたりの主機定格エネルギー消費量（温熱2台目）"] * Sf)[1],
                            "heat_source_sub_rated_power_consumption": df["床面積あたりの補機定格消費電力（温熱2台目）"] * Sf,
                            "primary_pump_power_consumption": primary_pump_power_consumption,
                            "primary_pump_control_type": "無",
                            "cooling_tower_capacity": 0,
                            "cooling_tower_fan_power_consumption": 0,
                            "cooling_tower_pump_power_consumption": 0,
                            "cooling_tower_control_type": "無",
                            "info": ""
                        }
                        )

                    if pd.isna(df["熱源種類（温熱3台目）"]) == False:

                        if df["一次ポンプWTF（温熱3台目）"] == 0:
                            primary_pump_power_consumption = 0
                        else:
                            primary_pump_power_consumption = df["床面積あたりの熱源容量（温熱3台目）"] * Sf / df[
                                "一次ポンプWTF（温熱3台目）"]

                        bldgdata["heat_source_system"]["RCH"]["暖房"]["heat_source"].append({
                            "heat_source_type": convert_heat_source_name(df["熱源種類（温熱3台目）"]),
                            "number": 1.0,
                            "supply_water_temp_summer": 42,
                            "supply_water_temp_middle": 42,
                            "supply_water_temp_winter": 42,
                            "heat_source_rated_capacity": df["床面積あたりの熱源容量（温熱3台目）"] * Sf,
                            "heat_source_rated_power_consumption": convert_heat_source_energy(df["熱源種類（温熱3台目）"], df[
                                "床面積あたりの主機定格エネルギー消費量（温熱3台目）"] * Sf)[0],
                            "heat_source_rated_fuel_consumption": convert_heat_source_energy(df["熱源種類（温熱3台目）"], df[
                                "床面積あたりの主機定格エネルギー消費量（温熱3台目）"] * Sf)[1],
                            "heat_source_sub_rated_power_consumption": df["床面積あたりの補機定格消費電力（温熱3台目）"] * Sf,
                            "primary_pump_power_consumption": primary_pump_power_consumption,
                            "primary_pump_control_type": "無",
                            "cooling_tower_capacity": 0,
                            "cooling_tower_fan_power_consumption": 0,
                            "cooling_tower_pump_power_consumption": 0,
                            "cooling_tower_control_type": "無",
                            "info": ""
                        }
                        )

                    # ---------------------------
                    # 二次ポンプ（冷水ポンプ）
                    # ---------------------------
                    if df["冷水ポンプ台数"] > 0 or df["温水ポンプ台数"] > 0:
                        bldgdata["secondary_pump_system"]["PCH"] = {}

                    if df["冷水ポンプ台数"] > 0:

                        if df["冷水ポンプ制御方式"] == "VWV":
                            control_type = "回転数制御"
                            min_opening_rate = 60
                        else:
                            control_type = "定流量制御"
                            min_opening_rate = 100

                        Qpump = df["冷水ポンプ能力"] * Sf

                        secondary_pump = []
                        for ipump in range(df["冷水ポンプ台数"]):
                            secondary_pump.append(
                                {
                                    "number": 1.0,
                                    "rated_water_flow_rate": 3600 * Qpump / (4200 * df["冷水ポンプ往還温度差"]) / df[
                                        "冷水ポンプ台数"],
                                    "rated_power_consumption": Qpump / df["冷水ポンプWTF"] / df["冷水ポンプ台数"],
                                    "control_type": control_type,
                                    "min_opening_rate": min_opening_rate,
                                    "info": ""
                                }
                            )

                        bldgdata["secondary_pump_system"]["PCH"]["冷房"] = {
                            "temperature_difference": df["冷水ポンプ往還温度差"],
                            "is_staging_control": df["冷水ポンプ台数制御"],
                            "secondary_pump": secondary_pump
                        }

                    # ---------------------------
                    # 二次ポンプ（温水ポンプ）
                    # ---------------------------
                    if df["温水ポンプ台数"] > 0:

                        if df["温水ポンプ制御方式"] == "VWV":
                            control_type = "回転数制御"
                            min_opening_rate = 60
                        else:
                            control_type = "定流量制御"
                            min_opening_rate = 100

                        Qpump = df["温水ポンプ能力"] * Sf

                        secondary_pump = []
                        for ipump in range(df["温水ポンプ台数"]):
                            secondary_pump.append(
                                {
                                    "number": 1.0,
                                    "rated_water_flow_rate": 3600 * Qpump / (4200 * df["温水ポンプ往還温度差"]) / df[
                                        "温水ポンプ台数"],
                                    "rated_power_consumption": Qpump / df["温水ポンプWTF"] / df["温水ポンプ台数"],
                                    "control_type": control_type,
                                    "min_opening_rate": min_opening_rate,
                                    "info": ""
                                }
                            )

                        bldgdata["secondary_pump_system"]["PCH"]["暖房"] = {
                            "temperature_difference": df["温水ポンプ往還温度差"],
                            "is_staging_control": df["温水ポンプ台数制御"],
                            "secondary_pump": secondary_pump
                        }

                    # ---------------------------
                    # 空調機（1台目）
                    # ---------------------------
                    if df["空調機タイプ（１台目）"] == "室内機":
                        if df["冷水ポンプ台数"] == 0:
                            bldgdata["air_handling_system"]["ACP-1"]["pump_cooling"] = None
                        if df["温水ポンプ台数"] == 0:
                            bldgdata["air_handling_system"]["ACP-1"]["pump_heating"] = None

                    bldgdata["air_handling_system"]["ACP-1"]["is_outdoor_air_cut"] = df["外気カット制御（１台目）"]
                    bldgdata["air_handling_system"]["ACP-1"]["is_economizer"] = df["外気冷房制御（１台目）"]
                    bldgdata["air_handling_system"]["ACP-1"]["economizer_max_air_volume"] = df[
                                                                                           "床面積あたりの定格給気風量（１台目）"] * Sf * 1000

                    if df["風量制御方式（１台目）"] == "CAV":
                        fan_control_type = "無"
                        fan_min_opening_rate = 100
                    elif df["風量制御方式（１台目）"] == "VAV":
                        fan_control_type = "回転数制御"
                        fan_min_opening_rate = 65

                    if pd.isna(df["空調機タイプ（2台目）"]) and df["全熱交換機制御"] == "有":
                        air_heat_exchange_ratio_cooling = 50
                        air_heat_exchange_ratio_heating = 50
                        air_heat_exchanger_control = "無"
                        air_heat_exchanger_power_consumption = df["全熱交換機ローター消費電力"] * Sf
                    else:
                        air_heat_exchange_ratio_cooling = None
                        air_heat_exchange_ratio_heating = None
                        air_heat_exchanger_control = "無"
                        air_heat_exchanger_power_consumption = 0

                    bldgdata["air_handling_system"]["ACP-1"]["air_handling_unit"].append({
                        "type": df["空調機タイプ（１台目）"],
                        "number": 1.0,
                        "rated_capacity_cooling": df["床面積あたりの定格冷房能力（１台目）"] * Sf,
                        "rated_capacity_heating": df["床面積あたりの定格暖房能力（１台目）"] * Sf,
                        "fan_type": None,
                        "fan_air_volume": df["床面積あたりの定格給気風量（１台目）"] * Sf * 1000,
                        "fan_power_consumption": df["床面積あたりの定格冷房能力（１台目）"] * Sf / df[
                            "給気/排気/外気ファンATF（１台目）"],
                        "fan_control_type": fan_control_type,
                        "fan_min_opening_rate": fan_min_opening_rate,
                        "air_heat_exchange_ratio_cooling": air_heat_exchange_ratio_cooling,
                        "air_heat_exchange_ratio_heating": air_heat_exchange_ratio_heating,
                        "air_heat_exchanger_effective_air_volume_ratio": None,
                        "air_heat_exchanger_control": air_heat_exchanger_control,
                        "air_heat_exchanger_power_consumption": air_heat_exchanger_power_consumption,
                        "info": ""
                    })

                    # ---------------------------
                    # 空調機（2台目）
                    # ---------------------------
                    if pd.isna(df["空調機タイプ（2台目）"]) == False:

                        bldgdata["air_handling_system"]["ACP-2"] = {
                            "is_economizer": "無",
                            "economizer_max_air_volume": None,
                            "is_outdoor_air_cut": "無",
                            "pump_cooling": "PCH",
                            "pump_heating": "PCH",
                            "heat_source_cooling": "RCH",
                            "heat_source_heating": "RCH",
                            "air_handling_unit": []
                        }

                        if df["風量制御方式（2台目）"] == "CAV":
                            fan_control_type = "無"
                            fan_min_opening_rate = 100
                        elif df["風量制御方式（2台目）"] == "VAV":
                            fan_control_type = "回転数制御"
                            fan_min_opening_rate = 65

                        if df["全熱交換機制御"] == "有":
                            air_heat_exchange_ratio_cooling = 50
                            air_heat_exchange_ratio_heating = 50
                            air_heat_exchanger_control = "無"
                            air_heat_exchanger_power_consumption = df["全熱交換機ローター消費電力"] * Sf
                        else:
                            air_heat_exchange_ratio_cooling = None
                            air_heat_exchange_ratio_heating = None
                            air_heat_exchanger_control = "無"
                            air_heat_exchanger_power_consumption = 0

                        if df["空調機タイプ（2台目）"] == "室内機":
                            if df["冷水ポンプ台数"] == 0:
                                bldgdata["air_handling_system"]["ACP-2"]["pump_cooling"] = None
                            if df["温水ポンプ台数"] == 0:
                                bldgdata["air_handling_system"]["ACP-2"]["pump_heating"] = None

                        bldgdata["air_handling_system"]["ACP-2"]["is_outdoor_air_cut"] = df["外気カット制御（2台目）"]
                        bldgdata["air_handling_system"]["ACP-2"]["is_economizer"] = df["外気冷房制御（2台目）"]
                        bldgdata["air_handling_system"]["ACP-2"]["economizer_max_air_volume"] = df[
                                                                                               "床面積あたりの定格給気風量（2台目）"] * Sf * 1000

                        if df["空調機タイプ（2台目）"] == "外調機":
                            type = "空調機"
                        else:
                            type = df["空調機タイプ（2台目）"]

                        bldgdata["air_handling_system"]["ACP-2"]["air_handling_unit"].append({
                            "type": type,
                            "number": 1.0,
                            "rated_capacity_cooling": df["床面積あたりの定格冷房能力（2台目）"] * Sf,
                            "rated_capacity_heating": df["床面積あたりの定格暖房能力（2台目）"] * Sf,
                            "fan_type": None,
                            "fan_air_volume": df["床面積あたりの定格給気風量（2台目）"] * Sf * 1000,
                            "fan_power_consumption": df["床面積あたりの定格冷房能力（2台目）"] * Sf / df[
                                "給気/排気/外気ファンATF（2台目）"],
                            "fan_control_type": fan_control_type,
                            "fan_min_opening_rate": fan_min_opening_rate,
                            "air_heat_exchange_ratio_cooling": air_heat_exchange_ratio_cooling,
                            "air_heat_exchange_ratio_heating": air_heat_exchange_ratio_heating,
                            "air_heat_exchanger_effective_air_volume_ratio": None,
                            "air_heat_exchanger_control": air_heat_exchanger_control,
                            "air_heat_exchanger_power_consumption": air_heat_exchanger_power_consumption,
                            "info": ""
                        })

                        bldgdata["air_conditioning_zone"]["室"]["ahu_cooling_outdoor_load"] = "ACP-2"
                        bldgdata["air_conditioning_zone"]["室"]["ahu_heating_outdoor_load"] = "ACP-2"

                    # ---------------------------
                    # 計算実行
                    # ---------------------------

                    is_calc = False
                    # オールインテリアは5m, 北側のみ計算
                    if iBLDG == "オールインテリア":
                        if iMODEL == "5m" and direction == "北":
                            is_calc = True
                    else:
                        is_calc = True

                    if is_calc:
                        print(
                            f"計算中: {iRESION}地域  {df['建物用途大分類']} - {df['建物用途小分類']}, {iBLDG}, {iMODEL}, {direction}")

                        # json出力（検証用）
                        # with open("standard_value_input.json",'w', encoding='utf-8') as fw:
                        #     json.dump(bldgdata,fw,indent=4,ensure_ascii=False)

                        # buielib/ACの実行
                        result_data_AC = airconditioning_webpro.calc_energy(bldgdata, debug=False)

                        # 設計一次エネ・基準一次エネ
                        print(result_data_AC["設計一次エネルギー消費量[MJ/年]"] / Sf)
                        print(result_data_AC["基準一次エネルギー消費量[MJ/年]"] / Sf)

                        result_room_type.append(result_data_AC["設計一次エネルギー消費量[MJ/年]"] / Sf)

        result.append(result_room_type)

    np.savetxt('平成28年基準_基準一次エネルギー再現_' + str(iRESION) + '地域.csv', result, fmt='%.6f', delimiter=',')
