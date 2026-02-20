import json
import numpy as np
import math
import os
import copy
# import matplotlib.pyplot as plt

import sys

from builelib import commons as bc
from builelib.climate import climate
from builelib.envelope import shading
# from . import make_figure as mf

# データベースファイルの保存場所
database_directory =  os.path.dirname(os.path.abspath(__file__)) + "/database/"
# 気象データファイルの保存場所
from builelib.climate import CLIMATEDATA_DIR as climatedata_directory

def air_enthalpy(Tdb, X):
    """
    空気のエンタルピーを算出する関数
    (WEBPROに合わせる)
    """
    
    Ca = 1.006  # 乾き空気の定圧比熱 [kJ/kg･K]
    Cw = 1.805  # 水蒸気の定圧比熱 [kJ/kg･K]
    Lw = 2502   # 水の蒸発潜熱 [kJ/kg]

    if len(Tdb) != len(X):
        raise Exception('温度と湿度のリストの長さが異なります。')
    else:
        
        H = np.zeros(len(Tdb))
        for i in range(0, len(Tdb)):
            H[i] = (Ca*Tdb[i] + (Cw*Tdb[i]+Lw)*X[i])

    return H   

def calc_palstar(inputdata, debug = False):

    inputdata["PUMP"] = {}
    inputdata["REF"] = {}

    # 計算結果を格納する変数
    resultJson = {
        "PAL": 0,
        "Qroom": {
        },
    }

    ##----------------------------------------------------------------------------------
    ## マトリックスの設定
    ##----------------------------------------------------------------------------------

    # 地域別データの読み込み
    with open(database_directory + 'AREA.json', 'r', encoding='utf-8') as f:
        Area = json.load(f)


    ##----------------------------------------------------------------------------------
    ## 気象データ（解説書 2.2.1）
    ## 任意評定 （SP-5: 気象データ)
    ##----------------------------------------------------------------------------------

    if "climate_data" in inputdata["SpecialInputData"]:  # 任意入力（SP-5）

        # 外気温 [℃]
        ToutALL = np.array(inputdata["SpecialInputData"]["climate_data"]["Tout"])
        # 外気湿度 [kg/kgDA]
        XoutALL = np.array(inputdata["SpecialInputData"]["climate_data"]["Xout"])
        # 法線面直達日射量 [W/m2]
        IodALL  = np.array(inputdata["SpecialInputData"]["climate_data"]["Iod"])
        # 水平面天空日射量 [W/m2]
        IosALL  = np.array(inputdata["SpecialInputData"]["climate_data"]["Ios"])
        # 水平面夜間放射量 [W/m2]
        InnALL  = np.array(inputdata["SpecialInputData"]["climate_data"]["Inn"])

    else:

        # 気象データ（HASP形式）読み込み ＜365×24の行列＞
        [ToutALL, XoutALL, IodALL, IosALL, InnALL] = \
            climate.readHaspClimateData( climatedata_directory + "/" + Area[inputdata["Building"]["Region"]+"地域"]["気象データファイル名"] )

    # 緯度
    phi  = Area[inputdata["Building"]["Region"]+"地域"]["緯度"]
    # 経度
    longi  = Area[inputdata["Building"]["Region"]+"地域"]["経度"]

    ##----------------------------------------------------------------------------------
    ## 冷暖房期間（解説書 2.2.2）
    ##----------------------------------------------------------------------------------

    # 空調運転モード
    with open(database_directory + 'ACoperationMode.json', 'r', encoding='utf-8') as f:
        ACoperationMode = json.load(f)

    # 各日の冷暖房期間の種類（冷房期、暖房期、中間期）（365×1の行列）
    ac_mode = ACoperationMode[ Area[inputdata["Building"]["Region"]+"地域"]["空調運転モードタイプ"] ]


    ##----------------------------------------------------------------------------------
    ## 平均外気温（解説書 2.2.3）
    ##----------------------------------------------------------------------------------

    # 日平均外気温[℃]（365×1）
    Toa_ave = np.mean(ToutALL,1)
    Toa_day = np.mean(ToutALL[:,[6,7,8,9,10,11,12,13,14,15,16,17]],1)
    Toa_ngt = np.mean(ToutALL[:,[0,1,2,3,4,5,18,19,20,21,22,23]],1)

    # 日平均外気絶対湿度 [kg/kgDA]（365×1）
    Xoa_ave = np.mean(XoutALL,1)
    Xoa_day = np.mean(XoutALL[:,[6,7,8,9,10,11,12,13,14,15,16,17]],1)
    Xoa_ngt = np.mean(XoutALL[:,[0,1,2,3,4,5,18,19,20,21,22,23]],1)


    ##----------------------------------------------------------------------------------
    ## 外気エンタルピー（解説書 2.2.4）
    ##----------------------------------------------------------------------------------

    Hoa_ave = air_enthalpy(Toa_ave, Xoa_ave)
    Hoa_day = air_enthalpy(Toa_day, Xoa_day)
    Hoa_ngt = air_enthalpy(Toa_ngt, Xoa_ngt)


    ##----------------------------------------------------------------------------------
    ## 空調室の設定温度、室内エンタルピー（解説書 2.3.1、2.3.2）
    ##----------------------------------------------------------------------------------

    TroomSP = np.zeros(365)    # 室内設定温度
    RroomSP = np.zeros(365)    # 室内設定湿度
    Hroom   = np.zeros(365)    # 室内設定エンタルピー

    for dd in range(0,365):

        if ac_mode[dd] == "冷房":
            TroomSP[dd] = 26
            RroomSP[dd] = 50
            Hroom[dd] = 52.91

        elif ac_mode[dd] == "中間":
            TroomSP[dd] = 24
            RroomSP[dd] = 50
            Hroom[dd] = 47.81

        elif ac_mode[dd] == "暖房":
            TroomSP[dd] = 22
            RroomSP[dd] = 40
            Hroom[dd] = 38.81



    ##----------------------------------------------------------------------------------
    ## 空調機の稼働状態、内部発熱量（解説書 2.3.3、2.3.4）
    ##----------------------------------------------------------------------------------

    roomAreaTotal = 0
    roomScheduleRoom   = {}
    roomScheduleLight  = {}
    roomSchedulePerson = {}
    roomScheduleOAapp  = {}
    roomDayMode        = {}

    # 空調ゾーン毎にループ
    for room_zone_name in inputdata["AirConditioningZone"]:

        if room_zone_name in inputdata["Rooms"]:  # ゾーン分けがない場合

            # 建物用途・室用途、ゾーン面積等の取得
            inputdata["AirConditioningZone"][room_zone_name]["buildingType"]  = inputdata["Rooms"][room_zone_name]["buildingType"]
            inputdata["AirConditioningZone"][room_zone_name]["roomType"]      = inputdata["Rooms"][room_zone_name]["roomType"]
            inputdata["AirConditioningZone"][room_zone_name]["zoneArea"]      = inputdata["Rooms"][room_zone_name]["roomArea"]
            inputdata["AirConditioningZone"][room_zone_name]["ceilingHeight"] = inputdata["Rooms"][room_zone_name]["ceilingHeight"]
                
        else:

            # 各室のゾーンを検索
            for room_name in inputdata["Rooms"]:
                if inputdata["Rooms"][room_name]["zone"] != None:   # ゾーンがあれば
                    for zone_name  in inputdata["Rooms"][room_name]["zone"]:   # ゾーン名を検索
                        if room_zone_name == (room_name+"_"+zone_name):

                            inputdata["AirConditioningZone"][room_zone_name]["buildingType"]  = inputdata["Rooms"][room_name]["buildingType"]
                            inputdata["AirConditioningZone"][room_zone_name]["roomType"]      = inputdata["Rooms"][room_name]["roomType"]
                            inputdata["AirConditioningZone"][room_zone_name]["ceilingHeight"] = inputdata["Rooms"][room_name]["ceilingHeight"]
                            inputdata["AirConditioningZone"][room_zone_name]["zoneArea"]      = inputdata["Rooms"][room_name]["zone"][zone_name]["zoneArea"]

                            break

        # 365日×24時間分のスケジュール （365×24の行列を格納した dict型）
        roomScheduleRoom[room_zone_name], roomScheduleLight[room_zone_name], roomSchedulePerson[room_zone_name], roomScheduleOAapp[room_zone_name], roomDayMode[room_zone_name] = \
            bc.get_roomUsageSchedule(inputdata["AirConditioningZone"][room_zone_name]["buildingType"], inputdata["AirConditioningZone"][room_zone_name]["roomType"], "")


        # 空調対象面積の合計
        roomAreaTotal += inputdata["AirConditioningZone"][room_zone_name]["zoneArea"]



    ##----------------------------------------------------------------------------------
    ## 室負荷計算（解説書 2.4）
    ##----------------------------------------------------------------------------------

    for room_zone_name in inputdata["AirConditioningZone"]:

        resultJson["Qroom"][room_zone_name] = {
            "Troom": TroomSP,   # 室内温度 [℃]
            "Hroom": Hroom,     # 室内エンタルピー [kJ/kg]
            "Tout": Toa_ave,    # 室外温度（日平均値） [℃]
            "Qwall_T": np.zeros(365),  # 壁からの温度差による熱取得 [W/m2]
            "Qwall_S": np.zeros(365),  # 壁からの日射による熱取得 [W/m2]
            "Qwall_N": np.zeros(365),  # 壁からの夜間放射による熱取得（マイナス）[W/m2]
            "Qwind_T": np.zeros(365),  # 窓からの温度差による熱取得 [W/m2]
            "Qwind_S": np.zeros(365),  # 窓からの日射による熱取得 [W/m2]
            "Qwind_N": np.zeros(365),  # 窓からの夜間放射による熱取得（マイナス）[W/m2]
            "QroomDc": np.zeros(365),  # 冷房熱取得（日積算）　[MJ/day]
            "QroomDh": np.zeros(365),  # 暖房熱取得（日積算）　[MJ/day]
        }

    ##----------------------------------------------------------------------------------
    ## 外皮面への入射日射量（解説書 2.4.1）
    ##----------------------------------------------------------------------------------

    solor_radiation = {
        "直達":{
        },
        "直達_入射角特性込":{
        },
        "天空":{
        },
        "夜間":{
        }
    }

    # 方位角別の日射量
    (solor_radiation["直達"]["南"],  solor_radiation["直達_入射角特性込"]["南"], solor_radiation["天空"]["垂直"], solor_radiation["夜間"]["垂直"])  = \
        climate.solarRadiationByAzimuth(  0, 90, phi, longi, IodALL, IosALL, InnALL)
    (solor_radiation["直達"]["南西"], solor_radiation["直達_入射角特性込"]["南西"], _, _) = climate.solarRadiationByAzimuth( 45, 90, phi, longi, IodALL, IosALL, InnALL)
    (solor_radiation["直達"]["西"],  solor_radiation["直達_入射角特性込"]["西"], _, _)  = climate.solarRadiationByAzimuth( 90, 90, phi, longi, IodALL, IosALL, InnALL)
    (solor_radiation["直達"]["北西"], solor_radiation["直達_入射角特性込"]["北西"], _, _) = climate.solarRadiationByAzimuth(135, 90, phi, longi, IodALL, IosALL, InnALL)
    (solor_radiation["直達"]["北"],  solor_radiation["直達_入射角特性込"]["北"], _, _)  = climate.solarRadiationByAzimuth(180, 90, phi, longi, IodALL, IosALL, InnALL)
    (solor_radiation["直達"]["北東"], solor_radiation["直達_入射角特性込"]["北東"], _, _) = climate.solarRadiationByAzimuth(225, 90, phi, longi, IodALL, IosALL, InnALL)
    (solor_radiation["直達"]["東"],  solor_radiation["直達_入射角特性込"]["東"], _, _)  = climate.solarRadiationByAzimuth(270, 90, phi, longi, IodALL, IosALL, InnALL)
    (solor_radiation["直達"]["南東"], solor_radiation["直達_入射角特性込"]["南東"], _, _) = climate.solarRadiationByAzimuth(315, 90, phi, longi, IodALL, IosALL, InnALL)
    (solor_radiation["直達"]["水平"], solor_radiation["直達_入射角特性込"]["水平"], solor_radiation["天空"]["水平"], solor_radiation["夜間"]["水平"])  = \
        climate.solarRadiationByAzimuth(  0,  0, phi, longi, IodALL, IosALL, InnALL)



    ##----------------------------------------------------------------------------------
    ## 外壁等の熱貫流率の算出（解説書 附属書A.1）
    ##----------------------------------------------------------------------------------

    ### ISSUE : 二つのデータベースにわかれてしまっているので統一する。###

    # 標準入力法建材データの読み込み
    with open(database_directory + 'HeatThermalConductivity.json', 'r', encoding='utf-8') as f:
        HeatThermalConductivity = json.load(f)

    # モデル建物法建材データの読み込み
    with open(database_directory + 'HeatThermalConductivity_model.json', 'r', encoding='utf-8') as f:
        HeatThermalConductivity_model = json.load(f)


    if "WallConfigure" in inputdata:  # WallConfigure があれば以下を実行

        for wall_name in inputdata["WallConfigure"].keys():

            if inputdata["WallConfigure"][wall_name]["inputMethod"] == "断熱材種類を入力":

                if inputdata["WallConfigure"][wall_name]["materialID"] == "無": # 断熱材種類が「無」の場合

                    inputdata["WallConfigure"][wall_name]["Uvalue_wall"]  = 2.63
                    inputdata["WallConfigure"][wall_name]["Uvalue_roof"]  = 1.53
                    inputdata["WallConfigure"][wall_name]["Uvalue_floor"] = 2.67

                else: # 断熱材種類が「無」以外、もしくは、熱伝導率が直接入力されている場合

                    # 熱伝導率の指定がない場合は「断熱材種類」から推定
                    if (inputdata["WallConfigure"][wall_name]["conductivity"] == None):
                        
                        inputdata["WallConfigure"][wall_name]["conductivity"] = \
                            float( HeatThermalConductivity_model[ inputdata["WallConfigure"][wall_name]["materialID"] ] )

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
                                Rvalue += (layer[1]["thickness"]/1000) / HeatThermalConductivity[material_name]["熱伝導率"]

                    else:

                        # 熱伝導率を入力している場合
                        Rvalue += (layer[1]["thickness"]/1000) / layer[1]["conductivity"]
                    
                inputdata["WallConfigure"][wall_name]["Uvalue"] = 1/Rvalue


    ##----------------------------------------------------------------------------------
    ## 窓の熱貫流率及び日射熱取得率の算出（解説書 附属書A.2）
    ##----------------------------------------------------------------------------------

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
                WindowHeatTransferPerformance\
                    [ inputdata["WindowConfigure"][window_name]["glassID"] ]\
                    [ inputdata["WindowConfigure"][window_name]["frameType"] ]["熱貫流率"]

                inputdata["WindowConfigure"][window_name]["Uvalue_blind"] = \
                WindowHeatTransferPerformance\
                    [ inputdata["WindowConfigure"][window_name]["glassID"] ]\
                    [ inputdata["WindowConfigure"][window_name]["frameType"] ]["熱貫流率・ブラインド込"]

                inputdata["WindowConfigure"][window_name]["Ivalue"] = \
                WindowHeatTransferPerformance\
                    [ inputdata["WindowConfigure"][window_name]["glassID"] ]\
                    [ inputdata["WindowConfigure"][window_name]["frameType"] ]["日射熱取得率"]

                inputdata["WindowConfigure"][window_name]["Ivalue_blind"] = \
                WindowHeatTransferPerformance\
                    [ inputdata["WindowConfigure"][window_name]["glassID"] ]\
                    [ inputdata["WindowConfigure"][window_name]["frameType"] ]["日射熱取得率・ブラインド込"]


            elif inputdata["WindowConfigure"][window_name]["inputMethod"] == "ガラスの性能を入力":

                ku_a = 0
                ku_b = 0
                kita  = 0
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
                kita  = glass2window[inputdata["WindowConfigure"][window_name]["frameType"]][inputdata["WindowConfigure"][window_name]["layerType"]]["kita"]            

                inputdata["WindowConfigure"][window_name]["Uvalue"] = ku_a * inputdata["WindowConfigure"][window_name]["glassUvalue"] + ku_b
                inputdata["WindowConfigure"][window_name]["Ivalue"] = kita * inputdata["WindowConfigure"][window_name]["glassIvalue"]

                # ガラスの熱貫流率と日射熱取得率が入力されている場合は、ブラインドの効果を見込む
                dR = (0.021 / inputdata["WindowConfigure"][window_name]["glassUvalue"]) + 0.022

                inputdata["WindowConfigure"][window_name]["Uvalue_blind"] = \
                    1 / ( ( 1/inputdata["WindowConfigure"][window_name]["Uvalue"]) + dR )

                inputdata["WindowConfigure"][window_name]["Ivalue_blind"] = \
                    inputdata["WindowConfigure"][window_name]["Ivalue"] / inputdata["WindowConfigure"][window_name]["glassIvalue"] \
                        * (-0.1331 * inputdata["WindowConfigure"][window_name]["glassIvalue"] ** 2 +\
                                0.8258 * inputdata["WindowConfigure"][window_name]["glassIvalue"] )


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
                        1 / ( ( 1/inputdata["WindowConfigure"][window_name]["windowUvalue"]) + dR )

                    inputdata["WindowConfigure"][window_name]["Ivalue_blind"] = \
                        inputdata["WindowConfigure"][window_name]["windowIvalue"] / inputdata["WindowConfigure"][window_name]["glassIvalue"] \
                            * (-0.1331 * inputdata["WindowConfigure"][window_name]["glassIvalue"] ** 2 +\
                                0.8258 * inputdata["WindowConfigure"][window_name]["glassIvalue"] )


            if debug: # pragma: no cover
                print(f'--- 窓名称 {window_name} ---')
                print(f'窓の熱貫流率 Uvalue : {inputdata["WindowConfigure"][window_name]["Uvalue"]}')
                print(f'窓+BLの熱貫流率 Uvalue_blind : {inputdata["WindowConfigure"][window_name]["Uvalue_blind"]}')

    ##----------------------------------------------------------------------------------
    ## 外壁の面積の計算（解説書 2.4.2.1）
    ##----------------------------------------------------------------------------------

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

        for (wall_id, wall_configure) in enumerate( inputdata["EnvelopeSet"][room_zone_name]["WallList"] ):

            window_total = 0  # 窓面積の集計用

            if "WindowList" in wall_configure:   # 窓がある場合

                # 窓面積の合計を求める（Σ{窓面積×枚数}）
                for (window_id, window_configure) in enumerate(wall_configure["WindowList"]):

                    if window_configure["WindowID"] != "無":

                        window_total += \
                            inputdata["WindowConfigure"][ window_configure["WindowID"] ]["windowArea"] * window_configure["WindowNumber"]


            # 壁のみの面積（窓がない場合は、window_total = 0）
            if wall_configure["EnvelopeArea"] >= window_total:
                inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WallArea"] = wall_configure["EnvelopeArea"] - window_total
            else:
                print(room_zone_name)
                print(wall_configure)
                raise Exception('窓面積が外皮面積よりも大きくなっています')


    ##----------------------------------------------------------------------------------
    ## ペリメータゾーン面積
    ##----------------------------------------------------------------------------------
    
    for room_zone_name in inputdata["EnvelopeSet"]:

        resultJson["Qroom"][room_zone_name]["perimeter_area"] = 0
        resultJson["Qroom"][room_zone_name]["perimeter_area_for_internal_gain"] = 0

        # 仮想床係数（階高が5m以上である場合の補正係数）
        resultJson["Qroom"][room_zone_name]["perimeter_virtual_floor"] = 1

        # 仮想床係数（階高が5m以上である場合の補正係数）
        if inputdata["Rooms"][room_zone_name]["floorHeight"] > 5:
            resultJson["Qroom"][room_zone_name]["perimeter_virtual_floor"] = \
                inputdata["Rooms"][room_zone_name]["floorHeight"] / 5

        # ペリメータ面積
        perimeter_area_horizontal = 0
        perimeter_area_vertical = 0
        
        for (wall_id, wall_configure) in enumerate( inputdata["EnvelopeSet"][room_zone_name]["WallList"] ):

            if "水平" in wall_configure["Direction"]:
                perimeter_area_horizontal += wall_configure["EnvelopeArea"]                
            else:
                perimeter_area_vertical += 5 * (wall_configure["EnvelopeArea"] / inputdata["Rooms"][room_zone_name]["floorHeight"])

        # ペリメータ面積の計算
        resultJson["Qroom"][room_zone_name]["perimeter_area"] = \
            perimeter_area_horizontal + perimeter_area_vertical * resultJson["Qroom"][room_zone_name]["perimeter_virtual_floor"]

        # ペリメータ面積の計算（内部発熱・外気負荷計算用）
        resultJson["Qroom"][room_zone_name]["perimeter_area_for_internal_gain"] = \
            max(perimeter_area_horizontal, perimeter_area_vertical)                
            

    ##----------------------------------------------------------------------------------
    ## 室の定常熱取得の計算（解説書 2.4.2.2〜2.4.2.7）
    ##----------------------------------------------------------------------------------

    ## EnvelopeSet に WallConfigure, WindowConfigure の情報を貼り付ける。
    for room_zone_name in inputdata["EnvelopeSet"]:

        # 壁毎にループ
        for (wall_id, wall_configure) in enumerate( inputdata["EnvelopeSet"][room_zone_name]["WallList"]):

            if inputdata["WallConfigure"][  wall_configure["WallSpec"]  ]["inputMethod"] == "断熱材種類を入力":

                if wall_configure["Direction"] == "水平（上）":  # 天井と見なす。

                    # 外壁のUA（熱貫流率×面積）を計算
                    inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["UA_wall"] = \
                        inputdata["WallConfigure"][  wall_configure["WallSpec"]  ]["Uvalue_roof"] * wall_configure["WallArea"]

                elif wall_configure["Direction"] == "水平（下）":  # 床と見なす。

                    # 外壁のUA（熱貫流率×面積）を計算
                    inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["UA_wall"] = \
                        inputdata["WallConfigure"][  wall_configure["WallSpec"]  ]["Uvalue_floor"] * wall_configure["WallArea"]

                else:

                    # 外壁のUA（熱貫流率×面積）を計算
                    inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["UA_wall"] = \
                        inputdata["WallConfigure"][  wall_configure["WallSpec"]  ]["Uvalue_wall"] * wall_configure["WallArea"]

            else:

                # 外壁のUA（熱貫流率×面積）を計算
                inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["UA_wall"] = \
                    inputdata["WallConfigure"][  wall_configure["WallSpec"]  ]["Uvalue"] * wall_configure["WallArea"]
                
            # 日射吸収率
            if inputdata["WallConfigure"][  wall_configure["WallSpec"]  ]["solarAbsorptionRatio"] == None:
                inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["solarAbsorptionRatio"] = 0.8
            else:
                inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["solarAbsorptionRatio"] = \
                    float(inputdata["WallConfigure"][  wall_configure["WallSpec"]  ]["solarAbsorptionRatio"])
                
            for (window_id, window_configure) in enumerate( inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WindowList"]):

                if window_configure["WindowID"] != "無":

                    # 日よけ効果係数の算出
                    if window_configure["EavesID"] == "無":

                        inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WindowList"][window_id]["shadingEffect_C"] = 1
                        inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WindowList"][window_id]["shadingEffect_H"] = 1

                    else:

                        if inputdata["ShadingConfigure"][ window_configure["EavesID"] ]["shadingEffect_C"] != None and \
                            inputdata["ShadingConfigure"][ window_configure["EavesID"] ]["shadingEffect_H"] != None :

                            inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WindowList"][window_id]["shadingEffect_C"] = \
                                inputdata["ShadingConfigure"][ window_configure["EavesID"] ]["shadingEffect_C"]
                            inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WindowList"][window_id]["shadingEffect_H"] = \
                                inputdata["ShadingConfigure"][ window_configure["EavesID"] ]["shadingEffect_H"]

                        else:

                            # 関数 shading.calc_shadingCoefficient で日よけ効果係数を算出。
                            (inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WindowList"][window_id]["shadingEffect_C"], \
                                inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WindowList"][window_id]["shadingEffect_H"] ) =  \
                                    shading.calc_shadingCoefficient(inputdata["Building"]["Region"],\
                                        wall_configure["Direction"], \
                                        inputdata["ShadingConfigure"][ window_configure["EavesID"] ]["x1"],\
                                        inputdata["ShadingConfigure"][ window_configure["EavesID"] ]["x2"],\
                                        inputdata["ShadingConfigure"][ window_configure["EavesID"] ]["x3"],\
                                        inputdata["ShadingConfigure"][ window_configure["EavesID"] ]["y1"],\
                                        inputdata["ShadingConfigure"][ window_configure["EavesID"] ]["y2"],\
                                        inputdata["ShadingConfigure"][ window_configure["EavesID"] ]["y3"],\
                                        inputdata["ShadingConfigure"][ window_configure["EavesID"] ]["zxPlus"],\
                                        inputdata["ShadingConfigure"][ window_configure["EavesID"] ]["zxMinus"],\
                                        inputdata["ShadingConfigure"][ window_configure["EavesID"] ]["zyPlus"],\
                                        inputdata["ShadingConfigure"][ window_configure["EavesID"] ]["zyMinus"])


                    # 窓のUA（熱貫流率×面積）を計算
                    if window_configure["isBlind"] == "無":  # ブラインドがない場合

                        inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WindowList"][window_id]["UA_window"] = \
                            window_configure["WindowNumber"] * inputdata["WindowConfigure"][ window_configure["WindowID"] ]["windowArea"] * \
                            inputdata["WindowConfigure"][ window_configure["WindowID"] ]["Uvalue"]

                        inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WindowList"][window_id]["IA_window"] = \
                            window_configure["WindowNumber"] * inputdata["WindowConfigure"][ window_configure["WindowID"] ]["windowArea"] * \
                            inputdata["WindowConfigure"][ window_configure["WindowID"] ]["Ivalue"]

                    elif window_configure["isBlind"] == "有": # ブラインドがある場合

                        inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WindowList"][window_id]["UA_window"] = \
                            window_configure["WindowNumber"] * inputdata["WindowConfigure"][ window_configure["WindowID"] ]["windowArea"] * \
                            inputdata["WindowConfigure"][ window_configure["WindowID"] ]["Uvalue_blind"]

                        inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WindowList"][window_id]["IA_window"] = \
                            window_configure["WindowNumber"] * inputdata["WindowConfigure"][ window_configure["WindowID"] ]["windowArea"] * \
                            inputdata["WindowConfigure"][ window_configure["WindowID"] ]["Ivalue_blind"]



    for room_zone_name in inputdata["AirConditioningZone"]:

        Qwall_T  = np.zeros(365)  # 壁からの温度差による熱取得 [W]
        Qwall_S  = np.zeros(365)  # 壁からの日射による熱取得 [W]
        Qwall_N  = np.zeros(365)  # 壁からの夜間放射による熱取得（マイナス）[W]
        Qwind_T  = np.zeros(365)  # 窓からの温度差による熱取得 [W]
        Qwind_S  = np.zeros(365)  # 窓からの日射による熱取得 [W]
        Qwind_N  = np.zeros(365)  # 窓からの夜間放射による熱取得（マイナス）[W]

        # 外壁があれば以下を実行
        if room_zone_name in inputdata["EnvelopeSet"]:

            # 壁毎にループ
            for (wall_id, wall_configure) in enumerate( inputdata["EnvelopeSet"][room_zone_name]["WallList"] ):

                if wall_configure["WallType"] == "日の当たる外壁":
                
                    ## ① 温度差による熱取得
                    Qwall_T += wall_configure["UA_wall"] * (Toa_ave - TroomSP) * 24

                    ## ② 日射による熱取得
                    if wall_configure["Direction"] == "水平（上）" or wall_configure["Direction"] == "水平（下）":
                        Qwall_S += wall_configure["UA_wall"] * wall_configure["solarAbsorptionRatio"] * 0.04 * \
                            (solor_radiation["直達"]["水平"] + solor_radiation["天空"]["水平"])
                    else:
                        Qwall_S += wall_configure["UA_wall"] * wall_configure["solarAbsorptionRatio"] * 0.04 * \
                            (solor_radiation["直達"][ wall_configure["Direction"] ] + solor_radiation["天空"]["垂直"])

                    ## ③ 夜間放射による熱取得（マイナス）
                    if wall_configure["Direction"] == "水平（上）" or wall_configure["Direction"] == "水平（下）":
                        Qwall_N -= wall_configure["UA_wall"] * 0.9 * 0.04 * (solor_radiation["夜間"]["水平"])
                    else:
                        Qwall_N -= wall_configure["UA_wall"] * 0.9 * 0.04 * (solor_radiation["夜間"]["垂直"])                    

                # elif wall_configure["WallType"] == "日の当たらない外壁":

                #     ## ① 温度差による熱取得
                #     Qwall_T = Qwall_T + wall_configure["UA_wall"] * (Toa_ave - TroomSP) * 24

                #     ## ③ 夜間放射による熱取得（マイナス）
                #     if wall_configure["Direction"] == "水平（上）" or wall_configure["Direction"] == "水平（下）":
                #         Qwall_N = Qwall_N - wall_configure["UA_wall"] * 0.9 * 0.04 * \
                #             (solor_radiation["夜間"]["水平"])
                #     else:
                #         Qwall_N = Qwall_N - wall_configure["UA_wall"] * 0.9 * 0.04 * \
                #             (solor_radiation["夜間"]["垂直"])                    

                # elif wall_configure["WallType"] == "地盤に接する外壁":
                
                #     ## ① 温度差による熱取得
                #     Qwall_T = Qwall_T + wall_configure["UA_wall"] * (np.mean(Toa_ave)* np.ones(365) - TroomSP) * 24

                #     ## ③ 夜間放射による熱取得（マイナス） ：　本当はこれは不要。Webproの実装と合わせるために追加。
                #     Qwall_N = Qwall_N - wall_configure["UA_wall"] * 0.9 * 0.04 * (solor_radiation["夜間"]["垂直"])   

                # elif wall_configure["WallType"] == "地盤に接する外壁_Ver2":  # Webpro Ver2の互換のための処理
                
                #     ## ① 温度差による熱取得
                #     Qwall_T = Qwall_T + wall_configure["UA_wall"] * (np.mean(Toa_ave)* np.ones(365) - TroomSP) * 24

                #     ## ② 日射による熱取得
                #     if wall_configure["Direction"] == "水平（上）" or wall_configure["Direction"] == "水平（下）":
                #         Qwall_S = Qwall_S + wall_configure["UA_wall"] * wall_configure["solarAbsorptionRatio"] * 0.04 * \
                #             (solor_radiation["直達"]["水平"]+solor_radiation["天空"]["水平"])
                #     else:
                #         Qwall_S = Qwall_S + wall_configure["UA_wall"] * wall_configure["solarAbsorptionRatio"] * 0.04 * \
                #             (solor_radiation["直達"][ wall_configure["Direction"] ]+solor_radiation["天空"]["垂直"])

                #     ## ③ 夜間放射による熱取得（マイナス）
                #     if wall_configure["Direction"] == "水平（上）" or wall_configure["Direction"] == "水平（下）":
                #         Qwall_N = Qwall_N - wall_configure["UA_wall"] * 0.9 * 0.04 * \
                #             (solor_radiation["夜間"]["水平"])
                #     else:
                #         Qwall_N = Qwall_N - wall_configure["UA_wall"] * 0.9 * 0.04 * \
                #             (solor_radiation["夜間"]["垂直"])   


                # 窓毎にループ
                for (window_id, window_configure) in enumerate( wall_configure["WindowList"]):

                    if window_configure["WindowID"] != "無":  # 窓がある場合

                        if wall_configure["WallType"] == "日の当たる外壁" or wall_configure["WallType"] == "地盤に接する外壁_Ver2":
                        
                            ## ① 温度差による熱取得
                            Qwind_T = Qwind_T + window_configure["UA_window"]*(Toa_ave-TroomSP)*24

                            ## ② 日射による熱取得
                            shading_daily = np.zeros(365)

                            for dd in range(0,365):

                                if ac_mode[dd] == "冷房":
                                    shading_daily[dd] = window_configure["shadingEffect_C"]
                                elif ac_mode[dd] == "中間":
                                    shading_daily[dd] = window_configure["shadingEffect_C"]
                                elif ac_mode[dd] == "暖房":
                                    shading_daily[dd] = window_configure["shadingEffect_H"]
                            
                            if isinstance(window_configure["IA_window"], float):

                                # 様式2-3に入力された窓仕様を使用する場合
                                # 0.88は標準ガラスの日射熱取得率
                                # 0.89は標準ガラスの入射角特性の最大値
                                # 0.808は天空・反射日射に対する標準ガラスの入射角特性 0.808/0.88 = 0.91818
                                if wall_configure["Direction"] == "水平（上）" or wall_configure["Direction"] == "水平（下）":

                                    Qwind_S = Qwind_S + shading_daily * \
                                        (window_configure["IA_window"] / 0.88) * \
                                        (solor_radiation["直達_入射角特性込"]["水平"]*0.89 + solor_radiation["天空"]["水平"]*0.808)

                                else:

                                    Qwind_S = Qwind_S + shading_daily * \
                                        (window_configure["IA_window"] / 0.88) * \
                                        (solor_radiation["直達_入射角特性込"][ wall_configure["Direction"] ]*0.89 + solor_radiation["天空"]["垂直"]*0.808)

                            else:

                                # 任意入力の場合（SP-8）
                                if wall_configure["Direction"] == "水平（上）" or wall_configure["Direction"] == "水平（下）":
                                    Qwind_S = Qwind_S +   \
                                        (window_configure["IA_window"]) * (solor_radiation["直達"]["水平"] + solor_radiation["天空"]["水平"])
                                else:
                                    Qwind_S = Qwind_S + shading_daily * \
                                        (window_configure["IA_window"]) * (solor_radiation["直達"][ wall_configure["Direction"] ] + solor_radiation["天空"]["垂直"])


                            ## ③ 夜間放射による熱取得（マイナス）
                            if wall_configure["Direction"] == "水平（上）" or wall_configure["Direction"] == "水平（下）":
                                Qwind_N = Qwind_N - window_configure["UA_window"] * 0.9 * 0.04 * solor_radiation["夜間"]["水平"]
                            else:
                                Qwind_N = Qwind_N - window_configure["UA_window"] * 0.9 * 0.04 * solor_radiation["夜間"]["垂直"]


                        elif wall_configure["WallType"] == "日の当たらない外壁":

                            ## ③ 夜間放射による熱取得（マイナス）
                            Qwind_N = Qwind_N - window_configure["UA_window"] * 0.9 * 0.04 * solor_radiation["夜間"]["水平"]




        # 保存 [Wh/m2日] （床面積あたり）
        resultJson["Qroom"][room_zone_name]["Qwall_T"] = Qwall_T / resultJson["Qroom"][room_zone_name]["perimeter_area"]
        resultJson["Qroom"][room_zone_name]["Qwall_S"] = Qwall_S / resultJson["Qroom"][room_zone_name]["perimeter_area"]
        resultJson["Qroom"][room_zone_name]["Qwall_N"] = Qwall_N / resultJson["Qroom"][room_zone_name]["perimeter_area"]
        resultJson["Qroom"][room_zone_name]["Qwind_T"] = Qwind_T / resultJson["Qroom"][room_zone_name]["perimeter_area"]
        resultJson["Qroom"][room_zone_name]["Qwind_S"] = Qwind_S / resultJson["Qroom"][room_zone_name]["perimeter_area"]
        resultJson["Qroom"][room_zone_name]["Qwind_N"] = Qwind_N / resultJson["Qroom"][room_zone_name]["perimeter_area"]



    ##----------------------------------------------------------------------------------
    ## 室負荷の計算（解説書 2.4.3、2.4.4）
    ##----------------------------------------------------------------------------------

    ## 室負荷計算のための係数（解説書 A.3）
    with open(database_directory + 'QROOM_COEFFI_AREA'+ inputdata["Building"]["Region"] +'.json', 'r', encoding='utf-8') as f:
        QROOM_COEFFI = json.load(f)


    for room_zone_name in inputdata["AirConditioningZone"]:

        Qroom_CTC = np.zeros(365)
        Qroom_CTH = np.zeros(365)
        Qroom_CSR = np.zeros(365)

        Qgain_internal = np.zeros(365)

        Qroom_c   = np.zeros(365)
        Qroom_h   = np.zeros(365)

        Qcool     = np.zeros(365)
        Qheat     = np.zeros(365)

        # 室が使用されているか否か＝空調運転時間（365日分）
        room_usage = np.sum(roomScheduleRoom[room_zone_name],1)

        btype = inputdata["AirConditioningZone"][room_zone_name]["buildingType"]
        rtype = inputdata["AirConditioningZone"][room_zone_name]["roomType"]

        # 発熱量参照値 [W/m2] を読み込む関数（空調）
        (roomHeatGain_Light, roomHeatGain_Person, roomHeatGain_OAapp, roomNumOfPerson) = \
                bc.get_roomHeatGain(btype, rtype)

        Heat_light_daily  = np.sum(roomScheduleLight[room_zone_name],1) * roomHeatGain_Light   # 照明からの発熱（日積算）（365日分）
        Heat_person_daily = np.sum(roomSchedulePerson[room_zone_name],1) * roomHeatGain_Person # 人体からの発熱（日積算）（365日分）
        Heat_OAapp_daily  = np.sum(roomScheduleOAapp[room_zone_name],1) * roomHeatGain_OAapp   # 機器からの発熱（日積算）（365日分）

        resultJson["Qroom"][room_zone_name]["Heat_light_daily"] = Heat_light_daily * resultJson["Qroom"][room_zone_name]["perimeter_area_for_internal_gain"]
        resultJson["Qroom"][room_zone_name]["Heat_person_daily"] = Heat_person_daily * resultJson["Qroom"][room_zone_name]["perimeter_area_for_internal_gain"]
        resultJson["Qroom"][room_zone_name]["Heat_OAapp_daily"] = Heat_OAapp_daily * resultJson["Qroom"][room_zone_name]["perimeter_area_for_internal_gain"]

        # 空調運転時間
        resultJson["Qroom"][room_zone_name]["AirConditioning_time"] = room_usage

        # 空調稼働時間帯
        resultJson["Qroom"][room_zone_name]["AirConditioning_daymode"] = roomDayMode[room_zone_name]

        # 外気エンタルピー
        if resultJson["Qroom"][room_zone_name]["AirConditioning_daymode"] == "終日":
            resultJson["Qroom"][room_zone_name]["Hoa"] = Hoa_ave
        elif resultJson["Qroom"][room_zone_name]["AirConditioning_daymode"] == "昼":
            resultJson["Qroom"][room_zone_name]["Hoa"] = Hoa_day
        elif resultJson["Qroom"][room_zone_name]["AirConditioning_daymode"] == "夜":
            resultJson["Qroom"][room_zone_name]["Hoa"] = Hoa_ngt

        # 各室の外気導入量 [m3/h]
        resultJson["Qroom"][room_zone_name]["OutdoorAirVolume"] = \
            bc.get_roomOutdoorAirVolume(btype, rtype) * resultJson["Qroom"][room_zone_name]["perimeter_area_for_internal_gain"]

        # 外気負荷 [Wh]
        resultJson["Qroom"][room_zone_name]["Qoa"] = \
            (resultJson["Qroom"][room_zone_name]["Hoa"] - Hroom) \
            * resultJson["Qroom"][room_zone_name]["OutdoorAirVolume"] *1.2/3600 \
            * resultJson["Qroom"][room_zone_name]["AirConditioning_time"] * 1000

        for dd in range(0,365):

            if room_usage[dd] > 0:

                # 前日の空調の有無
                if "終日空調" in QROOM_COEFFI[ btype ][ rtype ]:
                    onoff = "終日空調"
                elif (dd > 0) and (room_usage[dd-1] > 0):
                    onoff = "前日空調"
                else:
                    onoff = "前日休み"

                if ac_mode[dd] == "冷房":

                    Qroom_CTC[dd] = QROOM_COEFFI[ btype ][ rtype ][onoff]["冷房期"]["外気温変動"]["冷房負荷"]["係数"] * \
                        ( resultJson["Qroom"][room_zone_name]["Qwall_T"][dd] + resultJson["Qroom"][room_zone_name]["Qwall_N"][dd] + \
                        resultJson["Qroom"][room_zone_name]["Qwind_T"][dd] + resultJson["Qroom"][room_zone_name]["Qwind_N"][dd] ) + \
                        QROOM_COEFFI[ btype ][ rtype ][onoff]["冷房期"]["外気温変動"]["冷房負荷"]["補正切片"]

                    Qroom_CTH[dd] = QROOM_COEFFI[ btype ][ rtype ][onoff]["冷房期"]["外気温変動"]["暖房負荷"]["係数"] * \
                        ( resultJson["Qroom"][room_zone_name]["Qwall_T"][dd] + resultJson["Qroom"][room_zone_name]["Qwall_N"][dd] + \
                        resultJson["Qroom"][room_zone_name]["Qwind_T"][dd] + resultJson["Qroom"][room_zone_name]["Qwind_N"][dd] ) + \
                        QROOM_COEFFI[ btype ][ rtype ][onoff]["冷房期"]["外気温変動"]["暖房負荷"]["補正切片"]

                    Qroom_CSR[dd] = QROOM_COEFFI[ btype ][ rtype ][onoff]["冷房期"]["日射量変動"]["冷房負荷"]["係数"] * \
                        ( resultJson["Qroom"][room_zone_name]["Qwall_S"][dd] + resultJson["Qroom"][room_zone_name]["Qwind_S"][dd] ) + \
                        QROOM_COEFFI[ btype ][ rtype ][onoff]["冷房期"]["日射量変動"]["冷房負荷"]["切片"]

                elif ac_mode[dd] == "暖房":

                    Qroom_CTC[dd] = QROOM_COEFFI[ btype ][ rtype ][onoff]["暖房期"]["外気温変動"]["冷房負荷"]["係数"] * \
                        ( resultJson["Qroom"][room_zone_name]["Qwall_T"][dd] + resultJson["Qroom"][room_zone_name]["Qwall_N"][dd] + \
                        resultJson["Qroom"][room_zone_name]["Qwind_T"][dd] + resultJson["Qroom"][room_zone_name]["Qwind_N"][dd] ) + \
                        QROOM_COEFFI[ btype ][ rtype ][onoff]["暖房期"]["外気温変動"]["冷房負荷"]["切片"]

                    Qroom_CTH[dd] = QROOM_COEFFI[ btype ][ rtype ][onoff]["暖房期"]["外気温変動"]["暖房負荷"]["係数"] * \
                        ( resultJson["Qroom"][room_zone_name]["Qwall_T"][dd] + resultJson["Qroom"][room_zone_name]["Qwall_N"][dd] + \
                        resultJson["Qroom"][room_zone_name]["Qwind_T"][dd] + resultJson["Qroom"][room_zone_name]["Qwind_N"][dd] ) + \
                        QROOM_COEFFI[ btype ][ rtype ][onoff]["暖房期"]["外気温変動"]["暖房負荷"]["切片"]

                    Qroom_CSR[dd] = QROOM_COEFFI[ btype ][ rtype ][onoff]["暖房期"]["日射量変動"]["冷房負荷"]["係数"] * \
                        ( resultJson["Qroom"][room_zone_name]["Qwall_S"][dd] + resultJson["Qroom"][room_zone_name]["Qwind_S"][dd] ) + \
                        QROOM_COEFFI[ btype ][ rtype ][onoff]["暖房期"]["日射量変動"]["冷房負荷"]["切片"]
                        
                elif ac_mode[dd] == "中間":

                    Qroom_CTC[dd] = QROOM_COEFFI[ btype ][ rtype ][onoff]["中間期"]["外気温変動"]["冷房負荷"]["係数"] * \
                        ( resultJson["Qroom"][room_zone_name]["Qwall_T"][dd] + resultJson["Qroom"][room_zone_name]["Qwall_N"][dd] + \
                        resultJson["Qroom"][room_zone_name]["Qwind_T"][dd] + resultJson["Qroom"][room_zone_name]["Qwind_N"][dd] ) + \
                        QROOM_COEFFI[ btype ][ rtype ][onoff]["中間期"]["外気温変動"]["冷房負荷"]["補正切片"]

                    Qroom_CTH[dd] = QROOM_COEFFI[ btype ][ rtype ][onoff]["中間期"]["外気温変動"]["暖房負荷"]["係数"] * \
                        ( resultJson["Qroom"][room_zone_name]["Qwall_T"][dd] + resultJson["Qroom"][room_zone_name]["Qwall_N"][dd] + \
                        resultJson["Qroom"][room_zone_name]["Qwind_T"][dd] + resultJson["Qroom"][room_zone_name]["Qwind_N"][dd] ) + \
                        QROOM_COEFFI[ btype ][ rtype ][onoff]["中間期"]["外気温変動"]["暖房負荷"]["補正切片"]

                    Qroom_CSR[dd] = QROOM_COEFFI[ btype ][ rtype ][onoff]["中間期"]["日射量変動"]["冷房負荷"]["係数"] * \
                        ( resultJson["Qroom"][room_zone_name]["Qwall_S"][dd] + resultJson["Qroom"][room_zone_name]["Qwind_S"][dd] ) + \
                        QROOM_COEFFI[ btype ][ rtype ][onoff]["中間期"]["日射量変動"]["冷房負荷"]["切片"]

                if Qroom_CTC[dd] < 0:
                    Qroom_CTC[dd] = 0

                if Qroom_CTH[dd] > 0:
                    Qroom_CTH[dd] = 0

                if Qroom_CSR[dd] < 0:
                    Qroom_CSR[dd] = 0

                # 日射負荷 Qroom_CSR を暖房負荷 Qroom_CTH に足す
                Qcool[dd] = Qroom_CTC[dd]
                Qheat[dd] = Qroom_CTH[dd] + Qroom_CSR[dd]

                # 日射負荷によって暖房負荷がプラスになった場合は、超過分を冷房負荷に加算
                if Qheat[dd] > 0:
                    Qcool[dd] = Qcool[dd] + Qheat[dd]
                    Qheat[dd] = 0
                
                # [Wh]に変換
                Qcool[dd] = Qcool[dd] * resultJson["Qroom"][room_zone_name]["perimeter_area"]
                Qheat[dd] = Qheat[dd] * resultJson["Qroom"][room_zone_name]["perimeter_area"]

                Qgain_internal[dd] = \
                    resultJson["Qroom"][room_zone_name]["Heat_light_daily"][dd] + \
                    resultJson["Qroom"][room_zone_name]["Heat_person_daily"][dd] + \
                    resultJson["Qroom"][room_zone_name]["Heat_OAapp_daily"][dd]
                
                Qheat[dd] = Qheat[dd] + Qgain_internal[dd]

                # 内部発熱との相殺
                if Qheat[dd] > 0:
                    Qcool[dd] = Qcool[dd] + Qheat[dd]
                    Qheat[dd] = 0
            
                # 保存[Wh]
                Qroom_c[dd] = Qcool[dd]
                Qroom_h[dd] = Qheat[dd]

                # 外気負荷との相殺
                if resultJson["Qroom"][room_zone_name]["Qoa"][dd] > 0:  # 外気負荷が冷房負荷であれば

                    Qheat[dd] = Qheat[dd] + resultJson["Qroom"][room_zone_name]["Qoa"][dd]

                    if Qheat[dd] > 0:
                        Qcool[dd] = Qcool[dd] + Qheat[dd]
                        Qheat[dd] = 0

                elif resultJson["Qroom"][room_zone_name]["Qoa"][dd] <= 0:  # 外気負荷が暖房負荷であれば

                    Qcool[dd] = Qcool[dd] + resultJson["Qroom"][room_zone_name]["Qoa"][dd]

                    if Qcool[dd] < 0:
                        Qheat[dd] = Qcool[dd] + Qheat[dd]
                        Qcool[dd] = 0

            
            else:

                # 空調OFF時は 0 とする
                Qcool[dd] = 0
                Qheat[dd] = 0


        # 日積算熱取得  QroomDc, QroomDh [MJ/day]
        resultJson["Qroom"][room_zone_name]["QroomC"] = Qroom_c * (3600/1000000)
        resultJson["Qroom"][room_zone_name]["QroomH"] = Qroom_h * (3600/1000000)

        resultJson["Qroom"][room_zone_name]["QroomDc_Wh"] = Qcool
        resultJson["Qroom"][room_zone_name]["QroomDh_Wh"] = Qheat
        resultJson["Qroom"][room_zone_name]["QroomDc_MJ"] = Qcool * (3600/1000000)
        resultJson["Qroom"][room_zone_name]["QroomDh_MJ"] = Qheat * (3600/1000000)

    # PALの計算
    Qroom_c = 0
    Qroom_h = 0
    Aroom = 0
    Aroom2 = 0
    for room_zone_name in inputdata["AirConditioningZone"]:
        Qroom_c += abs( np.sum(resultJson["Qroom"][room_zone_name]["QroomDc_MJ"]) )
        Qroom_h += abs( np.sum(resultJson["Qroom"][room_zone_name]["QroomDh_MJ"]) )
        Aroom += resultJson["Qroom"][room_zone_name]["perimeter_area"]
        Aroom2 += resultJson["Qroom"][room_zone_name]["perimeter_area_for_internal_gain"]

    resultJson["PAL"] = (Qroom_c + Qroom_h)/(Aroom)
    resultJson["冷房負荷[MJ/年]"] = (Qroom_c)
    resultJson["暖房負荷[MJ/年]"] = (Qroom_h)
    resultJson["ペリメータ面積"] = (Aroom)
    resultJson["ペリメータ面積（発熱用）"] = (Aroom2)    

    return resultJson


if __name__ == '__main__':  # pragma: no cover


    number = '12'

    print('----- palstar.py -----')
    filename = './test_PAL/test_PAL_case'+number+'.json'

    # 入力ファイルの読み込み
    with open(filename, 'r', encoding='utf-8') as f:
        inputdata = json.load(f)

    resultJson = calc_palstar(inputdata, debug=True)

    print(f'PAL*: {resultJson["PAL"]}')
    print(f'冷房負荷: {resultJson["冷房負荷[MJ/年]"]}')
    print(f'暖房負荷: {resultJson["暖房負荷[MJ/年]"]}')
    print(f'ペリメータ面積: {resultJson["ペリメータ面積"]}')
    print(f'ペリメータ面積（発熱用）: {resultJson["ペリメータ面積（発熱用）"]}')

    with open("resultJson_PAL.json",'w', encoding='utf-8') as fw:
        json.dump(resultJson, fw, indent=4, ensure_ascii=False, cls = bc.MyEncoder)

    import csv

    csvdata = [[

        '室内温度 [℃]',
        '室内空気エンタルピー [kJ/kg]',
        '室外温度（日平均値） [℃]',
        '室外空気エンタルピー（空調時間帯平均） [kJ/kg]',

        '温度差による熱取得（壁） [Wh/day]',
        '日射による熱取得（壁）[Wh/day]',
        '夜間放射による熱取得（壁）[Wh/day]',
        '温度差による熱取得（窓） [Wh/day]',
        '日射による熱取得（窓）[Wh/day]',
        '夜間放射による熱取得（窓）[Wh/day]',

        '内部発熱による熱取得（照明） [Wh/day]',
        '内部発熱による熱取得（人体） [Wh/day]',
        '内部発熱による熱取得（機器） [Wh/day]',

        '空調運転時間 [時間/day]',
        '外気負荷 [Wh/day]',

        '室負荷（冷房） [Wh/day]',
        '室負荷（暖房） [Wh/day]',

        '日積算熱取得（冷房） [Wh/day]',
        '日積算熱取得（暖房） [Wh/day]',
        '日積算熱取得（冷房） [MJ/day]',
        '日積算熱取得（暖房） [MJ/day]',
        ]]
    
    for dd in range(365):
        csvdata.append([
                    resultJson["Qroom"]["1F_事務室"]["Troom"][dd],
                    resultJson["Qroom"]["1F_事務室"]["Hroom"][dd],
                    resultJson["Qroom"]["1F_事務室"]["Tout"][dd],
                    resultJson["Qroom"]["1F_事務室"]["Hoa"][dd],

                    resultJson["Qroom"]["1F_事務室"]["Qwall_T"][dd],
                    resultJson["Qroom"]["1F_事務室"]["Qwall_S"][dd],
                    resultJson["Qroom"]["1F_事務室"]["Qwall_N"][dd],
                    resultJson["Qroom"]["1F_事務室"]["Qwind_T"][dd],
                    resultJson["Qroom"]["1F_事務室"]["Qwind_S"][dd],
                    resultJson["Qroom"]["1F_事務室"]["Qwind_N"][dd],

                    resultJson["Qroom"]["1F_事務室"]["Heat_light_daily"][dd],
                    resultJson["Qroom"]["1F_事務室"]["Heat_person_daily"][dd],
                    resultJson["Qroom"]["1F_事務室"]["Heat_OAapp_daily"][dd],

                    resultJson["Qroom"]["1F_事務室"]["AirConditioning_time"][dd],
                    resultJson["Qroom"]["1F_事務室"]["Qoa"][dd],
                    
                    resultJson["Qroom"]["1F_事務室"]["QroomC"][dd],
                    resultJson["Qroom"]["1F_事務室"]["QroomH"][dd],

                    resultJson["Qroom"]["1F_事務室"]["QroomDc_Wh"][dd],
                    resultJson["Qroom"]["1F_事務室"]["QroomDh_Wh"][dd],
                    resultJson["Qroom"]["1F_事務室"]["QroomDc_MJ"][dd],
                    resultJson["Qroom"]["1F_事務室"]["QroomDh_MJ"][dd],

                    ])

    with open('./test_PAL/test_PAL_case' + number + '.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(csvdata)


