import json
import numpy as np
import math
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import commons as bc
import climate
import shading
import make_figure as mf

# データベースファイルの保存場所
database_directory = os.path.dirname(os.path.abspath(__file__)) + "/database/"
# 気象データファイルの保存場所
climatedata_directory = os.path.dirname(os.path.abspath(__file__)) + "/climatedata/"

# builelibモードかどうか（照明との連成）
BUILELIB_MODE = True


def calc_energy(inputdata, debug=False):

    inputdata["PUMP"] = {}
    inputdata["REF"] = {}

    #----------------------------------------------------------------------------------
    # 定数の設定
    #----------------------------------------------------------------------------------
    k_heatup = 0.84  # ファン・ポンプの発熱比率 [-]
    k_heatloss = 0.03  # 蓄熱槽の熱ロス [-]
    Cw = 4.186  # 水の比熱 [kJ/kg・K]

    #----------------------------------------------------------------------------------
    # 結果格納用の変数 resultJson
    #----------------------------------------------------------------------------------

    resultJson = {

        "E_ac": 0,  # 空気調和設備の設計一次エネルギー消費量 [MJ]
        "Es_ac": 0,  # 空気調和設備の基準一次エネルギー消費量 [MJ]
        "BEI/AC": 0,  # 空気調和設備のBEI/AC [-]
        "energy": {
            "E_ahu_fan": 0,  # 空調機群ファンの電力消費量 [MWh]
            "E_ahu_aex": 0,  # 空調機群全熱交換器の電力消費量 [MWh]
            "E_pump": 0,  # 二次ポンプ群の電力消費量 [MWh]
            "E_ref_main": 0,  # 熱源群主機の一次エネルギー消費量 [MJ]
            "E_ref_sub": 0,  # 熱源群補機の電力消費量 [MWh]
            "E_ref_pump": 0,  # 熱源群一次ポンプの電力消費量 [MWh]
            "E_ref_ct_fan": 0,  # 熱源群冷却塔ファンの電力消費量 [MWh]
            "E_ref_ct_pump": 0,  # 熱源群冷却水ポンプの電力消費量 [MWh]
            "E_fan_MWh_day": np.zeros(365),  # 空調機群の電力消費量 [MWh/day]
            "E_pump_MWh_day": np.zeros(365),  # 二次ポンプ群の電力消費量 [MWh/day]
            "E_ref_main_MWh_day": np.zeros(365),  # 熱源主機の電力消費量 [MWh/day]
            "E_ref_sub_MWh_day": np.zeros(365)  # 熱源主機以外の電力消費量 [MWh/day]
        },
        "schedule": {
            "room_temperature_setpoint": np.zeros((365, 24)),  # 室内設定温度
            "room_humidity_setpoint": np.zeros((365, 24)),  # 室内設定湿度
            "room_enthalpy": np.zeros((365, 24)),  # 室内設定エンタルピー
        },
        "climate": {
            "Tout": np.zeros((365, 24)),  # 気象データ（外気温度）
            "Xout": np.zeros((365, 24)),  # 気象データ（絶対湿度）
            "Iod": np.zeros((365, 24)),  # 気象データ（法線面直達日射量 W/m2）
            "Ios": np.zeros((365, 24)),  # 気象データ（水平面天空日射量 W/m2)
            "Inn": np.zeros((365, 24)),  # 気象データ（水平面夜間放射量 W/m2）
            "Tout_daily": np.zeros(365),  # 日平均外気温（地中熱計算用）
            "Tout_wb": np.zeros((365, 24)),  # 外気湿球温度
            "Tct_cooling": np.zeros((365, 24)),  # 日平均外気温
            "Tct_heating": np.zeros((365, 24)),  # 日平均外気温
        },
        "total_area": 0,  # 空調対象面積 [m2]
        "Qroom": {},  # 室負荷の計算結果
        "AHU": {},  # 空調機群の計算結果
        "PUMP": {},  # 二次ポンプ群の計算結果
        "REF": {},  # 熱源群の計算結果

        "for_CGS": {  # コジェネ計算のための計算結果
            "E_ref_cgsC_ABS_day": np.zeros(365),
            "Lt_ref_cgsC_day": np.zeros(365),
            "E_ref_cgsH_day": np.zeros(365),
            "Q_ref_cgsH_day": np.zeros(365),
            "T_ref_cgsC_day": np.zeros(365),
            "T_ref_cgsH_day": np.zeros(365),
            "NAC_ref_link": 0,
            "qAC_link_c_j_rated": 0,
            "EAC_link_c_j_rated": 0
        },
        "inputdata": {}
    }

    #----------------------------------------------------------------------------------
    # 流量制御データベースファイルの読み込み
    #----------------------------------------------------------------------------------

    with open(database_directory + 'FLOWCONTROL.json', 'r', encoding='utf-8') as f:
        FLOWCONTROL = json.load(f)

    # 任意評定用 （SP-1: 流量制御)の入力があれば追加
    if "SpecialInputData" in inputdata:
        if "flow_control" in inputdata["SpecialInputData"]:
            FLOWCONTROL.update(inputdata["SpecialInputData"]["flow_control"])

    #----------------------------------------------------------------------------------
    # 熱源機器特性データベースファイルの読み込み
    #----------------------------------------------------------------------------------

    with open(database_directory + "HeatSourcePerformance.json", 'r', encoding='utf-8') as f:
        HeatSourcePerformance = json.load(f)

    # 任意評定 （SP-2：　熱源機器特性)用の入力があれば追加
    if "SpecialInputData" in inputdata:
        if "heatsource_performance" in inputdata["SpecialInputData"]:
            HeatSourcePerformance.update(inputdata["SpecialInputData"]["heatsource_performance"])

    #----------------------------------------------------------------------------------
    # マトリックスの設定
    #----------------------------------------------------------------------------------

    # 地域別データの読み込み
    with open(database_directory + 'AREA.json', 'r', encoding='utf-8') as f:
        Area = json.load(f)

    #----------------------------------------------------------------------------------
    # 他人から供給された熱の一次エネルギー換算係数（デフォルト）
    #----------------------------------------------------------------------------------

    if inputdata["Building"]["Coefficient_DHC"]["Cooling"] == None:
        inputdata["Building"]["Coefficient_DHC"]["Cooling"] = 1.36

    if inputdata["Building"]["Coefficient_DHC"]["Heating"] == None:
        inputdata["Building"]["Coefficient_DHC"]["Heating"] = 1.36

    #----------------------------------------------------------------------------------
    # 気象データ（解説書 2.2.1）
    # 任意評定 （SP-5: 気象データ)
    #----------------------------------------------------------------------------------

    if "climate_data" in inputdata["SpecialInputData"]:  # 任意入力（SP-5）

        # 外気温 [℃]
        resultJson["climate"]["Tout"] = np.array(inputdata["SpecialInputData"]["climate_data"]["Tout"])
        # 外気湿度 [kg/kgDA]
        resultJson["climate"]["Xout"] = np.array(inputdata["SpecialInputData"]["climate_data"]["Xout"])
        # 法線面直達日射量 [W/m2]
        resultJson["climate"]["Iod"] = np.array(inputdata["SpecialInputData"]["climate_data"]["Iod"])
        # 水平面天空日射量 [W/m2]
        resultJson["climate"]["Ios"] = np.array(inputdata["SpecialInputData"]["climate_data"]["Ios"])
        # 水平面夜間放射量 [W/m2]
        resultJson["climate"]["Inn"] = np.array(inputdata["SpecialInputData"]["climate_data"]["Inn"])

    else:

        # 気象データ（HASP形式）読み込み ＜365×24の行列＞
        [resultJson["climate"]["Tout"], resultJson["climate"]["Xout"],
         resultJson["climate"]["Iod"], resultJson["climate"]["Ios"],
         resultJson["climate"]["Inn"]] = \
            climate.readHaspClimateData(climatedata_directory + "/" + Area[inputdata["Building"]["Region"] + "地域"]["気象データファイル名"])

    #----------------------------------------------------------------------------------
    # 冷暖房期間（解説書 2.2.2）
    #----------------------------------------------------------------------------------

    # 空調運転モード
    with open(database_directory + 'ACoperationMode.json', 'r', encoding='utf-8') as f:
        ACoperationMode = json.load(f)

    # 各日の冷暖房期間の種類（冷房期、暖房期、中間期）（365×1の行列）
    ac_mode = ACoperationMode[Area[inputdata["Building"]["Region"] + "地域"]["空調運転モードタイプ"]]

    #----------------------------------------------------------------------------------
    # 平均外気温（解説書 2.2.3）
    #----------------------------------------------------------------------------------

    # 日平均外気温[℃]（365×1）
    resultJson["climate"]["Tout_daily"] = np.mean(resultJson["climate"]["Tout"], 1)

    #----------------------------------------------------------------------------------
    # 外気エンタルピー（解説書 2.2.4）
    #----------------------------------------------------------------------------------

    Hoa_hourly = bc.trans_8760to36524(
        bc.air_enthalpy(
            bc.trans_36524to8760(resultJson["climate"]["Tout"]),
            bc.trans_36524to8760(resultJson["climate"]["Xout"])
        )
    )

    #----------------------------------------------------------------------------------
    # 空調室の設定温度、室内エンタルピー（解説書 2.3.1、2.3.2）
    #----------------------------------------------------------------------------------

    for dd in range(0, 365):
        for hh in range(0, 24):

            if ac_mode[dd] == "冷房":
                resultJson["schedule"]["room_temperature_setpoint"][dd][hh] = 26
                resultJson["schedule"]["room_humidity_setpoint"][dd][hh] = 50
                resultJson["schedule"]["room_enthalpy"][dd][hh] = 52.91

            elif ac_mode[dd] == "中間":
                resultJson["schedule"]["room_temperature_setpoint"][dd][hh] = 24
                resultJson["schedule"]["room_humidity_setpoint"][dd][hh] = 50
                resultJson["schedule"]["room_enthalpy"][dd][hh] = 47.81

            elif ac_mode[dd] == "暖房":
                resultJson["schedule"]["room_temperature_setpoint"][dd][hh] = 22
                resultJson["schedule"]["room_humidity_setpoint"][dd][hh] = 40
                resultJson["schedule"]["room_enthalpy"][dd][hh] = 38.81

    #----------------------------------------------------------------------------------
    # 任意評定 （SP-6: カレンダーパターン)
    #----------------------------------------------------------------------------------

    input_calendar = []
    if "calender" in inputdata["SpecialInputData"]:
        input_calendar = inputdata["SpecialInputData"]["calender"]

    #----------------------------------------------------------------------------------
    # 空調機の稼働状態、内部発熱量（解説書 2.3.3、2.3.4）
    #----------------------------------------------------------------------------------

    roomScheduleRoom = {}
    roomScheduleLight = {}
    roomSchedulePerson = {}
    roomScheduleOAapp = {}
    roomDayMode = {}

    # 空調ゾーン毎にループ
    for room_zone_name in inputdata["AirConditioningZone"]:

        if room_zone_name in inputdata["Rooms"]:  # ゾーン分けがない場合

            # 建物用途・室用途、ゾーン面積等の取得
            inputdata["AirConditioningZone"][room_zone_name]["buildingType"] = inputdata["Rooms"][room_zone_name]["buildingType"]
            inputdata["AirConditioningZone"][room_zone_name]["roomType"] = inputdata["Rooms"][room_zone_name]["roomType"]
            inputdata["AirConditioningZone"][room_zone_name]["zoneArea"] = inputdata["Rooms"][room_zone_name]["roomArea"]
            inputdata["AirConditioningZone"][room_zone_name]["ceilingHeight"] = inputdata["Rooms"][room_zone_name]["ceilingHeight"]

        else:

            # 各室のゾーンを検索
            for room_name in inputdata["Rooms"]:
                if inputdata["Rooms"][room_name]["zone"] != None:  # ゾーンがあれば
                    for zone_name in inputdata["Rooms"][room_name]["zone"]:  # ゾーン名を検索
                        if room_zone_name == (room_name + "_" + zone_name):
                            inputdata["AirConditioningZone"][room_zone_name]["buildingType"] = inputdata["Rooms"][room_name]["buildingType"]
                            inputdata["AirConditioningZone"][room_zone_name]["roomType"] = inputdata["Rooms"][room_name]["roomType"]
                            inputdata["AirConditioningZone"][room_zone_name]["ceilingHeight"] = inputdata["Rooms"][room_name]["ceilingHeight"]
                            inputdata["AirConditioningZone"][room_zone_name]["zoneArea"] = inputdata["Rooms"][room_name]["zone"][zone_name]["zoneArea"]

                            break

        # 365日×24時間分のスケジュール （365×24の行列を格納した dict型）
        roomScheduleRoom[room_zone_name], roomScheduleLight[room_zone_name], roomSchedulePerson[room_zone_name], roomScheduleOAapp[room_zone_name], roomDayMode[room_zone_name] = \
            bc.get_roomUsageSchedule(inputdata["AirConditioningZone"][room_zone_name]["buildingType"], inputdata["AirConditioningZone"][room_zone_name]["roomType"], input_calendar)

        # 空調対象面積の合計
        resultJson["total_area"] += inputdata["AirConditioningZone"][room_zone_name]["zoneArea"]

    #----------------------------------------------------------------------------------
    # 任意評定 （SP-7: 室スケジュール)
    #----------------------------------------------------------------------------------

    if "room_schedule" in inputdata["SpecialInputData"]:

        # 空調ゾーン毎にループ
        for room_zone_name in inputdata["AirConditioningZone"]:

            # SP-7に入力されていれば
            if room_zone_name in inputdata["SpecialInputData"]["room_schedule"]:

                # 使用時間帯
                roomDayMode[room_zone_name] = inputdata["SpecialInputData"]["room_schedule"][room_zone_name]["roomDayMode"]

                if "室の同時使用率" in inputdata["SpecialInputData"]["room_schedule"][room_zone_name]["schedule"]:
                    roomScheduleRoom_tmp = np.array(inputdata["SpecialInputData"]["room_schedule"][room_zone_name]["schedule"]["室の同時使用率"]).astype("float")
                    roomScheduleRoom_tmp = np.where(roomScheduleRoom_tmp < 1, 0, roomScheduleRoom_tmp)  # 同時使用率は考えない
                    roomScheduleRoom[room_zone_name] = roomScheduleRoom_tmp
                if "照明発熱密度比率" in inputdata["SpecialInputData"]["room_schedule"][room_zone_name]["schedule"]:
                    roomScheduleLight[room_zone_name] = np.array(inputdata["SpecialInputData"]["room_schedule"][room_zone_name]["schedule"]["照明発熱密度比率"])
                if "人体発熱密度比率" in inputdata["SpecialInputData"]["room_schedule"][room_zone_name]["schedule"]:
                    roomSchedulePerson[room_zone_name] = np.array(inputdata["SpecialInputData"]["room_schedule"][room_zone_name]["schedule"]["人体発熱密度比率"])
                if "機器発熱密度比率" in inputdata["SpecialInputData"]["room_schedule"][room_zone_name]["schedule"]:
                    roomScheduleOAapp[room_zone_name] = np.array(inputdata["SpecialInputData"]["room_schedule"][room_zone_name]["schedule"]["機器発熱密度比率"])

    #----------------------------------------------------------------------------------
    # 室負荷計算（解説書 2.4）
    #----------------------------------------------------------------------------------

    # 結果格納用の変数 resultJson　（室負荷）
    for room_zone_name in inputdata["AirConditioningZone"]:
        resultJson["Qroom"][room_zone_name] = {
            "Troom": np.zeros((365, 24)),  # 時刻別室温　[℃]
            "MRTroom": np.zeros((365, 24)),  # 時刻別平均放射温度　[℃]
            "Qroom_hourly": np.zeros((365, 24))  # 時刻別熱取得　[MJ/h]
        }

    #----------------------------------------------------------------------------------
    # 外壁等の熱貫流率の算出（解説書 附属書A.1）
    #----------------------------------------------------------------------------------

    # todo : 二つのデータベースにわかれてしまっているので統一する。

    # 標準入力法建材データの読み込み
    with open(database_directory + 'HeatThermalConductivity.json', 'r', encoding='utf-8') as f:
        HeatThermalConductivity = json.load(f)

    # モデル建物法建材データの読み込み
    with open(database_directory + 'HeatThermalConductivity_model.json', 'r', encoding='utf-8') as f:
        HeatThermalConductivity_model = json.load(f)

    if "WallConfigure" in inputdata:  # WallConfigure があれば以下を実行

        for wall_name in inputdata["WallConfigure"].keys():

            if inputdata["WallConfigure"][wall_name]["inputMethod"] == "断熱材種類を入力":

                if inputdata["WallConfigure"][wall_name]["materialID"] == "無":  # 断熱材種類が「無」の場合

                    inputdata["WallConfigure"][wall_name]["Uvalue_wall"] = 2.63
                    inputdata["WallConfigure"][wall_name]["Uvalue_roof"] = 1.53
                    inputdata["WallConfigure"][wall_name]["Uvalue_floor"] = 2.67

                else:  # 断熱材種類が「無」以外、もしくは、熱伝導率が直接入力されている場合

                    # 熱伝導率の指定がない場合は「断熱材種類」から推定
                    if inputdata["WallConfigure"][wall_name]["conductivity"] == None:
                        inputdata["WallConfigure"][wall_name]["conductivity"] = \
                            float(HeatThermalConductivity_model[inputdata["WallConfigure"][wall_name]["materialID"]])

                    # 熱伝導率と厚みとから、熱貫流率を計算（３種類）
                    inputdata["WallConfigure"][wall_name]["Uvalue_wall"] = \
                        0.663 * (inputdata["WallConfigure"][wall_name]["thickness"] / 1000 / inputdata["WallConfigure"][wall_name]["conductivity"]) ** (-0.638)
                    inputdata["WallConfigure"][wall_name]["Uvalue_roof"] = \
                        0.548 * (inputdata["WallConfigure"][wall_name]["thickness"] / 1000 / inputdata["WallConfigure"][wall_name]["conductivity"]) ** (-0.524)
                    inputdata["WallConfigure"][wall_name]["Uvalue_floor"] = \
                        0.665 * (inputdata["WallConfigure"][wall_name]["thickness"] / 1000 / inputdata["WallConfigure"][wall_name]["conductivity"]) ** (-0.641)


            elif inputdata["WallConfigure"][wall_name]["inputMethod"] == "建材構成を入力":

                Rvalue = 0.11 + 0.04

                for layer in enumerate(inputdata["WallConfigure"][wall_name]["layers"]):

                    # 熱伝導率が空欄である場合、建材名称から熱伝導率を見出す。
                    if layer[1]["conductivity"] == None:

                        if (layer[1]["materialID"] == "密閉中空層") or (layer[1]["materialID"] == "非密閉中空層"):

                            # 空気層の場合
                            Rvalue += HeatThermalConductivity[layer[1]["materialID"]]["熱抵抗値"]

                        else:

                            # 空気層以外の断熱材を指定している場合
                            if layer[1]["thickness"] != None:
                                material_name = layer[1]["materialID"].replace('\u3000', '')
                                Rvalue += (layer[1]["thickness"] / 1000) / HeatThermalConductivity[material_name]["熱伝導率"]

                    else:

                        # 熱伝導率を入力している場合
                        Rvalue += (layer[1]["thickness"] / 1000) / layer[1]["conductivity"]

                inputdata["WallConfigure"][wall_name]["Uvalue"] = 1 / Rvalue

    #----------------------------------------------------------------------------------
    # 窓の熱貫流率及び日射熱取得率の算出（解説書 附属書A.2）
    #----------------------------------------------------------------------------------

    # 窓データの読み込み
    with open(database_directory + 'WindowHeatTransferPerformance.json', 'r', encoding='utf-8') as f:
        WindowHeatTransferPerformance = json.load(f)

    with open(database_directory + 'glass2window.json', 'r', encoding='utf-8') as f:
        glass2window = json.load(f)

    if "WindowConfigure" in inputdata:

        for window_name in inputdata["WindowConfigure"].keys():

            if inputdata["WindowConfigure"][window_name]["inputMethod"] == "ガラスの種類を入力":

                # 建具の種類の読み替え
                if inputdata["WindowConfigure"][window_name]["frameType"] == "木製" or \
                        inputdata["WindowConfigure"][window_name]["frameType"] == "樹脂製":

                    inputdata["WindowConfigure"][window_name]["frameType"] = "木製・樹脂製建具"

                elif inputdata["WindowConfigure"][window_name]["frameType"] == "金属木複合製" or \
                        inputdata["WindowConfigure"][window_name]["frameType"] == "金属樹脂複合製":

                    inputdata["WindowConfigure"][window_name]["frameType"] = "金属木複合製・金属樹脂複合製建具"

                elif inputdata["WindowConfigure"][window_name]["frameType"] == "金属製":

                    inputdata["WindowConfigure"][window_name]["frameType"] = "金属製建具"

                # ガラスIDと建具の種類から、熱貫流率・日射熱取得率を抜き出す。
                inputdata["WindowConfigure"][window_name]["Uvalue"] = \
                    WindowHeatTransferPerformance \
                        [inputdata["WindowConfigure"][window_name]["glassID"]] \
                        [inputdata["WindowConfigure"][window_name]["frameType"]]["熱貫流率"]

                inputdata["WindowConfigure"][window_name]["Uvalue_blind"] = \
                    WindowHeatTransferPerformance \
                        [inputdata["WindowConfigure"][window_name]["glassID"]] \
                        [inputdata["WindowConfigure"][window_name]["frameType"]]["熱貫流率・ブラインド込"]

                inputdata["WindowConfigure"][window_name]["Ivalue"] = \
                    WindowHeatTransferPerformance \
                        [inputdata["WindowConfigure"][window_name]["glassID"]] \
                        [inputdata["WindowConfigure"][window_name]["frameType"]]["日射熱取得率"]

                inputdata["WindowConfigure"][window_name]["Ivalue_blind"] = \
                    WindowHeatTransferPerformance \
                        [inputdata["WindowConfigure"][window_name]["glassID"]] \
                        [inputdata["WindowConfigure"][window_name]["frameType"]]["日射熱取得率・ブラインド込"]


            elif inputdata["WindowConfigure"][window_name]["inputMethod"] == "ガラスの性能を入力":

                ku_a = 0
                ku_b = 0
                kita = 0
                dR = 0

                # 建具の種類の読み替え
                if inputdata["WindowConfigure"][window_name]["frameType"] == "木製" or \
                        inputdata["WindowConfigure"][window_name]["frameType"] == "樹脂製":

                    inputdata["WindowConfigure"][window_name]["frameType"] = "木製・樹脂製建具"

                elif inputdata["WindowConfigure"][window_name]["frameType"] == "金属木複合製" or \
                        inputdata["WindowConfigure"][window_name]["frameType"] == "金属樹脂複合製":

                    inputdata["WindowConfigure"][window_name]["frameType"] = "金属木複合製・金属樹脂複合製建具"

                elif inputdata["WindowConfigure"][window_name]["frameType"] == "金属製":

                    inputdata["WindowConfigure"][window_name]["frameType"] = "金属製建具"

                # 変換係数
                ku_a = glass2window[inputdata["WindowConfigure"][window_name]["frameType"]][inputdata["WindowConfigure"][window_name]["layerType"]]["ku_a1"] \
                       / glass2window[inputdata["WindowConfigure"][window_name]["frameType"]][inputdata["WindowConfigure"][window_name]["layerType"]]["ku_a2"]
                ku_b = glass2window[inputdata["WindowConfigure"][window_name]["frameType"]][inputdata["WindowConfigure"][window_name]["layerType"]]["ku_b1"] \
                       / glass2window[inputdata["WindowConfigure"][window_name]["frameType"]][inputdata["WindowConfigure"][window_name]["layerType"]]["ku_b2"]
                kita = glass2window[inputdata["WindowConfigure"][window_name]["frameType"]][inputdata["WindowConfigure"][window_name]["layerType"]]["kita"]

                inputdata["WindowConfigure"][window_name]["Uvalue"] = ku_a * inputdata["WindowConfigure"][window_name]["glassUvalue"] + ku_b
                inputdata["WindowConfigure"][window_name]["Ivalue"] = kita * inputdata["WindowConfigure"][window_name]["glassIvalue"]

                # ガラスの熱貫流率と日射熱取得率が入力されている場合は、ブラインドの効果を見込む
                dR = (0.021 / inputdata["WindowConfigure"][window_name]["glassUvalue"]) + 0.022

                inputdata["WindowConfigure"][window_name]["Uvalue_blind"] = \
                    1 / ((1 / inputdata["WindowConfigure"][window_name]["Uvalue"]) + dR)

                inputdata["WindowConfigure"][window_name]["Ivalue_blind"] = \
                    inputdata["WindowConfigure"][window_name]["Ivalue"] / inputdata["WindowConfigure"][window_name]["glassIvalue"] \
                    * (-0.1331 * inputdata["WindowConfigure"][window_name]["glassIvalue"] ** 2 +
                       0.8258 * inputdata["WindowConfigure"][window_name]["glassIvalue"])


            elif inputdata["WindowConfigure"][window_name]["inputMethod"] == "性能値を入力":

                inputdata["WindowConfigure"][window_name]["Uvalue"] = inputdata["WindowConfigure"][window_name]["windowUvalue"]
                inputdata["WindowConfigure"][window_name]["Ivalue"] = inputdata["WindowConfigure"][window_name]["windowIvalue"]

                # ブラインド込みの値を計算
                dR = 0

                if inputdata["WindowConfigure"][window_name]["glassUvalue"] == None or \
                        inputdata["WindowConfigure"][window_name]["glassIvalue"] == None:

                    inputdata["WindowConfigure"][window_name]["Uvalue_blind"] = inputdata["WindowConfigure"][window_name]["windowUvalue"]
                    inputdata["WindowConfigure"][window_name]["Ivalue_blind"] = inputdata["WindowConfigure"][window_name]["windowIvalue"]

                else:
                    # ガラスの熱貫流率と日射熱取得率が入力されている場合は、ブラインドの効果を見込む
                    dR = (0.021 / inputdata["WindowConfigure"][window_name]["glassUvalue"]) + 0.022

                    inputdata["WindowConfigure"][window_name]["Uvalue_blind"] = \
                        1 / ((1 / inputdata["WindowConfigure"][window_name]["windowUvalue"]) + dR)

                    inputdata["WindowConfigure"][window_name]["Ivalue_blind"] = \
                        inputdata["WindowConfigure"][window_name]["windowIvalue"] / inputdata["WindowConfigure"][window_name]["glassIvalue"] \
                        * (-0.1331 * inputdata["WindowConfigure"][window_name]["glassIvalue"] ** 2 +
                           0.8258 * inputdata["WindowConfigure"][window_name]["glassIvalue"])

            if debug:  # pragma: no cover
                print(f'--- 窓名称 {window_name} ---')
                print(f'窓の熱貫流率 Uvalue : {inputdata["WindowConfigure"][window_name]["Uvalue"]}')
                print(f'窓+BLの熱貫流率 Uvalue_blind : {inputdata["WindowConfigure"][window_name]["Uvalue_blind"]}')

    #----------------------------------------------------------------------------------
    # 外壁の面積の計算（解説書 2.4.2.1）
    #----------------------------------------------------------------------------------

    # 外皮面積の算出
    for room_zone_name in inputdata["EnvelopeSet"]:

        for wall_id, wall_configure in enumerate(inputdata["EnvelopeSet"][room_zone_name]["WallList"]):

            if inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["EnvelopeArea"] == None:  # 外皮面積が空欄であれば、外皮の寸法から面積を計算。

                inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["EnvelopeArea"] = \
                    wall_configure["EnvelopeWidth"] * wall_configure["EnvelopeHeight"]

    # 窓面積の算出
    for window_id in inputdata["WindowConfigure"]:
        if inputdata["WindowConfigure"][window_id]["windowArea"] == None:  # 窓面積が空欄であれば、窓寸法から面積を計算。
            inputdata["WindowConfigure"][window_id]["windowArea"] = \
                inputdata["WindowConfigure"][window_id]["windowWidth"] * inputdata["WindowConfigure"][window_id]["windowHeight"]

    # 外壁面積の算出
    for room_zone_name in inputdata["EnvelopeSet"]:

        for (wall_id, wall_configure) in enumerate(inputdata["EnvelopeSet"][room_zone_name]["WallList"]):

            window_total = 0  # 窓面積の集計用

            if "WindowList" in wall_configure:  # 窓がある場合

                # 窓面積の合計を求める（Σ{窓面積×枚数}）
                for (window_id, window_configure) in enumerate(wall_configure["WindowList"]):

                    if window_configure["WindowID"] != "無":
                        window_total += \
                            inputdata["WindowConfigure"][window_configure["WindowID"]]["windowArea"] * window_configure["WindowNumber"]

            # 壁のみの面積（窓がない場合は、window_total = 0）
            if wall_configure["EnvelopeArea"] >= window_total:
                inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WallArea"] = wall_configure["EnvelopeArea"] - window_total
            else:
                print(room_zone_name)
                print(wall_configure)
                raise Exception('窓面積が外皮面積よりも大きくなっています')

    #----------------------------------------------------------------------------------
    # 室の定常熱取得の計算（解説書 2.4.2.2〜2.4.2.7）
    #----------------------------------------------------------------------------------

    # EnvelopeSet に WallConfigure, WindowConfigure の情報を貼り付ける。
    for room_zone_name in inputdata["EnvelopeSet"]:

        # 壁毎にループ
        for (wall_id, wall_configure) in enumerate(inputdata["EnvelopeSet"][room_zone_name]["WallList"]):

            if inputdata["WallConfigure"][wall_configure["WallSpec"]]["inputMethod"] == "断熱材種類を入力":

                if wall_configure["Direction"] == "水平（上）":  # 天井と見なす。

                    inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["U_wall"] = \
                        inputdata["WallConfigure"][wall_configure["WallSpec"]]["Uvalue_roof"]
                    inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WallArea"] = wall_configure["WallArea"]

                elif wall_configure["Direction"] == "水平（下）":  # 床と見なす。

                    inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["U_wall"] = \
                        inputdata["WallConfigure"][wall_configure["WallSpec"]]["Uvalue_floor"]
                    inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WallArea"] = wall_configure["WallArea"]

                else:

                    inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["U_wall"] = \
                        inputdata["WallConfigure"][wall_configure["WallSpec"]]["Uvalue_wall"]
                    inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WallArea"] = wall_configure["WallArea"]

            else:

                inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["U_wall"] = \
                    inputdata["WallConfigure"][wall_configure["WallSpec"]]["Uvalue"]
                inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WallArea"] = wall_configure["WallArea"]

            for (window_id, window_configure) in enumerate(inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WindowList"]):

                if window_configure["WindowID"] != "無":

                    # 日よけ効果係数の算出
                    if window_configure["EavesID"] == "無":

                        inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WindowList"][window_id]["shadingEffect_C"] = 1
                        inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WindowList"][window_id]["shadingEffect_H"] = 1

                    else:

                        if inputdata["ShadingConfigure"][window_configure["EavesID"]]["shadingEffect_C"] != None and \
                                inputdata["ShadingConfigure"][window_configure["EavesID"]]["shadingEffect_H"] != None:

                            inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WindowList"][window_id]["shadingEffect_C"] = \
                                inputdata["ShadingConfigure"][window_configure["EavesID"]]["shadingEffect_C"]
                            inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WindowList"][window_id]["shadingEffect_H"] = \
                                inputdata["ShadingConfigure"][window_configure["EavesID"]]["shadingEffect_H"]

                        else:

                            # 関数 shading.calc_shadingCoefficient で日よけ効果係数を算出。
                            (inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WindowList"][window_id]["shadingEffect_C"],
                             inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WindowList"][window_id]["shadingEffect_H"]) = \
                                shading.calc_shadingCoefficient(inputdata["Building"]["Region"],
                                                                wall_configure["Direction"],
                                                                inputdata["ShadingConfigure"][window_configure["EavesID"]]["x1"],
                                                                inputdata["ShadingConfigure"][window_configure["EavesID"]]["x2"],
                                                                inputdata["ShadingConfigure"][window_configure["EavesID"]]["x3"],
                                                                inputdata["ShadingConfigure"][window_configure["EavesID"]]["y1"],
                                                                inputdata["ShadingConfigure"][window_configure["EavesID"]]["y2"],
                                                                inputdata["ShadingConfigure"][window_configure["EavesID"]]["y3"],
                                                                inputdata["ShadingConfigure"][window_configure["EavesID"]]["zxPlus"],
                                                                inputdata["ShadingConfigure"][window_configure["EavesID"]]["zxMinus"],
                                                                inputdata["ShadingConfigure"][window_configure["EavesID"]]["zyPlus"],
                                                                inputdata["ShadingConfigure"][window_configure["EavesID"]]["zyMinus"])

                    # 窓のUA（熱貫流率×面積）を計算
                    if window_configure["isBlind"] == "無":  # ブラインドがない場合

                        inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WindowList"][window_id]["U_window"] = \
                            inputdata["WindowConfigure"][window_configure["WindowID"]]["Uvalue"]
                        inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WindowList"][window_id]["I_window"] = \
                            inputdata["WindowConfigure"][window_configure["WindowID"]]["Ivalue"]
                        inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WindowList"][window_id]["windowArea"] = \
                            window_configure["WindowNumber"] * inputdata["WindowConfigure"][window_configure["WindowID"]]["windowArea"]

                    elif window_configure["isBlind"] == "有":  # ブラインドがある場合

                        inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WindowList"][window_id]["U_window"] = \
                            inputdata["WindowConfigure"][window_configure["WindowID"]]["Uvalue_blind"]
                        inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WindowList"][window_id]["I_window"] = \
                            inputdata["WindowConfigure"][window_configure["WindowID"]]["Ivalue_blind"]
                        inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WindowList"][window_id]["windowArea"] = \
                            window_configure["WindowNumber"] * inputdata["WindowConfigure"][window_configure["WindowID"]]["windowArea"]

                    # 任意入力 SP-8
                    if "window_Ivalue" in inputdata["SpecialInputData"]:
                        if window_configure["WindowID"] in inputdata["SpecialInputData"]["window_Ivalue"]:
                            inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WindowList"][window_id]["IA_window"] = \
                                window_configure["WindowNumber"] * inputdata["WindowConfigure"][window_configure["WindowID"]]["windowArea"] * \
                                np.array(inputdata["SpecialInputData"]["window_Ivalue"][window_configure["WindowID"]])

    #----------------------------------------------------------------------------------
    # 室負荷の計算（解説書 2.4.3、2.4.4）
    #----------------------------------------------------------------------------------

    Heat_light_hourly = {}
    Num_of_Person_hourly = {}
    Heat_OAapp_hourly = {}

    for room_zone_name in inputdata["AirConditioningZone"]:

        # 室が使用されているか否か＝空調運転時間（365日分）
        btype = inputdata["AirConditioningZone"][room_zone_name]["buildingType"]
        rtype = inputdata["AirConditioningZone"][room_zone_name]["roomType"]

        # 発熱量参照値 [W/m2] を読み込む関数（空調） SP-9
        if "room_usage_condition" in inputdata["SpecialInputData"]:
            (roomHeatGain_Light, roomHeatGain_Person, roomHeatGain_OAapp, roomNumOfPerson) = \
                bc.get_roomHeatGain(btype, rtype, inputdata["SpecialInputData"]["room_usage_condition"])
        else:
            (roomHeatGain_Light, roomHeatGain_Person, roomHeatGain_OAapp, roomNumOfPerson) = \
                bc.get_roomHeatGain(btype, rtype)

        # 様式4から照明発熱量を読み込む
        if BUILELIB_MODE:
            if room_zone_name in inputdata["LightingSystems"]:
                lighting_power = 0
                for unit_name in inputdata["LightingSystems"][room_zone_name]["lightingUnit"]:
                    lighting_power += inputdata["LightingSystems"][room_zone_name]["lightingUnit"][unit_name]["RatedPower"] * \
                                      inputdata["LightingSystems"][room_zone_name]["lightingUnit"][unit_name]["Number"]
                roomHeatGain_Light = lighting_power / inputdata["AirConditioningZone"][room_zone_name]["zoneArea"]

        # 時刻別計算用（本来はこのループに入れるべきではない → 時刻別計算の方に入れるべき）
        Heat_light_hourly[room_zone_name] = roomScheduleLight[room_zone_name] * roomHeatGain_Light  # 照明からの発熱 （365日分）
        Num_of_Person_hourly[room_zone_name] = roomSchedulePerson[room_zone_name] * roomNumOfPerson  # 人員密度（365日分）
        Heat_OAapp_hourly[room_zone_name] = roomScheduleOAapp[room_zone_name] * roomHeatGain_OAapp  # 機器からの発熱 （365日分）

    #----------------------------------------------------------------------------------
    # 動的室負荷計算
    #----------------------------------------------------------------------------------

    # 負荷計算モジュールの読み込み
    from .heat_load_calculation import Main
    import copy

    # ファイルの読み込み
    with open('./builelib/heat_load_calculation/heatload_calculation_template.json', 'r', encoding='utf-8') as js:
        # with open('input_non_residential.json', 'r', encoding='utf-8') as js:
        input_heatcalc_template = json.load(js)

    # 入力ファイルの生成（共通）
    # 地域
    input_heatcalc_template["common"]["region"] = inputdata["Building"]["Region"]
    input_heatcalc_template["common"]["is_residential"] = False

    # 室温上限値・下限
    input_heatcalc_template["rooms"][0]["schedule"]["temperature_upper_limit"] = bc.trans_36524to8760(resultJson["schedule"]["room_temperature_setpoint"])
    input_heatcalc_template["rooms"][0]["schedule"]["temperature_lower_limit"] = bc.trans_36524to8760(resultJson["schedule"]["room_temperature_setpoint"])

    # 相対湿度上限値・下限
    input_heatcalc_template["rooms"][0]["schedule"]["relative_humidity_upper_limit"] = bc.trans_36524to8760(resultJson["schedule"]["room_humidity_setpoint"])
    input_heatcalc_template["rooms"][0]["schedule"]["relative_humidity_lower_limit"] = bc.trans_36524to8760(resultJson["schedule"]["room_humidity_setpoint"])

    # 非住宅では使わない
    input_heatcalc_template["rooms"][0]["vent"] = 0
    input_heatcalc_template["rooms"][0]["schedule"]["heat_generation_cooking"] = np.zeros(8760)
    input_heatcalc_template["rooms"][0]["schedule"]["vapor_generation_cooking"] = np.zeros(8760)
    input_heatcalc_template["rooms"][0]["schedule"]["local_vent_amount"] = np.zeros(8760)

    # 空調ゾーン毎に負荷を計算
    for room_zone_name in inputdata["AirConditioningZone"]:

        # 入力ファイルの読み込み
        input_heatcalc = copy.deepcopy(input_heatcalc_template)

        # 入力ファイルの生成（室単位）

        # 室名
        input_heatcalc["rooms"][0]["name"] = room_zone_name
        # 気積 [m3]
        input_heatcalc["rooms"][0]["volume"] = inputdata["AirConditioningZone"][room_zone_name]["zoneArea"] * inputdata["AirConditioningZone"][room_zone_name]["ceilingHeight"]

        # 室温湿度の上下限
        input_heatcalc["rooms"][0]["schedule"]["is_upper_temp_limit_set"] = np.reshape(np.array(roomScheduleRoom[room_zone_name], dtype="bool"), 8760)
        input_heatcalc["rooms"][0]["schedule"]["is_lower_temp_limit_set"] = np.reshape(np.array(roomScheduleRoom[room_zone_name], dtype="bool"), 8760)
        input_heatcalc["rooms"][0]["schedule"]["is_upper_humidity_limit_set"] = np.reshape(np.array(roomScheduleRoom[room_zone_name], dtype="bool"), 8760)
        input_heatcalc["rooms"][0]["schedule"]["is_lower_humidity_limit_set"] = np.reshape(np.array(roomScheduleRoom[room_zone_name], dtype="bool"), 8760)

        # 発熱量
        # 照明発熱スケジュール[W]
        input_heatcalc["rooms"][0]["schedule"]["heat_generation_lighting"] = np.reshape(Heat_light_hourly[room_zone_name], 8760) * inputdata["AirConditioningZone"][room_zone_name][
            "zoneArea"]
        # 機器発熱スケジュール[W]
        input_heatcalc["rooms"][0]["schedule"]["heat_generation_appliances"] = np.reshape(Heat_OAapp_hourly[room_zone_name], 8760) * \
                                                                               inputdata["AirConditioningZone"][room_zone_name]["zoneArea"]
        # 人員数[人]
        input_heatcalc["rooms"][0]["schedule"]["number_of_people"] = np.reshape(Num_of_Person_hourly[room_zone_name], 8760) * inputdata["AirConditioningZone"][room_zone_name][
            "zoneArea"]

        # 床の面積（計算対象床面積を入力する）
        input_heatcalc["rooms"][0]["boundaries"][0]["area"] = \
            inputdata["AirConditioningZone"][room_zone_name]["zoneArea"]

        # 天井の面積（床と同じとする）
        input_heatcalc["rooms"][0]["boundaries"][1]["area"] = \
            inputdata["AirConditioningZone"][room_zone_name]["zoneArea"]

        # 外皮があれば
        if room_zone_name in inputdata["EnvelopeSet"]:

            # 外壁
            for (wall_id, wall_configure) in enumerate(inputdata["EnvelopeSet"][room_zone_name]["WallList"]):

                # 等価R値
                if inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["U_wall"] > 4:
                    equivalent_Rvalue = 0.001
                else:
                    equivalent_Rvalue = (1 / inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["U_wall"] - 0.25)

                direction = ""
                if inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["Direction"] == "北":
                    direction = "n"
                elif inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["Direction"] == "北東":
                    direction = "ne"
                elif inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["Direction"] == "東":
                    direction = "e"
                elif inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["Direction"] == "南東":
                    direction = "se"
                elif inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["Direction"] == "南":
                    direction = "s"
                elif inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["Direction"] == "南西":
                    direction = "sw"
                elif inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["Direction"] == "西":
                    direction = "w"
                elif inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["Direction"] == "北西":
                    direction = "nw"
                elif inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["Direction"] == "水平（上）":
                    direction = "top"
                elif inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["Direction"] == "水平（下）":
                    direction = "bottom"
                else:
                    raise Exception("方位が不正です")

                boundary_type = ""
                is_sun_striked_outside = ""
                if inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WallType"] == "日の当たる外壁":
                    boundary_type = "external_general_part"
                    is_sun_striked_outside = True
                elif inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WallType"] == "日の当たらない外壁":
                    boundary_type = "external_general_part"
                    is_sun_striked_outside = False
                elif inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WallType"] == "地盤に接する外壁":
                    boundary_type = "ground"
                    is_sun_striked_outside = False
                elif inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WallType"] == "地盤に接する外壁_Ver2":
                    boundary_type = "ground"
                    is_sun_striked_outside = False

                if boundary_type == "external_general_part":

                    input_heatcalc["rooms"][0]["boundaries"].append(
                        {
                            "name": "wall",
                            "boundary_type": boundary_type,
                            "area": inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WallArea"],
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
                                            "thermal_resistance": equivalent_Rvalue,
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
                            "area": inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WallArea"],
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
                                            "thermal_resistance": equivalent_Rvalue,
                                            "thermal_capacity": 1.00
                                        }
                                    ],
                                }
                        }
                    )

                # 窓
                for (window_id, window_configure) in enumerate(inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WindowList"]):

                    if window_configure["WindowID"] != "無":
                        input_heatcalc["rooms"][0]["boundaries"].append(
                            {
                                "name": "window",
                                "boundary_type": "external_transparent_part",
                                "area": inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WindowList"][window_id]["windowArea"],
                                "is_sun_striked_outside": True,
                                "temp_dif_coef": 0,
                                "direction": direction,
                                "is_solar_absorbed_inside": False,
                                "transparent_opening_part_spec": {
                                    "eta_value": inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WindowList"][window_id]["I_window"],
                                    "u_value": inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WindowList"][window_id]["U_window"],
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
        room_air_temperature, mean_radiant_temperature, heatload_sensible_convection, heatload_sensible_radiation, heatload_latent \
            = Main.run(input_heatcalc)

        # 室温
        resultJson["Qroom"][room_zone_name]["Troom"] = bc.trans_8760to36524(room_air_temperature)
        resultJson["Qroom"][room_zone_name]["MRTroom"] = bc.trans_8760to36524(mean_radiant_temperature)

        # 負荷の積算（全熱負荷）[W] (365×24)
        heatload = np.array(
            bc.trans_8760to36524(heatload_sensible_convection) + \
            bc.trans_8760to36524(heatload_sensible_radiation) + \
            bc.trans_8760to36524(heatload_latent)
        )

        for dd in range(0, 365):
            for hh in range(0, 24):
                # 時刻別室負荷 [W] → [MJ/hour]
                resultJson["Qroom"][room_zone_name]["Qroom_hourly"][dd][hh] = (-1) * heatload[dd][hh] * 3600 / 1000000

    if debug:  # pragma: no cover

        # 熱負荷のグラフ化
        for room_zone_name in inputdata["AirConditioningZone"]:
            mf.hourlyplot(resultJson["Qroom"][room_zone_name]["Troom"], "室内空気温度： " + room_zone_name, "b", "室内空気温度")
            mf.hourlyplot(resultJson["Qroom"][room_zone_name]["MRTroom"], "室内平均放射温度 " + room_zone_name, "b", "室内平均放射温度")
            mf.hourlyplot(resultJson["Qroom"][room_zone_name]["Qroom_hourly"], "室負荷： " + room_zone_name, "b", "時刻別室負荷")

    print('室負荷計算完了')

    #----------------------------------------------------------------------------------
    # 空調機群の一次エネルギー消費量（解説書 2.5）
    #----------------------------------------------------------------------------------

    # 結果格納用の変数 resultJson　（空調機群）
    for ahu_name in inputdata["AirHandlingSystem"]:
        resultJson["AHU"][ahu_name] = {

            "schedule": np.zeros((365, 24)),  # 時刻別の運転スケジュール（365×24）
            "Hoa_hourly": np.zeros((365, 24)),  # 空調運転時間帯の外気エンタルピー

            "Qoa_hourly": np.zeros((365, 24)),  # 日平均外気負荷 [kW]
            "Qroom_hourly": np.zeros((365, 24)),  # 時刻別室負荷の積算値 [MJ/h]
            "Qahu_hourly": np.zeros((365, 24)),  # 時刻別空調負荷 [MJ/day]
            "Qahu_unprocessed": np.zeros((365, 24)),  # 空調機群の未処理負荷（冷房）[MJ/h]

            "E_fan_hourly": np.zeros((365, 24)),  # 送風機の時刻別エネルギー消費量 [MWh]
            "E_aex_hourly": np.zeros((365, 24)),  # 全熱交換器の時刻別エネルギー消費量 [MWh]

            "Economizer": {
                "AHUVovc": np.zeros((365, 24)),  # 外気冷房運転時の外気風量 [kg/s]
                "Qahu_oac": np.zeros((365, 24)),  # 外気冷房による負荷削減効果 [MJ/day]
            },

            "load_ratio": np.zeros((365, 24)),  # 時刻別の負荷率

            "Eahu_total": 0,  # 消費電力の合計 [h]
            "Tahu_total": 0  # 運転時間の合計 [h]
        }

    #----------------------------------------------------------------------------------
    # 空調機群全体のスペックを整理
    #----------------------------------------------------------------------------------

    for ahu_name in inputdata["AirHandlingSystem"]:

        # 空調機タイプ（1つでも空調機があれば「空調機」と判断する）
        inputdata["AirHandlingSystem"][ahu_name]["AHU_type"] = "空調機以外"
        for unit_id, unit_configure in enumerate(inputdata["AirHandlingSystem"][ahu_name]["AirHandlingUnit"]):
            if unit_configure["Type"] == "空調機":
                inputdata["AirHandlingSystem"][ahu_name]["AHU_type"] = "空調機"
                break

        # 空調機の能力
        inputdata["AirHandlingSystem"][ahu_name]["RatedCapacityCooling"] = 0
        inputdata["AirHandlingSystem"][ahu_name]["RatedCapacityHeating"] = 0
        for unit_id, unit_configure in enumerate(inputdata["AirHandlingSystem"][ahu_name]["AirHandlingUnit"]):
            if unit_configure["RatedCapacityCooling"] != None:
                inputdata["AirHandlingSystem"][ahu_name]["RatedCapacityCooling"] += \
                    unit_configure["RatedCapacityCooling"] * unit_configure["Number"]

            if unit_configure["RatedCapacityHeating"] != None:
                inputdata["AirHandlingSystem"][ahu_name]["RatedCapacityHeating"] += \
                    unit_configure["RatedCapacityHeating"] * unit_configure["Number"]

        # 送風機単体の定格消費電力（解説書 2.5.8） [kW]
        for unit_id, unit_configure in enumerate(inputdata["AirHandlingSystem"][ahu_name]["AirHandlingUnit"]):
            inputdata["AirHandlingSystem"][ahu_name]["AirHandlingUnit"][unit_id]["FanPowerConsumption_total"] = 0
            if unit_configure["FanPowerConsumption"] != None:
                # 送風機の定格消費電力 kW = 1台あたりの消費電力 kW × 台数
                inputdata["AirHandlingSystem"][ahu_name]["AirHandlingUnit"][unit_id]["FanPowerConsumption_total"] = \
                    unit_configure["FanPowerConsumption"] * unit_configure["Number"]

        # 空調機の風量 [m3/h]
        inputdata["AirHandlingSystem"][ahu_name]["FanAirVolume"] = 0
        for unit_id, unit_configure in enumerate(inputdata["AirHandlingSystem"][ahu_name]["AirHandlingUnit"]):
            if unit_configure["FanAirVolume"] != None:
                inputdata["AirHandlingSystem"][ahu_name]["FanAirVolume"] += \
                    unit_configure["FanAirVolume"] * unit_configure["Number"]

        # 全熱交換器の効率（一番低いものを採用）
        inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioCooling"] = None
        inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioHeating"] = None
        for unit_id, unit_configure in enumerate(inputdata["AirHandlingSystem"][ahu_name]["AirHandlingUnit"]):

            # 冷房の効率
            if unit_configure["AirHeatExchangeRatioCooling"] != None:
                if inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioCooling"] == None:
                    inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioCooling"] = unit_configure["AirHeatExchangeRatioCooling"]
                elif inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioCooling"] > unit_configure["AirHeatExchangeRatioCooling"]:
                    inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioCooling"] = unit_configure["AirHeatExchangeRatioCooling"]

            # 暖房の効率
            if unit_configure["AirHeatExchangeRatioHeating"] != None:
                if inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioHeating"] == None:
                    inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioHeating"] = unit_configure["AirHeatExchangeRatioHeating"]
                elif inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioHeating"] > unit_configure["AirHeatExchangeRatioHeating"]:
                    inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioHeating"] = unit_configure["AirHeatExchangeRatioHeating"]

        # 全熱交換器のバイパス制御の有無（1つでもあればバイパス制御「有」とする）
        inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangerControl"] = "無"
        for unit_id, unit_configure in enumerate(inputdata["AirHandlingSystem"][ahu_name]["AirHandlingUnit"]):
            if (unit_configure["AirHeatExchangeRatioCooling"] != None) and (unit_configure["AirHeatExchangeRatioHeating"] != None):
                if unit_configure["AirHeatExchangerControl"] == "有":
                    inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangerControl"] = "有"

        # 全熱交換器の消費電力 [kW]
        inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangerPowerConsumption"] = 0
        for unit_id, unit_configure in enumerate(inputdata["AirHandlingSystem"][ahu_name]["AirHandlingUnit"]):
            if unit_configure["AirHeatExchangerPowerConsumption"] != None:
                inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangerPowerConsumption"] += \
                    unit_configure["AirHeatExchangerPowerConsumption"] * unit_configure["Number"]

        # 全熱交換器の風量 [m3/h]
        inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangerAirVolume"] = 0
        for unit_id, unit_configure in enumerate(inputdata["AirHandlingSystem"][ahu_name]["AirHandlingUnit"]):
            if (unit_configure["AirHeatExchangeRatioCooling"] != None) and (unit_configure["AirHeatExchangeRatioHeating"] != None):
                inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangerAirVolume"] += \
                    unit_configure["FanAirVolume"] * unit_configure["Number"]

    #----------------------------------------------------------------------------------
    # 冷暖同時供給の有無の判定
    #----------------------------------------------------------------------------------

    for ahu_name in inputdata["AirHandlingSystem"]:
        inputdata["AirHandlingSystem"][ahu_name]["isSimultaneousSupply"] = "無"
        inputdata["AirHandlingSystem"][ahu_name]["isSimultaneousSupply_cooling"] = "無"
        inputdata["AirHandlingSystem"][ahu_name]["isSimultaneousSupply_heating"] = "無"
    for pump_name in inputdata["SecondaryPumpSystem"]:
        inputdata["SecondaryPumpSystem"][pump_name]["isSimultaneousSupply"] = "無"
    for ref_name in inputdata["HeatsourceSystem"]:
        inputdata["HeatsourceSystem"][ref_name]["isSimultaneousSupply"] = "無"

    for room_zone_name in inputdata["AirConditioningZone"]:

        if inputdata["AirConditioningZone"][room_zone_name]["isSimultaneousSupply"] == "有":

            # 空調機群
            inputdata["AirHandlingSystem"][inputdata["AirConditioningZone"][room_zone_name]["AHU_cooling_insideLoad"]]["isSimultaneousSupply_cooling"] = "有"
            inputdata["AirHandlingSystem"][inputdata["AirConditioningZone"][room_zone_name]["AHU_cooling_outdoorLoad"]]["isSimultaneousSupply_cooling"] = "有"
            inputdata["AirHandlingSystem"][inputdata["AirConditioningZone"][room_zone_name]["AHU_heating_insideLoad"]]["isSimultaneousSupply_heating"] = "有"
            inputdata["AirHandlingSystem"][inputdata["AirConditioningZone"][room_zone_name]["AHU_heating_outdoorLoad"]]["isSimultaneousSupply_heating"] = "有"

            # 熱源群
            id_ref_c1 = inputdata["AirHandlingSystem"][inputdata["AirConditioningZone"][room_zone_name]["AHU_cooling_insideLoad"]]["HeatSource_cooling"]
            id_ref_c2 = inputdata["AirHandlingSystem"][inputdata["AirConditioningZone"][room_zone_name]["AHU_cooling_outdoorLoad"]]["HeatSource_cooling"]
            id_ref_h1 = inputdata["AirHandlingSystem"][inputdata["AirConditioningZone"][room_zone_name]["AHU_heating_insideLoad"]]["HeatSource_heating"]
            id_ref_h2 = inputdata["AirHandlingSystem"][inputdata["AirConditioningZone"][room_zone_name]["AHU_heating_outdoorLoad"]]["HeatSource_heating"]

            inputdata["HeatsourceSystem"][id_ref_c1]["isSimultaneousSupply"] = "有"
            inputdata["HeatsourceSystem"][id_ref_c2]["isSimultaneousSupply"] = "有"
            inputdata["HeatsourceSystem"][id_ref_h1]["isSimultaneousSupply"] = "有"
            inputdata["HeatsourceSystem"][id_ref_h2]["isSimultaneousSupply"] = "有"

            # 二次ポンプ群
            id_pump_c1 = inputdata["AirHandlingSystem"][inputdata["AirConditioningZone"][room_zone_name]["AHU_cooling_insideLoad"]]["Pump_cooling"]
            id_pump_c2 = inputdata["AirHandlingSystem"][inputdata["AirConditioningZone"][room_zone_name]["AHU_cooling_outdoorLoad"]]["Pump_cooling"]
            id_pump_h1 = inputdata["AirHandlingSystem"][inputdata["AirConditioningZone"][room_zone_name]["AHU_heating_insideLoad"]]["Pump_heating"]
            id_pump_h2 = inputdata["AirHandlingSystem"][inputdata["AirConditioningZone"][room_zone_name]["AHU_heating_outdoorLoad"]]["Pump_heating"]

            inputdata["SecondaryPumpSystem"][id_pump_c1]["isSimultaneousSupply"] = "有"
            inputdata["SecondaryPumpSystem"][id_pump_c2]["isSimultaneousSupply"] = "有"
            inputdata["SecondaryPumpSystem"][id_pump_h1]["isSimultaneousSupply"] = "有"
            inputdata["SecondaryPumpSystem"][id_pump_h2]["isSimultaneousSupply"] = "有"

        elif inputdata["AirConditioningZone"][room_zone_name]["isSimultaneousSupply"] == "有（室負荷）":

            # 空調機群
            inputdata["AirHandlingSystem"][inputdata["AirConditioningZone"][room_zone_name]["AHU_cooling_insideLoad"]]["isSimultaneousSupply_cooling"] = "有"
            inputdata["AirHandlingSystem"][inputdata["AirConditioningZone"][room_zone_name]["AHU_heating_insideLoad"]]["isSimultaneousSupply_heating"] = "有"

            # 熱源群
            id_ref_c1 = inputdata["AirHandlingSystem"][inputdata["AirConditioningZone"][room_zone_name]["AHU_cooling_insideLoad"]]["HeatSource_cooling"]
            id_ref_h1 = inputdata["AirHandlingSystem"][inputdata["AirConditioningZone"][room_zone_name]["AHU_heating_insideLoad"]]["HeatSource_heating"]

            inputdata["HeatsourceSystem"][id_ref_c1]["isSimultaneousSupply"] = "有"
            inputdata["HeatsourceSystem"][id_ref_h1]["isSimultaneousSupply"] = "有"

            # 二次ポンプ群
            id_pump_c1 = inputdata["AirHandlingSystem"][inputdata["AirConditioningZone"][room_zone_name]["AHU_cooling_insideLoad"]]["Pump_cooling"]
            id_pump_h1 = inputdata["AirHandlingSystem"][inputdata["AirConditioningZone"][room_zone_name]["AHU_heating_insideLoad"]]["Pump_heating"]

            inputdata["SecondaryPumpSystem"][id_pump_c1]["isSimultaneousSupply"] = "有"
            inputdata["SecondaryPumpSystem"][id_pump_h1]["isSimultaneousSupply"] = "有"

        elif inputdata["AirConditioningZone"][room_zone_name]["isSimultaneousSupply"] == "有（外気負荷）":

            # 空調機群
            inputdata["AirHandlingSystem"][inputdata["AirConditioningZone"][room_zone_name]["AHU_cooling_outdoorLoad"]]["isSimultaneousSupply_cooling"] = "有"
            inputdata["AirHandlingSystem"][inputdata["AirConditioningZone"][room_zone_name]["AHU_heating_outdoorLoad"]]["isSimultaneousSupply_heating"] = "有"

            # 熱源群
            id_ref_c2 = inputdata["AirHandlingSystem"][inputdata["AirConditioningZone"][room_zone_name]["AHU_cooling_outdoorLoad"]]["HeatSource_cooling"]
            id_ref_h2 = inputdata["AirHandlingSystem"][inputdata["AirConditioningZone"][room_zone_name]["AHU_heating_outdoorLoad"]]["HeatSource_heating"]

            inputdata["HeatsourceSystem"][id_ref_c2]["isSimultaneousSupply"] = "有"
            inputdata["HeatsourceSystem"][id_ref_h2]["isSimultaneousSupply"] = "有"

            # 二次ポンプ群
            id_pump_c2 = inputdata["AirHandlingSystem"][inputdata["AirConditioningZone"][room_zone_name]["AHU_cooling_outdoorLoad"]]["Pump_cooling"]
            id_pump_h2 = inputdata["AirHandlingSystem"][inputdata["AirConditioningZone"][room_zone_name]["AHU_heating_outdoorLoad"]]["Pump_heating"]

            inputdata["SecondaryPumpSystem"][id_pump_c2]["isSimultaneousSupply"] = "有"
            inputdata["SecondaryPumpSystem"][id_pump_h2]["isSimultaneousSupply"] = "有"

    # 両方とも冷暖同時なら、その空調機群は冷暖同時運転可能とする。
    for ahu_name in inputdata["AirHandlingSystem"]:

        if (inputdata["AirHandlingSystem"][ahu_name]["isSimultaneousSupply_cooling"] == "有") and \
                (inputdata["AirHandlingSystem"][ahu_name]["isSimultaneousSupply_heating"] == "有"):
            inputdata["AirHandlingSystem"][ahu_name]["isSimultaneousSupply"] = "有"

    #----------------------------------------------------------------------------------
    # 空調機群が処理する日積算室負荷（解説書 2.5.1）
    #----------------------------------------------------------------------------------
    for room_zone_name in inputdata["AirConditioningZone"]:
        # 室内負荷処理用空調機群の名称
        ahu_name = inputdata["AirConditioningZone"][room_zone_name]["AHU_cooling_insideLoad"]

        # 当該空調機群が熱を供給する時刻別室負荷を積算する。
        resultJson["AHU"][ahu_name]["Qroom_hourly"] += resultJson["Qroom"][room_zone_name]["Qroom_hourly"]

    #----------------------------------------------------------------------------------
    # 空調機群の運転時間（解説書 2.5.2）
    #----------------------------------------------------------------------------------

    for room_zone_name in inputdata["AirConditioningZone"]:
        # 室内負荷処理用空調機群の名称
        ahu_name = inputdata["AirConditioningZone"][room_zone_name]["AHU_cooling_insideLoad"]

        # 室の空調有無 roomScheduleRoom（365×24）を加算
        resultJson["AHU"][ahu_name]["schedule"] += roomScheduleRoom[room_zone_name]

    for room_zone_name in inputdata["AirConditioningZone"]:
        # 外気負荷処理用空調機群の名称
        ahu_name = inputdata["AirConditioningZone"][room_zone_name]["AHU_cooling_outdoorLoad"]

        # 室の空調有無 roomScheduleRoom（365×24）を加算
        resultJson["AHU"][ahu_name]["schedule"] += roomScheduleRoom[room_zone_name]

    # 各空調機群の運転時間
    for ahu_name in inputdata["AirHandlingSystem"]:
        # 運転スケジュールの和が「1以上（どこか一部屋は動いている）」であれば、空調機は稼働しているとする。
        resultJson["AHU"][ahu_name]["schedule"][resultJson["AHU"][ahu_name]["schedule"] > 1] = 1

        # 時刻別の外気エンタルピー
        resultJson["AHU"][ahu_name]["Hoa_hourly"] = Hoa_hourly

    #----------------------------------------------------------------------------------
    # 外気負荷[kW]の算出（解説書 2.5.3）
    #----------------------------------------------------------------------------------

    # 外気導入量 [m3/h]
    for ahu_name in inputdata["AirHandlingSystem"]:
        inputdata["AirHandlingSystem"][ahu_name]["outdoorAirVolume_cooling"] = 0
        inputdata["AirHandlingSystem"][ahu_name]["outdoorAirVolume_heating"] = 0

    for room_zone_name in inputdata["AirConditioningZone"]:

        # 各室の外気導入量 [m3/h]
        if "room_usage_condition" in inputdata["SpecialInputData"]:  # SP-9シートで任意の入力がされている場合

            inputdata["AirConditioningZone"][room_zone_name]["outdoorAirVolume"] = \
                bc.get_roomOutdoorAirVolume(
                    inputdata["AirConditioningZone"][room_zone_name]["buildingType"],
                    inputdata["AirConditioningZone"][room_zone_name]["roomType"],
                    inputdata["SpecialInputData"]["room_usage_condition"]
                ) * inputdata["AirConditioningZone"][room_zone_name]["zoneArea"]

        else:

            inputdata["AirConditioningZone"][room_zone_name]["outdoorAirVolume"] = \
                bc.get_roomOutdoorAirVolume(
                    inputdata["AirConditioningZone"][room_zone_name]["buildingType"],
                    inputdata["AirConditioningZone"][room_zone_name]["roomType"]
                ) * inputdata["AirConditioningZone"][room_zone_name]["zoneArea"]

        # 冷房期間における外気風量 [m3/h]
        inputdata["AirHandlingSystem"][inputdata["AirConditioningZone"][room_zone_name]["AHU_cooling_outdoorLoad"]]["outdoorAirVolume_cooling"] += \
            inputdata["AirConditioningZone"][room_zone_name]["outdoorAirVolume"]

        # 暖房期間における外気風量 [m3/h]
        inputdata["AirHandlingSystem"][inputdata["AirConditioningZone"][room_zone_name]["AHU_heating_outdoorLoad"]]["outdoorAirVolume_heating"] += \
            inputdata["AirConditioningZone"][room_zone_name]["outdoorAirVolume"]

    # 全熱交換効率の補正
    for ahu_name in inputdata["AirHandlingSystem"]:

        # 冷房運転時の補正
        if inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioCooling"] != None:
            ahuaexeff = inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioCooling"] / 100
            aexCeff = 1 - ((1 / 0.85) - 1) * (1 - ahuaexeff) / ahuaexeff
            aexCtol = 0.95
            aexCbal = 0.67
            inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioCooling"] = \
                ahuaexeff * aexCeff * aexCtol * aexCbal

        # 暖房運転時の補正
        if inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioHeating"] != None:
            ahuaexeff = inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioHeating"] / 100
            aexCeff = 1 - ((1 / 0.85) - 1) * (1 - ahuaexeff) / ahuaexeff
            aexCtol = 0.95
            aexCbal = 0.67
            inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioHeating"] = \
                ahuaexeff * aexCeff * aexCtol * aexCbal

    # 外気負荷[kW]
    for ahu_name in inputdata["AirHandlingSystem"]:

        for dd in range(0, 365):
            for hh in range(0, 24):

                if resultJson["AHU"][ahu_name]["schedule"][dd][hh] > 0:  # 空調機が稼働する場合

                    # 運転モードによって場合分け
                    if ac_mode[dd] == "暖房":

                        # 外気導入量 [m3/h]
                        ahuVoa = inputdata["AirHandlingSystem"][ahu_name]["outdoorAirVolume_heating"]
                        # 全熱交換風量 [m3/h]
                        ahuaexV = inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangerAirVolume"]

                        # 全熱交換風量（0以上、外気導入量以下とする）
                        if ahuaexV > ahuVoa:
                            ahuaexV = ahuVoa
                        elif ahuaexV <= 0:
                            ahuaexV = 0

                            # 外気負荷の算出
                        if inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioHeating"] == None:  # 全熱交換器がない場合

                            resultJson["AHU"][ahu_name]["Qoa_hourly"][dd][hh] = \
                                (resultJson["AHU"][ahu_name]["Hoa_hourly"][dd][hh] - resultJson["schedule"]["room_enthalpy"][dd][hh]) * inputdata["AirHandlingSystem"][ahu_name][
                                    "outdoorAirVolume_heating"] * 1.293 / 3600

                        else:  # 全熱交換器がある場合

                            if (resultJson["AHU"][ahu_name]["Hoa_hourly"][dd][hh] > resultJson["schedule"]["room_enthalpy"][dd][hh]) and (
                                    inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangerControl"] == "有"):

                                # バイパス有の場合はそのまま外気導入する。
                                resultJson["AHU"][ahu_name]["Qoa_hourly"][dd][hh] = \
                                    (resultJson["AHU"][ahu_name]["Hoa_hourly"][dd][hh] - resultJson["schedule"]["room_enthalpy"][dd][hh]) * \
                                    inputdata["AirHandlingSystem"][ahu_name]["outdoorAirVolume_heating"] * 1.293 / 3600

                            else:

                                # 全熱交換器による外気負荷削減を見込む。
                                resultJson["AHU"][ahu_name]["Qoa_hourly"][dd][hh] = \
                                    (resultJson["AHU"][ahu_name]["Hoa_hourly"][dd][hh] - resultJson["schedule"]["room_enthalpy"][dd][hh]) * \
                                    (inputdata["AirHandlingSystem"][ahu_name]["outdoorAirVolume_heating"] -
                                     ahuaexV * inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioHeating"]) * 1.293 / 3600


                    elif (ac_mode[dd] == "中間") or (ac_mode[dd] == "冷房"):

                        ahuVoa = inputdata["AirHandlingSystem"][ahu_name]["outdoorAirVolume_cooling"]
                        ahuaexV = inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangerAirVolume"]

                        # 全熱交換風量（0以上、外気導入量以下とする）
                        if ahuaexV > ahuVoa:
                            ahuaexV = ahuVoa
                        elif ahuaexV <= 0:
                            ahuaexV = 0

                        # 外気負荷の算出
                        if inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioCooling"] == None:  # 全熱交換器がない場合

                            resultJson["AHU"][ahu_name]["Qoa_hourly"][dd][hh] = \
                                (resultJson["AHU"][ahu_name]["Hoa_hourly"][dd][hh] - resultJson["schedule"]["room_enthalpy"][dd][hh]) * inputdata["AirHandlingSystem"][ahu_name][
                                    "outdoorAirVolume_cooling"] * 1.293 / 3600

                        else:  # 全熱交換器がある場合

                            if (resultJson["AHU"][ahu_name]["Hoa_hourly"][dd][hh] < resultJson["schedule"]["room_enthalpy"][dd][hh]) and (
                                    inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangerControl"] == "有"):

                                # バイパス有の場合はそのまま外気導入する。
                                resultJson["AHU"][ahu_name]["Qoa_hourly"][dd][hh] = \
                                    (resultJson["AHU"][ahu_name]["Hoa_hourly"][dd][hh] - resultJson["schedule"]["room_enthalpy"][dd][hh]) * \
                                    inputdata["AirHandlingSystem"][ahu_name]["outdoorAirVolume_cooling"] * 1.293 / 3600

                            else:  # 全熱交換器がある場合

                                # 全熱交換器による外気負荷削減を見込む。
                                resultJson["AHU"][ahu_name]["Qoa_hourly"][dd][hh] = \
                                    (resultJson["AHU"][ahu_name]["Hoa_hourly"][dd][hh] - resultJson["schedule"]["room_enthalpy"][dd][hh]) * \
                                    (inputdata["AirHandlingSystem"][ahu_name]["outdoorAirVolume_cooling"] -
                                     ahuaexV * inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioCooling"]) * 1.293 / 3600

    #----------------------------------------------------------------------------------
    # 外気冷房制御による負荷削減量（解説書 2.5.4）
    #----------------------------------------------------------------------------------

    for ahu_name in inputdata["AirHandlingSystem"]:

        for dd in range(0, 365):
            for hh in range(0, 24):

                if resultJson["AHU"][ahu_name]["schedule"][dd][hh] > 0:  # 空調機が稼働する場合

                    # 外気冷房効果の推定
                    if (inputdata["AirHandlingSystem"][ahu_name]["isEconomizer"] == "有") and (resultJson["AHU"][ahu_name]["Qroom_hourly"][dd][hh] > 0):  # 外気冷房があり、室負荷が冷房要求であれば

                        # 外気冷房運転時の外気風量 [kg/s]
                        resultJson["AHU"][ahu_name]["Economizer"]["AHUVovc"][dd][hh] = \
                            resultJson["AHU"][ahu_name]["Qroom_hourly"][dd][hh] / \
                            ((resultJson["schedule"]["room_enthalpy"][dd][hh] - resultJson["AHU"][ahu_name]["Hoa_hourly"][dd][hh]) * (3600 / 1000))

                        # 上限・下限
                        if resultJson["AHU"][ahu_name]["Economizer"]["AHUVovc"][dd][hh] < inputdata["AirHandlingSystem"][ahu_name]["outdoorAirVolume_cooling"] * 1.293 / 3600:

                            # 下限（外気取入量） [m3/h]→[kg/s]
                            resultJson["AHU"][ahu_name]["Economizer"]["AHUVovc"][dd][hh] = inputdata["AirHandlingSystem"][ahu_name]["outdoorAirVolume_cooling"] * 1.293 / 3600

                        elif resultJson["AHU"][ahu_name]["Economizer"]["AHUVovc"][dd][hh] > inputdata["AirHandlingSystem"][ahu_name]["EconomizerMaxAirVolume"] * 1.293 / 3600:

                            # 上限（給気風量) [m3/h]→[kg/s]
                            resultJson["AHU"][ahu_name]["Economizer"]["AHUVovc"][dd][hh] = inputdata["AirHandlingSystem"][ahu_name]["EconomizerMaxAirVolume"] * 1.293 / 3600

                        # 追加すべき外気量（外気冷房用の追加分のみ）[kg/s]
                        resultJson["AHU"][ahu_name]["Economizer"]["AHUVovc"][dd][hh] = \
                            resultJson["AHU"][ahu_name]["Economizer"]["AHUVovc"][dd][hh] - inputdata["AirHandlingSystem"][ahu_name]["outdoorAirVolume_cooling"] * 1.293 / 3600

                    # 外気冷房による負荷削減効果 [MJ/day]
                    if inputdata["AirHandlingSystem"][ahu_name]["isEconomizer"] == "有":  # 外気冷房があれば

                        if resultJson["AHU"][ahu_name]["Economizer"]["AHUVovc"][dd][hh] > 0:  # 外冷時風量＞０であれば

                            resultJson["AHU"][ahu_name]["Economizer"]["Qahu_oac"][dd][hh] = \
                                resultJson["AHU"][ahu_name]["Economizer"]["AHUVovc"][dd][hh] * (
                                            resultJson["schedule"]["room_enthalpy"][dd][hh] - resultJson["AHU"][ahu_name]["Hoa_hourly"][dd][hh]) * 3600 / 1000

    #----------------------------------------------------------------------------------
    # 日積算空調負荷 Qahu_c, Qahu_h の算出（解説書 2.5.5）
    #----------------------------------------------------------------------------------

    for ahu_name in inputdata["AirHandlingSystem"]:

        for dd in range(0, 365):
            for hh in range(0, 24):

                if resultJson["AHU"][ahu_name]["schedule"][dd][hh] > 0:  # 空調機が稼働する場合

                    if inputdata["AirHandlingSystem"][ahu_name]["isOutdoorAirCut"] == "無":  # 外気カットがない場合
                        resultJson["AHU"][ahu_name]["Qahu_hourly"][dd][hh] = \
                            resultJson["AHU"][ahu_name]["Qroom_hourly"][dd][hh] + resultJson["AHU"][ahu_name]["Qoa_hourly"][dd][hh] * 3600 / 1000
                    else:
                        if hh != 0 and resultJson["AHU"][ahu_name]["schedule"][dd][hh - 1] == 0:  # 起動時（前の時刻が停止状態）であれば
                            resultJson["AHU"][ahu_name]["Qahu_hourly"][dd][hh] = resultJson["AHU"][ahu_name]["Qroom_hourly"][dd][hh]
                        else:
                            resultJson["AHU"][ahu_name]["Qahu_hourly"][dd][hh] = \
                                resultJson["AHU"][ahu_name]["Qroom_hourly"][dd][hh] + resultJson["AHU"][ahu_name]["Qoa_hourly"][dd][hh] * 3600 / 1000

    print('空調負荷計算完了')

    if debug:  # pragma: no cover

        for ahu_name in inputdata["AirHandlingSystem"]:
            # 外気負荷のグラフ化
            mf.hourlyplot(resultJson["AHU"][ahu_name]["Qoa_hourly"], "外気負荷： " + ahu_name, "b", "時刻別外気負荷")
            # 外気冷房効果のグラフ化
            mf.hourlyplot(resultJson["AHU"][ahu_name]["Economizer"]["Qahu_oac"], "外気冷房による削減熱量： " + ahu_name, "b", "時刻別外気冷房効果")
            mf.hourlyplot(resultJson["AHU"][ahu_name]["Economizer"]["AHUVovc"], "外気冷房時の風量： " + ahu_name, "b", "時刻別外気冷房時風量")
            # 空調負荷のグラフ化
            mf.hourlyplot(resultJson["AHU"][ahu_name]["Qahu_hourly"], "空調負荷： " + ahu_name, "b", "時刻別空調負荷")

    #----------------------------------------------------------------------------------
    # 任意評定用　空調負荷（ SP-10 ）
    #----------------------------------------------------------------------------------

    if "SpecialInputData" in inputdata:
        if "Qahu" in inputdata["SpecialInputData"]:

            for ahu_name in inputdata["SpecialInputData"]["Qahu"]:  # SP-10シートに入力された空調機群毎に処理
                if ahu_name in resultJson["AHU"]:  # SP-10シートに入力された室が空調機群として存在していれば

                    for dd in range(0, 365):
                        for hh in range(0, 24):
                            # 空調負荷[kW] → [MJ/h]
                            resultJson["AHU"][ahu_name]["Qahu_hourly"][dd][hh] = inputdata["SpecialInputData"]["Qahu"][ahu_name][dd][hh] * 3600 / 1000
                            # 外気冷房は強制的に0とする（既に見込まれているものとする）
                            resultJson["AHU"][ahu_name]["Economizer"]["Qahu_oac"][dd][hh] = 0

    #----------------------------------------------------------------------------------
    # 空調機群の負荷率（解説書 2.5.6）
    #----------------------------------------------------------------------------------

    for ahu_name in inputdata["AirHandlingSystem"]:

        for dd in range(0, 365):
            for hh in range(0, 24):

                if resultJson["AHU"][ahu_name]["schedule"][dd][hh] > 0:  # 空調機が稼働する場合

                    # 冷暖同時運転が「有」である場合（季節に依らず、冷却コイル負荷も加熱コイル負荷も処理する）
                    if inputdata["AirHandlingSystem"][ahu_name]["isSimultaneousSupply"] == "有":

                        if resultJson["AHU"][ahu_name]["Qahu_hourly"][dd][hh] >= 0:  # 冷房負荷の場合
                            # 冷房時の負荷率 [-]
                            resultJson["AHU"][ahu_name]["load_ratio"][dd][hh] = \
                                resultJson["AHU"][ahu_name]["Qahu_hourly"][dd][hh] * 1000 / 3600 / inputdata["AirHandlingSystem"][ahu_name]["RatedCapacityCooling"]
                        else:
                            # 暖房時の負荷率 [-]
                            resultJson["AHU"][ahu_name]["load_ratio"][dd][hh] = \
                                (-1) * resultJson["AHU"][ahu_name]["Qahu_hourly"][dd][hh] * 1000 / 3600 / inputdata["AirHandlingSystem"][ahu_name]["RatedCapacityHeating"]

                    # 冷暖同時供給が「無」である場合（季節により、冷却コイル負荷か加熱コイル負荷のどちらか一方を処理する）
                    elif inputdata["AirHandlingSystem"][ahu_name]["isSimultaneousSupply"] == "無":

                        # 冷房期、中間期の場合
                        if ac_mode[dd] == "冷房" or ac_mode[dd] == "中間":

                            if resultJson["AHU"][ahu_name]["Qahu_hourly"][dd][hh] > 0:  # 冷房負荷の場合
                                resultJson["AHU"][ahu_name]["load_ratio"][dd][hh] = \
                                    resultJson["AHU"][ahu_name]["Qahu_hourly"][dd][hh] * 1000 / 3600 / inputdata["AirHandlingSystem"][ahu_name]["RatedCapacityCooling"]
                            else:
                                resultJson["AHU"][ahu_name]["load_ratio"][dd][hh] = 0.01


                        # 暖房期の場合
                        elif ac_mode[dd] == "暖房":

                            if resultJson["AHU"][ahu_name]["Qahu_hourly"][dd][hh] < 0:  # 暖房負荷の場合
                                resultJson["AHU"][ahu_name]["load_ratio"][dd][hh] = \
                                    (-1) * resultJson["AHU"][ahu_name]["Qahu_hourly"][dd][hh] * 1000 / 3600 / inputdata["AirHandlingSystem"][ahu_name]["RatedCapacityHeating"]
                            else:
                                resultJson["AHU"][ahu_name]["load_ratio"][dd][hh] = 0.01

    if debug:  # pragma: no cover

        for ahu_name in inputdata["AirHandlingSystem"]:
            # 空調負荷率のグラフ化
            mf.hourlyplot(resultJson["AHU"][ahu_name]["load_ratio"], "空調負荷率： " + ahu_name, "b", "時刻別負荷率")

    #----------------------------------------------------------------------------------
    # 風量制御方式によって定まる係数（解説書 2.5.7）
    #----------------------------------------------------------------------------------

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

    for ahu_name in inputdata["AirHandlingSystem"]:

        for unit_id, unit_configure in enumerate(inputdata["AirHandlingSystem"][ahu_name]["AirHandlingUnit"]):

            # 係数の取得
            if unit_configure["FanControlType"] in FLOWCONTROL.keys():

                a4 = FLOWCONTROL[unit_configure["FanControlType"]]["a4"]
                a3 = FLOWCONTROL[unit_configure["FanControlType"]]["a3"]
                a2 = FLOWCONTROL[unit_configure["FanControlType"]]["a2"]
                a1 = FLOWCONTROL[unit_configure["FanControlType"]]["a1"]
                a0 = FLOWCONTROL[unit_configure["FanControlType"]]["a0"]

                if unit_configure["FanMinOpeningRate"] == None:
                    Vmin = 1
                else:
                    Vmin = unit_configure["FanMinOpeningRate"] / 100

            elif unit_configure["FanControlType"] == "無":

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

                    if resultJson["AHU"][ahu_name]["schedule"][dd][hh] > 0:
                        # 送風機等の消費電力量 [MWh] = 消費電力[kW] × 効果率[-] × 1時間
                        resultJson["AHU"][ahu_name]["E_fan_hourly"][dd][hh] += \
                            inputdata["AirHandlingSystem"][ahu_name]["AirHandlingUnit"][unit_id]["FanPowerConsumption_total"] * \
                            ahu_control_performance_curve(resultJson["AHU"][ahu_name]["load_ratio"][dd][hh], a4, a3, a2, a1, a0, Vmin) / 1000

                        # 運転時間の合計 h
                        resultJson["AHU"][ahu_name]["Tahu_total"] += 1

    #----------------------------------------------------------------------------------
    # 全熱交換器の消費電力 （解説書 2.5.11）
    #----------------------------------------------------------------------------------

    for ahu_name in inputdata["AirHandlingSystem"]:
        for dd in range(0, 365):
            for hh in range(0, 24):

                if resultJson["AHU"][ahu_name]["schedule"][dd][hh] > 0:  # 空調機が稼働する場合

                    # 全熱交換器の消費電力量 MWh
                    resultJson["AHU"][ahu_name]["E_aex_hourly"][dd][hh] += \
                        inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangerPowerConsumption"] / 1000

    #----------------------------------------------------------------------------------
    # 空調機群の年間一次エネルギー消費量 （解説書 2.5.12）
    #----------------------------------------------------------------------------------

    # 送風機と全熱交換器の消費電力の合計 MWh
    for ahu_name in inputdata["AirHandlingSystem"]:

        for dd in range(0, 365):
            for hh in range(0, 24):
                resultJson["AHU"][ahu_name]["Eahu_total"] += \
                    resultJson["AHU"][ahu_name]["E_fan_hourly"][dd][hh] + resultJson["AHU"][ahu_name]["E_aex_hourly"][dd][hh]

                # 空調機群（送風機）のエネルギー消費量 MWh
                resultJson["energy"]["E_ahu_fan"] += resultJson["AHU"][ahu_name]["E_fan_hourly"][dd][hh]

                # 空調機群（全熱交換器）のエネルギー消費量 MWh
                resultJson["energy"]["E_ahu_aex"] += resultJson["AHU"][ahu_name]["E_aex_hourly"][dd][hh]

                # 空調機群（送風機+全熱交換器）のエネルギー消費量 MWh/day
                resultJson["energy"]["E_fan_MWh_day"][dd] += \
                    resultJson["AHU"][ahu_name]["E_fan_hourly"][dd][hh] + resultJson["AHU"][ahu_name]["E_aex_hourly"][dd][hh]

    print('空調機群のエネルギー消費量計算完了')

    if debug:  # pragma: no cover

        for ahu_name in inputdata["AirHandlingSystem"]:
            mf.hourlyplot(resultJson["AHU"][ahu_name]["E_fan_hourly"], "送風機の消費電力： " + ahu_name, "b", "時刻別送風機消費電力")
            mf.hourlyplot(resultJson["AHU"][ahu_name]["E_aex_hourly"], "全熱交換器の消費電力： " + ahu_name, "b", "時刻別全熱交換器消費電力")

            print("----" + ahu_name + "----")
            print(resultJson["AHU"][ahu_name]["Eahu_total"])
            print(resultJson["AHU"][ahu_name]["Tahu_total"])

            mf.histgram_matrix_ahu(resultJson["AHU"][ahu_name]["load_ratio"], resultJson["AHU"][ahu_name]["Qahu_hourly"], resultJson["AHU"][ahu_name]["E_fan_hourly"])

    #----------------------------------------------------------------------------------
    # 二次ポンプ群の一次エネルギー消費量（解説書 2.6）
    #----------------------------------------------------------------------------------

    # 二次ポンプが空欄であった場合、ダミーの仮想ポンプを追加する。
    number = 0
    for ahu_name in inputdata["AirHandlingSystem"]:

        if inputdata["AirHandlingSystem"][ahu_name]["Pump_cooling"] == None:
            inputdata["AirHandlingSystem"][ahu_name]["Pump_cooling"] = "dummyPump_" + str(number)

            inputdata["SecondaryPumpSystem"]["dummyPump_" + str(number)] = {
                "冷房": {
                    "TemperatureDifference": 0,
                    "isStagingControl": "無",
                    "SecondaryPump": [
                        {
                            "Number": 0,
                            "RatedWaterFlowRate": 0,
                            "RatedPowerConsumption": 0,
                            "ContolType": "無",
                            "MinOpeningRate": 100,
                        }
                    ]
                }
            }

            number += 1

        if inputdata["AirHandlingSystem"][ahu_name]["Pump_heating"] == None:
            inputdata["AirHandlingSystem"][ahu_name]["Pump_heating"] = "dummyPump_" + str(number)

            inputdata["SecondaryPumpSystem"]["dummyPump_" + str(number)] = {
                "暖房": {
                    "TemperatureDifference": 0,
                    "isStagingControl": "無",
                    "SecondaryPump": [
                        {
                            "Number": 0,
                            "RatedWaterFlowRate": 0,
                            "RatedPowerConsumption": 0,
                            "ContolType": "無",
                            "MinOpeningRate": 100,
                        }
                    ]
                }
            }

            number += 1

    # 冷房と暖房の二次ポンプ群に分ける。
    for pump_original_name in inputdata["SecondaryPumpSystem"]:

        if "冷房" in inputdata["SecondaryPumpSystem"][pump_original_name]:
            # 二次ポンプ群名称を置き換え
            pump_name = pump_original_name + "_冷房"
            inputdata["PUMP"][pump_name] = inputdata["SecondaryPumpSystem"][pump_original_name]["冷房"]
            inputdata["PUMP"][pump_name]["mode"] = "cooling"

        if "暖房" in inputdata["SecondaryPumpSystem"][pump_original_name]:
            # 二次ポンプ群名称を置き換え
            pump_name = pump_original_name + "_暖房"
            inputdata["PUMP"][pump_name] = inputdata["SecondaryPumpSystem"][pump_original_name]["暖房"]
            inputdata["PUMP"][pump_name]["mode"] = "heating"

    #----------------------------------------------------------------------------------
    # 結果格納用の変数 resultJson　（二次ポンプ群）
    #----------------------------------------------------------------------------------

    for pump_name in inputdata["PUMP"]:
        resultJson["PUMP"][pump_name] = {

            "schedule": np.zeros((365, 24)),  # ポンプ時刻別運転スケジュール

            "Qps_hourly": np.zeros((365, 24)),  # ポンプ負荷 [MJ/h]

            "heatloss_fan": np.zeros((365, 24)),  # ファン発熱量 [MJ/h]
            "heatloss_pump": np.zeros((365, 24)),  # ポンプの発熱量 [MJ/h]

            "load_ratio": np.zeros((365, 24)),  # 時刻別の負荷率
            "number_of_operation": np.zeros((365, 24)),  # 時刻別の負荷率マトリックス番号

            "E_pump": 0,
            "E_pump_MWh_day": np.zeros(365),
            "E_pump_hourly": np.zeros((365, 24))  # ポンプ電力消費量[MWh]

        }

    #----------------------------------------------------------------------------------
    # 二次ポンプ機群全体のスペックを整理する。
    #----------------------------------------------------------------------------------

    for pump_name in inputdata["PUMP"]:

        inputdata["PUMP"][pump_name]["AHU_list"] = set()  # 接続される空調機群
        inputdata["PUMP"][pump_name]["Qpsr"] = 0  # ポンプ定格能力
        inputdata["PUMP"][pump_name]["ContolType"] = set()  # 全台回転数制御かどうか（台数制御がない場合のみ有効）
        inputdata["PUMP"][pump_name]["MinOpeningRate"] = 100  # 変流量時最小負荷率の最小値（台数制御がない場合のみ有効）

        # ポンプの台数
        inputdata["PUMP"][pump_name]["number_of_pumps"] = len(inputdata["PUMP"][pump_name]["SecondaryPump"])

        # 二次ポンプの能力のリスト
        inputdata["PUMP"][pump_name]["Qpsr_list"] = []

        # 二次ポンプ群全体の定格消費電力の合計
        inputdata["PUMP"][pump_name]["RatedPowerConsumption_total"] = 0

        for unit_id, unit_configure in enumerate(inputdata["PUMP"][pump_name]["SecondaryPump"]):

            # 流量の合計（台数×流量）
            inputdata["PUMP"][pump_name]["SecondaryPump"][unit_id]["RatedWaterFlowRate_total"] = \
                inputdata["PUMP"][pump_name]["SecondaryPump"][unit_id]["RatedWaterFlowRate"] * \
                inputdata["PUMP"][pump_name]["SecondaryPump"][unit_id]["Number"]

            # 消費電力の合計（消費電力×流量）
            inputdata["PUMP"][pump_name]["SecondaryPump"][unit_id]["RatedPowerConsumption_total"] = \
                inputdata["PUMP"][pump_name]["SecondaryPump"][unit_id]["RatedPowerConsumption"] * \
                inputdata["PUMP"][pump_name]["SecondaryPump"][unit_id]["Number"]

            # 二次ポンプ群全体の定格消費電力の合計
            inputdata["PUMP"][pump_name]["RatedPowerConsumption_total"] += \
                inputdata["PUMP"][pump_name]["SecondaryPump"][unit_id]["RatedPowerConsumption_total"]

            # 制御方式
            inputdata["PUMP"][pump_name]["ContolType"].add(inputdata["PUMP"][pump_name]["SecondaryPump"][unit_id]["ContolType"])

            # 変流量時最小負荷率の最小値（台数制御がない場合のみ有効）
            if unit_configure["MinOpeningRate"] == None or np.isnan(unit_configure["MinOpeningRate"]) == True:
                inputdata["PUMP"][pump_name]["MinOpeningRate"] = 100
            elif inputdata["PUMP"][pump_name]["MinOpeningRate"] > unit_configure["MinOpeningRate"]:
                inputdata["PUMP"][pump_name]["MinOpeningRate"] = unit_configure["MinOpeningRate"]

        # 全台回転数制御かどうか（台数制御がない場合のみ有効）
        if "無" in inputdata["PUMP"][pump_name]["ContolType"]:
            inputdata["PUMP"][pump_name]["ContolType"] = "定流量制御がある"
        elif "定流量制御" in inputdata["PUMP"][pump_name]["ContolType"]:
            inputdata["PUMP"][pump_name]["ContolType"] = "定流量制御がある"
        else:
            inputdata["PUMP"][pump_name]["ContolType"] = "すべて変流量制御である"

    # 接続される空調機群
    for ahu_name in inputdata["AirHandlingSystem"]:
        inputdata["PUMP"][inputdata["AirHandlingSystem"][ahu_name]["Pump_cooling"] + "_冷房"]["AHU_list"].add(ahu_name)
        inputdata["PUMP"][inputdata["AirHandlingSystem"][ahu_name]["Pump_heating"] + "_暖房"]["AHU_list"].add(ahu_name)

    #----------------------------------------------------------------------------------
    # 二次ポンプ負荷（解説書 2.6.1）
    #----------------------------------------------------------------------------------

    # 未処理負荷の算出
    for ahu_name in inputdata["AirHandlingSystem"]:

        for dd in range(0, 365):
            for hh in range(0, 24):

                if ac_mode[dd] == "暖房":  # 暖房期である場合

                    # 空調負荷が正の値である場合、かつ、冷暖同時供給が無い場合
                    if (resultJson["AHU"][ahu_name]["Qahu_hourly"][dd][hh] > 0) and \
                            (inputdata["AirHandlingSystem"][ahu_name]["isSimultaneousSupply_heating"] == "無"):
                        resultJson["AHU"][ahu_name]["Qahu_unprocessed"][dd][hh] += (resultJson["AHU"][ahu_name]["Qahu_hourly"][dd][hh])
                        resultJson["AHU"][ahu_name]["Qahu_hourly"][dd][hh] = 0


                elif (ac_mode[dd] == "冷房") or (ac_mode[dd] == "中間"):

                    # 空調負荷が負の値である場合、かつ、冷暖同時供給が無い場合
                    if (resultJson["AHU"][ahu_name]["Qahu_hourly"][dd][hh] < 0) and \
                            (inputdata["AirHandlingSystem"][ahu_name]["isSimultaneousSupply_cooling"] == "無"):
                        resultJson["AHU"][ahu_name]["Qahu_unprocessed"][dd][hh] += (resultJson["AHU"][ahu_name]["Qahu_hourly"][dd][hh])
                        resultJson["AHU"][ahu_name]["Qahu_hourly"][dd][hh] = 0

    # ポンプ負荷の積算
    for pump_name in inputdata["PUMP"]:

        for ahu_name in inputdata["PUMP"][pump_name]["AHU_list"]:

            for dd in range(0, 365):
                for hh in range(0, 24):

                    if inputdata["PUMP"][pump_name]["mode"] == "cooling":  # 冷水ポンプの場合

                        # ファン発熱量 heatloss_fan [MJ/day] の算出（解説書 2.5.10）
                        if inputdata["AirHandlingSystem"][ahu_name]["AHU_type"] == "空調機":
                            # ファン発熱量 MWh * 3600 = MJ/h
                            resultJson["PUMP"][pump_name]["heatloss_fan"][dd][hh] = \
                                k_heatup * resultJson["AHU"][ahu_name]["E_fan_hourly"][dd][hh] * 3600

                        # 日積算ポンプ負荷 Qps [MJ/h] の算出

                        # 空調負荷が正である場合
                        if resultJson["AHU"][ahu_name]["Qahu_hourly"][dd][hh] > 0:

                            if resultJson["AHU"][ahu_name]["Economizer"]["Qahu_oac"][dd][hh] > 0:  # 外冷時はファン発熱量足さない ⇒ 小さな負荷が出てしまう

                                if abs(resultJson["AHU"][ahu_name]["Qahu_hourly"][dd][hh] - resultJson["AHU"][ahu_name]["Economizer"]["Qahu_oac"][dd][hh]) < 1:
                                    resultJson["PUMP"][pump_name]["Qps_hourly"][dd][hh] += 0
                                else:
                                    resultJson["PUMP"][pump_name]["Qps_hourly"][dd][hh] += \
                                        resultJson["AHU"][ahu_name]["Qahu_hourly"][dd][hh] - resultJson["AHU"][ahu_name]["Economizer"]["Qahu_oac"][dd][hh]
                            else:

                                resultJson["PUMP"][pump_name]["Qps_hourly"][dd][hh] += \
                                    resultJson["AHU"][ahu_name]["Qahu_hourly"][dd][hh] - resultJson["AHU"][ahu_name]["Economizer"]["Qahu_oac"][dd][hh] + \
                                    resultJson["PUMP"][pump_name]["heatloss_fan"][dd][hh]


                    elif inputdata["PUMP"][pump_name]["mode"] == "heating":

                        # ファン発熱量 heatloss_fan [MJ/day] の算出（解説書 2.5.10）
                        if inputdata["AirHandlingSystem"][ahu_name]["AHU_type"] == "空調機":
                            # ファン発熱量 MWh * 3600 = MJ/h
                            resultJson["PUMP"][pump_name]["heatloss_fan"][dd][hh] = k_heatup * resultJson["AHU"][ahu_name]["E_fan_hourly"][dd][hh] * 3600

                        # 日積算ポンプ負荷 Qps [MJ/day] の算出<符号逆転させる>
                        # 室負荷が冷房要求である場合において空調負荷が正である場合
                        if resultJson["AHU"][ahu_name]["Qahu_hourly"][dd][hh] < 0:
                            resultJson["PUMP"][pump_name]["Qps_hourly"][dd][hh] += \
                                (-1) * (resultJson["AHU"][ahu_name]["Qahu_hourly"][dd][hh] + resultJson["PUMP"][pump_name]["heatloss_fan"][dd][hh])

    #----------------------------------------------------------------------------------
    # 二次ポンプ群の運転時間（解説書 2.6.2）
    #----------------------------------------------------------------------------------

    for pump_name in inputdata["PUMP"]:

        for ahu_name in inputdata["PUMP"][pump_name]["AHU_list"]:
            resultJson["PUMP"][pump_name]["schedule"] += resultJson["AHU"][ahu_name]["schedule"]

        # 運転スケジュールの和が「1以上（接続されている空調機群の1つは動いている）」であれば、二次ポンプは稼働しているとする。
        resultJson["PUMP"][pump_name]["schedule"][resultJson["PUMP"][pump_name]["schedule"] > 1] = 1

    print('ポンプ負荷計算完了')

    if debug:  # pragma: no cover

        for pump_name in inputdata["PUMP"]:
            # ポンプ負荷のグラフ化
            mf.hourlyplot(resultJson["PUMP"][pump_name]["Qps_hourly"], "ポンプ負荷： " + pump_name, "b", "時刻別ポンプ負荷")

    #----------------------------------------------------------------------------------
    # 二次ポンプ群の仮想定格能力（解説書 2.6.3）
    #----------------------------------------------------------------------------------
    for pump_name in inputdata["PUMP"]:

        for unit_id, unit_configure in enumerate(inputdata["PUMP"][pump_name]["SecondaryPump"]):
            # 二次ポンプの定格処理能力[kW] = [K] * [m3/h] * [kJ/kg・K] * [kg/m3] * [h/s]
            inputdata["PUMP"][pump_name]["SecondaryPump"][unit_id]["Qpsr"] = \
                inputdata["PUMP"][pump_name]["TemperatureDifference"] * unit_configure["RatedWaterFlowRate_total"] * Cw * 1000 / 3600
            inputdata["PUMP"][pump_name]["Qpsr"] += inputdata["PUMP"][pump_name]["SecondaryPump"][unit_id]["Qpsr"]

            inputdata["PUMP"][pump_name]["Qpsr_list"].append(inputdata["PUMP"][pump_name]["SecondaryPump"][unit_id]["Qpsr"])

    #----------------------------------------------------------------------------------
    # 二次ポンプ群の負荷率（解説書 2.6.4）
    #----------------------------------------------------------------------------------

    for pump_name in inputdata["PUMP"]:

        if inputdata["PUMP"][pump_name]["Qpsr"] != 0:  # 仮想ポンプ（二次ポンプがないシステム用の仮想ポンプ）は除く

            for dd in range(0, 365):
                for hh in range(0, 24):

                    if resultJson["PUMP"][pump_name]["schedule"][dd][hh] > 0 and (inputdata["PUMP"][pump_name]["Qpsr"] > 0):
                        # 負荷率 Lpump[-] = [MJ/h] * [kJ/MJ] / [s/h] / [KJ/s]
                        resultJson["PUMP"][pump_name]["load_ratio"][dd][hh] = \
                            (resultJson["PUMP"][pump_name]["Qps_hourly"][dd][hh] * 1000 / 3600) / inputdata["PUMP"][pump_name]["Qpsr"]

    if debug:  # pragma: no cover

        for pump_name in inputdata["PUMP"]:
            # ポンプ負荷率のグラフ化
            mf.hourlyplot(resultJson["PUMP"][pump_name]["load_ratio"], "ポンプ負荷率： " + pump_name, "b", "時刻別ポンプ負荷率")

    #----------------------------------------------------------------------------------
    # 二次ポンプの運転台数
    #----------------------------------------------------------------------------------

    for pump_name in inputdata["PUMP"]:

        if inputdata["PUMP"][pump_name]["Qpsr"] != 0:  # 仮想ポンプ（二次ポンプがないシステム用の仮想ポンプ）は除く

            for dd in range(0, 365):
                for hh in range(0, 24):

                    if resultJson["PUMP"][pump_name]["Qps_hourly"][dd][hh] > 0:

                        if inputdata["PUMP"][pump_name]["isStagingControl"] == "無":  # 台数制御なし

                            # 運転台数（常に最大の台数） → 台数のマトリックスの表示用
                            resultJson["PUMP"][pump_name]["number_of_operation"][dd][hh] = inputdata["PUMP"][pump_name]["number_of_pumps"]


                        elif inputdata["PUMP"][pump_name]["isStagingControl"] == "有":  # 台数制御あり

                            # 運転台数 number_of_operation
                            rr = 0
                            for rr in range(0, inputdata["PUMP"][pump_name]["number_of_pumps"]):

                                # 1台～rr台までの最大能力合計値
                                if np.sum(inputdata["PUMP"][pump_name]["Qpsr_list"][0:rr + 1]) > resultJson["PUMP"][pump_name]["Qps_hourly"][dd][hh] * 1000 / 3600:
                                    break

                            resultJson["PUMP"][pump_name]["number_of_operation"][dd][hh] = rr + 1  # pythonのインデックスと実台数は「1」ずれることに注意。

    #----------------------------------------------------------------------------------
    # 流量制御方式によって定まる係数（解説書 2.6.7）
    #----------------------------------------------------------------------------------

    for pump_name in inputdata["PUMP"]:

        for unit_id, unit_configure in enumerate(inputdata["PUMP"][pump_name]["SecondaryPump"]):

            if unit_configure["ContolType"] in FLOWCONTROL.keys():

                inputdata["PUMP"][pump_name]["SecondaryPump"][unit_id]["a4"] = FLOWCONTROL[unit_configure["ContolType"]]["a4"]
                inputdata["PUMP"][pump_name]["SecondaryPump"][unit_id]["a3"] = FLOWCONTROL[unit_configure["ContolType"]]["a3"]
                inputdata["PUMP"][pump_name]["SecondaryPump"][unit_id]["a2"] = FLOWCONTROL[unit_configure["ContolType"]]["a2"]
                inputdata["PUMP"][pump_name]["SecondaryPump"][unit_id]["a1"] = FLOWCONTROL[unit_configure["ContolType"]]["a1"]
                inputdata["PUMP"][pump_name]["SecondaryPump"][unit_id]["a0"] = FLOWCONTROL[unit_configure["ContolType"]]["a0"]

            elif unit_configure["ContolType"] == "無":

                inputdata["PUMP"][pump_name]["SecondaryPump"][unit_id]["a4"] = 0
                inputdata["PUMP"][pump_name]["SecondaryPump"][unit_id]["a3"] = 0
                inputdata["PUMP"][pump_name]["SecondaryPump"][unit_id]["a2"] = 0
                inputdata["PUMP"][pump_name]["SecondaryPump"][unit_id]["a1"] = 0
                inputdata["PUMP"][pump_name]["SecondaryPump"][unit_id]["a0"] = 1
                inputdata["PUMP"][pump_name]["SecondaryPump"][unit_id]["MinOpeningRate"] = 100

            else:
                raise Exception('制御方式が不正です')

    #----------------------------------------------------------------------------------
    # 二次ポンプ群ごとの消費電力（解説書 2.6.8）
    #----------------------------------------------------------------------------------

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

    for pump_name in inputdata["PUMP"]:

        if inputdata["PUMP"][pump_name]["Qpsr"] != 0:  # 仮想ポンプ（二次ポンプがないシステム用の仮想ポンプ）は除く

            for dd in range(0, 365):
                for hh in range(0, 24):

                    if resultJson["PUMP"][pump_name]["Qps_hourly"][dd][hh] > 0:

                        if inputdata["PUMP"][pump_name]["isStagingControl"] == "無":  # 台数制御なし

                            # 流量制御方式
                            if inputdata["PUMP"][pump_name]["ContolType"] == "すべて変流量制御である":  # 全台VWVであれば

                                # VWVの効果率曲線(1番目の特性を代表して使う)
                                PUMPvwvfac = pump_control_performance_curve(
                                    resultJson["PUMP"][pump_name]["load_ratio"][dd][hh],
                                    inputdata["PUMP"][pump_name]["SecondaryPump"][0]["a4"],
                                    inputdata["PUMP"][pump_name]["SecondaryPump"][0]["a3"],
                                    inputdata["PUMP"][pump_name]["SecondaryPump"][0]["a2"],
                                    inputdata["PUMP"][pump_name]["SecondaryPump"][0]["a1"],
                                    inputdata["PUMP"][pump_name]["SecondaryPump"][0]["a0"],
                                    inputdata["PUMP"][pump_name]["MinOpeningRate"] / 100
                                )

                            else:  # 全台VWVでなければ、定流量とみなす。

                                PUMPvwvfac = pump_control_performance_curve(
                                    resultJson["PUMP"][pump_name]["load_ratio"][dd][hh], 0, 0, 0, 0, 1, 1)

                            # 消費電力（部分負荷特性×定格消費電力）[kW]
                            resultJson["PUMP"][pump_name]["E_pump_hourly"][dd][hh] = PUMPvwvfac * inputdata["PUMP"][pump_name]["RatedPowerConsumption_total"] / 1000


                        elif inputdata["PUMP"][pump_name]["isStagingControl"] == "有":  # 台数制御あり

                            # 定流量ポンプの処理熱量合計、VWVポンプの台数
                            Qtmp_CWV = 0
                            numVWV = resultJson["PUMP"][pump_name]["number_of_operation"][dd][hh]  # 運転台数（定流量＋変流量）

                            for rr in range(0, int(resultJson["PUMP"][pump_name]["number_of_operation"][dd][hh])):

                                if (inputdata["PUMP"][pump_name]["SecondaryPump"][rr]["ContolType"] == "無") or \
                                        (inputdata["PUMP"][pump_name]["SecondaryPump"][rr]["ContolType"] == "定流量制御"):
                                    Qtmp_CWV += inputdata["PUMP"][pump_name]["SecondaryPump"][rr]["Qpsr"]
                                    numVWV = numVWV - 1

                            # 制御を加味した消費エネルギー MxPUMPPower [kW]
                            for rr in range(0, int(resultJson["PUMP"][pump_name]["number_of_operation"][dd][hh])):

                                if (inputdata["PUMP"][pump_name]["SecondaryPump"][rr]["ContolType"] == "無") or \
                                        (inputdata["PUMP"][pump_name]["SecondaryPump"][rr]["ContolType"] == "定流量制御"):

                                    # 定流量制御の効果率
                                    PUMPvwvfac = pump_control_performance_curve(
                                        resultJson["PUMP"][pump_name]["load_ratio"][dd][hh],
                                        0, 0, 0, 0, 1, 1)

                                    resultJson["PUMP"][pump_name]["E_pump_hourly"][dd][hh] += inputdata["PUMP"][pump_name]["SecondaryPump"][rr][
                                                                                                  "RatedPowerConsumption_total"] * PUMPvwvfac / 1000

                                else:

                                    # 変流量ポンプjの負荷率 [-]
                                    tmpL = ((resultJson["PUMP"][pump_name]["Qps_hourly"][dd][hh] * 1000 / 3600 - Qtmp_CWV) / numVWV) \
                                           / inputdata["PUMP"][pump_name]["SecondaryPump"][rr]["Qpsr"]

                                    # 変流量制御による省エネ効果
                                    PUMPvwvfac = pump_control_performance_curve(
                                        tmpL,
                                        inputdata["PUMP"][pump_name]["SecondaryPump"][rr]["a4"],
                                        inputdata["PUMP"][pump_name]["SecondaryPump"][rr]["a3"],
                                        inputdata["PUMP"][pump_name]["SecondaryPump"][rr]["a2"],
                                        inputdata["PUMP"][pump_name]["SecondaryPump"][rr]["a1"],
                                        inputdata["PUMP"][pump_name]["SecondaryPump"][rr]["a0"],
                                        inputdata["PUMP"][pump_name]["SecondaryPump"][rr]["MinOpeningRate"] / 100
                                    )

                                    resultJson["PUMP"][pump_name]["E_pump_hourly"][dd][hh] += inputdata["PUMP"][pump_name]["SecondaryPump"][rr][
                                                                                                  "RatedPowerConsumption_total"] * PUMPvwvfac / 1000

                                    #----------------------------------------------------------------------------------
    # 二次ポンプ群全体の年間一次エネルギー消費量（解説書 2.6.10）
    #----------------------------------------------------------------------------------

    for pump_name in inputdata["PUMP"]:

        for dd in range(0, 365):
            for hh in range(0, 24):
                resultJson["PUMP"][pump_name]["E_pump"] += resultJson["PUMP"][pump_name]["E_pump_hourly"][dd][hh]

                resultJson["energy"]["E_pump"] += resultJson["PUMP"][pump_name]["E_pump_hourly"][dd][hh]
                resultJson["energy"]["E_pump_MWh_day"][dd] += resultJson["PUMP"][pump_name]["E_pump_hourly"][dd][hh]

    print('二次ポンプ群のエネルギー消費量計算完了')

    if debug:  # pragma: no cover

        for ahu_name in inputdata["AirHandlingSystem"]:
            mf.hourlyplot(resultJson["AHU"][ahu_name]["Qahu_unprocessed"], "未処理負荷： " + ahu_name, "b", "未処理負荷")

        for pump_name in inputdata["PUMP"]:
            mf.hourlyplot(resultJson["PUMP"][pump_name]["E_pump_hourly"], "ポンプ消費電力： " + pump_name, "b", "時刻別ポンプ消費電力")

            print("----" + pump_name + "----")
            print(resultJson["PUMP"][pump_name]["E_pump"])

            mf.histgram_matrix_pump(
                resultJson["PUMP"][pump_name]["load_ratio"],
                resultJson["PUMP"][pump_name]["number_of_operation"],
                resultJson["PUMP"][pump_name]["E_pump_hourly"]
            )

    #----------------------------------------------------------------------------------
    # 二次ポンプ群の発熱量 （解説書 2.6.9）
    #----------------------------------------------------------------------------------

    for pump_name in inputdata["PUMP"]:

        for dd in range(0, 365):
            for hh in range(0, 24):

                if resultJson["PUMP"][pump_name]["E_pump_hourly"][dd][hh] > 0:
                    # 二次ポンプ群の発熱量 MJ/h
                    resultJson["PUMP"][pump_name]["heatloss_pump"][dd][hh] = \
                        resultJson["PUMP"][pump_name]["E_pump_hourly"][dd][hh] * k_heatup * 3600

    if debug:  # pragma: no cover

        for pump_name in inputdata["PUMP"]:
            mf.hourlyplot(resultJson["PUMP"][pump_name]["heatloss_pump"], "ポンプ発熱量： " + pump_name, "b", "時刻別ポンプ発熱量")

    #----------------------------------------------------------------------------------
    # 熱源群の一次エネルギー消費量（解説書 2.7）
    #----------------------------------------------------------------------------------

    # モデル格納用変数

    # 冷房と暖房の熱源群に分ける。
    for ref_original_name in inputdata["HeatsourceSystem"]:

        if "冷房" in inputdata["HeatsourceSystem"][ref_original_name]:
            inputdata["REF"][ref_original_name + "_冷房"] = inputdata["HeatsourceSystem"][ref_original_name]["冷房"]
            inputdata["REF"][ref_original_name + "_冷房"]["mode"] = "cooling"

            if "冷房(蓄熱)" in inputdata["HeatsourceSystem"][ref_original_name]:
                inputdata["REF"][ref_original_name + "_冷房_蓄熱"] = inputdata["HeatsourceSystem"][ref_original_name]["冷房(蓄熱)"]
                inputdata["REF"][ref_original_name + "_冷房_蓄熱"]["isStorage"] = "蓄熱"
                inputdata["REF"][ref_original_name + "_冷房_蓄熱"]["mode"] = "cooling"
                inputdata["REF"][ref_original_name + "_冷房"]["isStorage"] = "追掛"
                inputdata["REF"][ref_original_name + "_冷房"]["StorageType"] = inputdata["HeatsourceSystem"][ref_original_name]["冷房(蓄熱)"]["StorageType"]
                inputdata["REF"][ref_original_name + "_冷房"]["StorageSize"] = inputdata["HeatsourceSystem"][ref_original_name]["冷房(蓄熱)"]["StorageSize"]
            else:
                inputdata["REF"][ref_original_name + "_冷房"]["isStorage"] = "無"

        if "暖房" in inputdata["HeatsourceSystem"][ref_original_name]:
            inputdata["REF"][ref_original_name + "_暖房"] = inputdata["HeatsourceSystem"][ref_original_name]["暖房"]
            inputdata["REF"][ref_original_name + "_暖房"]["mode"] = "heating"

            if "暖房(蓄熱)" in inputdata["HeatsourceSystem"][ref_original_name]:
                inputdata["REF"][ref_original_name + "_暖房_蓄熱"] = inputdata["HeatsourceSystem"][ref_original_name]["暖房(蓄熱)"]
                inputdata["REF"][ref_original_name + "_暖房_蓄熱"]["isStorage"] = "蓄熱"
                inputdata["REF"][ref_original_name + "_暖房_蓄熱"]["mode"] = "heating"
                inputdata["REF"][ref_original_name + "_暖房"]["isStorage"] = "追掛"
                inputdata["REF"][ref_original_name + "_暖房"]["StorageType"] = inputdata["HeatsourceSystem"][ref_original_name]["暖房(蓄熱)"]["StorageType"]
                inputdata["REF"][ref_original_name + "_暖房"]["StorageSize"] = inputdata["HeatsourceSystem"][ref_original_name]["暖房(蓄熱)"]["StorageSize"]
            else:
                inputdata["REF"][ref_original_name + "_暖房"]["isStorage"] = "無"

    #----------------------------------------------------------------------------------
    # 蓄熱がある場合の処理（蓄熱槽効率の追加、追掛用熱交換器の検証）
    #----------------------------------------------------------------------------------

    for ref_name in inputdata["REF"]:

        # 蓄熱槽効率
        if inputdata["REF"][ref_name]["isStorage"] == "蓄熱" or inputdata["REF"][ref_name]["isStorage"] == "追掛":

            inputdata["REF"][ref_name]["storageEffratio"] = 0.8
            if inputdata["REF"][ref_name]["StorageType"] == "水蓄熱(混合型)":
                inputdata["REF"][ref_name]["storageEffratio"] = 0.8
            elif inputdata["REF"][ref_name]["StorageType"] == "水蓄熱(成層型)":
                inputdata["REF"][ref_name]["storageEffratio"] = 0.9
            elif inputdata["REF"][ref_name]["StorageType"] == "氷蓄熱":
                inputdata["REF"][ref_name]["storageEffratio"] = 1.0
            else:
                raise Exception("蓄熱槽タイプが不正です")

        # 蓄熱追掛時の熱交換器の追加
        if inputdata["REF"][ref_name]["isStorage"] == "追掛":

            for unit_id, unit_configure in enumerate(inputdata["REF"][ref_name]["Heatsource"]):
                if unit_id == 0 and inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceType"] != "熱交換器":

                    # 1台目が熱交換器では無い場合、熱交換器を追加する。
                    inputdata["REF"][ref_name]["Heatsource"].insert(0,
                                                                    {
                                                                        "HeatsourceType": "熱交換器",
                                                                        "Number": 1.0,
                                                                        "SupplyWaterTempSummer": None,
                                                                        "SupplyWaterTempMiddle": None,
                                                                        "SupplyWaterTempWinter": None,
                                                                        "HeatsourceRatedCapacity": inputdata["REF"][ref_name]["storageEffratio"] * inputdata["REF"][ref_name][
                                                                            "StorageSize"] / 8 * (1000 / 3600),
                                                                        "HeatsourceRatedPowerConsumption": 0,
                                                                        "HeatsourceRatedFuelConsumption": 0,
                                                                        "Heatsource_sub_RatedPowerConsumption": 0,
                                                                        "PrimaryPumpPowerConsumption": 0,
                                                                        "PrimaryPumpContolType": "無",
                                                                        "CoolingTowerCapacity": 0,
                                                                        "CoolingTowerFanPowerConsumption": 0,
                                                                        "CoolingTowerPumpPowerConsumption": 0,
                                                                        "CoolingTowerContolType": "無",
                                                                        "Info": ""
                                                                    }
                                                                    )

                # 1台目以外に熱交換器があればエラーを返す。
                elif unit_id > 0 and inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceType"] == "熱交換器":
                    raise Exception("蓄熱槽があるシステムですが、1台目以外に熱交換器が設定されています")

    #----------------------------------------------------------------------------------
    # 熱源群全体のスペックを整理する。
    #----------------------------------------------------------------------------------

    for ref_name in inputdata["REF"]:

        inputdata["REF"][ref_name]["pump_list"] = set()
        inputdata["REF"][ref_name]["num_of_unit"] = 0

        # 熱源群全体の性能
        inputdata["REF"][ref_name]["Qref_rated"] = 0
        for unit_id, unit_configure in enumerate(inputdata["REF"][ref_name]["Heatsource"]):
            # 定格能力（台数×能力）
            inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedCapacity_total"] = \
                unit_configure["HeatsourceRatedCapacity"] * unit_configure["Number"]

            # 熱源主機の定格消費電力（台数×消費電力）
            inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedPowerConsumption_total"] = \
                unit_configure["HeatsourceRatedPowerConsumption"] * unit_configure["Number"]

            # 熱源主機の定格燃料消費量（台数×燃料消費量）
            inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedFuelConsumption_total"] = \
                unit_configure["HeatsourceRatedFuelConsumption"] * unit_configure["Number"]

            # 熱源補機の定格消費電力（台数×消費電力）
            inputdata["REF"][ref_name]["Heatsource"][unit_id]["Heatsource_sub_RatedPowerConsumption_total"] = \
                unit_configure["Heatsource_sub_RatedPowerConsumption"] * unit_configure["Number"]

            # 熱源機器の台数
            inputdata["REF"][ref_name]["num_of_unit"] += 1

            # 一次ポンプの消費電力の合計
            inputdata["REF"][ref_name]["Heatsource"][unit_id]["PrimaryPumpPowerConsumption_total"] = \
                unit_configure["PrimaryPumpPowerConsumption"] * unit_configure["Number"]

            # 冷却塔ファンの消費電力の合計
            inputdata["REF"][ref_name]["Heatsource"][unit_id]["CoolingTowerFanPowerConsumption_total"] = \
                unit_configure["CoolingTowerFanPowerConsumption"] * unit_configure["Number"]

            # 冷却塔ポンプの消費電力の合計
            inputdata["REF"][ref_name]["Heatsource"][unit_id]["CoolingTowerPumpPowerConsumption_total"] = \
                unit_configure["CoolingTowerPumpPowerConsumption"] * unit_configure["Number"]

        # 蓄熱システムの追掛運転用熱交換器の制約
        if inputdata["REF"][ref_name]["isStorage"] == "追掛":

            tmpCapacity = inputdata["REF"][ref_name]["storageEffratio"] * inputdata["REF"][ref_name]["StorageSize"] / 8 * (1000 / 3600)

            # 1台目は必ず熱交換器であると想定
            if inputdata["REF"][ref_name]["Heatsource"][0]["HeatsourceRatedCapacity_total"] > tmpCapacity:
                inputdata["REF"][ref_name]["Heatsource"][0]["HeatsourceRatedCapacity_total"] = tmpCapacity

    # 接続される二次ポンプ群

    for ahu_name in inputdata["AirHandlingSystem"]:

        if inputdata["AirHandlingSystem"][ahu_name]["HeatSource_cooling"] + "_冷房" in inputdata["REF"]:

            # 冷房熱源群（蓄熱なし）
            inputdata["REF"][inputdata["AirHandlingSystem"][ahu_name]["HeatSource_cooling"] + "_冷房"]["pump_list"].add(
                inputdata["AirHandlingSystem"][ahu_name]["Pump_cooling"] + "_冷房")

            # 冷房熱源群（蓄熱あり）
            if inputdata["REF"][inputdata["AirHandlingSystem"][ahu_name]["HeatSource_cooling"] + "_冷房"]["isStorage"] == "追掛":
                inputdata["REF"][inputdata["AirHandlingSystem"][ahu_name]["HeatSource_cooling"] + "_冷房_蓄熱"]["pump_list"].add(
                    inputdata["AirHandlingSystem"][ahu_name]["Pump_cooling"] + "_冷房")

        if inputdata["AirHandlingSystem"][ahu_name]["HeatSource_heating"] + "_暖房" in inputdata["REF"]:

            # 暖房熱源群（蓄熱なし）
            inputdata["REF"][inputdata["AirHandlingSystem"][ahu_name]["HeatSource_heating"] + "_暖房"]["pump_list"].add(
                inputdata["AirHandlingSystem"][ahu_name]["Pump_heating"] + "_暖房")

            # 暖房熱源群（蓄熱あり）
            if inputdata["REF"][inputdata["AirHandlingSystem"][ahu_name]["HeatSource_heating"] + "_暖房"]["isStorage"] == "追掛":
                inputdata["REF"][inputdata["AirHandlingSystem"][ahu_name]["HeatSource_heating"] + "_暖房_蓄熱"]["pump_list"].add(
                    inputdata["AirHandlingSystem"][ahu_name]["Pump_heating"] + "_暖房")

    #----------------------------------------------------------------------------------
    # 結果格納用の変数 resultJson　（熱源群）
    #----------------------------------------------------------------------------------

    for ref_name in inputdata["REF"]:

        resultJson["REF"][ref_name] = {

            "schedule": np.zeros((365, 24)),  # 運転スケジュール

            "load_ratio_rated": np.zeros((365, 24)),  # 負荷率（定格能力に対する比率） [-]

            "Qref_hourly": np.zeros((365, 24)),  # 熱源負荷 [MJ/h]
            "Qref_storage": np.zeros(365),  # 日積算必要蓄熱量 [MJ/day]
            "Tref_discharge": np.zeros(365),  # 最大追い掛け運転時間 [hour]

            "num_of_operation": np.zeros((365, 24)),  # 運転台数

            "Qref_kW_hour": np.zeros((365, 24)),  # 熱源平均負荷 [kW]
            "Qref_over_capacity": np.zeros((365, 24)),  # 過負荷分
            "ghsp_Rq": 0,  # 冷房負荷と暖房負荷の比率（地中熱ヒートポンプ用）

            "E_ref_main": np.zeros((365, 24)),  # 熱源主機一次エネルギー消費量 [MJ]
            "E_ref_main_MWh": np.zeros((365, 24)),  # 熱源主機電力消費量 [MWh]

            "E_ref_sub": np.zeros((365, 24)),  # 補機電力 [kW]
            "E_ref_pump": np.zeros((365, 24)),  # 一次ポンプ電力 [kW] 
            "E_ref_ct_fan": np.zeros((365, 24)),  # 冷却塔ファン電力 [kW] 
            "E_ref_ct_pump": np.zeros((365, 24)),  # 冷却水ポンプ電力 [kW]

            "E_ref_sub_MWh": np.zeros((365, 24)),  # 補機電力 [MWh]
            "E_ref_pump_MWh": np.zeros((365, 24)),  # 一次ポンプ電力 [MWh]
            "E_ref_ct_fan_MWh": np.zeros((365, 24)),  # 冷却塔ファン電力 [MWh]
            "E_ref_ct_pump_MWh": np.zeros((365, 24)),  # 冷却水ポンプ電力 [MWh]

            "Qref_thermal_loss": 0,  # 蓄熱槽の熱ロス [MJ]
            "Heatsource": {}
        }

        for unit_id, unit_configure in enumerate(inputdata["REF"][ref_name]["Heatsource"]):
            resultJson["REF"][ref_name]["Heatsource"][unit_id] = {
                "heatsource_temperature": np.zeros((365, 24)),  # 熱源水等の温度
                "load_ratio": np.zeros((365, 24)),  # 負荷率（最大能力に対する比率） [-]
                "xQratio": np.zeros((365, 24)),  # 能力比（各外気温帯における最大能力）
                "xPratio": np.zeros((365, 24)),  # 入力比（各外気温帯における最大入力）
                "coeff_x": np.zeros((365, 24)),  # 部分負荷特性
                "coeff_tw": np.ones((365, 24)),  # 送水温度特性
                "Q_ref_max": np.zeros((365, 24)),  # 最大能力
                "E_ref_max": np.zeros((365, 24)),  # 最大入力
                "E_ref_main_kW": np.zeros((365, 24)),  # 機種別の一次エネルギー消費量 [kW]
                "E_ref_main_MJ": np.zeros((365, 24)),  # 機種別の一次エネルギー消費量 [MJ/h]
                "E_ref_main_MWh": np.zeros((365, 24))  # 機種別の一次エネルギー消費量 [MWh]
            }

    #----------------------------------------------------------------------------------
    # 熱源群の合計定格能力 （解説書 2.7.5）
    #----------------------------------------------------------------------------------

    for ref_name in inputdata["REF"]:
        inputdata["REF"][ref_name]["Qref_rated"] = 0
        for unit_id, unit_configure in enumerate(inputdata["REF"][ref_name]["Heatsource"]):
            inputdata["REF"][ref_name]["Qref_rated"] += inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedCapacity_total"]

    #----------------------------------------------------------------------------------
    # 蓄熱槽の熱損失 （解説書 2.7.1）
    #----------------------------------------------------------------------------------

    for ref_name in inputdata["REF"]:

        # 蓄熱の場合: 熱損失量 [MJ/day] を足す。損失量は 蓄熱槽容量の3%。
        if inputdata["REF"][ref_name]["isStorage"] == "蓄熱":
            resultJson["REF"][ref_name]["Qref_thermal_loss"] = inputdata["REF"][ref_name]["StorageSize"] * k_heatloss

    #----------------------------------------------------------------------------------
    # 熱源負荷の算出（解説書 2.7.2）
    #----------------------------------------------------------------------------------

    for ref_name in inputdata["REF"]:

        for dd in range(0, 365):
            for hh in range(0, 24):

                if inputdata["REF"][ref_name]["mode"] == "cooling":  # 冷熱生成用熱源

                    for pump_name in inputdata["REF"][ref_name]["pump_list"]:

                        if resultJson["PUMP"][pump_name]["Qps_hourly"][dd][hh] > 0:
                            # 日積算熱源負荷  [MJ/h]
                            resultJson["REF"][ref_name]["Qref_hourly"][dd][hh] += \
                                resultJson["PUMP"][pump_name]["Qps_hourly"][dd][hh] + resultJson["PUMP"][pump_name]["heatloss_pump"][dd][hh]


                elif inputdata["REF"][ref_name]["mode"] == "heating":  # 温熱生成用熱源

                    for pump_name in inputdata["REF"][ref_name]["pump_list"]:

                        if (resultJson["PUMP"][pump_name]["Qps_hourly"][dd][hh] +
                            (-1) * resultJson["PUMP"][pump_name]["heatloss_pump"][dd][hh]) > 0:
                            resultJson["REF"][ref_name]["Qref_hourly"][dd][hh] += \
                                resultJson["PUMP"][pump_name]["Qps_hourly"][dd][hh] + (-1) * resultJson["PUMP"][pump_name]["heatloss_pump"][dd][hh]

    #----------------------------------------------------------------------------------
    # 熱源群の運転時間（解説書 2.7.3）
    #----------------------------------------------------------------------------------

    for ref_name in inputdata["REF"]:

        for pump_name in inputdata["REF"][ref_name]["pump_list"]:
            resultJson["REF"][ref_name]["schedule"] += resultJson["PUMP"][pump_name]["schedule"]

        # 運転スケジュールの和が「1以上（接続されている二次ポンプ群の1つは動いている）」であれば、熱源群は稼働しているとする。
        resultJson["REF"][ref_name]["schedule"][resultJson["REF"][ref_name]["schedule"] > 1] = 1

        # 日平均負荷[kW] と 過負荷[MJ/h] を求める。（検証用）
        for dd in range(0, 365):
            for hh in range(0, 24):

                # 平均負荷 [kW]
                if resultJson["REF"][ref_name]["Qref_hourly"][dd][hh] > 0:
                    resultJson["REF"][ref_name]["Qref_kW_hour"][dd][hh] = \
                        resultJson["REF"][ref_name]["Qref_hourly"][dd][hh] * 1000 / 3600

                # 過負荷分を集計 [MJ/h]
                if resultJson["REF"][ref_name]["Qref_kW_hour"][dd][hh] > inputdata["REF"][ref_name]["Qref_rated"]:
                    resultJson["REF"][ref_name]["Qref_over_capacity"][dd][hh] = \
                        (resultJson["REF"][ref_name]["Qref_kW_hour"][dd][hh] - inputdata["REF"][ref_name]["Qref_rated"]) * 3600 / 1000

    print('熱源負荷計算完了')

    if debug:  # pragma: no cover

        for ref_name in inputdata["REF"]:
            mf.hourlyplot(resultJson["REF"][ref_name]["Qref_kW_hour"], "熱源負荷： " + ref_name, "b", "時刻別熱源負荷")

    #----------------------------------------------------------------------------------
    # 熱源機器の特性の読み込み（解説書 附属書A.4）
    #----------------------------------------------------------------------------------

    for ref_name in inputdata["REF"]:

        inputdata["REF"][ref_name]["checkCTVWV"] = 0  # 冷却水変流量の有無
        inputdata["REF"][ref_name]["checkGEGHP"] = 0  # 発電機能の有無

        for unit_id, unit_configure in enumerate(inputdata["REF"][ref_name]["Heatsource"]):

            if "冷却水変流量" in unit_configure["HeatsourceType"]:
                inputdata["REF"][ref_name]["checkCTVWV"] = 1

            if "消費電力自給装置" in unit_configure["HeatsourceType"]:
                inputdata["REF"][ref_name]["checkGEGHP"] = 1

            # 特性を全て抜き出す。
            refParaSetALL = HeatSourcePerformance[unit_configure["HeatsourceType"]]

            # 燃料種類に応じて、一次エネルギー換算を行う。
            fuel_type = str()
            if inputdata["REF"][ref_name]["mode"] == "cooling":
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"] = refParaSetALL["冷房時の特性"]
                fuel_type = refParaSetALL["冷房時の特性"]["燃料種類"]

            elif inputdata["REF"][ref_name]["mode"] == "heating":
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"] = refParaSetALL["暖房時の特性"]
                fuel_type = refParaSetALL["暖房時の特性"]["燃料種類"]

            # 燃料種類＋一次エネルギー換算 [kW]
            if fuel_type == "電力":
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["refInputType"] = 1
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["Eref_rated_primary"] = (bc.fprime / 3600) * inputdata["REF"][ref_name]["Heatsource"][unit_id][
                    "HeatsourceRatedPowerConsumption_total"]
            elif fuel_type == "ガス":
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["refInputType"] = 2
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["Eref_rated_primary"] = inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedFuelConsumption_total"]
            elif fuel_type == "重油":
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["refInputType"] = 3
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["Eref_rated_primary"] = inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedFuelConsumption_total"]
            elif fuel_type == "灯油":
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["refInputType"] = 4
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["Eref_rated_primary"] = inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedFuelConsumption_total"]
            elif fuel_type == "液化石油ガス":
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["refInputType"] = 5
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["Eref_rated_primary"] = inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedFuelConsumption_total"]
            elif fuel_type == "蒸気":
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["refInputType"] = 6
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedFuelConsumption_total"] = inputdata["REF"][ref_name]["Heatsource"][unit_id][
                    "HeatsourceRatedCapacity_total"]
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["Eref_rated_primary"] = \
                    (inputdata["Building"]["Coefficient_DHC"]["Heating"]) * inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedCapacity_total"]
            elif fuel_type == "温水":
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["refInputType"] = 7
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedFuelConsumption_total"] = inputdata["REF"][ref_name]["Heatsource"][unit_id][
                    "HeatsourceRatedCapacity_total"]
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["Eref_rated_primary"] = \
                    (inputdata["Building"]["Coefficient_DHC"]["Heating"]) * inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedCapacity_total"]
            elif fuel_type == "冷水":
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["refInputType"] = 8
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedFuelConsumption_total"] = inputdata["REF"][ref_name]["Heatsource"][unit_id][
                    "HeatsourceRatedCapacity_total"]
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["Eref_rated_primary"] = \
                    (inputdata["Building"]["Coefficient_DHC"]["Cooling"]) * inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedCapacity_total"]

                #----------------------------------------------------------------------------------
    # 熱源群の負荷率（解説書 2.7.7）
    #----------------------------------------------------------------------------------

    for ref_name in inputdata["REF"]:

        for dd in range(0, 365):
            for hh in range(0, 24):

                # 負荷率の算出 [-]
                if resultJson["REF"][ref_name]["Qref_hourly"][dd][hh] > 0:
                    # 熱源定格負荷率（定格能力に対する比率）
                    try:
                        resultJson["REF"][ref_name]["load_ratio_rated"][dd][hh] = \
                            (resultJson["REF"][ref_name]["Qref_hourly"][dd][hh] * 1000 / 3600) / inputdata["REF"][ref_name]["Qref_rated"]
                    except ZeroDivisionError:
                        resultJson["REF"][ref_name]["load_ratio_rated"][dd][hh] = 0

    #----------------------------------------------------------------------------------
    # 湿球温度 （解説書 2.7.4.2）
    #----------------------------------------------------------------------------------

    for dd in range(0, 365):
        for hh in range(0, 24):

            if ac_mode[dd] == "冷房" or ac_mode[dd] == "中間期":

                resultJson["climate"]["Tout_wb"][dd][hh] = \
                    Area[inputdata["Building"]["Region"] + "地域"]["湿球温度係数_冷房a1"] * resultJson["climate"]["Tout"][dd][hh] + \
                    Area[inputdata["Building"]["Region"] + "地域"]["湿球温度係数_冷房a0"]

            elif ac_mode[dd] == "暖房":

                resultJson["climate"]["Tout_wb"][dd][hh] = \
                    Area[inputdata["Building"]["Region"] + "地域"]["湿球温度係数_暖房a1"] * resultJson["climate"]["Tout"][dd][hh] + \
                    Area[inputdata["Building"]["Region"] + "地域"]["湿球温度係数_暖房a0"]

    #----------------------------------------------------------------------------------
    # 冷却水温度 （解説書 2.7.4.3）
    #----------------------------------------------------------------------------------

    for dd in range(0, 365):
        for hh in range(0, 24):
            # 冷房運転時冷却水温度
            resultJson["climate"]["Tct_cooling"][dd][hh] = resultJson["climate"]["Tout_wb"][dd][hh] + 3
            # 暖房運転時冷却水温度
            resultJson["climate"]["Tct_heating"][dd][hh] = 15.5

    #----------------------------------------------------------------------------------
    # 地中熱交換器（クローズドループ）からの熱源水温度 （解説書 2.7.4.4）
    #----------------------------------------------------------------------------------

    # 地中熱ヒートポンプ用係数
    gshp_ah = [8.0278, 13.0253, 16.7424, 19.3145, 21.2833]  # 地盤モデル：暖房時パラメータa
    gshp_bh = [-1.1462, -1.8689, -2.4651, -3.091, -3.8325]  # 地盤モデル：暖房時パラメータb
    gshp_ch = [-0.1128, -0.1846, -0.2643, -0.2926, -0.3474]  # 地盤モデル：暖房時パラメータc
    gshp_dh = [0.1256, 0.2023, 0.2623, 0.3085, 0.3629]  # 地盤モデル：暖房時パラメータd
    gshp_ac = [8.0633, 12.6226, 16.1703, 19.6565, 21.8702]  # 地盤モデル：冷房時パラメータa
    gshp_bc = [2.9083, 4.7711, 6.3128, 7.8071, 9.148]  # 地盤モデル：冷房時パラメータb
    gshp_cc = [0.0613, 0.0568, 0.1027, 0.1984, 0.249]  # 地盤モデル：冷房時パラメータc
    gshp_dc = [0.2178, 0.3509, 0.4697, 0.5903, 0.7154]  # 地盤モデル：冷房時パラメータd

    ghspToa_ave = [5.8, 7.5, 10.2, 11.6, 13.3, 15.7, 17.4, 22.7]  # 地盤モデル：年平均外気温
    gshpToa_h = [-3, -0.8, 0, 1.1, 3.6, 6, 9.3, 17.5]  # 地盤モデル：暖房時平均外気温
    gshpToa_c = [16.8, 17, 18.9, 19.6, 20.5, 22.4, 22.1, 24.6]  # 地盤モデル：冷房時平均外気温

    # 冷暖房比率 ghsp_Rq
    for ref_original_name in inputdata["HeatsourceSystem"]:

        Qcmax = 0
        if "冷房" in inputdata["HeatsourceSystem"][ref_original_name]:
            Qcmax = np.max(np.sum(resultJson["REF"][ref_original_name + "_冷房"]["Qref_hourly"], axis=1), 0)

        Qhmax = 0
        if "暖房" in inputdata["HeatsourceSystem"][ref_original_name]:
            Qhmax = np.max(np.sum(resultJson["REF"][ref_original_name + "_暖房"]["Qref_hourly"], axis=1), 0)

        if Qcmax != 0 and Qhmax != 0:

            resultJson["REF"][ref_original_name + "_冷房"]["ghsp_Rq"] = (Qcmax - Qhmax) / (Qcmax + Qhmax)
            resultJson["REF"][ref_original_name + "_暖房"]["ghsp_Rq"] = (Qcmax - Qhmax) / (Qcmax + Qhmax)

        elif Qcmax == 0 and Qhmax != 0:
            resultJson["REF"][ref_original_name + "_暖房"]["ghsp_Rq"] = 0

        elif Qcmax != 0 and Qhmax == 0:
            resultJson["REF"][ref_original_name + "_冷房"]["ghsp_Rq"] = 0

    #----------------------------------------------------------------------------------
    # 熱源水等の温度 matrix_T （解説書 2.7.4）
    #----------------------------------------------------------------------------------

    # 地中熱オープンループの地盤特性の読み込み
    with open(database_directory + 'AC_gshp_openloop.json', 'r', encoding='utf-8') as f:
        AC_gshp_openloop = json.load(f)

    for ref_name in inputdata["REF"]:

        for unit_id, unit_configure in enumerate(inputdata["REF"][ref_name]["Heatsource"]):

            # 日別の熱源水等の温度

            if "地盤A" in unit_configure["parameter"]["熱源種類"] or "地盤B" in unit_configure["parameter"]["熱源種類"] or \
                    "地盤C" in unit_configure["parameter"]["熱源種類"] or "地盤D" in unit_configure["parameter"]["熱源種類"] or \
                    "地盤E" in unit_configure["parameter"]["熱源種類"] or "地盤F" in unit_configure["parameter"]["熱源種類"]:  # 地中熱オープンループ

                for dd in range(365):

                    # 月別の揚水温度
                    theta_wo_m = \
                        AC_gshp_openloop["theta_ac_wo_ave"][inputdata["Building"]["Region"] + "地域"] + \
                        AC_gshp_openloop["theta_ac_wo_m"][inputdata["Building"]["Region"] + "地域"][bc.day2month(dd)]

                    # 月別の地盤からの熱源水還り温度
                    heatsource_temperature = 0
                    if inputdata["REF"][ref_name]["mode"] == "cooling":

                        # 月別の熱源水還り温度（冷房期）
                        heatsource_temperature = \
                            theta_wo_m + \
                            AC_gshp_openloop["theta_wo_c"][unit_configure["parameter"]["熱源種類"]] + \
                            AC_gshp_openloop["theta_hex_c"][unit_configure["parameter"]["熱源種類"]]

                    elif inputdata["REF"][ref_name]["mode"] == "heating":

                        # 月別の熱源水還り温度（暖房期）
                        heatsource_temperature = \
                            theta_wo_m + \
                            AC_gshp_openloop["theta_wo_h"][unit_configure["parameter"]["熱源種類"]] + \
                            AC_gshp_openloop["theta_hex_h"][unit_configure["parameter"]["熱源種類"]]

                    # 時々刻々のデータ
                    for hh in range(0, 24):
                        resultJson["REF"][ref_name]["Heatsource"][unit_id]["heatsource_temperature"][dd][hh] = heatsource_temperature


            else:

                if unit_configure["parameter"]["熱源種類"] == "水" and inputdata["REF"][ref_name]["mode"] == "cooling":

                    # 冷却水温度（冷房）
                    resultJson["REF"][ref_name]["Heatsource"][unit_id]["heatsource_temperature"] = resultJson["climate"]["Tct_cooling"]

                elif unit_configure["parameter"]["熱源種類"] == "水" and inputdata["REF"][ref_name]["mode"] == "heating":

                    # 冷却水温度（暖房）
                    resultJson["REF"][ref_name]["Heatsource"][unit_id]["heatsource_temperature"] = resultJson["climate"]["Tct_heating"]

                elif unit_configure["parameter"]["熱源種類"] == "空気" and inputdata["REF"][ref_name]["mode"] == "cooling":

                    # 乾球温度 
                    resultJson["REF"][ref_name]["Heatsource"][unit_id]["heatsource_temperature"] = resultJson["climate"]["Tout"]

                elif unit_configure["parameter"]["熱源種類"] == "空気" and inputdata["REF"][ref_name]["mode"] == "heating":

                    # 湿球温度 
                    resultJson["REF"][ref_name]["Heatsource"][unit_id]["heatsource_temperature"] = resultJson["climate"]["Tout_wb"]

                elif unit_configure["parameter"]["熱源種類"] == "不要":

                    # 乾球温度 
                    resultJson["REF"][ref_name]["Heatsource"][unit_id]["heatsource_temperature"] = resultJson["climate"]["Tout"]


                elif "地盤1" in unit_configure["parameter"]["熱源種類"] or "地盤2" in unit_configure["parameter"]["熱源種類"] or \
                        "地盤3" in unit_configure["parameter"]["熱源種類"] or "地盤4" in unit_configure["parameter"]["熱源種類"] or \
                        "地盤5" in unit_configure["parameter"]["熱源種類"]:  # 地中熱クローズループ

                    for gound_type in range(1, 6):

                        if unit_configure["parameter"]["熱源種類"] == "地盤" + str(int(gound_type)) and inputdata["REF"][ref_name]["mode"] == "cooling":

                            igsType = int(gound_type) - 1
                            iAREA = int(inputdata["Building"]["Region"]) - 1

                            # 地盤からの還り温度（冷房）
                            for dd in range(0, 365):
                                for hh in range(0, 24):
                                    resultJson["REF"][ref_name]["Heatsource"][unit_id]["heatsource_temperature"][dd][hh] = \
                                        (gshp_cc[igsType] * resultJson["REF"][ref_name]["ghsp_Rq"] + gshp_dc[igsType]) * \
                                        (resultJson["climate"]["Tout_daily"][dd] - gshpToa_c[iAREA]) + \
                                        (ghspToa_ave[iAREA] + gshp_ac[igsType] * resultJson["REF"][ref_name]["ghsp_Rq"] + gshp_bc[igsType])

                        elif unit_configure["parameter"]["熱源種類"] == "地盤" + str(int(gound_type)) and inputdata["REF"][ref_name]["mode"] == "heating":

                            igsType = int(gound_type) - 1
                            iAREA = int(inputdata["Building"]["Region"]) - 1

                            # 地盤からの還り温度（暖房）
                            for dd in range(0, 365):
                                for hh in range(0, 24):
                                    resultJson["REF"][ref_name]["Heatsource"][unit_id]["heatsource_temperature"][dd][hh] = \
                                        (gshp_ch[igsType] * resultJson["REF"][ref_name]["ghsp_Rq"] + gshp_dh[igsType]) * \
                                        (resultJson["climate"]["Tout_daily"][dd] - gshpToa_h[iAREA]) + \
                                        (ghspToa_ave[iAREA] + gshp_ah[igsType] * resultJson["REF"][ref_name]["ghsp_Rq"] + gshp_bh[igsType])

                else:

                    raise Exception("熱源種類が不正です。")

    #----------------------------------------------------------------------------------
    # 任意評定用　熱源水温度（ SP-3 ）
    #----------------------------------------------------------------------------------

    if "SpecialInputData" in inputdata:

        if "heatsource_temperature_monthly" in inputdata["SpecialInputData"]:

            for ref_original_name in inputdata["SpecialInputData"]["heatsource_temperature_monthly"]:

                # 入力された熱源群名称から、計算上使用する熱源群名称（冷暖、蓄熱分離）に変換
                for ref_name in [ref_original_name + "_冷房", ref_original_name + "_暖房", ref_original_name + "_冷房_蓄熱", ref_original_name + "_暖房_蓄熱"]:

                    if ref_name in inputdata["REF"]:
                        for unit_id, unit_configure in enumerate(inputdata["REF"][ref_name]["Heatsource"]):
                            for dd in range(0, 365):
                                for hh in range(0, 24):
                                    resultJson["REF"][ref_name]["Heatsource"][unit_id]["heatsource_temperature"][dd][hh] = \
                                        inputdata["SpecialInputData"]["heatsource_temperature_monthly"][ref_original_name][bc.day2month(dd)]

    #----------------------------------------------------------------------------------
    # 最大能力比 xQratio （解説書 2.7.8）
    #----------------------------------------------------------------------------------

    for ref_name in inputdata["REF"]:

        for unit_id, unit_configure in enumerate(inputdata["REF"][ref_name]["Heatsource"]):

            # 能力比（各外気温帯における最大能力）
            for dd in range(0, 365):
                for hh in range(0, 24):

                    # 外気温度
                    temperature = resultJson["REF"][ref_name]["Heatsource"][unit_id]["heatsource_temperature"][dd][hh]

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
                            resultJson["REF"][ref_name]["Heatsource"][unit_id]["xQratio"][dd][hh] = \
                                unit_configure["parameter"]["能力比"][para_num]["基整促係数"] * (
                                        unit_configure["parameter"]["能力比"][para_num]["係数"]["a4"] * temperature ** 4 +
                                        unit_configure["parameter"]["能力比"][para_num]["係数"]["a3"] * temperature ** 3 +
                                        unit_configure["parameter"]["能力比"][para_num]["係数"]["a2"] * temperature ** 2 +
                                        unit_configure["parameter"]["能力比"][para_num]["係数"]["a1"] * temperature +
                                        unit_configure["parameter"]["能力比"][para_num]["係数"]["a0"])

        for unit_id, unit_configure in enumerate(inputdata["REF"][ref_name]["Heatsource"]):

            for dd in range(0, 365):
                for hh in range(0, 24):
                    # 各時刻の最大能力 [kW]
                    resultJson["REF"][ref_name]["Heatsource"][unit_id]["Q_ref_max"][dd][hh] = \
                        inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedCapacity_total"] * \
                        resultJson["REF"][ref_name]["Heatsource"][unit_id]["xQratio"][dd][hh]

    # ----------------------------------------------------------------------------------
    # 蓄熱システムによる運転時間の補正（解説書 2.7.15 蓄熱）
    # ----------------------------------------------------------------------------------

    # 必要蓄熱量の算出

    for ref_name in inputdata["REF"]:

        if inputdata["REF"][ref_name]["isStorage"] == "追掛":

            for dd in range(0, 365):

                # 最大放熱可能量[MJ]
                Q_discharge = inputdata["REF"][ref_name]["StorageSize"] * (1 - k_heatloss)

                for hh in range(0, 24):

                    if resultJson["REF"][ref_name]["Qref_hourly"][dd][hh] > 0:

                        # 必要蓄熱量 [MJ/day]
                        if resultJson["REF"][ref_name]["Qref_hourly"][dd][hh] > (inputdata["REF"][ref_name]["Heatsource"][0]["HeatsourceRatedCapacity_total"] * 3600 / 1000):
                            tmp = inputdata["REF"][ref_name]["Heatsource"][0]["HeatsourceRatedCapacity_total"] * 3600 / 1000
                        else:
                            tmp = resultJson["REF"][ref_name]["Qref_hourly"][dd][hh]

                        if (Q_discharge - tmp) > 0:
                            Q_discharge = Q_discharge - tmp
                            resultJson["REF"][ref_name]["Qref_storage"][dd] += tmp
                        else:
                            break

            # 必要蓄熱量[MJ] → 蓄熱用熱源に値を渡す
            resultJson["REF"][ref_name + "_蓄熱"]["Qref_storage"] = resultJson["REF"][ref_name]["Qref_storage"]

    for ref_name in inputdata["REF"]:
        if inputdata["REF"][ref_name]["isStorage"] == "蓄熱":

            # 一旦削除
            resultJson["REF"][ref_name]["Qref_hourly"] = np.zeros((365, 24))
            resultJson["REF"][ref_name]["load_ratio_rated"] = np.zeros((365, 24))

            for dd in range(0, 365):

                # 必要蓄熱量が 0　より大きい場合
                if resultJson["REF"][ref_name]["Qref_storage"][dd] > 0:

                    # 熱ロスを足す。
                    resultJson["REF"][ref_name]["Qref_storage"][dd] += inputdata["REF"][ref_name]["StorageSize"] * k_heatloss

                    # 蓄熱用熱源の最大能力（0〜8時の平均値とする）
                    Q_ref_max_total = np.zeros(8)
                    for hh in range(0, 8):
                        for unit_id, unit_configure in enumerate(inputdata["REF"][ref_name]["Heatsource"]):
                            Q_ref_max_total[hh] += resultJson["REF"][ref_name]["Heatsource"][unit_id]["Q_ref_max"][dd][hh]
                    Q_ref_max_ave = np.mean(Q_ref_max_total)

                    # 蓄熱運転すべき時間
                    hour_for_storage = math.ceil(resultJson["REF"][ref_name]["Qref_storage"][dd] / (Q_ref_max_ave * 3600 / 1000))

                    if hour_for_storage > 24:
                        print(hour_for_storage)
                        raise Exception("蓄熱に必要な能力が足りません")

                    # 1時間に蓄熱すべき量 [MJ/h]
                    storage_heat_in_hour = (resultJson["REF"][ref_name]["Qref_storage"][dd] / hour_for_storage)

                    # 本来は前日22時〜にすべきだが、ひとまず0時〜に設定
                    for hh in range(0, hour_for_storage):
                        resultJson["REF"][ref_name]["Qref_hourly"][dd][hh] = storage_heat_in_hour

                    # 負荷率帯マトリックスの更新
                    for hh in range(0, 24):
                        if resultJson["REF"][ref_name]["Qref_hourly"][dd][hh] > 0:
                            resultJson["REF"][ref_name]["load_ratio_rated"][dd][hh] = \
                                (resultJson["REF"][ref_name]["Qref_hourly"][dd][hh] * 1000 / 3600) / inputdata["REF"][ref_name]["Qref_rated"]

                            #----------------------------------------------------------------------------------
    # 最大入力比 xPratio （解説書 2.7.11）
    #----------------------------------------------------------------------------------

    for ref_name in inputdata["REF"]:

        for unit_id, unit_configure in enumerate(inputdata["REF"][ref_name]["Heatsource"]):

            # 外気温度帯マトリックス 
            for dd in range(0, 365):
                for hh in range(0, 24):

                    # 外気温度帯
                    temperature = resultJson["REF"][ref_name]["Heatsource"][unit_id]["heatsource_temperature"][dd][hh]

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
                            resultJson["REF"][ref_name]["Heatsource"][unit_id]["xPratio"][dd][hh] = \
                                unit_configure["parameter"]["入力比"][para_num]["基整促係数"] * (
                                        unit_configure["parameter"]["入力比"][para_num]["係数"]["a4"] * temperature ** 4 +
                                        unit_configure["parameter"]["入力比"][para_num]["係数"]["a3"] * temperature ** 3 +
                                        unit_configure["parameter"]["入力比"][para_num]["係数"]["a2"] * temperature ** 2 +
                                        unit_configure["parameter"]["入力比"][para_num]["係数"]["a1"] * temperature +
                                        unit_configure["parameter"]["入力比"][para_num]["係数"]["a0"])

        for unit_id, unit_configure in enumerate(inputdata["REF"][ref_name]["Heatsource"]):

            for dd in range(0, 365):
                for hh in range(0, 24):
                    # 各時刻における最大入力 [kW]  (1次エネルギー換算値であることに注意）
                    resultJson["REF"][ref_name]["Heatsource"][unit_id]["E_ref_max"][dd][hh] = \
                        inputdata["REF"][ref_name]["Heatsource"][unit_id]["Eref_rated_primary"] * \
                        resultJson["REF"][ref_name]["Heatsource"][unit_id]["xPratio"][dd][hh]

    #----------------------------------------------------------------------------------
    # 熱源機器の運転台数（解説書 2.7.9）
    #----------------------------------------------------------------------------------

    # 運転台数マトリックス
    for ref_name in inputdata["REF"]:

        for dd in range(0, 365):
            for hh in range(0, 24):

                if resultJson["REF"][ref_name]["Qref_hourly"][dd][hh] > 0:  # 負荷があれば

                    if inputdata["REF"][ref_name]["isStagingControl"] == "無":  # 運転台数制御が「無」の場合

                        resultJson["REF"][ref_name]["num_of_operation"][dd][hh] = inputdata["REF"][ref_name]["num_of_unit"]

                    elif inputdata["REF"][ref_name]["isStagingControl"] == "有":  # 運転台数制御が「有」の場合

                        # 処理熱量 [kW]
                        tmpQ = resultJson["REF"][ref_name]["Qref_hourly"][dd][hh] * 1000 / 3600

                        # 運転台数 num_of_operation
                        tmpQmax = 0
                        rr = 0
                        for rr in range(0, inputdata["REF"][ref_name]["num_of_unit"]):
                            tmpQmax += resultJson["REF"][ref_name]["Heatsource"][rr]["Q_ref_max"][dd][hh]

                            if tmpQ < tmpQmax:
                                break

                        resultJson["REF"][ref_name]["num_of_operation"][dd][hh] = rr + 1

    if debug:  # pragma: no cover
        for ref_name in inputdata["REF"]:
            mf.hourlyplot(resultJson["REF"][ref_name]["num_of_operation"], "熱源運転台数： " + ref_name, "b", "熱源運転台数")

    #----------------------------------------------------------------------------------
    # 熱源群の運転負荷率（解説書 2.7.12）
    #----------------------------------------------------------------------------------

    for ref_name in inputdata["REF"]:

        for dd in range(0, 365):
            for hh in range(0, 24):

                if resultJson["REF"][ref_name]["Qref_hourly"][dd][hh] > 0:  # 運転していれば

                    # 処理熱量 [kW]
                    tmpQ = resultJson["REF"][ref_name]["Qref_hourly"][dd][hh] * 1000 / 3600

                    Qrefr_mod_max = 0
                    for unit_id in range(0, int(resultJson["REF"][ref_name]["num_of_operation"][dd][hh])):
                        Qrefr_mod_max += resultJson["REF"][ref_name]["Heatsource"][unit_id]["Q_ref_max"][dd][hh]

                    # [iT,iL]における負荷率
                    if inputdata["REF"][ref_name]["isStorage"] == "追掛":

                        for unit_id, unit_configure in enumerate(inputdata["REF"][ref_name]["Heatsource"]):

                            if unit_id == 0:
                                # 熱交換器の負荷率は1とする
                                resultJson["REF"][ref_name]["Heatsource"][unit_id]["load_ratio"][dd][hh] = 1
                            else:
                                # 熱交換器以外で負荷率を求める。
                                resultJson["REF"][ref_name]["Heatsource"][unit_id]["load_ratio"][dd][hh] = \
                                    (tmpQ - inputdata["REF"][ref_name]["Heatsource"][0]["HeatsourceRatedCapacity_total"]) / \
                                    (Qrefr_mod_max - inputdata["REF"][ref_name]["Heatsource"][0]["HeatsourceRatedCapacity_total"])

                    else:

                        for unit_id, unit_configure in enumerate(inputdata["REF"][ref_name]["Heatsource"]):
                            try:
                                resultJson["REF"][ref_name]["Heatsource"][unit_id]["load_ratio"][dd][hh] = tmpQ / Qrefr_mod_max
                            except ZeroDivisionError:
                                resultJson["REF"][ref_name]["Heatsource"][unit_id]["load_ratio"][dd][hh] = 0

    #----------------------------------------------------------------------------------
    # 部分負荷特性 （解説書 2.7.13）
    #----------------------------------------------------------------------------------

    for ref_name in inputdata["REF"]:

        for dd in range(0, 365):
            for hh in range(0, 24):

                if resultJson["REF"][ref_name]["Qref_hourly"][dd][hh] > 0:  # 運転していれば

                    # 部分負荷特性（各負荷率・各温度帯について）
                    for unit_id in range(0, int(resultJson["REF"][ref_name]["num_of_operation"][dd][hh])):

                        # どの部分負荷特性を使うか（インバータターボなど、冷却水温度によって特性が異なる場合がある）
                        xCurveNum = 0
                        if len(inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["部分負荷特性"]) > 1:  # 部分負荷特性が2以上設定されている場合

                            for para_id in range(0, len(inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["部分負荷特性"])):

                                if resultJson["REF"][ref_name]["Heatsource"][unit_id]["heatsource_temperature"][dd][hh] > \
                                        inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["部分負荷特性"][para_id]["冷却水温度下限"] and \
                                        resultJson["REF"][ref_name]["Heatsource"][unit_id]["heatsource_temperature"][dd][hh] <= \
                                        inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["部分負荷特性"][para_id]["冷却水温度上限"]:
                                    xCurveNum = para_id

                        # 機器特性による上下限を考慮した部分負荷率 tmpL
                        tmpL = 0
                        if resultJson["REF"][ref_name]["Heatsource"][unit_id]["load_ratio"][dd][hh] < \
                                inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["部分負荷特性"][xCurveNum]["下限"]:
                            tmpL = inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["部分負荷特性"][xCurveNum]["下限"]
                        elif resultJson["REF"][ref_name]["Heatsource"][unit_id]["load_ratio"][dd][hh] > \
                                inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["部分負荷特性"][xCurveNum]["上限"]:
                            tmpL = inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["部分負荷特性"][xCurveNum]["上限"]
                        else:
                            tmpL = resultJson["REF"][ref_name]["Heatsource"][unit_id]["load_ratio"][dd][hh]

                        # 部分負荷特性
                        resultJson["REF"][ref_name]["Heatsource"][unit_id]["coeff_x"][dd][hh] = \
                            inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["部分負荷特性"][xCurveNum]["基整促係数"] * (
                                    inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["部分負荷特性"][xCurveNum]["係数"]["a4"] * tmpL ** 4 +
                                    inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["部分負荷特性"][xCurveNum]["係数"]["a3"] * tmpL ** 3 +
                                    inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["部分負荷特性"][xCurveNum]["係数"]["a2"] * tmpL ** 2 +
                                    inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["部分負荷特性"][xCurveNum]["係数"]["a1"] * tmpL +
                                    inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["部分負荷特性"][xCurveNum]["係数"]["a0"])

                        # 過負荷時のペナルティ
                        if resultJson["REF"][ref_name]["Heatsource"][unit_id]["load_ratio"][dd][hh] > 1:
                            resultJson["REF"][ref_name]["Heatsource"][unit_id]["coeff_x"][dd][hh] = \
                                resultJson["REF"][ref_name]["Heatsource"][unit_id]["coeff_x"][dd][hh] * 1.2

    #----------------------------------------------------------------------------------
    # 送水温度特性 （解説書 2.7.14）
    #----------------------------------------------------------------------------------

    for ref_name in inputdata["REF"]:

        for dd in range(0, 365):
            for hh in range(0, 24):

                # 送水温度特性（各負荷率・各温度帯について）
                for unit_id in range(0, int(resultJson["REF"][ref_name]["num_of_operation"][dd][hh])):

                    # 送水温度特性
                    if inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["送水温度特性"] != []:

                        # 送水温度 TCtmp
                        TCtmp = 0
                        if inputdata["REF"][ref_name]["mode"] == "cooling":

                            if inputdata["REF"][ref_name]["Heatsource"][unit_id]["SupplyWaterTempSummer"] is None:
                                TCtmp = 5
                            else:
                                TCtmp = inputdata["REF"][ref_name]["Heatsource"][unit_id]["SupplyWaterTempSummer"]

                        elif inputdata["REF"][ref_name]["mode"] == "heating":

                            if inputdata["REF"][ref_name]["Heatsource"][unit_id]["SupplyWaterTempWinter"] is None:
                                TCtmp = 50
                            else:
                                TCtmp = inputdata["REF"][ref_name]["Heatsource"][unit_id]["SupplyWaterTempWinter"]

                        # 送水温度の上下限
                        if TCtmp < inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["送水温度特性"][0]["下限"]:
                            TCtmp = inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["送水温度特性"][0]["下限"]
                        elif TCtmp > inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["送水温度特性"][0]["上限"]:
                            TCtmp = inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["送水温度特性"][0]["上限"]

                        # 送水温度特性
                        resultJson["REF"][ref_name]["Heatsource"][unit_id]["coeff_tw"][dd][hh] = \
                            inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["送水温度特性"][0]["基整促係数"] * (
                                    inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["送水温度特性"][0]["係数"]["a4"] * TCtmp ** 4 +
                                    inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["送水温度特性"][0]["係数"]["a3"] * TCtmp ** 3 +
                                    inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["送水温度特性"][0]["係数"]["a2"] * TCtmp ** 2 +
                                    inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["送水温度特性"][0]["係数"]["a1"] * TCtmp +
                                    inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["送水温度特性"][0]["係数"]["a0"])

    #----------------------------------------------------------------------------------
    # 熱源機器の一次エネルギー消費量（解説書 2.7.16）
    #----------------------------------------------------------------------------------

    for ref_name in inputdata["REF"]:

        for dd in range(0, 365):
            for hh in range(0, 24):

                # 熱源主機（機器毎）：エネルギー消費量 kW のマトリックス E_ref_main
                for unit_id in range(0, int(resultJson["REF"][ref_name]["num_of_operation"][dd][hh])):
                    resultJson["REF"][ref_name]["Heatsource"][unit_id]["E_ref_main_kW"][dd][hh] = \
                        resultJson["REF"][ref_name]["Heatsource"][unit_id]["E_ref_max"][dd][hh] * \
                        resultJson["REF"][ref_name]["Heatsource"][unit_id]["coeff_x"][dd][hh] * \
                        resultJson["REF"][ref_name]["Heatsource"][unit_id]["coeff_tw"][dd][hh]

                # 補機電力
                # 一台あたりの負荷率（熱源機器の負荷率＝最大能力を考慮した負荷率・ただし、熱源特性の上限・下限は考慮せず）
                aveLperU = resultJson["REF"][ref_name]["load_ratio_rated"][dd][hh]

                # 過負荷の場合は 平均負荷率＝1.2 とする。
                if aveLperU > 1:
                    aveLperU = 1.2

                # 発電機能付きの熱源機器が1台でもある場合
                if inputdata["REF"][ref_name]["checkGEGHP"] == 1:

                    for unit_id in range(0, int(resultJson["REF"][ref_name]["num_of_operation"][dd][hh])):

                        if "消費電力自給装置" in inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceType"]:

                            # 非発電時の消費電力 [kW]
                            E_nonGE = 0
                            if inputdata["REF"][ref_name]["mode"] == "cooling":
                                E_nonGE = inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedCapacity_total"] * 0.017
                            elif inputdata["REF"][ref_name]["mode"] == "heating":
                                E_nonGE = inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedCapacity_total"] * 0.012

                            E_GEkW = inputdata["REF"][ref_name]["Heatsource"][unit_id]["Heatsource_sub_RatedPowerConsumption_total"]  # 発電時の消費電力 [kW]

                            if aveLperU <= 0.3:
                                resultJson["REF"][ref_name]["E_ref_sub"][dd][hh] += (0.3 * E_nonGE - (E_nonGE - E_GEkW) * aveLperU)
                            else:
                                resultJson["REF"][ref_name]["E_ref_sub"][dd][hh] += (aveLperU * E_GEkW)

                        else:

                            if aveLperU <= 0.3:
                                resultJson["REF"][ref_name]["E_ref_sub"][dd][hh] += 0.3 * inputdata["REF"][ref_name]["Heatsource"][unit_id][
                                    "Heatsource_sub_RatedPowerConsumption_total"]
                            else:
                                resultJson["REF"][ref_name]["E_ref_sub"][dd][hh] += aveLperU * inputdata["REF"][ref_name]["Heatsource"][unit_id][
                                    "Heatsource_sub_RatedPowerConsumption_total"]

                else:

                    # 負荷に比例させる（発電機能なし）
                    refset_SubPower = 0
                    for unit_id in range(0, int(resultJson["REF"][ref_name]["num_of_operation"][dd][hh])):
                        if inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedFuelConsumption_total"] > 0:
                            refset_SubPower += inputdata["REF"][ref_name]["Heatsource"][unit_id]["Heatsource_sub_RatedPowerConsumption_total"]

                    if aveLperU <= 0.3:
                        resultJson["REF"][ref_name]["E_ref_sub"][dd][hh] += 0.3 * refset_SubPower
                    else:
                        resultJson["REF"][ref_name]["E_ref_sub"][dd][hh] += aveLperU * refset_SubPower

                # 一次ポンプ
                for unit_id in range(0, int(resultJson["REF"][ref_name]["num_of_operation"][dd][hh])):
                    resultJson["REF"][ref_name]["E_ref_pump"][dd][hh] += \
                        inputdata["REF"][ref_name]["Heatsource"][unit_id]["PrimaryPumpPowerConsumption_total"]

                # 冷却塔ファン
                for unit_id in range(0, int(resultJson["REF"][ref_name]["num_of_operation"][dd][hh])):
                    resultJson["REF"][ref_name]["E_ref_ct_fan"][dd][hh] += \
                        inputdata["REF"][ref_name]["Heatsource"][unit_id]["CoolingTowerFanPowerConsumption_total"]

                # 冷却水ポンプ
                if inputdata["REF"][ref_name]["checkCTVWV"] == 1:  # 変流量制御がある場合

                    for unit_id in range(0, int(resultJson["REF"][ref_name]["num_of_operation"][dd][hh])):

                        if "冷却水変流量" in inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceType"]:

                            if aveLperU <= 0.5:
                                resultJson["REF"][ref_name]["E_ref_ct_pump"][dd][hh] += \
                                    0.5 * inputdata["REF"][ref_name]["Heatsource"][unit_id]["CoolingTowerPumpPowerConsumption_total"]
                            else:
                                resultJson["REF"][ref_name]["E_ref_ct_pump"][dd][hh] += \
                                    aveLperU * inputdata["REF"][ref_name]["Heatsource"][unit_id]["CoolingTowerPumpPowerConsumption_total"]
                        else:
                            resultJson["REF"][ref_name]["E_ref_ct_pump"][dd][hh] += \
                                inputdata["REF"][ref_name]["Heatsource"][unit_id]["CoolingTowerPumpPowerConsumption_total"]

                else:

                    for unit_id in range(0, int(resultJson["REF"][ref_name]["num_of_operation"][dd][hh])):
                        resultJson["REF"][ref_name]["E_ref_ct_pump"][dd][hh] += \
                            inputdata["REF"][ref_name]["Heatsource"][unit_id]["CoolingTowerPumpPowerConsumption_total"]

    #----------------------------------------------------------------------------------
    # 熱熱源群の一次エネルギー消費量および消費電力（解説書 2.7.17）
    #----------------------------------------------------------------------------------

    for ref_name in inputdata["REF"]:

        for dd in range(0, 365):
            for hh in range(0, 24):

                if resultJson["REF"][ref_name]["Qref_hourly"][dd][hh] != 0:

                    # 熱源主機 [MJ/h]
                    for unit_id in range(0, len(inputdata["REF"][ref_name]["Heatsource"])):

                        resultJson["REF"][ref_name]["E_ref_main"][dd][hh] += \
                            resultJson["REF"][ref_name]["Heatsource"][unit_id]["E_ref_main_kW"][dd][hh] * 3600 / 1000

                        # CGSの計算用に機種別に一次エネルギー消費量を積算 [MJ/h]
                        resultJson["REF"][ref_name]["Heatsource"][unit_id]["E_ref_main_MJ"][dd][hh] = \
                            resultJson["REF"][ref_name]["Heatsource"][unit_id]["E_ref_main_kW"][dd][hh] * 3600 / 1000

                        # CGSの計算用に電力のみ積算 [MWh]
                        if inputdata["REF"][ref_name]["Heatsource"][unit_id]["refInputType"] == 1:  # 燃料種類が「電力」であれば、CGS計算用に集計を行う。

                            resultJson["REF"][ref_name]["E_ref_main_MWh"][dd][hh] += \
                                resultJson["REF"][ref_name]["Heatsource"][unit_id]["E_ref_main_kW"][dd][hh] * 3600 / 1000 / bc.fprime

                            resultJson["REF"][ref_name]["Heatsource"][unit_id]["E_ref_main_MWh"][dd][hh] = \
                                resultJson["REF"][ref_name]["Heatsource"][unit_id]["E_ref_main_kW"][dd][hh] * 3600 / 1000 / bc.fprime

                    # 補機電力 [MWh]
                    resultJson["REF"][ref_name]["E_ref_sub_MWh"][dd][hh] += \
                        resultJson["REF"][ref_name]["E_ref_sub"][dd][hh] / 1000

                    # 一次ポンプ電力 [MWh]
                    resultJson["REF"][ref_name]["E_ref_pump_MWh"][dd][hh] += \
                        resultJson["REF"][ref_name]["E_ref_pump"][dd][hh] / 1000

                    # 冷却塔ファン電力 [MWh]
                    resultJson["REF"][ref_name]["E_ref_ct_fan_MWh"][dd][hh] += \
                        resultJson["REF"][ref_name]["E_ref_ct_fan"][dd][hh] / 1000

                    # 冷却水ポンプ電力 [MWh]
                    resultJson["REF"][ref_name]["E_ref_ct_pump_MWh"][dd][hh] += \
                        resultJson["REF"][ref_name]["E_ref_ct_pump"][dd][hh] / 1000

    if debug:  # pragma: no cover

        for ref_name in inputdata["REF"]:
            mf.hourlyplot(resultJson["REF"][ref_name]["E_ref_main"], "熱源主機エネルギー消費量： " + ref_name, "b", "熱源主機エネルギー消費量")

            print(f'--- 熱源群名 {ref_name} ---')
            print(f'熱源群の処理熱量 Qref_hourly: {np.sum(np.sum(resultJson["REF"][ref_name]["Qref_hourly"]))}')
            print(f'熱源主機のエネルギー消費量 E_ref_main: {np.sum(np.sum(resultJson["REF"][ref_name]["E_ref_main"]))}')
            print(f'熱源補機の消費電力 E_ref_sub_MWh: {np.sum(np.sum(resultJson["REF"][ref_name]["E_ref_sub_MWh"]))}')
            print(f'一次ポンプの消費電力 E_ref_pump_MWh: {np.sum(np.sum(resultJson["REF"][ref_name]["E_ref_pump_MWh"]))}')
            print(f'冷却塔ファンの消費電力 E_ref_ct_fan_MWh: {np.sum(np.sum(resultJson["REF"][ref_name]["E_ref_ct_fan_MWh"]))}')
            print(f'冷却塔ポンプの消費電力 E_ref_ct_pump_MWh: {np.sum(np.sum(resultJson["REF"][ref_name]["E_ref_ct_pump_MWh"]))}')

    #----------------------------------------------------------------------------------
    # 熱源群のエネルギー消費量（解説書 2.7.18）
    #----------------------------------------------------------------------------------

    for ref_name in inputdata["REF"]:

        # 熱源主機の電力消費量 [MWh/day]
        resultJson["energy"]["E_ref_main_MWh_day"] += np.sum(resultJson["REF"][ref_name]["E_ref_main_MWh"], axis=1)

        # 熱源主機以外の電力消費量 [MWh/day]
        resultJson["energy"]["E_ref_sub_MWh_day"] += \
            np.sum(resultJson["REF"][ref_name]["E_ref_sub_MWh"] \
                   + resultJson["REF"][ref_name]["E_ref_pump_MWh"] \
                   + resultJson["REF"][ref_name]["E_ref_ct_fan_MWh"] \
                   + resultJson["REF"][ref_name]["E_ref_ct_pump_MWh"], axis=1)

        for dd in range(0, 365):
            for hh in range(0, 24):
                # 熱源主機のエネルギー消費量 [MJ]
                resultJson["energy"]["E_ref_main"] += resultJson["REF"][ref_name]["E_ref_main"][dd][hh]
                # 熱源補機電力消費量 [MWh]
                resultJson["energy"]["E_ref_sub"] += resultJson["REF"][ref_name]["E_ref_sub_MWh"][dd][hh]
                # 一次ポンプ電力消費量 [MWh]
                resultJson["energy"]["E_ref_pump"] += resultJson["REF"][ref_name]["E_ref_pump_MWh"][dd][hh]
                # 冷却塔ファン電力消費量 [MWh]
                resultJson["energy"]["E_ref_ct_fan"] += resultJson["REF"][ref_name]["E_ref_ct_fan_MWh"][dd][hh]
                # 冷却水ポンプ電力消費量 [MWh]
                resultJson["energy"]["E_ref_ct_pump"] += resultJson["REF"][ref_name]["E_ref_ct_pump_MWh"][dd][hh]

    print('熱源エネルギー計算完了')

    if debug:  # pragma: no cover

        print(f'熱源主機エネルギー消費量 E_ref_main: {resultJson["energy"]["E_ref_main"]}')
        print(f'熱源補機電力消費量 E_ref_sub: {resultJson["energy"]["E_ref_sub"]}')
        print(f'一次ポンプ電力消費量 E_ref_pump: {resultJson["energy"]["E_ref_pump"]}')
        print(f'冷却塔ファン電力消費量 E_ref_ct_fan: {resultJson["energy"]["E_ref_ct_fan"]}')
        print(f'冷却水ポンプ電力消費量 E_ref_ct_pump: {resultJson["energy"]["E_ref_ct_pump"]}')

    #----------------------------------------------------------------------------------
    # 設計一次エネルギー消費量（解説書 2.8）
    #----------------------------------------------------------------------------------

    # 空気調和設備の設計一次エネルギー消費量 [MJ]
    resultJson["E_ac"] = \
        + resultJson["energy"]["E_ahu_fan"] * bc.fprime \
        + resultJson["energy"]["E_ahu_aex"] * bc.fprime \
        + resultJson["energy"]["E_pump"] * bc.fprime \
        + resultJson["energy"]["E_ref_main"] \
        + resultJson["energy"]["E_ref_sub"] * bc.fprime \
        + resultJson["energy"]["E_ref_pump"] * bc.fprime \
        + resultJson["energy"]["E_ref_ct_fan"] * bc.fprime \
        + resultJson["energy"]["E_ref_ct_pump"] * bc.fprime

    if debug:  # pragma: no cover
        print(f'空調設備の設計一次エネルギー消費量 MJ/m2 : {resultJson["E_ac"] / resultJson["total_area"]}')
        print(f'空調設備の設計一次エネルギー消費量 MJ : {resultJson["E_ac"]}')

    #----------------------------------------------------------------------------------
    # 基準一次エネルギー消費量 （解説書 10.1）
    #----------------------------------------------------------------------------------    
    for room_zone_name in inputdata["AirConditioningZone"]:
        # 建物用途・室用途、ゾーン面積等の取得
        buildingType = inputdata["Rooms"][room_zone_name]["buildingType"]
        roomType = inputdata["Rooms"][room_zone_name]["roomType"]
        zoneArea = inputdata["Rooms"][room_zone_name]["roomArea"]

        # 空気調和設備の基準一次エネルギー消費量 [MJ]
        resultJson["Es_ac"] += \
            bc.RoomStandardValue[buildingType][roomType]["空調"][inputdata["Building"]["Region"] + "地域"] * zoneArea

    if debug:  # pragma: no cover
        print(f'空調設備の基準一次エネルギー消費量 MJ/m2 : {resultJson["Es_ac"] / resultJson["total_area"]}')
        print(f'空調設備の基準一次エネルギー消費量 MJ : {resultJson["Es_ac"]}')

    # BEI/ACの算出
    resultJson["BEI/AC"] = resultJson["E_ac"] / resultJson["Es_ac"]
    resultJson["BEI/AC"] = math.ceil(resultJson["BEI/AC"] * 100)/100

    #----------------------------------------------------------------------------------
    # CGS計算用変数 （解説書 ８章 附属書 G.10 他の設備の計算結果の読み込み）
    #----------------------------------------------------------------------------------    

    if len(inputdata["CogenerationSystems"]) == 1:  # コジェネがあれば実行

        for cgs_name in inputdata["CogenerationSystems"]:

            # 排熱を冷房に使用するか否か
            if inputdata["CogenerationSystems"][cgs_name]["CoolingSystem"] == None:
                cgs_cooling = False
            else:
                cgs_cooling = True

            # 排熱を暖房に使用するか否か
            if inputdata["CogenerationSystems"][cgs_name]["HeatingSystem"] == None:
                cgs_heating = False
            else:
                cgs_heating = True

            # 排熱利用機器（冷房）
            if cgs_cooling:
                resultJson["for_CGS"]["CGS_refName_C"] = inputdata["CogenerationSystems"][cgs_name]["CoolingSystem"] + "_冷房"
            else:
                resultJson["for_CGS"]["CGS_refName_C"] = None

            # 排熱利用機器（暖房）
            if cgs_heating:
                resultJson["for_CGS"]["CGS_refName_H"] = inputdata["CogenerationSystems"][cgs_name]["HeatingSystem"] + "_暖房"
            else:
                resultJson["for_CGS"]["CGS_refName_H"] = None

        # 熱源主機の電力消費量 [MWh/day]
        resultJson["for_CGS"]["E_ref_main_MWh_day"] = resultJson["energy"]["E_ref_main_MWh_day"]  # 後半でCGSから排熱供給を受ける熱源群の電力消費量を差し引く。

        # 熱源補機の電力消費量 [MWh/day]
        resultJson["for_CGS"]["E_ref_sub_MWh_day"] = resultJson["energy"]["E_ref_sub_MWh_day"]

        # 二次ポンプ群の電力消費量 [MWh/day]
        resultJson["for_CGS"]["E_pump_MWh_day"] = resultJson["energy"]["E_pump_MWh_day"]

        # 空調機群の電力消費量 [MWh/day]
        resultJson["for_CGS"]["E_fan_MWh_day"] = resultJson["energy"]["E_fan_MWh_day"]

        # 排熱利用熱源系統

        for ref_name in inputdata["REF"]:

            # CGS系統の「排熱利用する冷熱源」　。　蓄熱がある場合は「追い掛け運転」を採用（2020/7/6変更）
            if ref_name == resultJson["for_CGS"]["CGS_refName_C"]:

                for unit_id, unit_configure in enumerate(inputdata["REF"][ref_name]["Heatsource"]):

                    heatsource_using_exhaust_heat = [
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

                    if unit_configure["HeatsourceType"] in heatsource_using_exhaust_heat:

                        # CGS系統の「排熱利用する冷熱源」の「吸収式冷凍機（都市ガス）」の一次エネルギー消費量 [MJ]
                        for dd in range(0, 365):
                            resultJson["for_CGS"]["E_ref_cgsC_ABS_day"][dd] += np.sum(resultJson["REF"][ref_name]["Heatsource"][unit_id]["E_ref_main_MJ"][dd])

                            # 排熱投入型吸収式冷温水機jの定格冷却能力
                        resultJson["for_CGS"]["qAC_link_c_j_rated"] += inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedCapacity_total"]

                        # 排熱投入型吸収式冷温水機jの主機定格消費エネルギー
                        resultJson["for_CGS"]["EAC_link_c_j_rated"] += inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedFuelConsumption_total"]

                        resultJson["for_CGS"]["NAC_ref_link"] += 1

                # CGSの排熱利用が可能な排熱投入型吸収式冷温水機(系統)の冷熱源としての負荷率 [-]
                for dd in range(0, 365):
                    Qref_daily = 0
                    Tref_daily = 0
                    for hh in range(0, 24):
                        if resultJson["REF"][ref_name]["Qref_hourly"][dd][hh] > 0:
                            Qref_daily += resultJson["REF"][ref_name]["Qref_hourly"][dd][hh]
                            Tref_daily += 1

                    if Tref_daily > 0:
                        resultJson["for_CGS"]["Lt_ref_cgsC_day"][dd] = \
                            (Qref_daily * 1000 / 3600) / Tref_daily / inputdata["REF"][ref_name]["Qref_rated"]

                    if resultJson["for_CGS"]["Lt_ref_cgsC_day"][dd] > 1:
                        resultJson["for_CGS"]["Lt_ref_cgsC_day"][dd] = 1.2

                    # CGSの排熱利用が可能な排熱投入型吸収式冷温水機(系統)の運転時間 [h/日]
                    resultJson["for_CGS"]["T_ref_cgsC_day"][dd] = Tref_daily

            # CGS系統の「排熱利用する温熱源」
            if ref_name == resultJson["for_CGS"]["CGS_refName_H"]:

                # 当該温熱源群の主機の消費電力を差し引く。
                for unit_id, unit_configure in enumerate(inputdata["REF"][ref_name]["Heatsource"]):
                    for dd in range(0, 365):
                        resultJson["for_CGS"]["E_ref_main_MWh_day"][dd] -= np.sum(resultJson["REF"][ref_name]["Heatsource"][unit_id]["E_ref_main_MWh"][dd])

                # CGSの排熱利用が可能な温熱源群の主機の一次エネルギー消費量 [MJ/日]
                resultJson["for_CGS"]["E_ref_cgsH_day"] = np.sum(resultJson["REF"][ref_name]["E_ref_main"], axis=1)

                # CGSの排熱利用が可能な温熱源群の熱源負荷 [MJ/日]
                resultJson["for_CGS"]["Q_ref_cgsH_day"] = np.sum(resultJson["REF"][ref_name]["Qref_hourly"], axis=1)

                # CGSの排熱利用が可能な温熱源群の運転時間 [h/日]
                for dd in range(0, 365):
                    for hh in range(0, 24):
                        if resultJson["REF"][ref_name]["Qref_hourly"][dd][hh] > 0:
                            resultJson["for_CGS"]["T_ref_cgsH_day"][dd] += 1

        # 空気調和設備の電力消費量 [MWh/day]
        resultJson["for_CGS"]["electric_power_consumption"] = \
            + resultJson["for_CGS"]["E_ref_main_MWh_day"] \
            + resultJson["for_CGS"]["E_ref_sub_MWh_day"] \
            + resultJson["for_CGS"]["E_pump_MWh_day"] \
            + resultJson["for_CGS"]["E_fan_MWh_day"]

    # if debug:
    #     with open("inputdataJson_AC.json",'w', encoding='utf-8') as fw:
    #         json.dump(inputdata, fw, indent=4, ensure_ascii=False, cls = bc.MyEncoder)

    # 入力データの保存
    resultJson["inputdata"] = inputdata

    return resultJson


if __name__ == '__main__':  # pragma: no cover

    print('----- airconditioning.py -----')
