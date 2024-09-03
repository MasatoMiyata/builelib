import json
import math
import os
import sys

import numpy as np

# import matplotlib.pyplot as plt
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import commons as bc
import climate
import shading

# from . import make_figure as mf

# データベースファイルの保存場所
database_directory = os.path.dirname(os.path.abspath(__file__)) + "/database/"
# 気象データファイルの保存場所
climatedata_directory = os.path.dirname(os.path.abspath(__file__)) + "/climatedata/"

# builelibモードかどうか（照明との連成、動的負荷計算）
BUILELIB_MODE = False


def count_Matrix(x, mxL):
    """
    負荷率 X がマトリックス mxL の何番目（ix）のセルに入るかをカウント
    """

    # 初期値
    ix = 0

    # C#の処理に合わせる（代表負荷率にする）
    # 負荷率1.00の場合は x=1.05となるため過負荷判定
    x = math.floor(x * 10) / 10 + 0.05

    # 該当するマトリックスを探査
    while x > mxL[ix]:
        ix += 1

        if ix == len(mxL) - 1:
            break

    return ix + 1


def air_enthalpy(Tdb, X):
    """
    空気のエンタルピーを算出する関数
    (WEBPROに合わせる)
    """

    Ca = 1.006  # 乾き空気の定圧比熱 [kJ/kg･K]
    Cw = 1.805  # 水蒸気の定圧比熱 [kJ/kg･K]
    Lw = 2502  # 水の蒸発潜熱 [kJ/kg]

    if len(Tdb) != len(X):
        raise Exception('温度と湿度のリストの長さが異なります。')
    else:

        H = np.zeros(len(Tdb))
        for i in range(0, len(Tdb)):
            H[i] = (Ca * Tdb[i] + (Cw * Tdb[i] + Lw) * X[i])

    return H


def calc_energy(input_data, debug=False):
    input_data["PUMP"] = {}
    input_data["REF"] = {}

    # 計算結果を格納する変数
    result_json = {

        "設計一次エネルギー消費量[MJ/年]": 0,  # 空調設備の設計一次エネルギー消費量 [MJ/年]
        "基準一次エネルギー消費量[MJ/年]": 0,  # 空調設備の基準一次エネルギー消費量 [MJ/年]
        "設計一次エネルギー消費量[GJ/年]": 0,  # 空調設備の設計一次エネルギー消費量 [GJ/年]
        "基準一次エネルギー消費量[GJ/年]": 0,  # 空調設備の基準一次エネルギー消費量 [GJ/年]
        "設計一次エネルギー消費量[MJ/m2年]": 0,  # 空調設備の設計一次エネルギー消費量 [MJ/年]
        "基準一次エネルギー消費量[MJ/m2年]": 0,  # 空調設備の基準一次エネルギー消費量 [MJ/年]
        "計算対象面積": 0,
        "BEI/AC": 0,
        "q_room": {
        },
        "AHU": {
        },
        "PUMP": {
        },
        "REF": {
        },
        "年間エネルギー消費量": {
            "空調機群ファン[MWh]": 0,  # 空調機群の一次エネルギー消費量 [MWh]
            "空調機群ファン[GJ]": 0,  # 空調機群の一次エネルギー消費量 [GJ]
            "空調機群全熱交換器[MWh]": 0,  # 全熱交換器の一次エネルギー消費量 [MWh]
            "空調機群全熱交換器[GJ]": 0,  # 全熱交換器の一次エネルギー消費量 [GJ]
            "二次ポンプ群[MWh]": 0,  # 二次ポンプ群の一次エネルギー消費量 [MWh]
            "二次ポンプ群[GJ]": 0,  # 二次ポンプ群の一次エネルギー消費量 [GJ]
            "熱源群熱源主機[MJ]": 0,  # 熱源群主機の一次エネルギー消費量 [MJ]
            "熱源群熱源主機[GJ]": 0,  # 熱源群主機の一次エネルギー消費量 [GJ]
            "熱源群熱源補機[MWh]": 0,  # 熱源群補機の一次エネルギー消費量 [MWh]
            "熱源群熱源補機[GJ]": 0,  # 熱源群補機の一次エネルギー消費量 [GJ]
            "熱源群一次ポンプ[MWh]": 0,  # 熱源群一次ポンプの一次エネルギー消費量 [MWh]
            "熱源群一次ポンプ[GJ]": 0,  # 熱源群一次ポンプの一次エネルギー消費量 [GJ]
            "熱源群冷却塔ファン[MWh]": 0,  # 熱源群冷却塔ファンの一次エネルギー消費量 [MWh]
            "熱源群冷却塔ファン[GJ]": 0,  # 熱源群冷却塔ファンの一次エネルギー消費量 [GJ]
            "熱源群冷却水ポンプ[MWh]": 0,  # 熱源群冷却水ポンプの一次エネルギー消費量 [MWh]
            "熱源群冷却水ポンプ[GJ]": 0,  # 熱源群冷却水ポンプの一次エネルギー消費量 [GJ]
        },
        "日別エネルギー消費量": {
            "E_fan_MWh_day": np.zeros(365),
            "E_pump_MWh_day": np.zeros(365),
            "E_ref_main_MWh_day": np.zeros(365),
            "E_ref_sub_MWh_day": np.zeros(365),
        },
        "Matrix": {
        },
        "for_CGS": {
        }
    }

    ##----------------------------------------------------------------------------------
    ## 定数の設定
    ##----------------------------------------------------------------------------------
    k_heatup = 0.84  # ファン・ポンプの発熱比率
    Cw = 4.186  # 水の比熱 [kJ/kg・K]
    divL = 11  # 負荷帯マトリックス分割数 （10区分＋過負荷1区分）
    div_temperature = 6  # 外気温度帯マトリックス分割数

    ##----------------------------------------------------------------------------------
    ## データベースファイルの読み込み
    ##----------------------------------------------------------------------------------

    # 流量制御
    with open(database_directory + 'flow_control.json', 'r', encoding='utf-8') as f:
        flow_control = json.load(f)

    # 熱源機器特性
    with open(database_directory + "heat_source_performance.json", 'r', encoding='utf-8') as f:
        heat_source_performance = json.load(f)

    ##----------------------------------------------------------------------------------
    ## 任意評定 （SP-1: 流量制御)
    ##----------------------------------------------------------------------------------

    # 任意評定用の入力があれば追加
    if "special_input_data" in input_data:
        if "flow_control" in input_data["special_input_data"]:
            flow_control.update(input_data["special_input_data"]["flow_control"])

    ##----------------------------------------------------------------------------------
    ## 任意評定 （SP-2：　熱源機器特性)
    ##----------------------------------------------------------------------------------

    # 任意評定用の入力があれば追加
    if "special_input_data" in input_data:
        if "heat_source_performance" in input_data["special_input_data"]:
            heat_source_performance.update(input_data["special_input_data"]["heat_source_performance"])

    ##----------------------------------------------------------------------------------
    ## マトリックスの設定
    ##----------------------------------------------------------------------------------

    # 地域別データの読み込み
    with open(database_directory + 'area.json', 'r', encoding='utf-8') as f:
        Area = json.load(f)

    # 負荷率帯マトリックス mxL = array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.2])
    mxL = np.arange(1 / (divL - 1), 1.01, 1 / (divL - 1))
    mxL = np.append(mxL, 1.2)

    # 負荷率帯マトリックス（平均） aveL = array([0.05, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.95, 1.2 ])
    aveL = np.zeros(len(mxL))
    for iL in range(0, len(mxL)):
        if iL == 0:
            aveL[0] = mxL[0] / 2
        elif iL == len(mxL) - 1:
            aveL[iL] = 1.2
        else:
            aveL[iL] = mxL[iL - 1] + (mxL[iL] - mxL[iL - 1]) / 2

    ##----------------------------------------------------------------------------------
    ## 日平均外気温 （解説書 2.7.4.1）
    ##----------------------------------------------------------------------------------

    # 外気温度帯の上限・下限
    mx_thermal_heating_min = Area[input_data["building"]["region"] + "地域"]["暖房時外気温下限"]
    mx_thermal_heating_max = Area[input_data["building"]["region"] + "地域"]["暖房時外気温上限"]
    mx_thermal_cooling_min = Area[input_data["building"]["region"] + "地域"]["冷房時外気温下限"]
    mx_thermal_cooling_max = Area[input_data["building"]["region"] + "地域"]["冷房時外気温上限"]

    del_temperature_cooling = (mx_thermal_cooling_max - mx_thermal_cooling_min) / div_temperature
    del_temperature_heating = (mx_thermal_heating_max - mx_thermal_heating_min) / div_temperature

    mx_thermal_cooling = np.arange(mx_thermal_cooling_min + del_temperature_cooling, mx_thermal_cooling_max + del_temperature_cooling, del_temperature_cooling)
    mx_thermal_heating = np.arange(mx_thermal_heating_min + del_temperature_heating, mx_thermal_heating_max + del_temperature_heating, del_temperature_heating)

    ToadbC = mx_thermal_cooling - del_temperature_cooling / 2
    ToadbH = mx_thermal_heating - del_temperature_heating / 2

    # 保存用
    result_json["Matrix"]["ToadbC"] = ToadbC
    result_json["Matrix"]["ToadbH"] = ToadbH

    ##----------------------------------------------------------------------------------
    ## 他人から供給された熱の一次エネルギー換算係数（デフォルト）
    ##----------------------------------------------------------------------------------

    if input_data["building"]["coefficient_dhc"]["cooling"] == None:
        input_data["building"]["coefficient_dhc"]["cooling"] = 1.36

    if input_data["building"]["coefficient_dhc"]["heating"] == None:
        input_data["building"]["coefficient_dhc"]["heating"] = 1.36

    ##----------------------------------------------------------------------------------
    ## 気象データ（解説書 2.2.1）
    ## 任意評定 （SP-5: 気象データ)
    ##----------------------------------------------------------------------------------

    if "climate_data" in input_data["special_input_data"]:  # 任意入力（SP-5）

        # 外気温 [℃]
        t_out_all = np.array(input_data["special_input_data"]["climate_data"]["tout"])
        # 外気湿度 [kg/kgDA]
        x_out_all = np.array(input_data["special_input_data"]["climate_data"]["xout"])
        # 法線面直達日射量 [W/m2]
        iod_all = np.array(input_data["special_input_data"]["climate_data"]["iod"])
        # 水平面天空日射量 [W/m2]
        ios_all = np.array(input_data["special_input_data"]["climate_data"]["ios"])
        # 水平面夜間放射量 [W/m2]
        inn_all = np.array(input_data["special_input_data"]["climate_data"]["inn"])

    else:

        # 気象データ（HASP形式）読み込み ＜365×24の行列＞
        [t_out_all, x_out_all, iod_all, ios_all, inn_all] = \
            climate.readHaspClimateData(
                climatedata_directory + "/" + Area[input_data["building"]["region"] + "地域"]["気象データファイル名"])

    # 緯度
    phi = Area[input_data["building"]["region"] + "地域"]["緯度"]
    # 経度
    longi = Area[input_data["building"]["region"] + "地域"]["経度"]

    ##----------------------------------------------------------------------------------
    ## 冷暖房期間（解説書 2.2.2）
    ##----------------------------------------------------------------------------------

    # 空調運転モード
    with open(database_directory + 'ac_operation_mode.json', 'r', encoding='utf-8') as f:
        ac_operation_mode = json.load(f)

    # 各日の冷暖房期間の種類（冷房期、暖房期、中間期）（365×1の行列）
    ac_mode = ac_operation_mode[Area[input_data["building"]["region"] + "地域"]["空調運転モードタイプ"]]

    ##----------------------------------------------------------------------------------
    ## 平均外気温（解説書 2.2.3）
    ##----------------------------------------------------------------------------------

    # 日平均外気温[℃]（365×1）
    toa_ave = np.mean(t_out_all, 1)
    toa_day = np.mean(t_out_all[:, [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17]], 1)
    toa_night = np.mean(t_out_all[:, [0, 1, 2, 3, 4, 5, 18, 19, 20, 21, 22, 23]], 1)

    # 日平均外気絶対湿度 [kg/kgDA]（365×1）
    xoa_ave = np.mean(x_out_all, 1)
    xoa_day = np.mean(x_out_all[:, [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17]], 1)
    xoa_night = np.mean(x_out_all[:, [0, 1, 2, 3, 4, 5, 18, 19, 20, 21, 22, 23]], 1)

    ##----------------------------------------------------------------------------------
    ## 外気エンタルピー（解説書 2.2.4）
    ##----------------------------------------------------------------------------------

    h_oa_ave = air_enthalpy(toa_ave, xoa_ave)
    h_oa_day = air_enthalpy(toa_day, xoa_day)
    h_oa_night = air_enthalpy(toa_night, xoa_night)

    ##----------------------------------------------------------------------------------
    ## 空調室の設定温度、室内エンタルピー（解説書 2.3.1、2.3.2）
    ##----------------------------------------------------------------------------------

    # todo: what is the meaning of p?
    room_temperature_setting = np.zeros(365)  # 室内設定温度
    room_humidity_setting = np.zeros(365)  # 室内設定湿度
    room_enthalpy_setting = np.zeros(365)  # 室内設定エンタルピー

    for dd in range(0, 365):

        if ac_mode[dd] == "冷房":
            room_temperature_setting[dd] = 26
            room_humidity_setting[dd] = 50
            room_enthalpy_setting[dd] = 52.91

        elif ac_mode[dd] == "中間":
            room_temperature_setting[dd] = 24
            room_humidity_setting[dd] = 50
            room_enthalpy_setting[dd] = 47.81

        elif ac_mode[dd] == "暖房":
            room_temperature_setting[dd] = 22
            room_humidity_setting[dd] = 40
            room_enthalpy_setting[dd] = 38.81

    ##----------------------------------------------------------------------------------
    ## 任意評定 （SP-6: カレンダーパターン)
    ##----------------------------------------------------------------------------------
    input_calendar = []
    if "calender" in input_data["special_input_data"]:
        input_calendar = input_data["special_input_data"]["calender"]

    ##----------------------------------------------------------------------------------
    ## 空調機の稼働状態、内部発熱量（解説書 2.3.3、2.3.4）
    ##----------------------------------------------------------------------------------

    room_area_total = 0
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
                if input_data["rooms"][room_name]["zone"] != None:  # ゾーンがあれば
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
        room_area_total += input_data["air_conditioning_zone"][room_zone_name]["zone_area"]

    ##----------------------------------------------------------------------------------
    ## 任意評定 （SP-7: 室スケジュール)
    ##----------------------------------------------------------------------------------

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

    # %%
    ##----------------------------------------------------------------------------------
    ## 室負荷計算（解説書 2.4）
    ##----------------------------------------------------------------------------------

    for room_zone_name in input_data["air_conditioning_zone"]:
        # TODO: Qの意味がわからない…
        result_json["q_room"][room_zone_name] = {
            "q_wall_temperature": np.zeros(365),  # 壁からの温度差による熱取得 [W/m2]
            "q_wall_solar": np.zeros(365),  # 壁からの日射による熱取得 [W/m2]
            "q_wall_night": np.zeros(365),  # 壁からの夜間放射による熱取得（マイナス）[W/m2]
            "q_window_temperature": np.zeros(365),  # 窓からの温度差による熱取得 [W/m2]
            "q_window_solar": np.zeros(365),  # 窓からの日射による熱取得 [W/m2]
            "q_window_night": np.zeros(365),  # 窓からの夜間放射による熱取得（マイナス）[W/m2]
            "q_room_daily_cooling": np.zeros(365),  # 冷房熱取得（日積算）　[MJ/day]
            "q_room_daily_heating": np.zeros(365),  # 暖房熱取得（日積算）　[MJ/day]
            "q_room_hourly_cooling": np.zeros((365, 24)),  # 冷房熱取得（時刻別）　[MJ/h]
            "q_room_hourly_heating": np.zeros((365, 24))  # 暖房熱取得（時刻別）　[MJ/h]
        }

    ##----------------------------------------------------------------------------------
    ## 外皮面への入射日射量（解説書 2.4.1）
    ##----------------------------------------------------------------------------------

    solor_radiation = {
        "直達": {
        },
        "直達_入射角特性込": {
        },
        "天空": {
        },
        "夜間": {
        }
    }

    # 方位角別の日射量
    (solor_radiation["直達"]["南"], solor_radiation["直達_入射角特性込"]["南"], solor_radiation["天空"]["垂直"],
     solor_radiation["夜間"]["垂直"]) = \
        climate.solar_radiation_by_azimuth(0, 90, phi, longi, iod_all, ios_all, inn_all)
    (solor_radiation["直達"]["南西"], solor_radiation["直達_入射角特性込"]["南西"], _,
     _) = climate.solar_radiation_by_azimuth(45, 90, phi, longi, iod_all, ios_all, inn_all)
    (solor_radiation["直達"]["西"], solor_radiation["直達_入射角特性込"]["西"], _, _) = climate.solar_radiation_by_azimuth(
        90, 90, phi, longi, iod_all, ios_all, inn_all)
    (solor_radiation["直達"]["北西"], solor_radiation["直達_入射角特性込"]["北西"], _,
     _) = climate.solar_radiation_by_azimuth(135, 90, phi, longi, iod_all, ios_all, inn_all)
    (solor_radiation["直達"]["北"], solor_radiation["直達_入射角特性込"]["北"], _, _) = climate.solar_radiation_by_azimuth(
        180, 90, phi, longi, iod_all, ios_all, inn_all)
    (solor_radiation["直達"]["北東"], solor_radiation["直達_入射角特性込"]["北東"], _,
     _) = climate.solar_radiation_by_azimuth(225, 90, phi, longi, iod_all, ios_all, inn_all)
    (solor_radiation["直達"]["東"], solor_radiation["直達_入射角特性込"]["東"], _, _) = climate.solar_radiation_by_azimuth(
        270, 90, phi, longi, iod_all, ios_all, inn_all)
    (solor_radiation["直達"]["南東"], solor_radiation["直達_入射角特性込"]["南東"], _,
     _) = climate.solar_radiation_by_azimuth(315, 90, phi, longi, iod_all, ios_all, inn_all)
    (solor_radiation["直達"]["水平"], solor_radiation["直達_入射角特性込"]["水平"], solor_radiation["天空"]["水平"],
     solor_radiation["夜間"]["水平"]) = \
        climate.solar_radiation_by_azimuth(0, 0, phi, longi, iod_all, ios_all, inn_all)

    ##----------------------------------------------------------------------------------
    ## 外壁等の熱貫流率の算出（解説書 附属書A.1）
    ##----------------------------------------------------------------------------------

    ### ISSUE : 二つのデータベースにわかれてしまっているので統一する。###

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
                    if (input_data["wall_configure"][wall_name]["conductivity"] == None):
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
                    if layer[1]["conductivity"] == None:

                        if (layer[1]["material_id"] == "密閉中空層") or (layer[1]["material_id"] == "非密閉中空層"):

                            # 空気層の場合
                            r_value += heat_thermal_conductivity[layer[1]["material_id"]]["熱抵抗値"]

                        else:

                            # 空気層以外の断熱材を指定している場合
                            if layer[1]["thickness"] != None:
                                material_name = layer[1]["material_id"].replace('\u3000', '')
                                r_value += (layer[1]["thickness"] / 1000) / heat_thermal_conductivity[material_name][
                                    "熱伝導率"]

                    else:

                        # 熱伝導率を入力している場合
                        r_value += (layer[1]["thickness"] / 1000) / layer[1]["conductivity"]

                input_data["wall_configure"][wall_name]["u_value"] = 1 / r_value

    ##----------------------------------------------------------------------------------
    ## 窓の熱貫流率及び日射熱取得率の算出（解説書 附属書A.2）
    ##----------------------------------------------------------------------------------

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

                #  TODO: iってなにをいみするか
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
                d_r = 0

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

                # print(ku_a)
                # print(ku_b)
                # print(glass2window[input_data["window_configure"][window_name]["frame_type"]][input_data["window_configure"][window_name]["layer_type"]]["ku_a1"] )
                # print(glass2window[input_data["window_configure"][window_name]["frame_type"]][input_data["window_configure"][window_name]["layer_type"]]["ku_a2"] )
                # print(glass2window[input_data["window_configure"][window_name]["frame_type"]][input_data["window_configure"][window_name]["layer_type"]]["ku_b1"] )
                # print(glass2window[input_data["window_configure"][window_name]["frame_type"]][input_data["window_configure"][window_name]["layer_type"]]["ku_b2"] )
                # print(input_data["window_configure"][window_name]["glassu_value"])

                input_data["window_configure"][window_name]["u_value"] = ku_a * input_data["window_configure"][window_name][
                    "glassu_value"] + ku_b
                input_data["window_configure"][window_name]["i_value"] = kita * input_data["window_configure"][window_name][
                    "glassi_value"]

                # ガラスの熱貫流率と日射熱取得率が入力されている場合は、ブラインドの効果を見込む
                # TODO:変数名わかりやすくする
                d_r = (0.021 / input_data["window_configure"][window_name]["glassu_value"]) + 0.022

                input_data["window_configure"][window_name]["u_value_blind"] = \
                    1 / ((1 / input_data["window_configure"][window_name]["u_value"]) + d_r)

                input_data["window_configure"][window_name]["i_value_blind"] = \
                    input_data["window_configure"][window_name]["i_value"] / input_data["window_configure"][window_name][
                        "glassi_value"] \
                    * (-0.1331 * input_data["window_configure"][window_name]["glassi_value"] ** 2 + \
                       0.8258 * input_data["window_configure"][window_name]["glassi_value"])


            elif input_data["window_configure"][window_name]["input_method"] == "性能値を入力":

                input_data["window_configure"][window_name]["u_value"] = input_data["window_configure"][window_name][
                    "windowu_value"]
                input_data["window_configure"][window_name]["i_value"] = input_data["window_configure"][window_name][
                    "windowi_value"]

                # ブラインド込みの値を計算
                d_r = 0

                if input_data["window_configure"][window_name]["glassu_value"] == None or \
                        input_data["window_configure"][window_name]["glassi_value"] == None:

                    input_data["window_configure"][window_name]["u_value_blind"] = \
                        input_data["window_configure"][window_name]["windowu_value"]
                    input_data["window_configure"][window_name]["i_value_blind"] = \
                        input_data["window_configure"][window_name]["windowi_value"]

                else:
                    # ガラスの熱貫流率と日射熱取得率が入力されている場合は、ブラインドの効果を見込む
                    d_r = (0.021 / input_data["window_configure"][window_name]["glassu_value"]) + 0.022

                    input_data["window_configure"][window_name]["u_value_blind"] = \
                        1 / ((1 / input_data["window_configure"][window_name]["windowu_value"]) + d_r)

                    input_data["window_configure"][window_name]["i_value_blind"] = \
                        input_data["window_configure"][window_name]["windowi_value"] / \
                        input_data["window_configure"][window_name]["glassi_value"] \
                        * (-0.1331 * input_data["window_configure"][window_name]["glassi_value"] ** 2 + \
                           0.8258 * input_data["window_configure"][window_name]["glassi_value"])

            if debug:  # pragma: no cover
                print(f'--- 窓名称 {window_name} ---')
                print(f'窓の熱貫流率 u_value : {input_data["window_configure"][window_name]["u_value"]}')
                print(f'窓+BLの熱貫流率 u_value_blind : {input_data["window_configure"][window_name]["u_value_blind"]}')

    ##----------------------------------------------------------------------------------
    ## 外壁の面積の計算（解説書 2.4.2.1）
    ##----------------------------------------------------------------------------------

    # 外皮面積の算出
    for room_zone_name in input_data["envelope_set"]:

        for wall_id, wall_configure in enumerate(input_data["envelope_set"][room_zone_name]["wall_list"]):

            if input_data["envelope_set"][room_zone_name]["wall_list"][wall_id][
                "envelope_area"] == None:  # 外皮面積が空欄であれば、外皮の寸法から面積を計算。

                input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["envelope_area"] = \
                    wall_configure["envelope_width"] * wall_configure["envelope_height"]

    # 窓面積の算出
    for window_id in input_data["window_configure"]:
        if input_data["window_configure"][window_id]["window_area"] == None:  # 窓面積が空欄であれば、窓寸法から面積を計算。
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
                input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["WallArea"] = wall_configure[
                                                                                                "envelope_area"] - window_total
            else:
                print(room_zone_name)
                print(wall_configure)
                raise Exception('窓面積が外皮面積よりも大きくなっています')

    ##----------------------------------------------------------------------------------
    ## 室の定常熱取得の計算（解説書 2.4.2.2〜2.4.2.7）
    ##----------------------------------------------------------------------------------

    ## envelope_set に wall_configure, window_configure の情報を貼り付ける。
    for room_zone_name in input_data["envelope_set"]:

        # 壁毎にループ
        for (wall_id, wall_configure) in enumerate(input_data["envelope_set"][room_zone_name]["wall_list"]):

            if input_data["wall_configure"][wall_configure["wall_spec"]]["input_method"] == "断熱材種類を入力":

                if wall_configure["direction"] == "水平（上）":  # 天井と見なす。

                    # 外壁のUA（熱貫流率×面積）を計算
                    input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["UA_wall"] = \
                        input_data["wall_configure"][wall_configure["wall_spec"]]["u_value_roof"] * wall_configure[
                            "WallArea"]

                    # 動的負荷計算用
                    input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["U_wall"] = \
                        input_data["wall_configure"][wall_configure["wall_spec"]]["u_value_roof"]
                    input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["WallArea"] = wall_configure[
                        "WallArea"]

                elif wall_configure["direction"] == "水平（下）":  # 床と見なす。

                    # 外壁のUA（熱貫流率×面積）を計算
                    input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["UA_wall"] = \
                        input_data["wall_configure"][wall_configure["wall_spec"]]["u_value_floor"] * wall_configure[
                            "WallArea"]

                    # 動的負荷計算用
                    input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["U_wall"] = \
                        input_data["wall_configure"][wall_configure["wall_spec"]]["u_value_floor"]
                    input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["WallArea"] = wall_configure[
                        "WallArea"]

                else:

                    # 外壁のUA（熱貫流率×面積）を計算
                    input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["UA_wall"] = \
                        input_data["wall_configure"][wall_configure["wall_spec"]]["u_value_wall"] * wall_configure[
                            "WallArea"]

                    # 動的負荷計算用
                    input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["U_wall"] = \
                        input_data["wall_configure"][wall_configure["wall_spec"]]["u_value_wall"]
                    input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["WallArea"] = wall_configure[
                        "WallArea"]

            else:

                # 外壁のUA（熱貫流率×面積）を計算
                input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["UA_wall"] = \
                    input_data["wall_configure"][wall_configure["wall_spec"]]["u_value"] * wall_configure["WallArea"]

                # 動的負荷計算用
                input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["U_wall"] = \
                    input_data["wall_configure"][wall_configure["wall_spec"]]["u_value"]
                input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["WallArea"] = wall_configure["WallArea"]

            # 日射吸収率
            if input_data["wall_configure"][wall_configure["wall_spec"]]["solar_absorption_ratio"] == None:
                input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["solar_absorption_ratio"] = 0.8
            else:
                input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["solar_absorption_ratio"] = \
                    float(input_data["wall_configure"][wall_configure["wall_spec"]]["solar_absorption_ratio"])

            for (window_id, window_configure) in enumerate(
                    input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["window_list"]):

                if window_configure["window_id"] != "無":

                    # 日よけ効果係数の算出
                    if window_configure["eaves_id"] == "無":

                        input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["window_list"][window_id][
                            "shading_effect_C"] = 1
                        input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["window_list"][window_id][
                            "shading_effect_H"] = 1

                    else:

                        if input_data["shading_config"][window_configure["eaves_id"]]["shading_effect_C"] != None and \
                                input_data["shading_config"][window_configure["eaves_id"]]["shading_effect_H"] != None:

                            input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["window_list"][window_id][
                                "shading_effect_C"] = \
                                input_data["shading_config"][window_configure["eaves_id"]]["shading_effect_C"]
                            input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["window_list"][window_id][
                                "shading_effect_H"] = \
                                input_data["shading_config"][window_configure["eaves_id"]]["shading_effect_H"]

                        else:

                            # 関数 shading.calc_shadingCoefficient で日よけ効果係数を算出。
                            (input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["window_list"][window_id][
                                 "shading_effect_C"], \
                             input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["window_list"][window_id][
                                 "shading_effect_H"]) = \
                                shading.calc_shadingCoefficient(input_data["building"]["region"], \
                                                                wall_configure["direction"], \
                                                                input_data["shading_config"][
                                                                    window_configure["eaves_id"]]["x1"], \
                                                                input_data["shading_config"][
                                                                    window_configure["eaves_id"]]["x2"], \
                                                                input_data["shading_config"][
                                                                    window_configure["eaves_id"]]["x3"], \
                                                                input_data["shading_config"][
                                                                    window_configure["eaves_id"]]["y1"], \
                                                                input_data["shading_config"][
                                                                    window_configure["eaves_id"]]["y2"], \
                                                                input_data["shading_config"][
                                                                    window_configure["eaves_id"]]["y3"], \
                                                                input_data["shading_config"][
                                                                    window_configure["eaves_id"]]["zxplus"], \
                                                                input_data["shading_config"][
                                                                    window_configure["eaves_id"]]["zxminus"], \
                                                                input_data["shading_config"][
                                                                    window_configure["eaves_id"]]["zyplus"], \
                                                                input_data["shading_config"][
                                                                    window_configure["eaves_id"]]["zyminus"])

                    # 窓のUA（熱貫流率×面積）を計算
                    if window_configure["is_blind"] == "無":  # ブラインドがない場合

                        input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["window_list"][window_id][
                            "UA_window"] = \
                            window_configure["window_number"] * \
                            input_data["window_configure"][window_configure["window_id"]]["window_area"] * \
                            input_data["window_configure"][window_configure["window_id"]]["u_value"]

                        input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["window_list"][window_id][
                            "IA_window"] = \
                            window_configure["window_number"] * \
                            input_data["window_configure"][window_configure["window_id"]]["window_area"] * \
                            input_data["window_configure"][window_configure["window_id"]]["i_value"]

                        # 動的負荷計算用
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
                            "UA_window"] = \
                            window_configure["window_number"] * \
                            input_data["window_configure"][window_configure["window_id"]]["window_area"] * \
                            input_data["window_configure"][window_configure["window_id"]]["u_value_blind"]

                        input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["window_list"][window_id][
                            "IA_window"] = \
                            window_configure["window_number"] * \
                            input_data["window_configure"][window_configure["window_id"]]["window_area"] * \
                            input_data["window_configure"][window_configure["window_id"]]["i_value_blind"]

                        # 動的負荷計算用
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

    for room_zone_name in input_data["air_conditioning_zone"]:

        q_wall_temperature = np.zeros(365)  # 壁からの温度差による熱取得 [W/m2]
        q_wall_solar = np.zeros(365)  # 壁からの日射による熱取得 [W/m2]
        q_wall_night = np.zeros(365)  # 壁からの夜間放射による熱取得（マイナス）[W/m2]
        q_window_temperature = np.zeros(365)  # 窓からの温度差による熱取得 [W/m2]
        q_window_solar = np.zeros(365)  # 窓からの日射による熱取得 [W/m2]
        q_window_night = np.zeros(365)  # 窓からの夜間放射による熱取得（マイナス）[W/m2]

        # 外壁があれば以下を実行
        if room_zone_name in input_data["envelope_set"]:

            # 壁毎にループ
            for (wall_id, wall_configure) in enumerate(input_data["envelope_set"][room_zone_name]["wall_list"]):

                if wall_configure["wall_type"] == "日の当たる外壁":

                    ## ① 温度差による熱取得
                    q_wall_temperature = q_wall_temperature + wall_configure["UA_wall"] * (toa_ave - room_temperature_setting) * 24

                    ## ② 日射による熱取得
                    if wall_configure["direction"] == "水平（上）" or wall_configure["direction"] == "水平（下）":
                        q_wall_solar = q_wall_solar + wall_configure["UA_wall"] * wall_configure["solar_absorption_ratio"] * 0.04 * \
                                  (solor_radiation["直達"]["水平"] + solor_radiation["天空"]["水平"])
                    else:
                        q_wall_solar = q_wall_solar + wall_configure["UA_wall"] * wall_configure["solar_absorption_ratio"] * 0.04 * \
                                  (solor_radiation["直達"][wall_configure["direction"]] + solor_radiation["天空"][
                                      "垂直"])

                    ## ③ 夜間放射による熱取得（マイナス）
                    if wall_configure["direction"] == "水平（上）" or wall_configure["direction"] == "水平（下）":
                        q_wall_night = q_wall_night - wall_configure["UA_wall"] * 0.9 * 0.04 * \
                                  (solor_radiation["夜間"]["水平"])
                    else:
                        q_wall_night = q_wall_night - wall_configure["UA_wall"] * 0.9 * 0.04 * \
                                  (solor_radiation["夜間"]["垂直"])

                elif wall_configure["wall_type"] == "日の当たらない外壁":

                    ## ① 温度差による熱取得
                    q_wall_temperature = q_wall_temperature + wall_configure["UA_wall"] * (toa_ave - room_temperature_setting) * 24

                    ## ③ 夜間放射による熱取得（マイナス）
                    if wall_configure["direction"] == "水平（上）" or wall_configure["direction"] == "水平（下）":
                        q_wall_night = q_wall_night - wall_configure["UA_wall"] * 0.9 * 0.04 * \
                                  (solor_radiation["夜間"]["水平"])
                    else:
                        q_wall_night = q_wall_night - wall_configure["UA_wall"] * 0.9 * 0.04 * \
                                  (solor_radiation["夜間"]["垂直"])

                elif wall_configure["wall_type"] == "地盤に接する外壁":

                    ## ① 温度差による熱取得
                    q_wall_temperature = q_wall_temperature + wall_configure["UA_wall"] * (np.mean(toa_ave) * np.ones(365) - room_temperature_setting) * 24

                    ## ③ 夜間放射による熱取得（マイナス） ：　本当はこれは不要。Webproの実装と合わせるために追加。
                    q_wall_night = q_wall_night - wall_configure["UA_wall"] * 0.9 * 0.04 * (solor_radiation["夜間"]["垂直"])

                elif wall_configure["wall_type"] == "地盤に接する外壁_Ver2":  # Webpro Ver2の互換のための処理

                    ## ① 温度差による熱取得
                    q_wall_temperature = q_wall_temperature + wall_configure["UA_wall"] * (np.mean(toa_ave) * np.ones(365) - room_temperature_setting) * 24

                    ## ② 日射による熱取得
                    if wall_configure["direction"] == "水平（上）" or wall_configure["direction"] == "水平（下）":
                        q_wall_solar = q_wall_solar + wall_configure["UA_wall"] * wall_configure["solar_absorption_ratio"] * 0.04 * \
                                  (solor_radiation["直達"]["水平"] + solor_radiation["天空"]["水平"])
                    else:
                        q_wall_solar = q_wall_solar + wall_configure["UA_wall"] * wall_configure["solar_absorption_ratio"] * 0.04 * \
                                  (solor_radiation["直達"][wall_configure["direction"]] + solor_radiation["天空"][
                                      "垂直"])

                    ## ③ 夜間放射による熱取得（マイナス）
                    if wall_configure["direction"] == "水平（上）" or wall_configure["direction"] == "水平（下）":
                        q_wall_night = q_wall_night - wall_configure["UA_wall"] * 0.9 * 0.04 * \
                                  (solor_radiation["夜間"]["水平"])
                    else:
                        q_wall_night = q_wall_night - wall_configure["UA_wall"] * 0.9 * 0.04 * \
                                  (solor_radiation["夜間"]["垂直"])

                        # 窓毎にループ
                for (window_id, window_configure) in enumerate(wall_configure["window_list"]):

                    if window_configure["window_id"] != "無":  # 窓がある場合

                        if wall_configure["wall_type"] == "日の当たる外壁" or wall_configure[
                            "wall_type"] == "地盤に接する外壁_Ver2":

                            ## ① 温度差による熱取得
                            q_window_temperature = q_window_temperature + window_configure["UA_window"] * (toa_ave - room_temperature_setting) * 24

                            ## ② 日射による熱取得
                            shading_daily = np.zeros(365)

                            for dd in range(0, 365):

                                if ac_mode[dd] == "冷房":
                                    shading_daily[dd] = window_configure["shading_effect_C"]
                                elif ac_mode[dd] == "中間":
                                    shading_daily[dd] = window_configure["shading_effect_C"]
                                elif ac_mode[dd] == "暖房":
                                    shading_daily[dd] = window_configure["shading_effect_H"]

                            if isinstance(window_configure["IA_window"], float):

                                # 様式2-3に入力された窓仕様を使用する場合
                                # 0.88は標準ガラスの日射熱取得率
                                # 0.89は標準ガラスの入射角特性の最大値
                                # 0.808は天空・反射日射に対する標準ガラスの入射角特性 0.808/0.88 = 0.91818
                                if wall_configure["direction"] == "水平（上）" or wall_configure[
                                    "direction"] == "水平（下）":

                                    q_window_solar = q_window_solar + shading_daily * \
                                              (window_configure["IA_window"] / 0.88) * \
                                              (solor_radiation["直達_入射角特性込"]["水平"] * 0.89 +
                                               solor_radiation["天空"]["水平"] * 0.808)

                                else:

                                    q_window_solar = q_window_solar + shading_daily * \
                                              (window_configure["IA_window"] / 0.88) * \
                                              (solor_radiation["直達_入射角特性込"][
                                                   wall_configure["direction"]] * 0.89 + solor_radiation["天空"][
                                                   "垂直"] * 0.808)

                            else:

                                # 任意入力の場合（SP-8）
                                if wall_configure["direction"] == "水平（上）" or wall_configure[
                                    "direction"] == "水平（下）":
                                    q_window_solar = q_window_solar + \
                                              (window_configure["IA_window"]) * (
                                                      solor_radiation["直達"]["水平"] + solor_radiation["天空"][
                                                  "水平"])
                                else:
                                    q_window_solar = q_window_solar + shading_daily * \
                                              (window_configure["IA_window"]) * (
                                                      solor_radiation["直達"][wall_configure["direction"]] +
                                                      solor_radiation["天空"]["垂直"])

                            ## ③ 夜間放射による熱取得（マイナス）
                            if wall_configure["direction"] == "水平（上）" or wall_configure["direction"] == "水平（下）":
                                q_window_night = q_window_night - window_configure["UA_window"] * 0.9 * 0.04 * \
                                          solor_radiation["夜間"]["水平"]
                            else:
                                q_window_night = q_window_night - window_configure["UA_window"] * 0.9 * 0.04 * \
                                          solor_radiation["夜間"]["垂直"]


                        elif wall_configure["wall_type"] == "日の当たらない外壁":

                            ## ③ 夜間放射による熱取得（マイナス）
                            q_window_night = q_window_night - window_configure["UA_window"] * 0.9 * 0.04 * solor_radiation["夜間"][
                                "水平"]

        #  室面積あたりの熱量に変換 [Wh/m2/日]
        result_json["q_room"][room_zone_name]["q_wall_temperature"] = q_wall_temperature / input_data["air_conditioning_zone"][room_zone_name][
            "zone_area"]
        result_json["q_room"][room_zone_name]["q_wall_solar"] = q_wall_solar / input_data["air_conditioning_zone"][room_zone_name][
            "zone_area"]
        result_json["q_room"][room_zone_name]["q_wall_night"] = q_wall_night / input_data["air_conditioning_zone"][room_zone_name][
            "zone_area"]
        result_json["q_room"][room_zone_name]["q_window_temperature"] = q_window_temperature / input_data["air_conditioning_zone"][room_zone_name][
            "zone_area"]
        result_json["q_room"][room_zone_name]["q_window_solar"] = q_window_solar / input_data["air_conditioning_zone"][room_zone_name][
            "zone_area"]
        result_json["q_room"][room_zone_name]["q_window_night"] = q_window_night / input_data["air_conditioning_zone"][room_zone_name][
            "zone_area"]

    ##----------------------------------------------------------------------------------
    ## 室負荷の計算（解説書 2.4.3、2.4.4）
    ##----------------------------------------------------------------------------------

    ## 室負荷計算のための係数（解説書 A.3）
    with open(database_directory + 'q_room_COEFFI_AREA' + input_data["building"]["region"] + '.json', 'r',
              encoding='utf-8') as f:
        q_room_COEFFI = json.load(f)

    Heat_light_hourly = {}
    Num_of_Person_hourly = {}
    Heat_OAapp_hourly = {}

    for room_zone_name in input_data["air_conditioning_zone"]:

        q_room_CTC = np.zeros(365)
        q_room_CTH = np.zeros(365)
        q_room_CSR = np.zeros(365)

        Qcool = np.zeros(365)
        Qheat = np.zeros(365)

        # 室が使用されているか否か＝空調運転時間（365日分）
        room_usage = np.sum(room_schedule_room[room_zone_name], 1)

        btype = input_data["air_conditioning_zone"][room_zone_name]["building_type"]
        rtype = input_data["air_conditioning_zone"][room_zone_name]["room_type"]

        # 発熱量参照値 [W/m2] を読み込む関数（空調）
        if "room_usage_condition" in input_data["special_input_data"]:
            (roomHeatGain_Light, roomHeatGain_Person, roomHeatGain_OAapp, roomNumOfPerson) = \
                bc.get_roomHeatGain(btype, rtype, input_data["special_input_data"]["room_usage_condition"])
        else:
            (roomHeatGain_Light, roomHeatGain_Person, roomHeatGain_OAapp, roomNumOfPerson) = \
                bc.get_roomHeatGain(btype, rtype)

        # 様式4から照明発熱量を読み込む
        if BUILELIB_MODE:
            if room_zone_name in input_data["lighting_systems"]:
                lighting_power = 0
                for unit_name in input_data["lighting_systems"][room_zone_name]["lighting_unit"]:
                    lighting_power += input_data["lighting_systems"][room_zone_name]["lighting_unit"][unit_name][
                                          "rated_power"] * \
                                      input_data["lighting_systems"][room_zone_name]["lighting_unit"][unit_name]["number"]
                roomHeatGain_Light = lighting_power / input_data["air_conditioning_zone"][room_zone_name]["zone_area"]

        Heat_light_daily = np.sum(room_schedule_light[room_zone_name], 1) * roomHeatGain_Light  # 照明からの発熱（日積算）（365日分）
        Heat_person_daily = np.sum(room_schedule_person[room_zone_name], 1) * roomHeatGain_Person  # 人体からの発熱（日積算）（365日分）
        Heat_OAapp_daily = np.sum(room_schedule_oa_app[room_zone_name], 1) * roomHeatGain_OAapp  # 機器からの発熱（日積算）（365日分）

        # 時刻別計算用（本来はこのループに入れるべきではない → 時刻別計算の方に入れるべき）
        Heat_light_hourly[room_zone_name] = room_schedule_light[room_zone_name] * roomHeatGain_Light  # 照明からの発熱 （365日分）
        Num_of_Person_hourly[room_zone_name] = room_schedule_person[room_zone_name] * roomNumOfPerson  # 人員密度（365日分）
        Heat_OAapp_hourly[room_zone_name] = room_schedule_oa_app[room_zone_name] * roomHeatGain_OAapp  # 機器からの発熱 （365日分）

        for dd in range(0, 365):

            if room_usage[dd] > 0:

                # 前日の空調の有無
                if "終日空調" in q_room_COEFFI[btype][rtype]:
                    onoff = "終日空調"
                elif (dd > 0) and (room_usage[dd - 1] > 0):
                    onoff = "前日空調"
                else:
                    onoff = "前日休み"

                if ac_mode[dd] == "冷房":

                    q_room_CTC[dd] = q_room_COEFFI[btype][rtype][onoff]["冷房期"]["外気温変動"]["冷房負荷"]["係数"] * \
                                    (result_json["q_room"][room_zone_name]["q_wall_temperature"][dd] +
                                     result_json["q_room"][room_zone_name]["q_wall_night"][dd] + \
                                     result_json["q_room"][room_zone_name]["q_window_temperature"][dd] +
                                     result_json["q_room"][room_zone_name]["q_window_night"][dd]) + \
                                    q_room_COEFFI[btype][rtype][onoff]["冷房期"]["外気温変動"]["冷房負荷"]["補正切片"]

                    q_room_CTH[dd] = q_room_COEFFI[btype][rtype][onoff]["冷房期"]["外気温変動"]["暖房負荷"]["係数"] * \
                                    (result_json["q_room"][room_zone_name]["q_wall_temperature"][dd] +
                                     result_json["q_room"][room_zone_name]["q_wall_night"][dd] + \
                                     result_json["q_room"][room_zone_name]["q_window_temperature"][dd] +
                                     result_json["q_room"][room_zone_name]["q_window_night"][dd]) + \
                                    q_room_COEFFI[btype][rtype][onoff]["冷房期"]["外気温変動"]["暖房負荷"]["補正切片"]

                    q_room_CSR[dd] = q_room_COEFFI[btype][rtype][onoff]["冷房期"]["日射量変動"]["冷房負荷"]["係数"] * \
                                    (result_json["q_room"][room_zone_name]["q_wall_solar"][dd] +
                                     result_json["q_room"][room_zone_name]["q_window_solar"][dd]) + \
                                    q_room_COEFFI[btype][rtype][onoff]["冷房期"]["日射量変動"]["冷房負荷"]["切片"]

                elif ac_mode[dd] == "暖房":

                    q_room_CTC[dd] = q_room_COEFFI[btype][rtype][onoff]["暖房期"]["外気温変動"]["冷房負荷"]["係数"] * \
                                    (result_json["q_room"][room_zone_name]["q_wall_temperature"][dd] +
                                     result_json["q_room"][room_zone_name]["q_wall_night"][dd] + \
                                     result_json["q_room"][room_zone_name]["q_window_temperature"][dd] +
                                     result_json["q_room"][room_zone_name]["q_window_night"][dd]) + \
                                    q_room_COEFFI[btype][rtype][onoff]["暖房期"]["外気温変動"]["冷房負荷"]["切片"]

                    q_room_CTH[dd] = q_room_COEFFI[btype][rtype][onoff]["暖房期"]["外気温変動"]["暖房負荷"]["係数"] * \
                                    (result_json["q_room"][room_zone_name]["q_wall_temperature"][dd] +
                                     result_json["q_room"][room_zone_name]["q_wall_night"][dd] + \
                                     result_json["q_room"][room_zone_name]["q_window_temperature"][dd] +
                                     result_json["q_room"][room_zone_name]["q_window_night"][dd]) + \
                                    q_room_COEFFI[btype][rtype][onoff]["暖房期"]["外気温変動"]["暖房負荷"]["切片"]

                    q_room_CSR[dd] = q_room_COEFFI[btype][rtype][onoff]["暖房期"]["日射量変動"]["冷房負荷"]["係数"] * \
                                    (result_json["q_room"][room_zone_name]["q_wall_solar"][dd] +
                                     result_json["q_room"][room_zone_name]["q_window_solar"][dd]) + \
                                    q_room_COEFFI[btype][rtype][onoff]["暖房期"]["日射量変動"]["冷房負荷"]["切片"]

                elif ac_mode[dd] == "中間":

                    q_room_CTC[dd] = q_room_COEFFI[btype][rtype][onoff]["中間期"]["外気温変動"]["冷房負荷"]["係数"] * \
                                    (result_json["q_room"][room_zone_name]["q_wall_temperature"][dd] +
                                     result_json["q_room"][room_zone_name]["q_wall_night"][dd] + \
                                     result_json["q_room"][room_zone_name]["q_window_temperature"][dd] +
                                     result_json["q_room"][room_zone_name]["q_window_night"][dd]) + \
                                    q_room_COEFFI[btype][rtype][onoff]["中間期"]["外気温変動"]["冷房負荷"]["補正切片"]

                    q_room_CTH[dd] = q_room_COEFFI[btype][rtype][onoff]["中間期"]["外気温変動"]["暖房負荷"]["係数"] * \
                                    (result_json["q_room"][room_zone_name]["q_wall_temperature"][dd] +
                                     result_json["q_room"][room_zone_name]["q_wall_night"][dd] + \
                                     result_json["q_room"][room_zone_name]["q_window_temperature"][dd] +
                                     result_json["q_room"][room_zone_name]["q_window_night"][dd]) + \
                                    q_room_COEFFI[btype][rtype][onoff]["中間期"]["外気温変動"]["暖房負荷"]["補正切片"]

                    q_room_CSR[dd] = q_room_COEFFI[btype][rtype][onoff]["中間期"]["日射量変動"]["冷房負荷"]["係数"] * \
                                    (result_json["q_room"][room_zone_name]["q_wall_solar"][dd] +
                                     result_json["q_room"][room_zone_name]["q_window_solar"][dd]) + \
                                    q_room_COEFFI[btype][rtype][onoff]["中間期"]["日射量変動"]["冷房負荷"]["切片"]

                if q_room_CTC[dd] < 0:
                    q_room_CTC[dd] = 0

                if q_room_CTH[dd] > 0:
                    q_room_CTH[dd] = 0

                if q_room_CSR[dd] < 0:
                    q_room_CSR[dd] = 0

                # 日射負荷 q_room_CSR を暖房負荷 q_room_CTH に足す
                Qcool[dd] = q_room_CTC[dd]
                Qheat[dd] = q_room_CTH[dd] + q_room_CSR[dd]

                # 日射負荷によって暖房負荷がプラスになった場合は、超過分を冷房負荷に加算 ＜この処理は意味をなしていない＝不要＞
                if Qheat[dd] > 0:
                    Qcool[dd] = Qcool[dd] + Qheat[dd]
                    Qheat[dd] = 0

                # 内部発熱を暖房負荷 Qheat に足す
                Qheat[dd] = Qheat[dd] + (Heat_light_daily[dd] + Heat_person_daily[dd] + Heat_OAapp_daily[dd])

                # 内部発熱によって暖房負荷がプラスになった場合は、超過分を冷房負荷に加算
                if Qheat[dd] > 0:
                    Qcool[dd] = Qcool[dd] + Qheat[dd]
                    Qheat[dd] = 0

            else:

                # 空調OFF時は 0 とする
                Qcool[dd] = 0
                Qheat[dd] = 0

        # 日積算熱取得　　q_room_daily_cooling, q_room_daily_heating [MJ/day]
        result_json["q_room"][room_zone_name]["q_room_daily_cooling"] = Qcool * (3600 / 1000000) * \
                                                         input_data["air_conditioning_zone"][room_zone_name]["zone_area"]
        result_json["q_room"][room_zone_name]["q_room_daily_heating"] = Qheat * (3600 / 1000000) * \
                                                         input_data["air_conditioning_zone"][room_zone_name]["zone_area"]

    if debug:  # pragma: no cover

        for room_zone_name in input_data["air_conditioning_zone"]:
            print(f'--- ゾーン名 {room_zone_name} ---')

            print(f'熱取得_壁温度 q_wall_temperature: {np.sum(result_json["q_room"][room_zone_name]["q_wall_temperature"], 0)}')
            print(f'熱取得_壁日射 q_wall_solar: {np.sum(result_json["q_room"][room_zone_name]["q_wall_solar"], 0)}')
            print(f'熱取得_壁放射 q_wall_night: {np.sum(result_json["q_room"][room_zone_name]["q_wall_night"], 0)}')
            print(f'熱取得_窓温度 q_window_temperature: {np.sum(result_json["q_room"][room_zone_name]["q_window_temperature"], 0)}')
            print(f'熱取得_窓日射 q_window_solar: {np.sum(result_json["q_room"][room_zone_name]["q_window_solar"], 0)}')
            print(f'熱取得_窓放射 q_window_night: {np.sum(result_json["q_room"][room_zone_name]["q_window_night"], 0)}')

    ##----------------------------------------------------------------------------------
    ## 任意評定用　室負荷（ SP-4 ）
    ##----------------------------------------------------------------------------------

    if "special_input_data" in input_data:
        if "q_room" in input_data["special_input_data"]:

            for room_zone_name in input_data["special_input_data"]["q_room"]:  # SP-4シートに入力された室毎に処理

                if room_zone_name in result_json["q_room"]:  # SP-4シートに入力された室が空調ゾーンとして存在していれば
                    # 室負荷（冷房要求）の置き換え [MJ/day]
                    if "q_room_daily_cooling" in input_data["special_input_data"]["q_room"][room_zone_name]:
                        result_json["q_room"][room_zone_name]["q_room_daily_cooling"] = \
                            input_data["special_input_data"]["q_room"][room_zone_name]["q_room_daily_cooling"]

                    # 室負荷（暖房要求）の置き換え
                    if "q_room_daily_heating" in input_data["special_input_data"]["q_room"][room_zone_name]:
                        result_json["q_room"][room_zone_name]["q_room_daily_heating"] = \
                            input_data["special_input_data"]["q_room"][room_zone_name]["q_room_daily_heating"]

    ##----------------------------------------------------------------------------------
    # 時刻別熱取得 [MJ/hour]
    ##----------------------------------------------------------------------------------
    for room_zone_name in input_data["air_conditioning_zone"]:

        for dd in range(0, 365):

            # 日別の運転時間 [h]
            daily_opetime = sum(room_schedule_room[room_zone_name][dd])

            for hh in range(0, 24):
                if room_schedule_room[room_zone_name][dd][hh] > 0:
                    # 冷房熱取得
                    result_json["q_room"][room_zone_name]["q_room_hourly_cooling"][dd][hh] = \
                        result_json["q_room"][room_zone_name]["q_room_daily_cooling"][dd] / daily_opetime
                    # 暖房熱取得
                    result_json["q_room"][room_zone_name]["q_room_hourly_heating"][dd][hh] = \
                        result_json["q_room"][room_zone_name]["q_room_daily_heating"][dd] / daily_opetime

    ##----------------------------------------------------------------------------------
    ## 動的室負荷計算
    ##----------------------------------------------------------------------------------
    if False:

        # 負荷計算モジュールの読み込み
        from . heat_load_calculation import Main
        import copy

        # ファイルの読み込み
        with open('./builelib/heat_load_calculation/heatload_calculation_template.json', 'r', encoding='utf-8') as js:
            # with open('input_non_residential.json', 'r', encoding='utf-8') as js:
            input_heatcalc_template = json.load(js)

        ## 入力ファイルの生成（共通）
        # 地域
        input_heatcalc_template["common"]["region"] = input_data["building"]["region"]
        input_heatcalc_template["common"]["is_residential"] = False

        # 室温上限値・下限
        input_heatcalc_template["rooms"][0]["schedule"]["temperature_upper_limit"] = np.reshape(
            room_temperature_setting * np.ones([24, 1]), 8760)
        input_heatcalc_template["rooms"][0]["schedule"]["temperature_lower_limit"] = np.reshape(
            room_temperature_setting * np.ones([24, 1]), 8760)

        # 相対湿度上限値・下限
        input_heatcalc_template["rooms"][0]["schedule"]["relative_humidity_upper_limit"] = np.reshape(
            room_humidity_setting * np.ones([24, 1]), 8760)
        input_heatcalc_template["rooms"][0]["schedule"]["relative_humidity_lower_limit"] = np.reshape(
            room_humidity_setting * np.ones([24, 1]), 8760)

        # 非住宅では使わない
        input_heatcalc_template["rooms"][0]["vent"] = 0
        input_heatcalc_template["rooms"][0]["schedule"]["heat_generation_cooking"] = np.zeros(8760)
        input_heatcalc_template["rooms"][0]["schedule"]["vapor_generation_cooking"] = np.zeros(8760)
        input_heatcalc_template["rooms"][0]["schedule"]["local_vent_amount"] = np.zeros(8760)

        # 空調ゾーン毎に負荷を計算
        for room_zone_name in input_data["air_conditioning_zone"]:

            # 入力ファイルの読み込み
            input_heatcalc = copy.deepcopy(input_heatcalc_template)

            ## 入力ファイルの生成（室単位）

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
                Heat_light_hourly[room_zone_name], 8760) * input_data["air_conditioning_zone"][room_zone_name]["zone_area"]
            # 機器発熱スケジュール[W]
            input_heatcalc["rooms"][0]["schedule"]["heat_generation_appliances"] = np.reshape(
                Heat_OAapp_hourly[room_zone_name], 8760) * input_data["air_conditioning_zone"][room_zone_name]["zone_area"]
            # 人員数[人]
            input_heatcalc["rooms"][0]["schedule"]["number_of_people"] = np.reshape(
                Num_of_Person_hourly[room_zone_name], 8760) * input_data["air_conditioning_zone"][room_zone_name][
                                                                             "zone_area"]

            # 床の設定
            input_heatcalc["rooms"][0]["boundaries"][0] = {
                "name": 'floor',
                "boundary_type": 'external_general_part',
                "area": input_data["air_conditioning_zone"][room_zone_name]["zone_area"],
                "is_sun_striked_outside": False,
                "temp_dif_coef": 0,
                "is_solar_absorbed_inside": True,
                "general_part_spec":
                    {
                        "outside_emissivity": 0.9,
                        "outside_solar_absorption": 0.8,
                        "inside_heat_transfer_resistance": 0.11,
                        "outside_heat_transfer_resistance": 0.11,
                        "layers": [
                            {
                                "name": 'カーペット類',
                                "thermal_resistance": 0.0875,
                                "thermal_capacity": 2.24,
                            },
                            {
                                "name": '鋼',
                                "thermal_resistance": 0.000066667,
                                "thermal_capacity": 10.86,
                            },
                            {
                                "name": '非密閉中空層',
                                "thermal_resistance": 0.086,
                                "thermal_capacity": 0,
                            },
                            {
                                "name": '普通コンクリート',
                                "thermal_resistance": 0.107142857,
                                "thermal_capacity": 289.5,
                            },
                            {
                                "name": '非密閉中空層',
                                "thermal_resistance": 0.086,
                                "thermal_capacity": 0,
                            },
                            {
                                "name": 'せっこうボード',
                                "thermal_resistance": 0.052941176,
                                "thermal_capacity": 9.27,
                            },
                            {
                                "name": 'ロックウール化粧吸音板',
                                "thermal_resistance": 0.1875,
                                "thermal_capacity": 3.0,
                            },
                        ],
                        "solar_shading_part": {
                            "existence": False
                        },
                    }
            }

            # 天井
            input_heatcalc["rooms"][0]["boundaries"][1] = {
                "name": 'ceil',
                "boundary_type": 'external_general_part',
                "area": input_data["air_conditioning_zone"][room_zone_name]["zone_area"],
                "is_sun_striked_outside": False,
                "temp_dif_coef": 0,
                "is_solar_absorbed_inside": True,
                "general_part_spec":
                    {
                        "outside_emissivity": 0.9,
                        "outside_solar_absorption": 0.8,
                        "inside_heat_transfer_resistance": 0.11,
                        "outside_heat_transfer_resistance": 0.11,
                        "layers": [
                            {
                                "name": 'ロックウール化粧吸音板',
                                "thermal_resistance": 0.1875,
                                "thermal_capacity": 3.0,
                            },
                            {
                                "name": 'せっこうボード',
                                "thermal_resistance": 0.052941176,
                                "thermal_capacity": 9.27,
                            },

                            {
                                "name": '非密閉中空層',
                                "thermal_resistance": 0.086,
                                "thermal_capacity": 0,
                            },
                            {
                                "name": '普通コンクリート',
                                "thermal_resistance": 0.107142857,
                                "thermal_capacity": 289.5,
                            },
                            {
                                "name": '非密閉中空層',
                                "thermal_resistance": 0.086,
                                "thermal_capacity": 0,
                            },
                            {
                                "name": '鋼',
                                "thermal_resistance": 0.000066667,
                                "thermal_capacity": 10.86,
                            },
                            {
                                "name": 'カーペット類',
                                "thermal_resistance": 0.0875,
                                "thermal_capacity": 2.24,
                            },
                        ],
                        "solar_shading_part": {
                            "existence": False
                        },
                    }
            }

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
                    elif input_data["envelope_set"][room_zone_name]["wall_list"][wall_id][
                        "wall_type"] == "地盤に接する外壁_Ver2":
                        boundary_type = "ground"
                        is_sun_striked_outside = False

                    if boundary_type == "external_general_part":

                        input_heatcalc["rooms"][0]["boundaries"].append(
                            {
                                "name": "wall",
                                "boundary_type": boundary_type,
                                "area": input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["WallArea"],
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
                                "area": input_data["envelope_set"][room_zone_name]["wall_list"][wall_id]["WallArea"],
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
            # with open("heatloadcalc_input.json",'w', encoding='utf-8') as fw:
            #     json.dump(input_heatcalc, fw, indent=4, ensure_ascii=False, cls = bc.MyEncoder)

            # 負荷計算の実行
            heatload_sensible_convection, heatload_sensible_radiation, heatload_latent = Main.run(input_heatcalc)

            # 負荷の積算（全熱負荷）[W] (365×24)
            heatload = np.array(
                bc.trans_8760to36524(heatload_sensible_convection) + \
                bc.trans_8760to36524(heatload_sensible_radiation) + \
                bc.trans_8760to36524(heatload_latent)
            )

            # 冷房負荷と暖房負荷に分離する。
            result_json["q_room"][room_zone_name]["q_room_daily_cooling"] = np.zeros(365)
            result_json["q_room"][room_zone_name]["q_room_daily_heating"] = np.zeros(365)
            result_json["q_room"][room_zone_name]["q_room_hourly_cooling"] = np.zeros((365, 24))
            result_json["q_room"][room_zone_name]["q_room_hourly_heating"] = np.zeros((365, 24))

            for dd in range(0, 365):
                for hh in range(0, 24):

                    if heatload[dd][hh] > 0:
                        # 暖房負荷 [W] → [MJ/hour]
                        result_json["q_room"][room_zone_name]["q_room_hourly_heating"][dd][hh] = (-1) * heatload[dd][
                            hh] * 3600 / 1000000
                        # 暖房負荷 [W] → [MJ/day]
                        result_json["q_room"][room_zone_name]["q_room_daily_heating"][dd] += (-1) * heatload[dd][hh] * 3600 / 1000000

                    elif heatload[dd][hh] < 0:
                        # 冷房負荷 [W] → [MJ/hour]
                        result_json["q_room"][room_zone_name]["q_room_hourly_cooling"][dd][hh] = (-1) * heatload[dd][
                            hh] * 3600 / 1000000
                        # 冷房負荷 [W]→ [MJ/day]
                        result_json["q_room"][room_zone_name]["q_room_daily_cooling"][dd] += (-1) * heatload[dd][hh] * 3600 / 1000000

            print(
                f'室負荷（冷房要求）の合計 heatload_for_cooling: {np.sum(result_json["q_room"][room_zone_name]["q_room_daily_cooling"], 0)}')
            print(
                f'室負荷（暖房要求）の合計 heatload_for_heating: {np.sum(result_json["q_room"][room_zone_name]["q_room_daily_heating"], 0)}')

    ##----------------------------------------------------------------------------------
    ## 負荷計算結果の集約
    ##----------------------------------------------------------------------------------
    for room_zone_name in input_data["air_conditioning_zone"]:
        # 結果の集約 [MJ/年]
        result_json["q_room"][room_zone_name]["建物用途"] = input_data["air_conditioning_zone"][room_zone_name][
            "building_type"]
        result_json["q_room"][room_zone_name]["室用途"] = input_data["air_conditioning_zone"][room_zone_name]["room_type"]
        result_json["q_room"][room_zone_name]["床面積"] = input_data["air_conditioning_zone"][room_zone_name]["zone_area"]
        result_json["q_room"][room_zone_name]["年間空調時間"] = np.sum(np.sum(room_schedule_room[room_zone_name]))

        result_json["q_room"][room_zone_name]["年間室負荷（冷房）[MJ]"] = np.sum(
            result_json["q_room"][room_zone_name]["q_room_daily_cooling"])
        result_json["q_room"][room_zone_name]["年間室負荷（暖房）[MJ]"] = np.sum(
            result_json["q_room"][room_zone_name]["q_room_daily_heating"])
        result_json["q_room"][room_zone_name]["平均室負荷（冷房）[W/m2]"] = \
            result_json["q_room"][room_zone_name]["年間室負荷（冷房）[MJ]"] * 1000000 \
            / (result_json["q_room"][room_zone_name]["年間空調時間"] * 3600) \
            / result_json["q_room"][room_zone_name]["床面積"]
        result_json["q_room"][room_zone_name]["平均室負荷（暖房）[W/m2]"] = \
            result_json["q_room"][room_zone_name]["年間室負荷（暖房）[MJ]"] * 1000000 \
            / (result_json["q_room"][room_zone_name]["年間空調時間"] * 3600) \
            / result_json["q_room"][room_zone_name]["床面積"]

    if debug:  # pragma: no cover
        for room_zone_name in input_data["air_conditioning_zone"]:
            print(f'--- ゾーン名 {room_zone_name} ---')
            print(f'年間室負荷（冷房要求） q_room_daily_cooling: {result_json["q_room"][room_zone_name]["年間室負荷（冷房）[MJ]"]}')
            print(f'年間室負荷（暖房要求） q_room_daily_heating: {result_json["q_room"][room_zone_name]["年間室負荷（暖房）[MJ]"]}')

    # 熱負荷のグラフ化（確認用）
    # for room_zone_name in input_data["air_conditioning_zone"]:

    #     mf.hourlyplot(result_json["q_room"][room_zone_name]["q_room_hourly_cooling"], "室負荷（冷房）："+room_zone_name, "b", "室負荷（冷房）")
    #     mf.hourlyplot(result_json["q_room"][room_zone_name]["q_room_hourly_heating"], "室負荷（暖房）："+room_zone_name, "m", "室負荷（暖房）")

    # plt.show()

    print('室負荷計算完了')

    ##----------------------------------------------------------------------------------
    ## 空調機群の一次エネルギー消費量（解説書 2.5）
    ##----------------------------------------------------------------------------------

    ## 結果格納用の変数
    for ahu_name in input_data["air_handling_system"]:
        result_json["AHU"][ahu_name] = {

            "day_mode": [],  # 空調機群の運転時間帯（昼、夜、終日）
            "schedule": np.zeros((365, 24)),  # 時刻別の運転スケジュール（365×24）
            "HoaDayAve": np.zeros(365),  # 空調運転時間帯の外気エンタルピー

            "qoaAHU": np.zeros(365),  # 日平均外気負荷 [kW]
            "Tahu_total": np.zeros(365),  # 空調機群の日積算運転時間（冷暖合計）

            "E_fan_day": np.zeros(365),  # 空調機群のエネルギー消費量
            "E_fan_c_day": np.zeros(365),  # 空調機群のエネルギー消費量（冷房）
            "E_fan_h_day": np.zeros(365),  # 空調機群のエネルギー消費量（暖房）
            "E_AHUaex_day": np.zeros(365),  # 全熱交換器のエネルギー消費量

            "TdAHUc_total": np.zeros(365),  # 空調機群の冷房運転時間の合計
            "TdAHUh_total": np.zeros(365),  # 空調機群の暖房運転時間の合計

            "Qahu_remainC": np.zeros(365),  # 空調機群の未処理負荷（冷房）[MJ/day]
            "Qahu_remainH": np.zeros(365),  # 空調機群の未処理負荷（暖房）[MJ/day]

            "energy_consumption_each_LF": np.zeros(len(aveL)),

            "q_room": {
                "cooling_for_room": np.zeros(365),  # 日積算室負荷（冷房要求）の積算値 [MJ/day]
                "heating_for_room": np.zeros(365),  # 日積算室負荷（暖房要求）の積算値 [MJ/day]
            },
            "Qahu": {
                "cooling_for_room": np.zeros(365),  # 室負荷が正（冷房要求）であるときの空調負荷（正であれば冷却コイル負荷、負であれば加熱コイル負荷） [MJ/day]
                "heating_for_room": np.zeros(365),  # 室負荷が負（暖房要求）であるときの空調負荷（正であれば冷却コイル負荷、負であれば加熱コイル負荷） [MJ/day]
            },
            "Tahu": {
                "cooling_for_room": np.zeros(365),  # 室負荷が冷房要求である場合の空調機群の運転時間 [h/day]
                "heating_for_room": np.zeros(365),  # 室負荷が暖房要求である場合の空調機群の運転時間 [h/day]
            },

            "Economizer": {
                "AHUVovc": np.zeros(365),  # 外気冷房運転時の外気風量 [kg/s]
                "Qahu_oac": np.zeros(365),  # 外気冷房による負荷削減効果 [MJ/day]
            },

            "LdAHUc": {
                "cooling_for_room": np.zeros(365),  # 空調機群の冷房運転時の負荷率帯（室負荷が冷房要求である場合）
                "heating_for_room": np.zeros(365),  # 空調機群の冷房運転時の負荷率帯（室負荷が暖房要求である場合）
            },
            "TdAHUc": {
                "cooling_for_room": np.zeros(365),  # 空調機群の冷房運転時間（室負荷が冷房要求である場合）
                "heating_for_room": np.zeros(365),  # 空調機群の冷房運転時間（室負荷が冷房要求である場合）
            },
            "LdAHUh": {
                "cooling_for_room": np.zeros(365),  # 空調機群の暖房負荷率帯（室負荷が冷房要求である場合）
                "heating_for_room": np.zeros(365),  # 空調機群の暖房負荷率帯（室負荷が冷房要求である場合）
            },
            "TdAHUh": {
                "cooling_for_room": np.zeros(365),  # 空調機群の暖房運転時間（室負荷が冷房要求である場合）
                "heating_for_room": np.zeros(365),  # 空調機群の暖房運転時間（室負荷が冷房要求である場合）
            },

            "TcAHU": 0,
            "ThAHU": 0,
            "MxAHUcE": 0,
            "MxAHUhE": 0
        }

    ##----------------------------------------------------------------------------------
    ## 空調機群全体のスペックを整理
    ##----------------------------------------------------------------------------------

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
            if unit_configure["rated_capacity_cooling"] != None:
                input_data["air_handling_system"][ahu_name]["rated_capacity_cooling"] += \
                    unit_configure["rated_capacity_cooling"] * unit_configure["number"]

            if unit_configure["rated_capacity_heating"] != None:
                input_data["air_handling_system"][ahu_name]["rated_capacity_heating"] += \
                    unit_configure["rated_capacity_heating"] * unit_configure["number"]

        # 空調機の風量 [m3/h]
        input_data["air_handling_system"][ahu_name]["fan_air_volume"] = 0
        for unit_id, unit_configure in enumerate(input_data["air_handling_system"][ahu_name]["air_handling_unit"]):
            if unit_configure["fan_air_volume"] != None:
                input_data["air_handling_system"][ahu_name]["fan_air_volume"] += \
                    unit_configure["fan_air_volume"] * unit_configure["number"]

        # 全熱交換器の有無
        input_data["air_handling_system"][ahu_name]["is_air_heat_exchanger"] = "無"
        for unit_id, unit_configure in enumerate(input_data["air_handling_system"][ahu_name]["air_handling_unit"]):
            if unit_configure["is_air_heat_exchanger"] == "全熱交換器あり・様式2-9記載無し":
                input_data["air_handling_system"][ahu_name]["is_air_heat_exchanger"] = "有"

        # 全熱交換器の効率（一番低いものを採用）
        input_data["air_handling_system"][ahu_name]["air_heat_exchange_ratio_cooling"] = None
        input_data["air_handling_system"][ahu_name]["air_heat_exchange_ratio_heating"] = None

        if input_data["air_handling_system"][ahu_name]["is_air_heat_exchanger"] == "有":
            for unit_id, unit_configure in enumerate(input_data["air_handling_system"][ahu_name]["air_handling_unit"]):

                # 冷房の効率
                if (unit_configure["air_heat_exchange_ratio_cooling"] != None):
                    if input_data["air_handling_system"][ahu_name]["air_heat_exchange_ratio_cooling"] == None:
                        input_data["air_handling_system"][ahu_name]["air_heat_exchange_ratio_cooling"] = unit_configure[
                            "air_heat_exchange_ratio_cooling"]
                    elif input_data["air_handling_system"][ahu_name]["air_heat_exchange_ratio_cooling"] > unit_configure[
                        "air_heat_exchange_ratio_cooling"]:
                        input_data["air_handling_system"][ahu_name]["air_heat_exchange_ratio_cooling"] = unit_configure[
                            "air_heat_exchange_ratio_cooling"]

                # 暖房の効率
                if (unit_configure["air_heat_exchange_ratio_heating"] != None):
                    if input_data["air_handling_system"][ahu_name]["air_heat_exchange_ratio_heating"] == None:
                        input_data["air_handling_system"][ahu_name]["air_heat_exchange_ratio_heating"] = unit_configure[
                            "air_heat_exchange_ratio_heating"]
                    elif input_data["air_handling_system"][ahu_name]["air_heat_exchange_ratio_heating"] > unit_configure[
                        "air_heat_exchange_ratio_heating"]:
                        input_data["air_handling_system"][ahu_name]["air_heat_exchange_ratio_heating"] = unit_configure[
                            "air_heat_exchange_ratio_heating"]

        # 全熱交換器のバイパス制御の有無（1つでもあればバイパス制御「有」とする）
        input_data["air_handling_system"][ahu_name]["air_heat_exchanger_control"] = "無"

        if input_data["air_handling_system"][ahu_name]["is_air_heat_exchanger"] == "有":
            for unit_id, unit_configure in enumerate(input_data["air_handling_system"][ahu_name]["air_handling_unit"]):
                if unit_configure["air_heat_exchanger_control"] == "有":
                    input_data["air_handling_system"][ahu_name]["air_heat_exchanger_control"] = "有"

        # 全熱交換器の消費電力 [kW]（積算する）
        input_data["air_handling_system"][ahu_name]["air_heat_exchanger_power_consumption"] = 0

        if input_data["air_handling_system"][ahu_name]["is_air_heat_exchanger"] == "有":
            for unit_id, unit_configure in enumerate(input_data["air_handling_system"][ahu_name]["air_handling_unit"]):
                if unit_configure["air_heat_exchanger_power_consumption"] != None:
                    input_data["air_handling_system"][ahu_name]["air_heat_exchanger_power_consumption"] += \
                        unit_configure["air_heat_exchanger_power_consumption"] * unit_configure["number"]

        # 全熱交換器の風量 [m3/h]（積算する）
        input_data["air_handling_system"][ahu_name]["AirHeatExchangerAirVolume"] = 0

        if input_data["air_handling_system"][ahu_name]["is_air_heat_exchanger"] == "有":
            for unit_id, unit_configure in enumerate(input_data["air_handling_system"][ahu_name]["air_handling_unit"]):
                if unit_configure["fan_air_volume"] != None:
                    input_data["air_handling_system"][ahu_name]["AirHeatExchangerAirVolume"] += \
                        unit_configure["fan_air_volume"] * unit_configure["number"]

    ##----------------------------------------------------------------------------------
    ## 二次ポンプ群の一次エネルギー消費量（解説書 2.6）
    ##----------------------------------------------------------------------------------

    # 二次ポンプが空欄であった場合、ダミーの仮想ポンプを追加する。
    number = 0
    for ahu_name in input_data["air_handling_system"]:

        if input_data["air_handling_system"][ahu_name]["pump_cooling"] == None:
            input_data["air_handling_system"][ahu_name]["pump_cooling"] = "dummyPump_" + str(number)

            input_data["secondary_pump_system"]["dummyPump_" + str(number)] = {
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

        if input_data["air_handling_system"][ahu_name]["pump_heating"] == None:
            input_data["air_handling_system"][ahu_name]["pump_heating"] = "dummyPump_" + str(number)

            input_data["secondary_pump_system"]["dummyPump_" + str(number)] = {
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

    ##----------------------------------------------------------------------------------
    ## 冷暖同時供給の有無の判定
    ##----------------------------------------------------------------------------------

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
                input_data["air_handling_system"][
                    input_data["air_conditioning_zone"][room_zone_name]["ahu_cooling_inside_load"]][
                    "heat_source_cooling"]
            id_ref_c2 = \
                input_data["air_handling_system"][
                    input_data["air_conditioning_zone"][room_zone_name]["ahu_cooling_outdoor_load"]][
                    "heat_source_cooling"]
            id_ref_h1 = \
                input_data["air_handling_system"][
                    input_data["air_conditioning_zone"][room_zone_name]["ahu_heating_inside_load"]][
                    "heat_source_heating"]
            id_ref_h2 = \
                input_data["air_handling_system"][
                    input_data["air_conditioning_zone"][room_zone_name]["ahu_heating_outdoor_load"]][
                    "heat_source_heating"]

            input_data["heat_source_system"][id_ref_c1]["is_simultaneous_supply"] = "有"
            input_data["heat_source_system"][id_ref_c2]["is_simultaneous_supply"] = "有"
            input_data["heat_source_system"][id_ref_h1]["is_simultaneous_supply"] = "有"
            input_data["heat_source_system"][id_ref_h2]["is_simultaneous_supply"] = "有"

            # 二次ポンプ群
            id_pump_c1 = \
                input_data["air_handling_system"][
                    input_data["air_conditioning_zone"][room_zone_name]["ahu_cooling_inside_load"]][
                    "pump_cooling"]
            id_pump_c2 = \
                input_data["air_handling_system"][
                    input_data["air_conditioning_zone"][room_zone_name]["ahu_cooling_outdoor_load"]][
                    "pump_cooling"]
            id_pump_h1 = \
                input_data["air_handling_system"][
                    input_data["air_conditioning_zone"][room_zone_name]["ahu_heating_inside_load"]][
                    "pump_heating"]
            id_pump_h2 = \
                input_data["air_handling_system"][
                    input_data["air_conditioning_zone"][room_zone_name]["ahu_heating_outdoor_load"]][
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
                input_data["air_handling_system"][
                    input_data["air_conditioning_zone"][room_zone_name]["ahu_cooling_inside_load"]][
                    "heat_source_cooling"]
            id_ref_h1 = \
                input_data["air_handling_system"][
                    input_data["air_conditioning_zone"][room_zone_name]["ahu_heating_inside_load"]][
                    "heat_source_heating"]

            input_data["heat_source_system"][id_ref_c1]["is_simultaneous_supply"] = "有"
            input_data["heat_source_system"][id_ref_h1]["is_simultaneous_supply"] = "有"

            # 二次ポンプ群
            id_pump_c1 = \
                input_data["air_handling_system"][
                    input_data["air_conditioning_zone"][room_zone_name]["ahu_cooling_inside_load"]][
                    "pump_cooling"]
            id_pump_h1 = \
                input_data["air_handling_system"][
                    input_data["air_conditioning_zone"][room_zone_name]["ahu_heating_inside_load"]][
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
                input_data["air_handling_system"][
                    input_data["air_conditioning_zone"][room_zone_name]["ahu_cooling_outdoor_load"]][
                    "heat_source_cooling"]
            id_ref_h2 = \
                input_data["air_handling_system"][
                    input_data["air_conditioning_zone"][room_zone_name]["ahu_heating_outdoor_load"]][
                    "heat_source_heating"]

            input_data["heat_source_system"][id_ref_c2]["is_simultaneous_supply"] = "有"
            input_data["heat_source_system"][id_ref_h2]["is_simultaneous_supply"] = "有"

            # 二次ポンプ群
            id_pump_c2 = \
                input_data["air_handling_system"][
                    input_data["air_conditioning_zone"][room_zone_name]["ahu_cooling_outdoor_load"]][
                    "pump_cooling"]
            id_pump_h2 = \
                input_data["air_handling_system"][
                    input_data["air_conditioning_zone"][room_zone_name]["ahu_heating_outdoor_load"]][
                    "pump_heating"]

            input_data["secondary_pump_system"][id_pump_c2]["is_simultaneous_supply"] = "有"
            input_data["secondary_pump_system"][id_pump_h2]["is_simultaneous_supply"] = "有"

    # 両方とも冷暖同時なら、その空調機群は冷暖同時運転可能とする。
    for ahu_name in input_data["air_handling_system"]:

        if (input_data["air_handling_system"][ahu_name]["is_simultaneous_supply_cooling"] == "有") and \
                (input_data["air_handling_system"][ahu_name]["is_simultaneous_supply_heating"] == "有"):
            input_data["air_handling_system"][ahu_name]["is_simultaneous_supply"] = "有"

    ##----------------------------------------------------------------------------------
    ## 空調機群が処理する日積算室負荷（解説書 2.5.1）
    ##----------------------------------------------------------------------------------
    for room_zone_name in input_data["air_conditioning_zone"]:
        # 室内負荷処理用空調機群の名称
        ahu_name = input_data["air_conditioning_zone"][room_zone_name]["ahu_cooling_inside_load"]

        # 当該空調機群が熱を供給する室の室負荷（冷房要求）を積算する。
        result_json["AHU"][ahu_name]["q_room"]["cooling_for_room"] += result_json["q_room"][room_zone_name]["q_room_daily_cooling"]

        # 当該空調機群が熱を供給する室の室負荷（暖房要求）を積算する。
        result_json["AHU"][ahu_name]["q_room"]["heating_for_room"] += result_json["q_room"][room_zone_name]["q_room_daily_heating"]

    ##----------------------------------------------------------------------------------
    ## 空調機群の運転時間（解説書 2.5.2）
    ##----------------------------------------------------------------------------------

    for room_zone_name in input_data["air_conditioning_zone"]:
        # 室内負荷処理用空調機群の名称
        ahu_name = input_data["air_conditioning_zone"][room_zone_name]["ahu_cooling_inside_load"]

        # 室の空調有無 room_schedule_room（365×24）を加算
        result_json["AHU"][ahu_name]["schedule"] += room_schedule_room[room_zone_name]
        # 運転時間帯（昼、夜、終日）をリストに追加していく。
        result_json["AHU"][ahu_name]["day_mode"].append(room_day_mode[room_zone_name])

    for room_zone_name in input_data["air_conditioning_zone"]:
        # 外気負荷処理用空調機群の名称
        ahu_name = input_data["air_conditioning_zone"][room_zone_name]["ahu_cooling_outdoor_load"]

        # 室の空調有無 room_schedule_room（365×24）を加算
        result_json["AHU"][ahu_name]["schedule"] += room_schedule_room[room_zone_name]
        # 運転時間帯（昼、夜、終日）をリストに追加していく。
        result_json["AHU"][ahu_name]["day_mode"].append(room_day_mode[room_zone_name])

    # 各空調機群の運転時間
    for ahu_name in input_data["air_handling_system"]:

        # 運転スケジュールの和が「1以上（どこか一部屋は動いている）」であれば、空調機は稼働しているとする。
        result_json["AHU"][ahu_name]["schedule"][result_json["AHU"][ahu_name]["schedule"] > 1] = 1

        # 空調機群の日積算運転時間（冷暖合計）
        result_json["AHU"][ahu_name]["Tahu_total"] = np.sum(result_json["AHU"][ahu_name]["schedule"], 1)

        # 空調機の運転モード と　外気エンタルピー
        if "終日" in result_json["AHU"][ahu_name]["day_mode"]:  # 一つでも「終日」があれば
            result_json["AHU"][ahu_name]["day_mode"] = "終日"
            result_json["AHU"][ahu_name]["HoaDayAve"] = h_oa_ave

        elif result_json["AHU"][ahu_name]["day_mode"].count("昼") == len(
                result_json["AHU"][ahu_name]["day_mode"]):  # 全て「昼」であれば
            result_json["AHU"][ahu_name]["day_mode"] = "昼"
            result_json["AHU"][ahu_name]["HoaDayAve"] = h_oa_day

        elif result_json["AHU"][ahu_name]["day_mode"].count("夜") == len(
                result_json["AHU"][ahu_name]["day_mode"]):  # 全て夜であれば
            result_json["AHU"][ahu_name]["day_mode"] = "夜"
            result_json["AHU"][ahu_name]["HoaDayAve"] = h_oa_night

        else:  # 「昼」と「夜」が混在する場合は「終日とする。
            result_json["AHU"][ahu_name]["day_mode"] = "終日"
            result_json["AHU"][ahu_name]["HoaDayAve"] = h_oa_ave

        # 日別に運転時間を「冷房」と「暖房」に振り分ける。
        for dd in range(0, 365):

            if result_json["AHU"][ahu_name]["Tahu_total"][dd] == 0:

                # 日空調時間が0であれば、冷暖房空調時間は0とする。
                result_json["AHU"][ahu_name]["Tahu"]["cooling_for_room"][dd] = 0
                result_json["AHU"][ahu_name]["Tahu"]["heating_for_room"][dd] = 0

            else:

                if (result_json["AHU"][ahu_name]["q_room"]["cooling_for_room"][dd] == 0) and \
                        (result_json["AHU"][ahu_name]["q_room"]["heating_for_room"][
                             dd] == 0):  # 外調機を想定（空調運転時間は0より大きいが、q_roomが0である場合）

                    # 外調機の場合は「冷房側」に運転時間を割り当てる。
                    result_json["AHU"][ahu_name]["Tahu"]["cooling_for_room"][dd] = \
                        result_json["AHU"][ahu_name]["Tahu_total"][dd]
                    result_json["AHU"][ahu_name]["Tahu"]["heating_for_room"][dd] = 0

                elif result_json["AHU"][ahu_name]["q_room"]["cooling_for_room"][dd] == 0:  # 暖房要求しかない場合。

                    result_json["AHU"][ahu_name]["Tahu"]["cooling_for_room"][dd] = 0
                    result_json["AHU"][ahu_name]["Tahu"]["heating_for_room"][dd] = \
                        result_json["AHU"][ahu_name]["Tahu_total"][dd]

                elif result_json["AHU"][ahu_name]["q_room"]["heating_for_room"][dd] == 0:  # 冷房要求しかない場合。

                    result_json["AHU"][ahu_name]["Tahu"]["cooling_for_room"][dd] = \
                        result_json["AHU"][ahu_name]["Tahu_total"][dd]
                    result_json["AHU"][ahu_name]["Tahu"]["heating_for_room"][dd] = 0

                else:  # 冷房要求と暖房要求の両方が発生する場合

                    if abs(result_json["AHU"][ahu_name]["q_room"]["cooling_for_room"][dd]) < abs(
                            result_json["AHU"][ahu_name]["q_room"]["heating_for_room"][dd]):

                        # 暖房負荷の方が大きい場合
                        ratio = abs(result_json["AHU"][ahu_name]["q_room"]["cooling_for_room"][dd]) / \
                                (abs(result_json["AHU"][ahu_name]["q_room"]["cooling_for_room"][dd]) + abs(
                                    result_json["AHU"][ahu_name]["q_room"]["heating_for_room"][dd]))

                        result_json["AHU"][ahu_name]["Tahu"]["cooling_for_room"][dd] = math.ceil(
                            result_json["AHU"][ahu_name]["Tahu_total"][dd] * ratio)
                        result_json["AHU"][ahu_name]["Tahu"]["heating_for_room"][dd] = \
                            result_json["AHU"][ahu_name]["Tahu_total"][dd] - \
                            result_json["AHU"][ahu_name]["Tahu"]["cooling_for_room"][dd]

                    else:

                        # 冷房負荷の方が大きい場合
                        ratio = abs(result_json["AHU"][ahu_name]["q_room"]["heating_for_room"][dd]) / \
                                (abs(result_json["AHU"][ahu_name]["q_room"]["cooling_for_room"][dd]) + abs(
                                    result_json["AHU"][ahu_name]["q_room"]["heating_for_room"][dd]))

                        result_json["AHU"][ahu_name]["Tahu"]["heating_for_room"][dd] = math.ceil(
                            result_json["AHU"][ahu_name]["Tahu_total"][dd] * ratio)
                        result_json["AHU"][ahu_name]["Tahu"]["cooling_for_room"][dd] = \
                            result_json["AHU"][ahu_name]["Tahu_total"][dd] - \
                            result_json["AHU"][ahu_name]["Tahu"]["heating_for_room"][dd]

    ##----------------------------------------------------------------------------------
    ## 外気負荷[kW]の算出（解説書 2.5.3）
    ##----------------------------------------------------------------------------------

    # 外気導入量 [m3/h]
    for ahu_name in input_data["air_handling_system"]:
        input_data["air_handling_system"][ahu_name]["outdoorAirVolume_cooling"] = 0
        input_data["air_handling_system"][ahu_name]["outdoorAirVolume_heating"] = 0

    for room_zone_name in input_data["air_conditioning_zone"]:

        # 各室の外気導入量 [m3/h]
        if "room_usage_condition" in input_data["special_input_data"]:  # SPシートで任意の入力がされている場合

            input_data["air_conditioning_zone"][room_zone_name]["outdoorAirVolume"] = \
                bc.get_roomOutdoorAirVolume(
                    input_data["air_conditioning_zone"][room_zone_name]["building_type"],
                    input_data["air_conditioning_zone"][room_zone_name]["room_type"],
                    input_data["special_input_data"]["room_usage_condition"]
                ) * input_data["air_conditioning_zone"][room_zone_name]["zone_area"]

        else:

            input_data["air_conditioning_zone"][room_zone_name]["outdoorAirVolume"] = \
                bc.get_roomOutdoorAirVolume(
                    input_data["air_conditioning_zone"][room_zone_name]["building_type"],
                    input_data["air_conditioning_zone"][room_zone_name]["room_type"]
                ) * input_data["air_conditioning_zone"][room_zone_name]["zone_area"]

        # 冷房期間における外気風量 [m3/h]
        input_data["air_handling_system"][input_data["air_conditioning_zone"][room_zone_name]["ahu_cooling_outdoor_load"]][
            "outdoorAirVolume_cooling"] += \
            input_data["air_conditioning_zone"][room_zone_name]["outdoorAirVolume"]

        # 暖房期間における外気風量 [m3/h]
        input_data["air_handling_system"][input_data["air_conditioning_zone"][room_zone_name]["ahu_heating_outdoor_load"]][
            "outdoorAirVolume_heating"] += \
            input_data["air_conditioning_zone"][room_zone_name]["outdoorAirVolume"]

    # 全熱交換効率の補正
    for ahu_name in input_data["air_handling_system"]:

        # 冷房運転時の補正
        if input_data["air_handling_system"][ahu_name]["air_heat_exchange_ratio_cooling"] != None:
            ahuaexeff = input_data["air_handling_system"][ahu_name]["air_heat_exchange_ratio_cooling"] / 100
            aexCeff = 1 - ((1 / 0.85) - 1) * (1 - ahuaexeff) / ahuaexeff
            aexCtol = 0.95
            aexCbal = 0.67
            input_data["air_handling_system"][ahu_name]["air_heat_exchange_ratio_cooling"] = \
                ahuaexeff * aexCeff * aexCtol * aexCbal

        # 暖房運転時の補正
        if input_data["air_handling_system"][ahu_name]["air_heat_exchange_ratio_heating"] != None:
            ahuaexeff = input_data["air_handling_system"][ahu_name]["air_heat_exchange_ratio_heating"] / 100
            aexCeff = 1 - ((1 / 0.85) - 1) * (1 - ahuaexeff) / ahuaexeff
            aexCtol = 0.95
            aexCbal = 0.67
            input_data["air_handling_system"][ahu_name]["air_heat_exchange_ratio_heating"] = \
                ahuaexeff * aexCeff * aexCtol * aexCbal

    # 外気負荷[kW]
    for ahu_name in input_data["air_handling_system"]:

        for dd in range(0, 365):

            if result_json["AHU"][ahu_name]["Tahu_total"][dd] > 0:  # 空調機が稼働する場合

                # 運転モードによって場合分け
                if ac_mode[dd] == "暖房":

                    # 外気導入量 [m3/h]
                    ahuVoa = input_data["air_handling_system"][ahu_name]["outdoorAirVolume_heating"]
                    # 全熱交換風量 [m3/h]
                    ahuaexV = input_data["air_handling_system"][ahu_name]["AirHeatExchangerAirVolume"]

                    # 全熱交換風量（0以上、外気導入量以下とする）
                    if ahuaexV > ahuVoa:
                        ahuaexV = ahuVoa
                    elif ahuaexV <= 0:
                        ahuaexV = 0

                        # 外気負荷の算出
                    if input_data["air_handling_system"][ahu_name]["is_air_heat_exchanger"] == "無":  # 全熱交換器がない場合

                        result_json["AHU"][ahu_name]["qoaAHU"][dd] = \
                            (result_json["AHU"][ahu_name]["HoaDayAve"][dd] - room_enthalpy_setting[dd]) * \
                            input_data["air_handling_system"][ahu_name]["outdoorAirVolume_heating"] * 1.293 / 3600

                    else:  # 全熱交換器がある場合

                        if (result_json["AHU"][ahu_name]["HoaDayAve"][dd] > room_enthalpy_setting[dd]) and (
                                input_data["air_handling_system"][ahu_name]["air_heat_exchanger_control"] == "有"):

                            # バイパス有の場合はそのまま外気導入する。
                            result_json["AHU"][ahu_name]["qoaAHU"][dd] = \
                                (result_json["AHU"][ahu_name]["HoaDayAve"][dd] - room_enthalpy_setting[dd]) * \
                                input_data["air_handling_system"][ahu_name]["outdoorAirVolume_heating"] * 1.293 / 3600

                        else:

                            # 全熱交換器による外気負荷削減を見込む。
                            result_json["AHU"][ahu_name]["qoaAHU"][dd] = \
                                (result_json["AHU"][ahu_name]["HoaDayAve"][dd] - room_enthalpy_setting[dd]) * \
                                (input_data["air_handling_system"][ahu_name]["outdoorAirVolume_heating"] - \
                                 ahuaexV * input_data["air_handling_system"][ahu_name][
                                     "air_heat_exchange_ratio_heating"]) * 1.293 / 3600


                elif (ac_mode[dd] == "中間") or (ac_mode[dd] == "冷房"):

                    ahuVoa = input_data["air_handling_system"][ahu_name]["outdoorAirVolume_cooling"]
                    ahuaexV = input_data["air_handling_system"][ahu_name]["AirHeatExchangerAirVolume"]

                    # 全熱交換風量（0以上、外気導入量以下とする）
                    if ahuaexV > ahuVoa:
                        ahuaexV = ahuVoa
                    elif ahuaexV <= 0:
                        ahuaexV = 0

                    # 外気負荷の算出
                    if input_data["air_handling_system"][ahu_name]["is_air_heat_exchanger"] == "無":  # 全熱交換器がない場合

                        result_json["AHU"][ahu_name]["qoaAHU"][dd] = \
                            (result_json["AHU"][ahu_name]["HoaDayAve"][dd] - room_enthalpy_setting[dd]) * \
                            input_data["air_handling_system"][ahu_name]["outdoorAirVolume_cooling"] * 1.293 / 3600

                    else:  # 全熱交換器がある場合

                        if (result_json["AHU"][ahu_name]["HoaDayAve"][dd] < room_enthalpy_setting[dd]) and (
                                input_data["air_handling_system"][ahu_name]["air_heat_exchanger_control"] == "有"):

                            # バイパス有の場合はそのまま外気導入する。
                            result_json["AHU"][ahu_name]["qoaAHU"][dd] = \
                                (result_json["AHU"][ahu_name]["HoaDayAve"][dd] - room_enthalpy_setting[dd]) * \
                                input_data["air_handling_system"][ahu_name]["outdoorAirVolume_cooling"] * 1.293 / 3600

                        else:  # 全熱交換器がある場合

                            # 全熱交換器による外気負荷削減を見込む。
                            result_json["AHU"][ahu_name]["qoaAHU"][dd] = \
                                (result_json["AHU"][ahu_name]["HoaDayAve"][dd] - room_enthalpy_setting[dd]) * \
                                (input_data["air_handling_system"][ahu_name]["outdoorAirVolume_cooling"] - \
                                 ahuaexV * input_data["air_handling_system"][ahu_name][
                                     "air_heat_exchange_ratio_cooling"]) * 1.293 / 3600

    ##----------------------------------------------------------------------------------
    ## 外気冷房制御による負荷削減量（解説書 2.5.4）
    ##----------------------------------------------------------------------------------

    for ahu_name in input_data["air_handling_system"]:

        for dd in range(0, 365):

            if result_json["AHU"][ahu_name]["Tahu_total"][dd] > 0:  # 空調機が稼働する場合

                # 外気冷房効果の推定
                if (input_data["air_handling_system"][ahu_name]["is_economizer"] == "有") and (
                        result_json["AHU"][ahu_name]["Tahu"]["cooling_for_room"][dd] > 0):  # 外気冷房があり、室負荷が冷房要求であれば

                    # 外気冷房運転時の外気風量 [kg/s]
                    result_json["AHU"][ahu_name]["Economizer"]["AHUVovc"][dd] = \
                        result_json["AHU"][ahu_name]["q_room"]["cooling_for_room"][dd] / \
                        ((room_enthalpy_setting[dd] - result_json["AHU"][ahu_name]["HoaDayAve"][dd]) * (3600 / 1000) *
                         result_json["AHU"][ahu_name]["Tahu"]["cooling_for_room"][dd])

                    # 上限・下限
                    if result_json["AHU"][ahu_name]["Economizer"]["AHUVovc"][dd] < \
                            input_data["air_handling_system"][ahu_name]["outdoorAirVolume_cooling"] * 1.293 / 3600:

                        # 下限（外気取入量） [m3/h]→[kg/s]
                        result_json["AHU"][ahu_name]["Economizer"]["AHUVovc"][dd] = \
                            input_data["air_handling_system"][ahu_name]["outdoorAirVolume_cooling"] * 1.293 / 3600

                    elif result_json["AHU"][ahu_name]["Economizer"]["AHUVovc"][dd] > \
                            input_data["air_handling_system"][ahu_name]["economizer_max_air_volume"] * 1.293 / 3600:

                        # 上限（給気風量) [m3/h]→[kg/s]
                        result_json["AHU"][ahu_name]["Economizer"]["AHUVovc"][dd] = \
                            input_data["air_handling_system"][ahu_name]["economizer_max_air_volume"] * 1.293 / 3600

                    # 追加すべき外気量（外気冷房用の追加分のみ）[kg/s]
                    result_json["AHU"][ahu_name]["Economizer"]["AHUVovc"][dd] = \
                        result_json["AHU"][ahu_name]["Economizer"]["AHUVovc"][dd] - \
                        input_data["air_handling_system"][ahu_name]["outdoorAirVolume_cooling"] * 1.293 / 3600

                # 外気冷房による負荷削減効果 [MJ/day]
                if (input_data["air_handling_system"][ahu_name]["is_economizer"] == "有"):  # 外気冷房があれば

                    if result_json["AHU"][ahu_name]["Economizer"]["AHUVovc"][dd] > 0:  # 外冷時風量＞０であれば

                        result_json["AHU"][ahu_name]["Economizer"]["Qahu_oac"][dd] = \
                            result_json["AHU"][ahu_name]["Economizer"]["AHUVovc"][dd] * (
                                    room_enthalpy_setting[dd] - result_json["AHU"][ahu_name]["HoaDayAve"][dd]) * 3600 / 1000 * \
                            result_json["AHU"][ahu_name]["Tahu"]["cooling_for_room"][dd]

    ##----------------------------------------------------------------------------------
    ## 日積算空調負荷 Qahu_c, Qahu_h の算出（解説書 2.5.5）
    ##----------------------------------------------------------------------------------

    for ahu_name in input_data["air_handling_system"]:

        for dd in range(0, 365):

            # 外気負荷のみの処理が要求される空調機群である場合(処理上、「室負荷が冷房要求である場合」 として扱う)
            if (result_json["AHU"][ahu_name]["Tahu"]["cooling_for_room"][dd] == 0) and (
                    result_json["AHU"][ahu_name]["Tahu"]["heating_for_room"][dd] == 0):

                if (input_data["air_handling_system"][ahu_name]["is_outdoor_air_cut"] == "無"):

                    result_json["AHU"][ahu_name]["Qahu"]["cooling_for_room"][dd] = \
                        result_json["AHU"][ahu_name]["qoaAHU"][dd] * result_json["AHU"][ahu_name]["Tahu_total"][
                            dd] * 3600 / 1000

                else:

                    # 運転時間が1時間より大きい場合は、外気カットの効果を見込む。
                    if result_json["AHU"][ahu_name]["Tahu_total"][dd] > 1:
                        result_json["AHU"][ahu_name]["Qahu"]["cooling_for_room"][dd] = \
                            result_json["AHU"][ahu_name]["qoaAHU"][dd] * (
                                    result_json["AHU"][ahu_name]["Tahu_total"][dd] - 1) * 3600 / 1000

                    else:

                        # 運転時間が1時間以下である場合は、外気カットの効果を見込まない。
                        result_json["AHU"][ahu_name]["Qahu"]["cooling_for_room"][dd] = \
                            result_json["AHU"][ahu_name]["qoaAHU"][dd] * result_json["AHU"][ahu_name]["Tahu_total"][
                                dd] * 3600 / 1000

                # 外気負荷のみ場合は、便宜上、暖房要求の室負荷は 0 であるとする。
                result_json["AHU"][ahu_name]["Qahu"]["heating_for_room"][dd] = 0


            else:  # 室負荷と外気負荷の両方を処理が要求される空調機群である場合

                # 冷房要求の室負荷を処理する必要がある場合
                if result_json["AHU"][ahu_name]["Tahu"]["cooling_for_room"][dd] > 0:

                    if (input_data["air_handling_system"][ahu_name]["is_outdoor_air_cut"] == "有") and \
                            (result_json["AHU"][ahu_name]["Tahu"]["cooling_for_room"][dd] > 1) and \
                            (result_json["AHU"][ahu_name]["Tahu"]["cooling_for_room"][dd] >=
                             result_json["AHU"][ahu_name]["Tahu"]["heating_for_room"][dd]):

                        # 室負荷が正（冷房要求）であるときの空調負荷（正であれば冷却コイル負荷、負であれば加熱コイル負荷）　外気カットの効果を見込む
                        result_json["AHU"][ahu_name]["Qahu"]["cooling_for_room"][dd] = \
                            result_json["AHU"][ahu_name]["q_room"]["cooling_for_room"][dd] + \
                            result_json["AHU"][ahu_name]["qoaAHU"][dd] * (
                                    result_json["AHU"][ahu_name]["Tahu"]["cooling_for_room"][dd] - 1) * 3600 / 1000

                    else:

                        # 室負荷が正（冷房要求）であるときの空調負荷（正であれば冷却コイル負荷、負であれば加熱コイル負荷）
                        result_json["AHU"][ahu_name]["Qahu"]["cooling_for_room"][dd] = \
                            result_json["AHU"][ahu_name]["q_room"]["cooling_for_room"][dd] + \
                            result_json["AHU"][ahu_name]["qoaAHU"][dd] * (
                                result_json["AHU"][ahu_name]["Tahu"]["cooling_for_room"][dd]) * 3600 / 1000

                # 暖房要求の室負荷を処理する必要がある場合
                if result_json["AHU"][ahu_name]["Tahu"]["heating_for_room"][dd] > 0:

                    if (input_data["air_handling_system"][ahu_name]["is_outdoor_air_cut"] == "有") and \
                            (result_json["AHU"][ahu_name]["Tahu"]["heating_for_room"][dd] > 1) and \
                            (result_json["AHU"][ahu_name]["Tahu"]["cooling_for_room"][dd] <
                             result_json["AHU"][ahu_name]["Tahu"]["heating_for_room"][dd]):

                        # 室負荷が負（暖房要求）であるときの空調負荷（正であれば冷却コイル負荷、負であれば加熱コイル負荷）　外気カットの効果を見込む
                        result_json["AHU"][ahu_name]["Qahu"]["heating_for_room"][dd] = \
                            result_json["AHU"][ahu_name]["q_room"]["heating_for_room"][dd] + \
                            result_json["AHU"][ahu_name]["qoaAHU"][dd] * (
                                    result_json["AHU"][ahu_name]["Tahu"]["heating_for_room"][dd] - 1) * 3600 / 1000

                    else:

                        # 室負荷が負（暖房要求）であるときの空調負荷（正であれば冷却コイル負荷、負であれば加熱コイル負荷）
                        result_json["AHU"][ahu_name]["Qahu"]["heating_for_room"][dd] = \
                            result_json["AHU"][ahu_name]["q_room"]["heating_for_room"][dd] + \
                            result_json["AHU"][ahu_name]["qoaAHU"][dd] * (
                                result_json["AHU"][ahu_name]["Tahu"]["heating_for_room"][dd]) * 3600 / 1000

    print('空調負荷計算完了')

    if debug:  # pragma: no cover

        for ahu_name in input_data["air_handling_system"]:
            print(f'--- 空調機群名 {ahu_name} ---')

            print(f'外気負荷 qoaAHU {np.sum(result_json["AHU"][ahu_name]["qoaAHU"], 0)}')
            print(
                f'外気導入量 outdoorAirVolume_cooling {input_data["air_handling_system"][ahu_name]["outdoorAirVolume_cooling"]} m3/h')
            print(
                f'外気冷房時最大風量 economizer_max_air_volume {input_data["air_handling_system"][ahu_name]["economizer_max_air_volume"]} m3/h')
            print(f'外気冷房時風量 AHUVovc {np.sum(result_json["AHU"][ahu_name]["Economizer"]["AHUVovc"], 0)}')
            print(f'外気冷房効果 Qahu_oac： {np.sum(result_json["AHU"][ahu_name]["Economizer"]["Qahu_oac"], 0)}')

            print(
                f'室負荷が正（冷房要求）であるときの空調機群の運転時間 Tahu： {np.sum(result_json["AHU"][ahu_name]["Tahu"]["cooling_for_room"], 0)} 時間')
            print(
                f'室負荷が負（暖房要求）であるときの空調機群の運転時間 Tahu： {np.sum(result_json["AHU"][ahu_name]["Tahu"]["heating_for_room"], 0)} 時間')
            print(
                f'室負荷が正（冷房要求）であるときの空調負荷 Qahu： {np.sum(result_json["AHU"][ahu_name]["Qahu"]["cooling_for_room"], 0)}')
            print(
                f'室負荷が負（暖房要求）であるときの空調負荷 Qahu： {np.sum(result_json["AHU"][ahu_name]["Qahu"]["heating_for_room"], 0)}')

            print(f'空調機群 冷暖同時供給の有無： {input_data["air_handling_system"][ahu_name]["is_simultaneous_supply"]}')

    ##----------------------------------------------------------------------------------
    ## 任意評定用　空調負荷（ SP-10 ）
    ##----------------------------------------------------------------------------------

    if "special_input_data" in input_data:
        if "Qahu" in input_data["special_input_data"]:

            for ahu_name in input_data["special_input_data"]["Qahu"]:  # SP-10シートに入力された空調機群毎に処理
                if ahu_name in result_json["AHU"]:  # SP-10シートに入力された室が空調機群として存在していれば

                    Qahu_cooling = np.zeros(365)
                    Tahu_cooling = np.zeros(365)
                    Qahu_heating = np.zeros(365)
                    Tahu_heating = np.zeros(365)

                    for dd in range(0, 365):
                        for hh in range(0, 24):
                            if input_data["special_input_data"]["Qahu"][ahu_name][dd][hh] > 0:  # 冷房負荷であれば

                                # 空調負荷[kW] → [MJ/h]
                                Qahu_cooling[dd] += input_data["special_input_data"]["Qahu"][ahu_name][dd][
                                                        hh] * 3600 / 1000
                                Tahu_cooling[dd] += 1

                            elif input_data["special_input_data"]["Qahu"][ahu_name][dd][hh] < 0:  # 冷房負荷であれば

                                # 空調負荷[kW] → [MJ/h]
                                Qahu_heating[dd] += input_data["special_input_data"]["Qahu"][ahu_name][dd][
                                                        hh] * 3600 / 1000
                                Tahu_heating[dd] += 1

                    # 空調負荷 [MJ/day] を上書き
                    result_json["AHU"][ahu_name]["Qahu"]["cooling_for_room"] = Qahu_cooling
                    result_json["AHU"][ahu_name]["Qahu"]["heating_for_room"] = Qahu_heating
                    result_json["AHU"][ahu_name]["Tahu"]["cooling_for_room"] = Tahu_cooling
                    result_json["AHU"][ahu_name]["Tahu"]["heating_for_room"] = Tahu_heating

                    # 外気冷房は強制的に0とする（既に見込まれているものとする）
                    result_json["AHU"][ahu_name]["Economizer"]["Qahu_oac"] = np.zeros(365)

    ##----------------------------------------------------------------------------------
    ## 空調機群の負荷率（解説書 2.5.6）
    ##----------------------------------------------------------------------------------

    for ahu_name in input_data["air_handling_system"]:

        # 冷房要求の場合と暖房要求の場合で処理を繰り返す（同じ日に両方発生する場合がある）
        for requirement_type in ["cooling_for_room", "heating_for_room"]:

            La = np.zeros(365)

            # 負荷率の算出
            if requirement_type == "cooling_for_room":  # 室負荷が正（冷房要求）であるとき

                # 室負荷が正（冷房要求）であるときの平均負荷率 La [-]
                for dd in range(0, 365):

                    if result_json["AHU"][ahu_name]["Qahu"]["cooling_for_room"][dd] >= 0 and \
                            result_json["AHU"][ahu_name]["Tahu"]["cooling_for_room"][dd] != 0:

                        # 空調負荷が正（冷却コイル負荷）である場合　→　定格冷却能力で除して負荷率を求める。
                        La[dd] = (result_json["AHU"][ahu_name]["Qahu"]["cooling_for_room"][dd] /
                                  result_json["AHU"][ahu_name]["Tahu"]["cooling_for_room"][dd] * 1000 / 3600) / \
                                 input_data["air_handling_system"][ahu_name]["rated_capacity_cooling"]

                    elif result_json["AHU"][ahu_name]["Tahu"]["cooling_for_room"][dd] != 0:

                        # 空調負荷が負（加熱コイル負荷）である場合　→　定格加熱能力で除して負荷率を求める。
                        La[dd] = (result_json["AHU"][ahu_name]["Qahu"]["cooling_for_room"][dd] /
                                  result_json["AHU"][ahu_name]["Tahu"]["cooling_for_room"][dd] * 1000 / 3600) / \
                                 input_data["air_handling_system"][ahu_name]["rated_capacity_heating"]


            elif requirement_type == "heating_for_room":  # 室負荷が負（暖房要求）であるとき

                # 室負荷が負（暖房要求）であるときの平均負荷率 La [-]
                for dd in range(0, 365):

                    if result_json["AHU"][ahu_name]["Qahu"]["heating_for_room"][dd] <= 0 and \
                            result_json["AHU"][ahu_name]["Tahu"]["heating_for_room"][dd] != 0:

                        # 空調負荷が負（加熱コイル負荷）である場合　→　定格加熱能力で除して負荷率を求める。
                        La[dd] = (result_json["AHU"][ahu_name]["Qahu"]["heating_for_room"][dd] /
                                  result_json["AHU"][ahu_name]["Tahu"]["heating_for_room"][dd] * 1000 / 3600) / \
                                 input_data["air_handling_system"][ahu_name]["rated_capacity_heating"]

                    elif result_json["AHU"][ahu_name]["Tahu"]["heating_for_room"][dd] != 0:

                        # 空調負荷が正（冷却コイル負荷）である場合　→　定格冷却能力で除して負荷率を求める。
                        La[dd] = (result_json["AHU"][ahu_name]["Qahu"]["heating_for_room"][dd] /
                                  result_json["AHU"][ahu_name]["Tahu"]["heating_for_room"][dd] * 1000 / 3600) / \
                                 input_data["air_handling_system"][ahu_name]["rated_capacity_cooling"]

            # 定格能力＞０　→　空調機群に負荷を処理する機器があれば
            if (input_data["air_handling_system"][ahu_name]["rated_capacity_cooling"] > 0) or (
                    input_data["air_handling_system"][ahu_name]["rated_capacity_heating"] > 0):

                # 冷暖同時運転が「有」である場合（季節に依らず、冷却コイル負荷も加熱コイル負荷も処理する）
                if input_data["air_handling_system"][ahu_name]["is_simultaneous_supply"] == "有":

                    for dd in range(0, 365):

                        if np.isnan(La[dd]) == False:

                            if La[dd] > 0:  # 負荷率が正（冷却コイル負荷）である場合

                                # 負荷率帯インデックスの決定
                                iL = count_Matrix(La[dd], mxL)

                                if requirement_type == "cooling_for_room":  # 室負荷が正（冷房要求）である場合

                                    # 室負荷が正（冷房要求）であるときの冷却コイル負荷の負荷率帯インデックス
                                    result_json["AHU"][ahu_name]["LdAHUc"]["cooling_for_room"][dd] = iL
                                    # 室負荷が正（冷房要求）であるときの空調運転時間
                                    result_json["AHU"][ahu_name]["TdAHUc"]["cooling_for_room"][dd] = \
                                        result_json["AHU"][ahu_name]["Tahu"]["cooling_for_room"][dd]

                                elif requirement_type == "heating_for_room":  # 室負荷が負（暖房要求）である場合

                                    # 室負荷が負（暖房要求）であるときの冷却コイル負荷の負荷率帯インデックス
                                    result_json["AHU"][ahu_name]["LdAHUc"]["heating_for_room"][dd] = iL
                                    # 室負荷が負（暖房要求）であるときの空調運転時間
                                    result_json["AHU"][ahu_name]["TdAHUc"]["heating_for_room"][dd] = \
                                        result_json["AHU"][ahu_name]["Tahu"]["heating_for_room"][dd]

                            elif La[dd] < 0:  # 負荷率が負（加熱コイル負荷）である場合

                                # 負荷率帯インデックスの決定
                                iL = count_Matrix((-1) * La[dd], mxL)

                                if requirement_type == "cooling_for_room":  # 室負荷が正（冷房要求）である場合

                                    # 室負荷が正（冷房要求）であるときの加熱コイル負荷の負荷率帯インデックス
                                    result_json["AHU"][ahu_name]["LdAHUh"]["cooling_for_room"][dd] = iL
                                    # 室負荷が正（冷房要求）であるときの空調運転時間
                                    result_json["AHU"][ahu_name]["TdAHUh"]["cooling_for_room"][dd] = \
                                        result_json["AHU"][ahu_name]["Tahu"]["cooling_for_room"][dd]

                                elif requirement_type == "heating_for_room":  # 室負荷が負（暖房要求）である場合

                                    # 室負荷が負（暖房要求）であるときの加熱コイル負荷の負荷率帯インデックス
                                    result_json["AHU"][ahu_name]["LdAHUh"]["heating_for_room"][dd] = iL
                                    # 室負荷が負（暖房要求）であるときの空調運転時間
                                    result_json["AHU"][ahu_name]["TdAHUh"]["heating_for_room"][dd] = \
                                        result_json["AHU"][ahu_name]["Tahu"]["heating_for_room"][dd]

                                    # 冷暖同時供給が「無」である場合（季節により、冷却コイル負荷か加熱コイル負荷のどちらか一方を処理する）
                elif input_data["air_handling_system"][ahu_name]["is_simultaneous_supply"] == "無":

                    for dd in range(0, 365):

                        if np.isnan(La[dd]) == False:  # 日付dの負荷率が NaN で無い場合

                            # 冷房モード で動く期間の場合、かつ、空調負荷（冷却コイル負荷か加熱コイル負荷）が発生しているとき
                            if (La[dd] != 0) and (ac_mode[dd] == "冷房" or ac_mode[dd] == "中間"):

                                # 負荷率帯インデックスの決定
                                iL = count_Matrix(La[dd], mxL)

                                if requirement_type == "cooling_for_room":  # 室負荷が正（冷房要求）である場合

                                    # 室負荷が正（冷房要求）であるときの空調負荷の負荷率帯インデックス（ただし、加熱コイル負荷は 負荷率帯 0　となる）
                                    result_json["AHU"][ahu_name]["LdAHUc"]["cooling_for_room"][dd] = iL
                                    # 室負荷が正（冷房要求）であるときの空調運転時間(加熱コイル負荷発生時も 負荷率=0として送風機は動く想定)
                                    result_json["AHU"][ahu_name]["TdAHUc"]["cooling_for_room"][dd] = \
                                        result_json["AHU"][ahu_name]["Tahu"]["cooling_for_room"][dd]

                                elif requirement_type == "heating_for_room":  # 室負荷が負（暖房要求）である場合

                                    # 室負荷が負（暖房要求）であるときの空調負荷の負荷率帯インデックス（ただし、加熱コイル負荷は 負荷率帯 0　となる）
                                    result_json["AHU"][ahu_name]["LdAHUc"]["heating_for_room"][dd] = iL
                                    # 室負荷が負（暖房要求）であるときの空調運転時間(加熱コイル負荷発生時も 負荷率=0として送風機は動く想定)
                                    result_json["AHU"][ahu_name]["TdAHUc"]["heating_for_room"][dd] = \
                                        result_json["AHU"][ahu_name]["Tahu"]["heating_for_room"][dd]

                                    # 暖房モード で動く期間の場合、かつ、空調負荷（冷却コイル負荷か加熱コイル負荷）が発生しているとき
                            elif (La[dd] != 0) and (ac_mode[dd] == "暖房"):

                                # 負荷率帯インデックスの決定
                                iL = count_Matrix((-1) * La[dd], mxL)

                                if requirement_type == "cooling_for_room":  # 室負荷が正（冷房要求）である場合

                                    # 室負荷が正（冷房要求）であるときの空調負荷の負荷率帯インデックス（ただし、冷却コイル負荷は 負荷率帯 0　となる）
                                    result_json["AHU"][ahu_name]["LdAHUh"]["cooling_for_room"][dd] = iL
                                    # 室負荷が正（冷房要求）であるときの空調運転時間(冷却コイル負荷発生時も 負荷率=0として送風機は動く想定)
                                    result_json["AHU"][ahu_name]["TdAHUh"]["cooling_for_room"][dd] = \
                                        result_json["AHU"][ahu_name]["Tahu"]["cooling_for_room"][dd]

                                elif requirement_type == "heating_for_room":  # 室負荷が負（暖房要求）である場合

                                    # 室負荷が負（暖房要求）であるときの空調負荷の負荷率帯インデックス（ただし、冷却コイル負荷は 負荷率帯 0　となる）
                                    result_json["AHU"][ahu_name]["LdAHUh"]["heating_for_room"][dd] = iL
                                    # 室負荷が負（暖房要求）であるときの空調運転時間(冷却コイル負荷発生時も 負荷率=0として送風機は動く想定)
                                    result_json["AHU"][ahu_name]["TdAHUh"]["heating_for_room"][dd] = \
                                        result_json["AHU"][ahu_name]["Tahu"]["heating_for_room"][dd]

    if debug:  # pragma: no cover

        for ahu_name in input_data["air_handling_system"]:

            # マトリックスの再現
            matlix_AHUc_L = np.zeros(11)
            matlix_AHUh_L = np.zeros(11)
            for dd in range(0, 365):
                matlix_AHUc_L[int(result_json["AHU"][ahu_name]["LdAHUc"]["cooling_for_room"][dd] - 1)] += \
                    result_json["AHU"][ahu_name]["TdAHUc"]["cooling_for_room"][dd]
                matlix_AHUc_L[int(result_json["AHU"][ahu_name]["LdAHUc"]["heating_for_room"][dd] - 1)] += \
                    result_json["AHU"][ahu_name]["TdAHUc"]["heating_for_room"][dd]
                matlix_AHUh_L[int(result_json["AHU"][ahu_name]["LdAHUh"]["cooling_for_room"][dd] - 1)] += \
                    result_json["AHU"][ahu_name]["TdAHUh"]["cooling_for_room"][dd]
                matlix_AHUh_L[int(result_json["AHU"][ahu_name]["LdAHUh"]["heating_for_room"][dd] - 1)] += \
                    result_json["AHU"][ahu_name]["TdAHUh"]["heating_for_room"][dd]

            print("matlix_AHUc_L")
            print(matlix_AHUc_L)
            print(np.sum(matlix_AHUc_L))
            print("LAHUh")
            print(matlix_AHUh_L)
            print(np.sum(matlix_AHUh_L))

    ##----------------------------------------------------------------------------------
    ## 風量制御方式によって定まる係数（解説書 2.5.7）
    ##----------------------------------------------------------------------------------

    ## 搬送系制御に関する係数

    for ahu_name in input_data["air_handling_system"]:

        for unit_id, unit_configure in enumerate(input_data["air_handling_system"][ahu_name]["air_handling_unit"]):

            # 初期化
            input_data["air_handling_system"][ahu_name]["air_handling_unit"][unit_id]["energy_consumption_ratio"] = np.ones(
                len(aveL))

            # 係数の取得
            if unit_configure["fan_control_type"] in flow_control.keys():

                a4 = flow_control[unit_configure["fan_control_type"]]["a4"]
                a3 = flow_control[unit_configure["fan_control_type"]]["a3"]
                a2 = flow_control[unit_configure["fan_control_type"]]["a2"]
                a1 = flow_control[unit_configure["fan_control_type"]]["a1"]
                a0 = flow_control[unit_configure["fan_control_type"]]["a0"]

                if unit_configure["fan_min_opening_rate"] == None:
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

            # 負荷率帯毎のエネルギー消費量を算出
            for iL in range(0, len(aveL)):
                if aveL[iL] > 1:
                    input_data["air_handling_system"][ahu_name]["air_handling_unit"][unit_id]["energy_consumption_ratio"][
                        iL] = 1.2
                elif aveL[iL] == 0:
                    input_data["air_handling_system"][ahu_name]["air_handling_unit"][unit_id]["energy_consumption_ratio"][
                        iL] = 0
                elif aveL[iL] < Vmin:
                    input_data["air_handling_system"][ahu_name]["air_handling_unit"][unit_id]["energy_consumption_ratio"][
                        iL] = \
                        a4 * (Vmin) ** 4 + \
                        a3 * (Vmin) ** 3 + \
                        a2 * (Vmin) ** 2 + \
                        a1 * (Vmin) ** 1 + \
                        a0
                else:
                    input_data["air_handling_system"][ahu_name]["air_handling_unit"][unit_id]["energy_consumption_ratio"][
                        iL] = \
                        a4 * (aveL[iL]) ** 4 + \
                        a3 * (aveL[iL]) ** 3 + \
                        a2 * (aveL[iL]) ** 2 + \
                        a1 * (aveL[iL]) ** 1 + \
                        a0

    if debug:  # pragma: no cover

        for ahu_name in input_data["air_handling_system"]:
            print(f'--- 空調機群名 {ahu_name} ---')
            for unit_id, unit_configure in enumerate(input_data["air_handling_system"][ahu_name]["air_handling_unit"]):
                print(f'--- {unit_id + 1} 台目の送風機 ---')
                print(
                    f'負荷率帯毎のエネルギー消費量 energy_consumption_ratio {input_data["air_handling_system"][ahu_name]["air_handling_unit"][unit_id]["energy_consumption_ratio"]}')

    ##----------------------------------------------------------------------------------
    ## 送風機単体の定格消費電力（解説書 2.5.8）
    ##----------------------------------------------------------------------------------

    for ahu_name in input_data["air_handling_system"]:

        input_data["air_handling_system"][ahu_name]["fan_power_consumption_total"] = 0

        for unit_id, unit_configure in enumerate(input_data["air_handling_system"][ahu_name]["air_handling_unit"]):

            input_data["air_handling_system"][ahu_name]["air_handling_unit"][unit_id]["fan_power_consumption_total"] = 0

            if unit_configure["fan_power_consumption"] != None:
                # 送風機の定格消費電力 kW = 1台あたりの消費電力 kW × 台数
                input_data["air_handling_system"][ahu_name]["air_handling_unit"][unit_id]["fan_power_consumption_total"] = \
                    unit_configure["fan_power_consumption"] * unit_configure["number"]

                # 積算
                input_data["air_handling_system"][ahu_name]["fan_power_consumption_total"] += \
                    input_data["air_handling_system"][ahu_name]["air_handling_unit"][unit_id]["fan_power_consumption_total"]

            if debug:  # pragma: no cover
                print(f'--- 空調機群名 {ahu_name} ---')
                print(
                    f'送風機単体の定格消費電力: {input_data["air_handling_system"][ahu_name]["air_handling_unit"][unit_id]["fan_power_consumption_total"]}')

    ##----------------------------------------------------------------------------------
    ## 送風機の消費電力 （解説書 2.5.9）
    ##----------------------------------------------------------------------------------

    # 空調機群毎に、負荷率帯とエネルギー消費量[kW]の関係を算出
    for ahu_name in input_data["air_handling_system"]:

        for unit_id, unit_configure in enumerate(input_data["air_handling_system"][ahu_name]["air_handling_unit"]):

            for iL in range(0, len(aveL)):
                # 各負荷率帯における消費電力（制御の効果込み） [kW]
                result_json["AHU"][ahu_name]["energy_consumption_each_LF"][iL] += \
                    unit_configure["energy_consumption_ratio"][iL] * unit_configure["fan_power_consumption_total"]

            if debug:  # pragma: no cover
                print(f'--- 空調機群名 {ahu_name} ---')
                print(f'負荷率帯別の送風機消費電力: \n {result_json["AHU"][ahu_name]["energy_consumption_each_LF"]}')

    ##----------------------------------------------------------------------------------
    ## 全熱交換器の消費電力 （解説書 2.5.11）
    ##----------------------------------------------------------------------------------

    for ahu_name in input_data["air_handling_system"]:
        for dd in range(0, 365):

            # 冷房負荷or暖房負荷が発生していれば、全熱交換器は動いたとみなす。
            if (result_json["AHU"][ahu_name]["LdAHUc"]["cooling_for_room"][dd] > 0) or \
                    (result_json["AHU"][ahu_name]["LdAHUc"]["heating_for_room"][dd] > 0) or \
                    (result_json["AHU"][ahu_name]["LdAHUh"]["cooling_for_room"][dd] > 0) or \
                    (result_json["AHU"][ahu_name]["LdAHUh"]["heating_for_room"][dd] > 0):
                # 全熱交換器の消費電力量 MWh = 運転時間 h × 消費電力 kW
                result_json["AHU"][ahu_name]["E_AHUaex_day"][dd] += \
                    result_json["AHU"][ahu_name]["Tahu_total"][dd] * \
                    input_data["air_handling_system"][ahu_name]["air_heat_exchanger_power_consumption"] / 1000

    ##----------------------------------------------------------------------------------
    ## 空調機群の年間一次エネルギー消費量 （解説書 2.5.12）
    ##----------------------------------------------------------------------------------

    for ahu_name in input_data["air_handling_system"]:
        for dd in range(0, 365):

            ##-----------------------------------
            ## 室負荷が正（冷房要求）である場合：
            ##-----------------------------------
            if result_json["AHU"][ahu_name]["LdAHUc"]["cooling_for_room"][dd] > 0:  # 空調負荷が正（冷却コイル負荷）である場合

                # 負荷率帯番号
                iL = int(result_json["AHU"][ahu_name]["LdAHUc"]["cooling_for_room"][dd] - 1)

                # 空調負荷が正（冷却コイル負荷）の時の送風機等の消費電力　MWh
                result_json["AHU"][ahu_name]["E_fan_c_day"][dd] += \
                    result_json["AHU"][ahu_name]["energy_consumption_each_LF"][iL] / 1000 * \
                    result_json["AHU"][ahu_name]["TdAHUc"]["cooling_for_room"][dd]

                # 運転時間の合計 h
                result_json["AHU"][ahu_name]["TdAHUc_total"][dd] += \
                    result_json["AHU"][ahu_name]["TdAHUc"]["cooling_for_room"][dd]

            elif result_json["AHU"][ahu_name]["LdAHUh"]["cooling_for_room"][dd] > 0:  # 空調負荷が負（加熱コイル負荷）である場合

                # 負荷率帯番号
                iL = int(result_json["AHU"][ahu_name]["LdAHUh"]["cooling_for_room"][dd] - 1)

                # 空調負荷が負（加熱コイル負荷）の時の送風機等の消費電力　MWh
                result_json["AHU"][ahu_name]["E_fan_h_day"][dd] += \
                    result_json["AHU"][ahu_name]["energy_consumption_each_LF"][iL] / 1000 * \
                    result_json["AHU"][ahu_name]["TdAHUh"]["cooling_for_room"][dd]

                # 運転時間の合計 h
                result_json["AHU"][ahu_name]["TdAHUh_total"][dd] += \
                    result_json["AHU"][ahu_name]["TdAHUh"]["cooling_for_room"][dd]

            ##-----------------------------------
            ## 室負荷が負（暖房要求）である場合：
            ##-----------------------------------
            if result_json["AHU"][ahu_name]["LdAHUc"]["heating_for_room"][dd] > 0:  # 空調負荷が正（冷却コイル負荷）である場合

                # 負荷率帯番号
                iL = int(result_json["AHU"][ahu_name]["LdAHUc"]["heating_for_room"][dd] - 1)

                # 空調負荷が正（冷却コイル負荷）の時の送風機等の消費電力　MWh
                result_json["AHU"][ahu_name]["E_fan_c_day"][dd] += \
                    result_json["AHU"][ahu_name]["energy_consumption_each_LF"][iL] / 1000 * \
                    result_json["AHU"][ahu_name]["TdAHUc"]["heating_for_room"][dd]

                # 運転時間の合計 h
                result_json["AHU"][ahu_name]["TdAHUc_total"][dd] += \
                    result_json["AHU"][ahu_name]["TdAHUc"]["heating_for_room"][dd]


            elif result_json["AHU"][ahu_name]["LdAHUh"]["heating_for_room"][dd] > 0:  # 空調負荷が負（加熱コイル負荷）である場合

                # 負荷率帯番号
                iL = int(result_json["AHU"][ahu_name]["LdAHUh"]["heating_for_room"][dd] - 1)

                # 空調負荷が負（加熱コイル負荷）の時の送風機等の消費電力　MWh
                result_json["AHU"][ahu_name]["E_fan_h_day"][dd] += \
                    result_json["AHU"][ahu_name]["energy_consumption_each_LF"][iL] / 1000 * \
                    result_json["AHU"][ahu_name]["TdAHUh"]["heating_for_room"][dd]

                # 運転時間の合計 h
                result_json["AHU"][ahu_name]["TdAHUh_total"][dd] += \
                    result_json["AHU"][ahu_name]["TdAHUh"]["heating_for_room"][dd]

            ##------------------------
            # 空調負荷が正（冷却コイル負荷）のときと負（加熱コイル負荷）のときを合計する。
            ##------------------------            
            result_json["AHU"][ahu_name]["E_fan_day"][dd] = \
                result_json["AHU"][ahu_name]["E_fan_c_day"][dd] + result_json["AHU"][ahu_name]["E_fan_h_day"][dd]

    # 合計
    for ahu_name in input_data["air_handling_system"]:
        # 空調機群（送風機）のエネルギー消費量 MWh
        result_json["年間エネルギー消費量"]["空調機群ファン[MWh]"] += np.sum(result_json["AHU"][ahu_name]["E_fan_day"], 0)

        # 空調機群（全熱交換器）のエネルギー消費量 MWh
        result_json["年間エネルギー消費量"]["空調機群全熱交換器[MWh]"] += np.sum(result_json["AHU"][ahu_name]["E_AHUaex_day"],
                                                                           0)

        # 空調機群（送風機+全熱交換器）のエネルギー消費量 MWh/day
        result_json["日別エネルギー消費量"]["E_fan_MWh_day"] += \
            result_json["AHU"][ahu_name]["E_fan_day"] + result_json["AHU"][ahu_name]["E_AHUaex_day"]

        # ファン発熱量計算用
        result_json["AHU"][ahu_name]["TcAHU"] = np.sum(result_json["AHU"][ahu_name]["TdAHUc_total"], 0)
        result_json["AHU"][ahu_name]["ThAHU"] = np.sum(result_json["AHU"][ahu_name]["TdAHUh_total"], 0)
        result_json["AHU"][ahu_name]["MxAHUcE"] = np.sum(result_json["AHU"][ahu_name]["E_fan_c_day"], 0)
        result_json["AHU"][ahu_name]["MxAHUhE"] = np.sum(result_json["AHU"][ahu_name]["E_fan_h_day"], 0)

    result_json["年間エネルギー消費量"]["空調機群ファン[GJ]"] = result_json["年間エネルギー消費量"][
                                                           "空調機群ファン[MWh]"] * bc.fprime / 1000
    result_json["年間エネルギー消費量"]["空調機群全熱交換器[GJ]"] = result_json["年間エネルギー消費量"][
                                                                  "空調機群全熱交換器[MWh]"] * bc.fprime / 1000

    print('空調機群のエネルギー消費量計算完了')

    ##----------------------------------------------------------------------------------
    ## 空調機群計算結果の集約
    ##----------------------------------------------------------------------------------

    for ahu_name in input_data["air_handling_system"]:

        result_json["AHU"][ahu_name]["定格能力（冷房）[kW]"] = input_data["air_handling_system"][ahu_name][
            "rated_capacity_cooling"]
        result_json["AHU"][ahu_name]["定格能力（暖房）[kW]"] = input_data["air_handling_system"][ahu_name][
            "rated_capacity_heating"]
        result_json["AHU"][ahu_name]["定格消費電力[kW]"] = input_data["air_handling_system"][ahu_name][
            "fan_power_consumption_total"]

        cooling_load = 0
        heating_load = 0
        for dd in range(0, 365):

            if result_json["AHU"][ahu_name]["Qahu"]["cooling_for_room"][dd] >= 0:
                cooling_load += result_json["AHU"][ahu_name]["Qahu"]["cooling_for_room"][dd]
            else:
                heating_load += result_json["AHU"][ahu_name]["Qahu"]["cooling_for_room"][dd] * (-1)

            if result_json["AHU"][ahu_name]["Qahu"]["heating_for_room"][dd] >= 0:
                cooling_load += result_json["AHU"][ahu_name]["Qahu"]["heating_for_room"][dd]
            else:
                heating_load += result_json["AHU"][ahu_name]["Qahu"]["heating_for_room"][dd] * (-1)

        result_json["AHU"][ahu_name]["年間空調負荷（冷房）[MJ]"] = cooling_load
        result_json["AHU"][ahu_name]["年間空調負荷（暖房）[MJ]"] = heating_load

        result_json["AHU"][ahu_name]["年間空調時間（冷房）[時間]"] = \
            np.sum(result_json["AHU"][ahu_name]["TdAHUc"]["cooling_for_room"]) + np.sum(
                result_json["AHU"][ahu_name]["TdAHUc"]["heating_for_room"])
        result_json["AHU"][ahu_name]["年間空調時間（暖房）[時間]"] = \
            np.sum(result_json["AHU"][ahu_name]["TdAHUh"]["cooling_for_room"]) + np.sum(
                result_json["AHU"][ahu_name]["TdAHUh"]["heating_for_room"])

        if result_json["AHU"][ahu_name]["年間空調時間（冷房）[時間]"] != 0:
            result_json["AHU"][ahu_name]["平均空調負荷（冷房）[kW]"] = \
                result_json["AHU"][ahu_name]["年間空調負荷（冷房）[MJ]"] * 1000 \
                / (result_json["AHU"][ahu_name]["年間空調時間（冷房）[時間]"] * 3600)
        else:
            result_json["AHU"][ahu_name]["平均空調負荷（冷房）[kW]"] = 0

        if result_json["AHU"][ahu_name]["年間空調時間（暖房）[時間]"] != 0:
            result_json["AHU"][ahu_name]["平均空調負荷（暖房）[kW]"] = \
                result_json["AHU"][ahu_name]["年間空調負荷（暖房）[MJ]"] * 1000 \
                / (result_json["AHU"][ahu_name]["年間空調時間（暖房）[時間]"] * 3600)
        else:
            result_json["AHU"][ahu_name]["平均空調負荷（暖房）[kW]"] = 0

        if result_json["AHU"][ahu_name]["定格能力（冷房）[kW]"] != 0:
            result_json["AHU"][ahu_name]["平均負荷率（冷房）[-]"] = \
                result_json["AHU"][ahu_name]["平均空調負荷（冷房）[kW]"] / result_json["AHU"][ahu_name][
                    "定格能力（冷房）[kW]"]
        else:
            result_json["AHU"][ahu_name]["平均負荷率（冷房）[-]"] = 0

        if result_json["AHU"][ahu_name]["定格能力（暖房）[kW]"] != 0:
            result_json["AHU"][ahu_name]["平均負荷率（暖房）[-]"] = \
                result_json["AHU"][ahu_name]["平均空調負荷（暖房）[kW]"] / result_json["AHU"][ahu_name][
                    "定格能力（暖房）[kW]"]
        else:
            result_json["AHU"][ahu_name]["平均負荷率（暖房）[-]"] = 0

        result_json["AHU"][ahu_name]["電力消費量（送風機、冷房）[MWh]"] = np.sum(result_json["AHU"][ahu_name]["E_fan_c_day"])
        result_json["AHU"][ahu_name]["電力消費量（送風機、暖房）[MWh]"] = np.sum(result_json["AHU"][ahu_name]["E_fan_h_day"])
        result_json["AHU"][ahu_name]["電力消費量（全熱交換器）[MWh]"] = np.sum(result_json["AHU"][ahu_name]["E_AHUaex_day"])
        result_json["AHU"][ahu_name]["電力消費量（合計）[MWh]"] = \
            result_json["AHU"][ahu_name]["電力消費量（送風機、冷房）[MWh]"] \
            + result_json["AHU"][ahu_name]["電力消費量（送風機、暖房）[MWh]"] \
            + result_json["AHU"][ahu_name]["電力消費量（全熱交換器）[MWh]"]

    if debug:  # pragma: no cover

        for ahu_name in input_data["air_handling_system"]:
            print(f'--- 空調機群名 {ahu_name} ---')
            print(f'空調機群運転時間（冷房） TcAHU {np.sum(result_json["AHU"][ahu_name]["TcAHU"], 0)}')
            print(f'空調機群運転時間（暖房） ThAHU {np.sum(result_json["AHU"][ahu_name]["ThAHU"], 0)}')

            print(f'空調機群エネルギー消費量（冷房） MxAHUcE {np.sum(result_json["AHU"][ahu_name]["MxAHUcE"], 0)}')
            print(f'空調機群エネルギー消費量（暖房） MxAHUcE {np.sum(result_json["AHU"][ahu_name]["MxAHUhE"], 0)}')

        print(f'空調機群（送風機）のエネルギー消費量: {result_json["年間エネルギー消費量"]["空調機群ファン[MWh]"]} MWh')
        print(f'空調機群（全熱交換器）のエネルギー消費量: {result_json["年間エネルギー消費量"]["空調機群全熱交換器[MWh]"]} MWh')

    # 冷房と暖房の二次ポンプ群に分ける。
    for pump_original_name in input_data["secondary_pump_system"]:

        if "冷房" in input_data["secondary_pump_system"][pump_original_name]:
            # 二次ポンプ群名称を置き換え
            pump_name = pump_original_name + "_冷房"
            input_data["PUMP"][pump_name] = input_data["secondary_pump_system"][pump_original_name]["冷房"]
            input_data["PUMP"][pump_name]["mode"] = "cooling"

        if "暖房" in input_data["secondary_pump_system"][pump_original_name]:
            # 二次ポンプ群名称を置き換え
            pump_name = pump_original_name + "_暖房"
            input_data["PUMP"][pump_name] = input_data["secondary_pump_system"][pump_original_name]["暖房"]
            input_data["PUMP"][pump_name]["mode"] = "heating"

    for pump_name in input_data["PUMP"]:
        result_json["PUMP"][pump_name] = {}
        result_json["PUMP"][pump_name]["Qpsahu_fan"] = np.zeros(365)  # ファン発熱量 [MJ/day]
        result_json["PUMP"][pump_name]["pumpTime_Start"] = np.zeros(365)
        result_json["PUMP"][pump_name]["pumpTime_Stop"] = np.zeros(365)
        result_json["PUMP"][pump_name]["Qps"] = np.zeros(365)  # ポンプ負荷 [MJ/day]
        result_json["PUMP"][pump_name]["Tps"] = np.zeros(365)  # ポンプ運転時間 [時間/day]
        result_json["PUMP"][pump_name]["schedule"] = np.zeros((365, 24))  # ポンプ時刻別運転スケジュール
        result_json["PUMP"][pump_name]["LdPUMP"] = np.zeros(365)  # 負荷率帯
        result_json["PUMP"][pump_name]["TdPUMP"] = np.zeros(365)  # 運転時間
        result_json["PUMP"][pump_name]["Qpsahu_pump"] = np.zeros(365)  # ポンプの発熱量 [MJ/day]
        result_json["PUMP"][pump_name]["E_pump_day"] = np.zeros(365)  # 二次ポンプ群の電力消費量（消費電力×運転時間）[MWh]
        result_json["PUMP"][pump_name]["TcPUMP"] = 0
        result_json["PUMP"][pump_name]["MxPUMPE"] = 0

    ##----------------------------------------------------------------------------------
    ## 二次ポンプ機群全体のスペックを整理する。
    ##----------------------------------------------------------------------------------

    for pump_name in input_data["PUMP"]:

        input_data["PUMP"][pump_name]["ahu_list"] = set()  # 接続される空調機群
        input_data["PUMP"][pump_name]["Qpsr"] = 0  # ポンプ定格能力
        input_data["PUMP"][pump_name]["Vpsr"] = 0  # ポンプ定格流量 [m3/h]
        input_data["PUMP"][pump_name]["control_type"] = set()  # 全台回転数制御かどうか（台数制御がない場合のみ有効）
        input_data["PUMP"][pump_name]["min_opening_rate"] = 100  # 変流量時最小負荷率の最小値（台数制御がない場合のみ有効）

        # ポンプの台数
        input_data["PUMP"][pump_name]["number_of_pumps"] = len(input_data["PUMP"][pump_name]["secondary_pump"])

        # 二次ポンプの能力のリスト
        input_data["PUMP"][pump_name]["Qpsr_list"] = []

        # 二次ポンプ群全体の定格消費電力の合計
        input_data["PUMP"][pump_name]["rated_power_consumption_total"] = 0

        for unit_id, unit_configure in enumerate(input_data["PUMP"][pump_name]["secondary_pump"]):

            # 流量の合計（台数×流量）
            input_data["PUMP"][pump_name]["secondary_pump"][unit_id]["rated_water_flow_rate_total"] = \
                input_data["PUMP"][pump_name]["secondary_pump"][unit_id]["rated_water_flow_rate"] * \
                input_data["PUMP"][pump_name]["secondary_pump"][unit_id]["number"]

            input_data["PUMP"][pump_name]["Vpsr"] += input_data["PUMP"][pump_name]["secondary_pump"][unit_id][
                "rated_water_flow_rate_total"]

            # 消費電力の合計（消費電力×流量）
            input_data["PUMP"][pump_name]["secondary_pump"][unit_id]["rated_power_consumption_total"] = \
                input_data["PUMP"][pump_name]["secondary_pump"][unit_id]["rated_power_consumption"] * \
                input_data["PUMP"][pump_name]["secondary_pump"][unit_id]["number"]

            # 二次ポンプ群全体の定格消費電力の合計
            input_data["PUMP"][pump_name]["rated_power_consumption_total"] += \
                input_data["PUMP"][pump_name]["secondary_pump"][unit_id]["rated_power_consumption_total"]

            # 制御方式
            input_data["PUMP"][pump_name]["control_type"].add(
                input_data["PUMP"][pump_name]["secondary_pump"][unit_id]["control_type"])

            # 変流量時最小負荷率の最小値（台数制御がない場合のみ有効）
            if unit_configure["min_opening_rate"] == None or np.isnan(unit_configure["min_opening_rate"]) == True:
                input_data["PUMP"][pump_name]["min_opening_rate"] = 100
            elif input_data["PUMP"][pump_name]["min_opening_rate"] > unit_configure["min_opening_rate"]:
                input_data["PUMP"][pump_name]["min_opening_rate"] = unit_configure["min_opening_rate"]

        # 全台回転数制御かどうか（台数制御がない場合のみ有効）
        if "無" in input_data["PUMP"][pump_name]["control_type"]:
            input_data["PUMP"][pump_name]["control_type"] = "定流量制御がある"
        elif "定流量制御" in input_data["PUMP"][pump_name]["control_type"]:
            input_data["PUMP"][pump_name]["control_type"] = "定流量制御がある"
        else:
            input_data["PUMP"][pump_name]["control_type"] = "すべて変流量制御である"

    # 接続される空調機群
    # for room_zone_name in input_data["air_conditioning_zone"]:

    #     # 冷房（室内負荷処理用空調機）
    #     input_data["PUMP"][ input_data["air_conditioning_zone"][room_zone_name]["pump_cooling"] + "_冷房" ]["ahu_list"].add( \
    #         input_data["air_conditioning_zone"][room_zone_name]["ahu_cooling_inside_load"])
    #     # 冷房（外気負荷処理用空調機）
    #     input_data["PUMP"][ input_data["air_conditioning_zone"][room_zone_name]["pump_cooling"] + "_冷房" ]["ahu_list"].add( \
    #         input_data["air_conditioning_zone"][room_zone_name]["ahu_cooling_outdoor_load"])

    #     # 暖房（室内負荷処理用空調機）
    #     input_data["PUMP"][ input_data["air_conditioning_zone"][room_zone_name]["pump_heating"] + "_暖房" ]["ahu_list"].add( \
    #         input_data["air_conditioning_zone"][room_zone_name]["ahu_heating_inside_load"])
    #     # 暖房（外気負荷処理用空調機）
    #     input_data["PUMP"][ input_data["air_conditioning_zone"][room_zone_name]["pump_heating"] + "_暖房" ]["ahu_list"].add( \
    #         input_data["air_conditioning_zone"][room_zone_name]["ahu_heating_outdoor_load"])

    for ahu_name in input_data["air_handling_system"]:
        input_data["PUMP"][input_data["air_handling_system"][ahu_name]["pump_cooling"] + "_冷房"]["ahu_list"].add(ahu_name)
        input_data["PUMP"][input_data["air_handling_system"][ahu_name]["pump_heating"] + "_暖房"]["ahu_list"].add(ahu_name)

    ##----------------------------------------------------------------------------------
    ## 二次ポンプ負荷（解説書 2.6.1）
    ##----------------------------------------------------------------------------------

    # 未処理負荷の算出
    for ahu_name in input_data["air_handling_system"]:

        for dd in range(0, 365):

            if ac_mode[dd] == "暖房":  ## 暖房期である場合

                # 室負荷が冷房要求である場合において空調負荷が正の値である場合、かつ、冷暖同時供給が無い場合
                if (result_json["AHU"][ahu_name]["Qahu"]["cooling_for_room"][dd] > 0) and \
                        (input_data["air_handling_system"][ahu_name]["is_simultaneous_supply_heating"] == "無"):
                    result_json["AHU"][ahu_name]["Qahu_remainC"][dd] += (
                        result_json["AHU"][ahu_name]["Qahu"]["cooling_for_room"][dd])
                    result_json["AHU"][ahu_name]["Qahu"]["cooling_for_room"][dd] = 0

                # 室負荷が暖房要求である場合において空調負荷が正の値である場合、かつ、冷暖同時供給が無い場合
                if (result_json["AHU"][ahu_name]["Qahu"]["heating_for_room"][dd] > 0) and \
                        (input_data["air_handling_system"][ahu_name]["is_simultaneous_supply_heating"] == "無"):
                    result_json["AHU"][ahu_name]["Qahu_remainC"][dd] += (
                        result_json["AHU"][ahu_name]["Qahu"]["heating_for_room"][dd])
                    result_json["AHU"][ahu_name]["Qahu"]["heating_for_room"][dd] = 0

            elif (ac_mode[dd] == "冷房") or (ac_mode[dd] == "中間"):

                # 室負荷が冷房要求である場合において空調負荷が負の値である場合、かつ、冷暖同時供給が無い場合
                if (result_json["AHU"][ahu_name]["Qahu"]["cooling_for_room"][dd] < 0) and \
                        (input_data["air_handling_system"][ahu_name]["is_simultaneous_supply_cooling"] == "無"):
                    result_json["AHU"][ahu_name]["Qahu_remainH"][dd] += (-1) * (
                        result_json["AHU"][ahu_name]["Qahu"]["cooling_for_room"][dd])
                    result_json["AHU"][ahu_name]["Qahu"]["cooling_for_room"][dd] = 0

                # 室負荷が暖房要求である場合において空調負荷が負の値である場合、かつ、冷暖同時供給が無い場合
                if (result_json["AHU"][ahu_name]["Qahu"]["heating_for_room"][dd] < 0) and \
                        (input_data["air_handling_system"][ahu_name]["is_simultaneous_supply_cooling"] == "無"):
                    result_json["AHU"][ahu_name]["Qahu_remainH"][dd] += (-1) * (
                        result_json["AHU"][ahu_name]["Qahu"]["heating_for_room"][dd])
                    result_json["AHU"][ahu_name]["Qahu"]["heating_for_room"][dd] = 0

    # ポンプ負荷の積算
    for pump_name in input_data["PUMP"]:

        for ahu_name in input_data["PUMP"][pump_name]["ahu_list"]:

            for dd in range(0, 365):

                if input_data["PUMP"][pump_name]["mode"] == "cooling":  # 冷水ポンプの場合

                    # ファン発熱量 Qpsahu_fan [MJ/day] の算出（解説書 2.5.10）
                    tmpC = 0
                    tmpH = 0

                    if input_data["air_handling_system"][ahu_name]["ahu_type"] == "空調機":

                        # 室負荷が冷房要求である場合において空調負荷が正である場合
                        if result_json["AHU"][ahu_name]["Qahu"]["cooling_for_room"][dd] > 0:
                            tmpC = k_heatup * result_json["AHU"][ahu_name]["MxAHUcE"] * \
                                   result_json["AHU"][ahu_name]["Tahu"]["cooling_for_room"][dd] / \
                                   result_json["AHU"][ahu_name]["TcAHU"] * 3600

                        # 室負荷が暖房要求である場合において空調負荷が正である場合
                        if result_json["AHU"][ahu_name]["Qahu"]["heating_for_room"][dd] > 0:
                            tmpH = k_heatup * result_json["AHU"][ahu_name]["MxAHUhE"] * \
                                   result_json["AHU"][ahu_name]["Tahu"]["heating_for_room"][dd] / \
                                   result_json["AHU"][ahu_name]["ThAHU"] * 3600

                    result_json["PUMP"][pump_name]["Qpsahu_fan"][dd] = tmpC + tmpH

                    ## 日積算ポンプ負荷 Qps [MJ/day] の算出
                    # 室負荷が冷房要求である場合において空調負荷が正である場合
                    if result_json["AHU"][ahu_name]["Qahu"]["cooling_for_room"][dd] > 0:
                        if result_json["AHU"][ahu_name]["Economizer"]["Qahu_oac"][
                            dd] > 0:  # 外冷時はファン発熱量足さない ⇒ 小さな負荷が出てしまう
                            if abs(result_json["AHU"][ahu_name]["Qahu"]["cooling_for_room"][dd] -
                                   result_json["AHU"][ahu_name]["Economizer"]["Qahu_oac"][dd]) < 1:
                                result_json["PUMP"][pump_name]["Qps"][dd] += 0
                            else:
                                result_json["PUMP"][pump_name]["Qps"][dd] += \
                                    result_json["AHU"][ahu_name]["Qahu"]["cooling_for_room"][dd] - \
                                    result_json["AHU"][ahu_name]["Economizer"]["Qahu_oac"][dd]
                        else:
                            result_json["PUMP"][pump_name]["Qps"][dd] += \
                                result_json["AHU"][ahu_name]["Qahu"]["cooling_for_room"][dd] - \
                                result_json["AHU"][ahu_name]["Economizer"]["Qahu_oac"][dd] + \
                                result_json["PUMP"][pump_name]["Qpsahu_fan"][dd]

                    # 室負荷が暖房要求である場合において空調負荷が正である場合
                    if result_json["AHU"][ahu_name]["Qahu"]["heating_for_room"][dd] > 0:
                        result_json["PUMP"][pump_name]["Qps"][dd] += \
                            result_json["AHU"][ahu_name]["Qahu"]["heating_for_room"][dd] - \
                            result_json["AHU"][ahu_name]["Economizer"]["Qahu_oac"][dd] + \
                            result_json["PUMP"][pump_name]["Qpsahu_fan"][dd]


                elif input_data["PUMP"][pump_name]["mode"] == "heating":

                    # ファン発熱量 Qpsahu_fan [MJ/day] の算出
                    tmpC = 0
                    tmpH = 0

                    if input_data["air_handling_system"][ahu_name]["ahu_type"] == "空調機":

                        # 室負荷が冷房要求である場合の空調負荷が負である場合
                        if result_json["AHU"][ahu_name]["Qahu"]["cooling_for_room"][dd] < 0:
                            tmpC = k_heatup * result_json["AHU"][ahu_name]["MxAHUcE"] * \
                                   result_json["AHU"][ahu_name]["Tahu"]["cooling_for_room"][dd] / \
                                   result_json["AHU"][ahu_name]["TcAHU"] * 3600

                        # 室負荷が暖房要求である場合の空調負荷が負である場合
                        if result_json["AHU"][ahu_name]["Qahu"]["heating_for_room"][dd] < 0:
                            tmpH = k_heatup * result_json["AHU"][ahu_name]["MxAHUhE"] * \
                                   result_json["AHU"][ahu_name]["Tahu"]["heating_for_room"][dd] / \
                                   result_json["AHU"][ahu_name]["ThAHU"] * 3600

                    result_json["PUMP"][pump_name]["Qpsahu_fan"][dd] = tmpC + tmpH

                    ## 日積算ポンプ負荷 Qps [MJ/day] の算出<符号逆転させる>
                    # 室負荷が冷房要求である場合において空調負荷が正である場合
                    if result_json["AHU"][ahu_name]["Qahu"]["cooling_for_room"][dd] < 0:
                        result_json["PUMP"][pump_name]["Qps"][dd] += \
                            (-1) * (result_json["AHU"][ahu_name]["Qahu"]["cooling_for_room"][dd] +
                                    result_json["PUMP"][pump_name]["Qpsahu_fan"][dd])

                    # 室負荷が暖房要求である場合において空調負荷が正である場合
                    if result_json["AHU"][ahu_name]["Qahu"]["heating_for_room"][dd] < 0:
                        result_json["PUMP"][pump_name]["Qps"][dd] += \
                            (-1) * (result_json["AHU"][ahu_name]["Qahu"]["heating_for_room"][dd] +
                                    result_json["PUMP"][pump_name]["Qpsahu_fan"][dd])

    ##----------------------------------------------------------------------------------
    ## 二次ポンプ群の運転時間（解説書 2.6.2）
    ##----------------------------------------------------------------------------------

    for pump_name in input_data["PUMP"]:

        for ahu_name in input_data["PUMP"][pump_name]["ahu_list"]:
            result_json["PUMP"][pump_name]["schedule"] += result_json["AHU"][ahu_name]["schedule"]

        # 運転スケジュールの和が「1以上（接続されている空調機群の1つは動いている）」であれば、二次ポンプは稼働しているとする。
        result_json["PUMP"][pump_name]["schedule"][result_json["PUMP"][pump_name]["schedule"] > 1] = 1

        # 日積算運転時間
        result_json["PUMP"][pump_name]["Tps"] = np.sum(result_json["PUMP"][pump_name]["schedule"], 1)

    print('ポンプ負荷計算完了')

    if debug:  # pragma: no cover

        for ahu_name in input_data["air_handling_system"]:
            print(f'--- 空調機群名 {ahu_name} ---')

            print(f'未処理負荷（冷房）: {np.sum(result_json["AHU"][ahu_name]["Qahu_remainC"])} MJ')
            print(f'未処理負荷（暖房）: {np.sum(result_json["AHU"][ahu_name]["Qahu_remainH"])} MJ')

        for pump_name in input_data["PUMP"]:
            print(f'--- 二次ポンプ群名 {pump_name} ---')

            print(f'二次ポンプ負荷 Qps: {np.sum(result_json["PUMP"][pump_name]["Qps"], 0)}')
            print(f'二次ポンプ運転時間 Tps: {np.sum(result_json["PUMP"][pump_name]["Tps"], 0)}')

    ##----------------------------------------------------------------------------------
    ## 二次ポンプ群の仮想定格能力（解説書 2.6.3）
    ##----------------------------------------------------------------------------------
    for pump_name in input_data["PUMP"]:

        for unit_id, unit_configure in enumerate(input_data["PUMP"][pump_name]["secondary_pump"]):
            # 二次ポンプの定格処理能力[kW] = [K] * [m3/h] * [kJ/kg・K] * [kg/m3] * [h/s]
            input_data["PUMP"][pump_name]["secondary_pump"][unit_id]["Qpsr"] = \
                input_data["PUMP"][pump_name]["temperature_difference"] * unit_configure[
                    "rated_water_flow_rate_total"] * 4.1860 * 1000 / 3600

            input_data["PUMP"][pump_name]["Qpsr"] += input_data["PUMP"][pump_name]["secondary_pump"][unit_id]["Qpsr"]
            input_data["PUMP"][pump_name]["Qpsr_list"].append(
                input_data["PUMP"][pump_name]["secondary_pump"][unit_id]["Qpsr"])

    ##----------------------------------------------------------------------------------
    ## 二次ポンプ群の負荷率（解説書 2.6.4）
    ##----------------------------------------------------------------------------------

    for pump_name in input_data["PUMP"]:

        Lpump = np.zeros(365)
        Mxc = np.zeros(365)  # ポンプの負荷率区分
        Tdc = np.zeros(365)  # ポンプの運転時間

        if input_data["PUMP"][pump_name]["Qpsr"] != 0:  # 仮想ポンプ（二次ポンプがないシステム用の仮想ポンプ）は除く

            for dd in range(0, 365):

                if result_json["PUMP"][pump_name]["Tps"][dd] > 0:
                    # 負荷率 Lpump[-] = [MJ/day] / [h/day] * [kJ/MJ] / [s/h] / [KJ/s]
                    Lpump[dd] = (result_json["PUMP"][pump_name]["Qps"][dd] / result_json["PUMP"][pump_name]["Tps"][
                        dd] * 1000 / 3600) \
                                / input_data["PUMP"][pump_name]["Qpsr"]

            for dd in range(0, 365):

                if (result_json["PUMP"][pump_name]["Tps"][dd] > 0) and (
                        input_data["PUMP"][pump_name]["Qpsr"] > 0):  # ゼロ割でNaNになっている値を飛ばす

                    if Lpump[dd] > 0:
                        # 出現時間マトリックスを作成
                        iL = count_Matrix(Lpump[dd], mxL)

                        Mxc[dd] = iL
                        Tdc[dd] = result_json["PUMP"][pump_name]["Tps"][dd]

        result_json["PUMP"][pump_name]["LdPUMP"] = Mxc
        result_json["PUMP"][pump_name]["TdPUMP"] = Tdc

    ##----------------------------------------------------------------------------------
    ## 流量制御方式によって定まる係数（解説書 2.6.7）
    ##----------------------------------------------------------------------------------

    for pump_name in input_data["PUMP"]:

        result_json["PUMP"][pump_name]["変流量制御の有無"] = "無"

        for unit_id, unit_configure in enumerate(input_data["PUMP"][pump_name]["secondary_pump"]):

            if unit_configure["control_type"] in flow_control.keys():

                input_data["PUMP"][pump_name]["secondary_pump"][unit_id]["a4"] = \
                    flow_control[unit_configure["control_type"]]["a4"]
                input_data["PUMP"][pump_name]["secondary_pump"][unit_id]["a3"] = \
                    flow_control[unit_configure["control_type"]]["a3"]
                input_data["PUMP"][pump_name]["secondary_pump"][unit_id]["a2"] = \
                    flow_control[unit_configure["control_type"]]["a2"]
                input_data["PUMP"][pump_name]["secondary_pump"][unit_id]["a1"] = \
                    flow_control[unit_configure["control_type"]]["a1"]
                input_data["PUMP"][pump_name]["secondary_pump"][unit_id]["a0"] = \
                    flow_control[unit_configure["control_type"]]["a0"]

                result_json["PUMP"][pump_name]["変流量制御の有無"] = "有"

            elif unit_configure["control_type"] == "無":

                input_data["PUMP"][pump_name]["secondary_pump"][unit_id]["a4"] = 0
                input_data["PUMP"][pump_name]["secondary_pump"][unit_id]["a3"] = 0
                input_data["PUMP"][pump_name]["secondary_pump"][unit_id]["a2"] = 0
                input_data["PUMP"][pump_name]["secondary_pump"][unit_id]["a1"] = 0
                input_data["PUMP"][pump_name]["secondary_pump"][unit_id]["a0"] = 1
                input_data["PUMP"][pump_name]["secondary_pump"][unit_id]["min_opening_rate"] = 100

            else:
                raise Exception('制御方式が不正です')

    ##----------------------------------------------------------------------------------
    ## 二次ポンプのエネルギー消費量（解説書 2.6.8）
    ##----------------------------------------------------------------------------------

    for pump_name in input_data["PUMP"]:

        MxPUMPNum = np.zeros(divL)
        MxPUMPPower = np.zeros(divL)
        PUMPvwvfac = np.ones(divL)

        if input_data["PUMP"][pump_name]["Qpsr"] != 0:  # 仮想ポンプ（二次ポンプがないシステム用の仮想ポンプ）は除く

            if input_data["PUMP"][pump_name]["is_staging_control"] == "無":  # 台数制御なし

                # 運転台数
                MxPUMPNum = np.ones(divL) * input_data["PUMP"][pump_name]["number_of_pumps"]

                # 流量制御方式
                if input_data["PUMP"][pump_name]["control_type"] == "すべて変流量制御である":  # 全台VWVであれば

                    for iL in range(0, divL):

                        # 最小負荷率による下限を設ける。
                        if aveL[iL] < (input_data["PUMP"][pump_name]["min_opening_rate"] / 100):
                            tmpL = input_data["PUMP"][pump_name]["min_opening_rate"] / 100
                        else:
                            tmpL = aveL[iL]

                        # VWVの効果率曲線(1番目の特性を代表して使う)
                        PUMPvwvfac = np.ones(divL)
                        if aveL[iL] > 1.0:
                            PUMPvwvfac[iL] = 1.2
                        else:
                            PUMPvwvfac[iL] = \
                                input_data["PUMP"][pump_name]["secondary_pump"][0]["a4"] * tmpL ** 4 + \
                                input_data["PUMP"][pump_name]["secondary_pump"][0]["a3"] * tmpL ** 3 + \
                                input_data["PUMP"][pump_name]["secondary_pump"][0]["a2"] * tmpL ** 2 + \
                                input_data["PUMP"][pump_name]["secondary_pump"][0]["a1"] * tmpL + \
                                input_data["PUMP"][pump_name]["secondary_pump"][0]["a0"]

                else:  # 全台VWVでなければ、定流量とみなす。
                    PUMPvwvfac = np.ones(divL)
                    PUMPvwvfac[divL] = 1.2

                # 消費電力（部分負荷特性×定格消費電力）[kW]
                MxPUMPPower = PUMPvwvfac * input_data["PUMP"][pump_name]["rated_power_consumption_total"]


            elif input_data["PUMP"][pump_name]["is_staging_control"] == "有":  # 台数制御あり

                for iL in range(0, divL):

                    # 負荷区分 iL における処理負荷 [kW]
                    Qpsr_iL = input_data["PUMP"][pump_name]["Qpsr"] * aveL[iL]

                    # 運転台数 MxPUMPNum
                    for rr in range(0, input_data["PUMP"][pump_name]["number_of_pumps"]):

                        # 1台～rr台までの最大能力合計値
                        tmpQmax = np.sum(input_data["PUMP"][pump_name]["Qpsr_list"][0:rr + 1])

                        if Qpsr_iL < tmpQmax:
                            break

                    MxPUMPNum[iL] = rr + 1  # pythonのインデックスと実台数は「1」ずれることに注意。

                    # 定流量ポンプの処理熱量合計、VWVポンプの台数
                    Qtmp_CWV = 0
                    numVWV = MxPUMPNum[iL]  # MxPUMPNum[iL]は、負荷率帯 iL のときの運転台数（定流量＋変流量）

                    for rr in range(0, int(MxPUMPNum[iL])):

                        if (input_data["PUMP"][pump_name]["secondary_pump"][rr]["control_type"] == "無") or \
                                (input_data["PUMP"][pump_name]["secondary_pump"][rr]["control_type"] == "定流量制御"):
                            Qtmp_CWV += input_data["PUMP"][pump_name]["secondary_pump"][rr]["Qpsr"]
                            numVWV = numVWV - 1

                    # 制御を加味した消費エネルギー MxPUMPPower [kW]
                    for rr in range(0, int(MxPUMPNum[iL])):

                        if (input_data["PUMP"][pump_name]["secondary_pump"][rr]["control_type"] == "無") or \
                                (input_data["PUMP"][pump_name]["secondary_pump"][rr]["control_type"] == "定流量制御"):

                            # 変流量制御の効果率
                            PUMPvwvfac = np.ones(divL)
                            if aveL[iL] > 1.0:
                                PUMPvwvfac[iL] = 1.2

                            if aveL[iL] > 1.0:
                                MxPUMPPower[iL] += input_data["PUMP"][pump_name]["secondary_pump"][rr][
                                                       "rated_power_consumption_total"] * PUMPvwvfac[iL]
                            else:
                                MxPUMPPower[iL] += input_data["PUMP"][pump_name]["secondary_pump"][rr][
                                                       "rated_power_consumption_total"] * PUMPvwvfac[iL]


                        else:

                            # 変流量ポンプjの負荷率 [-]
                            tmpL = ((Qpsr_iL - Qtmp_CWV) / numVWV) / input_data["PUMP"][pump_name]["secondary_pump"][rr][
                                "Qpsr"]

                            # 最小流量の制限
                            if tmpL < input_data["PUMP"][pump_name]["secondary_pump"][rr]["min_opening_rate"] / 100:
                                tmpL = input_data["PUMP"][pump_name]["secondary_pump"][rr]["min_opening_rate"] / 100

                            # 変流量制御による省エネ効果
                            PUMPvwvfac = np.ones(divL)
                            if aveL[iL] > 1.0:
                                PUMPvwvfac[iL] = 1.2
                            else:
                                PUMPvwvfac[iL] = \
                                    input_data["PUMP"][pump_name]["secondary_pump"][rr]["a4"] * tmpL ** 4 + \
                                    input_data["PUMP"][pump_name]["secondary_pump"][rr]["a3"] * tmpL ** 3 + \
                                    input_data["PUMP"][pump_name]["secondary_pump"][rr]["a2"] * tmpL ** 2 + \
                                    input_data["PUMP"][pump_name]["secondary_pump"][rr]["a1"] * tmpL + \
                                    input_data["PUMP"][pump_name]["secondary_pump"][rr]["a0"]

                            MxPUMPPower[iL] += input_data["PUMP"][pump_name]["secondary_pump"][rr][
                                                   "rated_power_consumption_total"] * PUMPvwvfac[iL]

        result_json["PUMP"][pump_name]["MxPUMPNum"] = MxPUMPNum
        result_json["PUMP"][pump_name]["MxPUMPPower"] = MxPUMPPower

    ##----------------------------------------------------------------------------------
    ## 二次ポンプ群ごとの消費電力（解説書 2.6.8）
    ##----------------------------------------------------------------------------------

    for pump_name in input_data["PUMP"]:

        for dd in range(0, 365):

            if result_json["PUMP"][pump_name]["TdPUMP"][dd] > 0:
                result_json["PUMP"][pump_name]["E_pump_day"][dd] = \
                    result_json["PUMP"][pump_name]["MxPUMPPower"][
                        int(result_json["PUMP"][pump_name]["LdPUMP"][dd]) - 1] / 1000 * \
                    result_json["PUMP"][pump_name]["TdPUMP"][dd]

    ##----------------------------------------------------------------------------------
    ## 二次ポンプ群全体の年間一次エネルギー消費量（解説書 2.6.10）
    ##----------------------------------------------------------------------------------

    for pump_name in input_data["PUMP"]:
        result_json["年間エネルギー消費量"]["二次ポンプ群[MWh]"] += np.sum(result_json["PUMP"][pump_name]["E_pump_day"], 0)

        result_json["日別エネルギー消費量"]["E_pump_MWh_day"] += result_json["PUMP"][pump_name]["E_pump_day"]

        result_json["PUMP"][pump_name]["TcPUMP"] = np.sum(result_json["PUMP"][pump_name]["TdPUMP"], 0)
        result_json["PUMP"][pump_name]["MxPUMPE"] = np.sum(result_json["PUMP"][pump_name]["E_pump_day"], 0)

    result_json["年間エネルギー消費量"]["二次ポンプ群[GJ]"] = result_json["年間エネルギー消費量"]["二次ポンプ群[MWh]"] * bc.fprime / 1000

    print('二次ポンプ群のエネルギー消費量計算完了')

    if debug:  # pragma: no cover

        for ahu_name in input_data["air_handling_system"]:
            print(f'--- 空調機群名 {ahu_name} ---')

            print(f'未処理負荷（冷房）: {np.sum(result_json["AHU"][ahu_name]["Qahu_remainC"])} MJ')
            print(f'未処理負荷（暖房）: {np.sum(result_json["AHU"][ahu_name]["Qahu_remainH"])} MJ')

        for pump_name in input_data["PUMP"]:
            print(f'--- 二次ポンプ群名 {pump_name} ---')

            print(f'二次ポンプ群に加算されるファン発熱量 Qpsahu_fan: {np.sum(result_json["PUMP"][pump_name]["Qpsahu_fan"], 0)}')
            print(f'二次ポンプ群の負荷 Qps: {np.sum(result_json["PUMP"][pump_name]["Qps"], 0)}')
            print(f'二次ポンプ群の運転時間 Tps: {np.sum(result_json["PUMP"][pump_name]["Tps"], 0)}')
            print(f'二次ポンプ群の電力消費量 E_pump_day: {np.sum(result_json["PUMP"][pump_name]["E_pump_day"], 0)}')

        print(f'二次ポンプ群のエネルギー消費量 E_pump: {result_json["年間エネルギー消費量"]["二次ポンプ群[MWh]"]} MWh')

    ##----------------------------------------------------------------------------------
    ## 二次ポンプ群の発熱量 （解説書 2.6.9）
    ##----------------------------------------------------------------------------------

    for pump_name in input_data["PUMP"]:

        if result_json["PUMP"][pump_name]["TcPUMP"] > 0:

            for dd in range(0, 365):
                # 二次ポンプ群の発熱量 MJ/day
                result_json["PUMP"][pump_name]["Qpsahu_pump"][dd] = \
                    result_json["PUMP"][pump_name]["MxPUMPE"] * k_heatup / result_json["PUMP"][pump_name]["TcPUMP"] \
                    * result_json["PUMP"][pump_name]["Tps"][dd] * 3600

        if debug:  # pragma: no cover
            print(f'--- 二次ポンプ群名 {pump_name} ---')
            print(f'二次ポンプ群のポンプ発熱量 Qpsahu_fan: {np.sum(result_json["PUMP"][pump_name]["Qpsahu_pump"], 0)}')

    ##----------------------------------------------------------------------------------
    ## 二次ポンプ群計算結果の集約
    ##----------------------------------------------------------------------------------

    for pump_name in input_data["PUMP"]:

        if pump_name.startswith("dummyPump") == False:

            if input_data["PUMP"][pump_name]["mode"] == "cooling":
                result_json["PUMP"][pump_name]["運転モード"] = "冷房"
            elif input_data["PUMP"][pump_name]["mode"] == "heating":
                result_json["PUMP"][pump_name]["運転モード"] = "暖房"
            else:
                raise Exception("運転モードが不正です")

            result_json["PUMP"][pump_name]["台数"] = input_data["PUMP"][pump_name]["number_of_pumps"]

            result_json["PUMP"][pump_name]["定格能力[kW]"] = input_data["PUMP"][pump_name]["Qpsr"]
            result_json["PUMP"][pump_name]["定格消費電力[kW]"] = input_data["PUMP"][pump_name][
                "rated_power_consumption_total"]
            result_json["PUMP"][pump_name]["定格流量[m3/h]"] = input_data["PUMP"][pump_name]["Vpsr"]

            result_json["PUMP"][pump_name]["運転時間[時間]"] = np.sum(result_json["PUMP"][pump_name]["Tps"], 0)
            result_json["PUMP"][pump_name]["年間処理熱量[MJ]"] = np.sum(result_json["PUMP"][pump_name]["Qps"], 0)
            result_json["PUMP"][pump_name]["平均処理熱量[kW]"] = \
                result_json["PUMP"][pump_name]["年間処理熱量[MJ]"] * 1000 \
                / (result_json["PUMP"][pump_name]["運転時間[時間]"] * 3600)

            result_json["PUMP"][pump_name]["平均負荷率[-]"] = result_json["PUMP"][pump_name]["平均処理熱量[kW]"] / \
                                                             result_json["PUMP"][pump_name]["定格能力[kW]"]

            result_json["PUMP"][pump_name]["台数制御の有無"] = input_data["PUMP"][pump_name]["is_staging_control"]
            result_json["PUMP"][pump_name]["電力消費量[MWh]"] = np.sum(result_json["PUMP"][pump_name]["E_pump_day"], 0)

    ##----------------------------------------------------------------------------------
    ## 熱源群の一次エネルギー消費量（解説書 2.7）
    ##----------------------------------------------------------------------------------

    # モデル格納用変数

    # 冷房と暖房の熱源群に分ける。
    for ref_original_name in input_data["heat_source_system"]:

        if "冷房" in input_data["heat_source_system"][ref_original_name]:

            if len(input_data["heat_source_system"][ref_original_name]["冷房"]["heat_source"]) > 0:

                input_data["REF"][ref_original_name + "_冷房"] = input_data["heat_source_system"][ref_original_name]["冷房"]
                input_data["REF"][ref_original_name + "_冷房"]["mode"] = "cooling"

                if "冷房(蓄熱)" in input_data["heat_source_system"][ref_original_name]:
                    input_data["REF"][ref_original_name + "_冷房_蓄熱"] = \
                        input_data["heat_source_system"][ref_original_name]["冷房(蓄熱)"]
                    input_data["REF"][ref_original_name + "_冷房_蓄熱"]["isStorage"] = "蓄熱"
                    input_data["REF"][ref_original_name + "_冷房_蓄熱"]["mode"] = "cooling"
                    input_data["REF"][ref_original_name + "_冷房"]["isStorage"] = "追掛"
                    input_data["REF"][ref_original_name + "_冷房"]["storage_type"] = \
                        input_data["heat_source_system"][ref_original_name]["冷房(蓄熱)"]["storage_type"]
                    input_data["REF"][ref_original_name + "_冷房"]["storage_size"] = \
                        input_data["heat_source_system"][ref_original_name]["冷房(蓄熱)"]["storage_size"]
                else:
                    input_data["REF"][ref_original_name + "_冷房"]["isStorage"] = "無"

        if "暖房" in input_data["heat_source_system"][ref_original_name]:

            if len(input_data["heat_source_system"][ref_original_name]["暖房"]["heat_source"]) > 0:

                input_data["REF"][ref_original_name + "_暖房"] = input_data["heat_source_system"][ref_original_name]["暖房"]
                input_data["REF"][ref_original_name + "_暖房"]["mode"] = "heating"

                if "暖房(蓄熱)" in input_data["heat_source_system"][ref_original_name]:
                    input_data["REF"][ref_original_name + "_暖房_蓄熱"] = \
                        input_data["heat_source_system"][ref_original_name]["暖房(蓄熱)"]
                    input_data["REF"][ref_original_name + "_暖房_蓄熱"]["isStorage"] = "蓄熱"
                    input_data["REF"][ref_original_name + "_暖房_蓄熱"]["mode"] = "heating"
                    input_data["REF"][ref_original_name + "_暖房"]["isStorage"] = "追掛"
                    input_data["REF"][ref_original_name + "_暖房"]["storage_type"] = \
                        input_data["heat_source_system"][ref_original_name]["暖房(蓄熱)"]["storage_type"]
                    input_data["REF"][ref_original_name + "_暖房"]["storage_size"] = \
                        input_data["heat_source_system"][ref_original_name]["暖房(蓄熱)"]["storage_size"]
                else:
                    input_data["REF"][ref_original_name + "_暖房"]["isStorage"] = "無"

    ##----------------------------------------------------------------------------------
    ## 蓄熱がある場合の処理（蓄熱槽効率の追加、追掛用熱交換器の検証）
    ##----------------------------------------------------------------------------------

    for ref_name in input_data["REF"]:

        # 蓄熱槽効率
        if input_data["REF"][ref_name]["isStorage"] == "蓄熱" or input_data["REF"][ref_name]["isStorage"] == "追掛":

            input_data["REF"][ref_name]["storageEffratio"] = 0.8
            if input_data["REF"][ref_name]["storage_type"] == "水蓄熱(混合型)":
                input_data["REF"][ref_name]["storageEffratio"] = 0.8
            elif input_data["REF"][ref_name]["storage_type"] == "水蓄熱(成層型)":
                input_data["REF"][ref_name]["storageEffratio"] = 0.9
            elif input_data["REF"][ref_name]["storage_type"] == "氷蓄熱":
                input_data["REF"][ref_name]["storageEffratio"] = 1.0
            else:
                raise Exception("蓄熱槽タイプが不正です")

        # 蓄熱追掛時の熱交換器の追加
        if input_data["REF"][ref_name]["isStorage"] == "追掛":

            for unit_id, unit_configure in enumerate(input_data["REF"][ref_name]["heat_source"]):
                if unit_id == 0 and input_data["REF"][ref_name]["heat_source"][unit_id]["heat_source_type"] != "熱交換器":

                    # 1台目が熱交換器では無い場合、熱交換器を追加する。
                    input_data["REF"][ref_name]["heat_source"].insert(0,
                                                                    {
                                                                        "heat_source_type": "熱交換器",
                                                                        "number": 1.0,
                                                                        "supply_water_temp_summer": None,
                                                                        "supply_water_temp_middle": None,
                                                                        "supply_water_temp_winter": None,
                                                                        "heat_source_rated_capacity":
                                                                            input_data["REF"][ref_name][
                                                                                "storageEffratio"] *
                                                                            input_data["REF"][ref_name][
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
                elif unit_id > 0 and input_data["REF"][ref_name]["heat_source"][unit_id]["heat_source_type"] == "熱交換器":
                    raise Exception("蓄熱槽があるシステムですが、1台目以外に熱交換器が設定されています")

    ##----------------------------------------------------------------------------------
    ## 熱源群全体のスペックを整理する。
    ##----------------------------------------------------------------------------------

    for ref_name in input_data["REF"]:

        input_data["REF"][ref_name]["pump_list"] = set()
        input_data["REF"][ref_name]["num_of_unit"] = 0

        # 熱源群全体の性能
        input_data["REF"][ref_name]["Qref_rated"] = 0
        for unit_id, unit_configure in enumerate(input_data["REF"][ref_name]["heat_source"]):
            # 定格能力（台数×能力）
            input_data["REF"][ref_name]["heat_source"][unit_id]["heat_source_rated_capacity_total"] = \
                unit_configure["heat_source_rated_capacity"] * unit_configure["number"]

            # 熱源主機の定格消費電力（台数×消費電力）
            input_data["REF"][ref_name]["heat_source"][unit_id]["heat_source_rated_power_consumption_total"] = \
                unit_configure["heat_source_rated_power_consumption"] * unit_configure["number"]

            # 熱源主機の定格燃料消費量（台数×燃料消費量）
            input_data["REF"][ref_name]["heat_source"][unit_id]["heat_source_rated_fuel_consumption_total"] = \
                unit_configure["heat_source_rated_fuel_consumption"] * unit_configure["number"]

            # 熱源補機の定格消費電力（台数×消費電力）
            input_data["REF"][ref_name]["heat_source"][unit_id]["heat_source_sub_rated_power_consumption_total"] = \
                unit_configure["heat_source_sub_rated_power_consumption"] * unit_configure["number"]

            # 熱源機器の台数
            input_data["REF"][ref_name]["num_of_unit"] += 1

            # 一次ポンプの消費電力の合計
            input_data["REF"][ref_name]["heat_source"][unit_id]["primary_pump_power_consumption_total"] = \
                unit_configure["primary_pump_power_consumption"] * unit_configure["number"]

            # 冷却塔ファンの消費電力の合計
            input_data["REF"][ref_name]["heat_source"][unit_id]["cooling_tower_fan_power_consumption_total"] = \
                unit_configure["cooling_tower_fan_power_consumption"] * unit_configure["number"]

            # 冷却塔ポンプの消費電力の合計
            input_data["REF"][ref_name]["heat_source"][unit_id]["cooling_tower_pump_power_consumption_total"] = \
                unit_configure["cooling_tower_pump_power_consumption"] * unit_configure["number"]

        # 蓄熱システムの追掛運転用熱交換器の制約
        if input_data["REF"][ref_name]["isStorage"] == "追掛":

            tmpCapacity = input_data["REF"][ref_name]["storageEffratio"] * input_data["REF"][ref_name][
                "storage_size"] / 8 * (1000 / 3600)

            # 1台目は必ず熱交換器であると想定
            if input_data["REF"][ref_name]["heat_source"][0]["heat_source_rated_capacity_total"] > tmpCapacity:
                input_data["REF"][ref_name]["heat_source"][0]["heat_source_rated_capacity_total"] = tmpCapacity

    # 接続される二次ポンプ群

    for ahu_name in input_data["air_handling_system"]:

        if input_data["air_handling_system"][ahu_name]["heat_source_cooling"] + "_冷房" in input_data["REF"]:

            # 冷房熱源群（蓄熱なし）
            input_data["REF"][input_data["air_handling_system"][ahu_name]["heat_source_cooling"] + "_冷房"]["pump_list"].add( \
                input_data["air_handling_system"][ahu_name]["pump_cooling"] + "_冷房")

            # 冷房熱源群（蓄熱あり）
            if input_data["REF"][input_data["air_handling_system"][ahu_name]["heat_source_cooling"] + "_冷房"][
                "isStorage"] == "追掛":
                input_data["REF"][input_data["air_handling_system"][ahu_name]["heat_source_cooling"] + "_冷房_蓄熱"][
                    "pump_list"].add( \
                    input_data["air_handling_system"][ahu_name]["pump_cooling"] + "_冷房")

        if input_data["air_handling_system"][ahu_name]["heat_source_heating"] + "_暖房" in input_data["REF"]:

            # 暖房熱源群（蓄熱なし）
            input_data["REF"][input_data["air_handling_system"][ahu_name]["heat_source_heating"] + "_暖房"]["pump_list"].add( \
                input_data["air_handling_system"][ahu_name]["pump_heating"] + "_暖房")

            # 暖房熱源群（蓄熱あり）
            if input_data["REF"][input_data["air_handling_system"][ahu_name]["heat_source_heating"] + "_暖房"][
                "isStorage"] == "追掛":
                input_data["REF"][input_data["air_handling_system"][ahu_name]["heat_source_heating"] + "_暖房_蓄熱"][
                    "pump_list"].add( \
                    input_data["air_handling_system"][ahu_name]["pump_heating"] + "_暖房")

    ##----------------------------------------------------------------------------------
    ## 結果格納用変数
    ##----------------------------------------------------------------------------------

    for ref_name in input_data["REF"]:

        result_json["REF"][ref_name] = {}
        result_json["REF"][ref_name]["schedule"] = np.zeros((365, 24))  # 運転スケジュール
        result_json["REF"][ref_name]["Qref"] = np.zeros(365)  # 日積算熱源負荷 [MJ/Day]
        result_json["REF"][ref_name]["Tref"] = np.zeros(365)  # 日積算運転時間
        result_json["REF"][ref_name]["Qref_kW"] = np.zeros(365)  # 熱源平均負荷 kW
        result_json["REF"][ref_name]["Qref_OVER"] = np.zeros(365)  # 過負荷分
        result_json["REF"][ref_name]["ghsp_Rq"] = 0  # 冷房負荷と暖房負荷の比率（地中熱ヒートポンプ用）
        result_json["REF"][ref_name]["E_ref_day"] = np.zeros(365)  # 熱源群エネルギー消費量 [MJ]
        result_json["REF"][ref_name]["E_ref_day_MWh"] = np.zeros(365)  # 熱源主機電力消費量 [MWh]
        result_json["REF"][ref_name]["E_ref_ACc_day"] = np.zeros(365)  # 補機電力 [MWh]
        result_json["REF"][ref_name]["E_PPc_day"] = np.zeros(365)  # 一次ポンプ電力 [MWh]
        result_json["REF"][ref_name]["E_CTfan_day"] = np.zeros(365)  # 冷却塔ファン電力 [MWh]
        result_json["REF"][ref_name]["E_CTpump_day"] = np.zeros(365)  # 冷却水ポンプ電力 [MWh]

        result_json["REF"][ref_name]["heat_source"] = {}
        for unit_id, unit_configure in enumerate(input_data["REF"][ref_name]["heat_source"]):
            # 熱源群に属する各熱源機器の値
            result_json["REF"][ref_name]["heat_source"][unit_id] = {}
            result_json["REF"][ref_name]["heat_source"][unit_id]["E_ref_main"] = np.zeros(365)
            result_json["REF"][ref_name]["heat_source"][unit_id]["E_ref_day_per_unit"] = np.zeros(365)
            result_json["REF"][ref_name]["heat_source"][unit_id]["E_ref_day_per_unit_MWh"] = np.zeros(365)

    ##----------------------------------------------------------------------------------
    ## 熱源群の定格能力 （解説書 2.7.5）
    ##----------------------------------------------------------------------------------
    # 熱源群の合計定格能力
    for ref_name in input_data["REF"]:
        input_data["REF"][ref_name]["Qref_rated"] = 0
        for unit_id, unit_configure in enumerate(input_data["REF"][ref_name]["heat_source"]):
            input_data["REF"][ref_name]["Qref_rated"] += input_data["REF"][ref_name]["heat_source"][unit_id][
                "heat_source_rated_capacity_total"]

    ##----------------------------------------------------------------------------------
    ## 蓄熱槽の熱損失 （解説書 2.7.1）
    ##----------------------------------------------------------------------------------

    for ref_name in input_data["REF"]:

        # 蓄熱の場合: 熱損失量 [MJ/day] を足す。損失量は 蓄熱槽容量の3%。
        if input_data["REF"][ref_name]["isStorage"] == "蓄熱":
            result_json["REF"][ref_name]["Qref_thermal_loss"] = input_data["REF"][ref_name]["storage_size"] * 0.03
        else:
            result_json["REF"][ref_name]["Qref_thermal_loss"] = 0

    ##----------------------------------------------------------------------------------
    ## 熱源負荷の算出（解説書 2.7.2）
    ##----------------------------------------------------------------------------------

    for ref_name in input_data["REF"]:

        for dd in range(0, 365):

            if input_data["REF"][ref_name]["mode"] == "cooling":  # 冷熱生成用熱源

                for pump_name in input_data["REF"][ref_name]["pump_list"]:

                    if result_json["PUMP"][pump_name]["Qps"][dd] > 0:
                        # 日積算熱源負荷  [MJ/day]
                        result_json["REF"][ref_name]["Qref"][dd] += \
                            result_json["PUMP"][pump_name]["Qps"][dd] + result_json["PUMP"][pump_name]["Qpsahu_pump"][dd]


            elif input_data["REF"][ref_name]["mode"] == "heating":  # 温熱生成用熱源

                for pump_name in input_data["REF"][ref_name]["pump_list"]:

                    if (result_json["PUMP"][pump_name]["Qps"][dd] + \
                        (-1) * result_json["PUMP"][pump_name]["Qpsahu_pump"][dd]) > 0:
                        result_json["REF"][ref_name]["Qref"][dd] += \
                            result_json["PUMP"][pump_name]["Qps"][dd] + (-1) * \
                            result_json["PUMP"][pump_name]["Qpsahu_pump"][dd]

            # 蓄熱の場合: 熱損失量 [MJ/day] を足す。損失量は 蓄熱槽容量の3%。（MATLAB版では Tref>0で判定）
            if (result_json["REF"][ref_name]["Qref"][dd] != 0) and (input_data["REF"][ref_name]["isStorage"] == "蓄熱"):

                result_json["REF"][ref_name]["Qref"][dd] += result_json["REF"][ref_name]["Qref_thermal_loss"]

                # 蓄熱処理追加（蓄熱槽容量以上の負荷を処理しないようにする）
                if result_json["REF"][ref_name]["Qref"][dd] > \
                        input_data["REF"][ref_name]["storageEffratio"] * input_data["REF"][ref_name]["storage_size"]:
                    result_json["REF"][ref_name]["Qref"][dd] = \
                        input_data["REF"][ref_name]["storageEffratio"] * input_data["REF"][ref_name]["storage_size"]

    ##----------------------------------------------------------------------------------
    ## 熱源群の運転時間（解説書 2.7.3）
    ##----------------------------------------------------------------------------------

    for ref_name in input_data["REF"]:

        for pump_name in input_data["REF"][ref_name]["pump_list"]:
            result_json["REF"][ref_name]["schedule"] += result_json["PUMP"][pump_name]["schedule"]

        # 運転スケジュールの和が「1以上（接続されている二次ポンプ群の1つは動いている）」であれば、熱源群は稼働しているとする。
        result_json["REF"][ref_name]["schedule"][result_json["REF"][ref_name]["schedule"] > 1] = 1

        # 日積算運転時間（熱源負荷が0より大きい場合のみ積算する）
        for dd in range(0, 365):
            if result_json["REF"][ref_name]["Qref"][dd] > 0:
                result_json["REF"][ref_name]["Tref"][dd] = np.sum(result_json["REF"][ref_name]["schedule"][dd])

                # 日平均負荷[kW] と 過負荷[MJ/day] を求める。（検証用）
        for dd in range(0, 365):
            # 平均負荷 [kW]
            if result_json["REF"][ref_name]["Tref"][dd] == 0:
                result_json["REF"][ref_name]["Qref_kW"][dd] = 0
            else:
                result_json["REF"][ref_name]["Qref_kW"][dd] = result_json["REF"][ref_name]["Qref"][dd] / \
                                                             result_json["REF"][ref_name]["Tref"][dd] * 1000 / 3600

            # 過負荷分を集計 [MJ/day]
            if result_json["REF"][ref_name]["Qref_kW"][dd] > input_data["REF"][ref_name]["Qref_rated"]:
                result_json["REF"][ref_name]["Qref_OVER"][dd] = \
                    (result_json["REF"][ref_name]["Qref_kW"][dd] - input_data["REF"][ref_name]["Qref_rated"]) * \
                    result_json["REF"][ref_name]["Tref"][dd] * 3600 / 1000

    print('熱源負荷計算完了')

    if debug:  # pragma: no cover

        for ref_name in input_data["REF"]:
            print(f'--- 熱源群名 {ref_name} ---')

            print(f'熱源群の熱源負荷 Qref: {np.sum(result_json["REF"][ref_name]["Qref"], 0)}')
            print(f'熱源群の平均負荷 Qref_kW: {np.sum(result_json["REF"][ref_name]["Qref_kW"], 0)}')
            print(f'熱源群の過負荷 Qref_OVER: {np.sum(result_json["REF"][ref_name]["Qref_OVER"], 0)}')
            print(f'熱源群の運転時間 Tref: {np.sum(result_json["REF"][ref_name]["Tref"], 0)}')

    ##----------------------------------------------------------------------------------
    ## 熱源機器の特性の読み込み（解説書 附属書A.4）
    ##----------------------------------------------------------------------------------

    for ref_name in input_data["REF"]:

        input_data["REF"][ref_name]["Eref_rated_primary"] = 0

        input_data["REF"][ref_name]["checkCTVWV"] = 0  # 冷却水変流量の有無
        input_data["REF"][ref_name]["checkGEGHP"] = 0  # 発電機能の有無

        for unit_id, unit_configure in enumerate(input_data["REF"][ref_name]["heat_source"]):

            if "冷却水変流量" in unit_configure["heat_source_type"]:
                input_data["REF"][ref_name]["checkCTVWV"] = 1

            if "消費電力自給装置" in unit_configure["heat_source_type"]:
                input_data["REF"][ref_name]["checkGEGHP"] = 1

            # 特性を全て抜き出す。
            refParaSetALL = heat_source_performance[unit_configure["heat_source_type"]]

            # 燃料種類に応じて、一次エネルギー換算を行う。
            fuel_type = str()
            if input_data["REF"][ref_name]["mode"] == "cooling":
                input_data["REF"][ref_name]["heat_source"][unit_id]["parameter"] = refParaSetALL["冷房時の特性"]
                fuel_type = refParaSetALL["冷房時の特性"]["燃料種類"]

            elif input_data["REF"][ref_name]["mode"] == "heating":
                input_data["REF"][ref_name]["heat_source"][unit_id]["parameter"] = refParaSetALL["暖房時の特性"]
                fuel_type = refParaSetALL["暖房時の特性"]["燃料種類"]

            # 燃料種類＋一次エネルギー換算 [kW]
            if fuel_type == "電力":
                input_data["REF"][ref_name]["heat_source"][unit_id]["refInputtype"] = 1
                input_data["REF"][ref_name]["heat_source"][unit_id]["Eref_rated_primary"] = (bc.fprime / 3600) * \
                                                                                          input_data["REF"][ref_name][
                                                                                              "heat_source"][unit_id][
                                                                                              "heat_source_rated_power_consumption_total"]
            elif fuel_type == "ガス":
                input_data["REF"][ref_name]["heat_source"][unit_id]["refInputtype"] = 2
                input_data["REF"][ref_name]["heat_source"][unit_id]["Eref_rated_primary"] = \
                    input_data["REF"][ref_name]["heat_source"][unit_id]["heat_source_rated_fuel_consumption_total"]
            elif fuel_type == "重油":
                input_data["REF"][ref_name]["heat_source"][unit_id]["refInputtype"] = 3
                input_data["REF"][ref_name]["heat_source"][unit_id]["Eref_rated_primary"] = \
                    input_data["REF"][ref_name]["heat_source"][unit_id]["heat_source_rated_fuel_consumption_total"]
            elif fuel_type == "灯油":
                input_data["REF"][ref_name]["heat_source"][unit_id]["refInputtype"] = 4
                input_data["REF"][ref_name]["heat_source"][unit_id]["Eref_rated_primary"] = \
                    input_data["REF"][ref_name]["heat_source"][unit_id]["heat_source_rated_fuel_consumption_total"]
            elif fuel_type == "液化石油ガス":
                input_data["REF"][ref_name]["heat_source"][unit_id]["refInputtype"] = 5
                input_data["REF"][ref_name]["heat_source"][unit_id]["Eref_rated_primary"] = \
                    input_data["REF"][ref_name]["heat_source"][unit_id]["heat_source_rated_fuel_consumption_total"]
            elif fuel_type == "蒸気":
                input_data["REF"][ref_name]["heat_source"][unit_id]["refInputtype"] = 6
                input_data["REF"][ref_name]["heat_source"][unit_id]["heat_source_rated_fuel_consumption_total"] = \
                    input_data["REF"][ref_name]["heat_source"][unit_id]["heat_source_rated_capacity_total"]
                input_data["REF"][ref_name]["heat_source"][unit_id]["Eref_rated_primary"] = \
                    (input_data["building"]["coefficient_dhc"]["heating"]) * \
                    input_data["REF"][ref_name]["heat_source"][unit_id]["heat_source_rated_capacity_total"]
            elif fuel_type == "温水":
                input_data["REF"][ref_name]["heat_source"][unit_id]["refInputtype"] = 7
                input_data["REF"][ref_name]["heat_source"][unit_id]["heat_source_rated_fuel_consumption_total"] = \
                    input_data["REF"][ref_name]["heat_source"][unit_id]["heat_source_rated_capacity_total"]
                input_data["REF"][ref_name]["heat_source"][unit_id]["Eref_rated_primary"] = \
                    (input_data["building"]["coefficient_dhc"]["heating"]) * \
                    input_data["REF"][ref_name]["heat_source"][unit_id]["heat_source_rated_capacity_total"]
            elif fuel_type == "冷水":
                input_data["REF"][ref_name]["heat_source"][unit_id]["refInputtype"] = 8
                input_data["REF"][ref_name]["heat_source"][unit_id]["heat_source_rated_fuel_consumption_total"] = \
                    input_data["REF"][ref_name]["heat_source"][unit_id]["heat_source_rated_capacity_total"]
                input_data["REF"][ref_name]["heat_source"][unit_id]["Eref_rated_primary"] = \
                    (input_data["building"]["coefficient_dhc"]["cooling"]) * \
                    input_data["REF"][ref_name]["heat_source"][unit_id]["heat_source_rated_capacity_total"]

                # 熱源群ごとに積算
            input_data["REF"][ref_name]["Eref_rated_primary"] += input_data["REF"][ref_name]["heat_source"][unit_id][
                "Eref_rated_primary"]

    ##----------------------------------------------------------------------------------
    ## 蓄熱槽からの放熱を加味した補正定格能力 （解説書 2.7.6）
    ##----------------------------------------------------------------------------------

    # 蓄熱槽がある場合の放熱用熱交換器の容量の補正
    for ref_name in input_data["REF"]:

        hex_capacity = 0

        if input_data["REF"][ref_name]["isStorage"] == "追掛":
            if input_data["REF"][ref_name]["heat_source"][0]["heat_source_type"] == "熱交換器":

                # 熱源運転時間の最大値で補正した容量
                hex_capacity = input_data["REF"][ref_name]["heat_source"][0]["heat_source_rated_capacity_total"] * \
                               (8 / np.max(result_json["REF"][ref_name]["Tref"]))

                # 定格容量の合計値を更新
                input_data["REF"][ref_name]["Qref_rated"] = \
                    input_data["REF"][ref_name]["Qref_rated"] + \
                    hex_capacity - input_data["REF"][ref_name]["heat_source"][0]["heat_source_rated_capacity_total"]

                # 熱交換器の容量を修正
                input_data["REF"][ref_name]["heat_source"][0]["heat_source_rated_capacity_total"] = hex_capacity

            else:
                raise Exception('熱交換機が設定されていません')

            if debug:  # pragma: no cover

                print(f'--- 熱源群名 {ref_name} ---')
                print(f'熱交換器の容量: {input_data["REF"][ref_name]["heat_source"][0]["heat_source_rated_capacity_total"]}')
                print(f'熱源群の定格能力の合計 Qref_rated: {input_data["REF"][ref_name]["Qref_rated"]}')

    ##----------------------------------------------------------------------------------
    ## 熱源群の負荷率（解説書 2.7.7）
    ##----------------------------------------------------------------------------------

    for ref_name in input_data["REF"]:

        result_json["REF"][ref_name]["Lref"] = np.zeros(365)  # 日積算熱源負荷 [MJ/Day] の 定格能力に対する比率（熱源定格負荷率）

        for dd in range(0, 365):

            # 負荷率の算出 [-]
            if result_json["REF"][ref_name]["Tref"][dd] > 0:
                # 熱源定格負荷率（定格能力に対する比率
                result_json["REF"][ref_name]["Lref"][dd] = \
                    (result_json["REF"][ref_name]["Qref"][dd] / result_json["REF"][ref_name]["Tref"][dd] * 1000 / 3600) / \
                    input_data["REF"][ref_name]["Qref_rated"]

            if np.isnan(result_json["REF"][ref_name]["Lref"][dd]) == True:
                result_json["REF"][ref_name]["Lref"][dd] = 0

    ##----------------------------------------------------------------------------------
    ## 熱源群のマトリックスIDの指定
    ##----------------------------------------------------------------------------------

    for ref_name in input_data["REF"]:

        result_json["REF"][ref_name]["matrix_iL"] = np.zeros(365)  # 熱源の負荷率区分
        result_json["REF"][ref_name]["matrix_iT"] = np.zeros(365)  # 熱源の温度区分

        for dd in range(0, 365):

            if result_json["REF"][ref_name]["Lref"][dd] > 0:

                # 負荷率帯マトリックス
                result_json["REF"][ref_name]["matrix_iL"][dd] = count_Matrix(result_json["REF"][ref_name]["Lref"][dd],
                                                                            mxL)

                # 外気温帯マトリックス
                if input_data["REF"][ref_name]["mode"] == "cooling":
                    result_json["REF"][ref_name]["matrix_iT"][dd] = count_Matrix(toa_ave[dd], mx_thermal_cooling)
                elif input_data["REF"][ref_name]["mode"] == "heating":
                    result_json["REF"][ref_name]["matrix_iT"][dd] = count_Matrix(toa_ave[dd], mx_thermal_heating)

                    # ----------------------------------------------------------------------------------
    # 蓄熱システムによる外気温帯の補正
    # ----------------------------------------------------------------------------------

    for ref_name in input_data["REF"]:

        if input_data["REF"][ref_name]["isStorage"] == "蓄熱":

            for dd in range(0, 365):

                if result_json["REF"][ref_name]["matrix_iT"][dd] > 1:
                    result_json["REF"][ref_name]["matrix_iT"][dd] = result_json["REF"][ref_name]["matrix_iT"][
                                                                       dd] - 1  # 外気温帯を1つ下げる。
                elif result_json["REF"][ref_name]["matrix_iT"][dd] == 1:
                    result_json["REF"][ref_name]["matrix_iT"][dd] = result_json["REF"][ref_name]["matrix_iT"][dd]

    ##----------------------------------------------------------------------------------
    ## 湿球温度 （解説書 2.7.4.2）
    ##----------------------------------------------------------------------------------

    ToawbC = Area[input_data["building"]["region"] + "地域"]["湿球温度係数_冷房a1"] * ToadbC + \
             Area[input_data["building"]["region"] + "地域"]["湿球温度係数_冷房a0"]
    ToawbH = Area[input_data["building"]["region"] + "地域"]["湿球温度係数_暖房a1"] * ToadbH + \
             Area[input_data["building"]["region"] + "地域"]["湿球温度係数_暖房a0"]

    # 保存用
    result_json["Matrix"]["ToawbC"] = ToawbC
    result_json["Matrix"]["ToawbH"] = ToawbH

    ##----------------------------------------------------------------------------------
    ## 冷却水温度 （解説書 2.7.4.3）
    ##----------------------------------------------------------------------------------

    TctwC = ToawbC + 3  # 冷却水温度 [℃]
    TctwH = 15.5 * np.ones(6)  # 水冷式の暖房時熱源水温度（暫定） [℃]

    # 保存用
    result_json["Matrix"]["TctwC"] = TctwC
    result_json["Matrix"]["TctwH"] = TctwH

    ##----------------------------------------------------------------------------------
    ## 地中熱交換器（クローズドループ）からの熱源水温度 （解説書 2.7.4.4）
    ##----------------------------------------------------------------------------------

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
    gshpToa_h = [-3, -0.8, 0, 1.1, 3.6, 6, 9.3, 17.5]  # 地盤モデル：暖房時平均外気温
    gshpToa_c = [16.8, 17, 18.9, 19.6, 20.5, 22.4, 22.1, 24.6]  # 地盤モデル：冷房時平均外気温

    # 冷暖房比率 ghsp_Rq
    for ref_original_name in input_data["heat_source_system"]:

        Qcmax = 0
        if "冷房" in input_data["heat_source_system"][ref_original_name]:
            if len(input_data["heat_source_system"][ref_original_name]["冷房"]["heat_source"]) > 0:
                Qcmax = np.max(result_json["REF"][ref_original_name + "_冷房"]["Qref"], 0)

        Qhmax = 0
        if "暖房" in input_data["heat_source_system"][ref_original_name]:
            if len(input_data["heat_source_system"][ref_original_name]["暖房"]["heat_source"]) > 0:
                Qhmax = np.max(result_json["REF"][ref_original_name + "_暖房"]["Qref"], 0)

        if Qcmax != 0 and Qhmax != 0:

            result_json["REF"][ref_original_name + "_冷房"]["ghsp_Rq"] = (Qcmax - Qhmax) / (Qcmax + Qhmax)
            result_json["REF"][ref_original_name + "_暖房"]["ghsp_Rq"] = (Qcmax - Qhmax) / (Qcmax + Qhmax)

        elif Qcmax == 0 and Qhmax != 0:
            result_json["REF"][ref_original_name + "_暖房"]["ghsp_Rq"] = 0

        elif Qcmax != 0 and Qhmax == 0:
            result_json["REF"][ref_original_name + "_冷房"]["ghsp_Rq"] = 0

    ##----------------------------------------------------------------------------------
    ## 熱源水等の温度 matrix_T （解説書 2.7.4）
    ##----------------------------------------------------------------------------------

    # 地中熱オープンループの地盤特性の読み込み
    with open(database_directory + 'ac_gshp_openloop.json', 'r', encoding='utf-8') as f:
        AC_gshp_openloop = json.load(f)

    for ref_name in input_data["REF"]:

        for unit_id, unit_configure in enumerate(input_data["REF"][ref_name]["heat_source"]):

            # 日別の熱源水等の温度
            input_data["REF"][ref_name]["heat_source"][unit_id]["heat_source_temperature"] = np.zeros(365)

            if "地盤A" in unit_configure["parameter"]["熱源種類"] or "地盤B" in unit_configure["parameter"][
                "熱源種類"] or \
                    "地盤C" in unit_configure["parameter"]["熱源種類"] or "地盤D" in unit_configure["parameter"][
                "熱源種類"] or \
                    "地盤E" in unit_configure["parameter"]["熱源種類"] or "地盤F" in unit_configure["parameter"][
                "熱源種類"]:  # 地中熱オープンループ

                for dd in range(365):

                    # 月別の揚水温度
                    theta_wo_m = AC_gshp_openloop["theta_ac_wo_ave"][input_data["building"]["region"] + "地域"] + \
                                 AC_gshp_openloop["theta_ac_wo_m"][input_data["building"]["region"] + "地域"][
                                     bc.day2month(dd)]

                    # 月別の地盤からの熱源水還り温度
                    if input_data["REF"][ref_name]["mode"] == "cooling":

                        # 日別の熱源水還り温度（冷房期）
                        heat_source_temperature = \
                            theta_wo_m + AC_gshp_openloop["theta_wo_c"][unit_configure["parameter"]["熱源種類"]] + \
                            AC_gshp_openloop["theta_hex_c"][unit_configure["parameter"]["熱源種類"]]

                        # マトリックス化して日別のデータに変換
                        input_data["REF"][ref_name]["heat_source"][unit_id]["heat_source_temperature"][dd] = \
                            ToadbC[int(count_Matrix(heat_source_temperature, mx_thermal_cooling)) - 1]

                        # マトリックス化せずに日別のデータに変換（将来的にはこちらにすべき）
                        # input_data["REF"][ref_name]["heat_source"][unit_id]["heat_source_temperature"][dd] = heat_source_temperature

                    elif input_data["REF"][ref_name]["mode"] == "heating":

                        # 日別の熱源水還り温度（暖房期）
                        heat_source_temperature = \
                            theta_wo_m + AC_gshp_openloop["theta_wo_h"][unit_configure["parameter"]["熱源種類"]] + \
                            AC_gshp_openloop["theta_hex_h"][unit_configure["parameter"]["熱源種類"]]

                        # マトリックス化して日別のデータに変換
                        input_data["REF"][ref_name]["heat_source"][unit_id]["heat_source_temperature"][dd] = \
                            ToadbH[int(count_Matrix(heat_source_temperature, mx_thermal_heating)) - 1]

                        # マトリックス化せずに日別のデータに変換（将来的にはこちらにすべき）
                        # input_data["REF"][ref_name]["heat_source"][unit_id]["heat_source_temperature"][dd] = heat_source_temperature

            else:

                if unit_configure["parameter"]["熱源種類"] == "水" and input_data["REF"][ref_name]["mode"] == "cooling":
                    input_data["REF"][ref_name]["heat_source"][unit_id]["matrix_T"] = TctwC  # 冷却水温度

                elif unit_configure["parameter"]["熱源種類"] == "水" and input_data["REF"][ref_name][
                    "mode"] == "heating":
                    input_data["REF"][ref_name]["heat_source"][unit_id]["matrix_T"] = TctwH  # 冷却水温度

                elif unit_configure["parameter"]["熱源種類"] == "空気" and input_data["REF"][ref_name][
                    "mode"] == "cooling":
                    input_data["REF"][ref_name]["heat_source"][unit_id]["matrix_T"] = ToadbC  # 乾球温度

                elif unit_configure["parameter"]["熱源種類"] == "空気" and input_data["REF"][ref_name][
                    "mode"] == "heating":
                    input_data["REF"][ref_name]["heat_source"][unit_id]["matrix_T"] = ToawbH  # 湿球温度

                elif unit_configure["parameter"]["熱源種類"] == "不要" and input_data["REF"][ref_name][
                    "mode"] == "cooling":
                    input_data["REF"][ref_name]["heat_source"][unit_id]["matrix_T"] = ToadbC  # 乾球温度

                elif unit_configure["parameter"]["熱源種類"] == "不要" and input_data["REF"][ref_name][
                    "mode"] == "heating":
                    input_data["REF"][ref_name]["heat_source"][unit_id]["matrix_T"] = ToadbH  # 乾球温度

                elif "地盤1" in unit_configure["parameter"]["熱源種類"] or "地盤2" in unit_configure["parameter"][
                    "熱源種類"] or \
                        "地盤3" in unit_configure["parameter"]["熱源種類"] or "地盤4" in unit_configure["parameter"][
                    "熱源種類"] or \
                        "地盤5" in unit_configure["parameter"]["熱源種類"]:  # 地中熱クローズループ

                    for gound_type in range(1, 6):

                        if unit_configure["parameter"]["熱源種類"] == "地盤" + str(int(gound_type)) and \
                                input_data["REF"][ref_name]["mode"] == "cooling":
                            igstype = int(gound_type) - 1
                            iAREA = int(input_data["building"]["region"]) - 1
                            # 地盤からの還り温度（冷房）
                            input_data["REF"][ref_name]["heat_source"][unit_id]["matrix_T"] = \
                                (gshp_cc[igstype] * result_json["REF"][ref_name]["ghsp_Rq"] + gshp_dc[igstype]) * (
                                        ToadbC - gshpToa_c[iAREA]) + \
                                (ghsptoa_ave[iAREA] + gshp_ac[igstype] * result_json["REF"][ref_name]["ghsp_Rq"] +
                                 gshp_bc[igstype])

                        elif unit_configure["parameter"]["熱源種類"] == "地盤" + str(int(gound_type)) and \
                                input_data["REF"][ref_name]["mode"] == "heating":
                            igstype = int(gound_type) - 1
                            iAREA = int(input_data["building"]["region"]) - 1
                            # 地盤からの還り温度（暖房）
                            input_data["REF"][ref_name]["heat_source"][unit_id]["matrix_T"] = \
                                (gshp_ch[igstype] * result_json["REF"][ref_name]["ghsp_Rq"] + gshp_dh[igstype]) * (
                                        ToadbH - gshpToa_h[iAREA]) + \
                                (ghsptoa_ave[iAREA] + gshp_ah[igstype] * result_json["REF"][ref_name]["ghsp_Rq"] +
                                 gshp_bh[igstype])

                else:
                    raise Exception("熱源種類が不正です。")

                # マトリックスから日別のデータに変換
                for dd in range(365):

                    if result_json["REF"][ref_name]["matrix_iT"][dd] > 0:
                        iT = int(result_json["REF"][ref_name]["matrix_iT"][dd]) - 1
                        input_data["REF"][ref_name]["heat_source"][unit_id]["heat_source_temperature"][dd] = \
                            input_data["REF"][ref_name]["heat_source"][unit_id]["matrix_T"][iT]

    ##----------------------------------------------------------------------------------
    ## 任意評定用　熱源水温度（ SP-3 ）
    ##----------------------------------------------------------------------------------

    if "special_input_data" in input_data:
        if "heat_source_temperature_monthly" in input_data["special_input_data"]:

            for ref_original_name in input_data["special_input_data"]["heat_source_temperature_monthly"]:

                # 入力された熱源群名称から、計算上使用する熱源群名称（冷暖、蓄熱分離）に変換
                for ref_name in [ref_original_name + "_冷房", ref_original_name + "_暖房",
                                 ref_original_name + "_冷房_蓄熱", ref_original_name + "_暖房_蓄熱"]:

                    if ref_name in input_data["REF"]:
                        for unit_id, unit_configure in enumerate(input_data["REF"][ref_name]["heat_source"]):
                            for dd in range(0, 365):
                                input_data["REF"][ref_name]["heat_source"][unit_id]["heat_source_temperature"][dd] = \
                                    input_data["special_input_data"]["heat_source_temperature_monthly"][ref_original_name][
                                        bc.day2month(dd)]

    if debug:  # pragma: no cover
        for ref_name in input_data["REF"]:
            for unit_id, unit_configure in enumerate(input_data["REF"][ref_name]["heat_source"]):
                print(f'--- 熱源群名 {ref_name} ---')
                print(f'- {unit_id + 1} 台目の熱源機器の熱源水温度 -')
                print(input_data["REF"][ref_name]["heat_source"][unit_id]["heat_source_temperature"])

    ##----------------------------------------------------------------------------------
    ## 最大能力比 xQratio （解説書 2.7.8）
    ##----------------------------------------------------------------------------------

    for ref_name in input_data["REF"]:

        for unit_id, unit_configure in enumerate(input_data["REF"][ref_name]["heat_source"]):

            ## 能力比（各外気温帯における最大能力）
            input_data["REF"][ref_name]["heat_source"][unit_id]["xQratio"] = np.zeros(365)

            for dd in range(0, 365):

                # 外気温度帯
                temperature = input_data["REF"][ref_name]["heat_source"][unit_id]["heat_source_temperature"][dd]

                # 特性式の数
                curveNum = len(unit_configure["parameter"]["能力比"])

                # 下限値
                temp_min_list = []
                for para_num in range(0, curveNum):
                    temp_min_list.append(unit_configure["parameter"]["能力比"][para_num]["下限"])
                # 上限値
                temp_max_list = []
                for para_num in range(0, curveNum):
                    temp_max_list.append(unit_configure["parameter"]["能力比"][para_num]["上限"])

                # 上限と下限を定める
                if temperature < temp_min_list[0]:
                    temperature = temp_min_list[0]
                elif temperature > temp_max_list[-1]:
                    temperature = temp_max_list[-1]

                for para_num in reversed(range(0, curveNum)):
                    if temperature <= temp_max_list[para_num]:
                        input_data["REF"][ref_name]["heat_source"][unit_id]["xQratio"][dd] = \
                            unit_configure["parameter"]["能力比"][para_num]["基整促係数"] * ( \
                                        unit_configure["parameter"]["能力比"][para_num]["係数"][
                                            "a4"] * temperature ** 4 + \
                                        unit_configure["parameter"]["能力比"][para_num]["係数"][
                                            "a3"] * temperature ** 3 + \
                                        unit_configure["parameter"]["能力比"][para_num]["係数"][
                                            "a2"] * temperature ** 2 + \
                                        unit_configure["parameter"]["能力比"][para_num]["係数"]["a1"] * temperature + \
                                        unit_configure["parameter"]["能力比"][para_num]["係数"]["a0"])

        for unit_id, unit_configure in enumerate(input_data["REF"][ref_name]["heat_source"]):

            input_data["REF"][ref_name]["heat_source"][unit_id]["Q_ref_max"] = np.zeros(365)

            for dd in range(0, 365):
                # 各外気温区分における最大能力 [kW]
                input_data["REF"][ref_name]["heat_source"][unit_id]["Q_ref_max"][dd] = \
                    input_data["REF"][ref_name]["heat_source"][unit_id]["heat_source_rated_capacity_total"] * \
                    input_data["REF"][ref_name]["heat_source"][unit_id]["xQratio"][dd]

            if debug:  # pragma: no cover
                print(f'--- 熱源群名 {ref_name} ---')
                print(f'- {unit_id + 1} 台目の熱源機器 -')
                print(f' Q_ref_max {input_data["REF"][ref_name]["heat_source"][unit_id]["Q_ref_max"]}')

    # ----------------------------------------------------------------------------------
    # 蓄熱システムによる運転時間の補正（解説書 2.7.15 蓄熱）
    # ----------------------------------------------------------------------------------

    # 蓄熱の場合のマトリックス操作（負荷率１に集約＋外気温を１レベル変える）
    for ref_name in input_data["REF"]:

        input_data["REF"][ref_name]["Q_ref_max_total"] = np.zeros(365)

        if input_data["REF"][ref_name]["isStorage"] == "蓄熱":

            for unit_id, unit_configure in enumerate(input_data["REF"][ref_name]["heat_source"]):

                for dd in range(0, 365):
                    # 各外気温区分における最大能力の合計を算出[kW]
                    input_data["REF"][ref_name]["Q_ref_max_total"][dd] += \
                        input_data["REF"][ref_name]["heat_source"][unit_id]["Q_ref_max"][dd]

            for dd in range(0, 365):

                if result_json["REF"][ref_name]["matrix_iL"][dd] > 0:  # これを入れないと aveL(matrix_iL)でエラーとなる。

                    # 負荷率帯 matrix_iL のときの熱負荷
                    timeQmax = aveL[int(result_json["REF"][ref_name]["matrix_iL"][dd]) - 1] \
                               * result_json["REF"][ref_name]["Tref"][dd] * input_data["REF"][ref_name]["Qref_rated"]

                    # 負荷率帯を「負荷率帯 10」にする。
                    result_json["REF"][ref_name]["matrix_iL"][dd] = len(aveL) - 1

                    # 運転時間を書き換え ＝ 全負荷相当運転時間（熱負荷を最大負荷で除す）とする。
                    result_json["REF"][ref_name]["Tref"][dd] = \
                        timeQmax / (input_data["REF"][ref_name]["Q_ref_max_total"][dd])

                    ##----------------------------------------------------------------------------------
    ## 最大入力比 xPratio （解説書 2.7.11）
    ##----------------------------------------------------------------------------------

    for ref_name in input_data["REF"]:

        for unit_id, unit_configure in enumerate(input_data["REF"][ref_name]["heat_source"]):

            # 入力比（各外気温帯における最大入力）
            input_data["REF"][ref_name]["heat_source"][unit_id]["xPratio"] = np.zeros(365)

            # 外気温度帯マトリックス 
            for dd in range(0, 365):

                # 外気温度帯
                temperature = input_data["REF"][ref_name]["heat_source"][unit_id]["heat_source_temperature"][dd]

                # 特性式の数
                curveNum = len(unit_configure["parameter"]["入力比"])

                # 下限値
                temp_min_list = []
                for para_num in range(0, curveNum):
                    temp_min_list.append(unit_configure["parameter"]["入力比"][para_num]["下限"])
                # 上限値
                temp_max_list = []
                for para_num in range(0, curveNum):
                    temp_max_list.append(unit_configure["parameter"]["入力比"][para_num]["上限"])

                # 上限と下限を定める
                if temperature < temp_min_list[0]:
                    temperature = temp_min_list[0]
                elif temperature > temp_max_list[-1]:
                    temperature = temp_max_list[-1]

                for para_num in reversed(range(0, curveNum)):
                    if temperature <= temp_max_list[para_num]:
                        input_data["REF"][ref_name]["heat_source"][unit_id]["xPratio"][dd] = \
                            unit_configure["parameter"]["入力比"][para_num]["基整促係数"] * ( \
                                        unit_configure["parameter"]["入力比"][para_num]["係数"][
                                            "a4"] * temperature ** 4 + \
                                        unit_configure["parameter"]["入力比"][para_num]["係数"][
                                            "a3"] * temperature ** 3 + \
                                        unit_configure["parameter"]["入力比"][para_num]["係数"][
                                            "a2"] * temperature ** 2 + \
                                        unit_configure["parameter"]["入力比"][para_num]["係数"]["a1"] * temperature + \
                                        unit_configure["parameter"]["入力比"][para_num]["係数"]["a0"])

        for unit_id, unit_configure in enumerate(input_data["REF"][ref_name]["heat_source"]):

            input_data["REF"][ref_name]["heat_source"][unit_id]["E_ref_max"] = np.zeros(365)

            for dd in range(0, 365):
                # 各外気温区分における最大入力 [kW]  (1次エネルギー換算値であることに注意）
                input_data["REF"][ref_name]["heat_source"][unit_id]["E_ref_max"][dd] = \
                    input_data["REF"][ref_name]["heat_source"][unit_id]["Eref_rated_primary"] * \
                    input_data["REF"][ref_name]["heat_source"][unit_id]["xPratio"][dd]

            if debug:  # pragma: no cover
                print(f'--- 熱源群名 {ref_name} ---')
                print(f'- {unit_id + 1} 台目の熱源機器 -')
                print(f' E_ref_max {input_data["REF"][ref_name]["heat_source"][unit_id]["E_ref_max"]}')

    ##----------------------------------------------------------------------------------
    ## 熱源機器の運転台数（解説書 2.7.9）
    ##----------------------------------------------------------------------------------

    # 運転台数マトリックス
    for ref_name in input_data["REF"]:

        result_json["REF"][ref_name]["num_of_operation"] = np.zeros(365)

        for dd in range(0, 365):

            if result_json["REF"][ref_name]["Tref"][dd] > 0:  # 運転していれば

                iL = int(result_json["REF"][ref_name]["matrix_iL"][dd]) - 1

                if input_data["REF"][ref_name]["is_staging_control"] == "無":  # 運転台数制御が「無」の場合

                    result_json["REF"][ref_name]["num_of_operation"][dd] = input_data["REF"][ref_name]["num_of_unit"]

                elif input_data["REF"][ref_name]["is_staging_control"] == "有":  # 運転台数制御が「有」の場合

                    # 処理熱量 [kW]
                    tmpQ = input_data["REF"][ref_name]["Qref_rated"] * aveL[iL]

                    # 運転台数 num_of_operation
                    tmpQmax = 0
                    for rr in range(0, input_data["REF"][ref_name]["num_of_unit"]):
                        tmpQmax += input_data["REF"][ref_name]["heat_source"][rr]["Q_ref_max"][dd]

                        if tmpQ < tmpQmax:
                            break

                    result_json["REF"][ref_name]["num_of_operation"][dd] = rr + 1

        if debug:  # pragma: no cover
            print(f'--- 熱源群名 {ref_name} ---')
            print(f' num_of_operation {result_json["REF"][ref_name]["num_of_operation"]}')

    ##----------------------------------------------------------------------------------
    ## 熱源群の運転負荷率（解説書 2.7.12）
    ##----------------------------------------------------------------------------------

    for ref_name in input_data["REF"]:

        result_json["REF"][ref_name]["load_ratio"] = np.zeros(365)

        for dd in range(0, 365):

            if result_json["REF"][ref_name]["Tref"][dd] > 0:  # 運転していれば

                iL = int(result_json["REF"][ref_name]["matrix_iL"][dd]) - 1

                # 処理熱量 [kW]
                tmpQ = input_data["REF"][ref_name]["Qref_rated"] * aveL[iL]

                Qrefr_mod_max = 0
                for unit_id in range(0, int(result_json["REF"][ref_name]["num_of_operation"][dd])):
                    Qrefr_mod_max += input_data["REF"][ref_name]["heat_source"][unit_id]["Q_ref_max"][dd]

                # [iT,iL]における負荷率
                result_json["REF"][ref_name]["load_ratio"][dd] = tmpQ / Qrefr_mod_max

                if input_data["REF"][ref_name]["isStorage"] == "蓄熱":
                    result_json["REF"][ref_name]["load_ratio"][dd] = 1.0

                # # 過負荷時の負荷率は 1.0 とする。ペナルティは別途乗じる。
                # if iL == divL-1:
                #     result_json["REF"][ref_name]["load_ratio"][dd] = 1.0

        if debug:  # pragma: no cover
            print(f'--- 熱源群名 {ref_name} ---')
            print(f' load_ratio {result_json["REF"][ref_name]["load_ratio"]}')

    ##----------------------------------------------------------------------------------
    ## 部分負荷特性 （解説書 2.7.13）
    ##----------------------------------------------------------------------------------

    for ref_name in input_data["REF"]:

        for unit_id, unit_configure in enumerate(input_data["REF"][ref_name]["heat_source"]):
            input_data["REF"][ref_name]["heat_source"][unit_id]["coeff_x"] = np.zeros(365)

        for dd in range(0, 365):

            iL = int(result_json["REF"][ref_name]["matrix_iL"][dd]) - 1  # 負荷率帯のマトリックス番号

            # 部分負荷特性（各負荷率・各温度帯について）
            for unit_id in range(0, int(result_json["REF"][ref_name]["num_of_operation"][dd])):

                # どの部分負荷特性を使うか（インバータターボなど、冷却水温度によって特性が異なる場合がある）
                xCurveNum = 0
                if len(input_data["REF"][ref_name]["heat_source"][unit_id]["parameter"][
                           "部分負荷特性"]) > 1:  # 部分負荷特性が2以上設定されている場合

                    for para_id in range(0, len(
                            input_data["REF"][ref_name]["heat_source"][unit_id]["parameter"]["部分負荷特性"])):

                        if input_data["REF"][ref_name]["heat_source"][unit_id]["heat_source_temperature"][dd] > \
                                input_data["REF"][ref_name]["heat_source"][unit_id]["parameter"]["部分負荷特性"][para_id][
                                    "冷却水温度下限"] and \
                                input_data["REF"][ref_name]["heat_source"][unit_id]["heat_source_temperature"][dd] <= \
                                input_data["REF"][ref_name]["heat_source"][unit_id]["parameter"]["部分負荷特性"][para_id][
                                    "冷却水温度上限"]:
                            xCurveNum = para_id

                # 機器特性による上下限を考慮した部分負荷率 tmpL
                tmpL = 0
                if result_json["REF"][ref_name]["load_ratio"][dd] < \
                        input_data["REF"][ref_name]["heat_source"][unit_id]["parameter"]["部分負荷特性"][xCurveNum][
                            "下限"]:
                    tmpL = input_data["REF"][ref_name]["heat_source"][unit_id]["parameter"]["部分負荷特性"][xCurveNum][
                        "下限"]
                elif result_json["REF"][ref_name]["load_ratio"][dd] > \
                        input_data["REF"][ref_name]["heat_source"][unit_id]["parameter"]["部分負荷特性"][xCurveNum][
                            "上限"]:
                    tmpL = input_data["REF"][ref_name]["heat_source"][unit_id]["parameter"]["部分負荷特性"][xCurveNum][
                        "上限"]
                else:
                    tmpL = result_json["REF"][ref_name]["load_ratio"][dd]

                # 部分負荷特性
                input_data["REF"][ref_name]["heat_source"][unit_id]["coeff_x"][dd] = \
                    input_data["REF"][ref_name]["heat_source"][unit_id]["parameter"]["部分負荷特性"][xCurveNum][
                        "基整促係数"] * ( \
                                input_data["REF"][ref_name]["heat_source"][unit_id]["parameter"]["部分負荷特性"][
                                    xCurveNum]["係数"]["a4"] * tmpL ** 4 + \
                                input_data["REF"][ref_name]["heat_source"][unit_id]["parameter"]["部分負荷特性"][
                                    xCurveNum]["係数"]["a3"] * tmpL ** 3 + \
                                input_data["REF"][ref_name]["heat_source"][unit_id]["parameter"]["部分負荷特性"][
                                    xCurveNum]["係数"]["a2"] * tmpL ** 2 + \
                                input_data["REF"][ref_name]["heat_source"][unit_id]["parameter"]["部分負荷特性"][
                                    xCurveNum]["係数"]["a1"] * tmpL + \
                                input_data["REF"][ref_name]["heat_source"][unit_id]["parameter"]["部分負荷特性"][
                                    xCurveNum]["係数"]["a0"])

                # 過負荷時のペナルティ
                if iL == divL - 1:
                    input_data["REF"][ref_name]["heat_source"][unit_id]["coeff_x"][dd] = \
                        input_data["REF"][ref_name]["heat_source"][unit_id]["coeff_x"][dd] * 1.2

    ##----------------------------------------------------------------------------------
    ## 送水温度特性 （解説書 2.7.14）
    ##----------------------------------------------------------------------------------

    for ref_name in input_data["REF"]:

        # 送水温度特性（各負荷率・各温度帯について）
        for unit_id, unit_configure in enumerate(input_data["REF"][ref_name]["heat_source"]):
            input_data["REF"][ref_name]["heat_source"][unit_id]["coeff_tw"] = np.ones(365)

        for dd in range(0, 365):

            # iL = int(result_json["REF"][ref_name]["matrix_iL"][dd]) -1    # 負荷率帯のマトリックス番号

            # 送水温度特性（各負荷率・各温度帯について）
            for unit_id in range(0, int(result_json["REF"][ref_name]["num_of_operation"][dd])):

                # 送水温度特性
                if input_data["REF"][ref_name]["heat_source"][unit_id]["parameter"]["送水温度特性"] != []:

                    # 送水温度 TCtmp
                    TCtmp = 0
                    if input_data["REF"][ref_name]["mode"] == "cooling":

                        if input_data["REF"][ref_name]["heat_source"][unit_id]["supply_water_temp_summer"] is None:
                            TCtmp = 5
                        else:
                            TCtmp = input_data["REF"][ref_name]["heat_source"][unit_id]["supply_water_temp_summer"]

                    elif input_data["REF"][ref_name]["mode"] == "heating":

                        if input_data["REF"][ref_name]["heat_source"][unit_id]["supply_water_temp_winter"] is None:
                            TCtmp = 50
                        else:
                            TCtmp = input_data["REF"][ref_name]["heat_source"][unit_id]["supply_water_temp_winter"]

                    # 送水温度の上下限
                    if TCtmp < input_data["REF"][ref_name]["heat_source"][unit_id]["parameter"]["送水温度特性"][0][
                        "下限"]:
                        TCtmp = input_data["REF"][ref_name]["heat_source"][unit_id]["parameter"]["送水温度特性"][0][
                            "下限"]
                    elif TCtmp > input_data["REF"][ref_name]["heat_source"][unit_id]["parameter"]["送水温度特性"][0][
                        "上限"]:
                        TCtmp = input_data["REF"][ref_name]["heat_source"][unit_id]["parameter"]["送水温度特性"][0][
                            "上限"]

                    # 送水温度特性
                    input_data["REF"][ref_name]["heat_source"][unit_id]["coeff_tw"][dd] = \
                        input_data["REF"][ref_name]["heat_source"][unit_id]["parameter"]["送水温度特性"][0][
                            "基整促係数"] * ( \
                                    input_data["REF"][ref_name]["heat_source"][unit_id]["parameter"]["送水温度特性"][0][
                                        "係数"]["a4"] * TCtmp ** 4 + \
                                    input_data["REF"][ref_name]["heat_source"][unit_id]["parameter"]["送水温度特性"][0][
                                        "係数"]["a3"] * TCtmp ** 3 + \
                                    input_data["REF"][ref_name]["heat_source"][unit_id]["parameter"]["送水温度特性"][0][
                                        "係数"]["a2"] * TCtmp ** 2 + \
                                    input_data["REF"][ref_name]["heat_source"][unit_id]["parameter"]["送水温度特性"][0][
                                        "係数"]["a1"] * TCtmp + \
                                    input_data["REF"][ref_name]["heat_source"][unit_id]["parameter"]["送水温度特性"][0][
                                        "係数"]["a0"])

    # ----------------------------------------------------------------------------------
    # 蓄熱システムによる運転時間の補正（解説書 2.7.15 追掛）
    # ----------------------------------------------------------------------------------

    # 蓄熱槽を持つシステムの追い掛け時運転時間補正（追い掛け運転開始時に蓄熱量がすべて使われない問題を解消） 2014/1/10
    for ref_name in input_data["REF"]:

        result_json["REF"][ref_name]["hoseiStorage"] = np.ones(365)

        if input_data["REF"][ref_name]["isStorage"] == "追掛":

            for dd in range(0, 365):

                # iL = int(result_json["REF"][ref_name]["matrix_iL"][dd]) -1

                if int(result_json["REF"][ref_name]["num_of_operation"][dd]) >= 2:

                    # 2台目以降の合計最大能力（＝熱交換器以外の能力）
                    Qrefr_mod_except_HEX = 0
                    for unit_id in range(1, int(result_json["REF"][ref_name]["num_of_operation"][dd])):
                        Qrefr_mod_except_HEX += input_data["REF"][ref_name]["heat_source"][unit_id]["Q_ref_max"][dd]

                    # 追い掛け時運転時間の補正率
                    # （ Q_ref_max * hosei * xL + Qrefr_mod_except_HEX = (Q_ref_max + Qrefr_mod_except_HEX) * xL ）
                    result_json["REF"][ref_name]["hoseiStorage"][dd] = \
                        1 - (input_data["REF"][ref_name]["heat_source"][0]["Q_ref_max"][dd] * \
                             (1 - result_json["REF"][ref_name]["load_ratio"][dd]) / \
                             (result_json["REF"][ref_name]["load_ratio"][dd] * Qrefr_mod_except_HEX))

            # 運転時間を補正
            for dd in range(0, 365):
                if result_json["REF"][ref_name]["Tref"][dd] > 0:
                    result_json["REF"][ref_name]["Tref"][dd] = \
                        result_json["REF"][ref_name]["Tref"][dd] * result_json["REF"][ref_name]["hoseiStorage"][dd]

    ##----------------------------------------------------------------------------------
    ## 熱源機器の一次エネルギー消費量（解説書 2.7.16）
    ##----------------------------------------------------------------------------------

    for ref_name in input_data["REF"]:

        result_json["REF"][ref_name]["E_ref_sub"] = np.zeros(365)
        result_json["REF"][ref_name]["E_ref_pri_pump"] = np.zeros(365)
        result_json["REF"][ref_name]["E_ref_ct_fan"] = np.zeros(365)
        result_json["REF"][ref_name]["E_ref_ct_pump"] = np.zeros(365)

        for dd in range(0, 365):

            iL = int(result_json["REF"][ref_name]["matrix_iL"][dd]) - 1

            # 熱源主機（機器毎）：エネルギー消費量 kW のマトリックス E_ref_main
            for unit_id in range(0, int(result_json["REF"][ref_name]["num_of_operation"][dd])):
                result_json["REF"][ref_name]["heat_source"][unit_id]["E_ref_main"][dd] = \
                    input_data["REF"][ref_name]["heat_source"][unit_id]["E_ref_max"][dd] * \
                    input_data["REF"][ref_name]["heat_source"][unit_id]["coeff_x"][dd] * \
                    input_data["REF"][ref_name]["heat_source"][unit_id]["coeff_tw"][dd]

            ## 補機電力
            # 一台あたりの負荷率（熱源機器の負荷率＝最大能力を考慮した負荷率・ただし、熱源特性の上限・下限は考慮せず）
            aveLperU = result_json["REF"][ref_name]["load_ratio"][dd]

            # 過負荷の場合は 平均負荷率＝1.2 とする。
            if iL == divL - 1:
                aveLperU = 1.2

            # 発電機能付きの熱源機器が1台でもある場合
            if input_data["REF"][ref_name]["checkGEGHP"] == 1:

                for unit_id in range(0, int(result_json["REF"][ref_name]["num_of_operation"][dd])):

                    if "消費電力自給装置" in input_data["REF"][ref_name]["heat_source"][unit_id]["heat_source_type"]:

                        # 非発電時の消費電力 [kW]
                        if input_data["REF"][ref_name]["mode"] == "cooling":
                            E_nonGE = input_data["REF"][ref_name]["heat_source"][unit_id][
                                          "heat_source_rated_capacity_total"] * 0.017
                        elif input_data["REF"][ref_name]["mode"] == "heating":
                            E_nonGE = input_data["REF"][ref_name]["heat_source"][unit_id][
                                          "heat_source_rated_capacity_total"] * 0.012

                        E_GEkW = input_data["REF"][ref_name]["heat_source"][unit_id][
                            "heat_source_sub_rated_power_consumption_total"]  # 発電時の消費電力 [kW]

                        if aveLperU <= 0.3:
                            result_json["REF"][ref_name]["E_ref_sub"][dd] += (
                                    0.3 * E_nonGE - (E_nonGE - E_GEkW) * aveLperU)
                        else:
                            result_json["REF"][ref_name]["E_ref_sub"][dd] += (aveLperU * E_GEkW)

                    else:

                        if aveLperU <= 0.3:
                            result_json["REF"][ref_name]["E_ref_sub"][dd] += 0.3 * \
                                                                            input_data["REF"][ref_name]["heat_source"][
                                                                                unit_id][
                                                                                "heat_source_sub_rated_power_consumption_total"]
                        else:
                            result_json["REF"][ref_name]["E_ref_sub"][dd] += aveLperU * \
                                                                            input_data["REF"][ref_name]["heat_source"][
                                                                                unit_id][
                                                                                "heat_source_sub_rated_power_consumption_total"]

            else:

                # 負荷に比例させる（発電機能なし）
                refset_SubPower = 0
                for unit_id in range(0, int(result_json["REF"][ref_name]["num_of_operation"][dd])):
                    if input_data["REF"][ref_name]["heat_source"][unit_id]["heat_source_rated_fuel_consumption_total"] > 0:
                        refset_SubPower += input_data["REF"][ref_name]["heat_source"][unit_id][
                            "heat_source_sub_rated_power_consumption_total"]

                if aveLperU <= 0.3:
                    result_json["REF"][ref_name]["E_ref_sub"][dd] += 0.3 * refset_SubPower
                else:
                    result_json["REF"][ref_name]["E_ref_sub"][dd] += aveLperU * refset_SubPower

            # 一次ポンプ
            for unit_id in range(0, int(result_json["REF"][ref_name]["num_of_operation"][dd])):
                result_json["REF"][ref_name]["E_ref_pri_pump"][dd] += \
                    input_data["REF"][ref_name]["heat_source"][unit_id]["primary_pump_power_consumption_total"]

            # 冷却塔ファン
            for unit_id in range(0, int(result_json["REF"][ref_name]["num_of_operation"][dd])):
                result_json["REF"][ref_name]["E_ref_ct_fan"][dd] += \
                    input_data["REF"][ref_name]["heat_source"][unit_id]["cooling_tower_fan_power_consumption_total"]

            # 冷却水ポンプ
            if input_data["REF"][ref_name]["checkCTVWV"] == 1:  # 変流量制御がある場合

                for unit_id in range(0, int(result_json["REF"][ref_name]["num_of_operation"][dd])):

                    if "冷却水変流量" in input_data["REF"][ref_name]["heat_source"][unit_id]["heat_source_type"]:

                        if aveLperU <= 0.5:
                            result_json["REF"][ref_name]["E_ref_ct_pump"][dd] += \
                                0.5 * input_data["REF"][ref_name]["heat_source"][unit_id][
                                    "cooling_tower_pump_power_consumption_total"]
                        else:
                            result_json["REF"][ref_name]["E_ref_ct_pump"][dd] += \
                                aveLperU * input_data["REF"][ref_name]["heat_source"][unit_id][
                                    "cooling_tower_pump_power_consumption_total"]
                    else:
                        result_json["REF"][ref_name]["E_ref_ct_pump"][dd] += \
                            input_data["REF"][ref_name]["heat_source"][unit_id]["cooling_tower_pump_power_consumption_total"]

            else:

                for unit_id in range(0, int(result_json["REF"][ref_name]["num_of_operation"][dd])):
                    result_json["REF"][ref_name]["E_ref_ct_pump"][dd] += \
                        input_data["REF"][ref_name]["heat_source"][unit_id]["cooling_tower_pump_power_consumption_total"]

    ##----------------------------------------------------------------------------------
    ## 熱源群の一次エネルギー消費量および消費電力（解説書 2.7.17）
    ##----------------------------------------------------------------------------------

    for ref_name in input_data["REF"]:

        for dd in range(0, 365):

            if result_json["REF"][ref_name]["Tref"][dd] == 0:

                result_json["REF"][ref_name]["E_ref_day"][dd] = 0  # 熱源主機エネルギー消費量 [MJ]
                result_json["REF"][ref_name]["E_ref_day_MWh"][dd] = 0  # 熱源主機電力消費量 [MWh]
                result_json["REF"][ref_name]["E_ref_ACc_day"][dd] = 0  # 熱源補機電力 [MWh]
                result_json["REF"][ref_name]["E_PPc_day"][dd] = 0  # 一次ポンプ電力 [MWh]
                result_json["REF"][ref_name]["E_CTfan_day"][dd] = 0  # 冷却塔ファン電力 [MWh]
                result_json["REF"][ref_name]["E_CTpump_day"][dd] = 0  # 冷却水ポンプ電力 [MWh]

            else:

                # 熱源主機 [MJ/day]
                for unit_id in range(0, len(input_data["REF"][ref_name]["heat_source"])):

                    result_json["REF"][ref_name]["E_ref_day"][dd] += \
                        result_json["REF"][ref_name]["heat_source"][unit_id]["E_ref_main"][dd] * 3600 / 1000 * \
                        result_json["REF"][ref_name]["Tref"][dd]

                    # CGSの計算用に機種別に一次エネルギー消費量を積算 [MJ/day]
                    result_json["REF"][ref_name]["heat_source"][unit_id]["E_ref_day_per_unit"][dd] = \
                        result_json["REF"][ref_name]["heat_source"][unit_id]["E_ref_main"][dd] * 3600 / 1000 * \
                        result_json["REF"][ref_name]["Tref"][dd]

                    # CGSの計算用に電力のみ積算 [MWh]
                    if input_data["REF"][ref_name]["heat_source"][unit_id][
                        "refInputtype"] == 1:  # 燃料種類が「電力」であれば、CGS計算用に集計を行う。

                        result_json["REF"][ref_name]["E_ref_day_MWh"][dd] += \
                            result_json["REF"][ref_name]["heat_source"][unit_id]["E_ref_main"][dd] * 3600 / 1000 * \
                            result_json["REF"][ref_name]["Tref"][dd] / bc.fprime

                        result_json["REF"][ref_name]["heat_source"][unit_id]["E_ref_day_per_unit_MWh"][dd] = \
                            result_json["REF"][ref_name]["heat_source"][unit_id]["E_ref_main"][dd] * 3600 / 1000 * \
                            result_json["REF"][ref_name]["Tref"][dd] / bc.fprime

                # 補機電力 [MWh]
                result_json["REF"][ref_name]["E_ref_ACc_day"][dd] += \
                    result_json["REF"][ref_name]["E_ref_sub"][dd] / 1000 * result_json["REF"][ref_name]["Tref"][dd]

                # 一次ポンプ電力 [MWh]
                result_json["REF"][ref_name]["E_PPc_day"][dd] += \
                    result_json["REF"][ref_name]["E_ref_pri_pump"][dd] / 1000 * result_json["REF"][ref_name]["Tref"][dd]

                # 冷却塔ファン電力 [MWh]
                result_json["REF"][ref_name]["E_CTfan_day"][dd] += \
                    result_json["REF"][ref_name]["E_ref_ct_fan"][dd] / 1000 * result_json["REF"][ref_name]["Tref"][dd]

                # 冷却水ポンプ電力 [MWh]
                result_json["REF"][ref_name]["E_CTpump_day"][dd] += \
                    result_json["REF"][ref_name]["E_ref_ct_pump"][dd] / 1000 * result_json["REF"][ref_name]["Tref"][dd]

        if debug:  # pragma: no cover

            print(f'--- 熱源群名 {ref_name} ---')
            print(f'熱源主機のエネルギー消費量 E_ref_day: {np.sum(result_json["REF"][ref_name]["E_ref_day"])}')
            print(f'熱源補機の消費電力 E_ref_ACc_day: {np.sum(result_json["REF"][ref_name]["E_ref_ACc_day"])}')
            print(f'一次ポンプの消費電力 E_PPc_day: {np.sum(result_json["REF"][ref_name]["E_PPc_day"])}')
            print(f'冷却塔ファンの消費電力 E_CTfan_day: {np.sum(result_json["REF"][ref_name]["E_CTfan_day"])}')
            print(f'冷却塔ポンプの消費電力 E_CTpump_day: {np.sum(result_json["REF"][ref_name]["E_CTpump_day"])}')

    ##----------------------------------------------------------------------------------
    ## 熱源群のエネルギー消費量（解説書 2.7.18）
    ##----------------------------------------------------------------------------------

    for ref_name in input_data["REF"]:

        result_json["REF"][ref_name]["熱源群熱源主機[MJ]"] = 0
        result_json["REF"][ref_name]["熱源群熱源補機[MWh]"] = 0
        result_json["REF"][ref_name]["熱源群一次ポンプ[MWh]"] = 0
        result_json["REF"][ref_name]["熱源群冷却塔ファン[MWh]"] = 0
        result_json["REF"][ref_name]["熱源群冷却水ポンプ[MWh]"] = 0

        result_json["REF"][ref_name]["熱源群熱源主機[GJ]"] = 0
        result_json["REF"][ref_name]["熱源群熱源補機[GJ]"] = 0
        result_json["REF"][ref_name]["熱源群一次ポンプ[GJ]"] = 0
        result_json["REF"][ref_name]["熱源群冷却塔ファン[GJ]"] = 0
        result_json["REF"][ref_name]["熱源群冷却水ポンプ[GJ]"] = 0

        # 熱源主機の電力消費量 [MWh/day]
        result_json["日別エネルギー消費量"]["E_ref_main_MWh_day"] += result_json["REF"][ref_name]["E_ref_day_MWh"]
        # 熱源主機以外の電力消費量 [MWh/day]
        result_json["日別エネルギー消費量"]["E_ref_sub_MWh_day"] += result_json["REF"][ref_name]["E_ref_ACc_day"] \
                                                              + result_json["REF"][ref_name]["E_PPc_day"] + \
                                                              result_json["REF"][ref_name]["E_CTfan_day"] \
                                                              + result_json["REF"][ref_name]["E_CTpump_day"]

        for dd in range(0, 365):
            # 熱源主機のエネルギー消費量 [MJ]
            result_json["REF"][ref_name]["熱源群熱源主機[MJ]"] += result_json["REF"][ref_name]["E_ref_day"][dd]
            # 熱源補機電力消費量 [MWh]
            result_json["REF"][ref_name]["熱源群熱源補機[MWh]"] += result_json["REF"][ref_name]["E_ref_ACc_day"][dd]
            # 一次ポンプ電力消費量 [MWh]
            result_json["REF"][ref_name]["熱源群一次ポンプ[MWh]"] += result_json["REF"][ref_name]["E_PPc_day"][dd]
            # 冷却塔ファン電力消費量 [MWh]
            result_json["REF"][ref_name]["熱源群冷却塔ファン[MWh]"] += result_json["REF"][ref_name]["E_CTfan_day"][dd]
            # 冷却水ポンプ電力消費量 [MWh]
            result_json["REF"][ref_name]["熱源群冷却水ポンプ[MWh]"] += result_json["REF"][ref_name]["E_CTpump_day"][dd]

        result_json["REF"][ref_name]["熱源群熱源主機[GJ]"] = result_json["REF"][ref_name]["熱源群熱源主機[MJ]"] / 1000
        result_json["REF"][ref_name]["熱源群熱源補機[GJ]"] = result_json["REF"][ref_name][
                                                                "熱源群熱源補機[MWh]"] * bc.fprime / 1000
        result_json["REF"][ref_name]["熱源群一次ポンプ[GJ]"] = result_json["REF"][ref_name][
                                                               "熱源群一次ポンプ[MWh]"] * bc.fprime / 1000
        result_json["REF"][ref_name]["熱源群冷却塔ファン[GJ]"] = result_json["REF"][ref_name][
                                                                 "熱源群冷却塔ファン[MWh]"] * bc.fprime / 1000
        result_json["REF"][ref_name]["熱源群冷却水ポンプ[GJ]"] = result_json["REF"][ref_name][
                                                                 "熱源群冷却水ポンプ[MWh]"] * bc.fprime / 1000

        # 建物全体
        result_json["年間エネルギー消費量"]["熱源群熱源主機[MJ]"] += result_json["REF"][ref_name]["熱源群熱源主機[MJ]"]
        result_json["年間エネルギー消費量"]["熱源群熱源補機[MWh]"] += result_json["REF"][ref_name]["熱源群熱源補機[MWh]"]
        result_json["年間エネルギー消費量"]["熱源群一次ポンプ[MWh]"] += result_json["REF"][ref_name]["熱源群一次ポンプ[MWh]"]
        result_json["年間エネルギー消費量"]["熱源群冷却塔ファン[MWh]"] += result_json["REF"][ref_name]["熱源群冷却塔ファン[MWh]"]
        result_json["年間エネルギー消費量"]["熱源群冷却水ポンプ[MWh]"] += result_json["REF"][ref_name]["熱源群冷却水ポンプ[MWh]"]

        result_json["年間エネルギー消費量"]["熱源群熱源主機[GJ]"] += result_json["REF"][ref_name]["熱源群熱源主機[GJ]"]
        result_json["年間エネルギー消費量"]["熱源群熱源補機[GJ]"] += result_json["REF"][ref_name]["熱源群熱源補機[GJ]"]
        result_json["年間エネルギー消費量"]["熱源群一次ポンプ[GJ]"] += result_json["REF"][ref_name]["熱源群一次ポンプ[GJ]"]
        result_json["年間エネルギー消費量"]["熱源群冷却塔ファン[GJ]"] += result_json["REF"][ref_name]["熱源群冷却塔ファン[GJ]"]
        result_json["年間エネルギー消費量"]["熱源群冷却水ポンプ[GJ]"] += result_json["REF"][ref_name]["熱源群冷却水ポンプ[GJ]"]

    print('熱源エネルギー計算完了')

    if debug:  # pragma: no cover

        print(f'熱源主機エネルギー消費量 : {result_json["年間エネルギー消費量"]["熱源群熱源主機[MJ]"]} MJ')
        print(f'熱源補機電力消費量 : {result_json["年間エネルギー消費量"]["熱源群熱源補機[MWh]"]} MWh')
        print(f'一次ポンプ電力消費量 : {result_json["年間エネルギー消費量"]["熱源群一次ポンプ[MWh]"]} MWh')
        print(f'冷却塔ファン電力消費量 : {result_json["年間エネルギー消費量"]["熱源群冷却塔ファン[MWh]"]} MWh')
        print(f'冷却水ポンプ電力消費量 : {result_json["年間エネルギー消費量"]["熱源群冷却水ポンプ[MWh]"]} MWh')

    ##----------------------------------------------------------------------------------
    ## 熱源群計算結果の集約
    ##----------------------------------------------------------------------------------

    for ref_name in input_data["REF"]:

        if input_data["REF"][ref_name]["mode"] == "cooling":
            result_json["REF"][ref_name]["運転モード"] = "冷房"
        elif input_data["REF"][ref_name]["mode"] == "heating":
            result_json["REF"][ref_name]["運転モード"] = "暖房"
        else:
            raise Exception("運転モードが不正です")

        result_json["REF"][ref_name]["定格能力[kW]"] = input_data["REF"][ref_name]["Qref_rated"]
        result_json["REF"][ref_name]["熱源主機_定格消費エネルギー[kW]"] = input_data["REF"][ref_name]["Eref_rated_primary"]
        result_json["REF"][ref_name]["年間運転時間[時間]"] = np.sum(result_json["REF"][ref_name]["Tref"])
        result_json["REF"][ref_name]["年積算熱源負荷[GJ]"] = np.sum(result_json["REF"][ref_name]["Qref"]) / 1000
        result_json["REF"][ref_name]["年積算過負荷[GJ]"] = np.sum(result_json["REF"][ref_name]["Qref_OVER"]) / 1000
        result_json["REF"][ref_name]["年積算エネルギー消費量[GJ]"] = \
            result_json["REF"][ref_name]["熱源群熱源主機[GJ]"] \
            + result_json["REF"][ref_name]["熱源群熱源補機[GJ]"] \
            + result_json["REF"][ref_name]["熱源群一次ポンプ[GJ]"] \
            + result_json["REF"][ref_name]["熱源群冷却塔ファン[GJ]"] \
            + result_json["REF"][ref_name]["熱源群冷却水ポンプ[GJ]"] \
 \
                result_json["REF"][ref_name]["年間平均負荷率[-]"] = \
                    (result_json["REF"][ref_name]["年積算熱源負荷[GJ]"] * 1000000 / (
                            result_json["REF"][ref_name]["年間運転時間[時間]"] * 3600)) \
                    / result_json["REF"][ref_name]["熱源主機_定格消費エネルギー[kW]"]

        result_json["REF"][ref_name]["年間運転効率[-]"] = \
            result_json["REF"][ref_name]["年積算熱源負荷[GJ]"] \
            / result_json["REF"][ref_name]["年積算エネルギー消費量[GJ]"]

    ##----------------------------------------------------------------------------------
    ## 設計一次エネルギー消費量（解説書 2.8）
    ##----------------------------------------------------------------------------------

    result_json["設計一次エネルギー消費量[MJ/年]"] = \
        + result_json["年間エネルギー消費量"]["空調機群ファン[GJ]"] * 1000 \
        + result_json["年間エネルギー消費量"]["空調機群全熱交換器[GJ]"] * 1000 \
        + result_json["年間エネルギー消費量"]["二次ポンプ群[GJ]"] * 1000 \
        + result_json["年間エネルギー消費量"]["熱源群熱源主機[GJ]"] * 1000 \
        + result_json["年間エネルギー消費量"]["熱源群熱源補機[GJ]"] * 1000 \
        + result_json["年間エネルギー消費量"]["熱源群一次ポンプ[GJ]"] * 1000 \
        + result_json["年間エネルギー消費量"]["熱源群冷却塔ファン[GJ]"] * 1000 \
        + result_json["年間エネルギー消費量"]["熱源群冷却水ポンプ[GJ]"] * 1000

    ##----------------------------------------------------------------------------------
    ## 基準一次エネルギー消費量 （解説書 10.1）
    ##----------------------------------------------------------------------------------    
    for room_zone_name in input_data["air_conditioning_zone"]:
        # 建物用途・室用途、ゾーン面積等の取得
        building_type = input_data["rooms"][room_zone_name]["building_type"]
        room_type = input_data["rooms"][room_zone_name]["room_type"]
        zone_area = input_data["rooms"][room_zone_name]["room_area"]

        result_json["計算対象面積"] += zone_area
        result_json["基準一次エネルギー消費量[MJ/年]"] += \
            bc.room_standard_value[building_type][room_type]["空調"][input_data["building"]["region"] + "地域"] * zone_area

    # BEI/ACの算出
    result_json["BEI/AC"] = result_json["設計一次エネルギー消費量[MJ/年]"] / result_json["基準一次エネルギー消費量[MJ/年]"]
    result_json["BEI/AC"] = math.ceil(result_json["BEI/AC"] * 100) / 100

    result_json["設計一次エネルギー消費量[GJ/年]"] = result_json["設計一次エネルギー消費量[MJ/年]"] / 1000
    result_json["基準一次エネルギー消費量[GJ/年]"] = result_json["基準一次エネルギー消費量[MJ/年]"] / 1000
    result_json["設計一次エネルギー消費量[MJ/m2年]"] = result_json["設計一次エネルギー消費量[MJ/年]"] / result_json["計算対象面積"]
    result_json["基準一次エネルギー消費量[MJ/m2年]"] = result_json["基準一次エネルギー消費量[MJ/年]"] / result_json["計算対象面積"]

    if debug:  # pragma: no cover
        print(f'空調設備の設計一次エネルギー消費量 MJ/m2 : {result_json["設計一次エネルギー消費量[MJ/m2年]"]}')
        print(f'空調設備の設計一次エネルギー消費量 MJ : {result_json["設計一次エネルギー消費量[MJ/年]"]}')
        print(f'空調設備の基準一次エネルギー消費量 MJ/m2 : {result_json["基準一次エネルギー消費量[MJ/m2年]"]}')
        print(f'空調設備の基準一次エネルギー消費量 MJ : {result_json["基準一次エネルギー消費量[MJ/年]"]}')

    ##----------------------------------------------------------------------------------
    ## CGS計算用変数 （解説書 ８章 附属書 G.10 他の設備の計算結果の読み込み）
    ##----------------------------------------------------------------------------------    

    if len(input_data["cogeneration_systems"]) == 1:  # コジェネがあれば実行

        for cgs_name in input_data["cogeneration_systems"]:

            # 排熱を冷房に使用するか否か
            if input_data["cogeneration_systems"][cgs_name]["cooling_system"] == None:
                cgs_cooling = False
            else:
                cgs_cooling = True

            # 排熱を暖房に使用するか否か
            if input_data["cogeneration_systems"][cgs_name]["heating_system"] == None:
                cgs_heating = False
            else:
                cgs_heating = True

            # 排熱利用機器（冷房）
            if cgs_cooling:
                result_json["for_CGS"]["CGS_refname_C"] = input_data["cogeneration_systems"][cgs_name][
                                                             "cooling_system"] + "_冷房"
            else:
                result_json["for_CGS"]["CGS_refname_C"] = None

            # 排熱利用機器（暖房）
            if cgs_heating:
                result_json["for_CGS"]["CGS_refname_H"] = input_data["cogeneration_systems"][cgs_name][
                                                             "heating_system"] + "_暖房"
            else:
                result_json["for_CGS"]["CGS_refname_H"] = None

        # 熱源主機の電力消費量 [MWh/day]
        result_json["for_CGS"]["E_ref_main_MWh_day"] = result_json["日別エネルギー消費量"][
            "E_ref_main_MWh_day"]  # 後半でCGSから排熱供給を受ける熱源群の電力消費量を差し引く。

        # 熱源補機の電力消費量 [MWh/day]
        result_json["for_CGS"]["E_ref_sub_MWh_day"] = result_json["日別エネルギー消費量"]["E_ref_sub_MWh_day"]

        # 二次ポンプ群の電力消費量 [MWh/day]
        result_json["for_CGS"]["E_pump_MWh_day"] = result_json["日別エネルギー消費量"]["E_pump_MWh_day"]

        # 空調機群の電力消費量 [MWh/day]
        result_json["for_CGS"]["E_fan_MWh_day"] = result_json["日別エネルギー消費量"]["E_fan_MWh_day"]

        ## 排熱利用熱源系統
        result_json["for_CGS"]["E_ref_cgsC_ABS_day"] = np.zeros(365)
        result_json["for_CGS"]["Lt_ref_cgsC_day"] = np.zeros(365)
        result_json["for_CGS"]["E_ref_cgsH_day"] = np.zeros(365)
        result_json["for_CGS"]["Q_ref_cgsH_day"] = np.zeros(365)
        result_json["for_CGS"]["T_ref_cgsC_day"] = np.zeros(365)
        result_json["for_CGS"]["T_ref_cgsH_day"] = np.zeros(365)
        result_json["for_CGS"]["NAC_ref_link"] = 0
        result_json["for_CGS"]["qAC_link_c_j_rated"] = 0
        result_json["for_CGS"]["EAC_link_c_j_rated"] = 0

        for ref_name in input_data["REF"]:

            # CGS系統の「排熱利用する冷熱源」　。　蓄熱がある場合は「追い掛け運転」を採用（2020/7/6変更）
            if ref_name == result_json["for_CGS"]["CGS_refname_C"]:

                for unit_id, unit_configure in enumerate(input_data["REF"][ref_name]["heat_source"]):

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
                        result_json["for_CGS"]["E_ref_cgsC_ABS_day"] += \
                            result_json["REF"][ref_name]["heat_source"][unit_id]["E_ref_day_per_unit"]

                        # 排熱投入型吸収式冷温水機jの定格冷却能力
                        result_json["for_CGS"]["qAC_link_c_j_rated"] += \
                            input_data["REF"][ref_name]["heat_source"][unit_id]["heat_source_rated_capacity_total"]

                        # 排熱投入型吸収式冷温水機jの主機定格消費エネルギー
                        result_json["for_CGS"]["EAC_link_c_j_rated"] += \
                            input_data["REF"][ref_name]["heat_source"][unit_id]["heat_source_rated_fuel_consumption_total"]

                        result_json["for_CGS"]["NAC_ref_link"] += 1

                # CGSの排熱利用が可能な排熱投入型吸収式冷温水機(系統)の冷熱源としての負荷率 [-]
                for dd in range(0, 365):

                    if result_json["REF"][ref_name]["Tref"][dd] == 0:
                        result_json["for_CGS"]["Lt_ref_cgsC_day"][dd] = 0
                    elif result_json["REF"][ref_name]["matrix_iL"][dd] == 11:
                        result_json["for_CGS"]["Lt_ref_cgsC_day"][dd] = 1.2
                    else:
                        result_json["for_CGS"]["Lt_ref_cgsC_day"][dd] = round(
                            0.1 * result_json["REF"][ref_name]["matrix_iL"][dd] - 0.05, 2)

                # CGSの排熱利用が可能な排熱投入型吸収式冷温水機(系統)の運転時間 [h/日]
                result_json["for_CGS"]["T_ref_cgsC_day"] = result_json["REF"][ref_name]["Tref"]

            # CGS系統の「排熱利用する温熱源」
            if ref_name == result_json["for_CGS"]["CGS_refname_H"]:

                # 当該温熱源群の主機の消費電力を差し引く。
                for unit_id, unit_configure in enumerate(input_data["REF"][ref_name]["heat_source"]):
                    result_json["for_CGS"]["E_ref_main_MWh_day"] -= result_json["REF"][ref_name]["heat_source"][unit_id][
                        "E_ref_day_per_unit_MWh"]

                # CGSの排熱利用が可能な温熱源群の主機の一次エネルギー消費量 [MJ/日]
                result_json["for_CGS"]["E_ref_cgsH_day"] = result_json["REF"][ref_name]["E_ref_day"]

                # CGSの排熱利用が可能な温熱源群の熱源負荷 [MJ/日]
                result_json["for_CGS"]["Q_ref_cgsH_day"] = result_json["REF"][ref_name]["Qref"]

                # CGSの排熱利用が可能な温熱源群の運転時間 [h/日]
                result_json["for_CGS"]["T_ref_cgsH_day"] = result_json["REF"][ref_name]["Tref"]

        # 空気調和設備の電力消費量 [MWh/day]
        result_json["for_CGS"]["electric_power_consumption"] = \
            + result_json["for_CGS"]["E_ref_main_MWh_day"] \
            + result_json["for_CGS"]["E_ref_sub_MWh_day"] \
            + result_json["for_CGS"]["E_pump_MWh_day"] \
            + result_json["for_CGS"]["E_fan_MWh_day"]

    # with open("input_dataJson_AC.json",'w', encoding='utf-8') as fw:
    #     json.dump(input_data, fw, indent=4, ensure_ascii=False, cls = bc.MyEncoder)

    ##----------------------------------------------------------------------------------
    # 不要な要素を削除
    ##----------------------------------------------------------------------------------

    for room_zone_name in result_json["q_room"]:
        del result_json["q_room"][room_zone_name]["q_wall_temperature"]
        del result_json["q_room"][room_zone_name]["q_wall_solar"]
        del result_json["q_room"][room_zone_name]["q_wall_night"]
        del result_json["q_room"][room_zone_name]["q_window_temperature"]
        del result_json["q_room"][room_zone_name]["q_window_solar"]
        del result_json["q_room"][room_zone_name]["q_window_night"]
        del result_json["q_room"][room_zone_name]["q_room_daily_cooling"]
        del result_json["q_room"][room_zone_name]["q_room_daily_heating"]
        del result_json["q_room"][room_zone_name]["q_room_hourly_cooling"]
        del result_json["q_room"][room_zone_name]["q_room_hourly_heating"]

    for ahu_name in result_json["AHU"]:
        del result_json["AHU"][ahu_name]["schedule"]
        del result_json["AHU"][ahu_name]["HoaDayAve"]
        del result_json["AHU"][ahu_name]["qoaAHU"]
        del result_json["AHU"][ahu_name]["Tahu_total"]
        del result_json["AHU"][ahu_name]["E_fan_day"]
        del result_json["AHU"][ahu_name]["E_fan_c_day"]
        del result_json["AHU"][ahu_name]["E_fan_h_day"]
        del result_json["AHU"][ahu_name]["E_AHUaex_day"]
        del result_json["AHU"][ahu_name]["TdAHUc_total"]
        del result_json["AHU"][ahu_name]["TdAHUh_total"]
        del result_json["AHU"][ahu_name]["Qahu_remainC"]
        del result_json["AHU"][ahu_name]["Qahu_remainH"]
        del result_json["AHU"][ahu_name]["energy_consumption_each_LF"]
        del result_json["AHU"][ahu_name]["q_room"]
        del result_json["AHU"][ahu_name]["Qahu"]
        del result_json["AHU"][ahu_name]["Tahu"]
        del result_json["AHU"][ahu_name]["Economizer"]
        del result_json["AHU"][ahu_name]["LdAHUc"]
        del result_json["AHU"][ahu_name]["TdAHUc"]
        del result_json["AHU"][ahu_name]["LdAHUh"]
        del result_json["AHU"][ahu_name]["TdAHUh"]

    dummypumplist = []
    for pump_name in result_json["PUMP"]:
        if pump_name.startswith("dummyPump"):
            dummypumplist.append(pump_name)

    for pump_name in dummypumplist:
        del result_json["PUMP"][pump_name]

    for pump_name in result_json["PUMP"]:
        del result_json["PUMP"][pump_name]["Qpsahu_fan"]
        del result_json["PUMP"][pump_name]["pumpTime_Start"]
        del result_json["PUMP"][pump_name]["pumpTime_Stop"]
        del result_json["PUMP"][pump_name]["Qps"]
        del result_json["PUMP"][pump_name]["Tps"]
        del result_json["PUMP"][pump_name]["schedule"]
        del result_json["PUMP"][pump_name]["LdPUMP"]
        del result_json["PUMP"][pump_name]["TdPUMP"]
        del result_json["PUMP"][pump_name]["Qpsahu_pump"]
        del result_json["PUMP"][pump_name]["MxPUMPNum"]
        del result_json["PUMP"][pump_name]["MxPUMPPower"]
        del result_json["PUMP"][pump_name]["E_pump_day"]

    for ref_name in result_json["REF"]:
        del result_json["REF"][ref_name]["schedule"]
        del result_json["REF"][ref_name]["ghsp_Rq"]
        del result_json["REF"][ref_name]["Qref_thermal_loss"]
        del result_json["REF"][ref_name]["Qref"]
        del result_json["REF"][ref_name]["Tref"]
        del result_json["REF"][ref_name]["Qref_kW"]
        del result_json["REF"][ref_name]["Qref_OVER"]
        del result_json["REF"][ref_name]["E_ref_day"]
        del result_json["REF"][ref_name]["E_ref_day_MWh"]
        del result_json["REF"][ref_name]["E_ref_ACc_day"]
        del result_json["REF"][ref_name]["E_PPc_day"]
        del result_json["REF"][ref_name]["E_CTfan_day"]
        del result_json["REF"][ref_name]["E_CTpump_day"]
        del result_json["REF"][ref_name]["heat_source"]
        del result_json["REF"][ref_name]["Lref"]
        del result_json["REF"][ref_name]["matrix_iL"]
        del result_json["REF"][ref_name]["matrix_iT"]
        del result_json["REF"][ref_name]["num_of_operation"]
        del result_json["REF"][ref_name]["load_ratio"]
        del result_json["REF"][ref_name]["hoseiStorage"]
        del result_json["REF"][ref_name]["E_ref_sub"]
        del result_json["REF"][ref_name]["E_ref_pri_pump"]
        del result_json["REF"][ref_name]["E_ref_ct_fan"]
        del result_json["REF"][ref_name]["E_ref_ct_pump"]

    del result_json["Matrix"]
    del result_json["日別エネルギー消費量"]

    return result_json


if __name__ == '__main__':  # pragma: no cover

    print('----- airconditioning.py -----')
    # filename = './sample/ACtest_Case001.json'
    # filename = './sample/Builelib_sample_SP1_input.json'
    # filename = './sample/WEBPRO_inputSheet_sample.json'
    # filename = './sample/Builelib_sample_SP10.json'
    # filename = './sample/WEBPRO_KE14_Case01.json'
    filename = './sample/sample01_WEBPRO_inputSheet_for_Ver3.6.json'
    # filename = './tests/cogeneration/Case_hospital_00.json'
    # filename = './tests/airconditioning_heatsoucetemp/airconditioning_heatsoucetemp_area_6.json'
    # filename = "./tests/airconditioning_gshp_openloop/AC_gshp_closeloop_Case001.json"

    # 入力ファイルの読み込み
    with open(filename, 'r', encoding='utf-8') as f:
        input_data = json.load(f)

    result_json = calc_energy(input_data, debug=True)

    with open("result_json_AC.json", 'w', encoding='utf-8') as fw:
        json.dump(result_json, fw, indent=4, ensure_ascii=False, cls=bc.MyEncoder)

    print(f'BEI/AC: {result_json["BEI/AC"]}')
    print(f'設計一次エネルギー消費量 全体: {result_json["設計一次エネルギー消費量[GJ/年]"]} GJ')
    print(f'設計一次エネルギー消費量 空調ファン: {result_json["年間エネルギー消費量"]["空調機群ファン[GJ]"]} GJ')
    print(f'設計一次エネルギー消費量 空調全熱交換器: {result_json["年間エネルギー消費量"]["空調機群全熱交換器[GJ]"]} GJ')
    print(f'設計一次エネルギー消費量 二次ポンプ: {result_json["年間エネルギー消費量"]["二次ポンプ群[GJ]"]} GJ')
    print(f'設計一次エネルギー消費量 熱源主機: {result_json["年間エネルギー消費量"]["熱源群熱源主機[GJ]"]} GJ')
    print(f'設計一次エネルギー消費量 熱源補機: {result_json["年間エネルギー消費量"]["熱源群熱源補機[GJ]"]} GJ')
    print(f'設計一次エネルギー消費量 一次ポンプ: {result_json["年間エネルギー消費量"]["熱源群一次ポンプ[GJ]"]} GJ')
    print(f'設計一次エネルギー消費量 冷却塔ファン: {result_json["年間エネルギー消費量"]["熱源群冷却塔ファン[GJ]"]} GJ')
    print(f'設計一次エネルギー消費量 冷却水ポンプ: {result_json["年間エネルギー消費量"]["熱源群冷却水ポンプ[GJ]"]} GJ')

    # デバッグ用
    # print( f'{result_json["設計一次エネルギー消費量[MJ/年]"]}, {result_json["ENERGY"]["E_fan"] * bc.fprime}, {result_json["ENERGY"]["E_aex"] * bc.fprime}, {result_json["ENERGY"]["E_pump"] * bc.fprime}, {result_json["ENERGY"]["E_refsysr"]}, {result_json["ENERGY"]["E_refac"] * bc.fprime}, {result_json["ENERGY"]["E_pumpP"] * bc.fprime}, {result_json["ENERGY"]["E_ctfan"] * bc.fprime}, {result_json["ENERGY"]["E_ctpump"] * bc.fprime}')

    # for ref_name in input_data["REF"]:
    #     print( f'--- 熱源群名 {ref_name} ---')
    #     print( f'熱源群の熱源負荷 Qref: {np.sum(result_json["REF"][ref_name]["Qref"],0)}' )

    print(f'設計一次エネルギー消費量 全体: {result_json["設計一次エネルギー消費量[MJ/年]"]}')
