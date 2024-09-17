import json
import math
import os
import sys

import numpy as np

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import commons as bc
import climate
import shading
import make_figure as mf

# データベースファイルの保存場所
database_directory = os.path.dirname(os.path.abspath(__file__)) + "/database/"
# 気象データファイルの保存場所
climate_data_directory = os.path.dirname(os.path.abspath(__file__)) + "/climatedata/"

# builelibモードかどうか（照明との連成）
BUILELIB_MODE = True


def calc_energy(input_data, debug=False):
    input_data["pump"] = {}
    input_data["ref"] = {}

    # ----------------------------------------------------------------------------------
    # 定数の設定
    # ----------------------------------------------------------------------------------
    k_heatup = 0.84  # ファン・ポンプの発熱比率 [-]
    k_heatloss = 0.03  # 蓄熱槽の熱ロス [-]
    cw = 4.186  # 水の比熱 [kJ/kg・K]

    # ----------------------------------------------------------------------------------
    # 結果格納用の変数 result_json
    # ----------------------------------------------------------------------------------

    result_json = {

        "E_ac": 0,  # 空気調和設備の設計一次エネルギー消費量 [MJ]
        "Es_ac": 0,  # 空気調和設備の基準一次エネルギー消費量 [MJ]
        "BEI/AC": 0,  # 空気調和設備のBEI/AC [-]
        "energy": {
            "E_ahu_fan": 0,  # 空調機群ファンの電力消費量 [MWh]
            "E_ahu_aex": 0,  # 空調機群全熱交換器の電力消費量 [MWh]
            "E_pump": 0,  # 二次ポンプ群の電力消費量 [MWh]
            "E_ref_main": 0,  # 熱源群主機の一次エネルギー消費量 [MJ]
            "e_ref_sub": 0,  # 熱源群補機の電力消費量 [MWh]
            "E_ref_pump": 0,  # 熱源群一次ポンプの電力消費量 [MWh]
            "e_ref_ct_fan": 0,  # 熱源群冷却塔ファンの電力消費量 [MWh]
            "e_ref_ct_pumpa": 0,  # 熱源群冷却水ポンプの電力消費量 [MWh]
            "e_fan_mwh_day": np.zeros(365),  # 空調機群の電力消費量 [MWh/day]
            "e_pump_mwh_day": np.zeros(365),  # 二次ポンプ群の電力消費量 [MWh/day]
            "e_ref_main_mwh_day": np.zeros(365),  # 熱源主機の電力消費量 [MWh/day]
            "e_ref_sub_mwh_day": np.zeros(365)  # 熱源主機以外の電力消費量 [MWh/day]
        },
        "schedule": {
            "room_temperature_setpoint": np.zeros((365, 24)),  # 室内設定温度
            "room_humidity_setpoint": np.zeros((365, 24)),  # 室内設定湿度
            "room_enthalpy": np.zeros((365, 24)),  # 室内設定エンタルピー
        },
        "climate": {
            "tout": np.zeros((365, 24)),  # 気象データ（外気温度）
            "xout": np.zeros((365, 24)),  # 気象データ（絶対湿度）
            "iod": np.zeros((365, 24)),  # 気象データ（法線面直達日射量 W/m2）
            "ios": np.zeros((365, 24)),  # 気象データ（水平面天空日射量 W/m2)
            "inn": np.zeros((365, 24)),  # 気象データ（水平面夜間放射量 W/m2）
            "tout_daily": np.zeros(365),  # 日平均外気温（地中熱計算用）
            "tout_wb": np.zeros((365, 24)),  # 外気湿球温度
            "Tct_cooling": np.zeros((365, 24)),  # 日平均外気温
            "Tct_heating": np.zeros((365, 24)),  # 日平均外気温
        },
        "total_area": 0,  # 空調対象面積 [m2]
        "q_room": {},  # 室負荷の計算結果
        "ahu": {},  # 空調機群の計算結果
        "pump": {},  # 二次ポンプ群の計算結果
        "ref": {},  # 熱源群の計算結果

        "for_cgs": {  # コジェネ計算のための計算結果
            "e_ref_cgsc_abs_day": np.zeros(365),
            "lt_ref_cgs_c_day": np.zeros(365),
            "e_ref_cgsh_day": np.zeros(365),
            "q_ref_cgs_h_day": np.zeros(365),
            "t_ref_cgs_c_day": np.zeros(365),
            "t_ref_cgs_h_day": np.zeros(365),
            "nac_ref_link": 0,
            "qac_link_c_j_rated": 0,
            "eac_link_c_j_rated": 0
        },
        "input_data": {}
    }

    # ----------------------------------------------------------------------------------
    # 流量制御データベースファイルの読み込み
    # ----------------------------------------------------------------------------------

    with open(database_directory + 'flow_control.json', 'r', encoding='utf-8') as f:
        flow_control = json.load(f)

    # 任意評定用 （SP-1: 流量制御)の入力があれば追加
    if "special_input_data" in input_data:
        if "flow_control" in input_data["special_input_data"]:
            flow_control.update(input_data["special_input_data"]["flow_control"])

    # ----------------------------------------------------------------------------------
    # 熱源機器特性データベースファイルの読み込み
    # ----------------------------------------------------------------------------------

    with open(database_directory + "heat_source_performance.json", 'r', encoding='utf-8') as f:
        heat_source_performance = json.load(f)

    # 任意評定 （SP-2：　熱源機器特性)用の入力があれば追加
    if "special_input_data" in input_data:
        if "heat_source_performance" in input_data["special_input_data"]:
            heat_source_performance.update(input_data["special_input_data"]["heat_source_performance"])

    # ----------------------------------------------------------------------------------
    # マトリックスの設定
    # ----------------------------------------------------------------------------------

    # 地域別データの読み込み
    with open(database_directory + 'area.json', 'r', encoding='utf-8') as f:
        area = json.load(f)

    # ----------------------------------------------------------------------------------
    # 他人から供給された熱の一次エネルギー換算係数（デフォルト）
    # ----------------------------------------------------------------------------------

    if input_data["building"]["coefficient_dhc"]["cooling"] is None:
        input_data["building"]["coefficient_dhc"]["cooling"] = 1.36

    if input_data["building"]["coefficient_dhc"]["heating"] is None:
        input_data["building"]["coefficient_dhc"]["heating"] = 1.36

    # ----------------------------------------------------------------------------------
    # 気象データ（解説書 2.2.1）
    # 任意評定 （SP-5: 気象データ)
    # ----------------------------------------------------------------------------------

    if "climate_data" in input_data["special_input_data"]:  # 任意入力（SP-5）

        # 外気温 [℃]
        result_json["climate"]["tout"] = np.array(input_data["special_input_data"]["climate_data"]["tout"])
        # 外気湿度 [kg/kgDA]
        result_json["climate"]["xout"] = np.array(input_data["special_input_data"]["climate_data"]["xout"])
        # 法線面直達日射量 [W/m2]
        result_json["climate"]["iod"] = np.array(input_data["special_input_data"]["climate_data"]["iod"])
        # 水平面天空日射量 [W/m2]
        result_json["climate"]["ios"] = np.array(input_data["special_input_data"]["climate_data"]["ios"])
        # 水平面夜間放射量 [W/m2]
        result_json["climate"]["inn"] = np.array(input_data["special_input_data"]["climate_data"]["inn"])

    else:

        # 気象データ（HASP形式）読み込み ＜365×24の行列＞
        [result_json["climate"]["tout"], result_json["climate"]["xout"],
         result_json["climate"]["iod"], result_json["climate"]["ios"],
         result_json["climate"]["inn"]] = \
            climate.read_hasp_climate_data(
                climate_data_directory + "/" + area[input_data["building"]["region"] + "地域"]["気象データファイル名"])

    # ----------------------------------------------------------------------------------
    # 冷暖房期間（解説書 2.2.2）
    # ----------------------------------------------------------------------------------

    # 空調運転モード
    with open(database_directory + 'ac_operation_mode.json', 'r', encoding='utf-8') as f:
        ac_operation_mode = json.load(f)

    # 各日の冷暖房期間の種類（冷房期、暖房期、中間期）（365×1の行列）
    ac_mode = ac_operation_mode[area[input_data["building"]["region"] + "地域"]["空調運転モードタイプ"]]

    # ----------------------------------------------------------------------------------
    # 平均外気温（解説書 2.2.3）
    # ----------------------------------------------------------------------------------

    # 日平均外気温[℃]（365×1）
    result_json["climate"]["tout_daily"] = np.mean(result_json["climate"]["tout"], 1)

    # ----------------------------------------------------------------------------------
    # 外気エンタルピー（解説書 2.2.4）
    # ----------------------------------------------------------------------------------

    hoa_hourly = bc.trans_8760to36524(
        bc.air_enthalpy(
            bc.trans_36524to8760(result_json["climate"]["tout"]),
            bc.trans_36524to8760(result_json["climate"]["xout"])
        )
    )

    # ----------------------------------------------------------------------------------
    # 空調室の設定温度、室内エンタルピー（解説書 2.3.1、2.3.2）
    # ----------------------------------------------------------------------------------

    for dd in range(0, 365):
        for hh in range(0, 24):

            if ac_mode[dd] == "冷房":
                result_json["schedule"]["room_temperature_setpoint"][dd][hh] = 26
                result_json["schedule"]["room_humidity_setpoint"][dd][hh] = 50
                result_json["schedule"]["room_enthalpy"][dd][hh] = 52.91

            elif ac_mode[dd] == "中間":
                result_json["schedule"]["room_temperature_setpoint"][dd][hh] = 24
                result_json["schedule"]["room_humidity_setpoint"][dd][hh] = 50
                result_json["schedule"]["room_enthalpy"][dd][hh] = 47.81

            elif ac_mode[dd] == "暖房":
                result_json["schedule"]["room_temperature_setpoint"][dd][hh] = 22
                result_json["schedule"]["room_humidity_setpoint"][dd][hh] = 40
                result_json["schedule"]["room_enthalpy"][dd][hh] = 38.81

    # ----------------------------------------------------------------------------------
    # 任意評定 （SP-6: カレンダーパターン)
    # ----------------------------------------------------------------------------------

    input_calendar = []
    if "calender" in input_data["special_input_data"]:
        input_calendar = input_data["special_input_data"]["calender"]

    # ----------------------------------------------------------------------------------
    # 空調機の稼働状態、内部発熱量（解説書 2.3.3、2.3.4）
    # ----------------------------------------------------------------------------------

    room_schedule_room = {}
    room_schedule_light = {}
    room_schedule_person = {}
    room_schedule_oa_app = {}
    room_day_mode = {}

    # 空調ゾーン毎にループ
    for room_zone_name in input_data["air_conditioning_zone"]:

        if room_zone_name in input_data["rooms"]:  # ゾーン分けがない場合

            # 建物用途・室用途、ゾーン面積等の取得
            input_data["air_conditioning_zone"][room_zone_name]["building_type"] = input_data["rooms"][room_zone_name][
                "building_type"]
            input_data["air_conditioning_zone"][room_zone_name]["room_type"] = input_data["rooms"][room_zone_name][
                "room_type"]
            input_data["air_conditioning_zone"][room_zone_name]["zone_area"] = input_data["rooms"][room_zone_name][
                "room_area"]
            input_data["air_conditioning_zone"][room_zone_name]["ceiling_height"] = input_data["rooms"][room_zone_name][
                "ceiling_height"]

        else:

            # 各室のゾーンを検索
            for room_name in input_data["rooms"]:
                if input_data["rooms"][room_name]["zone"] is not None:  # ゾーンがあれば
                    for zone_name in input_data["rooms"][room_name]["zone"]:  # ゾーン名を検索
                        if room_zone_name == (room_name + "_" + zone_name):
                            input_data["air_conditioning_zone"][room_zone_name]["building_type"] = \
                            input_data["rooms"][room_name]["building_type"]
                            input_data["air_conditioning_zone"][room_zone_name]["room_type"] = \
                            input_data["rooms"][room_name]["room_type"]
                            input_data["air_conditioning_zone"][room_zone_name]["ceiling_height"] = \
                            input_data["rooms"][room_name]["ceiling_height"]
                            input_data["air_conditioning_zone"][room_zone_name]["zone_area"] = \
                            input_data["rooms"][room_name]["zone"][zone_name]["zone_area"]

                            break

        # 365日×24時間分のスケジュール （365×24の行列を格納した dict型）
        room_schedule_room[room_zone_name], room_schedule_light[room_zone_name], room_schedule_person[room_zone_name], \
        room_schedule_oa_app[room_zone_name], room_day_mode[room_zone_name] = \
            bc.get_room_usage_schedule(input_data["air_conditioning_zone"][room_zone_name]["building_type"],
                                     input_data["air_conditioning_zone"][room_zone_name]["room_type"], input_calendar)

        # 空調対象面積の合計
        result_json["total_area"] += input_data["air_conditioning_zone"][room_zone_name]["zone_area"]

    # ----------------------------------------------------------------------------------
    # 任意評定 （SP-7: 室スケジュール)
    # ----------------------------------------------------------------------------------

    if "room_schedule" in input_data["special_input_data"]:

        # 空調ゾーン毎にループ
        for room_zone_name in input_data["air_conditioning_zone"]:

            # SP-7に入力されていれば
            if room_zone_name in input_data["special_input_data"]["room_schedule"]:

                # 使用時間帯
                room_day_mode[room_zone_name] = input_data["special_input_data"]["room_schedule"][room_zone_name][
                    "room_day_mode"]

                if "室の同時使用率" in input_data["special_input_data"]["room_schedule"][room_zone_name]["schedule"]:
                    room_schedule_room_tmp = np.array(
                        input_data["special_input_data"]["room_schedule"][room_zone_name]["schedule"][
                            "室の同時使用率"]).astype("float")
                    room_schedule_room_tmp = np.where(room_schedule_room_tmp < 1, 0, room_schedule_room_tmp)  # 同時使用率は考えない
                    room_schedule_room[room_zone_name] = room_schedule_room_tmp
                if "照明発熱密度比率" in input_data["special_input_data"]["room_schedule"][room_zone_name]["schedule"]:
                    room_schedule_light[room_zone_name] = np.array(
                        input_data["special_input_data"]["room_schedule"][room_zone_name]["schedule"]["照明発熱密度比率"])
                if "人体発熱密度比率" in input_data["special_input_data"]["room_schedule"][room_zone_name]["schedule"]:
                    room_schedule_person[room_zone_name] = np.array(
                        input_data["special_input_data"]["room_schedule"][room_zone_name]["schedule"]["人体発熱密度比率"])
                if "機器発熱密度比率" in input_data["special_input_data"]["room_schedule"][room_zone_name]["schedule"]:
                    room_schedule_oa_app[room_zone_name] = np.array(
                        input_data["special_input_data"]["room_schedule"][room_zone_name]["schedule"]["機器発熱密度比率"])

    # ----------------------------------------------------------------------------------
    # 室負荷計算（解説書 2.4）
    # ----------------------------------------------------------------------------------

    # 結果格納用の変数 result_json　（室負荷）
    for room_zone_name in input_data["air_conditioning_zone"]:
        result_json["q_room"][room_zone_name] = {
            "Troom": np.zeros((365, 24)),  # 時刻別室温　[℃]
            "MRTroom": np.zeros((365, 24)),  # 時刻別平均放射温度　[℃]
            "q_room_hourly": np.zeros((365, 24))  # 時刻別熱取得　[MJ/h]
        }

    # ----------------------------------------------------------------------------------
    # 外壁等の熱貫流率の算出（解説書 附属書A.1）
    # ----------------------------------------------------------------------------------

    # todo : 二つのデータベースにわかれてしまっているので統一する。

    # 標準入力法建材データの読み込み
    with open(database_directory + 'heat_thermal_conductivity.json', 'r', encoding='utf-8') as f:
        heat_thermal_conductivity = json.load(f)

    # モデル建物法建材データの読み込み
    with open(database_directory + 'heat_thermal_conductivity_model.json', 'r', encoding='utf-8') as f:
        heat_thermal_conductivity_model = json.load(f)

    if "wall_configure" in input_data:  # wall_configure があれば以下を実行

        for wall_name in input_data["wall_configure"].keys():

            if input_data["wall_configure"][wall_name]["input_method"] == "断熱材種類を入力":

                if input_data["wall_configure"][wall_name]["material_id"] == "無":  # 断熱材種類が「無」の場合

                    input_data["wall_configure"][wall_name]["u_value_wall"] = 2.63
                    input_data["wall_configure"][wall_name]["u_value_roof"] = 1.53
                    input_data["wall_configure"][wall_name]["u_value_floor"] = 2.67

                else:  # 断熱材種類が「無」以外、もしくは、熱伝導率が直接入力されている場合

                    # 熱伝導率の指定がない場合は「断熱材種類」から推定
                    if input_data["wall_configure"][wall_name]["conductivity"] is None:
                        input_data["wall_configure"][wall_name]["conductivity"] = \
                            float(heat_thermal_conductivity_model[input_data["wall_configure"][wall_name]["material_id"]])

                    # 熱伝導率と厚みとから、熱貫流率を計算（３種類）
                    input_data["wall_configure"][wall_name]["u_value_wall"] = \
                        0.663 * (input_data["wall_configure"][wall_name]["thickness"] / 1000 /
                                 input_data["wall_configure"][wall_name]["conductivity"]) ** (-0.638)
                    input_data["wall_configure"][wall_name]["u_value_roof"] = \
                        0.548 * (input_data["wall_configure"][wall_name]["thickness"] / 1000 /
                                 input_data["wall_configure"][wall_name]["conductivity"]) ** (-0.524)
                    input_data["wall_configure"][wall_name]["u_value_floor"] = \
                        0.665 * (input_data["wall_configure"][wall_name]["thickness"] / 1000 /
                                 input_data["wall_configure"][wall_name]["conductivity"]) ** (-0.641)


            elif input_data["wall_configure"][wall_name]["input_method"] == "建材構成を入力":

                r_value = 0.11 + 0.04

                for layer in enumerate(input_data["wall_configure"][wall_name]["layers"]):

                    # 熱伝導率が空欄である場合、建材名称から熱伝導率を見出す。
                    if layer[1]["conductivity"] is None:

                        if (layer[1]["material_id"] == "密閉中空層") or (layer[1]["material_id"] == "非密閉中空層"):

                            # 空気層の場合
                            r_value += heat_thermal_conductivity[layer[1]["material_id"]]["熱抵抗値"]

                        else:

                            # 空気層以外の断熱材を指定している場合
                            if layer[1]["thickness"] is not None:
                                material_name = layer[1]["material_id"].replace('\u3000', '')
                                r_value += (layer[1]["thickness"] / 1000) / heat_thermal_conductivity[material_name][
                                    "熱伝導率"]

                    else:

                        # 熱伝導率を入力している場合
                        r_value += (layer[1]["thickness"] / 1000) / layer[1]["conductivity"]

                input_data["wall_configure"][wall_name]["u_value"] = 1 / r_value

    # ----------------------------------------------------------------------------------
    # 窓の熱貫流率及び日射熱取得率の算出（解説書 附属書A.2）
    # ----------------------------------------------------------------------------------

    # 窓データの読み込み
    with open(database_directory + 'window_heat_transfer_performance.json', 'r', encoding='utf-8') as f:
        window_heat_transfer_performance = json.load(f)

    with open(database_directory + 'glass2window.json', 'r', encoding='utf-8') as f:
        glass2window = json.load(f)

    if "window_configure" in input_data:

        for window_name in input_data["window_configure"].keys():

            if input_data["window_configure"][window_name]["input_method"] == "ガラスの種類を入力":

                # 建具の種類の読み替え
                if input_data["window_configure"][window_name]["frame_type"] == "木製" or \
                        input_data["window_configure"][window_name]["frame_type"] == "樹脂製":

                    input_data["window_configure"][window_name]["frame_type"] = "木製・樹脂製建具"

                elif input_data["window_configure"][window_name]["frame_type"] == "金属木複合製" or \
                        input_data["window_configure"][window_name]["frame_type"] == "金属樹脂複合製":

                    input_data["window_configure"][window_name]["frame_type"] = "金属木複合製・金属樹脂複合製建具"

                elif input_data["window_configure"][window_name]["frame_type"] == "金属製":

                    input_data["window_configure"][window_name]["frame_type"] = "金属製建具"

                # ガラスIDと建具の種類から、熱貫流率・日射熱取得率を抜き出す。
                input_data["window_configure"][window_name]["u_value"] = \
                    window_heat_transfer_performance \
                        [input_data["window_configure"][window_name]["glass_id"]] \
                        [input_data["window_configure"][window_name]["frame_type"]]["熱貫流率"]

                input_data["window_configure"][window_name]["u_value_blind"] = \
                    window_heat_transfer_performance \
                        [input_data["window_configure"][window_name]["glass_id"]] \
                        [input_data["window_configure"][window_name]["frame_type"]]["熱貫流率・ブラインド込"]

                input_data["window_configure"][window_name]["i_value"] = \
                    window_heat_transfer_performance \
                        [input_data["window_configure"][window_name]["glass_id"]] \
                        [input_data["window_configure"][window_name]["frame_type"]]["日射熱取得率"]

                input_data["window_configure"][window_name]["i_value_blind"] = \
                    window_heat_transfer_performance \
                        [input_data["window_configure"][window_name]["glass_id"]] \
                        [input_data["window_configure"][window_name]["frame_type"]]["日射熱取得率・ブラインド込"]


            elif input_data["window_configure"][window_name]["input_method"] == "ガラスの性能を入力":

                ku_a = 0
                ku_b = 0
                kita = 0
                dR = 0

                # 建具の種類の読み替え
                if input_data["window_configure"][window_name]["frame_type"] == "木製" or \
                        input_data["window_configure"][window_name]["frame_type"] == "樹脂製":

                    input_data["window_configure"][window_name]["frame_type"] = "木製・樹脂製建具"

                elif input_data["window_configure"][window_name]["frame_type"] == "金属木複合製" or \
                        input_data["window_configure"][window_name]["frame_type"] == "金属樹脂複合製":

                    input_data["window_configure"][window_name]["frame_type"] = "金属木複合製・金属樹脂複合製建具"

                elif input_data["window_configure"][window_name]["frame_type"] == "金属製":

                    input_data["window_configure"][window_name]["frame_type"] = "金属製建具"

                # 変換係数
                ku_a = glass2window[input_data["window_configure"][window_name]["frame_type"]][
                           input_data["window_configure"][window_name]["layer_type"]]["ku_a1"] \
                       / glass2window[input_data["window_configure"][window_name]["frame_type"]][
                           input_data["window_configure"][window_name]["layer_type"]]["ku_a2"]
                ku_b = glass2window[input_data["window_configure"][window_name]["frame_type"]][
                           input_data["window_configure"][window_name]["layer_type"]]["ku_b1"] \
                       / glass2window[input_data["window_configure"][window_name]["frame_type"]][
                           input_data["window_configure"][window_name]["layer_type"]]["ku_b2"]
                kita = glass2window[input_data["window_configure"][window_name]["frame_type"]][
                    input_data["window_configure"][window_name]["layer_type"]]["kita"]

                input_data["window_configure"][window_name]["u_value"] = ku_a * input_data["window_configure"][window_name][
                    "glassu_value"] + ku_b
                input_data["window_configure"][window_name]["i_value"] = kita * input_data["window_configure"][window_name][
                    "glassi_value"]

                # ガラスの熱貫流率と日射熱取得率が入力されている場合は、ブラインドの効果を見込む
                dR = (0.021 / input_data["window_configure"][window_name]["glassu_value"]) + 0.022

                input_data["window_configure"][window_name]["u_value_blind"] = \
                    1 / ((1 / input_data["window_configure"][window_name]["u_value"]) + dR)

                input_data["window_configure"][window_name]["i_value_blind"] = \
                    input_data["window_configure"][window_name]["i_value"] / input_data["window_configure"][window_name][
                        "glassi_value"] \
                    * (-0.1331 * input_data["window_configure"][window_name]["glassi_value"] ** 2 +
                       0.8258 * input_data["window_configure"][window_name]["glassi_value"])


            elif input_data["window_configure"][window_name]["input_method"] == "性能値を入力":

                input_data["window_configure"][window_name]["u_value"] = input_data["window_configure"][window_name][
                    "windowu_value"]
                input_data["window_configure"][window_name]["i_value"] = input_data["window_configure"][window_name][
                    "windowi_value"]

                # ブラインド込みの値を計算
                dR = 0

                if input_data["window_configure"][window_name]["glassu_value"] is None or \
                        input_data["window_configure"][window_name]["glassi_value"] is None:

                    input_data["window_configure"][window_name]["u_value_blind"] = \
                    input_data["window_configure"][window_name]["windowu_value"]
                    input_data["window_configure"][window_name]["i_value_blind"] = \
                    input_data["window_configure"][window_name]["windowi_value"]

                else:
                    # ガラスの熱貫流率と日射熱取得率が入力されている場合は、ブラインドの効果を見込む
                    dR = (0.021 / input_data["window_configure"][window_name]["glassu_value"]) + 0.022

                    input_data["window_configure"][window_name]["u_value_blind"] = \
                        1 / ((1 / input_data["window_configure"][window_name]["windowu_value"]) + dR)

                    input_data["window_configure"][window_name]["i_value_blind"] = \
                        input_data["window_configure"][window_name]["windowi_value"] / \
                        input_data["window_configure"][window_name]["glassi_value"] \
                        * (-0.1331 * input_data["window_configure"][window_name]["glassi_value"] ** 2 +
                           0.8258 * input_data["window_configure"][window_name]["glassi_value"])

            if debug:  # pragma: no cover
                print(f'--- 窓名称 {window_name} ---')
                print(f'窓の熱貫流率 u_value : {input_data["window_configure"][window_name]["u_value"]}')
                print(f'窓+BLの熱貫流率 u_value_blind : {input_data["window_configure"][window_name]["u_value_blind"]}')

    # ----------------------------------------------------------------------------------
    # 外壁の面積の計算（解説書 2.4.2.1）
    # ----------------------------------------------------------------------------------

    # 外皮面積の算出
    for room_zone_name in input_data["envelope_set"]:

        for wall_id, wall_configure in enumerate(input_data["envelope_set"][room_zone_name]["wall_list"]):

            if input_data["envelope_set"][room_zone_name]["wall_list"][wall_id][
                "envelope_area"] is None:  # 外皮面積が空欄であれば、外皮の寸法から面積を計算。

                input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["envelope_area"] = \
                    wall_configure["envelope_width"] * wall_configure["envelope_height"]

    # 窓面積の算出
    for window_id in input_data["window_configure"]:
        if input_data["window_configure"][window_id]["window_area"] is None:  # 窓面積が空欄であれば、窓寸法から面積を計算。
            input_data["window_configure"][window_id]["window_area"] = \
                input_data["window_configure"][window_id]["window_width"] * input_data["window_configure"][window_id][
                    "window_height"]

    # 外壁面積の算出
    for room_zone_name in input_data["envelope_set"]:

        for (wall_id, wall_configure) in enumerate(input_data["envelope_set"][room_zone_name]["wall_list"]):

            window_total = 0  # 窓面積の集計用

            if "window_list" in wall_configure:  # 窓がある場合

                # 窓面積の合計を求める（Σ{窓面積×枚数}）
                for (window_id, window_configure) in enumerate(wall_configure["window_list"]):

                    if window_configure["window_id"] != "無":
                        window_total += \
                            input_data["window_configure"][window_configure["window_id"]]["window_area"] * window_configure[
                                "window_number"]

            # 壁のみの面積（窓がない場合は、window_total = 0）
            if wall_configure["envelope_area"] >= window_total:
                input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["wall_area"] = wall_configure[
                                                                                                "envelope_area"] - window_total
            else:
                print(room_zone_name)
                print(wall_configure)
                raise Exception('窓面積が外皮面積よりも大きくなっています')

    # ----------------------------------------------------------------------------------
    # 室の定常熱取得の計算（解説書 2.4.2.2〜2.4.2.7）
    # ----------------------------------------------------------------------------------

    # envelope_set に wall_configure, window_configure の情報を貼り付ける。
    for room_zone_name in input_data["envelope_set"]:

        # 壁毎にループ
        for (wall_id, wall_configure) in enumerate(input_data["envelope_set"][room_zone_name]["wall_list"]):

            if input_data["wall_configure"][wall_configure["wall_spec"]]["input_method"] == "断熱材種類を入力":

                if wall_configure["direction"] == "水平（上）":  # 天井と見なす。

                    input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["U_wall"] = \
                        input_data["wall_configure"][wall_configure["wall_spec"]]["u_value_roof"]
                    input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["wall_area"] = wall_configure[
                        "wall_area"]

                elif wall_configure["direction"] == "水平（下）":  # 床と見なす。

                    input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["U_wall"] = \
                        input_data["wall_configure"][wall_configure["wall_spec"]]["u_value_floor"]
                    input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["wall_area"] = wall_configure[
                        "wall_area"]

                else:

                    input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["U_wall"] = \
                        input_data["wall_configure"][wall_configure["wall_spec"]]["u_value_wall"]
                    input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["wall_area"] = wall_configure[
                        "wall_area"]

            else:

                input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["U_wall"] = \
                    input_data["wall_configure"][wall_configure["wall_spec"]]["u_value"]
                input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["wall_area"] = wall_configure["wall_area"]

            for (window_id, window_configure) in enumerate(
                    input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["window_list"]):

                if window_configure["window_id"] != "無":

                    # 日よけ効果係数の算出
                    if window_configure["eaves_id"] == "無":

                        input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["window_list"][window_id][
                            "shading_effect_C"] = 1
                        input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["window_list"][window_id][
                            "shading_effect_h"] = 1

                    else:

                        if input_data["shading_config"][window_configure["eaves_id"]]["shading_effect_C"] is not None and \
                                input_data["shading_config"][window_configure["eaves_id"]]["shading_effect_h"] is not None:

                            input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["window_list"][window_id][
                                "shading_effect_C"] = \
                                input_data["shading_config"][window_configure["eaves_id"]]["shading_effect_C"]
                            input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["window_list"][window_id][
                                "shading_effect_h"] = \
                                input_data["shading_config"][window_configure["eaves_id"]]["shading_effect_h"]

                        else:

                            # 関数 shading.calc_shading_coefficient で日よけ効果係数を算出。
                            (input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["window_list"][window_id][
                                 "shading_effect_C"],
                             input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["window_list"][window_id][
                                 "shading_effect_h"]) = \
                                shading.calc_shading_coefficient(input_data["building"]["region"],
                                                                wall_configure["direction"],
                                                                input_data["shading_config"][
                                                                    window_configure["eaves_id"]]["x1"],
                                                                input_data["shading_config"][
                                                                    window_configure["eaves_id"]]["x2"],
                                                                input_data["shading_config"][
                                                                    window_configure["eaves_id"]]["x3"],
                                                                input_data["shading_config"][
                                                                    window_configure["eaves_id"]]["y1"],
                                                                input_data["shading_config"][
                                                                    window_configure["eaves_id"]]["y2"],
                                                                input_data["shading_config"][
                                                                    window_configure["eaves_id"]]["y3"],
                                                                input_data["shading_config"][
                                                                    window_configure["eaves_id"]]["zxplus"],
                                                                input_data["shading_config"][
                                                                    window_configure["eaves_id"]]["zxminus"],
                                                                input_data["shading_config"][
                                                                    window_configure["eaves_id"]]["zyplus"],
                                                                input_data["shading_config"][
                                                                    window_configure["eaves_id"]]["zyminus"])

                    # 窓のUA（熱貫流率×面積）を計算
                    if window_configure["is_blind"] == "無":  # ブラインドがない場合

                        input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["window_list"][window_id][
                            "U_window"] = \
                            input_data["window_configure"][window_configure["window_id"]]["u_value"]
                        input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["window_list"][window_id][
                            "I_window"] = \
                            input_data["window_configure"][window_configure["window_id"]]["i_value"]
                        input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["window_list"][window_id][
                            "window_area"] = \
                            window_configure["window_number"] * \
                            input_data["window_configure"][window_configure["window_id"]]["window_area"]

                    elif window_configure["is_blind"] == "有":  # ブラインドがある場合

                        input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["window_list"][window_id][
                            "U_window"] = \
                            input_data["window_configure"][window_configure["window_id"]]["u_value_blind"]
                        input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["window_list"][window_id][
                            "I_window"] = \
                            input_data["window_configure"][window_configure["window_id"]]["i_value_blind"]
                        input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["window_list"][window_id][
                            "window_area"] = \
                            window_configure["window_number"] * \
                            input_data["window_configure"][window_configure["window_id"]]["window_area"]

                    # 任意入力 SP-8
                    if "window_i_value" in input_data["special_input_data"]:
                        if window_configure["window_id"] in input_data["special_input_data"]["window_i_value"]:
                            input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["window_list"][window_id][
                                "IA_window"] = \
                                window_configure["window_number"] * \
                                input_data["window_configure"][window_configure["window_id"]]["window_area"] * \
                                np.array(input_data["special_input_data"]["window_i_value"][window_configure["window_id"]])

    # ----------------------------------------------------------------------------------
    # 室負荷の計算（解説書 2.4.3、2.4.4）
    # ----------------------------------------------------------------------------------

    heat_light_hourly = {}
    Num_of_Person_hourly = {}
    heat_oaapp_hourly = {}

    for room_zone_name in input_data["air_conditioning_zone"]:

        # 室が使用されているか否か＝空調運転時間（365日分）
        btype = input_data["air_conditioning_zone"][room_zone_name]["building_type"]
        rtype = input_data["air_conditioning_zone"][room_zone_name]["room_type"]

        # 発熱量参照値 [W/m2] を読み込む関数（空調） SP-9
        if "room_usage_condition" in input_data["special_input_data"]:
            (room_heat_gain_light, room_heat_gain_person, room_heat_gain_oaapp, room_num_of_person) = \
                bc.get_room_heat_gain(btype, rtype, input_data["special_input_data"]["room_usage_condition"])
        else:
            (room_heat_gain_light, room_heat_gain_person, room_heat_gain_oaapp, room_num_of_person) = \
                bc.get_room_heat_gain(btype, rtype)

        # 様式4から照明発熱量を読み込む
        if BUILELIB_MODE:
            if room_zone_name in input_data["lighting_systems"]:
                lighting_power = 0
                for unit_name in input_data["lighting_systems"][room_zone_name]["lighting_unit"]:
                    lighting_power += input_data["lighting_systems"][room_zone_name]["lighting_unit"][unit_name][
                                          "rated_power"] * \
                                      input_data["lighting_systems"][room_zone_name]["lighting_unit"][unit_name]["number"]
                room_heat_gain_light = lighting_power / input_data["air_conditioning_zone"][room_zone_name]["zone_area"]

        # 時刻別計算用（本来はこのループに入れるべきではない → 時刻別計算の方に入れるべき）
        heat_light_hourly[room_zone_name] = room_schedule_light[room_zone_name] * room_heat_gain_light  # 照明からの発熱 （365日分）
        Num_of_Person_hourly[room_zone_name] = room_schedule_person[room_zone_name] * room_num_of_person  # 人員密度（365日分）
        heat_oaapp_hourly[room_zone_name] = room_schedule_oa_app[room_zone_name] * room_heat_gain_oaapp  # 機器からの発熱 （365日分）

    # ----------------------------------------------------------------------------------
    # 動的室負荷計算
    # ----------------------------------------------------------------------------------

    # 負荷計算モジュールの読み込み
    from .heat_load_calculation import Main
    import copy

    # ファイルの読み込み
    with open('./builelib/heat_load_calculation/heat_load_calculation_template.json', 'r', encoding='utf-8') as js:
        # with open('input_non_residential.json', 'r', encoding='utf-8') as js:
        input_heatcalc_template = json.load(js)

    # 入力ファイルの生成（共通）
    # 地域
    input_heatcalc_template["common"]["region"] = input_data["building"]["region"]
    input_heatcalc_template["common"]["is_residential"] = False

    # 室温上限値・下限
    input_heatcalc_template["rooms"][0]["schedule"]["temperature_upper_limit"] = bc.trans_36524to8760(
        result_json["schedule"]["room_temperature_setpoint"])
    input_heatcalc_template["rooms"][0]["schedule"]["temperature_lower_limit"] = bc.trans_36524to8760(
        result_json["schedule"]["room_temperature_setpoint"])

    # 相対湿度上限値・下限
    input_heatcalc_template["rooms"][0]["schedule"]["relative_humidity_upper_limit"] = bc.trans_36524to8760(
        result_json["schedule"]["room_humidity_setpoint"])
    input_heatcalc_template["rooms"][0]["schedule"]["relative_humidity_lower_limit"] = bc.trans_36524to8760(
        result_json["schedule"]["room_humidity_setpoint"])

    # 非住宅では使わない
    input_heatcalc_template["rooms"][0]["vent"] = 0
    input_heatcalc_template["rooms"][0]["schedule"]["heat_generation_cooking"] = np.zeros(8760)
    input_heatcalc_template["rooms"][0]["schedule"]["vapor_generation_cooking"] = np.zeros(8760)
    input_heatcalc_template["rooms"][0]["schedule"]["local_vent_amount"] = np.zeros(8760)

    # 空調ゾーン毎に負荷を計算
    for room_zone_name in input_data["air_conditioning_zone"]:

        # 入力ファイルの読み込み
        input_heatcalc = copy.deepcopy(input_heatcalc_template)

        # 入力ファイルの生成（室単位）

        # 室名
        input_heatcalc["rooms"][0]["name"] = room_zone_name
        # 気積 [m3]
        input_heatcalc["rooms"][0]["volume"] = input_data["air_conditioning_zone"][room_zone_name]["zone_area"] * \
                                               input_data["air_conditioning_zone"][room_zone_name]["ceiling_height"]

        # 室温湿度の上下限
        input_heatcalc["rooms"][0]["schedule"]["is_upper_temp_limit_set"] = np.reshape(
            np.array(room_schedule_room[room_zone_name], dtype="bool"), 8760)
        input_heatcalc["rooms"][0]["schedule"]["is_lower_temp_limit_set"] = np.reshape(
            np.array(room_schedule_room[room_zone_name], dtype="bool"), 8760)
        input_heatcalc["rooms"][0]["schedule"]["is_upper_humidity_limit_set"] = np.reshape(
            np.array(room_schedule_room[room_zone_name], dtype="bool"), 8760)
        input_heatcalc["rooms"][0]["schedule"]["is_lower_humidity_limit_set"] = np.reshape(
            np.array(room_schedule_room[room_zone_name], dtype="bool"), 8760)

        # 発熱量
        # 照明発熱スケジュール[W]
        input_heatcalc["rooms"][0]["schedule"]["heat_generation_lighting"] = np.reshape(
            heat_light_hourly[room_zone_name], 8760) * input_data["air_conditioning_zone"][room_zone_name][
                                                                                 "zone_area"]
        # 機器発熱スケジュール[W]
        input_heatcalc["rooms"][0]["schedule"]["heat_generation_appliances"] = np.reshape(
            heat_oaapp_hourly[room_zone_name], 8760) * \
                                                                               input_data["air_conditioning_zone"][
                                                                                   room_zone_name]["zone_area"]
        # 人員数[人]
        input_heatcalc["rooms"][0]["schedule"]["number_of_people"] = np.reshape(Num_of_Person_hourly[room_zone_name],
                                                                                8760) * \
                                                                     input_data["air_conditioning_zone"][room_zone_name][
                                                                         "zone_area"]

        # 床の面積（計算対象床面積を入力する）
        input_heatcalc["rooms"][0]["boundaries"][0]["area"] = \
            input_data["air_conditioning_zone"][room_zone_name]["zone_area"]

        # 天井の面積（床と同じとする）
        input_heatcalc["rooms"][0]["boundaries"][1]["area"] = \
            input_data["air_conditioning_zone"][room_zone_name]["zone_area"]

        # 外皮があれば
        if room_zone_name in input_data["envelope_set"]:

            # 外壁
            for (wall_id, wall_configure) in enumerate(input_data["envelope_set"][room_zone_name]["wall_list"]):

                # 等価R値
                if input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["U_wall"] > 4:
                    equivalent_r_value = 0.001
                else:
                    equivalent_r_value = (
                                1 / input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["U_wall"] - 0.25)

                direction = ""
                if input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["direction"] == "北":
                    direction = "n"
                elif input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["direction"] == "北東":
                    direction = "ne"
                elif input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["direction"] == "東":
                    direction = "e"
                elif input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["direction"] == "南東":
                    direction = "se"
                elif input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["direction"] == "南":
                    direction = "s"
                elif input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["direction"] == "南西":
                    direction = "sw"
                elif input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["direction"] == "西":
                    direction = "w"
                elif input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["direction"] == "北西":
                    direction = "nw"
                elif input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["direction"] == "水平（上）":
                    direction = "top"
                elif input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["direction"] == "水平（下）":
                    direction = "bottom"
                else:
                    raise Exception("方位が不正です")

                boundary_type = ""
                is_sun_striked_outside = ""
                if input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["wall_type"] == "日の当たる外壁":
                    boundary_type = "external_general_part"
                    is_sun_striked_outside = True
                elif input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["wall_type"] == "日の当たらない外壁":
                    boundary_type = "external_general_part"
                    is_sun_striked_outside = False
                elif input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["wall_type"] == "地盤に接する外壁":
                    boundary_type = "ground"
                    is_sun_striked_outside = False
                elif input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["wall_type"] == "地盤に接する外壁_Ver2":
                    boundary_type = "ground"
                    is_sun_striked_outside = False

                if boundary_type == "external_general_part":

                    input_heatcalc["rooms"][0]["boundaries"].append(
                        {
                            "name": "wall",
                            "boundary_type": boundary_type,
                            "area": input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["wall_area"],
                            "is_sun_striked_outside": is_sun_striked_outside,
                            "temp_dif_coef": 0,
                            "direction": direction,
                            "is_solar_absorbed_inside": False,
                            "general_part_spec":
                                {
                                    "outside_emissivity": 0.9,
                                    "outside_solar_absorption": 0.8,
                                    "inside_heat_transfer_resistance": 0.11,
                                    "outside_heat_transfer_resistance": 0.04,
                                    "layers": [
                                        {
                                            "name": "コンクリート",
                                            "thermal_resistance": 0.10,
                                            "thermal_capacity": 300
                                        },
                                        {
                                            "name": "吹付け硬質ウレタンフォーム",
                                            "thermal_resistance": equivalent_r_value,
                                            "thermal_capacity": 1.00
                                        }
                                    ],
                                },
                            "solar_shading_part": {
                                "existence": False
                            },
                        }
                    )

                elif boundary_type == "ground":

                    input_heatcalc["rooms"][0]["boundaries"].append(
                        {
                            "name": "wall",
                            "boundary_type": boundary_type,
                            "area": input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["wall_area"],
                            "is_sun_striked_outside": is_sun_striked_outside,
                            "temp_dif_coef": 0,
                            "direction": direction,
                            "is_solar_absorbed_inside": False,
                            "ground_spec":
                                {
                                    "inside_heat_transfer_resistance": 0.11,
                                    "layers": [
                                        {
                                            "name": "コンクリート",
                                            "thermal_resistance": 0.10,
                                            "thermal_capacity": 300
                                        },
                                        {
                                            "name": "吹付け硬質ウレタンフォーム",
                                            "thermal_resistance": equivalent_r_value,
                                            "thermal_capacity": 1.00
                                        }
                                    ],
                                }
                        }
                    )

                # 窓
                for (window_id, window_configure) in enumerate(
                        input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["window_list"]):

                    if window_configure["window_id"] != "無":
                        input_heatcalc["rooms"][0]["boundaries"].append(
                            {
                                "name": "window",
                                "boundary_type": "external_transparent_part",
                                "area": input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["window_list"][
                                    window_id]["window_area"],
                                "is_sun_striked_outside": True,
                                "temp_dif_coef": 0,
                                "direction": direction,
                                "is_solar_absorbed_inside": False,
                                "transparent_opening_part_spec": {
                                    "eta_value":
                                        input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["window_list"][
                                            window_id]["I_window"],
                                    "u_value":
                                        input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["window_list"][
                                            window_id]["U_window"],
                                    "outside_emissivity": 0.8,
                                    "inside_heat_transfer_resistance": 0.11,
                                    "outside_heat_transfer_resistance": 0.04,
                                    "incident_angle_characteristics": "1"
                                },
                                "solar_shading_part": {
                                    "existence": False
                                }
                            }
                        )

        # デバッグ用
        # with open("heat_loadcalc_input.json",'w', encoding='utf-8') as fw:
        #     json.dump(input_heatcalc, fw, indent=4, ensure_ascii=False, cls = bc.MyEncoder)

        # 負荷計算の実行
        room_air_temperature, mean_radiant_temperature, heat_load_sensible_convection, heat_load_sensible_radiation, heat_load_latent \
            = Main.run(input_heatcalc)

        # 室温
        result_json["q_room"][room_zone_name]["Troom"] = bc.trans_8760to36524(room_air_temperature)
        result_json["q_room"][room_zone_name]["MRTroom"] = bc.trans_8760to36524(mean_radiant_temperature)

        # 負荷の積算（全熱負荷）[W] (365×24)
        heat_load = np.array(
            bc.trans_8760to36524(heat_load_sensible_convection) + \
            bc.trans_8760to36524(heat_load_sensible_radiation) + \
            bc.trans_8760to36524(heat_load_latent)
        )

        for dd in range(0, 365):
            for hh in range(0, 24):
                # 時刻別室負荷 [W] → [MJ/hour]
                result_json["q_room"][room_zone_name]["q_room_hourly"][dd][hh] = (-1) * heat_load[dd][hh] * 3600 / 1000000

    if debug:  # pragma: no cover

        # 熱負荷のグラフ化
        for room_zone_name in input_data["air_conditioning_zone"]:
            mf.hourlyplot(result_json["q_room"][room_zone_name]["Troom"], "室内空気温度： " + room_zone_name, "b",
                          "室内空気温度")
            mf.hourlyplot(result_json["q_room"][room_zone_name]["MRTroom"], "室内平均放射温度 " + room_zone_name, "b",
                          "室内平均放射温度")
            mf.hourlyplot(result_json["q_room"][room_zone_name]["q_room_hourly"], "室負荷： " + room_zone_name, "b",
                          "時刻別室負荷")

    print('室負荷計算完了')

    # ----------------------------------------------------------------------------------
    # 空調機群の一次エネルギー消費量（解説書 2.5）
    # ----------------------------------------------------------------------------------

    # 結果格納用の変数 result_json　（空調機群）
    for ahu_name in input_data["air_handling_system"]:
        result_json["ahu"][ahu_name] = {

            "schedule": np.zeros((365, 24)),  # 時刻別の運転スケジュール（365×24）
            "hoa_hourly": np.zeros((365, 24)),  # 空調運転時間帯の外気エンタルピー

            "Qoa_hourly": np.zeros((365, 24)),  # 日平均外気負荷 [kW]
            "q_room_hourly": np.zeros((365, 24)),  # 時刻別室負荷の積算値 [MJ/h]
            "q_ahu_hourly": np.zeros((365, 24)),  # 時刻別空調負荷 [MJ/day]
            "q_ahu_unprocessed": np.zeros((365, 24)),  # 空調機群の未処理負荷（冷房）[MJ/h]

            "E_fan_hourly": np.zeros((365, 24)),  # 送風機の時刻別エネルギー消費量 [MWh]
            "E_aex_hourly": np.zeros((365, 24)),  # 全熱交換器の時刻別エネルギー消費量 [MWh]

            "economizer": {
                "ahu_vovc": np.zeros((365, 24)),  # 外気冷房運転時の外気風量 [kg/s]
                "q_ahu_oac": np.zeros((365, 24)),  # 外気冷房による負荷削減効果 [MJ/day]
            },

            "load_ratio": np.zeros((365, 24)),  # 時刻別の負荷率

            "Eahu_total": 0,  # 消費電力の合計 [h]
            "ahu_total_time": 0  # 運転時間の合計 [h]
        }

    # ----------------------------------------------------------------------------------
    # 空調機群全体のスペックを整理
    # ----------------------------------------------------------------------------------

    for ahu_name in input_data["air_handling_system"]:

        # 空調機タイプ（1つでも空調機があれば「空調機」と判断する）
        input_data["air_handling_system"][ahu_name]["ahu_type"] = "空調機以外"
        for unit_id, unit_configure in enumerate(input_data["air_handling_system"][ahu_name]["air_handling_unit"]):
            if unit_configure["type"] == "空調機":
                input_data["air_handling_system"][ahu_name]["ahu_type"] = "空調機"
                break

        # 空調機の能力
        input_data["air_handling_system"][ahu_name]["rated_capacity_cooling"] = 0
        input_data["air_handling_system"][ahu_name]["rated_capacity_heating"] = 0
        for unit_id, unit_configure in enumerate(input_data["air_handling_system"][ahu_name]["air_handling_unit"]):
            if unit_configure["rated_capacity_cooling"] is not None:
                input_data["air_handling_system"][ahu_name]["rated_capacity_cooling"] += \
                    unit_configure["rated_capacity_cooling"] * unit_configure["number"]

            if unit_configure["rated_capacity_heating"] is not None:
                input_data["air_handling_system"][ahu_name]["rated_capacity_heating"] += \
                    unit_configure["rated_capacity_heating"] * unit_configure["number"]

        # 送風機単体の定格消費電力（解説書 2.5.8） [kW]
        for unit_id, unit_configure in enumerate(input_data["air_handling_system"][ahu_name]["air_handling_unit"]):
            input_data["air_handling_system"][ahu_name]["air_handling_unit"][unit_id]["fan_power_consumption_total"] = 0
            if unit_configure["fan_power_consumption"] is not None:
                # 送風機の定格消費電力 kW = 1台あたりの消費電力 kW × 台数
                input_data["air_handling_system"][ahu_name]["air_handling_unit"][unit_id]["fan_power_consumption_total"] = \
                    unit_configure["fan_power_consumption"] * unit_configure["number"]

        # 空調機の風量 [m3/h]
        input_data["air_handling_system"][ahu_name]["fan_air_volume"] = 0
        for unit_id, unit_configure in enumerate(input_data["air_handling_system"][ahu_name]["air_handling_unit"]):
            if unit_configure["fan_air_volume"] is not None:
                input_data["air_handling_system"][ahu_name]["fan_air_volume"] += \
                    unit_configure["fan_air_volume"] * unit_configure["number"]

        # 全熱交換器の効率（一番低いものを採用）
        input_data["air_handling_system"][ahu_name]["air_heat_exchange_ratio_cooling"] = None
        input_data["air_handling_system"][ahu_name]["air_heat_exchange_ratio_heating"] = None
        for unit_id, unit_configure in enumerate(input_data["air_handling_system"][ahu_name]["air_handling_unit"]):

            # 冷房の効率
            if unit_configure["air_heat_exchange_ratio_cooling"] is not None:
                if input_data["air_handling_system"][ahu_name]["air_heat_exchange_ratio_cooling"] is None:
                    input_data["air_handling_system"][ahu_name]["air_heat_exchange_ratio_cooling"] = unit_configure[
                        "air_heat_exchange_ratio_cooling"]
                elif input_data["air_handling_system"][ahu_name]["air_heat_exchange_ratio_cooling"] > unit_configure[
                    "air_heat_exchange_ratio_cooling"]:
                    input_data["air_handling_system"][ahu_name]["air_heat_exchange_ratio_cooling"] = unit_configure[
                        "air_heat_exchange_ratio_cooling"]

            # 暖房の効率
            if unit_configure["air_heat_exchange_ratio_heating"] is not None:
                if input_data["air_handling_system"][ahu_name]["air_heat_exchange_ratio_heating"] is None:
                    input_data["air_handling_system"][ahu_name]["air_heat_exchange_ratio_heating"] = unit_configure[
                        "air_heat_exchange_ratio_heating"]
                elif input_data["air_handling_system"][ahu_name]["air_heat_exchange_ratio_heating"] > unit_configure[
                    "air_heat_exchange_ratio_heating"]:
                    input_data["air_handling_system"][ahu_name]["air_heat_exchange_ratio_heating"] = unit_configure[
                        "air_heat_exchange_ratio_heating"]

        # 全熱交換器のバイパス制御の有無（1つでもあればバイパス制御「有」とする）
        input_data["air_handling_system"][ahu_name]["air_heat_exchanger_control"] = "無"
        for unit_id, unit_configure in enumerate(input_data["air_handling_system"][ahu_name]["air_handling_unit"]):
            if (unit_configure["air_heat_exchange_ratio_cooling"] is not None) and (
                    unit_configure["air_heat_exchange_ratio_heating"] is not None):
                if unit_configure["air_heat_exchanger_control"] == "有":
                    input_data["air_handling_system"][ahu_name]["air_heat_exchanger_control"] = "有"

        # 全熱交換器の消費電力 [kW]
        input_data["air_handling_system"][ahu_name]["air_heat_exchanger_power_consumption"] = 0
        for unit_id, unit_configure in enumerate(input_data["air_handling_system"][ahu_name]["air_handling_unit"]):
            if unit_configure["air_heat_exchanger_power_consumption"] is not None:
                input_data["air_handling_system"][ahu_name]["air_heat_exchanger_power_consumption"] += \
                    unit_configure["air_heat_exchanger_power_consumption"] * unit_configure["number"]

        # 全熱交換器の風量 [m3/h]
        input_data["air_handling_system"][ahu_name]["air_heat_exchanger_air_volume"] = 0
        for unit_id, unit_configure in enumerate(input_data["air_handling_system"][ahu_name]["air_handling_unit"]):
            if (unit_configure["air_heat_exchange_ratio_cooling"] is not None) and (
                    unit_configure["air_heat_exchange_ratio_heating"] is not None):
                input_data["air_handling_system"][ahu_name]["air_heat_exchanger_air_volume"] += \
                    unit_configure["fan_air_volume"] * unit_configure["number"]

    # ----------------------------------------------------------------------------------
    # 冷暖同時供給の有無の判定
    # ----------------------------------------------------------------------------------

    for ahu_name in input_data["air_handling_system"]:
        input_data["air_handling_system"][ahu_name]["is_simultaneous_supply"] = "無"
        input_data["air_handling_system"][ahu_name]["is_simultaneous_supply_cooling"] = "無"
        input_data["air_handling_system"][ahu_name]["is_simultaneous_supply_heating"] = "無"
    for pump_name in input_data["secondary_pump_system"]:
        input_data["secondary_pump_system"][pump_name]["is_simultaneous_supply"] = "無"
    for ref_name in input_data["heat_source_system"]:
        input_data["heat_source_system"][ref_name]["is_simultaneous_supply"] = "無"

    for room_zone_name in input_data["air_conditioning_zone"]:

        if input_data["air_conditioning_zone"][room_zone_name]["is_simultaneous_supply"] == "有":

            # 空調機群
            input_data["air_handling_system"][input_data["air_conditioning_zone"][room_zone_name]["ahu_cooling_inside_load"]][
                "is_simultaneous_supply_cooling"] = "有"
            input_data["air_handling_system"][input_data["air_conditioning_zone"][room_zone_name]["ahu_cooling_outdoor_load"]][
                "is_simultaneous_supply_cooling"] = "有"
            input_data["air_handling_system"][input_data["air_conditioning_zone"][room_zone_name]["ahu_heating_inside_load"]][
                "is_simultaneous_supply_heating"] = "有"
            input_data["air_handling_system"][input_data["air_conditioning_zone"][room_zone_name]["ahu_heating_outdoor_load"]][
                "is_simultaneous_supply_heating"] = "有"

            # 熱源群
            id_ref_c1 = \
            input_data["air_handling_system"][input_data["air_conditioning_zone"][room_zone_name]["ahu_cooling_inside_load"]][
                "heat_source_cooling"]
            id_ref_c2 = \
            input_data["air_handling_system"][input_data["air_conditioning_zone"][room_zone_name]["ahu_cooling_outdoor_load"]][
                "heat_source_cooling"]
            id_ref_h1 = \
            input_data["air_handling_system"][input_data["air_conditioning_zone"][room_zone_name]["ahu_heating_inside_load"]][
                "heat_source_heating"]
            id_ref_h2 = \
            input_data["air_handling_system"][input_data["air_conditioning_zone"][room_zone_name]["ahu_heating_outdoor_load"]][
                "heat_source_heating"]

            input_data["heat_source_system"][id_ref_c1]["is_simultaneous_supply"] = "有"
            input_data["heat_source_system"][id_ref_c2]["is_simultaneous_supply"] = "有"
            input_data["heat_source_system"][id_ref_h1]["is_simultaneous_supply"] = "有"
            input_data["heat_source_system"][id_ref_h2]["is_simultaneous_supply"] = "有"

            # 二次ポンプ群
            id_pump_c1 = \
            input_data["air_handling_system"][input_data["air_conditioning_zone"][room_zone_name]["ahu_cooling_inside_load"]][
                "pump_cooling"]
            id_pump_c2 = \
            input_data["air_handling_system"][input_data["air_conditioning_zone"][room_zone_name]["ahu_cooling_outdoor_load"]][
                "pump_cooling"]
            id_pump_h1 = \
            input_data["air_handling_system"][input_data["air_conditioning_zone"][room_zone_name]["ahu_heating_inside_load"]][
                "pump_heating"]
            id_pump_h2 = \
            input_data["air_handling_system"][input_data["air_conditioning_zone"][room_zone_name]["ahu_heating_outdoor_load"]][
                "pump_heating"]

            input_data["secondary_pump_system"][id_pump_c1]["is_simultaneous_supply"] = "有"
            input_data["secondary_pump_system"][id_pump_c2]["is_simultaneous_supply"] = "有"
            input_data["secondary_pump_system"][id_pump_h1]["is_simultaneous_supply"] = "有"
            input_data["secondary_pump_system"][id_pump_h2]["is_simultaneous_supply"] = "有"

        elif input_data["air_conditioning_zone"][room_zone_name]["is_simultaneous_supply"] == "有（室負荷）":

            # 空調機群
            input_data["air_handling_system"][input_data["air_conditioning_zone"][room_zone_name]["ahu_cooling_inside_load"]][
                "is_simultaneous_supply_cooling"] = "有"
            input_data["air_handling_system"][input_data["air_conditioning_zone"][room_zone_name]["ahu_heating_inside_load"]][
                "is_simultaneous_supply_heating"] = "有"

            # 熱源群
            id_ref_c1 = \
            input_data["air_handling_system"][input_data["air_conditioning_zone"][room_zone_name]["ahu_cooling_inside_load"]][
                "heat_source_cooling"]
            id_ref_h1 = \
            input_data["air_handling_system"][input_data["air_conditioning_zone"][room_zone_name]["ahu_heating_inside_load"]][
                "heat_source_heating"]

            input_data["heat_source_system"][id_ref_c1]["is_simultaneous_supply"] = "有"
            input_data["heat_source_system"][id_ref_h1]["is_simultaneous_supply"] = "有"

            # 二次ポンプ群
            id_pump_c1 = \
            input_data["air_handling_system"][input_data["air_conditioning_zone"][room_zone_name]["ahu_cooling_inside_load"]][
                "pump_cooling"]
            id_pump_h1 = \
            input_data["air_handling_system"][input_data["air_conditioning_zone"][room_zone_name]["ahu_heating_inside_load"]][
                "pump_heating"]

            input_data["secondary_pump_system"][id_pump_c1]["is_simultaneous_supply"] = "有"
            input_data["secondary_pump_system"][id_pump_h1]["is_simultaneous_supply"] = "有"

        elif input_data["air_conditioning_zone"][room_zone_name]["is_simultaneous_supply"] == "有（外気負荷）":

            # 空調機群
            input_data["air_handling_system"][input_data["air_conditioning_zone"][room_zone_name]["ahu_cooling_outdoor_load"]][
                "is_simultaneous_supply_cooling"] = "有"
            input_data["air_handling_system"][input_data["air_conditioning_zone"][room_zone_name]["ahu_heating_outdoor_load"]][
                "is_simultaneous_supply_heating"] = "有"

            # 熱源群
            id_ref_c2 = \
            input_data["air_handling_system"][input_data["air_conditioning_zone"][room_zone_name]["ahu_cooling_outdoor_load"]][
                "heat_source_cooling"]
            id_ref_h2 = \
            input_data["air_handling_system"][input_data["air_conditioning_zone"][room_zone_name]["ahu_heating_outdoor_load"]][
                "heat_source_heating"]

            input_data["heat_source_system"][id_ref_c2]["is_simultaneous_supply"] = "有"
            input_data["heat_source_system"][id_ref_h2]["is_simultaneous_supply"] = "有"

            # 二次ポンプ群
            id_pump_c2 = \
            input_data["air_handling_system"][input_data["air_conditioning_zone"][room_zone_name]["ahu_cooling_outdoor_load"]][
                "pump_cooling"]
            id_pump_h2 = \
            input_data["air_handling_system"][input_data["air_conditioning_zone"][room_zone_name]["ahu_heating_outdoor_load"]][
                "pump_heating"]

            input_data["secondary_pump_system"][id_pump_c2]["is_simultaneous_supply"] = "有"
            input_data["secondary_pump_system"][id_pump_h2]["is_simultaneous_supply"] = "有"

    # 両方とも冷暖同時なら、その空調機群は冷暖同時運転可能とする。
    for ahu_name in input_data["air_handling_system"]:

        if (input_data["air_handling_system"][ahu_name]["is_simultaneous_supply_cooling"] == "有") and \
                (input_data["air_handling_system"][ahu_name]["is_simultaneous_supply_heating"] == "有"):
            input_data["air_handling_system"][ahu_name]["is_simultaneous_supply"] = "有"

    # ----------------------------------------------------------------------------------
    # 空調機群が処理する日積算室負荷（解説書 2.5.1）
    # ----------------------------------------------------------------------------------
    for room_zone_name in input_data["air_conditioning_zone"]:
        # 室内負荷処理用空調機群の名称
        ahu_name = input_data["air_conditioning_zone"][room_zone_name]["ahu_cooling_inside_load"]

        # 当該空調機群が熱を供給する時刻別室負荷を積算する。
        result_json["ahu"][ahu_name]["q_room_hourly"] += result_json["q_room"][room_zone_name]["q_room_hourly"]

    # ----------------------------------------------------------------------------------
    # 空調機群の運転時間（解説書 2.5.2）
    # ----------------------------------------------------------------------------------

    for room_zone_name in input_data["air_conditioning_zone"]:
        # 室内負荷処理用空調機群の名称
        ahu_name = input_data["air_conditioning_zone"][room_zone_name]["ahu_cooling_inside_load"]

        # 室の空調有無 room_schedule_room（365×24）を加算
        result_json["ahu"][ahu_name]["schedule"] += room_schedule_room[room_zone_name]

    for room_zone_name in input_data["air_conditioning_zone"]:
        # 外気負荷処理用空調機群の名称
        ahu_name = input_data["air_conditioning_zone"][room_zone_name]["ahu_cooling_outdoor_load"]

        # 室の空調有無 room_schedule_room（365×24）を加算
        result_json["ahu"][ahu_name]["schedule"] += room_schedule_room[room_zone_name]

    # 各空調機群の運転時間
    for ahu_name in input_data["air_handling_system"]:
        # 運転スケジュールの和が「1以上（どこか一部屋は動いている）」であれば、空調機は稼働しているとする。
        result_json["ahu"][ahu_name]["schedule"][result_json["ahu"][ahu_name]["schedule"] > 1] = 1

        # 時刻別の外気エンタルピー
        result_json["ahu"][ahu_name]["hoa_hourly"] = hoa_hourly

    # ----------------------------------------------------------------------------------
    # 外気負荷[kW]の算出（解説書 2.5.3）
    # ----------------------------------------------------------------------------------

    # 外気導入量 [m3/h]
    for ahu_name in input_data["air_handling_system"]:
        input_data["air_handling_system"][ahu_name]["outdoor_air_volume_cooling"] = 0
        input_data["air_handling_system"][ahu_name]["outdoor_air_volume_heating"] = 0

    for room_zone_name in input_data["air_conditioning_zone"]:

        # 各室の外気導入量 [m3/h]
        if "room_usage_condition" in input_data["special_input_data"]:  # SP-9シートで任意の入力がされている場合

            input_data["air_conditioning_zone"][room_zone_name]["outdoor_air_volume"] = \
                bc.get_room_outdoor_air_volume(
                    input_data["air_conditioning_zone"][room_zone_name]["building_type"],
                    input_data["air_conditioning_zone"][room_zone_name]["room_type"],
                    input_data["special_input_data"]["room_usage_condition"]
                ) * input_data["air_conditioning_zone"][room_zone_name]["zone_area"]

        else:

            input_data["air_conditioning_zone"][room_zone_name]["outdoor_air_volume"] = \
                bc.get_room_outdoor_air_volume(
                    input_data["air_conditioning_zone"][room_zone_name]["building_type"],
                    input_data["air_conditioning_zone"][room_zone_name]["room_type"]
                ) * input_data["air_conditioning_zone"][room_zone_name]["zone_area"]

        # 冷房期間における外気風量 [m3/h]
        input_data["air_handling_system"][input_data["air_conditioning_zone"][room_zone_name]["ahu_cooling_outdoor_load"]][
            "outdoor_air_volume_cooling"] += \
            input_data["air_conditioning_zone"][room_zone_name]["outdoor_air_volume"]

        # 暖房期間における外気風量 [m3/h]
        input_data["air_handling_system"][input_data["air_conditioning_zone"][room_zone_name]["ahu_heating_outdoor_load"]][
            "outdoor_air_volume_heating"] += \
            input_data["air_conditioning_zone"][room_zone_name]["outdoor_air_volume"]

    # 全熱交換効率の補正
    for ahu_name in input_data["air_handling_system"]:

        # 冷房運転時の補正
        if input_data["air_handling_system"][ahu_name]["air_heat_exchange_ratio_cooling"] is not None:
            ahu_aex_eff = input_data["air_handling_system"][ahu_name]["air_heat_exchange_ratio_cooling"] / 100
            aex_ceff = 1 - ((1 / 0.85) - 1) * (1 - ahu_aex_eff) / ahu_aex_eff
            aex_ctol = 0.95
            aex_cbal = 0.67
            input_data["air_handling_system"][ahu_name]["air_heat_exchange_ratio_cooling"] = \
                ahu_aex_eff * aex_ceff * aex_ctol * aex_cbal

        # 暖房運転時の補正
        if input_data["air_handling_system"][ahu_name]["air_heat_exchange_ratio_heating"] is not None:
            ahu_aex_eff = input_data["air_handling_system"][ahu_name]["air_heat_exchange_ratio_heating"] / 100
            aex_ceff = 1 - ((1 / 0.85) - 1) * (1 - ahu_aex_eff) / ahu_aex_eff
            aex_ctol = 0.95
            aex_cbal = 0.67
            input_data["air_handling_system"][ahu_name]["air_heat_exchange_ratio_heating"] = \
                ahu_aex_eff * aex_ceff * aex_ctol * aex_cbal

    # 外気負荷[kW]
    for ahu_name in input_data["air_handling_system"]:

        for dd in range(0, 365):
            for hh in range(0, 24):

                if result_json["ahu"][ahu_name]["schedule"][dd][hh] > 0:  # 空調機が稼働する場合

                    # 運転モードによって場合分け
                    if ac_mode[dd] == "暖房":

                        # 外気導入量 [m3/h]
                        ahuVoa = input_data["air_handling_system"][ahu_name]["outdoor_air_volume_heating"]
                        # 全熱交換風量 [m3/h]
                        ahu_air_exchange_volume = input_data["air_handling_system"][ahu_name]["air_heat_exchanger_air_volume"]

                        # 全熱交換風量（0以上、外気導入量以下とする）
                        if ahu_air_exchange_volume > ahuVoa:
                            ahu_air_exchange_volume = ahuVoa
                        elif ahu_air_exchange_volume <= 0:
                            ahu_air_exchange_volume = 0

                            # 外気負荷の算出
                        if input_data["air_handling_system"][ahu_name][
                            "air_heat_exchange_ratio_heating"] is None:  # 全熱交換器がない場合

                            result_json["ahu"][ahu_name]["Qoa_hourly"][dd][hh] = \
                                (result_json["ahu"][ahu_name]["hoa_hourly"][dd][hh] -
                                 result_json["schedule"]["room_enthalpy"][dd][hh]) * \
                                input_data["air_handling_system"][ahu_name][
                                    "outdoor_air_volume_heating"] * 1.293 / 3600

                        else:  # 全熱交換器がある場合

                            if (result_json["ahu"][ahu_name]["hoa_hourly"][dd][hh] >
                                result_json["schedule"]["room_enthalpy"][dd][hh]) and (
                                    input_data["air_handling_system"][ahu_name]["air_heat_exchanger_control"] == "有"):

                                # バイパス有の場合はそのまま外気導入する。
                                result_json["ahu"][ahu_name]["Qoa_hourly"][dd][hh] = \
                                    (result_json["ahu"][ahu_name]["hoa_hourly"][dd][hh] -
                                     result_json["schedule"]["room_enthalpy"][dd][hh]) * \
                                    input_data["air_handling_system"][ahu_name]["outdoor_air_volume_heating"] * 1.293 / 3600

                            else:

                                # 全熱交換器による外気負荷削減を見込む。
                                result_json["ahu"][ahu_name]["Qoa_hourly"][dd][hh] = \
                                    (result_json["ahu"][ahu_name]["hoa_hourly"][dd][hh] -
                                     result_json["schedule"]["room_enthalpy"][dd][hh]) * \
                                    (input_data["air_handling_system"][ahu_name]["outdoor_air_volume_heating"] -
                                     ahu_air_exchange_volume * input_data["air_handling_system"][ahu_name][
                                         "air_heat_exchange_ratio_heating"]) * 1.293 / 3600


                    elif (ac_mode[dd] == "中間") or (ac_mode[dd] == "冷房"):

                        ahuVoa = input_data["air_handling_system"][ahu_name]["outdoor_air_volume_cooling"]
                        ahu_air_exchange_volume = input_data["air_handling_system"][ahu_name]["air_heat_exchanger_air_volume"]

                        # 全熱交換風量（0以上、外気導入量以下とする）
                        if ahu_air_exchange_volume > ahuVoa:
                            ahu_air_exchange_volume = ahuVoa
                        elif ahu_air_exchange_volume <= 0:
                            ahu_air_exchange_volume = 0

                        # 外気負荷の算出
                        if input_data["air_handling_system"][ahu_name][
                            "air_heat_exchange_ratio_cooling"] is None:  # 全熱交換器がない場合

                            result_json["ahu"][ahu_name]["Qoa_hourly"][dd][hh] = \
                                (result_json["ahu"][ahu_name]["hoa_hourly"][dd][hh] -
                                 result_json["schedule"]["room_enthalpy"][dd][hh]) * \
                                input_data["air_handling_system"][ahu_name][
                                    "outdoor_air_volume_cooling"] * 1.293 / 3600

                        else:  # 全熱交換器がある場合

                            if (result_json["ahu"][ahu_name]["hoa_hourly"][dd][hh] <
                                result_json["schedule"]["room_enthalpy"][dd][hh]) and (
                                    input_data["air_handling_system"][ahu_name]["air_heat_exchanger_control"] == "有"):

                                # バイパス有の場合はそのまま外気導入する。
                                result_json["ahu"][ahu_name]["Qoa_hourly"][dd][hh] = \
                                    (result_json["ahu"][ahu_name]["hoa_hourly"][dd][hh] -
                                     result_json["schedule"]["room_enthalpy"][dd][hh]) * \
                                    input_data["air_handling_system"][ahu_name]["outdoor_air_volume_cooling"] * 1.293 / 3600

                            else:  # 全熱交換器がある場合

                                # 全熱交換器による外気負荷削減を見込む。
                                result_json["ahu"][ahu_name]["Qoa_hourly"][dd][hh] = \
                                    (result_json["ahu"][ahu_name]["hoa_hourly"][dd][hh] -
                                     result_json["schedule"]["room_enthalpy"][dd][hh]) * \
                                    (input_data["air_handling_system"][ahu_name]["outdoor_air_volume_cooling"] -
                                     ahu_air_exchange_volume * input_data["air_handling_system"][ahu_name][
                                         "air_heat_exchange_ratio_cooling"]) * 1.293 / 3600

    # ----------------------------------------------------------------------------------
    # 外気冷房制御による負荷削減量（解説書 2.5.4）
    # ----------------------------------------------------------------------------------

    for ahu_name in input_data["air_handling_system"]:

        for dd in range(0, 365):
            for hh in range(0, 24):

                if result_json["ahu"][ahu_name]["schedule"][dd][hh] > 0:  # 空調機が稼働する場合

                    # 外気冷房効果の推定
                    if (input_data["air_handling_system"][ahu_name]["is_economizer"] == "有") and (
                            result_json["ahu"][ahu_name]["q_room_hourly"][dd][hh] > 0):  # 外気冷房があり、室負荷が冷房要求であれば

                        # 外気冷房運転時の外気風量 [kg/s]
                        result_json["ahu"][ahu_name]["economizer"]["ahu_vovc"][dd][hh] = \
                            result_json["ahu"][ahu_name]["q_room_hourly"][dd][hh] / \
                            ((result_json["schedule"]["room_enthalpy"][dd][hh] -
                              result_json["ahu"][ahu_name]["hoa_hourly"][dd][hh]) * (3600 / 1000))

                        # 上限・下限
                        if result_json["ahu"][ahu_name]["economizer"]["ahu_vovc"][dd][hh] < \
                                input_data["air_handling_system"][ahu_name]["outdoor_air_volume_cooling"] * 1.293 / 3600:

                            # 下限（外気取入量） [m3/h]→[kg/s]
                            result_json["ahu"][ahu_name]["economizer"]["ahu_vovc"][dd][hh] = \
                            input_data["air_handling_system"][ahu_name]["outdoor_air_volume_cooling"] * 1.293 / 3600

                        elif result_json["ahu"][ahu_name]["economizer"]["ahu_vovc"][dd][hh] > \
                                input_data["air_handling_system"][ahu_name]["economizer_max_air_volume"] * 1.293 / 3600:

                            # 上限（給気風量) [m3/h]→[kg/s]
                            result_json["ahu"][ahu_name]["economizer"]["ahu_vovc"][dd][hh] = \
                            input_data["air_handling_system"][ahu_name]["economizer_max_air_volume"] * 1.293 / 3600

                        # 追加すべき外気量（外気冷房用の追加分のみ）[kg/s]
                        result_json["ahu"][ahu_name]["economizer"]["ahu_vovc"][dd][hh] = \
                            result_json["ahu"][ahu_name]["economizer"]["ahu_vovc"][dd][hh] - \
                            input_data["air_handling_system"][ahu_name]["outdoor_air_volume_cooling"] * 1.293 / 3600

                    # 外気冷房による負荷削減効果 [MJ/day]
                    if input_data["air_handling_system"][ahu_name]["is_economizer"] == "有":  # 外気冷房があれば

                        if result_json["ahu"][ahu_name]["economizer"]["ahu_vovc"][dd][hh] > 0:  # 外冷時風量＞０であれば

                            result_json["ahu"][ahu_name]["economizer"]["q_ahu_oac"][dd][hh] = \
                                result_json["ahu"][ahu_name]["economizer"]["ahu_vovc"][dd][hh] * (
                                        result_json["schedule"]["room_enthalpy"][dd][hh] -
                                        result_json["ahu"][ahu_name]["hoa_hourly"][dd][hh]) * 3600 / 1000

    # ----------------------------------------------------------------------------------
    # 日積算空調負荷 q_ahu_c, q_ahu_h の算出（解説書 2.5.5）
    # ----------------------------------------------------------------------------------

    for ahu_name in input_data["air_handling_system"]:

        for dd in range(0, 365):
            for hh in range(0, 24):

                if result_json["ahu"][ahu_name]["schedule"][dd][hh] > 0:  # 空調機が稼働する場合

                    if input_data["air_handling_system"][ahu_name]["is_outdoor_air_cut"] == "無":  # 外気カットがない場合
                        result_json["ahu"][ahu_name]["q_ahu_hourly"][dd][hh] = \
                            result_json["ahu"][ahu_name]["q_room_hourly"][dd][hh] + \
                            result_json["ahu"][ahu_name]["Qoa_hourly"][dd][hh] * 3600 / 1000
                    else:
                        if hh != 0 and result_json["ahu"][ahu_name]["schedule"][dd][hh - 1] == 0:  # 起動時（前の時刻が停止状態）であれば
                            result_json["ahu"][ahu_name]["q_ahu_hourly"][dd][hh] = \
                            result_json["ahu"][ahu_name]["q_room_hourly"][dd][hh]
                        else:
                            result_json["ahu"][ahu_name]["q_ahu_hourly"][dd][hh] = \
                                result_json["ahu"][ahu_name]["q_room_hourly"][dd][hh] + \
                                result_json["ahu"][ahu_name]["Qoa_hourly"][dd][hh] * 3600 / 1000

    print('空調負荷計算完了')

    if debug:  # pragma: no cover

        for ahu_name in input_data["air_handling_system"]:
            # 外気負荷のグラフ化
            mf.hourlyplot(result_json["ahu"][ahu_name]["Qoa_hourly"], "外気負荷： " + ahu_name, "b", "時刻別外気負荷")
            # 外気冷房効果のグラフ化
            mf.hourlyplot(result_json["ahu"][ahu_name]["economizer"]["q_ahu_oac"], "外気冷房による削減熱量： " + ahu_name,
                          "b", "時刻別外気冷房効果")
            mf.hourlyplot(result_json["ahu"][ahu_name]["economizer"]["ahu_vovc"], "外気冷房時の風量： " + ahu_name, "b",
                          "時刻別外気冷房時風量")
            # 空調負荷のグラフ化
            mf.hourlyplot(result_json["ahu"][ahu_name]["q_ahu_hourly"], "空調負荷： " + ahu_name, "b", "時刻別空調負荷")

    # ----------------------------------------------------------------------------------
    # 任意評定用　空調負荷（ SP-10 ）
    # ----------------------------------------------------------------------------------

    if "special_input_data" in input_data:
        if "q_ahu" in input_data["special_input_data"]:

            for ahu_name in input_data["special_input_data"]["q_ahu"]:  # SP-10シートに入力された空調機群毎に処理
                if ahu_name in result_json["ahu"]:  # SP-10シートに入力された室が空調機群として存在していれば

                    for dd in range(0, 365):
                        for hh in range(0, 24):
                            # 空調負荷[kW] → [MJ/h]
                            result_json["ahu"][ahu_name]["q_ahu_hourly"][dd][hh] = \
                            input_data["special_input_data"]["q_ahu"][ahu_name][dd][hh] * 3600 / 1000
                            # 外気冷房は強制的に0とする（既に見込まれているものとする）
                            result_json["ahu"][ahu_name]["economizer"]["q_ahu_oac"][dd][hh] = 0

    # ----------------------------------------------------------------------------------
    # 空調機群の負荷率（解説書 2.5.6）
    # ----------------------------------------------------------------------------------

    for ahu_name in input_data["air_handling_system"]:

        for dd in range(0, 365):
            for hh in range(0, 24):

                if result_json["ahu"][ahu_name]["schedule"][dd][hh] > 0:  # 空調機が稼働する場合

                    # 冷暖同時運転が「有」である場合（季節に依らず、冷却コイル負荷も加熱コイル負荷も処理する）
                    if input_data["air_handling_system"][ahu_name]["is_simultaneous_supply"] == "有":

                        if result_json["ahu"][ahu_name]["q_ahu_hourly"][dd][hh] >= 0:  # 冷房負荷の場合
                            # 冷房時の負荷率 [-]
                            result_json["ahu"][ahu_name]["load_ratio"][dd][hh] = \
                                result_json["ahu"][ahu_name]["q_ahu_hourly"][dd][hh] * 1000 / 3600 / \
                                input_data["air_handling_system"][ahu_name]["rated_capacity_cooling"]
                        else:
                            # 暖房時の負荷率 [-]
                            result_json["ahu"][ahu_name]["load_ratio"][dd][hh] = \
                                (-1) * result_json["ahu"][ahu_name]["q_ahu_hourly"][dd][hh] * 1000 / 3600 / \
                                input_data["air_handling_system"][ahu_name]["rated_capacity_heating"]

                    # 冷暖同時供給が「無」である場合（季節により、冷却コイル負荷か加熱コイル負荷のどちらか一方を処理する）
                    elif input_data["air_handling_system"][ahu_name]["is_simultaneous_supply"] == "無":

                        # 冷房期、中間期の場合
                        if ac_mode[dd] == "冷房" or ac_mode[dd] == "中間":

                            if result_json["ahu"][ahu_name]["q_ahu_hourly"][dd][hh] > 0:  # 冷房負荷の場合
                                result_json["ahu"][ahu_name]["load_ratio"][dd][hh] = \
                                    result_json["ahu"][ahu_name]["q_ahu_hourly"][dd][hh] * 1000 / 3600 / \
                                    input_data["air_handling_system"][ahu_name]["rated_capacity_cooling"]
                            else:
                                result_json["ahu"][ahu_name]["load_ratio"][dd][hh] = 0.01


                        # 暖房期の場合
                        elif ac_mode[dd] == "暖房":

                            if result_json["ahu"][ahu_name]["q_ahu_hourly"][dd][hh] < 0:  # 暖房負荷の場合
                                result_json["ahu"][ahu_name]["load_ratio"][dd][hh] = \
                                    (-1) * result_json["ahu"][ahu_name]["q_ahu_hourly"][dd][hh] * 1000 / 3600 / \
                                    input_data["air_handling_system"][ahu_name]["rated_capacity_heating"]
                            else:
                                result_json["ahu"][ahu_name]["load_ratio"][dd][hh] = 0.01

    if debug:  # pragma: no cover

        for ahu_name in input_data["air_handling_system"]:
            # 空調負荷率のグラフ化
            mf.hourlyplot(result_json["ahu"][ahu_name]["load_ratio"], "空調負荷率： " + ahu_name, "b", "時刻別負荷率")

    # ----------------------------------------------------------------------------------
    # 風量制御方式によって定まる係数（解説書 2.5.7）
    # ----------------------------------------------------------------------------------

    def ahu_control_performance_curve(load_ratio, a4, a3, a2, a1, a0, Vmin):
        """
        空調機群の制御によるエネルギー削減効果（負荷率の関数）
        """

        if load_ratio <= 0:
            saving_factor = 0
        else:
            if load_ratio > 1:
                saving_factor = 1.2
            elif load_ratio == 0:
                saving_factor = 0
            elif load_ratio < Vmin:
                saving_factor = a4 * Vmin ** 4 + a3 * Vmin ** 3 + a2 * Vmin ** 2 + a1 * Vmin ** 1 + a0
            else:
                saving_factor = a4 * load_ratio ** 4 + a3 * load_ratio ** 3 + a2 * load_ratio ** 2 + a1 * load_ratio ** 1 + a0

        return saving_factor

    for ahu_name in input_data["air_handling_system"]:

        for unit_id, unit_configure in enumerate(input_data["air_handling_system"][ahu_name]["air_handling_unit"]):

            # 係数の取得
            if unit_configure["fan_control_type"] in flow_control.keys():

                a4 = flow_control[unit_configure["fan_control_type"]]["a4"]
                a3 = flow_control[unit_configure["fan_control_type"]]["a3"]
                a2 = flow_control[unit_configure["fan_control_type"]]["a2"]
                a1 = flow_control[unit_configure["fan_control_type"]]["a1"]
                a0 = flow_control[unit_configure["fan_control_type"]]["a0"]

                if unit_configure["fan_min_opening_rate"] is None:
                    Vmin = 1
                else:
                    Vmin = unit_configure["fan_min_opening_rate"] / 100

            elif unit_configure["fan_control_type"] == "無":

                a4 = 0
                a3 = 0
                a2 = 0
                a1 = 0
                a0 = 1
                Vmin = 1

            else:
                raise Exception('制御方式が不正です')

            for dd in range(0, 365):
                for hh in range(0, 24):

                    if result_json["ahu"][ahu_name]["schedule"][dd][hh] > 0:
                        # 送風機等の消費電力量 [MWh] = 消費電力[kW] × 効果率[-] × 1時間
                        result_json["ahu"][ahu_name]["E_fan_hourly"][dd][hh] += \
                            input_data["air_handling_system"][ahu_name]["air_handling_unit"][unit_id][
                                "fan_power_consumption_total"] * \
                            ahu_control_performance_curve(result_json["ahu"][ahu_name]["load_ratio"][dd][hh], a4, a3, a2,
                                                          a1, a0, Vmin) / 1000

                        # 運転時間の合計 h
                        result_json["ahu"][ahu_name]["ahu_total_time"] += 1

    # ----------------------------------------------------------------------------------
    # 全熱交換器の消費電力 （解説書 2.5.11）
    # ----------------------------------------------------------------------------------

    for ahu_name in input_data["air_handling_system"]:
        for dd in range(0, 365):
            for hh in range(0, 24):

                if result_json["ahu"][ahu_name]["schedule"][dd][hh] > 0:  # 空調機が稼働する場合

                    # 全熱交換器の消費電力量 MWh
                    result_json["ahu"][ahu_name]["E_aex_hourly"][dd][hh] += \
                        input_data["air_handling_system"][ahu_name]["air_heat_exchanger_power_consumption"] / 1000

    # ----------------------------------------------------------------------------------
    # 空調機群の年間一次エネルギー消費量 （解説書 2.5.12）
    # ----------------------------------------------------------------------------------

    # 送風機と全熱交換器の消費電力の合計 MWh
    for ahu_name in input_data["air_handling_system"]:

        for dd in range(0, 365):
            for hh in range(0, 24):
                result_json["ahu"][ahu_name]["Eahu_total"] += \
                    result_json["ahu"][ahu_name]["E_fan_hourly"][dd][hh] + \
                    result_json["ahu"][ahu_name]["E_aex_hourly"][dd][hh]

                # 空調機群（送風機）のエネルギー消費量 MWh
                result_json["energy"]["E_ahu_fan"] += result_json["ahu"][ahu_name]["E_fan_hourly"][dd][hh]

                # 空調機群（全熱交換器）のエネルギー消費量 MWh
                result_json["energy"]["E_ahu_aex"] += result_json["ahu"][ahu_name]["E_aex_hourly"][dd][hh]

                # 空調機群（送風機+全熱交換器）のエネルギー消費量 MWh/day
                result_json["energy"]["e_fan_mwh_day"][dd] += \
                    result_json["ahu"][ahu_name]["E_fan_hourly"][dd][hh] + \
                    result_json["ahu"][ahu_name]["E_aex_hourly"][dd][hh]

    print('空調機群のエネルギー消費量計算完了')

    if debug:  # pragma: no cover

        for ahu_name in input_data["air_handling_system"]:
            mf.hourlyplot(result_json["ahu"][ahu_name]["E_fan_hourly"], "送風機の消費電力： " + ahu_name, "b",
                          "時刻別送風機消費電力")
            mf.hourlyplot(result_json["ahu"][ahu_name]["E_aex_hourly"], "全熱交換器の消費電力： " + ahu_name, "b",
                          "時刻別全熱交換器消費電力")

            print("----" + ahu_name + "----")
            print(result_json["ahu"][ahu_name]["Eahu_total"])
            print(result_json["ahu"][ahu_name]["ahu_total_time"])

            mf.histgram_matrix_ahu(result_json["ahu"][ahu_name]["load_ratio"],
                                   result_json["ahu"][ahu_name]["q_ahu_hourly"],
                                   result_json["ahu"][ahu_name]["E_fan_hourly"])

    # ----------------------------------------------------------------------------------
    # 二次ポンプ群の一次エネルギー消費量（解説書 2.6）
    # ----------------------------------------------------------------------------------

    # 二次ポンプが空欄であった場合、ダミーの仮想ポンプを追加する。
    number = 0
    for ahu_name in input_data["air_handling_system"]:

        if input_data["air_handling_system"][ahu_name]["pump_cooling"] is None:
            input_data["air_handling_system"][ahu_name]["pump_cooling"] = "dummy_pump_" + str(number)

            input_data["secondary_pump_system"]["dummy_pump_" + str(number)] = {
                "冷房": {
                    "temperature_difference": 0,
                    "is_staging_control": "無",
                    "secondary_pump": [
                        {
                            "number": 0,
                            "rated_water_flow_rate": 0,
                            "rated_power_consumption": 0,
                            "control_type": "無",
                            "min_opening_rate": 100,
                        }
                    ]
                }
            }

            number += 1

        if input_data["air_handling_system"][ahu_name]["pump_heating"] is None:
            input_data["air_handling_system"][ahu_name]["pump_heating"] = "dummy_pump_" + str(number)

            input_data["secondary_pump_system"]["dummy_pump_" + str(number)] = {
                "暖房": {
                    "temperature_difference": 0,
                    "is_staging_control": "無",
                    "secondary_pump": [
                        {
                            "number": 0,
                            "rated_water_flow_rate": 0,
                            "rated_power_consumption": 0,
                            "control_type": "無",
                            "min_opening_rate": 100,
                        }
                    ]
                }
            }

            number += 1

    # 冷房と暖房の二次ポンプ群に分ける。
    for pump_original_name in input_data["secondary_pump_system"]:

        if "冷房" in input_data["secondary_pump_system"][pump_original_name]:
            # 二次ポンプ群名称を置き換え
            pump_name = pump_original_name + "_冷房"
            input_data["pump"][pump_name] = input_data["secondary_pump_system"][pump_original_name]["冷房"]
            input_data["pump"][pump_name]["mode"] = "cooling"

        if "暖房" in input_data["secondary_pump_system"][pump_original_name]:
            # 二次ポンプ群名称を置き換え
            pump_name = pump_original_name + "_暖房"
            input_data["pump"][pump_name] = input_data["secondary_pump_system"][pump_original_name]["暖房"]
            input_data["pump"][pump_name]["mode"] = "heating"

    # ----------------------------------------------------------------------------------
    # 結果格納用の変数 result_json　（二次ポンプ群）
    # ----------------------------------------------------------------------------------

    for pump_name in input_data["pump"]:
        result_json["pump"][pump_name] = {

            "schedule": np.zeros((365, 24)),  # ポンプ時刻別運転スケジュール

            "q_ps_hourly": np.zeros((365, 24)),  # ポンプ負荷 [MJ/h]

            "heatloss_fan": np.zeros((365, 24)),  # ファン発熱量 [MJ/h]
            "heatloss_pump": np.zeros((365, 24)),  # ポンプの発熱量 [MJ/h]

            "load_ratio": np.zeros((365, 24)),  # 時刻別の負荷率
            "number_of_operation": np.zeros((365, 24)),  # 時刻別の負荷率マトリックス番号

            "E_pump": 0,
            "e_pump_mwh_day": np.zeros(365),
            "E_pump_hourly": np.zeros((365, 24))  # ポンプ電力消費量[MWh]

        }

    # ----------------------------------------------------------------------------------
    # 二次ポンプ機群全体のスペックを整理する。
    # ----------------------------------------------------------------------------------

    for pump_name in input_data["pump"]:

        input_data["pump"][pump_name]["ahu_list"] = set()  # 接続される空調機群
        input_data["pump"][pump_name]["q_psr"] = 0  # ポンプ定格能力
        input_data["pump"][pump_name]["control_type"] = set()  # 全台回転数制御かどうか（台数制御がない場合のみ有効）
        input_data["pump"][pump_name]["min_opening_rate"] = 100  # 変流量時最小負荷率の最小値（台数制御がない場合のみ有効）

        # ポンプの台数
        input_data["pump"][pump_name]["number_of_pumps"] = len(input_data["pump"][pump_name]["secondary_pump"])

        # 二次ポンプの能力のリスト
        input_data["pump"][pump_name]["q_psr_list"] = []

        # 二次ポンプ群全体の定格消費電力の合計
        input_data["pump"][pump_name]["rated_power_consumption_total"] = 0

        for unit_id, unit_configure in enumerate(input_data["pump"][pump_name]["secondary_pump"]):

            # 流量の合計（台数×流量）
            input_data["pump"][pump_name]["secondary_pump"][unit_id]["rated_water_flow_rate_total"] = \
                input_data["pump"][pump_name]["secondary_pump"][unit_id]["rated_water_flow_rate"] * \
                input_data["pump"][pump_name]["secondary_pump"][unit_id]["number"]

            # 消費電力の合計（消費電力×流量）
            input_data["pump"][pump_name]["secondary_pump"][unit_id]["rated_power_consumption_total"] = \
                input_data["pump"][pump_name]["secondary_pump"][unit_id]["rated_power_consumption"] * \
                input_data["pump"][pump_name]["secondary_pump"][unit_id]["number"]

            # 二次ポンプ群全体の定格消費電力の合計
            input_data["pump"][pump_name]["rated_power_consumption_total"] += \
                input_data["pump"][pump_name]["secondary_pump"][unit_id]["rated_power_consumption_total"]

            # 制御方式
            input_data["pump"][pump_name]["control_type"].add(
                input_data["pump"][pump_name]["secondary_pump"][unit_id]["control_type"])

            # 変流量時最小負荷率の最小値（台数制御がない場合のみ有効）
            if unit_configure["min_opening_rate"] is None or np.isnan(unit_configure["min_opening_rate"]) == True:
                input_data["pump"][pump_name]["min_opening_rate"] = 100
            elif input_data["pump"][pump_name]["min_opening_rate"] > unit_configure["min_opening_rate"]:
                input_data["pump"][pump_name]["min_opening_rate"] = unit_configure["min_opening_rate"]

        # 全台回転数制御かどうか（台数制御がない場合のみ有効）
        if "無" in input_data["pump"][pump_name]["control_type"]:
            input_data["pump"][pump_name]["control_type"] = "定流量制御がある"
        elif "定流量制御" in input_data["pump"][pump_name]["control_type"]:
            input_data["pump"][pump_name]["control_type"] = "定流量制御がある"
        else:
            input_data["pump"][pump_name]["control_type"] = "すべて変流量制御である"

    # 接続される空調機群
    for ahu_name in input_data["air_handling_system"]:
        input_data["pump"][input_data["air_handling_system"][ahu_name]["pump_cooling"] + "_冷房"]["ahu_list"].add(ahu_name)
        input_data["pump"][input_data["air_handling_system"][ahu_name]["pump_heating"] + "_暖房"]["ahu_list"].add(ahu_name)

    # ----------------------------------------------------------------------------------
    # 二次ポンプ負荷（解説書 2.6.1）
    # ----------------------------------------------------------------------------------

    # 未処理負荷の算出
    for ahu_name in input_data["air_handling_system"]:

        for dd in range(0, 365):
            for hh in range(0, 24):

                if ac_mode[dd] == "暖房":  # 暖房期である場合

                    # 空調負荷が正の値である場合、かつ、冷暖同時供給が無い場合
                    if (result_json["ahu"][ahu_name]["q_ahu_hourly"][dd][hh] > 0) and \
                            (input_data["air_handling_system"][ahu_name]["is_simultaneous_supply_heating"] == "無"):
                        result_json["ahu"][ahu_name]["q_ahu_unprocessed"][dd][hh] += (
                        result_json["ahu"][ahu_name]["q_ahu_hourly"][dd][hh])
                        result_json["ahu"][ahu_name]["q_ahu_hourly"][dd][hh] = 0


                elif (ac_mode[dd] == "冷房") or (ac_mode[dd] == "中間"):

                    # 空調負荷が負の値である場合、かつ、冷暖同時供給が無い場合
                    if (result_json["ahu"][ahu_name]["q_ahu_hourly"][dd][hh] < 0) and \
                            (input_data["air_handling_system"][ahu_name]["is_simultaneous_supply_cooling"] == "無"):
                        result_json["ahu"][ahu_name]["q_ahu_unprocessed"][dd][hh] += (
                        result_json["ahu"][ahu_name]["q_ahu_hourly"][dd][hh])
                        result_json["ahu"][ahu_name]["q_ahu_hourly"][dd][hh] = 0

    # ポンプ負荷の積算
    for pump_name in input_data["pump"]:

        for ahu_name in input_data["pump"][pump_name]["ahu_list"]:

            for dd in range(0, 365):
                for hh in range(0, 24):

                    if input_data["pump"][pump_name]["mode"] == "cooling":  # 冷水ポンプの場合

                        # ファン発熱量 heatloss_fan [MJ/day] の算出（解説書 2.5.10）
                        if input_data["air_handling_system"][ahu_name]["ahu_type"] == "空調機":
                            # ファン発熱量 MWh * 3600 = MJ/h
                            result_json["pump"][pump_name]["heatloss_fan"][dd][hh] = \
                                k_heatup * result_json["ahu"][ahu_name]["E_fan_hourly"][dd][hh] * 3600

                        # 日積算ポンプ負荷 q_ps [MJ/h] の算出

                        # 空調負荷が正である場合
                        if result_json["ahu"][ahu_name]["q_ahu_hourly"][dd][hh] > 0:

                            if result_json["ahu"][ahu_name]["economizer"]["q_ahu_oac"][dd][
                                hh] > 0:  # 外冷時はファン発熱量足さない ⇒ 小さな負荷が出てしまう

                                if abs(result_json["ahu"][ahu_name]["q_ahu_hourly"][dd][hh] -
                                       result_json["ahu"][ahu_name]["economizer"]["q_ahu_oac"][dd][hh]) < 1:
                                    result_json["pump"][pump_name]["q_ps_hourly"][dd][hh] += 0
                                else:
                                    result_json["pump"][pump_name]["q_ps_hourly"][dd][hh] += \
                                        result_json["ahu"][ahu_name]["q_ahu_hourly"][dd][hh] - \
                                        result_json["ahu"][ahu_name]["economizer"]["q_ahu_oac"][dd][hh]
                            else:

                                result_json["pump"][pump_name]["q_ps_hourly"][dd][hh] += \
                                    result_json["ahu"][ahu_name]["q_ahu_hourly"][dd][hh] - \
                                    result_json["ahu"][ahu_name]["economizer"]["q_ahu_oac"][dd][hh] + \
                                    result_json["pump"][pump_name]["heatloss_fan"][dd][hh]


                    elif input_data["pump"][pump_name]["mode"] == "heating":

                        # ファン発熱量 heatloss_fan [MJ/day] の算出（解説書 2.5.10）
                        if input_data["air_handling_system"][ahu_name]["ahu_type"] == "空調機":
                            # ファン発熱量 MWh * 3600 = MJ/h
                            result_json["pump"][pump_name]["heatloss_fan"][dd][hh] = k_heatup * \
                                                                                    result_json["ahu"][ahu_name][
                                                                                        "E_fan_hourly"][dd][hh] * 3600

                        # 日積算ポンプ負荷 q_ps [MJ/day] の算出<符号逆転させる>
                        # 室負荷が冷房要求である場合において空調負荷が正である場合
                        if result_json["ahu"][ahu_name]["q_ahu_hourly"][dd][hh] < 0:
                            result_json["pump"][pump_name]["q_ps_hourly"][dd][hh] += \
                                (-1) * (result_json["ahu"][ahu_name]["q_ahu_hourly"][dd][hh] +
                                        result_json["pump"][pump_name]["heatloss_fan"][dd][hh])

    # ----------------------------------------------------------------------------------
    # 二次ポンプ群の運転時間（解説書 2.6.2）
    # ----------------------------------------------------------------------------------

    for pump_name in input_data["pump"]:

        for ahu_name in input_data["pump"][pump_name]["ahu_list"]:
            result_json["pump"][pump_name]["schedule"] += result_json["ahu"][ahu_name]["schedule"]

        # 運転スケジュールの和が「1以上（接続されている空調機群の1つは動いている）」であれば、二次ポンプは稼働しているとする。
        result_json["pump"][pump_name]["schedule"][result_json["pump"][pump_name]["schedule"] > 1] = 1

    print('ポンプ負荷計算完了')

    if debug:  # pragma: no cover

        for pump_name in input_data["pump"]:
            # ポンプ負荷のグラフ化
            mf.hourlyplot(result_json["pump"][pump_name]["q_ps_hourly"], "ポンプ負荷： " + pump_name, "b", "時刻別ポンプ負荷")

    # ----------------------------------------------------------------------------------
    # 二次ポンプ群の仮想定格能力（解説書 2.6.3）
    # ----------------------------------------------------------------------------------
    for pump_name in input_data["pump"]:

        for unit_id, unit_configure in enumerate(input_data["pump"][pump_name]["secondary_pump"]):
            # 二次ポンプの定格処理能力[kW] = [K] * [m3/h] * [kJ/kg・K] * [kg/m3] * [h/s]
            input_data["pump"][pump_name]["secondary_pump"][unit_id]["q_psr"] = \
                input_data["pump"][pump_name]["temperature_difference"] * unit_configure[
                    "rated_water_flow_rate_total"] * cw * 1000 / 3600
            input_data["pump"][pump_name]["q_psr"] += input_data["pump"][pump_name]["secondary_pump"][unit_id]["q_psr"]

            input_data["pump"][pump_name]["q_psr_list"].append(
                input_data["pump"][pump_name]["secondary_pump"][unit_id]["q_psr"])

    # ----------------------------------------------------------------------------------
    # 二次ポンプ群の負荷率（解説書 2.6.4）
    # ----------------------------------------------------------------------------------

    for pump_name in input_data["pump"]:

        if input_data["pump"][pump_name]["q_psr"] != 0:  # 仮想ポンプ（二次ポンプがないシステム用の仮想ポンプ）は除く

            for dd in range(0, 365):
                for hh in range(0, 24):

                    if result_json["pump"][pump_name]["schedule"][dd][hh] > 0 and (
                            input_data["pump"][pump_name]["q_psr"] > 0):
                        # 負荷率 Lpump[-] = [MJ/h] * [kJ/MJ] / [s/h] / [KJ/s]
                        result_json["pump"][pump_name]["load_ratio"][dd][hh] = \
                            (result_json["pump"][pump_name]["q_ps_hourly"][dd][hh] * 1000 / 3600) / \
                            input_data["pump"][pump_name]["q_psr"]

    if debug:  # pragma: no cover

        for pump_name in input_data["pump"]:
            # ポンプ負荷率のグラフ化
            mf.hourlyplot(result_json["pump"][pump_name]["load_ratio"], "ポンプ負荷率： " + pump_name, "b",
                          "時刻別ポンプ負荷率")

    # ----------------------------------------------------------------------------------
    # 二次ポンプの運転台数
    # ----------------------------------------------------------------------------------

    for pump_name in input_data["pump"]:

        if input_data["pump"][pump_name]["q_psr"] != 0:  # 仮想ポンプ（二次ポンプがないシステム用の仮想ポンプ）は除く

            for dd in range(0, 365):
                for hh in range(0, 24):

                    if result_json["pump"][pump_name]["q_ps_hourly"][dd][hh] > 0:

                        if input_data["pump"][pump_name]["is_staging_control"] == "無":  # 台数制御なし

                            # 運転台数（常に最大の台数） → 台数のマトリックスの表示用
                            result_json["pump"][pump_name]["number_of_operation"][dd][hh] = input_data["pump"][pump_name][
                                "number_of_pumps"]


                        elif input_data["pump"][pump_name]["is_staging_control"] == "有":  # 台数制御あり

                            # 運転台数 number_of_operation
                            rr = 0
                            for rr in range(0, input_data["pump"][pump_name]["number_of_pumps"]):

                                # 1台～rr台までの最大能力合計値
                                if np.sum(input_data["pump"][pump_name]["q_psr_list"][0:rr + 1]) > \
                                        result_json["pump"][pump_name]["q_ps_hourly"][dd][hh] * 1000 / 3600:
                                    break

                            result_json["pump"][pump_name]["number_of_operation"][dd][
                                hh] = rr + 1  # pythonのインデックスと実台数は「1」ずれることに注意。

    # ----------------------------------------------------------------------------------
    # 流量制御方式によって定まる係数（解説書 2.6.7）
    # ----------------------------------------------------------------------------------

    for pump_name in input_data["pump"]:

        for unit_id, unit_configure in enumerate(input_data["pump"][pump_name]["secondary_pump"]):

            if unit_configure["control_type"] in flow_control.keys():

                input_data["pump"][pump_name]["secondary_pump"][unit_id]["a4"] = \
                flow_control[unit_configure["control_type"]]["a4"]
                input_data["pump"][pump_name]["secondary_pump"][unit_id]["a3"] = \
                flow_control[unit_configure["control_type"]]["a3"]
                input_data["pump"][pump_name]["secondary_pump"][unit_id]["a2"] = \
                flow_control[unit_configure["control_type"]]["a2"]
                input_data["pump"][pump_name]["secondary_pump"][unit_id]["a1"] = \
                flow_control[unit_configure["control_type"]]["a1"]
                input_data["pump"][pump_name]["secondary_pump"][unit_id]["a0"] = \
                flow_control[unit_configure["control_type"]]["a0"]

            elif unit_configure["control_type"] == "無":

                input_data["pump"][pump_name]["secondary_pump"][unit_id]["a4"] = 0
                input_data["pump"][pump_name]["secondary_pump"][unit_id]["a3"] = 0
                input_data["pump"][pump_name]["secondary_pump"][unit_id]["a2"] = 0
                input_data["pump"][pump_name]["secondary_pump"][unit_id]["a1"] = 0
                input_data["pump"][pump_name]["secondary_pump"][unit_id]["a0"] = 1
                input_data["pump"][pump_name]["secondary_pump"][unit_id]["min_opening_rate"] = 100

            else:
                raise Exception('制御方式が不正です')

    # ----------------------------------------------------------------------------------
    # 二次ポンプ群ごとの消費電力（解説書 2.6.8）
    # ----------------------------------------------------------------------------------

    def pump_control_performance_curve(load_ratio, a4, a3, a2, a1, a0, Vmin):
        """
        二次ポンプ群の制御によるエネルギー削減効果（負荷率の関数）
        """

        if load_ratio <= 0:
            saving_factor = 0
        else:
            if load_ratio > 1:
                saving_factor = 1.2
            elif load_ratio == 0:
                saving_factor = 0
            elif load_ratio < Vmin:
                saving_factor = a4 * Vmin ** 4 + a3 * Vmin ** 3 + a2 * Vmin ** 2 + a1 * Vmin ** 1 + a0
            else:
                saving_factor = a4 * load_ratio ** 4 + a3 * load_ratio ** 3 + a2 * load_ratio ** 2 + a1 * load_ratio ** 1 + a0

        return saving_factor

    for pump_name in input_data["pump"]:

        if input_data["pump"][pump_name]["q_psr"] != 0:  # 仮想ポンプ（二次ポンプがないシステム用の仮想ポンプ）は除く

            for dd in range(0, 365):
                for hh in range(0, 24):

                    if result_json["pump"][pump_name]["q_ps_hourly"][dd][hh] > 0:

                        if input_data["pump"][pump_name]["is_staging_control"] == "無":  # 台数制御なし

                            # 流量制御方式
                            if input_data["pump"][pump_name]["control_type"] == "すべて変流量制御である":  # 全台VWVであれば

                                # VWVの効果率曲線(1番目の特性を代表して使う)
                                pump_vwv_fac = pump_control_performance_curve(
                                    result_json["pump"][pump_name]["load_ratio"][dd][hh],
                                    input_data["pump"][pump_name]["secondary_pump"][0]["a4"],
                                    input_data["pump"][pump_name]["secondary_pump"][0]["a3"],
                                    input_data["pump"][pump_name]["secondary_pump"][0]["a2"],
                                    input_data["pump"][pump_name]["secondary_pump"][0]["a1"],
                                    input_data["pump"][pump_name]["secondary_pump"][0]["a0"],
                                    input_data["pump"][pump_name]["min_opening_rate"] / 100
                                )

                            else:  # 全台VWVでなければ、定流量とみなす。

                                pump_vwv_fac = pump_control_performance_curve(
                                    result_json["pump"][pump_name]["load_ratio"][dd][hh], 0, 0, 0, 0, 1, 1)

                            # 消費電力（部分負荷特性×定格消費電力）[kW]
                            result_json["pump"][pump_name]["E_pump_hourly"][dd][hh] = pump_vwv_fac * \
                                                                                     input_data["pump"][pump_name][
                                                                                         "rated_power_consumption_total"] / 1000


                        elif input_data["pump"][pump_name]["is_staging_control"] == "有":  # 台数制御あり

                            # 定流量ポンプの処理熱量合計、VWVポンプの台数
                            q_tmp_cw_v = 0
                            num_vwv = result_json["pump"][pump_name]["number_of_operation"][dd][hh]  # 運転台数（定流量＋変流量）

                            for rr in range(0, int(result_json["pump"][pump_name]["number_of_operation"][dd][hh])):

                                if (input_data["pump"][pump_name]["secondary_pump"][rr]["control_type"] == "無") or \
                                        (input_data["pump"][pump_name]["secondary_pump"][rr][
                                             "control_type"] == "定流量制御"):
                                    q_tmp_cw_v += input_data["pump"][pump_name]["secondary_pump"][rr]["q_psr"]
                                    num_vwv = num_vwv - 1

                            # 制御を加味した消費エネルギー mx_pump_power [kW]
                            for rr in range(0, int(result_json["pump"][pump_name]["number_of_operation"][dd][hh])):

                                if (input_data["pump"][pump_name]["secondary_pump"][rr]["control_type"] == "無") or \
                                        (input_data["pump"][pump_name]["secondary_pump"][rr][
                                             "control_type"] == "定流量制御"):

                                    # 定流量制御の効果率
                                    pump_vwv_fac = pump_control_performance_curve(
                                        result_json["pump"][pump_name]["load_ratio"][dd][hh],
                                        0, 0, 0, 0, 1, 1)

                                    result_json["pump"][pump_name]["E_pump_hourly"][dd][hh] += \
                                    input_data["pump"][pump_name]["secondary_pump"][rr][
                                        "rated_power_consumption_total"] * pump_vwv_fac / 1000

                                else:

                                    # 変流量ポンプjの負荷率 [-]
                                    tmpL = ((result_json["pump"][pump_name]["q_ps_hourly"][dd][
                                                 hh] * 1000 / 3600 - q_tmp_cw_v) / num_vwv) \
                                           / input_data["pump"][pump_name]["secondary_pump"][rr]["q_psr"]

                                    # 変流量制御による省エネ効果
                                    pump_vwv_fac = pump_control_performance_curve(
                                        tmpL,
                                        input_data["pump"][pump_name]["secondary_pump"][rr]["a4"],
                                        input_data["pump"][pump_name]["secondary_pump"][rr]["a3"],
                                        input_data["pump"][pump_name]["secondary_pump"][rr]["a2"],
                                        input_data["pump"][pump_name]["secondary_pump"][rr]["a1"],
                                        input_data["pump"][pump_name]["secondary_pump"][rr]["a0"],
                                        input_data["pump"][pump_name]["secondary_pump"][rr]["min_opening_rate"] / 100
                                    )

                                    result_json["pump"][pump_name]["E_pump_hourly"][dd][hh] += \
                                    input_data["pump"][pump_name]["secondary_pump"][rr][
                                        "rated_power_consumption_total"] * pump_vwv_fac / 1000

                                    # ----------------------------------------------------------------------------------
    # 二次ポンプ群全体の年間一次エネルギー消費量（解説書 2.6.10）
    # ----------------------------------------------------------------------------------

    for pump_name in input_data["pump"]:

        for dd in range(0, 365):
            for hh in range(0, 24):
                result_json["pump"][pump_name]["E_pump"] += result_json["pump"][pump_name]["E_pump_hourly"][dd][hh]

                result_json["energy"]["E_pump"] += result_json["pump"][pump_name]["E_pump_hourly"][dd][hh]
                result_json["energy"]["e_pump_mwh_day"][dd] += result_json["pump"][pump_name]["E_pump_hourly"][dd][hh]

    print('二次ポンプ群のエネルギー消費量計算完了')

    if debug:  # pragma: no cover

        for ahu_name in input_data["air_handling_system"]:
            mf.hourlyplot(result_json["ahu"][ahu_name]["q_ahu_unprocessed"], "未処理負荷： " + ahu_name, "b", "未処理負荷")

        for pump_name in input_data["pump"]:
            mf.hourlyplot(result_json["pump"][pump_name]["E_pump_hourly"], "ポンプ消費電力： " + pump_name, "b",
                          "時刻別ポンプ消費電力")

            print("----" + pump_name + "----")
            print(result_json["pump"][pump_name]["E_pump"])

            mf.histgram_matrix_pump(
                result_json["pump"][pump_name]["load_ratio"],
                result_json["pump"][pump_name]["number_of_operation"],
                result_json["pump"][pump_name]["E_pump_hourly"]
            )

    # ----------------------------------------------------------------------------------
    # 二次ポンプ群の発熱量 （解説書 2.6.9）
    # ----------------------------------------------------------------------------------

    for pump_name in input_data["pump"]:

        for dd in range(0, 365):
            for hh in range(0, 24):

                if result_json["pump"][pump_name]["E_pump_hourly"][dd][hh] > 0:
                    # 二次ポンプ群の発熱量 MJ/h
                    result_json["pump"][pump_name]["heatloss_pump"][dd][hh] = \
                        result_json["pump"][pump_name]["E_pump_hourly"][dd][hh] * k_heatup * 3600

    if debug:  # pragma: no cover

        for pump_name in input_data["pump"]:
            mf.hourlyplot(result_json["pump"][pump_name]["heatloss_pump"], "ポンプ発熱量： " + pump_name, "b",
                          "時刻別ポンプ発熱量")

    # ----------------------------------------------------------------------------------
    # 熱源群の一次エネルギー消費量（解説書 2.7）
    # ----------------------------------------------------------------------------------

    # モデル格納用変数

    # 冷房と暖房の熱源群に分ける。
    for ref_original_name in input_data["heat_source_system"]:

        if "冷房" in input_data["heat_source_system"][ref_original_name]:
            input_data["ref"][ref_original_name + "_冷房"] = input_data["heat_source_system"][ref_original_name]["冷房"]
            input_data["ref"][ref_original_name + "_冷房"]["mode"] = "cooling"

            if "冷房(蓄熱)" in input_data["heat_source_system"][ref_original_name]:
                input_data["ref"][ref_original_name + "_冷房_蓄熱"] = input_data["heat_source_system"][ref_original_name][
                    "冷房(蓄熱)"]
                input_data["ref"][ref_original_name + "_冷房_蓄熱"]["is_storage"] = "蓄熱"
                input_data["ref"][ref_original_name + "_冷房_蓄熱"]["mode"] = "cooling"
                input_data["ref"][ref_original_name + "_冷房"]["is_storage"] = "追掛"
                input_data["ref"][ref_original_name + "_冷房"]["storage_type"] = \
                input_data["heat_source_system"][ref_original_name]["冷房(蓄熱)"]["storage_type"]
                input_data["ref"][ref_original_name + "_冷房"]["storage_size"] = \
                input_data["heat_source_system"][ref_original_name]["冷房(蓄熱)"]["storage_size"]
            else:
                input_data["ref"][ref_original_name + "_冷房"]["is_storage"] = "無"

        if "暖房" in input_data["heat_source_system"][ref_original_name]:
            input_data["ref"][ref_original_name + "_暖房"] = input_data["heat_source_system"][ref_original_name]["暖房"]
            input_data["ref"][ref_original_name + "_暖房"]["mode"] = "heating"

            if "暖房(蓄熱)" in input_data["heat_source_system"][ref_original_name]:
                input_data["ref"][ref_original_name + "_暖房_蓄熱"] = input_data["heat_source_system"][ref_original_name][
                    "暖房(蓄熱)"]
                input_data["ref"][ref_original_name + "_暖房_蓄熱"]["is_storage"] = "蓄熱"
                input_data["ref"][ref_original_name + "_暖房_蓄熱"]["mode"] = "heating"
                input_data["ref"][ref_original_name + "_暖房"]["is_storage"] = "追掛"
                input_data["ref"][ref_original_name + "_暖房"]["storage_type"] = \
                input_data["heat_source_system"][ref_original_name]["暖房(蓄熱)"]["storage_type"]
                input_data["ref"][ref_original_name + "_暖房"]["storage_size"] = \
                input_data["heat_source_system"][ref_original_name]["暖房(蓄熱)"]["storage_size"]
            else:
                input_data["ref"][ref_original_name + "_暖房"]["is_storage"] = "無"

    # ----------------------------------------------------------------------------------
    # 蓄熱がある場合の処理（蓄熱槽効率の追加、追掛用熱交換器の検証）
    # ----------------------------------------------------------------------------------

    for ref_name in input_data["ref"]:

        # 蓄熱槽効率
        if input_data["ref"][ref_name]["is_storage"] == "蓄熱" or input_data["ref"][ref_name]["is_storage"] == "追掛":

            input_data["ref"][ref_name]["storage_efficient_ratio"] = 0.8
            if input_data["ref"][ref_name]["storage_type"] == "水蓄熱(混合型)":
                input_data["ref"][ref_name]["storage_efficient_ratio"] = 0.8
            elif input_data["ref"][ref_name]["storage_type"] == "水蓄熱(成層型)":
                input_data["ref"][ref_name]["storage_efficient_ratio"] = 0.9
            elif input_data["ref"][ref_name]["storage_type"] == "氷蓄熱":
                input_data["ref"][ref_name]["storage_efficient_ratio"] = 1.0
            else:
                raise Exception("蓄熱槽タイプが不正です")

        # 蓄熱追掛時の熱交換器の追加
        if input_data["ref"][ref_name]["is_storage"] == "追掛":

            for unit_id, unit_configure in enumerate(input_data["ref"][ref_name]["heat_source"]):
                if unit_id == 0 and input_data["ref"][ref_name]["heat_source"][unit_id]["heat_source_type"] != "熱交換器":

                    # 1台目が熱交換器では無い場合、熱交換器を追加する。
                    input_data["ref"][ref_name]["heat_source"].insert(0,
                                                                    {
                                                                        "heat_source_type": "熱交換器",
                                                                        "number": 1.0,
                                                                        "supply_water_temp_summer": None,
                                                                        "supply_water_temp_middle": None,
                                                                        "supply_water_temp_winter": None,
                                                                        "heat_source_rated_capacity":
                                                                            input_data["ref"][ref_name][
                                                                                "storage_efficient_ratio"] *
                                                                            input_data["ref"][ref_name][
                                                                                "storage_size"] / 8 * (1000 / 3600),
                                                                        "heat_source_rated_power_consumption": 0,
                                                                        "heat_source_rated_fuel_consumption": 0,
                                                                        "heat_source_sub_rated_power_consumption": 0,
                                                                        "primary_pump_power_consumption": 0,
                                                                        "primary_pump_control_type": "無",
                                                                        "cooling_tower_capacity": 0,
                                                                        "cooling_tower_fan_power_consumption": 0,
                                                                        "cooling_tower_pump_power_consumption": 0,
                                                                        "cooling_tower_control_type": "無",
                                                                        "info": ""
                                                                    }
                                                                    )

                # 1台目以外に熱交換器があればエラーを返す。
                elif unit_id > 0 and input_data["ref"][ref_name]["heat_source"][unit_id]["heat_source_type"] == "熱交換器":
                    raise Exception("蓄熱槽があるシステムですが、1台目以外に熱交換器が設定されています")

    # ----------------------------------------------------------------------------------
    # 熱源群全体のスペックを整理する。
    # ----------------------------------------------------------------------------------

    for ref_name in input_data["ref"]:

        input_data["ref"][ref_name]["pump_list"] = set()
        input_data["ref"][ref_name]["num_of_unit"] = 0

        # 熱源群全体の性能
        input_data["ref"][ref_name]["q_ref_rated"] = 0
        for unit_id, unit_configure in enumerate(input_data["ref"][ref_name]["heat_source"]):
            # 定格能力（台数×能力）
            input_data["ref"][ref_name]["heat_source"][unit_id]["heat_source_rated_capacity_total"] = \
                unit_configure["heat_source_rated_capacity"] * unit_configure["number"]

            # 熱源主機の定格消費電力（台数×消費電力）
            input_data["ref"][ref_name]["heat_source"][unit_id]["heat_source_rated_power_consumption_total"] = \
                unit_configure["heat_source_rated_power_consumption"] * unit_configure["number"]

            # 熱源主機の定格燃料消費量（台数×燃料消費量）
            input_data["ref"][ref_name]["heat_source"][unit_id]["heat_source_rated_fuel_consumption_total"] = \
                unit_configure["heat_source_rated_fuel_consumption"] * unit_configure["number"]

            # 熱源補機の定格消費電力（台数×消費電力）
            input_data["ref"][ref_name]["heat_source"][unit_id]["heat_source_sub_rated_power_consumption_total"] = \
                unit_configure["heat_source_sub_rated_power_consumption"] * unit_configure["number"]

            # 熱源機器の台数
            input_data["ref"][ref_name]["num_of_unit"] += 1

            # 一次ポンプの消費電力の合計
            input_data["ref"][ref_name]["heat_source"][unit_id]["primary_pump_power_consumption_total"] = \
                unit_configure["primary_pump_power_consumption"] * unit_configure["number"]

            # 冷却塔ファンの消費電力の合計
            input_data["ref"][ref_name]["heat_source"][unit_id]["cooling_tower_fan_power_consumption_total"] = \
                unit_configure["cooling_tower_fan_power_consumption"] * unit_configure["number"]

            # 冷却塔ポンプの消費電力の合計
            input_data["ref"][ref_name]["heat_source"][unit_id]["cooling_tower_pump_power_consumption_total"] = \
                unit_configure["cooling_tower_pump_power_consumption"] * unit_configure["number"]

        # 蓄熱システムの追掛運転用熱交換器の制約
        if input_data["ref"][ref_name]["is_storage"] == "追掛":

            tmpCapacity = input_data["ref"][ref_name]["storage_efficient_ratio"] * input_data["ref"][ref_name][
                "storage_size"] / 8 * (1000 / 3600)

            # 1台目は必ず熱交換器であると想定
            if input_data["ref"][ref_name]["heat_source"][0]["heat_source_rated_capacity_total"] > tmpCapacity:
                input_data["ref"][ref_name]["heat_source"][0]["heat_source_rated_capacity_total"] = tmpCapacity

    # 接続される二次ポンプ群

    for ahu_name in input_data["air_handling_system"]:

        if input_data["air_handling_system"][ahu_name]["heat_source_cooling"] + "_冷房" in input_data["ref"]:

            # 冷房熱源群（蓄熱なし）
            input_data["ref"][input_data["air_handling_system"][ahu_name]["heat_source_cooling"] + "_冷房"]["pump_list"].add(
                input_data["air_handling_system"][ahu_name]["pump_cooling"] + "_冷房")

            # 冷房熱源群（蓄熱あり）
            if input_data["ref"][input_data["air_handling_system"][ahu_name]["heat_source_cooling"] + "_冷房"][
                "is_storage"] == "追掛":
                input_data["ref"][input_data["air_handling_system"][ahu_name]["heat_source_cooling"] + "_冷房_蓄熱"][
                    "pump_list"].add(
                    input_data["air_handling_system"][ahu_name]["pump_cooling"] + "_冷房")

        if input_data["air_handling_system"][ahu_name]["heat_source_heating"] + "_暖房" in input_data["ref"]:

            # 暖房熱源群（蓄熱なし）
            input_data["ref"][input_data["air_handling_system"][ahu_name]["heat_source_heating"] + "_暖房"]["pump_list"].add(
                input_data["air_handling_system"][ahu_name]["pump_heating"] + "_暖房")

            # 暖房熱源群（蓄熱あり）
            if input_data["ref"][input_data["air_handling_system"][ahu_name]["heat_source_heating"] + "_暖房"][
                "is_storage"] == "追掛":
                input_data["ref"][input_data["air_handling_system"][ahu_name]["heat_source_heating"] + "_暖房_蓄熱"][
                    "pump_list"].add(
                    input_data["air_handling_system"][ahu_name]["pump_heating"] + "_暖房")

    # ----------------------------------------------------------------------------------
    # 結果格納用の変数 result_json　（熱源群）
    # ----------------------------------------------------------------------------------

    for ref_name in input_data["ref"]:

        result_json["ref"][ref_name] = {

            "schedule": np.zeros((365, 24)),  # 運転スケジュール

            "load_ratio_rated": np.zeros((365, 24)),  # 負荷率（定格能力に対する比率） [-]

            "q_ref_hourly": np.zeros((365, 24)),  # 熱源負荷 [MJ/h]
            "q_ref_storage": np.zeros(365),  # 日積算必要蓄熱量 [MJ/day]
            "t_ref_discharge": np.zeros(365),  # 最大追い掛け運転時間 [hour]

            "num_of_operation": np.zeros((365, 24)),  # 運転台数

            "q_ref_kW_hour": np.zeros((365, 24)),  # 熱源平均負荷 [kW]
            "q_ref_over_capacity": np.zeros((365, 24)),  # 過負荷分
            "ghsp_rq": 0,  # 冷房負荷と暖房負荷の比率（地中熱ヒートポンプ用）

            "E_ref_main": np.zeros((365, 24)),  # 熱源主機一次エネルギー消費量 [MJ]
            "E_ref_main_MWh": np.zeros((365, 24)),  # 熱源主機電力消費量 [MWh]

            "e_ref_sub": np.zeros((365, 24)),  # 補機電力 [kW]
            "E_ref_pump": np.zeros((365, 24)),  # 一次ポンプ電力 [kW] 
            "e_ref_ct_fan": np.zeros((365, 24)),  # 冷却塔ファン電力 [kW] 
            "e_ref_ct_pumpa": np.zeros((365, 24)),  # 冷却水ポンプ電力 [kW]

            "e_ref_sub_MWh": np.zeros((365, 24)),  # 補機電力 [MWh]
            "E_ref_pump_MWh": np.zeros((365, 24)),  # 一次ポンプ電力 [MWh]
            "e_ref_ct_fan_MWh": np.zeros((365, 24)),  # 冷却塔ファン電力 [MWh]
            "e_ref_ct_pumpa_MWh": np.zeros((365, 24)),  # 冷却水ポンプ電力 [MWh]

            "q_ref_thermal_loss": 0,  # 蓄熱槽の熱ロス [MJ]
            "heat_source": {}
        }

        for unit_id, unit_configure in enumerate(input_data["ref"][ref_name]["heat_source"]):
            result_json["ref"][ref_name]["heat_source"][unit_id] = {
                "heat_source_temperature": np.zeros((365, 24)),  # 熱源水等の温度
                "load_ratio": np.zeros((365, 24)),  # 負荷率（最大能力に対する比率） [-]
                "x_q_ratio": np.zeros((365, 24)),  # 能力比（各外気温帯における最大能力）
                "x_pratio": np.zeros((365, 24)),  # 入力比（各外気温帯における最大入力）
                "coefficient_x": np.zeros((365, 24)),  # 部分負荷特性
                "coefficient_tw": np.ones((365, 24)),  # 送水温度特性
                "q_ref_max": np.zeros((365, 24)),  # 最大能力
                "e_ref_max": np.zeros((365, 24)),  # 最大入力
                "E_ref_main_kW": np.zeros((365, 24)),  # 機種別の一次エネルギー消費量 [kW]
                "E_ref_main_MJ": np.zeros((365, 24)),  # 機種別の一次エネルギー消費量 [MJ/h]
                "E_ref_main_MWh": np.zeros((365, 24))  # 機種別の一次エネルギー消費量 [MWh]
            }

    # ----------------------------------------------------------------------------------
    # 熱源群の合計定格能力 （解説書 2.7.5）
    # ----------------------------------------------------------------------------------

    for ref_name in input_data["ref"]:
        input_data["ref"][ref_name]["q_ref_rated"] = 0
        for unit_id, unit_configure in enumerate(input_data["ref"][ref_name]["heat_source"]):
            input_data["ref"][ref_name]["q_ref_rated"] += input_data["ref"][ref_name]["heat_source"][unit_id][
                "heat_source_rated_capacity_total"]

    # ----------------------------------------------------------------------------------
    # 蓄熱槽の熱損失 （解説書 2.7.1）
    # ----------------------------------------------------------------------------------

    for ref_name in input_data["ref"]:

        # 蓄熱の場合: 熱損失量 [MJ/day] を足す。損失量は 蓄熱槽容量の3%。
        if input_data["ref"][ref_name]["is_storage"] == "蓄熱":
            result_json["ref"][ref_name]["q_ref_thermal_loss"] = input_data["ref"][ref_name]["storage_size"] * k_heatloss

    # ----------------------------------------------------------------------------------
    # 熱源負荷の算出（解説書 2.7.2）
    # ----------------------------------------------------------------------------------

    for ref_name in input_data["ref"]:

        for dd in range(0, 365):
            for hh in range(0, 24):

                if input_data["ref"][ref_name]["mode"] == "cooling":  # 冷熱生成用熱源

                    for pump_name in input_data["ref"][ref_name]["pump_list"]:

                        if result_json["pump"][pump_name]["q_ps_hourly"][dd][hh] > 0:
                            # 日積算熱源負荷  [MJ/h]
                            result_json["ref"][ref_name]["q_ref_hourly"][dd][hh] += \
                                result_json["pump"][pump_name]["q_ps_hourly"][dd][hh] + \
                                result_json["pump"][pump_name]["heatloss_pump"][dd][hh]


                elif input_data["ref"][ref_name]["mode"] == "heating":  # 温熱生成用熱源

                    for pump_name in input_data["ref"][ref_name]["pump_list"]:

                        if (result_json["pump"][pump_name]["q_ps_hourly"][dd][hh] +
                            (-1) * result_json["pump"][pump_name]["heatloss_pump"][dd][hh]) > 0:
                            result_json["ref"][ref_name]["q_ref_hourly"][dd][hh] += \
                                result_json["pump"][pump_name]["q_ps_hourly"][dd][hh] + (-1) * \
                                result_json["pump"][pump_name]["heatloss_pump"][dd][hh]

    # ----------------------------------------------------------------------------------
    # 熱源群の運転時間（解説書 2.7.3）
    # ----------------------------------------------------------------------------------

    for ref_name in input_data["ref"]:

        for pump_name in input_data["ref"][ref_name]["pump_list"]:
            result_json["ref"][ref_name]["schedule"] += result_json["pump"][pump_name]["schedule"]

        # 運転スケジュールの和が「1以上（接続されている二次ポンプ群の1つは動いている）」であれば、熱源群は稼働しているとする。
        result_json["ref"][ref_name]["schedule"][result_json["ref"][ref_name]["schedule"] > 1] = 1

        # 日平均負荷[kW] と 過負荷[MJ/h] を求める。（検証用）
        for dd in range(0, 365):
            for hh in range(0, 24):

                # 平均負荷 [kW]
                if result_json["ref"][ref_name]["q_ref_hourly"][dd][hh] > 0:
                    result_json["ref"][ref_name]["q_ref_kW_hour"][dd][hh] = \
                        result_json["ref"][ref_name]["q_ref_hourly"][dd][hh] * 1000 / 3600

                # 過負荷分を集計 [MJ/h]
                if result_json["ref"][ref_name]["q_ref_kW_hour"][dd][hh] > input_data["ref"][ref_name]["q_ref_rated"]:
                    result_json["ref"][ref_name]["q_ref_over_capacity"][dd][hh] = \
                        (result_json["ref"][ref_name]["q_ref_kW_hour"][dd][hh] - input_data["ref"][ref_name][
                            "q_ref_rated"]) * 3600 / 1000

    print('熱源負荷計算完了')

    if debug:  # pragma: no cover

        for ref_name in input_data["ref"]:
            mf.hourlyplot(result_json["ref"][ref_name]["q_ref_kW_hour"], "熱源負荷： " + ref_name, "b", "時刻別熱源負荷")

    # ----------------------------------------------------------------------------------
    # 熱源機器の特性の読み込み（解説書 附属書A.4）
    # ----------------------------------------------------------------------------------

    for ref_name in input_data["ref"]:

        input_data["ref"][ref_name]["check_ctvwv"] = 0  # 冷却水変流量の有無
        input_data["ref"][ref_name]["check_ge_ghp"] = 0  # 発電機能の有無

        for unit_id, unit_configure in enumerate(input_data["ref"][ref_name]["heat_source"]):

            if "冷却水変流量" in unit_configure["heat_source_type"]:
                input_data["ref"][ref_name]["check_ctvwv"] = 1

            if "消費電力自給装置" in unit_configure["heat_source_type"]:
                input_data["ref"][ref_name]["check_ge_ghp"] = 1

            # 特性を全て抜き出す。
            ref_para_set_all = heat_source_performance[unit_configure["heat_source_type"]]

            # 燃料種類に応じて、一次エネルギー換算を行う。
            fuel_type = str()
            if input_data["ref"][ref_name]["mode"] == "cooling":
                input_data["ref"][ref_name]["heat_source"][unit_id]["parameter"] = ref_para_set_all["冷房時の特性"]
                fuel_type = ref_para_set_all["冷房時の特性"]["燃料種類"]

            elif input_data["ref"][ref_name]["mode"] == "heating":
                input_data["ref"][ref_name]["heat_source"][unit_id]["parameter"] = ref_para_set_all["暖房時の特性"]
                fuel_type = ref_para_set_all["暖房時の特性"]["燃料種類"]

            # 燃料種類＋一次エネルギー換算 [kW]
            if fuel_type == "電力":
                input_data["ref"][ref_name]["heat_source"][unit_id]["ref_input_type"] = 1
                input_data["ref"][ref_name]["heat_source"][unit_id]["eref_rated_primary"] = (bc.fprime / 3600) * \
                                                                                          input_data["ref"][ref_name][
                                                                                              "heat_source"][unit_id][
                                                                                              "heat_source_rated_power_consumption_total"]
            elif fuel_type == "ガス":
                input_data["ref"][ref_name]["heat_source"][unit_id]["ref_input_type"] = 2
                input_data["ref"][ref_name]["heat_source"][unit_id]["eref_rated_primary"] = \
                input_data["ref"][ref_name]["heat_source"][unit_id]["heat_source_rated_fuel_consumption_total"]
            elif fuel_type == "重油":
                input_data["ref"][ref_name]["heat_source"][unit_id]["ref_input_type"] = 3
                input_data["ref"][ref_name]["heat_source"][unit_id]["eref_rated_primary"] = \
                input_data["ref"][ref_name]["heat_source"][unit_id]["heat_source_rated_fuel_consumption_total"]
            elif fuel_type == "灯油":
                input_data["ref"][ref_name]["heat_source"][unit_id]["ref_input_type"] = 4
                input_data["ref"][ref_name]["heat_source"][unit_id]["eref_rated_primary"] = \
                input_data["ref"][ref_name]["heat_source"][unit_id]["heat_source_rated_fuel_consumption_total"]
            elif fuel_type == "液化石油ガス":
                input_data["ref"][ref_name]["heat_source"][unit_id]["ref_input_type"] = 5
                input_data["ref"][ref_name]["heat_source"][unit_id]["eref_rated_primary"] = \
                input_data["ref"][ref_name]["heat_source"][unit_id]["heat_source_rated_fuel_consumption_total"]
            elif fuel_type == "蒸気":
                input_data["ref"][ref_name]["heat_source"][unit_id]["ref_input_type"] = 6
                input_data["ref"][ref_name]["heat_source"][unit_id]["heat_source_rated_fuel_consumption_total"] = \
                input_data["ref"][ref_name]["heat_source"][unit_id][
                    "heat_source_rated_capacity_total"]
                input_data["ref"][ref_name]["heat_source"][unit_id]["eref_rated_primary"] = \
                    (input_data["building"]["coefficient_dhc"]["heating"]) * \
                    input_data["ref"][ref_name]["heat_source"][unit_id]["heat_source_rated_capacity_total"]
            elif fuel_type == "温水":
                input_data["ref"][ref_name]["heat_source"][unit_id]["ref_input_type"] = 7
                input_data["ref"][ref_name]["heat_source"][unit_id]["heat_source_rated_fuel_consumption_total"] = \
                input_data["ref"][ref_name]["heat_source"][unit_id][
                    "heat_source_rated_capacity_total"]
                input_data["ref"][ref_name]["heat_source"][unit_id]["eref_rated_primary"] = \
                    (input_data["building"]["coefficient_dhc"]["heating"]) * \
                    input_data["ref"][ref_name]["heat_source"][unit_id]["heat_source_rated_capacity_total"]
            elif fuel_type == "冷水":
                input_data["ref"][ref_name]["heat_source"][unit_id]["ref_input_type"] = 8
                input_data["ref"][ref_name]["heat_source"][unit_id]["heat_source_rated_fuel_consumption_total"] = \
                input_data["ref"][ref_name]["heat_source"][unit_id][
                    "heat_source_rated_capacity_total"]
                input_data["ref"][ref_name]["heat_source"][unit_id]["eref_rated_primary"] = \
                    (input_data["building"]["coefficient_dhc"]["cooling"]) * \
                    input_data["ref"][ref_name]["heat_source"][unit_id]["heat_source_rated_capacity_total"]

                # ----------------------------------------------------------------------------------
    # 熱源群の負荷率（解説書 2.7.7）
    # ----------------------------------------------------------------------------------

    for ref_name in input_data["ref"]:

        for dd in range(0, 365):
            for hh in range(0, 24):

                # 負荷率の算出 [-]
                if result_json["ref"][ref_name]["q_ref_hourly"][dd][hh] > 0:
                    # 熱源定格負荷率（定格能力に対する比率）
                    try:
                        result_json["ref"][ref_name]["load_ratio_rated"][dd][hh] = \
                            (result_json["ref"][ref_name]["q_ref_hourly"][dd][hh] * 1000 / 3600) / \
                            input_data["ref"][ref_name]["q_ref_rated"]
                    except ZeroDivisionError:
                        result_json["ref"][ref_name]["load_ratio_rated"][dd][hh] = 0

    # ----------------------------------------------------------------------------------
    # 湿球温度 （解説書 2.7.4.2）
    # ----------------------------------------------------------------------------------

    for dd in range(0, 365):
        for hh in range(0, 24):

            if ac_mode[dd] == "冷房" or ac_mode[dd] == "中間期":

                result_json["climate"]["tout_wb"][dd][hh] = \
                    area[input_data["building"]["region"] + "地域"]["湿球温度係数_冷房a1"] * \
                    result_json["climate"]["tout"][dd][hh] + \
                    area[input_data["building"]["region"] + "地域"]["湿球温度係数_冷房a0"]

            elif ac_mode[dd] == "暖房":

                result_json["climate"]["tout_wb"][dd][hh] = \
                    area[input_data["building"]["region"] + "地域"]["湿球温度係数_暖房a1"] * \
                    result_json["climate"]["tout"][dd][hh] + \
                    area[input_data["building"]["region"] + "地域"]["湿球温度係数_暖房a0"]

    # ----------------------------------------------------------------------------------
    # 冷却水温度 （解説書 2.7.4.3）
    # ----------------------------------------------------------------------------------

    for dd in range(0, 365):
        for hh in range(0, 24):
            # 冷房運転時冷却水温度
            result_json["climate"]["Tct_cooling"][dd][hh] = result_json["climate"]["tout_wb"][dd][hh] + 3
            # 暖房運転時冷却水温度
            result_json["climate"]["Tct_heating"][dd][hh] = 15.5

    # ----------------------------------------------------------------------------------
    # 地中熱交換器（クローズドループ）からの熱源水温度 （解説書 2.7.4.4）
    # ----------------------------------------------------------------------------------

    # 地中熱ヒートポンプ用係数
    gshp_ah = [8.0278, 13.0253, 16.7424, 19.3145, 21.2833]  # 地盤モデル：暖房時パラメータa
    gshp_bh = [-1.1462, -1.8689, -2.4651, -3.091, -3.8325]  # 地盤モデル：暖房時パラメータb
    gshp_ch = [-0.1128, -0.1846, -0.2643, -0.2926, -0.3474]  # 地盤モデル：暖房時パラメータc
    gshp_dh = [0.1256, 0.2023, 0.2623, 0.3085, 0.3629]  # 地盤モデル：暖房時パラメータd
    gshp_ac = [8.0633, 12.6226, 16.1703, 19.6565, 21.8702]  # 地盤モデル：冷房時パラメータa
    gshp_bc = [2.9083, 4.7711, 6.3128, 7.8071, 9.148]  # 地盤モデル：冷房時パラメータb
    gshp_cc = [0.0613, 0.0568, 0.1027, 0.1984, 0.249]  # 地盤モデル：冷房時パラメータc
    gshp_dc = [0.2178, 0.3509, 0.4697, 0.5903, 0.7154]  # 地盤モデル：冷房時パラメータd

    ghsptoa_ave = [5.8, 7.5, 10.2, 11.6, 13.3, 15.7, 17.4, 22.7]  # 地盤モデル：年平均外気温
    gshp_toa_h = [-3, -0.8, 0, 1.1, 3.6, 6, 9.3, 17.5]  # 地盤モデル：暖房時平均外気温
    gshp_toa_c = [16.8, 17, 18.9, 19.6, 20.5, 22.4, 22.1, 24.6]  # 地盤モデル：冷房時平均外気温

    # 冷暖房比率 ghsp_rq
    for ref_original_name in input_data["heat_source_system"]:

        q_c_max = 0
        if "冷房" in input_data["heat_source_system"][ref_original_name]:
            q_c_max = np.max(np.sum(result_json["ref"][ref_original_name + "_冷房"]["q_ref_hourly"], axis=1), 0)

        q_h_max = 0
        if "暖房" in input_data["heat_source_system"][ref_original_name]:
            q_h_max = np.max(np.sum(result_json["ref"][ref_original_name + "_暖房"]["q_ref_hourly"], axis=1), 0)

        if q_c_max != 0 and q_h_max != 0:

            result_json["ref"][ref_original_name + "_冷房"]["ghsp_rq"] = (q_c_max - q_h_max) / (q_c_max + q_h_max)
            result_json["ref"][ref_original_name + "_暖房"]["ghsp_rq"] = (q_c_max - q_h_max) / (q_c_max + q_h_max)

        elif q_c_max == 0 and q_h_max != 0:
            result_json["ref"][ref_original_name + "_暖房"]["ghsp_rq"] = 0

        elif q_c_max != 0 and q_h_max == 0:
            result_json["ref"][ref_original_name + "_冷房"]["ghsp_rq"] = 0

    # ----------------------------------------------------------------------------------
    # 熱源水等の温度 matrix_t （解説書 2.7.4）
    # ----------------------------------------------------------------------------------

    # 地中熱オープンループの地盤特性の読み込み
    with open(database_directory + 'ac_gshp_openloop.json', 'r', encoding='utf-8') as f:
        ac_gshp_openloop = json.load(f)

    for ref_name in input_data["ref"]:

        for unit_id, unit_configure in enumerate(input_data["ref"][ref_name]["heat_source"]):

            # 日別の熱源水等の温度

            if "地盤A" in unit_configure["parameter"]["熱源種類"] or "地盤B" in unit_configure["parameter"][
                "熱源種類"] or \
                    "地盤C" in unit_configure["parameter"]["熱源種類"] or "地盤D" in unit_configure["parameter"][
                "熱源種類"] or \
                    "地盤E" in unit_configure["parameter"]["熱源種類"] or "地盤F" in unit_configure["parameter"][
                "熱源種類"]:  # 地中熱オープンループ

                for dd in range(365):

                    # 月別の揚水温度
                    theta_wo_m = \
                        ac_gshp_openloop["theta_ac_wo_ave"][input_data["building"]["region"] + "地域"] + \
                        ac_gshp_openloop["theta_ac_wo_m"][input_data["building"]["region"] + "地域"][bc.day2month(dd)]

                    # 月別の地盤からの熱源水還り温度
                    heat_source_temperature = 0
                    if input_data["ref"][ref_name]["mode"] == "cooling":

                        # 月別の熱源水還り温度（冷房期）
                        heat_source_temperature = \
                            theta_wo_m + \
                            ac_gshp_openloop["theta_wo_c"][unit_configure["parameter"]["熱源種類"]] + \
                            ac_gshp_openloop["theta_hex_c"][unit_configure["parameter"]["熱源種類"]]

                    elif input_data["ref"][ref_name]["mode"] == "heating":

                        # 月別の熱源水還り温度（暖房期）
                        heat_source_temperature = \
                            theta_wo_m + \
                            ac_gshp_openloop["theta_wo_h"][unit_configure["parameter"]["熱源種類"]] + \
                            ac_gshp_openloop["theta_hex_h"][unit_configure["parameter"]["熱源種類"]]

                    # 時々刻々のデータ
                    for hh in range(0, 24):
                        result_json["ref"][ref_name]["heat_source"][unit_id]["heat_source_temperature"][dd][
                            hh] = heat_source_temperature


            else:

                if unit_configure["parameter"]["熱源種類"] == "水" and input_data["ref"][ref_name]["mode"] == "cooling":

                    # 冷却水温度（冷房）
                    result_json["ref"][ref_name]["heat_source"][unit_id]["heat_source_temperature"] = \
                    result_json["climate"]["Tct_cooling"]

                elif unit_configure["parameter"]["熱源種類"] == "水" and input_data["ref"][ref_name][
                    "mode"] == "heating":

                    # 冷却水温度（暖房）
                    result_json["ref"][ref_name]["heat_source"][unit_id]["heat_source_temperature"] = \
                    result_json["climate"]["Tct_heating"]

                elif unit_configure["parameter"]["熱源種類"] == "空気" and input_data["ref"][ref_name][
                    "mode"] == "cooling":

                    # 乾球温度 
                    result_json["ref"][ref_name]["heat_source"][unit_id]["heat_source_temperature"] = \
                    result_json["climate"]["tout"]

                elif unit_configure["parameter"]["熱源種類"] == "空気" and input_data["ref"][ref_name][
                    "mode"] == "heating":

                    # 湿球温度 
                    result_json["ref"][ref_name]["heat_source"][unit_id]["heat_source_temperature"] = \
                    result_json["climate"]["tout_wb"]

                elif unit_configure["parameter"]["熱源種類"] == "不要":

                    # 乾球温度 
                    result_json["ref"][ref_name]["heat_source"][unit_id]["heat_source_temperature"] = \
                    result_json["climate"]["tout"]


                elif "地盤1" in unit_configure["parameter"]["熱源種類"] or "地盤2" in unit_configure["parameter"][
                    "熱源種類"] or \
                        "地盤3" in unit_configure["parameter"]["熱源種類"] or "地盤4" in unit_configure["parameter"][
                    "熱源種類"] or \
                        "地盤5" in unit_configure["parameter"]["熱源種類"]:  # 地中熱クローズループ

                    for gound_type in range(1, 6):

                        if unit_configure["parameter"]["熱源種類"] == "地盤" + str(int(gound_type)) and \
                                input_data["ref"][ref_name]["mode"] == "cooling":

                            igs_type = int(gound_type) - 1
                            iarea = int(input_data["building"]["region"]) - 1

                            # 地盤からの還り温度（冷房）
                            for dd in range(0, 365):
                                for hh in range(0, 24):
                                    result_json["ref"][ref_name]["heat_source"][unit_id]["heat_source_temperature"][dd][
                                        hh] = \
                                        (gshp_cc[igs_type] * result_json["ref"][ref_name]["ghsp_rq"] + gshp_dc[igs_type]) * \
                                        (result_json["climate"]["tout_daily"][dd] - gshp_toa_c[iarea]) + \
                                        (ghsptoa_ave[iarea] + gshp_ac[igs_type] * result_json["ref"][ref_name][
                                            "ghsp_rq"] + gshp_bc[igs_type])

                        elif unit_configure["parameter"]["熱源種類"] == "地盤" + str(int(gound_type)) and \
                                input_data["ref"][ref_name]["mode"] == "heating":

                            igs_type = int(gound_type) - 1
                            iarea = int(input_data["building"]["region"]) - 1

                            # 地盤からの還り温度（暖房）
                            for dd in range(0, 365):
                                for hh in range(0, 24):
                                    result_json["ref"][ref_name]["heat_source"][unit_id]["heat_source_temperature"][dd][
                                        hh] = \
                                        (gshp_ch[igs_type] * result_json["ref"][ref_name]["ghsp_rq"] + gshp_dh[igs_type]) * \
                                        (result_json["climate"]["tout_daily"][dd] - gshp_toa_h[iarea]) + \
                                        (ghsptoa_ave[iarea] + gshp_ah[igs_type] * result_json["ref"][ref_name][
                                            "ghsp_rq"] + gshp_bh[igs_type])

                else:

                    raise Exception("熱源種類が不正です。")

    # ----------------------------------------------------------------------------------
    # 任意評定用　熱源水温度（ SP-3 ）
    # ----------------------------------------------------------------------------------

    if "special_input_data" in input_data:

        if "heat_source_temperature_monthly" in input_data["special_input_data"]:

            for ref_original_name in input_data["special_input_data"]["heat_source_temperature_monthly"]:

                # 入力された熱源群名称から、計算上使用する熱源群名称（冷暖、蓄熱分離）に変換
                for ref_name in [ref_original_name + "_冷房", ref_original_name + "_暖房",
                                 ref_original_name + "_冷房_蓄熱", ref_original_name + "_暖房_蓄熱"]:

                    if ref_name in input_data["ref"]:
                        for unit_id, unit_configure in enumerate(input_data["ref"][ref_name]["heat_source"]):
                            for dd in range(0, 365):
                                for hh in range(0, 24):
                                    result_json["ref"][ref_name]["heat_source"][unit_id]["heat_source_temperature"][dd][
                                        hh] = \
                                        input_data["special_input_data"]["heat_source_temperature_monthly"][
                                            ref_original_name][bc.day2month(dd)]

    # ----------------------------------------------------------------------------------
    # 最大能力比 x_q_ratio （解説書 2.7.8）
    # ----------------------------------------------------------------------------------

    for ref_name in input_data["ref"]:

        for unit_id, unit_configure in enumerate(input_data["ref"][ref_name]["heat_source"]):

            # 能力比（各外気温帯における最大能力）
            for dd in range(0, 365):
                for hh in range(0, 24):

                    # 外気温度
                    temperature = result_json["ref"][ref_name]["heat_source"][unit_id]["heat_source_temperature"][dd][hh]

                    # 特性式の数
                    curve_number = len(unit_configure["parameter"]["能力比"])

                    # 下限値
                    temp_min_list = []
                    for para_num in range(0, curve_number):
                        temp_min_list.append(unit_configure["parameter"]["能力比"][para_num]["下限"])
                    # 上限値
                    temp_max_list = []
                    for para_num in range(0, curve_number):
                        temp_max_list.append(unit_configure["parameter"]["能力比"][para_num]["上限"])

                    # 上限と下限を定める
                    if temperature < temp_min_list[0]:
                        temperature = temp_min_list[0]
                    elif temperature > temp_max_list[-1]:
                        temperature = temp_max_list[-1]

                    for para_num in reversed(range(0, curve_number)):
                        if temperature <= temp_max_list[para_num]:
                            result_json["ref"][ref_name]["heat_source"][unit_id]["x_q_ratio"][dd][hh] = \
                                unit_configure["parameter"]["能力比"][para_num]["基整促係数"] * (
                                        unit_configure["parameter"]["能力比"][para_num]["係数"][
                                            "a4"] * temperature ** 4 +
                                        unit_configure["parameter"]["能力比"][para_num]["係数"][
                                            "a3"] * temperature ** 3 +
                                        unit_configure["parameter"]["能力比"][para_num]["係数"][
                                            "a2"] * temperature ** 2 +
                                        unit_configure["parameter"]["能力比"][para_num]["係数"]["a1"] * temperature +
                                        unit_configure["parameter"]["能力比"][para_num]["係数"]["a0"])

        for unit_id, unit_configure in enumerate(input_data["ref"][ref_name]["heat_source"]):

            for dd in range(0, 365):
                for hh in range(0, 24):
                    # 各時刻の最大能力 [kW]
                    result_json["ref"][ref_name]["heat_source"][unit_id]["q_ref_max"][dd][hh] = \
                        input_data["ref"][ref_name]["heat_source"][unit_id]["heat_source_rated_capacity_total"] * \
                        result_json["ref"][ref_name]["heat_source"][unit_id]["x_q_ratio"][dd][hh]

    # ----------------------------------------------------------------------------------
    # 蓄熱システムによる運転時間の補正（解説書 2.7.15 蓄熱）
    # ----------------------------------------------------------------------------------

    # 必要蓄熱量の算出

    for ref_name in input_data["ref"]:

        if input_data["ref"][ref_name]["is_storage"] == "追掛":

            for dd in range(0, 365):

                # 最大放熱可能量[MJ]
                Q_discharge = input_data["ref"][ref_name]["storage_size"] * (1 - k_heatloss)

                for hh in range(0, 24):

                    if result_json["ref"][ref_name]["q_ref_hourly"][dd][hh] > 0:

                        # 必要蓄熱量 [MJ/day]
                        if result_json["ref"][ref_name]["q_ref_hourly"][dd][hh] > (
                                input_data["ref"][ref_name]["heat_source"][0][
                                    "heat_source_rated_capacity_total"] * 3600 / 1000):
                            tmp = input_data["ref"][ref_name]["heat_source"][0][
                                      "heat_source_rated_capacity_total"] * 3600 / 1000
                        else:
                            tmp = result_json["ref"][ref_name]["q_ref_hourly"][dd][hh]

                        if (Q_discharge - tmp) > 0:
                            Q_discharge = Q_discharge - tmp
                            result_json["ref"][ref_name]["q_ref_storage"][dd] += tmp
                        else:
                            break

            # 必要蓄熱量[MJ] → 蓄熱用熱源に値を渡す
            result_json["ref"][ref_name + "_蓄熱"]["q_ref_storage"] = result_json["ref"][ref_name]["q_ref_storage"]

    for ref_name in input_data["ref"]:
        if input_data["ref"][ref_name]["is_storage"] == "蓄熱":

            # 一旦削除
            result_json["ref"][ref_name]["q_ref_hourly"] = np.zeros((365, 24))
            result_json["ref"][ref_name]["load_ratio_rated"] = np.zeros((365, 24))

            for dd in range(0, 365):

                # 必要蓄熱量が 0　より大きい場合
                if result_json["ref"][ref_name]["q_ref_storage"][dd] > 0:

                    # 熱ロスを足す。
                    result_json["ref"][ref_name]["q_ref_storage"][dd] += input_data["ref"][ref_name][
                                                                           "storage_size"] * k_heatloss

                    # 蓄熱用熱源の最大能力（0〜8時の平均値とする）
                    q_ref_max_total = np.zeros(8)
                    for hh in range(0, 8):
                        for unit_id, unit_configure in enumerate(input_data["ref"][ref_name]["heat_source"]):
                            q_ref_max_total[hh] += result_json["ref"][ref_name]["heat_source"][unit_id]["q_ref_max"][dd][
                                hh]
                    q_ref_max_ave = np.mean(q_ref_max_total)

                    # 蓄熱運転すべき時間
                    hour_for_storage = math.ceil(
                        result_json["ref"][ref_name]["q_ref_storage"][dd] / (q_ref_max_ave * 3600 / 1000))

                    if hour_for_storage > 24:
                        print(hour_for_storage)
                        raise Exception("蓄熱に必要な能力が足りません")

                    # 1時間に蓄熱すべき量 [MJ/h]
                    storage_heat_in_hour = (result_json["ref"][ref_name]["q_ref_storage"][dd] / hour_for_storage)

                    # 本来は前日22時〜にすべきだが、ひとまず0時〜に設定
                    for hh in range(0, hour_for_storage):
                        result_json["ref"][ref_name]["q_ref_hourly"][dd][hh] = storage_heat_in_hour

                    # 負荷率帯マトリックスの更新
                    for hh in range(0, 24):
                        if result_json["ref"][ref_name]["q_ref_hourly"][dd][hh] > 0:
                            result_json["ref"][ref_name]["load_ratio_rated"][dd][hh] = \
                                (result_json["ref"][ref_name]["q_ref_hourly"][dd][hh] * 1000 / 3600) / \
                                input_data["ref"][ref_name]["q_ref_rated"]

                            # ----------------------------------------------------------------------------------
    # 最大入力比 x_pratio （解説書 2.7.11）
    # ----------------------------------------------------------------------------------

    for ref_name in input_data["ref"]:

        for unit_id, unit_configure in enumerate(input_data["ref"][ref_name]["heat_source"]):

            # 外気温度帯マトリックス 
            for dd in range(0, 365):
                for hh in range(0, 24):

                    # 外気温度帯
                    temperature = result_json["ref"][ref_name]["heat_source"][unit_id]["heat_source_temperature"][dd][hh]

                    # 特性式の数
                    curve_number = len(unit_configure["parameter"]["入力比"])

                    # 下限値
                    temp_min_list = []
                    for para_num in range(0, curve_number):
                        temp_min_list.append(unit_configure["parameter"]["入力比"][para_num]["下限"])
                    # 上限値
                    temp_max_list = []
                    for para_num in range(0, curve_number):
                        temp_max_list.append(unit_configure["parameter"]["入力比"][para_num]["上限"])

                    # 上限と下限を定める
                    if temperature < temp_min_list[0]:
                        temperature = temp_min_list[0]
                    elif temperature > temp_max_list[-1]:
                        temperature = temp_max_list[-1]

                    for para_num in reversed(range(0, curve_number)):
                        if temperature <= temp_max_list[para_num]:
                            result_json["ref"][ref_name]["heat_source"][unit_id]["x_pratio"][dd][hh] = \
                                unit_configure["parameter"]["入力比"][para_num]["基整促係数"] * (
                                        unit_configure["parameter"]["入力比"][para_num]["係数"][
                                            "a4"] * temperature ** 4 +
                                        unit_configure["parameter"]["入力比"][para_num]["係数"][
                                            "a3"] * temperature ** 3 +
                                        unit_configure["parameter"]["入力比"][para_num]["係数"][
                                            "a2"] * temperature ** 2 +
                                        unit_configure["parameter"]["入力比"][para_num]["係数"]["a1"] * temperature +
                                        unit_configure["parameter"]["入力比"][para_num]["係数"]["a0"])

        for unit_id, unit_configure in enumerate(input_data["ref"][ref_name]["heat_source"]):

            for dd in range(0, 365):
                for hh in range(0, 24):
                    # 各時刻における最大入力 [kW]  (1次エネルギー換算値であることに注意）
                    result_json["ref"][ref_name]["heat_source"][unit_id]["e_ref_max"][dd][hh] = \
                        input_data["ref"][ref_name]["heat_source"][unit_id]["eref_rated_primary"] * \
                        result_json["ref"][ref_name]["heat_source"][unit_id]["x_pratio"][dd][hh]

    # ----------------------------------------------------------------------------------
    # 熱源機器の運転台数（解説書 2.7.9）
    # ----------------------------------------------------------------------------------

    # 運転台数マトリックス
    for ref_name in input_data["ref"]:

        for dd in range(0, 365):
            for hh in range(0, 24):

                if result_json["ref"][ref_name]["q_ref_hourly"][dd][hh] > 0:  # 負荷があれば

                    if input_data["ref"][ref_name]["is_staging_control"] == "無":  # 運転台数制御が「無」の場合

                        result_json["ref"][ref_name]["num_of_operation"][dd][hh] = input_data["ref"][ref_name][
                            "num_of_unit"]

                    elif input_data["ref"][ref_name]["is_staging_control"] == "有":  # 運転台数制御が「有」の場合

                        # 処理熱量 [kW]
                        tmp_q = result_json["ref"][ref_name]["q_ref_hourly"][dd][hh] * 1000 / 3600

                        # 運転台数 num_of_operation
                        tmp_qmax = 0
                        rr = 0
                        for rr in range(0, input_data["ref"][ref_name]["num_of_unit"]):
                            tmp_qmax += result_json["ref"][ref_name]["heat_source"][rr]["q_ref_max"][dd][hh]

                            if tmp_q < tmp_qmax:
                                break

                        result_json["ref"][ref_name]["num_of_operation"][dd][hh] = rr + 1

    if debug:  # pragma: no cover
        for ref_name in input_data["ref"]:
            mf.hourlyplot(result_json["ref"][ref_name]["num_of_operation"], "熱源運転台数： " + ref_name, "b",
                          "熱源運転台数")

    # ----------------------------------------------------------------------------------
    # 熱源群の運転負荷率（解説書 2.7.12）
    # ----------------------------------------------------------------------------------

    for ref_name in input_data["ref"]:

        for dd in range(0, 365):
            for hh in range(0, 24):

                if result_json["ref"][ref_name]["q_ref_hourly"][dd][hh] > 0:  # 運転していれば

                    # 処理熱量 [kW]
                    tmp_q = result_json["ref"][ref_name]["q_ref_hourly"][dd][hh] * 1000 / 3600

                    q_ref_r_mod_max = 0
                    for unit_id in range(0, int(result_json["ref"][ref_name]["num_of_operation"][dd][hh])):
                        q_ref_r_mod_max += result_json["ref"][ref_name]["heat_source"][unit_id]["q_ref_max"][dd][hh]

                    # [iT,iL]における負荷率
                    if input_data["ref"][ref_name]["is_storage"] == "追掛":

                        for unit_id, unit_configure in enumerate(input_data["ref"][ref_name]["heat_source"]):

                            if unit_id == 0:
                                # 熱交換器の負荷率は1とする
                                result_json["ref"][ref_name]["heat_source"][unit_id]["load_ratio"][dd][hh] = 1
                            else:
                                # 熱交換器以外で負荷率を求める。
                                result_json["ref"][ref_name]["heat_source"][unit_id]["load_ratio"][dd][hh] = \
                                    (tmp_q - input_data["ref"][ref_name]["heat_source"][0][
                                        "heat_source_rated_capacity_total"]) / \
                                    (q_ref_r_mod_max - input_data["ref"][ref_name]["heat_source"][0][
                                        "heat_source_rated_capacity_total"])

                    else:

                        for unit_id, unit_configure in enumerate(input_data["ref"][ref_name]["heat_source"]):
                            try:
                                result_json["ref"][ref_name]["heat_source"][unit_id]["load_ratio"][dd][
                                    hh] = tmp_q / q_ref_r_mod_max
                            except ZeroDivisionError:
                                result_json["ref"][ref_name]["heat_source"][unit_id]["load_ratio"][dd][hh] = 0

    # ----------------------------------------------------------------------------------
    # 部分負荷特性 （解説書 2.7.13）
    # ----------------------------------------------------------------------------------

    for ref_name in input_data["ref"]:

        for dd in range(0, 365):
            for hh in range(0, 24):

                if result_json["ref"][ref_name]["q_ref_hourly"][dd][hh] > 0:  # 運転していれば

                    # 部分負荷特性（各負荷率・各温度帯について）
                    for unit_id in range(0, int(result_json["ref"][ref_name]["num_of_operation"][dd][hh])):

                        # どの部分負荷特性を使うか（インバータターボなど、冷却水温度によって特性が異なる場合がある）
                        xcurve_number = 0
                        if len(input_data["ref"][ref_name]["heat_source"][unit_id]["parameter"][
                                   "部分負荷特性"]) > 1:  # 部分負荷特性が2以上設定されている場合

                            for para_id in range(0, len(
                                    input_data["ref"][ref_name]["heat_source"][unit_id]["parameter"]["部分負荷特性"])):

                                if result_json["ref"][ref_name]["heat_source"][unit_id]["heat_source_temperature"][dd][
                                    hh] > \
                                        input_data["ref"][ref_name]["heat_source"][unit_id]["parameter"]["部分負荷特性"][
                                            para_id]["冷却水温度下限"] and \
                                        result_json["ref"][ref_name]["heat_source"][unit_id]["heat_source_temperature"][
                                            dd][hh] <= \
                                        input_data["ref"][ref_name]["heat_source"][unit_id]["parameter"]["部分負荷特性"][
                                            para_id]["冷却水温度上限"]:
                                    xcurve_number = para_id

                        # 機器特性による上下限を考慮した部分負荷率 tmpL
                        tmpL = 0
                        if result_json["ref"][ref_name]["heat_source"][unit_id]["load_ratio"][dd][hh] < \
                                input_data["ref"][ref_name]["heat_source"][unit_id]["parameter"]["部分負荷特性"][
                                    xcurve_number]["下限"]:
                            tmpL = \
                            input_data["ref"][ref_name]["heat_source"][unit_id]["parameter"]["部分負荷特性"][xcurve_number][
                                "下限"]
                        elif result_json["ref"][ref_name]["heat_source"][unit_id]["load_ratio"][dd][hh] > \
                                input_data["ref"][ref_name]["heat_source"][unit_id]["parameter"]["部分負荷特性"][
                                    xcurve_number]["上限"]:
                            tmpL = \
                            input_data["ref"][ref_name]["heat_source"][unit_id]["parameter"]["部分負荷特性"][xcurve_number][
                                "上限"]
                        else:
                            tmpL = result_json["ref"][ref_name]["heat_source"][unit_id]["load_ratio"][dd][hh]

                        # 部分負荷特性
                        result_json["ref"][ref_name]["heat_source"][unit_id]["coefficient_x"][dd][hh] = \
                            input_data["ref"][ref_name]["heat_source"][unit_id]["parameter"]["部分負荷特性"][xcurve_number][
                                "基整促係数"] * (
                                    input_data["ref"][ref_name]["heat_source"][unit_id]["parameter"]["部分負荷特性"][
                                        xcurve_number]["係数"]["a4"] * tmpL ** 4 +
                                    input_data["ref"][ref_name]["heat_source"][unit_id]["parameter"]["部分負荷特性"][
                                        xcurve_number]["係数"]["a3"] * tmpL ** 3 +
                                    input_data["ref"][ref_name]["heat_source"][unit_id]["parameter"]["部分負荷特性"][
                                        xcurve_number]["係数"]["a2"] * tmpL ** 2 +
                                    input_data["ref"][ref_name]["heat_source"][unit_id]["parameter"]["部分負荷特性"][
                                        xcurve_number]["係数"]["a1"] * tmpL +
                                    input_data["ref"][ref_name]["heat_source"][unit_id]["parameter"]["部分負荷特性"][
                                        xcurve_number]["係数"]["a0"])

                        # 過負荷時のペナルティ
                        if result_json["ref"][ref_name]["heat_source"][unit_id]["load_ratio"][dd][hh] > 1:
                            result_json["ref"][ref_name]["heat_source"][unit_id]["coefficient_x"][dd][hh] = \
                                result_json["ref"][ref_name]["heat_source"][unit_id]["coefficient_x"][dd][hh] * 1.2

    # ----------------------------------------------------------------------------------
    # 送水温度特性 （解説書 2.7.14）
    # ----------------------------------------------------------------------------------

    for ref_name in input_data["ref"]:

        for dd in range(0, 365):
            for hh in range(0, 24):

                # 送水温度特性（各負荷率・各温度帯について）
                for unit_id in range(0, int(result_json["ref"][ref_name]["num_of_operation"][dd][hh])):

                    # 送水温度特性
                    if input_data["ref"][ref_name]["heat_source"][unit_id]["parameter"]["送水温度特性"] != []:

                        # 送水温度 tc_temperature
                        tc_temperature = 0
                        if input_data["ref"][ref_name]["mode"] == "cooling":

                            if input_data["ref"][ref_name]["heat_source"][unit_id]["supply_water_temp_summer"] is None:
                                tc_temperature = 5
                            else:
                                tc_temperature = input_data["ref"][ref_name]["heat_source"][unit_id]["supply_water_temp_summer"]

                        elif input_data["ref"][ref_name]["mode"] == "heating":

                            if input_data["ref"][ref_name]["heat_source"][unit_id]["supply_water_temp_winter"] is None:
                                tc_temperature = 50
                            else:
                                tc_temperature = input_data["ref"][ref_name]["heat_source"][unit_id]["supply_water_temp_winter"]

                        # 送水温度の上下限
                        if tc_temperature < input_data["ref"][ref_name]["heat_source"][unit_id]["parameter"]["送水温度特性"][0][
                            "下限"]:
                            tc_temperature = input_data["ref"][ref_name]["heat_source"][unit_id]["parameter"]["送水温度特性"][0][
                                "下限"]
                        elif tc_temperature > input_data["ref"][ref_name]["heat_source"][unit_id]["parameter"]["送水温度特性"][0][
                            "上限"]:
                            tc_temperature = input_data["ref"][ref_name]["heat_source"][unit_id]["parameter"]["送水温度特性"][0][
                                "上限"]

                        # 送水温度特性
                        result_json["ref"][ref_name]["heat_source"][unit_id]["coefficient_tw"][dd][hh] = \
                            input_data["ref"][ref_name]["heat_source"][unit_id]["parameter"]["送水温度特性"][0][
                                "基整促係数"] * (
                                    input_data["ref"][ref_name]["heat_source"][unit_id]["parameter"]["送水温度特性"][0][
                                        "係数"]["a4"] * tc_temperature ** 4 +
                                    input_data["ref"][ref_name]["heat_source"][unit_id]["parameter"]["送水温度特性"][0][
                                        "係数"]["a3"] * tc_temperature ** 3 +
                                    input_data["ref"][ref_name]["heat_source"][unit_id]["parameter"]["送水温度特性"][0][
                                        "係数"]["a2"] * tc_temperature ** 2 +
                                    input_data["ref"][ref_name]["heat_source"][unit_id]["parameter"]["送水温度特性"][0][
                                        "係数"]["a1"] * tc_temperature +
                                    input_data["ref"][ref_name]["heat_source"][unit_id]["parameter"]["送水温度特性"][0][
                                        "係数"]["a0"])

    # ----------------------------------------------------------------------------------
    # 熱源機器の一次エネルギー消費量（解説書 2.7.16）
    # ----------------------------------------------------------------------------------

    for ref_name in input_data["ref"]:

        for dd in range(0, 365):
            for hh in range(0, 24):

                # 熱源主機（機器毎）：エネルギー消費量 kW のマトリックス E_ref_main
                for unit_id in range(0, int(result_json["ref"][ref_name]["num_of_operation"][dd][hh])):
                    result_json["ref"][ref_name]["heat_source"][unit_id]["E_ref_main_kW"][dd][hh] = \
                        result_json["ref"][ref_name]["heat_source"][unit_id]["e_ref_max"][dd][hh] * \
                        result_json["ref"][ref_name]["heat_source"][unit_id]["coefficient_x"][dd][hh] * \
                        result_json["ref"][ref_name]["heat_source"][unit_id]["coefficient_tw"][dd][hh]

                # 補機電力
                # 一台あたりの負荷率（熱源機器の負荷率＝最大能力を考慮した負荷率・ただし、熱源特性の上限・下限は考慮せず）
                ave_l_per_u = result_json["ref"][ref_name]["load_ratio_rated"][dd][hh]

                # 過負荷の場合は 平均負荷率＝1.2 とする。
                if ave_l_per_u > 1:
                    ave_l_per_u = 1.2

                # 発電機能付きの熱源機器が1台でもある場合
                if input_data["ref"][ref_name]["check_ge_ghp"] == 1:

                    for unit_id in range(0, int(result_json["ref"][ref_name]["num_of_operation"][dd][hh])):

                        if "消費電力自給装置" in input_data["ref"][ref_name]["heat_source"][unit_id]["heat_source_type"]:

                            # 非発電時の消費電力 [kW]
                            e_nonge = 0
                            if input_data["ref"][ref_name]["mode"] == "cooling":
                                e_nonge = input_data["ref"][ref_name]["heat_source"][unit_id][
                                              "heat_source_rated_capacity_total"] * 0.017
                            elif input_data["ref"][ref_name]["mode"] == "heating":
                                e_nonge = input_data["ref"][ref_name]["heat_source"][unit_id][
                                              "heat_source_rated_capacity_total"] * 0.012

                            e_gekw = input_data["ref"][ref_name]["heat_source"][unit_id][
                                "heat_source_sub_rated_power_consumption_total"]  # 発電時の消費電力 [kW]

                            if ave_l_per_u <= 0.3:
                                result_json["ref"][ref_name]["e_ref_sub"][dd][hh] += (
                                            0.3 * e_nonge - (e_nonge - e_gekw) * ave_l_per_u)
                            else:
                                result_json["ref"][ref_name]["e_ref_sub"][dd][hh] += (ave_l_per_u * e_gekw)

                        else:

                            if ave_l_per_u <= 0.3:
                                result_json["ref"][ref_name]["e_ref_sub"][dd][hh] += 0.3 * input_data["ref"][ref_name][
                                    "heat_source"][unit_id][
                                    "heat_source_sub_rated_power_consumption_total"]
                            else:
                                result_json["ref"][ref_name]["e_ref_sub"][dd][hh] += ave_l_per_u * \
                                                                                    input_data["ref"][ref_name][
                                                                                        "heat_source"][unit_id][
                                                                                        "heat_source_sub_rated_power_consumption_total"]

                else:

                    # 負荷に比例させる（発電機能なし）
                    ref_set_sub_power = 0
                    for unit_id in range(0, int(result_json["ref"][ref_name]["num_of_operation"][dd][hh])):
                        if input_data["ref"][ref_name]["heat_source"][unit_id][
                            "heat_source_rated_fuel_consumption_total"] > 0:
                            ref_set_sub_power += input_data["ref"][ref_name]["heat_source"][unit_id][
                                "heat_source_sub_rated_power_consumption_total"]

                    if ave_l_per_u <= 0.3:
                        result_json["ref"][ref_name]["e_ref_sub"][dd][hh] += 0.3 * ref_set_sub_power
                    else:
                        result_json["ref"][ref_name]["e_ref_sub"][dd][hh] += ave_l_per_u * ref_set_sub_power

                # 一次ポンプ
                for unit_id in range(0, int(result_json["ref"][ref_name]["num_of_operation"][dd][hh])):
                    result_json["ref"][ref_name]["E_ref_pump"][dd][hh] += \
                        input_data["ref"][ref_name]["heat_source"][unit_id]["primary_pump_power_consumption_total"]

                # 冷却塔ファン
                for unit_id in range(0, int(result_json["ref"][ref_name]["num_of_operation"][dd][hh])):
                    result_json["ref"][ref_name]["e_ref_ct_fan"][dd][hh] += \
                        input_data["ref"][ref_name]["heat_source"][unit_id]["cooling_tower_fan_power_consumption_total"]

                # 冷却水ポンプ
                if input_data["ref"][ref_name]["check_ctvwv"] == 1:  # 変流量制御がある場合

                    for unit_id in range(0, int(result_json["ref"][ref_name]["num_of_operation"][dd][hh])):

                        if "冷却水変流量" in input_data["ref"][ref_name]["heat_source"][unit_id]["heat_source_type"]:

                            if ave_l_per_u <= 0.5:
                                result_json["ref"][ref_name]["e_ref_ct_pumpa"][dd][hh] += \
                                    0.5 * input_data["ref"][ref_name]["heat_source"][unit_id][
                                        "cooling_tower_pump_power_consumption_total"]
                            else:
                                result_json["ref"][ref_name]["e_ref_ct_pumpa"][dd][hh] += \
                                    ave_l_per_u * input_data["ref"][ref_name]["heat_source"][unit_id][
                                        "cooling_tower_pump_power_consumption_total"]
                        else:
                            result_json["ref"][ref_name]["e_ref_ct_pumpa"][dd][hh] += \
                                input_data["ref"][ref_name]["heat_source"][unit_id][
                                    "cooling_tower_pump_power_consumption_total"]

                else:

                    for unit_id in range(0, int(result_json["ref"][ref_name]["num_of_operation"][dd][hh])):
                        result_json["ref"][ref_name]["e_ref_ct_pumpa"][dd][hh] += \
                            input_data["ref"][ref_name]["heat_source"][unit_id]["cooling_tower_pump_power_consumption_total"]

    # ----------------------------------------------------------------------------------
    # 熱熱源群の一次エネルギー消費量および消費電力（解説書 2.7.17）
    # ----------------------------------------------------------------------------------

    for ref_name in input_data["ref"]:

        for dd in range(0, 365):
            for hh in range(0, 24):

                if result_json["ref"][ref_name]["q_ref_hourly"][dd][hh] != 0:

                    # 熱源主機 [MJ/h]
                    for unit_id in range(0, len(input_data["ref"][ref_name]["heat_source"])):

                        result_json["ref"][ref_name]["E_ref_main"][dd][hh] += \
                            result_json["ref"][ref_name]["heat_source"][unit_id]["E_ref_main_kW"][dd][hh] * 3600 / 1000

                        # CGSの計算用に機種別に一次エネルギー消費量を積算 [MJ/h]
                        result_json["ref"][ref_name]["heat_source"][unit_id]["E_ref_main_MJ"][dd][hh] = \
                            result_json["ref"][ref_name]["heat_source"][unit_id]["E_ref_main_kW"][dd][hh] * 3600 / 1000

                        # CGSの計算用に電力のみ積算 [MWh]
                        if input_data["ref"][ref_name]["heat_source"][unit_id][
                            "ref_input_type"] == 1:  # 燃料種類が「電力」であれば、CGS計算用に集計を行う。

                            result_json["ref"][ref_name]["E_ref_main_MWh"][dd][hh] += \
                                result_json["ref"][ref_name]["heat_source"][unit_id]["E_ref_main_kW"][dd][
                                    hh] * 3600 / 1000 / bc.fprime

                            result_json["ref"][ref_name]["heat_source"][unit_id]["E_ref_main_MWh"][dd][hh] = \
                                result_json["ref"][ref_name]["heat_source"][unit_id]["E_ref_main_kW"][dd][
                                    hh] * 3600 / 1000 / bc.fprime

                    # 補機電力 [MWh]
                    result_json["ref"][ref_name]["e_ref_sub_MWh"][dd][hh] += \
                        result_json["ref"][ref_name]["e_ref_sub"][dd][hh] / 1000

                    # 一次ポンプ電力 [MWh]
                    result_json["ref"][ref_name]["E_ref_pump_MWh"][dd][hh] += \
                        result_json["ref"][ref_name]["E_ref_pump"][dd][hh] / 1000

                    # 冷却塔ファン電力 [MWh]
                    result_json["ref"][ref_name]["e_ref_ct_fan_MWh"][dd][hh] += \
                        result_json["ref"][ref_name]["e_ref_ct_fan"][dd][hh] / 1000

                    # 冷却水ポンプ電力 [MWh]
                    result_json["ref"][ref_name]["e_ref_ct_pumpa_MWh"][dd][hh] += \
                        result_json["ref"][ref_name]["e_ref_ct_pumpa"][dd][hh] / 1000

    if debug:  # pragma: no cover

        for ref_name in input_data["ref"]:
            mf.hourlyplot(result_json["ref"][ref_name]["E_ref_main"], "熱源主機エネルギー消費量： " + ref_name, "b",
                          "熱源主機エネルギー消費量")

            print(f'--- 熱源群名 {ref_name} ---')
            print(f'熱源群の処理熱量 q_ref_hourly: {np.sum(np.sum(result_json["ref"][ref_name]["q_ref_hourly"]))}')
            print(f'熱源主機のエネルギー消費量 E_ref_main: {np.sum(np.sum(result_json["ref"][ref_name]["E_ref_main"]))}')
            print(f'熱源補機の消費電力 e_ref_sub_MWh: {np.sum(np.sum(result_json["ref"][ref_name]["e_ref_sub_MWh"]))}')
            print(f'一次ポンプの消費電力 E_ref_pump_MWh: {np.sum(np.sum(result_json["ref"][ref_name]["E_ref_pump_MWh"]))}')
            print(
                f'冷却塔ファンの消費電力 e_ref_ct_fan_MWh: {np.sum(np.sum(result_json["ref"][ref_name]["e_ref_ct_fan_MWh"]))}')
            print(
                f'冷却塔ポンプの消費電力 e_ref_ct_pumpa_MWh: {np.sum(np.sum(result_json["ref"][ref_name]["e_ref_ct_pumpa_MWh"]))}')

    # ----------------------------------------------------------------------------------
    # 熱源群のエネルギー消費量（解説書 2.7.18）
    # ----------------------------------------------------------------------------------

    for ref_name in input_data["ref"]:

        # 熱源主機の電力消費量 [MWh/day]
        result_json["energy"]["e_ref_main_mwh_day"] += np.sum(result_json["ref"][ref_name]["E_ref_main_MWh"], axis=1)

        # 熱源主機以外の電力消費量 [MWh/day]
        result_json["energy"]["e_ref_sub_mwh_day"] += \
            np.sum(result_json["ref"][ref_name]["e_ref_sub_MWh"] \
                   + result_json["ref"][ref_name]["E_ref_pump_MWh"] \
                   + result_json["ref"][ref_name]["e_ref_ct_fan_MWh"] \
                   + result_json["ref"][ref_name]["e_ref_ct_pumpa_MWh"], axis=1)

        for dd in range(0, 365):
            for hh in range(0, 24):
                # 熱源主機のエネルギー消費量 [MJ]
                result_json["energy"]["E_ref_main"] += result_json["ref"][ref_name]["E_ref_main"][dd][hh]
                # 熱源補機電力消費量 [MWh]
                result_json["energy"]["e_ref_sub"] += result_json["ref"][ref_name]["e_ref_sub_MWh"][dd][hh]
                # 一次ポンプ電力消費量 [MWh]
                result_json["energy"]["E_ref_pump"] += result_json["ref"][ref_name]["E_ref_pump_MWh"][dd][hh]
                # 冷却塔ファン電力消費量 [MWh]
                result_json["energy"]["e_ref_ct_fan"] += result_json["ref"][ref_name]["e_ref_ct_fan_MWh"][dd][hh]
                # 冷却水ポンプ電力消費量 [MWh]
                result_json["energy"]["e_ref_ct_pumpa"] += result_json["ref"][ref_name]["e_ref_ct_pumpa_MWh"][dd][hh]

    print('熱源エネルギー計算完了')

    if debug:  # pragma: no cover

        print(f'熱源主機エネルギー消費量 E_ref_main: {result_json["energy"]["E_ref_main"]}')
        print(f'熱源補機電力消費量 e_ref_sub: {result_json["energy"]["e_ref_sub"]}')
        print(f'一次ポンプ電力消費量 E_ref_pump: {result_json["energy"]["E_ref_pump"]}')
        print(f'冷却塔ファン電力消費量 e_ref_ct_fan: {result_json["energy"]["e_ref_ct_fan"]}')
        print(f'冷却水ポンプ電力消費量 e_ref_ct_pumpa: {result_json["energy"]["e_ref_ct_pumpa"]}')

    # ----------------------------------------------------------------------------------
    # 設計一次エネルギー消費量（解説書 2.8）
    # ----------------------------------------------------------------------------------

    # 空気調和設備の設計一次エネルギー消費量 [MJ]
    result_json["E_ac"] = \
        + result_json["energy"]["E_ahu_fan"] * bc.fprime \
        + result_json["energy"]["E_ahu_aex"] * bc.fprime \
        + result_json["energy"]["E_pump"] * bc.fprime \
        + result_json["energy"]["E_ref_main"] \
        + result_json["energy"]["e_ref_sub"] * bc.fprime \
        + result_json["energy"]["E_ref_pump"] * bc.fprime \
        + result_json["energy"]["e_ref_ct_fan"] * bc.fprime \
        + result_json["energy"]["e_ref_ct_pumpa"] * bc.fprime

    if debug:  # pragma: no cover
        print(f'空調設備の設計一次エネルギー消費量 MJ/m2 : {result_json["E_ac"] / result_json["total_area"]}')
        print(f'空調設備の設計一次エネルギー消費量 MJ : {result_json["E_ac"]}')

    # ----------------------------------------------------------------------------------
    # 基準一次エネルギー消費量 （解説書 10.1）
    # ----------------------------------------------------------------------------------
    for room_zone_name in input_data["air_conditioning_zone"]:
        # 建物用途・室用途、ゾーン面積等の取得
        building_type = input_data["rooms"][room_zone_name]["building_type"]
        room_type = input_data["rooms"][room_zone_name]["room_type"]
        zone_area = input_data["rooms"][room_zone_name]["room_area"]

        # 空気調和設備の基準一次エネルギー消費量 [MJ]
        result_json["Es_ac"] += \
            bc.room_standard_value[building_type][room_type]["空調"][input_data["building"]["region"] + "地域"] * zone_area

    if debug:  # pragma: no cover
        print(f'空調設備の基準一次エネルギー消費量 MJ/m2 : {result_json["Es_ac"] / result_json["total_area"]}')
        print(f'空調設備の基準一次エネルギー消費量 MJ : {result_json["Es_ac"]}')

    # BEI/ACの算出
    result_json["BEI/AC"] = result_json["E_ac"] / result_json["Es_ac"]
    result_json["BEI/AC"] = math.ceil(result_json["BEI/AC"] * 100) / 100

    # ----------------------------------------------------------------------------------
    # CGS計算用変数 （解説書 ８章 附属書 G.10 他の設備の計算結果の読み込み）
    # ----------------------------------------------------------------------------------

    if len(input_data["cogeneration_systems"]) == 1:  # コジェネがあれば実行

        for cgs_name in input_data["cogeneration_systems"]:

            # 排熱を冷房に使用するか否か
            if input_data["cogeneration_systems"][cgs_name]["cooling_system"] is None:
                cgs_cooling = False
            else:
                cgs_cooling = True

            # 排熱を暖房に使用するか否か
            if input_data["cogeneration_systems"][cgs_name]["heating_system"] is None:
                cgs_heating = False
            else:
                cgs_heating = True

            # 排熱利用機器（冷房）
            if cgs_cooling:
                result_json["for_cgs"]["CGS_refname_C"] = input_data["cogeneration_systems"][cgs_name][
                                                             "cooling_system"] + "_冷房"
            else:
                result_json["for_cgs"]["CGS_refname_C"] = None

            # 排熱利用機器（暖房）
            if cgs_heating:
                result_json["for_cgs"]["cgs_ref_name_h"] = input_data["cogeneration_systems"][cgs_name][
                                                             "heating_system"] + "_暖房"
            else:
                result_json["for_cgs"]["cgs_ref_name_h"] = None

        # 熱源主機の電力消費量 [MWh/day]
        result_json["for_cgs"]["e_ref_main_mwh_day"] = result_json["energy"][
            "e_ref_main_mwh_day"]  # 後半でCGSから排熱供給を受ける熱源群の電力消費量を差し引く。

        # 熱源補機の電力消費量 [MWh/day]
        result_json["for_cgs"]["e_ref_sub_mwh_day"] = result_json["energy"]["e_ref_sub_mwh_day"]

        # 二次ポンプ群の電力消費量 [MWh/day]
        result_json["for_cgs"]["e_pump_mwh_day"] = result_json["energy"]["e_pump_mwh_day"]

        # 空調機群の電力消費量 [MWh/day]
        result_json["for_cgs"]["e_fan_mwh_day"] = result_json["energy"]["e_fan_mwh_day"]

        # 排熱利用熱源系統

        for ref_name in input_data["ref"]:

            # CGS系統の「排熱利用する冷熱源」　。　蓄熱がある場合は「追い掛け運転」を採用（2020/7/6変更）
            if ref_name == result_json["for_cgs"]["CGS_refname_C"]:

                for unit_id, unit_configure in enumerate(input_data["ref"][ref_name]["heat_source"]):

                    heat_source_using_exhaust_heat = [
                        "吸収式冷凍機(蒸気)",
                        "吸収式冷凍機(冷却水変流量、蒸気)",
                        "吸収式冷凍機(温水)",
                        "吸収式冷凍機(一重二重併用形、都市ガス)",
                        "吸収式冷凍機(一重二重併用形、冷却水変流量、都市ガス)",
                        "吸収式冷凍機(一重二重併用形、LPG)",
                        "吸収式冷凍機(一重二重併用形、冷却水変流量、LPG)",
                        "吸収式冷凍機(一重二重併用形、蒸気)",
                        "吸収式冷凍機(一重二重併用形、冷却水変流量、蒸気)"
                    ]

                    if unit_configure["heat_source_type"] in heat_source_using_exhaust_heat:

                        # CGS系統の「排熱利用する冷熱源」の「吸収式冷凍機（都市ガス）」の一次エネルギー消費量 [MJ]
                        for dd in range(0, 365):
                            result_json["for_cgs"]["e_ref_cgsc_abs_day"][dd] += np.sum(
                                result_json["ref"][ref_name]["heat_source"][unit_id]["E_ref_main_MJ"][dd])

                            # 排熱投入型吸収式冷温水機jの定格冷却能力
                        result_json["for_cgs"]["qac_link_c_j_rated"] += \
                        input_data["ref"][ref_name]["heat_source"][unit_id]["heat_source_rated_capacity_total"]

                        # 排熱投入型吸収式冷温水機jの主機定格消費エネルギー
                        result_json["for_cgs"]["eac_link_c_j_rated"] += \
                        input_data["ref"][ref_name]["heat_source"][unit_id]["heat_source_rated_fuel_consumption_total"]

                        result_json["for_cgs"]["nac_ref_link"] += 1

                # CGSの排熱利用が可能な排熱投入型吸収式冷温水機(系統)の冷熱源としての負荷率 [-]
                for dd in range(0, 365):
                    q_ref_daily = 0
                    t_ref_daily = 0
                    for hh in range(0, 24):
                        if result_json["ref"][ref_name]["q_ref_hourly"][dd][hh] > 0:
                            q_ref_daily += result_json["ref"][ref_name]["q_ref_hourly"][dd][hh]
                            t_ref_daily += 1

                    if t_ref_daily > 0:
                        result_json["for_cgs"]["lt_ref_cgs_c_day"][dd] = \
                            (q_ref_daily * 1000 / 3600) / t_ref_daily / input_data["ref"][ref_name]["q_ref_rated"]

                    if result_json["for_cgs"]["lt_ref_cgs_c_day"][dd] > 1:
                        result_json["for_cgs"]["lt_ref_cgs_c_day"][dd] = 1.2

                    # CGSの排熱利用が可能な排熱投入型吸収式冷温水機(系統)の運転時間 [h/日]
                    result_json["for_cgs"]["t_ref_cgs_c_day"][dd] = t_ref_daily

            # CGS系統の「排熱利用する温熱源」
            if ref_name == result_json["for_cgs"]["cgs_ref_name_h"]:

                # 当該温熱源群の主機の消費電力を差し引く。
                for unit_id, unit_configure in enumerate(input_data["ref"][ref_name]["heat_source"]):
                    for dd in range(0, 365):
                        result_json["for_cgs"]["e_ref_main_mwh_day"][dd] -= np.sum(
                            result_json["ref"][ref_name]["heat_source"][unit_id]["E_ref_main_MWh"][dd])

                # CGSの排熱利用が可能な温熱源群の主機の一次エネルギー消費量 [MJ/日]
                result_json["for_cgs"]["e_ref_cgsh_day"] = np.sum(result_json["ref"][ref_name]["E_ref_main"], axis=1)

                # CGSの排熱利用が可能な温熱源群の熱源負荷 [MJ/日]
                result_json["for_cgs"]["q_ref_cgs_h_day"] = np.sum(result_json["ref"][ref_name]["q_ref_hourly"], axis=1)

                # CGSの排熱利用が可能な温熱源群の運転時間 [h/日]
                for dd in range(0, 365):
                    for hh in range(0, 24):
                        if result_json["ref"][ref_name]["q_ref_hourly"][dd][hh] > 0:
                            result_json["for_cgs"]["t_ref_cgs_h_day"][dd] += 1

        # 空気調和設備の電力消費量 [MWh/day]
        result_json["for_cgs"]["electric_power_consumption"] = \
            + result_json["for_cgs"]["e_ref_main_mwh_day"] \
            + result_json["for_cgs"]["e_ref_sub_mwh_day"] \
            + result_json["for_cgs"]["e_pump_mwh_day"] \
            + result_json["for_cgs"]["e_fan_mwh_day"]

    # if debug:
    #     with open("input_dataJson_AC.json",'w', encoding='utf-8') as fw:
    #         json.dump(input_data, fw, indent=4, ensure_ascii=False, cls = bc.MyEncoder)

    # 入力データの保存
    result_json["input_data"] = input_data

    return result_json


if __name__ == '__main__':  # pragma: no cover

    print('----- airconditioning.py -----')
