import json
import numpy as np
import math
import os
import copy
# import matplotlib.pyplot as plt

import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from . import commons as bc
from . import climate
from . import shading
# from . import make_figure as mf

# データベースファイルの保存場所
database_directory =  os.path.dirname(os.path.abspath(__file__)) + "/database/"
# 気象データファイルの保存場所
climatedata_directory =  os.path.dirname(os.path.abspath(__file__)) + "/climatedata/"

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
    x = math.floor(x*10)/10+0.05

    # 該当するマトリックスを探査
    while x > mxL[ix]:
        ix += 1

        if ix == len(mxL)-1:
            break

    return ix+1


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

def calc_energy(inputdata, debug = False):

    inputdata["PUMP"] = {}
    inputdata["REF"] = {}

    # 計算結果を格納する変数
    resultJson = {

        "設計一次エネルギー消費量[MJ/年]": 0,    # 空調設備の設計一次エネルギー消費量 [MJ/年]
        "基準一次エネルギー消費量[MJ/年]": 0,    # 空調設備の基準一次エネルギー消費量 [MJ/年]
        "設計一次エネルギー消費量[GJ/年]": 0,    # 空調設備の設計一次エネルギー消費量 [GJ/年]
        "基準一次エネルギー消費量[GJ/年]": 0,    # 空調設備の基準一次エネルギー消費量 [GJ/年]
        "設計一次エネルギー消費量[MJ/m2年]": 0,  # 空調設備の設計一次エネルギー消費量 [MJ/年]
        "基準一次エネルギー消費量[MJ/m2年]": 0,  # 空調設備の基準一次エネルギー消費量 [MJ/年]
        "計算対象面積": 0,
        "BEI/AC": 0,
        "Qroom": {
        },
        "AHU":{
        },
        "PUMP":{
        },
        "REF":{
        },
        "年間エネルギー消費量":{
            "空調機群ファン[MWh]": 0,     # 空調機群の一次エネルギー消費量 [MWh]
            "空調機群ファン[GJ]": 0,     # 空調機群の一次エネルギー消費量 [GJ]
            "空調機群全熱交換器[MWh]": 0,  # 全熱交換器の一次エネルギー消費量 [MWh]
            "空調機群全熱交換器[GJ]": 0,  # 全熱交換器の一次エネルギー消費量 [GJ]
            "二次ポンプ群[MWh]": 0,    # 二次ポンプ群の一次エネルギー消費量 [MWh]
            "二次ポンプ群[GJ]": 0,    # 二次ポンプ群の一次エネルギー消費量 [GJ]
            "熱源群熱源主機[MJ]": 0, # 熱源群主機の一次エネルギー消費量 [MJ]
            "熱源群熱源主機[GJ]": 0, # 熱源群主機の一次エネルギー消費量 [GJ]
            "熱源群熱源補機[MWh]": 0,   # 熱源群補機の一次エネルギー消費量 [MWh]
            "熱源群熱源補機[GJ]": 0,     # 熱源群補機の一次エネルギー消費量 [GJ]
            "熱源群一次ポンプ[MWh]": 0,   # 熱源群一次ポンプの一次エネルギー消費量 [MWh]
            "熱源群一次ポンプ[GJ]": 0,    # 熱源群一次ポンプの一次エネルギー消費量 [GJ]
            "熱源群冷却塔ファン[MWh]": 0,  # 熱源群冷却塔ファンの一次エネルギー消費量 [MWh]
            "熱源群冷却塔ファン[GJ]": 0,   # 熱源群冷却塔ファンの一次エネルギー消費量 [GJ]
            "熱源群冷却水ポンプ[MWh]": 0,  # 熱源群冷却水ポンプの一次エネルギー消費量 [MWh]
            "熱源群冷却水ポンプ[GJ]": 0,   # 熱源群冷却水ポンプの一次エネルギー消費量 [GJ]
        },
        "日別エネルギー消費量":{
            "E_fan_MWh_day": np.zeros(365),
            "E_pump_MWh_day": np.zeros(365),
            "E_ref_main_MWh_day": np.zeros(365),
            "E_ref_sub_MWh_day": np.zeros(365),
        },
        "Matrix":{
        },
        "for_CGS":{
        }
    }

    ##----------------------------------------------------------------------------------
    ## 定数の設定
    ##----------------------------------------------------------------------------------
    k_heatup = 0.84       # ファン・ポンプの発熱比率
    Cw = 4.186            # 水の比熱 [kJ/kg・K]
    divL = 11             # 負荷帯マトリックス分割数 （10区分＋過負荷1区分）
    divT =  6             # 外気温度帯マトリックス分割数


    ##----------------------------------------------------------------------------------
    ## データベースファイルの読み込み
    ##----------------------------------------------------------------------------------

    # 流量制御
    with open(database_directory + 'FLOWCONTROL.json', 'r', encoding='utf-8') as f:
        FLOWCONTROL = json.load(f)

    # 熱源機器特性
    with open(database_directory + "HeatSourcePerformance.json", 'r', encoding='utf-8') as f:
        HeatSourcePerformance = json.load(f)

    ##----------------------------------------------------------------------------------
    ## 任意評定 （SP-1: 流量制御)
    ##----------------------------------------------------------------------------------

    # 任意評定用の入力があれば追加
    if "SpecialInputData" in inputdata:
        if "flow_control" in inputdata["SpecialInputData"]:
            FLOWCONTROL.update(inputdata["SpecialInputData"]["flow_control"])

    ##----------------------------------------------------------------------------------
    ## 任意評定 （SP-2：　熱源機器特性)
    ##----------------------------------------------------------------------------------

    # 任意評定用の入力があれば追加
    if "SpecialInputData" in inputdata:
        if "heatsource_performance" in inputdata["SpecialInputData"]:
            HeatSourcePerformance.update(inputdata["SpecialInputData"]["heatsource_performance"])


    ##----------------------------------------------------------------------------------
    ## マトリックスの設定
    ##----------------------------------------------------------------------------------

    # 地域別データの読み込み
    with open(database_directory + 'AREA.json', 'r', encoding='utf-8') as f:
        Area = json.load(f)

    # 負荷率帯マトリックス mxL = array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.2])
    mxL = np.arange(1/(divL-1), 1.01, 1/(divL-1))
    mxL = np.append(mxL,1.2)

    # 負荷率帯マトリックス（平均） aveL = array([0.05, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.95, 1.2 ])
    aveL = np.zeros(len(mxL))
    for iL in range(0,len(mxL)):
        if iL == 0:
            aveL[0] = mxL[0]/2
        elif iL == len(mxL)-1:
            aveL[iL] = 1.2
        else:
            aveL[iL] = mxL[iL-1] + (mxL[iL]-mxL[iL-1])/2

    ##----------------------------------------------------------------------------------
    ## 日平均外気温 （解説書 2.7.4.1）
    ##----------------------------------------------------------------------------------

    # 外気温度帯の上限・下限
    mxTH_min = Area[inputdata["Building"]["Region"]+"地域"]["暖房時外気温下限"]
    mxTH_max = Area[inputdata["Building"]["Region"]+"地域"]["暖房時外気温上限"]
    mxTC_min = Area[inputdata["Building"]["Region"]+"地域"]["冷房時外気温下限"]
    mxTC_max = Area[inputdata["Building"]["Region"]+"地域"]["冷房時外気温上限"]

    delTC = (mxTC_max - mxTC_min)/divT
    delTH = (mxTH_max - mxTH_min)/divT

    mxTC = np.arange(mxTC_min+delTC, mxTC_max+delTC, delTC)
    mxTH = np.arange(mxTH_min+delTH, mxTH_max+delTH, delTH)

    ToadbC = mxTC - delTC/2
    ToadbH = mxTH - delTH/2

    # 保存用
    resultJson["Matrix"]["ToadbC"] = ToadbC
    resultJson["Matrix"]["ToadbH"] = ToadbH

    ##----------------------------------------------------------------------------------
    ## 他人から供給された熱の一次エネルギー換算係数（デフォルト）
    ##----------------------------------------------------------------------------------

    if inputdata["Building"]["Coefficient_DHC"]["Cooling"] == None:
        inputdata["Building"]["Coefficient_DHC"]["Cooling"] = 1.36

    if inputdata["Building"]["Coefficient_DHC"]["Heating"] == None:
        inputdata["Building"]["Coefficient_DHC"]["Heating"] = 1.36


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
            climate.readHaspClimateData( climatedata_directory + "/C1_" + Area[inputdata["Building"]["Region"]+"地域"]["気象データファイル名"] )

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
    ## 任意評定 （SP-6: カレンダーパターン)
    ##----------------------------------------------------------------------------------
    input_calendar = []
    if "calender" in inputdata["SpecialInputData"]:
        input_calendar = inputdata["SpecialInputData"]["calender"]


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
            bc.get_roomUsageSchedule(inputdata["AirConditioningZone"][room_zone_name]["buildingType"], inputdata["AirConditioningZone"][room_zone_name]["roomType"], input_calendar)


        # 空調対象面積の合計
        roomAreaTotal += inputdata["AirConditioningZone"][room_zone_name]["zoneArea"]


    ##----------------------------------------------------------------------------------
    ## 任意評定 （SP-7: 室スケジュール)
    ##----------------------------------------------------------------------------------

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


    #%%
    ##----------------------------------------------------------------------------------
    ## 室負荷計算（解説書 2.4）
    ##----------------------------------------------------------------------------------

    for room_zone_name in inputdata["AirConditioningZone"]:

        resultJson["Qroom"][room_zone_name] = {
            "Qwall_T": np.zeros(365),  # 壁からの温度差による熱取得 [W/m2]
            "Qwall_S": np.zeros(365),  # 壁からの日射による熱取得 [W/m2]
            "Qwall_N": np.zeros(365),  # 壁からの夜間放射による熱取得（マイナス）[W/m2]
            "Qwind_T": np.zeros(365),  # 窓からの温度差による熱取得 [W/m2]
            "Qwind_S": np.zeros(365),  # 窓からの日射による熱取得 [W/m2]
            "Qwind_N": np.zeros(365),  # 窓からの夜間放射による熱取得（マイナス）[W/m2]
            "QroomDc": np.zeros(365),  # 冷房熱取得（日積算）　[MJ/day]
            "QroomDh": np.zeros(365),   # 暖房熱取得（日積算）　[MJ/day]
            "QroomHc": np.zeros((365,24)),  # 冷房熱取得（時刻別）　[MJ/h]
            "QroomHh": np.zeros((365,24))   # 暖房熱取得（時刻別）　[MJ/h]
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




    if debug: # pragma: no cover

        for room_zone_name in inputdata["AirConditioningZone"]:

            print( f'--- ゾーン名 {room_zone_name} ---')

            print( f'熱取得_壁温度 Qwall_T: {np.sum(resultJson["Qroom"][room_zone_name]["Qwall_T"],0)}' )
            print( f'熱取得_壁日射 Qwall_S: {np.sum(resultJson["Qroom"][room_zone_name]["Qwall_S"],0)}' )
            print( f'熱取得_壁放射 Qwall_N: {np.sum(resultJson["Qroom"][room_zone_name]["Qwall_N"],0)}' )
            print( f'熱取得_窓温度 Qwind_T: {np.sum(resultJson["Qroom"][room_zone_name]["Qwind_T"],0)}' )
            print( f'熱取得_窓日射 Qwind_S: {np.sum(resultJson["Qroom"][room_zone_name]["Qwind_S"],0)}' )
            print( f'熱取得_窓放射 Qwind_N: {np.sum(resultJson["Qroom"][room_zone_name]["Qwind_N"],0)}' )


    ##----------------------------------------------------------------------------------
    ## 任意評定用　室負荷（ SP-4 ）
    ##----------------------------------------------------------------------------------

    if "SpecialInputData" in inputdata:
        if "Qroom" in inputdata["SpecialInputData"]:

            for room_zone_name in inputdata["SpecialInputData"]["Qroom"]: # SP-4シートに入力された室毎に処理

                if room_zone_name in resultJson["Qroom"]:  # SP-4シートに入力された室が空調ゾーンとして存在していれば
                    # 室負荷（冷房要求）の置き換え [MJ/day]
                    if "QroomDc" in inputdata["SpecialInputData"]["Qroom"][room_zone_name]:
                        resultJson["Qroom"][room_zone_name]["QroomDc"] = inputdata["SpecialInputData"]["Qroom"][room_zone_name]["QroomDc"]

                    # 室負荷（暖房要求）の置き換え
                    if "QroomDh" in inputdata["SpecialInputData"]["Qroom"][room_zone_name]:
                        resultJson["Qroom"][room_zone_name]["QroomDh"] = inputdata["SpecialInputData"]["Qroom"][room_zone_name]["QroomDh"]


    ##----------------------------------------------------------------------------------
    # 時刻別熱取得 [MJ/hour]
    ##----------------------------------------------------------------------------------
    for room_zone_name in inputdata["AirConditioningZone"]:

        for dd in range(0,365):

            # 日別の運転時間 [h]
            daily_opetime = sum(roomScheduleRoom[room_zone_name][dd])

            for hh in range(0,24):
                if roomScheduleRoom[room_zone_name][dd][hh] > 0:
                    # 冷房熱取得
                    resultJson["Qroom"][room_zone_name]["QroomHc"][dd][hh] = resultJson["Qroom"][room_zone_name]["QroomDc"][dd] / daily_opetime
                    # 暖房熱取得
                    resultJson["Qroom"][room_zone_name]["QroomHh"][dd][hh] = resultJson["Qroom"][room_zone_name]["QroomDh"][dd] / daily_opetime


    ##----------------------------------------------------------------------------------
    ## 動的室負荷計算
    ##----------------------------------------------------------------------------------
    if False:

        # 負荷計算モジュールの読み込み
        from .heat_load_calculation import Main
        import copy

        # ファイルの読み込み
        with open('./builelib/heat_load_calculation/heatload_calculation_template.json', 'r', encoding='utf-8') as js:
        # with open('input_non_residential.json', 'r', encoding='utf-8') as js:
            input_heatcalc_template = json.load(js)

        ## 入力ファイルの生成（共通）
        # 地域
        input_heatcalc_template["common"]["region"] = inputdata["Building"]["Region"]
        input_heatcalc_template["common"]["is_residential"] = False

        # 室温上限値・下限
        input_heatcalc_template["rooms"][0]["schedule"]["temperature_upper_limit"] = np.reshape(TroomSP*np.ones([24,1]),8760)
        input_heatcalc_template["rooms"][0]["schedule"]["temperature_lower_limit"] = np.reshape(TroomSP*np.ones([24,1]),8760)

        # 相対湿度上限値・下限
        input_heatcalc_template["rooms"][0]["schedule"]["relative_humidity_upper_limit"] = np.reshape(RroomSP*np.ones([24,1]),8760)
        input_heatcalc_template["rooms"][0]["schedule"]["relative_humidity_lower_limit"] = np.reshape(RroomSP*np.ones([24,1]),8760)

        # 非住宅では使わない
        input_heatcalc_template["rooms"][0]["vent"] = 0
        input_heatcalc_template["rooms"][0]["schedule"]["heat_generation_cooking"] = np.zeros(8760)
        input_heatcalc_template["rooms"][0]["schedule"]["vapor_generation_cooking"] = np.zeros(8760)
        input_heatcalc_template["rooms"][0]["schedule"]["local_vent_amount"] = np.zeros(8760)

        # 空調ゾーン毎に負荷を計算
        for room_zone_name in inputdata["AirConditioningZone"]:

            # 入力ファイルの読み込み
            input_heatcalc = copy.deepcopy(input_heatcalc_template)

            ## 入力ファイルの生成（室単位）

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
            input_heatcalc["rooms"][0]["schedule"]["heat_generation_lighting"] = np.reshape(Heat_light_hourly[room_zone_name],8760) * inputdata["AirConditioningZone"][room_zone_name]["zoneArea"]
            # 機器発熱スケジュール[W]
            input_heatcalc["rooms"][0]["schedule"]["heat_generation_appliances"] = np.reshape(Heat_OAapp_hourly[room_zone_name],8760) * inputdata["AirConditioningZone"][room_zone_name]["zoneArea"]
            # 人員数[人]
            input_heatcalc["rooms"][0]["schedule"]["number_of_people"] = np.reshape(Num_of_Person_hourly[room_zone_name],8760) * inputdata["AirConditioningZone"][room_zone_name]["zoneArea"]


            # 床の設定
            input_heatcalc["rooms"][0]["boundaries"][0] = {
                "name" : 'floor',
                "boundary_type" : 'external_general_part',
                "area": inputdata["AirConditioningZone"][room_zone_name]["zoneArea"],
                "is_sun_striked_outside": False,
                "temp_dif_coef": 0,
                "is_solar_absorbed_inside": True,
                "general_part_spec" :
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
                            "existence" : False
                        },
                    }
            }

            # 天井
            input_heatcalc["rooms"][0]["boundaries"][1] = {
                "name" : 'ceil',
                "boundary_type" : 'external_general_part',
                "area": inputdata["AirConditioningZone"][room_zone_name]["zoneArea"],
                "is_sun_striked_outside": False,
                "temp_dif_coef": 0,
                "is_solar_absorbed_inside": True,
                "general_part_spec" :
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
                            "existence" : False
                        },
                    }
            }

            # 外皮があれば
            if room_zone_name in inputdata["EnvelopeSet"]:

                # 外壁
                for (wall_id, wall_configure) in enumerate( inputdata["EnvelopeSet"][room_zone_name]["WallList"]):

                    # 等価R値
                    if inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["U_wall"] > 4:
                        equivalent_Rvalue = 0.001
                    else:
                        equivalent_Rvalue = (1/inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["U_wall"] - 0.25)

                    direction = ""
                    if inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["Direction"] ==  "北":
                        direction = "n"
                    elif inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["Direction"] ==  "北東":
                        direction = "ne"
                    elif inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["Direction"] ==  "東":
                        direction = "e"
                    elif inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["Direction"] ==  "南東":
                        direction = "se"
                    elif inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["Direction"] ==  "南":
                        direction = "s"
                    elif inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["Direction"] ==  "南西":
                        direction = "sw"
                    elif inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["Direction"] ==  "西":
                        direction = "w"
                    elif inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["Direction"] ==  "北西":
                        direction = "nw"
                    elif inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["Direction"] ==  "水平（上）":
                        direction = "top"
                    elif inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["Direction"] ==  "水平（下）":
                        direction = "bottom"
                    else:
                        raise Exception("方位が不正です")

                    boundary_type  = ""
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
                                "general_part_spec" :
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
                                    "existence" : False
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
                                "ground_spec" :
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
                    for (window_id, window_configure) in enumerate( inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WindowList"]):

                        if window_configure["WindowID"] != "無":

                            input_heatcalc["rooms"][0]["boundaries"].append(
                                {
                                    "name": "window",
                                    "boundary_type": "external_transparent_part",
                                    "area": inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WindowList"][window_id]["windowArea"] ,
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
            heatload_sensible_convection, heatload_sensible_radiation, heatload_latent = Main.run(input_heatcalc)

            # 負荷の積算（全熱負荷）[W] (365×24)
            heatload = np.array(
                    bc.trans_8760to36524(heatload_sensible_convection) + \
                    bc.trans_8760to36524(heatload_sensible_radiation) + \
                    bc.trans_8760to36524(heatload_latent)
                )

            # 冷房負荷と暖房負荷に分離する。
            resultJson["Qroom"][room_zone_name]["QroomDc"] = np.zeros(365)
            resultJson["Qroom"][room_zone_name]["QroomDh"] = np.zeros(365)
            resultJson["Qroom"][room_zone_name]["QroomHc"] = np.zeros((365,24))
            resultJson["Qroom"][room_zone_name]["QroomHh"] = np.zeros((365,24))

            for dd in range(0,365):
                for hh in range(0,24):

                    if heatload[dd][hh] > 0:
                        # 暖房負荷 [W] → [MJ/hour]
                        resultJson["Qroom"][room_zone_name]["QroomHh"][dd][hh] = (-1) * heatload[dd][hh] * 3600/1000000
                        # 暖房負荷 [W] → [MJ/day]
                        resultJson["Qroom"][room_zone_name]["QroomDh"][dd] += (-1) * heatload[dd][hh] * 3600/1000000

                    elif heatload[dd][hh] < 0:
                        # 冷房負荷 [W] → [MJ/hour]
                        resultJson["Qroom"][room_zone_name]["QroomHc"][dd][hh] = (-1) * heatload[dd][hh] * 3600/1000000
                        # 冷房負荷 [W]→ [MJ/day]
                        resultJson["Qroom"][room_zone_name]["QroomDc"][dd] += (-1) * heatload[dd][hh] * 3600/1000000


            print( f'室負荷（冷房要求）の合計 heatload_for_cooling: {np.sum(resultJson["Qroom"][room_zone_name]["QroomDc"],0)}' )
            print( f'室負荷（暖房要求）の合計 heatload_for_heating: {np.sum(resultJson["Qroom"][room_zone_name]["QroomDh"],0)}' )



    ##----------------------------------------------------------------------------------
    ## 負荷計算結果の集約
    ##----------------------------------------------------------------------------------
    for room_zone_name in inputdata["AirConditioningZone"]:

        # 結果の集約 [MJ/年]
        resultJson["Qroom"][room_zone_name]["建物用途"] = inputdata["AirConditioningZone"][room_zone_name]["buildingType"]
        resultJson["Qroom"][room_zone_name]["室用途"] = inputdata["AirConditioningZone"][room_zone_name]["roomType"]
        resultJson["Qroom"][room_zone_name]["床面積"] = inputdata["AirConditioningZone"][room_zone_name]["zoneArea"]
        resultJson["Qroom"][room_zone_name]["年間空調時間"] = np.sum( np.sum( roomScheduleRoom[room_zone_name] ))

        resultJson["Qroom"][room_zone_name]["年間室負荷（冷房）[MJ]"] = np.sum(resultJson["Qroom"][room_zone_name]["QroomDc"])
        resultJson["Qroom"][room_zone_name]["年間室負荷（暖房）[MJ]"] = np.sum(resultJson["Qroom"][room_zone_name]["QroomDh"])
        resultJson["Qroom"][room_zone_name]["平均室負荷（冷房）[W/m2]"] = \
            resultJson["Qroom"][room_zone_name]["年間室負荷（冷房）[MJ]"] *1000000 \
            / (resultJson["Qroom"][room_zone_name]["年間空調時間"]*3600) \
            / resultJson["Qroom"][room_zone_name]["床面積"]
        resultJson["Qroom"][room_zone_name]["平均室負荷（暖房）[W/m2]"] = \
            resultJson["Qroom"][room_zone_name]["年間室負荷（暖房）[MJ]"] *1000000 \
            / (resultJson["Qroom"][room_zone_name]["年間空調時間"]*3600) \
            / resultJson["Qroom"][room_zone_name]["床面積"]

    if debug: # pragma: no cover
        for room_zone_name in inputdata["AirConditioningZone"]:
            print( f'--- ゾーン名 {room_zone_name} ---')
            print( f'年間室負荷（冷房要求） QroomDc: {resultJson["Qroom"][room_zone_name]["年間室負荷（冷房）[MJ]"]}' )
            print( f'年間室負荷（暖房要求） QroomDh: {resultJson["Qroom"][room_zone_name]["年間室負荷（暖房）[MJ]"]}' )


    # 熱負荷のグラフ化（確認用）
    # for room_zone_name in inputdata["AirConditioningZone"]:

    #     mf.hourlyplot(resultJson["Qroom"][room_zone_name]["QroomHc"], "室負荷（冷房）："+room_zone_name, "b", "室負荷（冷房）")
    #     mf.hourlyplot(resultJson["Qroom"][room_zone_name]["QroomHh"], "室負荷（暖房）："+room_zone_name, "m", "室負荷（暖房）")

    # plt.show()

    print('室負荷計算完了')


    ##----------------------------------------------------------------------------------
    ## 空調機群の一次エネルギー消費量（解説書 2.5）
    ##----------------------------------------------------------------------------------

    ## 結果格納用の変数
    for ahu_name in inputdata["AirHandlingSystem"]:

        resultJson["AHU"][ahu_name] = {

            "day_mode": [],                    # 空調機群の運転時間帯（昼、夜、終日）
            "schedule": np.zeros((365,24)),    # 時刻別の運転スケジュール（365×24）
            "HoaDayAve": np.zeros(365),        # 空調運転時間帯の外気エンタルピー

            "qoaAHU": np.zeros(365),           # 日平均外気負荷 [kW]
            "Tahu_total": np.zeros(365),       # 空調機群の日積算運転時間（冷暖合計）

            "E_fan_day": np.zeros(365),        # 空調機群のエネルギー消費量
            "E_fan_c_day": np.zeros(365),      # 空調機群のエネルギー消費量（冷房）
            "E_fan_h_day": np.zeros(365),      # 空調機群のエネルギー消費量（暖房）
            "E_AHUaex_day": np.zeros(365),     # 全熱交換器のエネルギー消費量

            "TdAHUc_total": np.zeros(365),     # 空調機群の冷房運転時間の合計
            "TdAHUh_total": np.zeros(365),     # 空調機群の暖房運転時間の合計

            "Qahu_remainC": np.zeros(365),     # 空調機群の未処理負荷（冷房）[MJ/day]
            "Qahu_remainH": np.zeros(365),     # 空調機群の未処理負荷（暖房）[MJ/day]

            "energy_consumption_each_LF": np.zeros(len(aveL)),

            "Qroom" :{
                "cooling_for_room" : np.zeros(365),   # 日積算室負荷（冷房要求）の積算値 [MJ/day]
                "heating_for_room" : np.zeros(365),   # 日積算室負荷（暖房要求）の積算値 [MJ/day]
            },
            "Qahu" :{
                "cooling_for_room" : np.zeros(365),   # 室負荷が正（冷房要求）であるときの空調負荷（正であれば冷却コイル負荷、負であれば加熱コイル負荷） [MJ/day]
                "heating_for_room" : np.zeros(365),   # 室負荷が負（暖房要求）であるときの空調負荷（正であれば冷却コイル負荷、負であれば加熱コイル負荷） [MJ/day]
            },
            "Tahu" :{
                "cooling_for_room" : np.zeros(365),   # 室負荷が冷房要求である場合の空調機群の運転時間 [h/day]
                "heating_for_room" : np.zeros(365),   # 室負荷が暖房要求である場合の空調機群の運転時間 [h/day]
            },

            "Economizer":{
                "AHUVovc" : np.zeros(365),   # 外気冷房運転時の外気風量 [kg/s]
                "Qahu_oac": np.zeros(365),   # 外気冷房による負荷削減効果 [MJ/day]
            },

            "LdAHUc": {
                "cooling_for_room" : np.zeros(365), # 空調機群の冷房運転時の負荷率帯（室負荷が冷房要求である場合）
                "heating_for_room" : np.zeros(365), # 空調機群の冷房運転時の負荷率帯（室負荷が暖房要求である場合）
            },
            "TdAHUc": {
                "cooling_for_room" : np.zeros(365), # 空調機群の冷房運転時間（室負荷が冷房要求である場合）
                "heating_for_room" : np.zeros(365), # 空調機群の冷房運転時間（室負荷が冷房要求である場合）
            },
            "LdAHUh": {
                "cooling_for_room" : np.zeros(365), # 空調機群の暖房負荷率帯（室負荷が冷房要求である場合）
                "heating_for_room" : np.zeros(365), # 空調機群の暖房負荷率帯（室負荷が冷房要求である場合）
            },
            "TdAHUh": {
                "cooling_for_room" : np.zeros(365), # 空調機群の暖房運転時間（室負荷が冷房要求である場合）
                "heating_for_room" : np.zeros(365), # 空調機群の暖房運転時間（室負荷が冷房要求である場合）
            },

            "TcAHU": 0,
            "ThAHU": 0,
            "MxAHUcE": 0,
            "MxAHUhE": 0
        }


    ##----------------------------------------------------------------------------------
    ## 空調機群全体のスペックを整理
    ##----------------------------------------------------------------------------------

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
            if (unit_configure["AirHeatExchangeRatioCooling"] != None):
                if inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioCooling"] == None:
                    inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioCooling"] = unit_configure["AirHeatExchangeRatioCooling"]
                elif inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioCooling"] > unit_configure["AirHeatExchangeRatioCooling"]:
                    inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioCooling"] = unit_configure["AirHeatExchangeRatioCooling"]

            # 暖房の効率
            if (unit_configure["AirHeatExchangeRatioHeating"] != None):
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
                inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangerAirVolume"]  += \
                    unit_configure["FanAirVolume"] * unit_configure["Number"]


    ##----------------------------------------------------------------------------------
    ## 二次ポンプ群の一次エネルギー消費量（解説書 2.6）
    ##----------------------------------------------------------------------------------

    # 二次ポンプが空欄であった場合、ダミーの仮想ポンプを追加する。
    number = 0
    for ahu_name in inputdata["AirHandlingSystem"]:

        if inputdata["AirHandlingSystem"][ahu_name]["Pump_cooling"] == None:

            inputdata["AirHandlingSystem"][ahu_name]["Pump_cooling"] = "dummyPump_" + str(number)

            inputdata["SecondaryPumpSystem"][ "dummyPump_" + str(number) ] = {
                "冷房":{
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

            inputdata["SecondaryPumpSystem"][ "dummyPump_" + str(number) ] = {
                "暖房":{
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


    ##----------------------------------------------------------------------------------
    ## 冷暖同時供給の有無の判定
    ##----------------------------------------------------------------------------------

    for ahu_name in inputdata["AirHandlingSystem"]:
        inputdata["AirHandlingSystem"][ ahu_name ]["isSimultaneousSupply"] = "無"
        inputdata["AirHandlingSystem"][ ahu_name ]["isSimultaneousSupply_cooling"] = "無"
        inputdata["AirHandlingSystem"][ ahu_name ]["isSimultaneousSupply_heating"] = "無"
    for pump_name in inputdata["SecondaryPumpSystem"]:
        inputdata["SecondaryPumpSystem"][ pump_name ]["isSimultaneousSupply"] = "無"
    for ref_name in inputdata["HeatsourceSystem"]:
        inputdata["HeatsourceSystem"][ ref_name ]["isSimultaneousSupply"] = "無"

    for room_zone_name in inputdata["AirConditioningZone"]:

        if inputdata["AirConditioningZone"][room_zone_name]["isSimultaneousSupply"] == "有":

            # 空調機群
            inputdata["AirHandlingSystem"][ inputdata["AirConditioningZone"][room_zone_name]["AHU_cooling_insideLoad"] ]["isSimultaneousSupply_cooling"] = "有"
            inputdata["AirHandlingSystem"][ inputdata["AirConditioningZone"][room_zone_name]["AHU_cooling_outdoorLoad"]]["isSimultaneousSupply_cooling"] = "有"
            inputdata["AirHandlingSystem"][ inputdata["AirConditioningZone"][room_zone_name]["AHU_heating_insideLoad"] ]["isSimultaneousSupply_heating"] = "有"
            inputdata["AirHandlingSystem"][ inputdata["AirConditioningZone"][room_zone_name]["AHU_heating_outdoorLoad"]]["isSimultaneousSupply_heating"] = "有"

            # 熱源群
            id_ref_c1 = inputdata["AirHandlingSystem"][ inputdata["AirConditioningZone"][room_zone_name]["AHU_cooling_insideLoad"]  ]["HeatSource_cooling"]
            id_ref_c2 = inputdata["AirHandlingSystem"][ inputdata["AirConditioningZone"][room_zone_name]["AHU_cooling_outdoorLoad"] ]["HeatSource_cooling"]
            id_ref_h1 = inputdata["AirHandlingSystem"][ inputdata["AirConditioningZone"][room_zone_name]["AHU_heating_insideLoad"]  ]["HeatSource_heating"]
            id_ref_h2 = inputdata["AirHandlingSystem"][ inputdata["AirConditioningZone"][room_zone_name]["AHU_heating_outdoorLoad"] ]["HeatSource_heating"]

            inputdata["HeatsourceSystem"][ id_ref_c1 ]["isSimultaneousSupply"] = "有"
            inputdata["HeatsourceSystem"][ id_ref_c2 ]["isSimultaneousSupply"] = "有"
            inputdata["HeatsourceSystem"][ id_ref_h1 ]["isSimultaneousSupply"] = "有"
            inputdata["HeatsourceSystem"][ id_ref_h2 ]["isSimultaneousSupply"] = "有"

            # 二次ポンプ群
            id_pump_c1 = inputdata["AirHandlingSystem"][ inputdata["AirConditioningZone"][room_zone_name]["AHU_cooling_insideLoad"]  ]["Pump_cooling"]
            id_pump_c2 = inputdata["AirHandlingSystem"][ inputdata["AirConditioningZone"][room_zone_name]["AHU_cooling_outdoorLoad"] ]["Pump_cooling"]
            id_pump_h1 = inputdata["AirHandlingSystem"][ inputdata["AirConditioningZone"][room_zone_name]["AHU_heating_insideLoad"]  ]["Pump_heating"]
            id_pump_h2 = inputdata["AirHandlingSystem"][ inputdata["AirConditioningZone"][room_zone_name]["AHU_heating_outdoorLoad"] ]["Pump_heating"]

            inputdata["SecondaryPumpSystem"][ id_pump_c1 ]["isSimultaneousSupply"] = "有"
            inputdata["SecondaryPumpSystem"][ id_pump_c2 ]["isSimultaneousSupply"] = "有"
            inputdata["SecondaryPumpSystem"][ id_pump_h1 ]["isSimultaneousSupply"] = "有"
            inputdata["SecondaryPumpSystem"][ id_pump_h2 ]["isSimultaneousSupply"] = "有"

        elif inputdata["AirConditioningZone"][room_zone_name]["isSimultaneousSupply"] == "有（室負荷）":

            # 空調機群
            inputdata["AirHandlingSystem"][ inputdata["AirConditioningZone"][room_zone_name]["AHU_cooling_insideLoad"] ]["isSimultaneousSupply_cooling"] = "有"
            inputdata["AirHandlingSystem"][ inputdata["AirConditioningZone"][room_zone_name]["AHU_heating_insideLoad"] ]["isSimultaneousSupply_heating"] = "有"

            # 熱源群
            id_ref_c1 = inputdata["AirHandlingSystem"][ inputdata["AirConditioningZone"][room_zone_name]["AHU_cooling_insideLoad"]  ]["HeatSource_cooling"]
            id_ref_h1 = inputdata["AirHandlingSystem"][ inputdata["AirConditioningZone"][room_zone_name]["AHU_heating_insideLoad"]  ]["HeatSource_heating"]

            inputdata["HeatsourceSystem"][ id_ref_c1 ]["isSimultaneousSupply"] = "有"
            inputdata["HeatsourceSystem"][ id_ref_h1 ]["isSimultaneousSupply"] = "有"

            # 二次ポンプ群
            id_pump_c1 = inputdata["AirHandlingSystem"][ inputdata["AirConditioningZone"][room_zone_name]["AHU_cooling_insideLoad"]  ]["Pump_cooling"]
            id_pump_h1 = inputdata["AirHandlingSystem"][ inputdata["AirConditioningZone"][room_zone_name]["AHU_heating_insideLoad"]  ]["Pump_heating"]

            inputdata["SecondaryPumpSystem"][ id_pump_c1 ]["isSimultaneousSupply"] = "有"
            inputdata["SecondaryPumpSystem"][ id_pump_h1 ]["isSimultaneousSupply"] = "有"

        elif inputdata["AirConditioningZone"][room_zone_name]["isSimultaneousSupply"] == "有（外気負荷）":

            # 空調機群
            inputdata["AirHandlingSystem"][ inputdata["AirConditioningZone"][room_zone_name]["AHU_cooling_outdoorLoad"]]["isSimultaneousSupply_cooling"] = "有"
            inputdata["AirHandlingSystem"][ inputdata["AirConditioningZone"][room_zone_name]["AHU_heating_outdoorLoad"]]["isSimultaneousSupply_heating"] = "有"

            # 熱源群
            id_ref_c2 = inputdata["AirHandlingSystem"][ inputdata["AirConditioningZone"][room_zone_name]["AHU_cooling_outdoorLoad"] ]["HeatSource_cooling"]
            id_ref_h2 = inputdata["AirHandlingSystem"][ inputdata["AirConditioningZone"][room_zone_name]["AHU_heating_outdoorLoad"] ]["HeatSource_heating"]

            inputdata["HeatsourceSystem"][ id_ref_c2 ]["isSimultaneousSupply"] = "有"
            inputdata["HeatsourceSystem"][ id_ref_h2 ]["isSimultaneousSupply"] = "有"

            # 二次ポンプ群
            id_pump_c2 = inputdata["AirHandlingSystem"][ inputdata["AirConditioningZone"][room_zone_name]["AHU_cooling_outdoorLoad"] ]["Pump_cooling"]
            id_pump_h2 = inputdata["AirHandlingSystem"][ inputdata["AirConditioningZone"][room_zone_name]["AHU_heating_outdoorLoad"] ]["Pump_heating"]

            inputdata["SecondaryPumpSystem"][ id_pump_c2 ]["isSimultaneousSupply"] = "有"
            inputdata["SecondaryPumpSystem"][ id_pump_h2 ]["isSimultaneousSupply"] = "有"

    # 両方とも冷暖同時なら、その空調機群は冷暖同時運転可能とする。
    for ahu_name in inputdata["AirHandlingSystem"]:

        if (inputdata["AirHandlingSystem"][ ahu_name ]["isSimultaneousSupply_cooling"] == "有") and \
            (inputdata["AirHandlingSystem"][ ahu_name ]["isSimultaneousSupply_heating"] == "有"):

            inputdata["AirHandlingSystem"][ ahu_name ]["isSimultaneousSupply"] = "有"


    ##----------------------------------------------------------------------------------
    ## 空調機群が処理する日積算室負荷（解説書 2.5.1）
    ##----------------------------------------------------------------------------------
    for room_zone_name in inputdata["AirConditioningZone"]:

        # 室内負荷処理用空調機群の名称
        ahu_name = inputdata["AirConditioningZone"][room_zone_name]["AHU_cooling_insideLoad"]

        # 当該空調機群が熱を供給する室の室負荷（冷房要求）を積算する。
        resultJson["AHU"][ahu_name]["Qroom"]["cooling_for_room"] += resultJson["Qroom"][room_zone_name]["QroomDc"]

        # 当該空調機群が熱を供給する室の室負荷（暖房要求）を積算する。
        resultJson["AHU"][ahu_name]["Qroom"]["heating_for_room"] += resultJson["Qroom"][room_zone_name]["QroomDh"]


    ##----------------------------------------------------------------------------------
    ## 空調機群の運転時間（解説書 2.5.2）
    ##----------------------------------------------------------------------------------

    for room_zone_name in inputdata["AirConditioningZone"]:

        # 室内負荷処理用空調機群の名称
        ahu_name = inputdata["AirConditioningZone"][room_zone_name]["AHU_cooling_insideLoad"]

        # 室の空調有無 roomScheduleRoom（365×24）を加算
        resultJson["AHU"][ ahu_name ]["schedule"] += roomScheduleRoom[room_zone_name]
        # 運転時間帯（昼、夜、終日）をリストに追加していく。
        resultJson["AHU"][ ahu_name ]["day_mode"].append( roomDayMode[room_zone_name] )


    for room_zone_name in inputdata["AirConditioningZone"]:

        # 外気負荷処理用空調機群の名称
        ahu_name = inputdata["AirConditioningZone"][room_zone_name]["AHU_cooling_outdoorLoad"]

        # 室の空調有無 roomScheduleRoom（365×24）を加算
        resultJson["AHU"][ ahu_name ]["schedule"] += roomScheduleRoom[room_zone_name]
        # 運転時間帯（昼、夜、終日）をリストに追加していく。
        resultJson["AHU"][ ahu_name ]["day_mode"].append( roomDayMode[room_zone_name] )


    # 各空調機群の運転時間
    for ahu_name in inputdata["AirHandlingSystem"]:

        # 運転スケジュールの和が「1以上（どこか一部屋は動いている）」であれば、空調機は稼働しているとする。
        resultJson["AHU"][ahu_name]["schedule"][   resultJson["AHU"][ahu_name]["schedule"] > 1   ] = 1

        # 空調機群の日積算運転時間（冷暖合計）
        resultJson["AHU"][ahu_name]["Tahu_total"] = np.sum(resultJson["AHU"][ahu_name]["schedule"], 1)

        # 空調機の運転モード と　外気エンタルピー
        if "終日" in resultJson["AHU"][ahu_name]["day_mode"]: # 一つでも「終日」があれば
            resultJson["AHU"][ahu_name]["day_mode"] = "終日"
            resultJson["AHU"][ahu_name]["HoaDayAve"] = Hoa_ave

        elif resultJson["AHU"][ahu_name]["day_mode"].count("昼") == len(resultJson["AHU"][ahu_name]["day_mode"]): # 全て「昼」であれば
            resultJson["AHU"][ahu_name]["day_mode"] = "昼"
            resultJson["AHU"][ahu_name]["HoaDayAve"] = Hoa_day

        elif resultJson["AHU"][ahu_name]["day_mode"].count("夜") == len(resultJson["AHU"][ahu_name]["day_mode"]): # 全て夜であれば
            resultJson["AHU"][ahu_name]["day_mode"] = "夜"
            resultJson["AHU"][ahu_name]["HoaDayAve"] = Hoa_ngt

        else: # 「昼」と「夜」が混在する場合は「終日とする。
            resultJson["AHU"][ahu_name]["day_mode"]  = "終日"
            resultJson["AHU"][ahu_name]["HoaDayAve"] = Hoa_ave

        # 日別に運転時間を「冷房」と「暖房」に振り分ける。
        for dd in range(0,365):

            if resultJson["AHU"][ahu_name]["Tahu_total"][dd] == 0:

                # 日空調時間が0であれば、冷暖房空調時間は0とする。
                resultJson["AHU"][ahu_name]["Tahu"]["cooling_for_room"][dd] = 0
                resultJson["AHU"][ahu_name]["Tahu"]["heating_for_room"][dd] = 0

            else:

                if (resultJson["AHU"][ahu_name]["Qroom"]["cooling_for_room"][dd] == 0) and \
                    (resultJson["AHU"][ahu_name]["Qroom"]["heating_for_room"][dd] == 0): # 外調機を想定（空調運転時間は0より大きいが、Qroomが0である場合）

                    # 外調機の場合は「冷房側」に運転時間を割り当てる。
                    resultJson["AHU"][ahu_name]["Tahu"]["cooling_for_room"][dd] = resultJson["AHU"][ahu_name]["Tahu_total"][dd]
                    resultJson["AHU"][ahu_name]["Tahu"]["heating_for_room"][dd] = 0

                elif resultJson["AHU"][ahu_name]["Qroom"]["cooling_for_room"][dd] == 0:  # 暖房要求しかない場合。

                    resultJson["AHU"][ahu_name]["Tahu"]["cooling_for_room"][dd] = 0
                    resultJson["AHU"][ahu_name]["Tahu"]["heating_for_room"][dd] = resultJson["AHU"][ahu_name]["Tahu_total"][dd]

                elif resultJson["AHU"][ahu_name]["Qroom"]["heating_for_room"][dd] == 0:  # 冷房要求しかない場合。

                    resultJson["AHU"][ahu_name]["Tahu"]["cooling_for_room"][dd] = resultJson["AHU"][ahu_name]["Tahu_total"][dd]
                    resultJson["AHU"][ahu_name]["Tahu"]["heating_for_room"][dd] = 0

                else: # 冷房要求と暖房要求の両方が発生する場合

                    if abs(resultJson["AHU"][ahu_name]["Qroom"]["cooling_for_room"][dd]) < abs(resultJson["AHU"][ahu_name]["Qroom"]["heating_for_room"][dd]):

                        # 暖房負荷の方が大きい場合
                        ratio = abs(resultJson["AHU"][ahu_name]["Qroom"]["cooling_for_room"][dd]) / \
                            ( abs(resultJson["AHU"][ahu_name]["Qroom"]["cooling_for_room"][dd]) + abs(resultJson["AHU"][ahu_name]["Qroom"]["heating_for_room"][dd]) )

                        resultJson["AHU"][ahu_name]["Tahu"]["cooling_for_room"][dd] = math.ceil( resultJson["AHU"][ahu_name]["Tahu_total"][dd] * ratio )
                        resultJson["AHU"][ahu_name]["Tahu"]["heating_for_room"][dd] = resultJson["AHU"][ahu_name]["Tahu_total"][dd] - resultJson["AHU"][ahu_name]["Tahu"]["cooling_for_room"][dd]

                    else:

                        # 冷房負荷の方が大きい場合
                        ratio = abs(resultJson["AHU"][ahu_name]["Qroom"]["heating_for_room"][dd]) / \
                            ( abs(resultJson["AHU"][ahu_name]["Qroom"]["cooling_for_room"][dd]) + abs(resultJson["AHU"][ahu_name]["Qroom"]["heating_for_room"][dd]) )

                        resultJson["AHU"][ahu_name]["Tahu"]["heating_for_room"][dd] = math.ceil( resultJson["AHU"][ahu_name]["Tahu_total"][dd] * ratio )
                        resultJson["AHU"][ahu_name]["Tahu"]["cooling_for_room"][dd] = resultJson["AHU"][ahu_name]["Tahu_total"][dd] - resultJson["AHU"][ahu_name]["Tahu"]["heating_for_room"][dd]


    ##----------------------------------------------------------------------------------
    ## 外気負荷[kW]の算出（解説書 2.5.3）
    ##----------------------------------------------------------------------------------

    # 外気導入量 [m3/h]
    for ahu_name in inputdata["AirHandlingSystem"]:
        inputdata["AirHandlingSystem"][ ahu_name ]["outdoorAirVolume_cooling"] = 0
        inputdata["AirHandlingSystem"][ ahu_name ]["outdoorAirVolume_heating"] = 0

    for room_zone_name in inputdata["AirConditioningZone"]:

        # 各室の外気導入量 [m3/h]
        if "room_usage_condition" in inputdata["SpecialInputData"]:    # SPシートで任意の入力がされている場合

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
        inputdata["AirHandlingSystem"][ inputdata["AirConditioningZone"][room_zone_name]["AHU_cooling_outdoorLoad"] ]["outdoorAirVolume_cooling"] += \
            inputdata["AirConditioningZone"][room_zone_name]["outdoorAirVolume"]

        # 暖房期間における外気風量 [m3/h]
        inputdata["AirHandlingSystem"][ inputdata["AirConditioningZone"][room_zone_name]["AHU_heating_outdoorLoad"] ]["outdoorAirVolume_heating"] += \
            inputdata["AirConditioningZone"][room_zone_name]["outdoorAirVolume"]


    # 全熱交換効率の補正
    for ahu_name in inputdata["AirHandlingSystem"]:

        # 冷房運転時の補正
        if inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioCooling"] != None:

            ahuaexeff = inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioCooling"]/100
            aexCeff = 1 - ((1/0.85)-1) * (1-ahuaexeff)/ahuaexeff
            aexCtol = 0.95
            aexCbal = 0.67
            inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioCooling"] = \
                ahuaexeff * aexCeff * aexCtol * aexCbal

        # 暖房運転時の補正
        if inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioHeating"] != None:

            ahuaexeff = inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioHeating"]/100
            aexCeff = 1 - ((1/0.85)-1) * (1-ahuaexeff)/ahuaexeff
            aexCtol = 0.95
            aexCbal = 0.67
            inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioHeating"] = \
                ahuaexeff * aexCeff * aexCtol * aexCbal


    # 外気負荷[kW]
    for ahu_name in inputdata["AirHandlingSystem"]:

        for dd in range(0,365):

            if resultJson["AHU"][ahu_name]["Tahu_total"][dd] > 0:  # 空調機が稼働する場合

                # 運転モードによって場合分け
                if ac_mode[dd] == "暖房":

                    # 外気導入量 [m3/h]
                    ahuVoa  = inputdata["AirHandlingSystem"][ahu_name]["outdoorAirVolume_heating"]
                    # 全熱交換風量 [m3/h]
                    ahuaexV = inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangerAirVolume"]

                    # 全熱交換風量（0以上、外気導入量以下とする）
                    if ahuaexV > ahuVoa:
                        ahuaexV = ahuVoa
                    elif ahuaexV <= 0:
                        ahuaexV = 0

                    # 外気負荷の算出
                    if inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioHeating"] == None:   # 全熱交換器がない場合

                        resultJson["AHU"][ahu_name]["qoaAHU"][dd] = \
                            (resultJson["AHU"][ahu_name]["HoaDayAve"][dd] - Hroom[dd]) * inputdata["AirHandlingSystem"][ahu_name]["outdoorAirVolume_heating"] *1.293/3600

                    else:  # 全熱交換器がある場合

                        if (resultJson["AHU"][ahu_name]["HoaDayAve"][dd] > Hroom[dd]) and (inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangerControl"] == "有"):

                            # バイパス有の場合はそのまま外気導入する。
                            resultJson["AHU"][ahu_name]["qoaAHU"][dd] = \
                                (resultJson["AHU"][ahu_name]["HoaDayAve"][dd] - Hroom[dd]) * inputdata["AirHandlingSystem"][ahu_name]["outdoorAirVolume_heating"] *1.293/3600

                        else:

                            # 全熱交換器による外気負荷削減を見込む。
                            resultJson["AHU"][ahu_name]["qoaAHU"][dd] = \
                                (resultJson["AHU"][ahu_name]["HoaDayAve"][dd] - Hroom[dd]) * \
                                (inputdata["AirHandlingSystem"][ahu_name]["outdoorAirVolume_heating"] - \
                                    ahuaexV * inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioHeating"] ) *1.293/3600


                elif (ac_mode[dd] == "中間") or (ac_mode[dd] == "冷房"):

                    ahuVoa  = inputdata["AirHandlingSystem"][ahu_name]["outdoorAirVolume_cooling"]
                    ahuaexV = inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangerAirVolume"]

                    # 全熱交換風量（0以上、外気導入量以下とする）
                    if ahuaexV > ahuVoa:
                        ahuaexV = ahuVoa
                    elif ahuaexV <= 0:
                        ahuaexV = 0

                    # 外気負荷の算出
                    if inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioCooling"] == None:   # 全熱交換器がない場合

                        resultJson["AHU"][ahu_name]["qoaAHU"][dd] = \
                            (resultJson["AHU"][ahu_name]["HoaDayAve"][dd] - Hroom[dd]) * inputdata["AirHandlingSystem"][ahu_name]["outdoorAirVolume_cooling"] *1.293/3600

                    else:  # 全熱交換器がある場合

                        if (resultJson["AHU"][ahu_name]["HoaDayAve"][dd] < Hroom[dd]) and  (inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangerControl"] == "有"):

                            # バイパス有の場合はそのまま外気導入する。
                            resultJson["AHU"][ahu_name]["qoaAHU"][dd] = \
                                (resultJson["AHU"][ahu_name]["HoaDayAve"][dd] - Hroom[dd]) * inputdata["AirHandlingSystem"][ahu_name]["outdoorAirVolume_cooling"] *1.293/3600

                        else:  # 全熱交換器がある場合

                            # 全熱交換器による外気負荷削減を見込む。
                            resultJson["AHU"][ahu_name]["qoaAHU"][dd] = \
                                (resultJson["AHU"][ahu_name]["HoaDayAve"][dd] - Hroom[dd]) * \
                                (inputdata["AirHandlingSystem"][ahu_name]["outdoorAirVolume_cooling"] - \
                                    ahuaexV * inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioCooling"] ) *1.293/3600


    ##----------------------------------------------------------------------------------
    ## 外気冷房制御による負荷削減量（解説書 2.5.4）
    ##----------------------------------------------------------------------------------

    for ahu_name in inputdata["AirHandlingSystem"]:

        for dd in range(0,365):

            if resultJson["AHU"][ahu_name]["Tahu_total"][dd] > 0:    # 空調機が稼働する場合

                # 外気冷房効果の推定
                if (inputdata["AirHandlingSystem"][ahu_name]["isEconomizer"] == "有") and (resultJson["AHU"][ahu_name]["Tahu"]["cooling_for_room"][dd]>0):   # 外気冷房があり、室負荷が冷房要求であれば

                    # 外気冷房運転時の外気風量 [kg/s]
                    resultJson["AHU"][ahu_name]["Economizer"]["AHUVovc"][dd] = \
                        resultJson["AHU"][ahu_name]["Qroom"]["cooling_for_room"][dd] / \
                        ((Hroom[dd]-resultJson["AHU"][ahu_name]["HoaDayAve"][dd]) * (3600/1000) * resultJson["AHU"][ahu_name]["Tahu"]["cooling_for_room"][dd])

                    # 上限・下限
                    if resultJson["AHU"][ahu_name]["Economizer"]["AHUVovc"][dd] < inputdata["AirHandlingSystem"][ahu_name]["outdoorAirVolume_cooling"] *1.293/3600:

                        # 下限（外気取入量） [m3/h]→[kg/s]
                        resultJson["AHU"][ahu_name]["Economizer"]["AHUVovc"][dd] = inputdata["AirHandlingSystem"][ahu_name]["outdoorAirVolume_cooling"] *1.293/3600

                    elif resultJson["AHU"][ahu_name]["Economizer"]["AHUVovc"][dd] > inputdata["AirHandlingSystem"][ahu_name]["EconomizerMaxAirVolume"] *1.293/3600:

                        # 上限（給気風量) [m3/h]→[kg/s]
                        resultJson["AHU"][ahu_name]["Economizer"]["AHUVovc"][dd] = inputdata["AirHandlingSystem"][ahu_name]["EconomizerMaxAirVolume"] *1.293/3600

                    # 追加すべき外気量（外気冷房用の追加分のみ）[kg/s]
                    resultJson["AHU"][ahu_name]["Economizer"]["AHUVovc"][dd] = \
                        resultJson["AHU"][ahu_name]["Economizer"]["AHUVovc"][dd] - inputdata["AirHandlingSystem"][ahu_name]["outdoorAirVolume_cooling"] *1.293/3600

                # 外気冷房による負荷削減効果 [MJ/day]
                if (inputdata["AirHandlingSystem"][ahu_name]["isEconomizer"] == "有"): # 外気冷房があれば

                    if resultJson["AHU"][ahu_name]["Economizer"]["AHUVovc"][dd] > 0: # 外冷時風量＞０であれば

                        resultJson["AHU"][ahu_name]["Economizer"]["Qahu_oac"][dd] = \
                            resultJson["AHU"][ahu_name]["Economizer"]["AHUVovc"][dd] * (Hroom[dd]-resultJson["AHU"][ahu_name]["HoaDayAve"][dd])*3600/1000* \
                            resultJson["AHU"][ahu_name]["Tahu"]["cooling_for_room"][dd]


    ##----------------------------------------------------------------------------------
    ## 日積算空調負荷 Qahu_c, Qahu_h の算出（解説書 2.5.5）
    ##----------------------------------------------------------------------------------

    for ahu_name in inputdata["AirHandlingSystem"]:

        for dd in range(0,365):

            # 外気負荷のみの処理が要求される空調機群である場合(処理上、「室負荷が冷房要求である場合」 として扱う)
            if (resultJson["AHU"][ahu_name]["Tahu"]["cooling_for_room"][dd] == 0) and (resultJson["AHU"][ahu_name]["Tahu"]["heating_for_room"][dd] == 0):

                if (inputdata["AirHandlingSystem"][ahu_name]["isOutdoorAirCut"] == "無"):

                    resultJson["AHU"][ahu_name]["Qahu"]["cooling_for_room"][dd] = \
                        resultJson["AHU"][ahu_name]["qoaAHU"][dd] * resultJson["AHU"][ahu_name]["Tahu_total"][dd] * 3600/1000

                else:

                    # 運転時間が1時間より大きい場合は、外気カットの効果を見込む。
                    if resultJson["AHU"][ahu_name]["Tahu_total"][dd] > 1:
                        resultJson["AHU"][ahu_name]["Qahu"]["cooling_for_room"][dd] = \
                            resultJson["AHU"][ahu_name]["qoaAHU"][dd] * (resultJson["AHU"][ahu_name]["Tahu_total"][dd]-1) * 3600/1000

                    else:

                        # 運転時間が1時間以下である場合は、外気カットの効果を見込まない。
                        resultJson["AHU"][ahu_name]["Qahu"]["cooling_for_room"][dd] = \
                            resultJson["AHU"][ahu_name]["qoaAHU"][dd] * resultJson["AHU"][ahu_name]["Tahu_total"][dd] * 3600/1000

                # 外気負荷のみ場合は、便宜上、暖房要求の室負荷は 0 であるとする。
                resultJson["AHU"][ahu_name]["Qahu"]["heating_for_room"][dd] = 0


            else:  # 室負荷と外気負荷の両方を処理が要求される空調機群である場合

                # 冷房要求の室負荷を処理する必要がある場合
                if resultJson["AHU"][ahu_name]["Tahu"]["cooling_for_room"][dd] > 0:

                    if (inputdata["AirHandlingSystem"][ahu_name]["isOutdoorAirCut"] == "有") and \
                        (resultJson["AHU"][ahu_name]["Tahu"]["cooling_for_room"][dd] > 1) and \
                        (resultJson["AHU"][ahu_name]["Tahu"]["cooling_for_room"][dd] >= resultJson["AHU"][ahu_name]["Tahu"]["heating_for_room"][dd]):

                        # 室負荷が正（冷房要求）であるときの空調負荷（正であれば冷却コイル負荷、負であれば加熱コイル負荷）　外気カットの効果を見込む
                        resultJson["AHU"][ahu_name]["Qahu"]["cooling_for_room"][dd] = \
                            resultJson["AHU"][ahu_name]["Qroom"]["cooling_for_room"][dd] + \
                            resultJson["AHU"][ahu_name]["qoaAHU"][dd] * (resultJson["AHU"][ahu_name]["Tahu"]["cooling_for_room"][dd] - 1) * 3600/1000

                    else:

                        # 室負荷が正（冷房要求）であるときの空調負荷（正であれば冷却コイル負荷、負であれば加熱コイル負荷）
                        resultJson["AHU"][ahu_name]["Qahu"]["cooling_for_room"][dd] = \
                            resultJson["AHU"][ahu_name]["Qroom"]["cooling_for_room"][dd] + \
                            resultJson["AHU"][ahu_name]["qoaAHU"][dd] * (resultJson["AHU"][ahu_name]["Tahu"]["cooling_for_room"][dd]) * 3600/1000


                # 暖房要求の室負荷を処理する必要がある場合
                if resultJson["AHU"][ahu_name]["Tahu"]["heating_for_room"][dd] > 0:

                    if (inputdata["AirHandlingSystem"][ahu_name]["isOutdoorAirCut"] == "有") and \
                        (resultJson["AHU"][ahu_name]["Tahu"]["heating_for_room"][dd] > 1) and \
                        (resultJson["AHU"][ahu_name]["Tahu"]["cooling_for_room"][dd] < resultJson["AHU"][ahu_name]["Tahu"]["heating_for_room"][dd]):

                        # 室負荷が負（暖房要求）であるときの空調負荷（正であれば冷却コイル負荷、負であれば加熱コイル負荷）　外気カットの効果を見込む
                        resultJson["AHU"][ahu_name]["Qahu"]["heating_for_room"][dd] = \
                            resultJson["AHU"][ahu_name]["Qroom"]["heating_for_room"][dd] + \
                            resultJson["AHU"][ahu_name]["qoaAHU"][dd] * (resultJson["AHU"][ahu_name]["Tahu"]["heating_for_room"][dd] - 1) * 3600/1000

                    else:

                        # 室負荷が負（暖房要求）であるときの空調負荷（正であれば冷却コイル負荷、負であれば加熱コイル負荷）
                        resultJson["AHU"][ahu_name]["Qahu"]["heating_for_room"][dd] = \
                            resultJson["AHU"][ahu_name]["Qroom"]["heating_for_room"][dd] + \
                            resultJson["AHU"][ahu_name]["qoaAHU"][dd] * (resultJson["AHU"][ahu_name]["Tahu"]["heating_for_room"][dd]) * 3600/1000


    print('空調負荷計算完了')

    if debug: # pragma: no cover

        for ahu_name in inputdata["AirHandlingSystem"]:

            print( f'--- 空調機群名 {ahu_name} ---')

            print( f'外気負荷 qoaAHU {np.sum(resultJson["AHU"][ahu_name]["qoaAHU"],0)}' )
            print( f'外気導入量 outdoorAirVolume_cooling {inputdata["AirHandlingSystem"][ahu_name]["outdoorAirVolume_cooling"]} m3/h' )
            print( f'外気冷房時最大風量 EconomizerMaxAirVolume {inputdata["AirHandlingSystem"][ahu_name]["EconomizerMaxAirVolume"]} m3/h' )
            print( f'外気冷房時風量 AHUVovc {np.sum(resultJson["AHU"][ahu_name]["Economizer"]["AHUVovc"],0)}' )
            print( f'外気冷房効果 Qahu_oac： {np.sum(resultJson["AHU"][ahu_name]["Economizer"]["Qahu_oac"],0)}' )

            print( f'室負荷が正（冷房要求）であるときの空調機群の運転時間 Tahu： {np.sum(resultJson["AHU"][ahu_name]["Tahu"]["cooling_for_room"],0)} 時間' )
            print( f'室負荷が負（暖房要求）であるときの空調機群の運転時間 Tahu： {np.sum(resultJson["AHU"][ahu_name]["Tahu"]["heating_for_room"],0)} 時間' )
            print( f'室負荷が正（冷房要求）であるときの空調負荷 Qahu： {np.sum(resultJson["AHU"][ahu_name]["Qahu"]["cooling_for_room"],0)}' )
            print( f'室負荷が負（暖房要求）であるときの空調負荷 Qahu： {np.sum(resultJson["AHU"][ahu_name]["Qahu"]["heating_for_room"],0)}' )

            print( f'空調機群 冷暖同時供給の有無： {inputdata["AirHandlingSystem"][ahu_name]["isSimultaneousSupply"]}' )


    ##----------------------------------------------------------------------------------
    ## 任意評定用　空調負荷（ SP-10 ）
    ##----------------------------------------------------------------------------------

    if "SpecialInputData" in inputdata:
        if "Qahu" in inputdata["SpecialInputData"]:

            for ahu_name in inputdata["SpecialInputData"]["Qahu"]: # SP-10シートに入力された空調機群毎に処理
                if ahu_name in resultJson["AHU"]:  # SP-10シートに入力された室が空調機群として存在していれば

                    Qahu_cooling = np.zeros(365)
                    Tahu_cooling = np.zeros(365)
                    Qahu_heating = np.zeros(365)
                    Tahu_heating = np.zeros(365)

                    for dd in range(0,365):
                        for hh in range(0,24):
                            if inputdata["SpecialInputData"]["Qahu"][ahu_name][dd][hh] > 0: # 冷房負荷であれば

                                # 空調負荷[kW] → [MJ/h]
                                Qahu_cooling[dd] += inputdata["SpecialInputData"]["Qahu"][ahu_name][dd][hh] * 3600 / 1000
                                Tahu_cooling[dd] += 1

                            elif inputdata["SpecialInputData"]["Qahu"][ahu_name][dd][hh] < 0: # 冷房負荷であれば

                                # 空調負荷[kW] → [MJ/h]
                                Qahu_heating[dd] += inputdata["SpecialInputData"]["Qahu"][ahu_name][dd][hh] * 3600 / 1000
                                Tahu_heating[dd] += 1


                    # 空調負荷 [MJ/day] を上書き
                    resultJson["AHU"][ahu_name]["Qahu"]["cooling_for_room"] = Qahu_cooling
                    resultJson["AHU"][ahu_name]["Qahu"]["heating_for_room"] = Qahu_heating
                    resultJson["AHU"][ahu_name]["Tahu"]["cooling_for_room"] = Tahu_cooling
                    resultJson["AHU"][ahu_name]["Tahu"]["heating_for_room"] = Tahu_heating

                    # 外気冷房は強制的に0とする（既に見込まれているものとする）
                    resultJson["AHU"][ahu_name]["Economizer"]["Qahu_oac"] = np.zeros(365)


    ##----------------------------------------------------------------------------------
    ## 空調機群の負荷率（解説書 2.5.6）
    ##----------------------------------------------------------------------------------

    for ahu_name in inputdata["AirHandlingSystem"]:

        # 冷房要求の場合と暖房要求の場合で処理を繰り返す（同じ日に両方発生する場合がある）
        for requirement_type in ["cooling_for_room", "heating_for_room"]:

            La  = np.zeros(365)

            # 負荷率の算出
            if requirement_type == "cooling_for_room": # 室負荷が正（冷房要求）であるとき

                # 室負荷が正（冷房要求）であるときの平均負荷率 La [-]
                for dd in range(0,365):

                    if resultJson["AHU"][ahu_name]["Qahu"]["cooling_for_room"][dd] >= 0 and resultJson["AHU"][ahu_name]["Tahu"]["cooling_for_room"][dd] != 0:

                        # 空調負荷が正（冷却コイル負荷）である場合　→　定格冷却能力で除して負荷率を求める。
                        La[dd] = (resultJson["AHU"][ahu_name]["Qahu"]["cooling_for_room"][dd] / resultJson["AHU"][ahu_name]["Tahu"]["cooling_for_room"][dd] *1000/3600) / \
                            inputdata["AirHandlingSystem"][ahu_name]["RatedCapacityCooling"]

                    elif resultJson["AHU"][ahu_name]["Tahu"]["cooling_for_room"][dd] != 0:

                        # 空調負荷が負（加熱コイル負荷）である場合　→　定格加熱能力で除して負荷率を求める。
                        La[dd] = (resultJson["AHU"][ahu_name]["Qahu"]["cooling_for_room"][dd] / resultJson["AHU"][ahu_name]["Tahu"]["cooling_for_room"][dd] *1000/3600) / \
                            inputdata["AirHandlingSystem"][ahu_name]["RatedCapacityHeating"]


            elif requirement_type == "heating_for_room": # 室負荷が負（暖房要求）であるとき

                # 室負荷が負（暖房要求）であるときの平均負荷率 La [-]
                for dd in range(0,365):

                    if resultJson["AHU"][ahu_name]["Qahu"]["heating_for_room"][dd] <= 0 and resultJson["AHU"][ahu_name]["Tahu"]["heating_for_room"][dd] != 0:

                        # 空調負荷が負（加熱コイル負荷）である場合　→　定格加熱能力で除して負荷率を求める。
                        La[dd] = (resultJson["AHU"][ahu_name]["Qahu"]["heating_for_room"][dd] / resultJson["AHU"][ahu_name]["Tahu"]["heating_for_room"][dd] *1000/3600) / \
                            inputdata["AirHandlingSystem"][ahu_name]["RatedCapacityHeating"]

                    elif resultJson["AHU"][ahu_name]["Tahu"]["heating_for_room"][dd] != 0:

                        # 空調負荷が正（冷却コイル負荷）である場合　→　定格冷却能力で除して負荷率を求める。
                        La[dd] = (resultJson["AHU"][ahu_name]["Qahu"]["heating_for_room"][dd] / resultJson["AHU"][ahu_name]["Tahu"]["heating_for_room"][dd] *1000/3600) / \
                            inputdata["AirHandlingSystem"][ahu_name]["RatedCapacityCooling"]


            # 定格能力＞０　→　空調機群に負荷を処理する機器があれば
            if (inputdata["AirHandlingSystem"][ahu_name]["RatedCapacityCooling"] > 0) or (inputdata["AirHandlingSystem"][ahu_name]["RatedCapacityHeating"] > 0):

                # 冷暖同時運転が「有」である場合（季節に依らず、冷却コイル負荷も加熱コイル負荷も処理する）
                if inputdata["AirHandlingSystem"][ahu_name]["isSimultaneousSupply"] == "有":

                    for dd in range(0,365):

                        if np.isnan(La[dd]) == False:

                            if La[dd] > 0:    # 負荷率が正（冷却コイル負荷）である場合

                                # 負荷率帯インデックスの決定
                                iL = count_Matrix(La[dd], mxL)

                                if requirement_type == "cooling_for_room":     # 室負荷が正（冷房要求）である場合

                                    # 室負荷が正（冷房要求）であるときの冷却コイル負荷の負荷率帯インデックス
                                    resultJson["AHU"][ahu_name]["LdAHUc"]["cooling_for_room"][dd] = iL
                                    # 室負荷が正（冷房要求）であるときの空調運転時間
                                    resultJson["AHU"][ahu_name]["TdAHUc"]["cooling_for_room"][dd] = resultJson["AHU"][ahu_name]["Tahu"]["cooling_for_room"][dd]

                                elif requirement_type == "heating_for_room":   # 室負荷が負（暖房要求）である場合

                                    # 室負荷が負（暖房要求）であるときの冷却コイル負荷の負荷率帯インデックス
                                    resultJson["AHU"][ahu_name]["LdAHUc"]["heating_for_room"][dd] = iL
                                    # 室負荷が負（暖房要求）であるときの空調運転時間
                                    resultJson["AHU"][ahu_name]["TdAHUc"]["heating_for_room"][dd] = resultJson["AHU"][ahu_name]["Tahu"]["heating_for_room"][dd]

                            elif La[dd] < 0:  # 負荷率が負（加熱コイル負荷）である場合

                                # 負荷率帯インデックスの決定
                                iL = count_Matrix((-1)*La[dd], mxL)

                                if requirement_type == "cooling_for_room":     # 室負荷が正（冷房要求）である場合

                                    # 室負荷が正（冷房要求）であるときの加熱コイル負荷の負荷率帯インデックス
                                    resultJson["AHU"][ahu_name]["LdAHUh"]["cooling_for_room"][dd] = iL
                                    # 室負荷が正（冷房要求）であるときの空調運転時間
                                    resultJson["AHU"][ahu_name]["TdAHUh"]["cooling_for_room"][dd] = resultJson["AHU"][ahu_name]["Tahu"]["cooling_for_room"][dd]

                                elif requirement_type == "heating_for_room":   # 室負荷が負（暖房要求）である場合

                                    # 室負荷が負（暖房要求）であるときの加熱コイル負荷の負荷率帯インデックス
                                    resultJson["AHU"][ahu_name]["LdAHUh"]["heating_for_room"][dd] = iL
                                    # 室負荷が負（暖房要求）であるときの空調運転時間
                                    resultJson["AHU"][ahu_name]["TdAHUh"]["heating_for_room"][dd] = resultJson["AHU"][ahu_name]["Tahu"]["heating_for_room"][dd]


                # 冷暖同時供給が「無」である場合（季節により、冷却コイル負荷か加熱コイル負荷のどちらか一方を処理する）
                elif inputdata["AirHandlingSystem"][ahu_name]["isSimultaneousSupply"] == "無":

                    for dd in range(0,365):

                        if np.isnan(La[dd]) == False:   # 日付dの負荷率が NaN で無い場合

                            # 冷房モード で動く期間の場合、かつ、空調負荷（冷却コイル負荷か加熱コイル負荷）が発生しているとき
                            if (La[dd] != 0) and (ac_mode[dd] == "冷房" or ac_mode[dd] == "中間"):

                                # 負荷率帯インデックスの決定
                                iL = count_Matrix(La[dd], mxL)

                                if requirement_type == "cooling_for_room":     # 室負荷が正（冷房要求）である場合

                                    # 室負荷が正（冷房要求）であるときの空調負荷の負荷率帯インデックス（ただし、加熱コイル負荷は 負荷率帯 0　となる）
                                    resultJson["AHU"][ahu_name]["LdAHUc"]["cooling_for_room"][dd] = iL
                                    # 室負荷が正（冷房要求）であるときの空調運転時間(加熱コイル負荷発生時も 負荷率=0として送風機は動く想定)
                                    resultJson["AHU"][ahu_name]["TdAHUc"]["cooling_for_room"][dd] = resultJson["AHU"][ahu_name]["Tahu"]["cooling_for_room"][dd]

                                elif requirement_type == "heating_for_room":   # 室負荷が負（暖房要求）である場合

                                    # 室負荷が負（暖房要求）であるときの空調負荷の負荷率帯インデックス（ただし、加熱コイル負荷は 負荷率帯 0　となる）
                                    resultJson["AHU"][ahu_name]["LdAHUc"]["heating_for_room"][dd] = iL
                                    # 室負荷が負（暖房要求）であるときの空調運転時間(加熱コイル負荷発生時も 負荷率=0として送風機は動く想定)
                                    resultJson["AHU"][ahu_name]["TdAHUc"]["heating_for_room"][dd] = resultJson["AHU"][ahu_name]["Tahu"]["heating_for_room"][dd]

                            # 暖房モード で動く期間の場合、かつ、空調負荷（冷却コイル負荷か加熱コイル負荷）が発生しているとき
                            elif (La[dd] != 0) and (ac_mode[dd] == "暖房"):

                                # 負荷率帯インデックスの決定
                                iL = count_Matrix((-1)*La[dd], mxL)

                                if requirement_type == "cooling_for_room":     # 室負荷が正（冷房要求）である場合

                                    # 室負荷が正（冷房要求）であるときの空調負荷の負荷率帯インデックス（ただし、冷却コイル負荷は 負荷率帯 0　となる）
                                    resultJson["AHU"][ahu_name]["LdAHUh"]["cooling_for_room"][dd] = iL
                                    # 室負荷が正（冷房要求）であるときの空調運転時間(冷却コイル負荷発生時も 負荷率=0として送風機は動く想定)
                                    resultJson["AHU"][ahu_name]["TdAHUh"]["cooling_for_room"][dd] = resultJson["AHU"][ahu_name]["Tahu"]["cooling_for_room"][dd]

                                elif requirement_type == "heating_for_room":   # 室負荷が負（暖房要求）である場合

                                    # 室負荷が負（暖房要求）であるときの空調負荷の負荷率帯インデックス（ただし、冷却コイル負荷は 負荷率帯 0　となる）
                                    resultJson["AHU"][ahu_name]["LdAHUh"]["heating_for_room"][dd] = iL
                                    # 室負荷が負（暖房要求）であるときの空調運転時間(冷却コイル負荷発生時も 負荷率=0として送風機は動く想定)
                                    resultJson["AHU"][ahu_name]["TdAHUh"]["heating_for_room"][dd] = resultJson["AHU"][ahu_name]["Tahu"]["heating_for_room"][dd]

    if debug: # pragma: no cover

        for ahu_name in inputdata["AirHandlingSystem"]:

            # マトリックスの再現
            LAHUc0 = np.zeros(11)
            LAHUc1 = np.zeros(11)
            LAHUh0 = np.zeros(11)
            LAHUh1 = np.zeros(11)
            for dd in range(0,365):
                LAHUc0[ int(resultJson["AHU"][ahu_name]["LdAHUc"]["cooling_for_room"][dd]-1) ] += resultJson["AHU"][ahu_name]["TdAHUc"]["cooling_for_room"][dd]
                LAHUc1[ int(resultJson["AHU"][ahu_name]["LdAHUc"]["heating_for_room"][dd]-1) ] += resultJson["AHU"][ahu_name]["TdAHUc"]["heating_for_room"][dd]
                LAHUh0[ int(resultJson["AHU"][ahu_name]["LdAHUh"]["cooling_for_room"][dd]-1) ] += resultJson["AHU"][ahu_name]["TdAHUh"]["cooling_for_room"][dd]
                LAHUh1[ int(resultJson["AHU"][ahu_name]["LdAHUh"]["heating_for_room"][dd]-1) ] += resultJson["AHU"][ahu_name]["TdAHUh"]["heating_for_room"][dd]


    ##----------------------------------------------------------------------------------
    ## 風量制御方式によって定まる係数（解説書 2.5.7）
    ##----------------------------------------------------------------------------------

    ## 搬送系制御に関する係数

    for ahu_name in inputdata["AirHandlingSystem"]:

        for unit_id, unit_configure in enumerate(inputdata["AirHandlingSystem"][ahu_name]["AirHandlingUnit"]):

            # 初期化
            inputdata["AirHandlingSystem"][ahu_name]["AirHandlingUnit"][unit_id]["energy_consumption_ratio"] = np.ones(len(aveL))

            # 係数の取得
            if unit_configure["FanControlType"] in FLOWCONTROL.keys():

                a4 = FLOWCONTROL[ unit_configure["FanControlType"] ]["a4"]
                a3 = FLOWCONTROL[ unit_configure["FanControlType"] ]["a3"]
                a2 = FLOWCONTROL[ unit_configure["FanControlType"] ]["a2"]
                a1 = FLOWCONTROL[ unit_configure["FanControlType"] ]["a1"]
                a0 = FLOWCONTROL[ unit_configure["FanControlType"] ]["a0"]

                if unit_configure["FanMinOpeningRate"] == None:
                    Vmin = 1
                else:
                    Vmin = unit_configure["FanMinOpeningRate"]/100

            elif unit_configure["FanControlType"] == "無":

                a4 = 0
                a3 = 0
                a2 = 0
                a1 = 0
                a0 = 1
                Vmin = 1

            else:
                raise Exception('制御方式が不正です')


            # 負荷率帯毎のエネルギー消費量を算出
            for iL in range(0,len(aveL)):
                if aveL[iL] > 1:
                    inputdata["AirHandlingSystem"][ahu_name]["AirHandlingUnit"][unit_id]["energy_consumption_ratio"][iL] = 1.2
                elif aveL[iL] == 0:
                    inputdata["AirHandlingSystem"][ahu_name]["AirHandlingUnit"][unit_id]["energy_consumption_ratio"][iL] = 0
                elif aveL[iL] < Vmin:
                    inputdata["AirHandlingSystem"][ahu_name]["AirHandlingUnit"][unit_id]["energy_consumption_ratio"][iL] = \
                        a4 * (Vmin)**4 + \
                        a3 * (Vmin)**3 + \
                        a2 * (Vmin)**2 + \
                        a1 * (Vmin)**1 + \
                        a0
                else:
                    inputdata["AirHandlingSystem"][ahu_name]["AirHandlingUnit"][unit_id]["energy_consumption_ratio"][iL] = \
                        a4 * (aveL[iL])**4 + \
                        a3 * (aveL[iL])**3 + \
                        a2 * (aveL[iL])**2 + \
                        a1 * (aveL[iL])**1 + \
                        a0

    if debug: # pragma: no cover

        for ahu_name in inputdata["AirHandlingSystem"]:
            print( f'--- 空調機群名 {ahu_name} ---')
            for unit_id, unit_configure in enumerate(inputdata["AirHandlingSystem"][ahu_name]["AirHandlingUnit"]):
                print( f'--- {unit_id+1} 台目の送風機 ---')
                print(f'負荷率帯毎のエネルギー消費量 energy_consumption_ratio {inputdata["AirHandlingSystem"][ahu_name]["AirHandlingUnit"][unit_id]["energy_consumption_ratio"]}')


    ##----------------------------------------------------------------------------------
    ## 送風機単体の定格消費電力（解説書 2.5.8）
    ##----------------------------------------------------------------------------------

    for ahu_name in inputdata["AirHandlingSystem"]:

        inputdata["AirHandlingSystem"][ahu_name]["FanPowerConsumption_total"] = 0

        for unit_id, unit_configure in enumerate(inputdata["AirHandlingSystem"][ahu_name]["AirHandlingUnit"]):

            inputdata["AirHandlingSystem"][ahu_name]["AirHandlingUnit"][unit_id]["FanPowerConsumption_total"] = 0

            if unit_configure["FanPowerConsumption"] != None:

                # 送風機の定格消費電力 kW = 1台あたりの消費電力 kW × 台数
                inputdata["AirHandlingSystem"][ahu_name]["AirHandlingUnit"][unit_id]["FanPowerConsumption_total"] = \
                    unit_configure["FanPowerConsumption"] * unit_configure["Number"]

                # 積算
                inputdata["AirHandlingSystem"][ahu_name]["FanPowerConsumption_total"] += \
                    inputdata["AirHandlingSystem"][ahu_name]["AirHandlingUnit"][unit_id]["FanPowerConsumption_total"]

            if debug: # pragma: no cover
                print( f'--- 空調機群名 {ahu_name} ---')
                print( f'送風機単体の定格消費電力: {inputdata["AirHandlingSystem"][ahu_name]["AirHandlingUnit"][unit_id]["FanPowerConsumption_total"]}')



    ##----------------------------------------------------------------------------------
    ## 送風機の消費電力 （解説書 2.5.9）
    ##----------------------------------------------------------------------------------

    # 空調機群毎に、負荷率帯とエネルギー消費量[kW]の関係を算出
    for ahu_name in inputdata["AirHandlingSystem"]:

        for unit_id, unit_configure in enumerate(inputdata["AirHandlingSystem"][ahu_name]["AirHandlingUnit"]):

            for iL in range(0,len(aveL)):

                # 各負荷率帯における消費電力（制御の効果込み） [kW]
                resultJson["AHU"][ahu_name]["energy_consumption_each_LF"][iL] += \
                    unit_configure["energy_consumption_ratio"][iL] * unit_configure["FanPowerConsumption_total"]

            if debug: # pragma: no cover
                print( f'--- 空調機群名 {ahu_name} ---')
                print( f'負荷率帯別の送風機消費電力: \n {resultJson["AHU"][ahu_name]["energy_consumption_each_LF"]}')

    ##----------------------------------------------------------------------------------
    ## 全熱交換器の消費電力 （解説書 2.5.11）
    ##----------------------------------------------------------------------------------

    for ahu_name in inputdata["AirHandlingSystem"]:
        for dd in range(0,365):

            # 冷房負荷or暖房負荷が発生していれば、全熱交換器は動いたとみなす。
            if (resultJson["AHU"][ahu_name]["LdAHUc"]["cooling_for_room"][dd] > 0) or \
                (resultJson["AHU"][ahu_name]["LdAHUc"]["heating_for_room"][dd] > 0) or \
                (resultJson["AHU"][ahu_name]["LdAHUh"]["cooling_for_room"][dd] > 0) or \
                (resultJson["AHU"][ahu_name]["LdAHUh"]["heating_for_room"][dd] > 0):

                # 全熱交換器の消費電力量 MWh = 運転時間 h × 消費電力 kW
                resultJson["AHU"][ahu_name]["E_AHUaex_day"][dd] += \
                    resultJson["AHU"][ahu_name]["Tahu_total"][dd] * \
                    inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangerPowerConsumption"] / 1000


    ##----------------------------------------------------------------------------------
    ## 空調機群の年間一次エネルギー消費量 （解説書 2.5.12）
    ##----------------------------------------------------------------------------------

    for ahu_name in inputdata["AirHandlingSystem"]:
        for dd in range(0,365):

            ##-----------------------------------
            ## 室負荷が正（冷房要求）である場合：
            ##-----------------------------------
            if resultJson["AHU"][ahu_name]["LdAHUc"]["cooling_for_room"][dd] > 0:   # 空調負荷が正（冷却コイル負荷）である場合

                # 負荷率帯番号
                iL = int(resultJson["AHU"][ahu_name]["LdAHUc"]["cooling_for_room"][dd] - 1)

                # 空調負荷が正（冷却コイル負荷）の時の送風機等の消費電力　MWh
                resultJson["AHU"][ahu_name]["E_fan_c_day"][dd] += \
                    resultJson["AHU"][ahu_name]["energy_consumption_each_LF"][iL] / 1000 * resultJson["AHU"][ahu_name]["TdAHUc"]["cooling_for_room"][dd]

                # 運転時間の合計 h
                resultJson["AHU"][ahu_name]["TdAHUc_total"][dd] += resultJson["AHU"][ahu_name]["TdAHUc"]["cooling_for_room"][dd]

            elif resultJson["AHU"][ahu_name]["LdAHUh"]["cooling_for_room"][dd] > 0:  # 空調負荷が負（加熱コイル負荷）である場合

                # 負荷率帯番号
                iL = int(resultJson["AHU"][ahu_name]["LdAHUh"]["cooling_for_room"][dd] - 1)

                # 空調負荷が負（加熱コイル負荷）の時の送風機等の消費電力　MWh
                resultJson["AHU"][ahu_name]["E_fan_h_day"][dd] += \
                    resultJson["AHU"][ahu_name]["energy_consumption_each_LF"][iL] / 1000 * \
                    resultJson["AHU"][ahu_name]["TdAHUh"]["cooling_for_room"][dd]

                # 運転時間の合計 h
                resultJson["AHU"][ahu_name]["TdAHUh_total"][dd] += resultJson["AHU"][ahu_name]["TdAHUh"]["cooling_for_room"][dd]


            ##-----------------------------------
            ## 室負荷が負（暖房要求）である場合：
            ##-----------------------------------
            if resultJson["AHU"][ahu_name]["LdAHUc"]["heating_for_room"][dd] > 0:   # 空調負荷が正（冷却コイル負荷）である場合

                # 負荷率帯番号
                iL = int(resultJson["AHU"][ahu_name]["LdAHUc"]["heating_for_room"][dd] - 1)

                # 空調負荷が正（冷却コイル負荷）の時の送風機等の消費電力　MWh
                resultJson["AHU"][ahu_name]["E_fan_c_day"][dd] += \
                    resultJson["AHU"][ahu_name]["energy_consumption_each_LF"][iL] / 1000 * resultJson["AHU"][ahu_name]["TdAHUc"]["heating_for_room"][dd]

                # 運転時間の合計 h
                resultJson["AHU"][ahu_name]["TdAHUc_total"][dd] += resultJson["AHU"][ahu_name]["TdAHUc"]["heating_for_room"][dd]


            elif resultJson["AHU"][ahu_name]["LdAHUh"]["heating_for_room"][dd] > 0:   # 空調負荷が負（加熱コイル負荷）である場合

                # 負荷率帯番号
                iL = int(resultJson["AHU"][ahu_name]["LdAHUh"]["heating_for_room"][dd] - 1)

                # 空調負荷が負（加熱コイル負荷）の時の送風機等の消費電力　MWh
                resultJson["AHU"][ahu_name]["E_fan_h_day"][dd] += \
                    resultJson["AHU"][ahu_name]["energy_consumption_each_LF"][iL] / 1000 * \
                    resultJson["AHU"][ahu_name]["TdAHUh"]["heating_for_room"][dd]

                # 運転時間の合計 h
                resultJson["AHU"][ahu_name]["TdAHUh_total"][dd] += resultJson["AHU"][ahu_name]["TdAHUh"]["heating_for_room"][dd]


            ##------------------------
            # 空調負荷が正（冷却コイル負荷）のときと負（加熱コイル負荷）のときを合計する。
            ##------------------------
            resultJson["AHU"][ahu_name]["E_fan_day"][dd] = \
                resultJson["AHU"][ahu_name]["E_fan_c_day"][dd] + resultJson["AHU"][ahu_name]["E_fan_h_day"][dd]


    # 合計
    for ahu_name in inputdata["AirHandlingSystem"]:

        # 空調機群（送風機）のエネルギー消費量 MWh
        resultJson["年間エネルギー消費量"]["空調機群ファン[MWh]"] += np.sum(resultJson["AHU"][ahu_name]["E_fan_day"],0)

        # 空調機群（全熱交換器）のエネルギー消費量 MWh
        resultJson["年間エネルギー消費量"]["空調機群全熱交換器[MWh]"] += np.sum(resultJson["AHU"][ahu_name]["E_AHUaex_day"],0)

        # 空調機群（送風機+全熱交換器）のエネルギー消費量 MWh/day
        resultJson["日別エネルギー消費量"]["E_fan_MWh_day"] += \
            resultJson["AHU"][ahu_name]["E_fan_day"] + resultJson["AHU"][ahu_name]["E_AHUaex_day"]

        # ファン発熱量計算用
        resultJson["AHU"][ahu_name]["TcAHU"] = np.sum(resultJson["AHU"][ahu_name]["TdAHUc_total"],0)
        resultJson["AHU"][ahu_name]["ThAHU"] = np.sum(resultJson["AHU"][ahu_name]["TdAHUh_total"],0)
        resultJson["AHU"][ahu_name]["MxAHUcE"] = np.sum(resultJson["AHU"][ahu_name]["E_fan_c_day"],0)
        resultJson["AHU"][ahu_name]["MxAHUhE"] = np.sum(resultJson["AHU"][ahu_name]["E_fan_h_day"],0)

    resultJson["年間エネルギー消費量"]["空調機群ファン[GJ]"]  = resultJson["年間エネルギー消費量"]["空調機群ファン[MWh]"]  * bc.fprime /1000
    resultJson["年間エネルギー消費量"]["空調機群全熱交換器[GJ]"]  = resultJson["年間エネルギー消費量"]["空調機群全熱交換器[MWh]"]  * bc.fprime /1000

    print('空調機群のエネルギー消費量計算完了')


    ##----------------------------------------------------------------------------------
    ## 空調機群計算結果の集約
    ##----------------------------------------------------------------------------------

    for ahu_name in inputdata["AirHandlingSystem"]:

        resultJson["AHU"][ahu_name]["定格能力（冷房）[kW]"] = inputdata["AirHandlingSystem"][ahu_name]["RatedCapacityCooling"]
        resultJson["AHU"][ahu_name]["定格能力（暖房）[kW]"] = inputdata["AirHandlingSystem"][ahu_name]["RatedCapacityHeating"]
        resultJson["AHU"][ahu_name]["定格消費電力[kW]"] = inputdata["AirHandlingSystem"][ahu_name]["FanPowerConsumption_total"]

        cooling_load = 0
        heating_load = 0
        for dd in range(0,365):

            if resultJson["AHU"][ahu_name]["Qahu"]["cooling_for_room"][dd] >= 0:
                cooling_load += resultJson["AHU"][ahu_name]["Qahu"]["cooling_for_room"][dd]
            else:
                heating_load += resultJson["AHU"][ahu_name]["Qahu"]["cooling_for_room"][dd] * (-1)

            if resultJson["AHU"][ahu_name]["Qahu"]["heating_for_room"][dd] >= 0:
                cooling_load += resultJson["AHU"][ahu_name]["Qahu"]["heating_for_room"][dd]
            else:
                heating_load += resultJson["AHU"][ahu_name]["Qahu"]["heating_for_room"][dd] * (-1)

        resultJson["AHU"][ahu_name]["年間空調負荷（冷房）[MJ]"] = cooling_load
        resultJson["AHU"][ahu_name]["年間空調負荷（暖房）[MJ]"] = heating_load

        resultJson["AHU"][ahu_name]["年間空調時間（冷房）[時間]"] = \
            np.sum(resultJson["AHU"][ahu_name]["TdAHUc"]["cooling_for_room"]) + np.sum(resultJson["AHU"][ahu_name]["TdAHUc"]["heating_for_room"])
        resultJson["AHU"][ahu_name]["年間空調時間（暖房）[時間]"] = \
            np.sum(resultJson["AHU"][ahu_name]["TdAHUh"]["cooling_for_room"]) + np.sum(resultJson["AHU"][ahu_name]["TdAHUh"]["heating_for_room"])

        if resultJson["AHU"][ahu_name]["年間空調時間（冷房）[時間]"] != 0:
            resultJson["AHU"][ahu_name]["平均空調負荷（冷房）[kW]"] = \
                resultJson["AHU"][ahu_name]["年間空調負荷（冷房）[MJ]"] * 1000 \
                / (resultJson["AHU"][ahu_name]["年間空調時間（冷房）[時間]"] * 3600)
        else:
            resultJson["AHU"][ahu_name]["平均空調負荷（冷房）[kW]"] = 0

        if resultJson["AHU"][ahu_name]["年間空調時間（暖房）[時間]"] != 0:
            resultJson["AHU"][ahu_name]["平均空調負荷（暖房）[kW]"] = \
                resultJson["AHU"][ahu_name]["年間空調負荷（暖房）[MJ]"] * 1000 \
                / (resultJson["AHU"][ahu_name]["年間空調時間（暖房）[時間]"] * 3600)
        else:
            resultJson["AHU"][ahu_name]["平均空調負荷（暖房）[kW]"] = 0

        if resultJson["AHU"][ahu_name]["定格能力（冷房）[kW]"] != 0:
            resultJson["AHU"][ahu_name]["平均負荷率（冷房）[-]"] = \
                resultJson["AHU"][ahu_name]["平均空調負荷（冷房）[kW]"] / resultJson["AHU"][ahu_name]["定格能力（冷房）[kW]"]
        else:
            resultJson["AHU"][ahu_name]["平均負荷率（冷房）[-]"] = 0

        if resultJson["AHU"][ahu_name]["定格能力（暖房）[kW]"] != 0:
            resultJson["AHU"][ahu_name]["平均負荷率（暖房）[-]"] = \
                resultJson["AHU"][ahu_name]["平均空調負荷（暖房）[kW]"] / resultJson["AHU"][ahu_name]["定格能力（暖房）[kW]"]
        else:
            resultJson["AHU"][ahu_name]["平均負荷率（暖房）[-]"] = 0

        resultJson["AHU"][ahu_name]["電力消費量（送風機、冷房）[MWh]"] = np.sum( resultJson["AHU"][ahu_name]["E_fan_c_day"] )
        resultJson["AHU"][ahu_name]["電力消費量（送風機、暖房）[MWh]"] = np.sum( resultJson["AHU"][ahu_name]["E_fan_h_day"] )
        resultJson["AHU"][ahu_name]["電力消費量（全熱交換器）[MWh]"] = np.sum( resultJson["AHU"][ahu_name]["E_AHUaex_day"] )
        resultJson["AHU"][ahu_name]["電力消費量（合計）[MWh]"] = \
            resultJson["AHU"][ahu_name]["電力消費量（送風機、冷房）[MWh]"] \
            + resultJson["AHU"][ahu_name]["電力消費量（送風機、暖房）[MWh]"]  \
            + resultJson["AHU"][ahu_name]["電力消費量（全熱交換器）[MWh]"]


    if debug: # pragma: no cover

        for ahu_name in inputdata["AirHandlingSystem"]:

            print( f'--- 空調機群名 {ahu_name} ---')
            print( f'空調機群運転時間（冷房） TcAHU {np.sum(resultJson["AHU"][ahu_name]["TcAHU"],0)}' )
            print( f'空調機群運転時間（暖房） ThAHU {np.sum(resultJson["AHU"][ahu_name]["ThAHU"],0)}' )

            print( f'空調機群エネルギー消費量（冷房） MxAHUcE {np.sum(resultJson["AHU"][ahu_name]["MxAHUcE"],0)}' )
            print( f'空調機群エネルギー消費量（暖房） MxAHUcE {np.sum(resultJson["AHU"][ahu_name]["MxAHUhE"],0)}' )

        print( f'空調機群（送風機）のエネルギー消費量: {resultJson["年間エネルギー消費量"]["空調機群ファン[MWh]"]} MWh' )
        print( f'空調機群（全熱交換器）のエネルギー消費量: {resultJson["年間エネルギー消費量"]["空調機群全熱交換器[MWh]"]} MWh' )


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


    for pump_name in inputdata["PUMP"]:

        resultJson["PUMP"][pump_name] = {}
        resultJson["PUMP"][pump_name]["Qpsahu_fan"]       = np.zeros(365)   # ファン発熱量 [MJ/day]
        resultJson["PUMP"][pump_name]["pumpTime_Start"]   = np.zeros(365)
        resultJson["PUMP"][pump_name]["pumpTime_Stop"]    = np.zeros(365)
        resultJson["PUMP"][pump_name]["Qps"] = np.zeros(365)  # ポンプ負荷 [MJ/day]
        resultJson["PUMP"][pump_name]["Tps"] = np.zeros(365)  # ポンプ運転時間 [時間/day]
        resultJson["PUMP"][pump_name]["schedule"] = np.zeros((365,24))  # ポンプ時刻別運転スケジュール
        resultJson["PUMP"][pump_name]["LdPUMP"] = np.zeros(365)    # 負荷率帯
        resultJson["PUMP"][pump_name]["TdPUMP"] = np.zeros(365)    # 運転時間
        resultJson["PUMP"][pump_name]["Qpsahu_pump"] = np.zeros(365)  # ポンプの発熱量 [MJ/day]
        resultJson["PUMP"][pump_name]["E_pump_day"] = np.zeros(365)   # 二次ポンプ群の電力消費量（消費電力×運転時間）[MWh]
        resultJson["PUMP"][pump_name]["TcPUMP"] = 0
        resultJson["PUMP"][pump_name]["MxPUMPE"] = 0

    ##----------------------------------------------------------------------------------
    ## 二次ポンプ機群全体のスペックを整理する。
    ##----------------------------------------------------------------------------------

    for pump_name in inputdata["PUMP"]:

        inputdata["PUMP"][pump_name]["AHU_list"] = set()        # 接続される空調機群
        inputdata["PUMP"][pump_name]["Qpsr"] = 0                # ポンプ定格能力
        inputdata["PUMP"][pump_name]["Vpsr"] = 0                # ポンプ定格流量 [m3/h]
        inputdata["PUMP"][pump_name]["ContolType"] = set()      # 全台回転数制御かどうか（台数制御がない場合のみ有効）
        inputdata["PUMP"][pump_name]["MinOpeningRate"] = 100    # 変流量時最小負荷率の最小値（台数制御がない場合のみ有効）


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

            inputdata["PUMP"][pump_name]["Vpsr"] += inputdata["PUMP"][pump_name]["SecondaryPump"][unit_id]["RatedWaterFlowRate_total"]

            # 消費電力の合計（消費電力×流量）
            inputdata["PUMP"][pump_name]["SecondaryPump"][unit_id]["RatedPowerConsumption_total"] = \
                inputdata["PUMP"][pump_name]["SecondaryPump"][unit_id]["RatedPowerConsumption"] * \
                inputdata["PUMP"][pump_name]["SecondaryPump"][unit_id]["Number"]

            # 二次ポンプ群全体の定格消費電力の合計
            inputdata["PUMP"][pump_name]["RatedPowerConsumption_total"] += \
                inputdata["PUMP"][pump_name]["SecondaryPump"][unit_id]["RatedPowerConsumption_total"]

            # 制御方式
            inputdata["PUMP"][pump_name]["ContolType"].add( inputdata["PUMP"][pump_name]["SecondaryPump"][unit_id]["ContolType"] )

            # 変流量時最小負荷率の最小値（台数制御がない場合のみ有効）
            if unit_configure["MinOpeningRate"] == None or np.isnan( unit_configure["MinOpeningRate"] ) == True:
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
    # for room_zone_name in inputdata["AirConditioningZone"]:

    #     # 冷房（室内負荷処理用空調機）
    #     inputdata["PUMP"][ inputdata["AirConditioningZone"][room_zone_name]["Pump_cooling"] + "_冷房" ]["AHU_list"].add( \
    #         inputdata["AirConditioningZone"][room_zone_name]["AHU_cooling_insideLoad"])
    #     # 冷房（外気負荷処理用空調機）
    #     inputdata["PUMP"][ inputdata["AirConditioningZone"][room_zone_name]["Pump_cooling"] + "_冷房" ]["AHU_list"].add( \
    #         inputdata["AirConditioningZone"][room_zone_name]["AHU_cooling_outdoorLoad"])

    #     # 暖房（室内負荷処理用空調機）
    #     inputdata["PUMP"][ inputdata["AirConditioningZone"][room_zone_name]["Pump_heating"] + "_暖房" ]["AHU_list"].add( \
    #         inputdata["AirConditioningZone"][room_zone_name]["AHU_heating_insideLoad"])
    #     # 暖房（外気負荷処理用空調機）
    #     inputdata["PUMP"][ inputdata["AirConditioningZone"][room_zone_name]["Pump_heating"] + "_暖房" ]["AHU_list"].add( \
    #         inputdata["AirConditioningZone"][room_zone_name]["AHU_heating_outdoorLoad"])

    for ahu_name in inputdata["AirHandlingSystem"]:

        inputdata["PUMP"][ inputdata["AirHandlingSystem"][ahu_name]["Pump_cooling"] + "_冷房" ]["AHU_list"].add(ahu_name)
        inputdata["PUMP"][ inputdata["AirHandlingSystem"][ahu_name]["Pump_heating"] + "_暖房" ]["AHU_list"].add(ahu_name)



    ##----------------------------------------------------------------------------------
    ## 二次ポンプ負荷（解説書 2.6.1）
    ##----------------------------------------------------------------------------------

    # 未処理負荷の算出
    for ahu_name in inputdata["AirHandlingSystem"]:

        for dd in range(0,365):

            if ac_mode[dd] == "暖房":  ## 暖房期である場合

                # 室負荷が冷房要求である場合において空調負荷が正の値である場合、かつ、冷暖同時供給が無い場合
                if (resultJson["AHU"][ahu_name]["Qahu"]["cooling_for_room"][dd] > 0) and \
                    (inputdata["AirHandlingSystem"][ahu_name]["isSimultaneousSupply_heating"] == "無"):

                    resultJson["AHU"][ahu_name]["Qahu_remainC"][dd] += ( resultJson["AHU"][ahu_name]["Qahu"]["cooling_for_room"][dd] )
                    resultJson["AHU"][ahu_name]["Qahu"]["cooling_for_room"][dd] = 0

                # 室負荷が暖房要求である場合において空調負荷が正の値である場合、かつ、冷暖同時供給が無い場合
                if (resultJson["AHU"][ahu_name]["Qahu"]["heating_for_room"][dd] > 0) and \
                    (inputdata["AirHandlingSystem"][ahu_name]["isSimultaneousSupply_heating"] == "無"):

                    resultJson["AHU"][ahu_name]["Qahu_remainC"][dd] += ( resultJson["AHU"][ahu_name]["Qahu"]["heating_for_room"][dd] )
                    resultJson["AHU"][ahu_name]["Qahu"]["heating_for_room"][dd] = 0

            elif (ac_mode[dd] == "冷房") or (ac_mode[dd] == "中間"):

                # 室負荷が冷房要求である場合において空調負荷が負の値である場合、かつ、冷暖同時供給が無い場合
                if (resultJson["AHU"][ahu_name]["Qahu"]["cooling_for_room"][dd] < 0) and \
                    (inputdata["AirHandlingSystem"][ahu_name]["isSimultaneousSupply_cooling"] == "無"):

                    resultJson["AHU"][ahu_name]["Qahu_remainH"][dd] += (-1)*( resultJson["AHU"][ahu_name]["Qahu"]["cooling_for_room"][dd] )
                    resultJson["AHU"][ahu_name]["Qahu"]["cooling_for_room"][dd] = 0

                # 室負荷が暖房要求である場合において空調負荷が負の値である場合、かつ、冷暖同時供給が無い場合
                if (resultJson["AHU"][ahu_name]["Qahu"]["heating_for_room"][dd] < 0) and \
                    (inputdata["AirHandlingSystem"][ahu_name]["isSimultaneousSupply_cooling"] == "無"):

                    resultJson["AHU"][ahu_name]["Qahu_remainH"][dd] += (-1)*( resultJson["AHU"][ahu_name]["Qahu"]["heating_for_room"][dd] )
                    resultJson["AHU"][ahu_name]["Qahu"]["heating_for_room"][dd] = 0


    # ポンプ負荷の積算
    for pump_name in inputdata["PUMP"]:

        for ahu_name in inputdata["PUMP"][pump_name]["AHU_list"]:

            for dd in range(0,365):

                if inputdata["PUMP"][pump_name]["mode"] == "cooling":  # 冷水ポンプの場合

                    # ファン発熱量 Qpsahu_fan [MJ/day] の算出（解説書 2.5.10）
                    tmpC = 0
                    tmpH = 0

                    if inputdata["AirHandlingSystem"][ahu_name]["AHU_type"] == "空調機":

                        # 室負荷が冷房要求である場合において空調負荷が正である場合
                        if resultJson["AHU"][ahu_name]["Qahu"]["cooling_for_room"][dd] > 0:
                            tmpC = k_heatup * resultJson["AHU"][ahu_name]["MxAHUcE"] * \
                                resultJson["AHU"][ahu_name]["Tahu"]["cooling_for_room"][dd] / resultJson["AHU"][ahu_name]["TcAHU"] * 3600

                        # 室負荷が暖房要求である場合において空調負荷が正である場合
                        if resultJson["AHU"][ahu_name]["Qahu"]["heating_for_room"][dd] > 0:
                            tmpH = k_heatup * resultJson["AHU"][ahu_name]["MxAHUhE"] * \
                                resultJson["AHU"][ahu_name]["Tahu"]["heating_for_room"][dd] / resultJson["AHU"][ahu_name]["ThAHU"] * 3600

                    resultJson["PUMP"][pump_name]["Qpsahu_fan"][dd] = tmpC + tmpH


                    ## 日積算ポンプ負荷 Qps [MJ/day] の算出
                    # 室負荷が冷房要求である場合において空調負荷が正である場合
                    if resultJson["AHU"][ahu_name]["Qahu"]["cooling_for_room"][dd] > 0:
                        if resultJson["AHU"][ahu_name]["Economizer"]["Qahu_oac"][dd] > 0: # 外冷時はファン発熱量足さない ⇒ 小さな負荷が出てしまう
                            if abs(resultJson["AHU"][ahu_name]["Qahu"]["cooling_for_room"][dd] - resultJson["AHU"][ahu_name]["Economizer"]["Qahu_oac"][dd]) < 1:
                                resultJson["PUMP"][pump_name]["Qps"][dd] += 0
                            else:
                                resultJson["PUMP"][pump_name]["Qps"][dd] += \
                                    resultJson["AHU"][ahu_name]["Qahu"]["cooling_for_room"][dd] - resultJson["AHU"][ahu_name]["Economizer"]["Qahu_oac"][dd]
                        else:
                            resultJson["PUMP"][pump_name]["Qps"][dd] += \
                                resultJson["AHU"][ahu_name]["Qahu"]["cooling_for_room"][dd] - resultJson["AHU"][ahu_name]["Economizer"]["Qahu_oac"][dd] + resultJson["PUMP"][pump_name]["Qpsahu_fan"][dd]

                    # 室負荷が暖房要求である場合において空調負荷が正である場合
                    if resultJson["AHU"][ahu_name]["Qahu"]["heating_for_room"][dd] > 0:

                        resultJson["PUMP"][pump_name]["Qps"][dd] += \
                            resultJson["AHU"][ahu_name]["Qahu"]["heating_for_room"][dd] - resultJson["AHU"][ahu_name]["Economizer"]["Qahu_oac"][dd] + resultJson["PUMP"][pump_name]["Qpsahu_fan"][dd]


                elif inputdata["PUMP"][pump_name]["mode"] == "heating":

                    # ファン発熱量 Qpsahu_fan [MJ/day] の算出
                    tmpC = 0
                    tmpH = 0

                    if inputdata["AirHandlingSystem"][ahu_name]["AHU_type"] == "空調機":

                        # 室負荷が冷房要求である場合の空調負荷が負である場合
                        if resultJson["AHU"][ahu_name]["Qahu"]["cooling_for_room"][dd] < 0:
                            tmpC = k_heatup * resultJson["AHU"][ahu_name]["MxAHUcE"] * \
                                resultJson["AHU"][ahu_name]["Tahu"]["cooling_for_room"][dd] / resultJson["AHU"][ahu_name]["TcAHU"] * 3600

                        # 室負荷が暖房要求である場合の空調負荷が負である場合
                        if resultJson["AHU"][ahu_name]["Qahu"]["heating_for_room"][dd] < 0:
                            tmpH = k_heatup * resultJson["AHU"][ahu_name]["MxAHUhE"] * \
                                resultJson["AHU"][ahu_name]["Tahu"]["heating_for_room"][dd] / resultJson["AHU"][ahu_name]["ThAHU"] * 3600

                    resultJson["PUMP"][pump_name]["Qpsahu_fan"][dd] = tmpC + tmpH


                    ## 日積算ポンプ負荷 Qps [MJ/day] の算出<符号逆転させる>
                    # 室負荷が冷房要求である場合において空調負荷が正である場合
                    if resultJson["AHU"][ahu_name]["Qahu"]["cooling_for_room"][dd] < 0:

                        resultJson["PUMP"][pump_name]["Qps"][dd] += \
                            (-1) * ( resultJson["AHU"][ahu_name]["Qahu"]["cooling_for_room"][dd] + resultJson["PUMP"][pump_name]["Qpsahu_fan"][dd] )

                    # 室負荷が暖房要求である場合において空調負荷が正である場合
                    if resultJson["AHU"][ahu_name]["Qahu"]["heating_for_room"][dd] < 0:

                        resultJson["PUMP"][pump_name]["Qps"][dd] += \
                            (-1) * ( resultJson["AHU"][ahu_name]["Qahu"]["heating_for_room"][dd] + resultJson["PUMP"][pump_name]["Qpsahu_fan"][dd] )


    ##----------------------------------------------------------------------------------
    ## 二次ポンプ群の運転時間（解説書 2.6.2）
    ##----------------------------------------------------------------------------------

    for pump_name in inputdata["PUMP"]:

        for ahu_name in inputdata["PUMP"][pump_name]["AHU_list"]:

            resultJson["PUMP"][ pump_name ]["schedule"] += resultJson["AHU"][ ahu_name ]["schedule"]

        # 運転スケジュールの和が「1以上（接続されている空調機群の1つは動いている）」であれば、二次ポンプは稼働しているとする。
        resultJson["PUMP"][ pump_name ]["schedule"][ resultJson["PUMP"][ pump_name ]["schedule"] > 1 ] = 1

        # 日積算運転時間
        resultJson["PUMP"][pump_name]["Tps"] = np.sum(resultJson["PUMP"][ pump_name ]["schedule"],1)


    print('ポンプ負荷計算完了')


    if debug: # pragma: no cover

        for ahu_name in inputdata["AirHandlingSystem"]:

            print( f'--- 空調機群名 {ahu_name} ---')

            print( f'未処理負荷（冷房）: {np.sum(resultJson["AHU"][ahu_name]["Qahu_remainC"])} MJ' )
            print( f'未処理負荷（暖房）: {np.sum(resultJson["AHU"][ahu_name]["Qahu_remainH"])} MJ' )

        for pump_name in inputdata["PUMP"]:

            print( f'--- 二次ポンプ群名 {pump_name} ---')

            print( f'二次ポンプ負荷 Qps: {np.sum(resultJson["PUMP"][pump_name]["Qps"],0)}' )
            print( f'二次ポンプ運転時間 Tps: {np.sum(resultJson["PUMP"][pump_name]["Tps"],0)}' )


    ##----------------------------------------------------------------------------------
    ## 二次ポンプ群の仮想定格能力（解説書 2.6.3）
    ##----------------------------------------------------------------------------------
    for pump_name in inputdata["PUMP"]:

        for unit_id, unit_configure in enumerate(inputdata["PUMP"][pump_name]["SecondaryPump"]):

            # 二次ポンプの定格処理能力[kW] = [K] * [m3/h] * [kJ/kg・K] * [kg/m3] * [h/s]
            inputdata["PUMP"][pump_name]["SecondaryPump"][unit_id]["Qpsr"] = \
                inputdata["PUMP"][pump_name]["TemperatureDifference"]* unit_configure["RatedWaterFlowRate_total"] *4.1860*1000/3600

            inputdata["PUMP"][pump_name]["Qpsr"] += inputdata["PUMP"][pump_name]["SecondaryPump"][unit_id]["Qpsr"]
            inputdata["PUMP"][pump_name]["Qpsr_list"].append( inputdata["PUMP"][pump_name]["SecondaryPump"][unit_id]["Qpsr"] )


    ##----------------------------------------------------------------------------------
    ## 二次ポンプ群の負荷率（解説書 2.6.4）
    ##----------------------------------------------------------------------------------

    for pump_name in inputdata["PUMP"]:

        Lpump = np.zeros(365)
        Mxc = np.zeros(365)  # ポンプの負荷率区分
        Tdc = np.zeros(365)  # ポンプの運転時間

        if inputdata["PUMP"][pump_name]["Qpsr"] != 0:   # 仮想ポンプ（二次ポンプがないシステム用の仮想ポンプ）は除く

            for dd in range(0,365):

                if resultJson["PUMP"][pump_name]["Tps"][dd] > 0:
                    # 負荷率 Lpump[-] = [MJ/day] / [h/day] * [kJ/MJ] / [s/h] / [KJ/s]
                    Lpump[dd] = (resultJson["PUMP"][pump_name]["Qps"][dd] / resultJson["PUMP"][pump_name]["Tps"][dd] *1000/3600) \
                        /inputdata["PUMP"][pump_name]["Qpsr"]

            for dd in range(0,365):

                if (resultJson["PUMP"][pump_name]["Tps"][dd] > 0) and (inputdata["PUMP"][pump_name]["Qpsr"] > 0):  # ゼロ割でNaNになっている値を飛ばす

                    if Lpump[dd] > 0:

                        # 出現時間マトリックスを作成
                        iL = count_Matrix(Lpump[dd],mxL)

                        Mxc[dd] = iL
                        Tdc[dd] = resultJson["PUMP"][pump_name]["Tps"][dd]

        resultJson["PUMP"][pump_name]["LdPUMP"] = Mxc
        resultJson["PUMP"][pump_name]["TdPUMP"] = Tdc


    ##----------------------------------------------------------------------------------
    ## 流量制御方式によって定まる係数（解説書 2.6.7）
    ##----------------------------------------------------------------------------------

    for pump_name in inputdata["PUMP"]:

        resultJson["PUMP"][pump_name]["変流量制御の有無"] = "無"

        for unit_id, unit_configure in enumerate(inputdata["PUMP"][pump_name]["SecondaryPump"]):

            if unit_configure["ContolType"] in FLOWCONTROL.keys():

                inputdata["PUMP"][pump_name]["SecondaryPump"][unit_id]["a4"] = FLOWCONTROL[ unit_configure["ContolType"] ]["a4"]
                inputdata["PUMP"][pump_name]["SecondaryPump"][unit_id]["a3"] = FLOWCONTROL[ unit_configure["ContolType"] ]["a3"]
                inputdata["PUMP"][pump_name]["SecondaryPump"][unit_id]["a2"] = FLOWCONTROL[ unit_configure["ContolType"] ]["a2"]
                inputdata["PUMP"][pump_name]["SecondaryPump"][unit_id]["a1"] = FLOWCONTROL[ unit_configure["ContolType"] ]["a1"]
                inputdata["PUMP"][pump_name]["SecondaryPump"][unit_id]["a0"] = FLOWCONTROL[ unit_configure["ContolType"] ]["a0"]

                resultJson["PUMP"][pump_name]["変流量制御の有無"] = "有"

            elif unit_configure["ContolType"] == "無":

                inputdata["PUMP"][pump_name]["SecondaryPump"][unit_id]["a4"] = 0
                inputdata["PUMP"][pump_name]["SecondaryPump"][unit_id]["a3"] = 0
                inputdata["PUMP"][pump_name]["SecondaryPump"][unit_id]["a2"] = 0
                inputdata["PUMP"][pump_name]["SecondaryPump"][unit_id]["a1"] = 0
                inputdata["PUMP"][pump_name]["SecondaryPump"][unit_id]["a0"] = 1
                inputdata["PUMP"][pump_name]["SecondaryPump"][unit_id]["MinOpeningRate"] = 100

            else:
                raise Exception('制御方式が不正です')


    ##----------------------------------------------------------------------------------
    ## 二次ポンプのエネルギー消費量（解説書 2.6.8）
    ##----------------------------------------------------------------------------------

    for pump_name in inputdata["PUMP"]:

        MxPUMPNum = np.zeros(divL)
        MxPUMPPower = np.zeros(divL)
        PUMPvwvfac = np.ones(divL)

        if inputdata["PUMP"][pump_name]["Qpsr"] != 0:   # 仮想ポンプ（二次ポンプがないシステム用の仮想ポンプ）は除く

            if inputdata["PUMP"][pump_name]["isStagingControl"] == "無":    # 台数制御なし

                # 運転台数
                MxPUMPNum = np.ones(divL) * inputdata["PUMP"][pump_name]["number_of_pumps"]

                # 流量制御方式
                if inputdata["PUMP"][pump_name]["ContolType"] == "すべて変流量制御である":  # 全台VWVであれば

                    for iL in range(0,divL):

                        # 最小負荷率による下限を設ける。
                        if aveL[iL] < (inputdata["PUMP"][pump_name]["MinOpeningRate"] /100):
                            tmpL = inputdata["PUMP"][pump_name]["MinOpeningRate"] / 100
                        else:
                            tmpL = aveL[iL]

                        # VWVの効果率曲線(1番目の特性を代表して使う)
                        PUMPvwvfac = np.ones(divL)
                        if aveL[iL] > 1.0:
                            PUMPvwvfac[iL] = 1.2
                        else:
                            PUMPvwvfac[iL] = \
                                inputdata["PUMP"][pump_name]["SecondaryPump"][0]["a4"] * tmpL ** 4 + \
                                inputdata["PUMP"][pump_name]["SecondaryPump"][0]["a3"] * tmpL ** 3 + \
                                inputdata["PUMP"][pump_name]["SecondaryPump"][0]["a2"] * tmpL ** 2 + \
                                inputdata["PUMP"][pump_name]["SecondaryPump"][0]["a1"] * tmpL + \
                                inputdata["PUMP"][pump_name]["SecondaryPump"][0]["a0"]

                else: # 全台VWVでなければ、定流量とみなす。
                    PUMPvwvfac = np.ones(divL)
                    PUMPvwvfac[divL] = 1.2


                # 消費電力（部分負荷特性×定格消費電力）[kW]
                MxPUMPPower = PUMPvwvfac * inputdata["PUMP"][pump_name]["RatedPowerConsumption_total"]


            elif inputdata["PUMP"][pump_name]["isStagingControl"] == "有":   # 台数制御あり

                for iL in range(0,divL):

                    # 負荷区分 iL における処理負荷 [kW]
                    Qpsr_iL  = inputdata["PUMP"][pump_name]["Qpsr"] * aveL[iL]

                    # 運転台数 MxPUMPNum
                    for rr in range(0, inputdata["PUMP"][pump_name]["number_of_pumps"]):

                        # 1台～rr台までの最大能力合計値
                        tmpQmax = np.sum( inputdata["PUMP"][pump_name]["Qpsr_list"][0:rr+1] )

                        if Qpsr_iL < tmpQmax:
                            break

                    MxPUMPNum[iL] = rr+1   # pythonのインデックスと実台数は「1」ずれることに注意。


                    # 定流量ポンプの処理熱量合計、VWVポンプの台数
                    Qtmp_CWV = 0
                    numVWV = MxPUMPNum[iL]  # MxPUMPNum[iL]は、負荷率帯 iL のときの運転台数（定流量＋変流量）

                    for rr in range(0, int(MxPUMPNum[iL])):

                        if (inputdata["PUMP"][pump_name]["SecondaryPump"][rr]["ContolType"] == "無") or \
                            (inputdata["PUMP"][pump_name]["SecondaryPump"][rr]["ContolType"] == "定流量制御"):

                            Qtmp_CWV += inputdata["PUMP"][pump_name]["SecondaryPump"][rr]["Qpsr"]
                            numVWV = numVWV -1


                    # 制御を加味した消費エネルギー MxPUMPPower [kW]
                    for rr in range(0, int(MxPUMPNum[iL])):

                        if (inputdata["PUMP"][pump_name]["SecondaryPump"][rr]["ContolType"] == "無") or \
                            (inputdata["PUMP"][pump_name]["SecondaryPump"][rr]["ContolType"] == "定流量制御"):

                            # 変流量制御の効果率
                            PUMPvwvfac = np.ones(divL)
                            if aveL[iL] > 1.0:
                                PUMPvwvfac[iL] = 1.2

                            if aveL[iL] > 1.0:
                                MxPUMPPower[iL] += inputdata["PUMP"][pump_name]["SecondaryPump"][rr]["RatedPowerConsumption_total"] * PUMPvwvfac[iL]
                            else:
                                MxPUMPPower[iL] += inputdata["PUMP"][pump_name]["SecondaryPump"][rr]["RatedPowerConsumption_total"] * PUMPvwvfac[iL]


                        else:

                            # 変流量ポンプjの負荷率 [-]
                            tmpL = ( (Qpsr_iL - Qtmp_CWV)/numVWV ) / inputdata["PUMP"][pump_name]["SecondaryPump"][rr]["Qpsr"]

                            # 最小流量の制限
                            if tmpL < inputdata["PUMP"][pump_name]["SecondaryPump"][rr]["MinOpeningRate"]/100:
                                tmpL = inputdata["PUMP"][pump_name]["SecondaryPump"][rr]["MinOpeningRate"]/100

                            # 変流量制御による省エネ効果
                            PUMPvwvfac = np.ones(divL)
                            if aveL[iL] > 1.0:
                                PUMPvwvfac[iL] = 1.2
                            else:
                                PUMPvwvfac[iL] = \
                                    inputdata["PUMP"][pump_name]["SecondaryPump"][rr]["a4"] * tmpL ** 4 + \
                                    inputdata["PUMP"][pump_name]["SecondaryPump"][rr]["a3"] * tmpL ** 3 + \
                                    inputdata["PUMP"][pump_name]["SecondaryPump"][rr]["a2"] * tmpL ** 2 + \
                                    inputdata["PUMP"][pump_name]["SecondaryPump"][rr]["a1"] * tmpL + \
                                    inputdata["PUMP"][pump_name]["SecondaryPump"][rr]["a0"]

                            MxPUMPPower[iL] +=  inputdata["PUMP"][pump_name]["SecondaryPump"][rr]["RatedPowerConsumption_total"] * PUMPvwvfac[iL]


        resultJson["PUMP"][pump_name]["MxPUMPNum"]   = MxPUMPNum
        resultJson["PUMP"][pump_name]["MxPUMPPower"] = MxPUMPPower


    ##----------------------------------------------------------------------------------
    ## 二次ポンプ群ごとの消費電力（解説書 2.6.8）
    ##----------------------------------------------------------------------------------

    for pump_name in inputdata["PUMP"]:

        for dd in range(0,365):

            if resultJson["PUMP"][pump_name]["TdPUMP"][dd] > 0:

                resultJson["PUMP"][pump_name]["E_pump_day"][dd] = \
                    resultJson["PUMP"][pump_name]["MxPUMPPower"][ int(resultJson["PUMP"][pump_name]["LdPUMP"][dd])-1 ] / 1000 * \
                    resultJson["PUMP"][pump_name]["TdPUMP"][dd]


    ##----------------------------------------------------------------------------------
    ## 二次ポンプ群全体の年間一次エネルギー消費量（解説書 2.6.10）
    ##----------------------------------------------------------------------------------

    for pump_name in inputdata["PUMP"]:

        resultJson["年間エネルギー消費量"]["二次ポンプ群[MWh]"] += np.sum(resultJson["PUMP"][pump_name]["E_pump_day"], 0)

        resultJson["日別エネルギー消費量"]["E_pump_MWh_day"] += resultJson["PUMP"][pump_name]["E_pump_day"]

        resultJson["PUMP"][pump_name]["TcPUMP"]  = np.sum(resultJson["PUMP"][pump_name]["TdPUMP"], 0)
        resultJson["PUMP"][pump_name]["MxPUMPE"]  = np.sum(resultJson["PUMP"][pump_name]["E_pump_day"], 0)

    resultJson["年間エネルギー消費量"]["二次ポンプ群[GJ]"]  = resultJson["年間エネルギー消費量"]["二次ポンプ群[MWh]"]  * bc.fprime /1000


    print('二次ポンプ群のエネルギー消費量計算完了')


    if debug: # pragma: no cover

        for ahu_name in inputdata["AirHandlingSystem"]:

            print( f'--- 空調機群名 {ahu_name} ---')

            print( f'未処理負荷（冷房）: {np.sum(resultJson["AHU"][ahu_name]["Qahu_remainC"])} MJ' )
            print( f'未処理負荷（暖房）: {np.sum(resultJson["AHU"][ahu_name]["Qahu_remainH"])} MJ' )

        for pump_name in inputdata["PUMP"]:

            print( f'--- 二次ポンプ群名 {pump_name} ---')

            print( f'二次ポンプ群に加算されるファン発熱量 Qpsahu_fan: {np.sum(resultJson["PUMP"][pump_name]["Qpsahu_fan"],0)}' )
            print( f'二次ポンプ群の負荷 Qps: {np.sum(resultJson["PUMP"][pump_name]["Qps"],0)}' )
            print( f'二次ポンプ群の運転時間 Tps: {np.sum(resultJson["PUMP"][pump_name]["Tps"],0)}' )
            print( f'二次ポンプ群の電力消費量 E_pump_day: {np.sum(resultJson["PUMP"][pump_name]["E_pump_day"],0)}' )

        print( f'二次ポンプ群のエネルギー消費量 E_pump: {resultJson["年間エネルギー消費量"]["二次ポンプ群[MWh]"]} MWh' )



    ##----------------------------------------------------------------------------------
    ## 二次ポンプ群の発熱量 （解説書 2.6.9）
    ##----------------------------------------------------------------------------------

    for pump_name in inputdata["PUMP"]:

        if resultJson["PUMP"][pump_name]["TcPUMP"] > 0:

            for dd in range(0,365):

                # 二次ポンプ群の発熱量 MJ/day
                resultJson["PUMP"][pump_name]["Qpsahu_pump"][dd] = \
                    resultJson["PUMP"][pump_name]["MxPUMPE"] * k_heatup / resultJson["PUMP"][pump_name]["TcPUMP"] \
                    * resultJson["PUMP"][pump_name]["Tps"][dd] * 3600

        if debug: # pragma: no cover
            print( f'--- 二次ポンプ群名 {pump_name} ---')
            print( f'二次ポンプ群のポンプ発熱量 Qpsahu_fan: {np.sum(resultJson["PUMP"][pump_name]["Qpsahu_pump"],0)}' )


    ##----------------------------------------------------------------------------------
    ## 二次ポンプ群計算結果の集約
    ##----------------------------------------------------------------------------------

    for pump_name in inputdata["PUMP"]:

        if pump_name.startswith("dummyPump") == False:

            if inputdata["PUMP"][pump_name]["mode"] == "cooling":
                resultJson["PUMP"][pump_name]["運転モード"] = "冷房"
            elif inputdata["PUMP"][pump_name]["mode"] == "heating":
                resultJson["PUMP"][pump_name]["運転モード"] = "暖房"
            else:
                raise Exception("運転モードが不正です")

            resultJson["PUMP"][pump_name]["台数"] = inputdata["PUMP"][pump_name]["number_of_pumps"]

            resultJson["PUMP"][pump_name]["定格能力[kW]"] = inputdata["PUMP"][pump_name]["Qpsr"]
            resultJson["PUMP"][pump_name]["定格消費電力[kW]"] = inputdata["PUMP"][pump_name]["RatedPowerConsumption_total"]
            resultJson["PUMP"][pump_name]["定格流量[m3/h]"] = inputdata["PUMP"][pump_name]["Vpsr"]

            resultJson["PUMP"][pump_name]["運転時間[時間]"] = np.sum(resultJson["PUMP"][pump_name]["Tps"],0)
            resultJson["PUMP"][pump_name]["年間処理熱量[MJ]"] = np.sum(resultJson["PUMP"][pump_name]["Qps"],0)
            resultJson["PUMP"][pump_name]["平均処理熱量[kW]"] = \
                resultJson["PUMP"][pump_name]["年間処理熱量[MJ]"] * 1000 \
                / (resultJson["PUMP"][pump_name]["運転時間[時間]"] * 3600)

            resultJson["PUMP"][pump_name]["平均負荷率[-]"] = resultJson["PUMP"][pump_name]["平均処理熱量[kW]"] / resultJson["PUMP"][pump_name]["定格能力[kW]"]

            resultJson["PUMP"][pump_name]["台数制御の有無"] = inputdata["PUMP"][pump_name]["isStagingControl"]
            resultJson["PUMP"][pump_name]["電力消費量[MWh]"] = np.sum(resultJson["PUMP"][pump_name]["E_pump_day"], 0)


    ##----------------------------------------------------------------------------------
    ## 熱源群の一次エネルギー消費量（解説書 2.7）
    ##----------------------------------------------------------------------------------

    # モデル格納用変数

    # 冷房と暖房の熱源群に分ける。
    for ref_original_name in inputdata["HeatsourceSystem"]:

        if "冷房" in inputdata["HeatsourceSystem"][ref_original_name]:

            if len(inputdata["HeatsourceSystem"][ref_original_name]["冷房"]["Heatsource"]) > 0:

                inputdata["REF"][ ref_original_name + "_冷房"] = inputdata["HeatsourceSystem"][ref_original_name]["冷房"]
                inputdata["REF"][ ref_original_name + "_冷房"]["mode"] = "cooling"

                if "冷房(蓄熱)" in inputdata["HeatsourceSystem"][ref_original_name]:
                    inputdata["REF"][ ref_original_name + "_冷房_蓄熱"] = inputdata["HeatsourceSystem"][ref_original_name]["冷房(蓄熱)"]
                    inputdata["REF"][ ref_original_name + "_冷房_蓄熱"]["isStorage"] = "蓄熱"
                    inputdata["REF"][ ref_original_name + "_冷房_蓄熱"]["mode"] = "cooling"
                    inputdata["REF"][ ref_original_name + "_冷房"]["isStorage"] = "追掛"
                    inputdata["REF"][ ref_original_name + "_冷房"]["StorageType"] = inputdata["HeatsourceSystem"][ref_original_name]["冷房(蓄熱)"]["StorageType"]
                    inputdata["REF"][ ref_original_name + "_冷房"]["StorageSize"] = inputdata["HeatsourceSystem"][ref_original_name]["冷房(蓄熱)"]["StorageSize"]
                else:
                    inputdata["REF"][ ref_original_name + "_冷房"]["isStorage"] = "無"


        if "暖房" in inputdata["HeatsourceSystem"][ref_original_name]:

            if len(inputdata["HeatsourceSystem"][ref_original_name]["暖房"]["Heatsource"]) > 0:

                inputdata["REF"][ ref_original_name + "_暖房"] = inputdata["HeatsourceSystem"][ref_original_name]["暖房"]
                inputdata["REF"][ ref_original_name + "_暖房"]["mode"] = "heating"

                if "暖房(蓄熱)" in inputdata["HeatsourceSystem"][ref_original_name]:
                    inputdata["REF"][ ref_original_name + "_暖房_蓄熱"] = inputdata["HeatsourceSystem"][ref_original_name]["暖房(蓄熱)"]
                    inputdata["REF"][ ref_original_name + "_暖房_蓄熱"]["isStorage"] = "蓄熱"
                    inputdata["REF"][ ref_original_name + "_暖房_蓄熱"]["mode"] = "heating"
                    inputdata["REF"][ ref_original_name + "_暖房"]["isStorage"] = "追掛"
                    inputdata["REF"][ ref_original_name + "_暖房"]["StorageType"] = inputdata["HeatsourceSystem"][ref_original_name]["暖房(蓄熱)"]["StorageType"]
                    inputdata["REF"][ ref_original_name + "_暖房"]["StorageSize"] = inputdata["HeatsourceSystem"][ref_original_name]["暖房(蓄熱)"]["StorageSize"]
                else:
                    inputdata["REF"][ ref_original_name + "_暖房"]["isStorage"] = "無"


    ##----------------------------------------------------------------------------------
    ## 蓄熱がある場合の処理（蓄熱槽効率の追加、追掛用熱交換器の検証）
    ##----------------------------------------------------------------------------------

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
                            "HeatsourceRatedCapacity": inputdata["REF"][ref_name]["storageEffratio"] * inputdata["REF"][ref_name]["StorageSize"] /8*(1000/3600),
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

    ##----------------------------------------------------------------------------------
    ## 熱源群全体のスペックを整理する。
    ##----------------------------------------------------------------------------------

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

            tmpCapacity = inputdata["REF"][ref_name]["storageEffratio"] * inputdata["REF"][ref_name]["StorageSize"] /8*(1000/3600)

            # 1台目は必ず熱交換器であると想定
            if inputdata["REF"][ref_name]["Heatsource"][0]["HeatsourceRatedCapacity_total"] > tmpCapacity:
                inputdata["REF"][ref_name]["Heatsource"][0]["HeatsourceRatedCapacity_total"] = tmpCapacity


    # 接続される二次ポンプ群

    for ahu_name in inputdata["AirHandlingSystem"]:

        if inputdata["AirHandlingSystem"][ahu_name]["HeatSource_cooling"] + "_冷房" in inputdata["REF"]:

            # 冷房熱源群（蓄熱なし）
            inputdata["REF"][ inputdata["AirHandlingSystem"][ahu_name]["HeatSource_cooling"] + "_冷房" ]["pump_list"].add( \
                inputdata["AirHandlingSystem"][ahu_name]["Pump_cooling"] + "_冷房")

            # 冷房熱源群（蓄熱あり）
            if inputdata["REF"][ inputdata["AirHandlingSystem"][ahu_name]["HeatSource_cooling"] + "_冷房" ]["isStorage"] == "追掛":
                inputdata["REF"][ inputdata["AirHandlingSystem"][ahu_name]["HeatSource_cooling"] + "_冷房_蓄熱" ]["pump_list"].add( \
                    inputdata["AirHandlingSystem"][ahu_name]["Pump_cooling"] + "_冷房")

        if inputdata["AirHandlingSystem"][ahu_name]["HeatSource_heating"] + "_暖房" in inputdata["REF"]:

            # 暖房熱源群（蓄熱なし）
            inputdata["REF"][ inputdata["AirHandlingSystem"][ahu_name]["HeatSource_heating"] + "_暖房" ]["pump_list"].add( \
                inputdata["AirHandlingSystem"][ahu_name]["Pump_heating"] + "_暖房")

            # 暖房熱源群（蓄熱あり）
            if inputdata["REF"][ inputdata["AirHandlingSystem"][ahu_name]["HeatSource_heating"] + "_暖房" ]["isStorage"] == "追掛":
                inputdata["REF"][ inputdata["AirHandlingSystem"][ahu_name]["HeatSource_heating"] + "_暖房_蓄熱" ]["pump_list"].add( \
                    inputdata["AirHandlingSystem"][ahu_name]["Pump_heating"] + "_暖房")

    ##----------------------------------------------------------------------------------
    ## 結果格納用変数
    ##----------------------------------------------------------------------------------

    for ref_name in inputdata["REF"]:

        resultJson["REF"][ref_name] = {}
        resultJson["REF"][ref_name]["schedule"]      = np.zeros((365,24)) # 運転スケジュール
        resultJson["REF"][ref_name]["Qref"]          = np.zeros(365)      # 日積算熱源負荷 [MJ/Day]
        resultJson["REF"][ref_name]["Tref"]          = np.zeros(365)      # 日積算運転時間
        resultJson["REF"][ref_name]["Qref_kW"]       = np.zeros(365)      # 熱源平均負荷 kW
        resultJson["REF"][ref_name]["Qref_OVER"]     = np.zeros(365)      # 過負荷分
        resultJson["REF"][ref_name]["ghsp_Rq"]       = 0                  # 冷房負荷と暖房負荷の比率（地中熱ヒートポンプ用）
        resultJson["REF"][ref_name]["E_ref_day"]     = np.zeros(365)      # 熱源群エネルギー消費量 [MJ]
        resultJson["REF"][ref_name]["E_ref_day_MWh"] = np.zeros(365)      # 熱源主機電力消費量 [MWh]
        resultJson["REF"][ref_name]["E_ref_ACc_day"] = np.zeros(365)      # 補機電力 [MWh]
        resultJson["REF"][ref_name]["E_PPc_day"]     = np.zeros(365)      # 一次ポンプ電力 [MWh]
        resultJson["REF"][ref_name]["E_CTfan_day"]   = np.zeros(365)      # 冷却塔ファン電力 [MWh]
        resultJson["REF"][ref_name]["E_CTpump_day"]  = np.zeros(365)      # 冷却水ポンプ電力 [MWh]

        resultJson["REF"][ref_name]["Heatsource"]    = {}
        for unit_id, unit_configure in enumerate(inputdata["REF"][ref_name]["Heatsource"]):

            # 熱源群に属する各熱源機器の値
            resultJson["REF"][ref_name]["Heatsource"][unit_id] = {}
            resultJson["REF"][ref_name]["Heatsource"][unit_id]["E_ref_main"]  = np.zeros(365)
            resultJson["REF"][ref_name]["Heatsource"][unit_id]["E_ref_day_per_unit"] = np.zeros(365)
            resultJson["REF"][ref_name]["Heatsource"][unit_id]["E_ref_day_per_unit_MWh"] = np.zeros(365)


    ##----------------------------------------------------------------------------------
    ## 熱源群の定格能力 （解説書 2.7.5）
    ##----------------------------------------------------------------------------------
    # 熱源群の合計定格能力
    for ref_name in inputdata["REF"]:
        inputdata["REF"][ref_name]["Qref_rated"] = 0
        for unit_id, unit_configure in enumerate(inputdata["REF"][ref_name]["Heatsource"]):
            inputdata["REF"][ref_name]["Qref_rated"] += inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedCapacity_total"]


    ##----------------------------------------------------------------------------------
    ## 蓄熱槽の熱損失 （解説書 2.7.1）
    ##----------------------------------------------------------------------------------

    for ref_name in inputdata["REF"]:

        # 蓄熱の場合: 熱損失量 [MJ/day] を足す。損失量は 蓄熱槽容量の3%。
        if inputdata["REF"][ref_name]["isStorage"] == "蓄熱":
            resultJson["REF"][ref_name]["Qref_thermal_loss"] = inputdata["REF"][ref_name]["StorageSize"] * 0.03
        else:
            resultJson["REF"][ref_name]["Qref_thermal_loss"] = 0


    ##----------------------------------------------------------------------------------
    ## 熱源負荷の算出（解説書 2.7.2）
    ##----------------------------------------------------------------------------------

    for ref_name in inputdata["REF"]:

        for dd in range(0,365):

            if inputdata["REF"][ref_name]["mode"] == "cooling": # 冷熱生成用熱源

                for pump_name in inputdata["REF"][ref_name]["pump_list"]:

                    if resultJson["PUMP"][pump_name]["Qps"][dd] > 0:

                        # 日積算熱源負荷  [MJ/day]
                        resultJson["REF"][ref_name]["Qref"][dd] += \
                            resultJson["PUMP"][pump_name]["Qps"][dd] + resultJson["PUMP"][pump_name]["Qpsahu_pump"][dd]


            elif inputdata["REF"][ref_name]["mode"] == "heating": # 温熱生成用熱源

                for pump_name in inputdata["REF"][ref_name]["pump_list"]:

                    if ( resultJson["PUMP"][pump_name]["Qps"][dd] + \
                        (-1) * resultJson["PUMP"][pump_name]["Qpsahu_pump"][dd] ) > 0:

                        resultJson["REF"][ref_name]["Qref"][dd] += \
                            resultJson["PUMP"][pump_name]["Qps"][dd] + (-1) * resultJson["PUMP"][pump_name]["Qpsahu_pump"][dd]


            # 蓄熱の場合: 熱損失量 [MJ/day] を足す。損失量は 蓄熱槽容量の3%。（MATLAB版では Tref>0で判定）
            if (resultJson["REF"][ref_name]["Qref"][dd] != 0) and (inputdata["REF"][ref_name]["isStorage"] == "蓄熱"):

                resultJson["REF"][ref_name]["Qref"][dd] += resultJson["REF"][ref_name]["Qref_thermal_loss"]

                # 蓄熱処理追加（蓄熱槽容量以上の負荷を処理しないようにする）
                if resultJson["REF"][ref_name]["Qref"][dd] > \
                    inputdata["REF"][ref_name]["storageEffratio"] * inputdata["REF"][ref_name]["StorageSize"]:

                    resultJson["REF"][ref_name]["Qref"][dd] = \
                        inputdata["REF"][ref_name]["storageEffratio"] * inputdata["REF"][ref_name]["StorageSize"]


    ##----------------------------------------------------------------------------------
    ## 熱源群の運転時間（解説書 2.7.3）
    ##----------------------------------------------------------------------------------

    for ref_name in inputdata["REF"]:

        for pump_name in inputdata["REF"][ref_name]["pump_list"]:

            resultJson["REF"][ref_name]["schedule"] += resultJson["PUMP"][ pump_name ]["schedule"]

        # 運転スケジュールの和が「1以上（接続されている二次ポンプ群の1つは動いている）」であれば、熱源群は稼働しているとする。
        resultJson["REF"][ref_name]["schedule"][ resultJson["REF"][ref_name]["schedule"] > 1 ] = 1

        # 日積算運転時間（熱源負荷が0より大きい場合のみ積算する）
        for dd in range(0,365):
            if resultJson["REF"][ref_name]["Qref"][dd] > 0:
                resultJson["REF"][ref_name]["Tref"][dd] = np.sum(resultJson["REF"][ref_name]["schedule"][dd])


        # 日平均負荷[kW] と 過負荷[MJ/day] を求める。（検証用）
        for dd in range(0,365):
            # 平均負荷 [kW]
            if resultJson["REF"][ref_name]["Tref"][dd] == 0:
                resultJson["REF"][ref_name]["Qref_kW"][dd] = 0
            else:
                resultJson["REF"][ref_name]["Qref_kW"][dd] = resultJson["REF"][ref_name]["Qref"][dd] / resultJson["REF"][ref_name]["Tref"][dd] *1000 /3600


            # 過負荷分を集計 [MJ/day]
            if resultJson["REF"][ref_name]["Qref_kW"][dd] > inputdata["REF"][ref_name]["Qref_rated"]:

                resultJson["REF"][ref_name]["Qref_OVER"][dd] = \
                    (resultJson["REF"][ref_name]["Qref_kW"][dd] -inputdata["REF"][ref_name]["Qref_rated"] ) * \
                    resultJson["REF"][ref_name]["Tref"][dd]*3600/1000


    print('熱源負荷計算完了')


    if debug: # pragma: no cover

        for ref_name in inputdata["REF"]:

            print( f'--- 熱源群名 {ref_name} ---')

            print( f'熱源群の熱源負荷 Qref: {np.sum(resultJson["REF"][ref_name]["Qref"],0)}' )
            print( f'熱源群の平均負荷 Qref_kW: {np.sum(resultJson["REF"][ref_name]["Qref_kW"],0)}' )
            print( f'熱源群の過負荷 Qref_OVER: {np.sum(resultJson["REF"][ref_name]["Qref_OVER"],0)}' )
            print( f'熱源群の運転時間 Tref: {np.sum(resultJson["REF"][ref_name]["Tref"],0)}' )

    ##----------------------------------------------------------------------------------
    ## 熱源機器の特性の読み込み（解説書 附属書A.4）
    ##----------------------------------------------------------------------------------

    for ref_name in inputdata["REF"]:

        inputdata["REF"][ref_name]["Eref_rated_primary"] = 0

        inputdata["REF"][ref_name]["checkCTVWV"] = 0   # 冷却水変流量の有無
        inputdata["REF"][ref_name]["checkGEGHP"] = 0   # 発電機能の有無

        for unit_id, unit_configure in enumerate(inputdata["REF"][ref_name]["Heatsource"]):

            if "冷却水変流量" in unit_configure["HeatsourceType"]:
                inputdata["REF"][ref_name]["checkCTVWV"] = 1

            if "消費電力自給装置" in unit_configure["HeatsourceType"]:
                inputdata["REF"][ref_name]["checkGEGHP"] = 1

            # 特性を全て抜き出す。
            refParaSetALL = HeatSourcePerformance[ unit_configure["HeatsourceType"] ]

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
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["Eref_rated_primary"] = (bc.fprime/3600) * inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedPowerConsumption_total"]
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
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedFuelConsumption_total"] = inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedCapacity_total"]
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["Eref_rated_primary"] = \
                    (inputdata["Building"]["Coefficient_DHC"]["Heating"]) * inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedCapacity_total"]
            elif fuel_type == "温水":
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["refInputType"] = 7
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedFuelConsumption_total"] = inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedCapacity_total"]
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["Eref_rated_primary"] = \
                    (inputdata["Building"]["Coefficient_DHC"]["Heating"])*inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedCapacity_total"]
            elif fuel_type == "冷水":
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["refInputType"] = 8
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedFuelConsumption_total"] = inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedCapacity_total"]
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["Eref_rated_primary"] = \
                    (inputdata["Building"]["Coefficient_DHC"]["Cooling"])*inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedCapacity_total"]

            # 熱源群ごとに積算
            inputdata["REF"][ref_name]["Eref_rated_primary"] += inputdata["REF"][ref_name]["Heatsource"][unit_id]["Eref_rated_primary"]


    ##----------------------------------------------------------------------------------
    ## 蓄熱槽からの放熱を加味した補正定格能力 （解説書 2.7.6）
    ##----------------------------------------------------------------------------------

    # 蓄熱槽がある場合の放熱用熱交換器の容量の補正
    for ref_name in inputdata["REF"]:

        hex_capacity = 0

        if inputdata["REF"][ref_name]["isStorage"] == "追掛":
            if inputdata["REF"][ref_name]["Heatsource"][0]["HeatsourceType"] == "熱交換器":

                # 熱源運転時間の最大値で補正した容量
                hex_capacity = inputdata["REF"][ref_name]["Heatsource"][0]["HeatsourceRatedCapacity_total"] * \
                    (8 / np.max(resultJson["REF"][ref_name]["Tref"]))

                # 定格容量の合計値を更新
                inputdata["REF"][ref_name]["Qref_rated"] = \
                    inputdata["REF"][ref_name]["Qref_rated"] + \
                    hex_capacity - inputdata["REF"][ref_name]["Heatsource"][0]["HeatsourceRatedCapacity_total"]

                # 熱交換器の容量を修正
                inputdata["REF"][ref_name]["Heatsource"][0]["HeatsourceRatedCapacity_total"] = hex_capacity

            else:
                raise Exception('熱交換機が設定されていません')

            if debug: # pragma: no cover

                print( f'--- 熱源群名 {ref_name} ---')
                print( f'熱交換器の容量: {inputdata["REF"][ref_name]["Heatsource"][0]["HeatsourceRatedCapacity_total"]}')
                print( f'熱源群の定格能力の合計 Qref_rated: {inputdata["REF"][ref_name]["Qref_rated"]}' )


    ##----------------------------------------------------------------------------------
    ## 熱源群の負荷率（解説書 2.7.7）
    ##----------------------------------------------------------------------------------

    for ref_name in inputdata["REF"]:

        resultJson["REF"][ref_name]["Lref"] = np.zeros(365)      # 日積算熱源負荷 [MJ/Day] の 定格能力に対する比率（熱源定格負荷率）

        for dd in range(0,365):

            # 負荷率の算出 [-]
            if resultJson["REF"][ref_name]["Tref"][dd] > 0:

                # 熱源定格負荷率（定格能力に対する比率
                resultJson["REF"][ref_name]["Lref"][dd] = \
                    (resultJson["REF"][ref_name]["Qref"][dd] / resultJson["REF"][ref_name]["Tref"][dd] *1000/3600) / \
                    inputdata["REF"][ref_name]["Qref_rated"]

            if np.isnan(resultJson["REF"][ref_name]["Lref"][dd]) == True:
                resultJson["REF"][ref_name]["Lref"][dd] = 0


    ##----------------------------------------------------------------------------------
    ## 熱源群のマトリックスIDの指定
    ##----------------------------------------------------------------------------------

    for ref_name in inputdata["REF"]:

        resultJson["REF"][ref_name]["matrix_iL"] = np.zeros(365)      # 熱源の負荷率区分
        resultJson["REF"][ref_name]["matrix_iT"] = np.zeros(365)      # 熱源の温度区分

        for dd in range(0,365):

            if resultJson["REF"][ref_name]["Lref"][dd] > 0:

                # 負荷率帯マトリックス
                resultJson["REF"][ref_name]["matrix_iL"][dd] = count_Matrix(resultJson["REF"][ref_name]["Lref"][dd], mxL)

                # 外気温帯マトリックス
                if inputdata["REF"][ref_name]["mode"] == "cooling":
                    resultJson["REF"][ref_name]["matrix_iT"][dd] = count_Matrix(Toa_ave[dd], mxTC)
                elif inputdata["REF"][ref_name]["mode"] == "heating":
                    resultJson["REF"][ref_name]["matrix_iT"][dd] = count_Matrix(Toa_ave[dd], mxTH)


    #----------------------------------------------------------------------------------
    # 蓄熱システムによる外気温帯の補正
    #----------------------------------------------------------------------------------

    for ref_name in inputdata["REF"]:

        if inputdata["REF"][ref_name]["isStorage"] == "蓄熱":

            for dd in range(0,365):

                if resultJson["REF"][ref_name]["matrix_iT"][dd] > 1:
                    resultJson["REF"][ref_name]["matrix_iT"][dd] = resultJson["REF"][ref_name]["matrix_iT"][dd] - 1   # 外気温帯を1つ下げる。
                elif resultJson["REF"][ref_name]["matrix_iT"][dd] == 1:
                    resultJson["REF"][ref_name]["matrix_iT"][dd] = resultJson["REF"][ref_name]["matrix_iT"][dd]



    ##----------------------------------------------------------------------------------
    ## 湿球温度 （解説書 2.7.4.2）
    ##----------------------------------------------------------------------------------

    ToawbC = Area[inputdata["Building"]["Region"]+"地域"]["湿球温度係数_冷房a1"] * ToadbC + Area[inputdata["Building"]["Region"]+"地域"]["湿球温度係数_冷房a0"]
    ToawbH = Area[inputdata["Building"]["Region"]+"地域"]["湿球温度係数_暖房a1"] * ToadbH + Area[inputdata["Building"]["Region"]+"地域"]["湿球温度係数_暖房a0"]

    # 保存用
    resultJson["Matrix"]["ToawbC"] = ToawbC
    resultJson["Matrix"]["ToawbH"] = ToawbH


    ##----------------------------------------------------------------------------------
    ## 冷却水温度 （解説書 2.7.4.3）
    ##----------------------------------------------------------------------------------

    TctwC  = ToawbC + 3  # 冷却水温度 [℃]
    TctwH  = 15.5 * np.ones(6)  #  水冷式の暖房時熱源水温度（暫定） [℃]

    # 保存用
    resultJson["Matrix"]["TctwC"]  = TctwC
    resultJson["Matrix"]["TctwH"]  = TctwH


    ##----------------------------------------------------------------------------------
    ## 地中熱交換器（クローズドループ）からの熱源水温度 （解説書 2.7.4.4）
    ##----------------------------------------------------------------------------------

    # 地中熱ヒートポンプ用係数
    gshp_ah = [8.0278, 13.0253, 16.7424, 19.3145, 21.2833]   # 地盤モデル：暖房時パラメータa
    gshp_bh = [-1.1462, -1.8689, -2.4651, -3.091, -3.8325]   # 地盤モデル：暖房時パラメータb
    gshp_ch = [-0.1128, -0.1846, -0.2643, -0.2926, -0.3474]  # 地盤モデル：暖房時パラメータc
    gshp_dh = [0.1256, 0.2023, 0.2623, 0.3085, 0.3629]       # 地盤モデル：暖房時パラメータd
    gshp_ac = [8.0633, 12.6226, 16.1703, 19.6565, 21.8702]   # 地盤モデル：冷房時パラメータa
    gshp_bc = [2.9083, 4.7711, 6.3128, 7.8071, 9.148]        # 地盤モデル：冷房時パラメータb
    gshp_cc = [0.0613, 0.0568, 0.1027, 0.1984, 0.249]        # 地盤モデル：冷房時パラメータc
    gshp_dc = [0.2178, 0.3509, 0.4697, 0.5903, 0.7154]       # 地盤モデル：冷房時パラメータd

    ghspToa_ave = [5.8, 7.5, 10.2, 11.6, 13.3, 15.7, 17.4, 22.7] # 地盤モデル：年平均外気温
    gshpToa_h   = [-3, -0.8, 0, 1.1, 3.6, 6, 9.3, 17.5]          # 地盤モデル：暖房時平均外気温
    gshpToa_c   = [16.8,17,18.9,19.6,20.5,22.4,22.1,24.6]        # 地盤モデル：冷房時平均外気温


    # 冷暖房比率 ghsp_Rq
    for ref_original_name in inputdata["HeatsourceSystem"]:

        Qcmax = 0
        if "冷房" in inputdata["HeatsourceSystem"][ref_original_name]:
            if len(inputdata["HeatsourceSystem"][ref_original_name]["冷房"]["Heatsource"]) > 0:
                Qcmax =  np.max( resultJson["REF"][ref_original_name + "_冷房"]["Qref"] , 0)

        Qhmax = 0
        if "暖房" in inputdata["HeatsourceSystem"][ref_original_name]:
            if len(inputdata["HeatsourceSystem"][ref_original_name]["暖房"]["Heatsource"]) > 0:
                Qhmax =  np.max( resultJson["REF"][ref_original_name + "_暖房"]["Qref"] , 0)

        if Qcmax != 0 and Qhmax != 0:

            resultJson["REF"][ref_original_name + "_冷房"]["ghsp_Rq"] = (Qcmax-Qhmax)/(Qcmax+Qhmax)
            resultJson["REF"][ref_original_name + "_暖房"]["ghsp_Rq"] = (Qcmax-Qhmax)/(Qcmax+Qhmax)

        elif Qcmax == 0 and Qhmax != 0:
            resultJson["REF"][ref_original_name + "_暖房"]["ghsp_Rq"] = 0

        elif Qcmax != 0 and Qhmax == 0:
            resultJson["REF"][ref_original_name + "_冷房"]["ghsp_Rq"] = 0


    ##----------------------------------------------------------------------------------
    ## 熱源水等の温度 matrix_T （解説書 2.7.4）
    ##----------------------------------------------------------------------------------

    # 地中熱オープンループの地盤特性の読み込み
    with open(database_directory + 'AC_gshp_openloop.json', 'r', encoding='utf-8') as f:
        AC_gshp_openloop = json.load(f)

    for ref_name in inputdata["REF"]:

        for unit_id, unit_configure in enumerate(inputdata["REF"][ref_name]["Heatsource"]):

            # 日別の熱源水等の温度
            inputdata["REF"][ref_name]["Heatsource"][unit_id]["heatsource_temperature"] = np.zeros(365)

            if "地盤A" in unit_configure["parameter"]["熱源種類"] or "地盤B" in unit_configure["parameter"]["熱源種類"] or \
                "地盤C" in unit_configure["parameter"]["熱源種類"] or "地盤D" in unit_configure["parameter"]["熱源種類"] or \
                "地盤E" in unit_configure["parameter"]["熱源種類"] or "地盤F" in unit_configure["parameter"]["熱源種類"]:  # 地中熱オープンループ

                for dd in range(365):

                    # 月別の揚水温度
                    theta_wo_m = AC_gshp_openloop["theta_ac_wo_ave"][ inputdata["Building"]["Region"]+"地域" ] + \
                        AC_gshp_openloop["theta_ac_wo_m"][ inputdata["Building"]["Region"]+"地域" ][ bc.day2month(dd) ]

                    # 月別の地盤からの熱源水還り温度
                    if inputdata["REF"][ref_name]["mode"] == "cooling":

                        # 日別の熱源水還り温度（冷房期）
                        heatsource_temperature = \
                            theta_wo_m + AC_gshp_openloop["theta_wo_c"][ unit_configure["parameter"]["熱源種類"] ] + \
                                AC_gshp_openloop["theta_hex_c"][ unit_configure["parameter"]["熱源種類"] ]

                        # マトリックス化して日別のデータに変換
                        inputdata["REF"][ref_name]["Heatsource"][unit_id]["heatsource_temperature"][dd] = \
                            ToadbC[ int(count_Matrix(heatsource_temperature, mxTC)) - 1 ]

                        # マトリックス化せずに日別のデータに変換（将来的にはこちらにすべき）
                        # inputdata["REF"][ref_name]["Heatsource"][unit_id]["heatsource_temperature"][dd] = heatsource_temperature

                    elif inputdata["REF"][ref_name]["mode"] == "heating":

                        # 日別の熱源水還り温度（暖房期）
                        heatsource_temperature = \
                            theta_wo_m + AC_gshp_openloop["theta_wo_h"][ unit_configure["parameter"]["熱源種類"] ] + \
                                AC_gshp_openloop["theta_hex_h"][ unit_configure["parameter"]["熱源種類"] ]

                        # マトリックス化して日別のデータに変換
                        inputdata["REF"][ref_name]["Heatsource"][unit_id]["heatsource_temperature"][dd] = \
                            ToadbH[ int(count_Matrix(heatsource_temperature, mxTH)) - 1 ]

                        # マトリックス化せずに日別のデータに変換（将来的にはこちらにすべき）
                        # inputdata["REF"][ref_name]["Heatsource"][unit_id]["heatsource_temperature"][dd] = heatsource_temperature

            else:

                if unit_configure["parameter"]["熱源種類"] == "水" and inputdata["REF"][ref_name]["mode"] == "cooling":
                    inputdata["REF"][ref_name]["Heatsource"][unit_id]["matrix_T"] = TctwC   # 冷却水温度

                elif unit_configure["parameter"]["熱源種類"] == "水" and inputdata["REF"][ref_name]["mode"] == "heating":
                    inputdata["REF"][ref_name]["Heatsource"][unit_id]["matrix_T"] = TctwH   # 冷却水温度

                elif unit_configure["parameter"]["熱源種類"] == "空気" and inputdata["REF"][ref_name]["mode"] == "cooling":
                    inputdata["REF"][ref_name]["Heatsource"][unit_id]["matrix_T"] = ToadbC  # 乾球温度

                elif unit_configure["parameter"]["熱源種類"] == "空気" and inputdata["REF"][ref_name]["mode"] == "heating":
                    inputdata["REF"][ref_name]["Heatsource"][unit_id]["matrix_T"] = ToawbH  # 湿球温度

                elif unit_configure["parameter"]["熱源種類"] == "不要" and inputdata["REF"][ref_name]["mode"] == "cooling":
                    inputdata["REF"][ref_name]["Heatsource"][unit_id]["matrix_T"] = ToadbC  # 乾球温度

                elif unit_configure["parameter"]["熱源種類"] == "不要" and inputdata["REF"][ref_name]["mode"] == "heating":
                    inputdata["REF"][ref_name]["Heatsource"][unit_id]["matrix_T"] = ToadbH  # 乾球温度

                elif "地盤1" in unit_configure["parameter"]["熱源種類"] or "地盤2" in unit_configure["parameter"]["熱源種類"] or \
                    "地盤3" in unit_configure["parameter"]["熱源種類"] or "地盤4" in unit_configure["parameter"]["熱源種類"] or \
                    "地盤5" in unit_configure["parameter"]["熱源種類"]:   # 地中熱クローズループ

                    for gound_type in range(1,6):

                        if unit_configure["parameter"]["熱源種類"] == "地盤"+str(int(gound_type)) and inputdata["REF"][ref_name]["mode"] == "cooling":
                            igsType = int(gound_type)-1
                            iAREA = int(inputdata["Building"]["Region"])-1
                            # 地盤からの還り温度（冷房）
                            inputdata["REF"][ref_name]["Heatsource"][unit_id]["matrix_T"] = \
                                ( gshp_cc[igsType] * resultJson["REF"][ref_name]["ghsp_Rq"] + gshp_dc[igsType] ) * ( ToadbC - gshpToa_c[iAREA] ) + \
                                (ghspToa_ave[iAREA] + gshp_ac[igsType] * resultJson["REF"][ref_name]["ghsp_Rq"] + gshp_bc[igsType])

                        elif unit_configure["parameter"]["熱源種類"] == "地盤"+str(int(gound_type)) and inputdata["REF"][ref_name]["mode"] == "heating":
                            igsType = int(gound_type)-1
                            iAREA = int(inputdata["Building"]["Region"])-1
                            # 地盤からの還り温度（暖房）
                            inputdata["REF"][ref_name]["Heatsource"][unit_id]["matrix_T"] = \
                                ( gshp_ch[igsType] * resultJson["REF"][ref_name]["ghsp_Rq"] + gshp_dh[igsType] ) * ( ToadbH - gshpToa_h[iAREA] ) + \
                                (ghspToa_ave[iAREA] + gshp_ah[igsType] * resultJson["REF"][ref_name]["ghsp_Rq"] + gshp_bh[igsType])

                else:
                    raise Exception("熱源種類が不正です。")

                # マトリックスから日別のデータに変換
                for dd in range(365):

                    if resultJson["REF"][ref_name]["matrix_iT"][dd] > 0:

                        iT = int(resultJson["REF"][ref_name]["matrix_iT"][dd]) - 1
                        inputdata["REF"][ref_name]["Heatsource"][unit_id]["heatsource_temperature"][dd] = \
                            inputdata["REF"][ref_name]["Heatsource"][unit_id]["matrix_T"][ iT ]


    ##----------------------------------------------------------------------------------
    ## 任意評定用　熱源水温度（ SP-3 ）
    ##----------------------------------------------------------------------------------

    if "SpecialInputData" in inputdata:
        if "heatsource_temperature_monthly" in inputdata["SpecialInputData"]:

            for ref_original_name in inputdata["SpecialInputData"]["heatsource_temperature_monthly"]:

                # 入力された熱源群名称から、計算上使用する熱源群名称（冷暖、蓄熱分離）に変換
                for ref_name in [ref_original_name + "_冷房", ref_original_name + "_暖房", ref_original_name + "_冷房_蓄熱", ref_original_name + "_暖房_蓄熱"]:

                    if  ref_name in inputdata["REF"]:
                        for unit_id, unit_configure in enumerate(inputdata["REF"][ref_name]["Heatsource"]):
                            for dd in range(0,365):
                                inputdata["REF"][ref_name]["Heatsource"][unit_id]["heatsource_temperature"][dd] = \
                                    inputdata["SpecialInputData"]["heatsource_temperature_monthly"][ref_original_name][ bc.day2month(dd) ]

    if debug: # pragma: no cover
        for ref_name in inputdata["REF"]:
            for unit_id, unit_configure in enumerate(inputdata["REF"][ref_name]["Heatsource"]):
                print( f'--- 熱源群名 {ref_name} ---')
                print( f'- {unit_id+1} 台目の熱源機器の熱源水温度 -')
                print( inputdata["REF"][ref_name]["Heatsource"][unit_id]["heatsource_temperature"])


    ##----------------------------------------------------------------------------------
    ## 最大能力比 xQratio （解説書 2.7.8）
    ##----------------------------------------------------------------------------------

    for ref_name in inputdata["REF"]:

        for unit_id, unit_configure in enumerate(inputdata["REF"][ref_name]["Heatsource"]):

            ## 能力比（各外気温帯における最大能力）
            inputdata["REF"][ref_name]["Heatsource"][unit_id]["xQratio"] = np.zeros(365)

            for dd in range(0,365):

                # 外気温度帯
                temperature = inputdata["REF"][ref_name]["Heatsource"][unit_id]["heatsource_temperature"][dd]

                # 特性式の数
                curveNum = len(unit_configure["parameter"]["能力比"])

                # 下限値
                temp_min_list = []
                for para_num in range(0,curveNum):
                    temp_min_list.append(unit_configure["parameter"]["能力比"][para_num]["下限"])
                # 上限値
                temp_max_list = []
                for para_num in range(0,curveNum):
                    temp_max_list.append(unit_configure["parameter"]["能力比"][para_num]["上限"])

                # 上限と下限を定める
                if temperature < temp_min_list[0]:
                    temperature = temp_min_list[0]
                elif temperature > temp_max_list[-1]:
                    temperature = temp_max_list[-1]

                for para_num in reversed(range(0,curveNum)):
                    if temperature <= temp_max_list[para_num]:

                        inputdata["REF"][ref_name]["Heatsource"][unit_id]["xQratio"][dd] =  \
                            unit_configure["parameter"]["能力比"][para_num]["基整促係数"] * ( \
                            unit_configure["parameter"]["能力比"][para_num]["係数"]["a4"] * temperature ** 4 + \
                            unit_configure["parameter"]["能力比"][para_num]["係数"]["a3"] * temperature ** 3 + \
                            unit_configure["parameter"]["能力比"][para_num]["係数"]["a2"] * temperature ** 2 + \
                            unit_configure["parameter"]["能力比"][para_num]["係数"]["a1"] * temperature  + \
                            unit_configure["parameter"]["能力比"][para_num]["係数"]["a0"] )


        for unit_id, unit_configure in enumerate(inputdata["REF"][ref_name]["Heatsource"]):

            inputdata["REF"][ref_name]["Heatsource"][unit_id]["Q_ref_max"] = np.zeros(365)

            for dd in range(0,365):

                # 各外気温区分における最大能力 [kW]
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["Q_ref_max"][dd] = \
                    inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedCapacity_total"] * \
                    inputdata["REF"][ref_name]["Heatsource"][unit_id]["xQratio"][dd]

            if debug: # pragma: no cover
                print( f'--- 熱源群名 {ref_name} ---')
                print( f'- {unit_id+1} 台目の熱源機器 -')
                print( f' Q_ref_max {inputdata["REF"][ref_name]["Heatsource"][unit_id]["Q_ref_max"]}')

    #----------------------------------------------------------------------------------
    # 蓄熱システムによる運転時間の補正（解説書 2.7.15 蓄熱）
    #----------------------------------------------------------------------------------

    # 蓄熱の場合のマトリックス操作（負荷率１に集約＋外気温を１レベル変える）
    for ref_name in inputdata["REF"]:

        inputdata["REF"][ref_name]["Q_ref_max_total"] = np.zeros(365)

        if inputdata["REF"][ref_name]["isStorage"] == "蓄熱":

            for unit_id, unit_configure in enumerate(inputdata["REF"][ref_name]["Heatsource"]):

                for dd in range(0,365):

                    # 各外気温区分における最大能力の合計を算出[kW]
                    inputdata["REF"][ref_name]["Q_ref_max_total"][dd] += \
                        inputdata["REF"][ref_name]["Heatsource"][unit_id]["Q_ref_max"][dd]

            for dd in range(0,365):

                if resultJson["REF"][ref_name]["matrix_iL"][dd] > 0:   # これを入れないと aveL(matrix_iL)でエラーとなる。

                    # 負荷率帯 matrix_iL のときの熱負荷
                    timeQmax =  aveL[ int(resultJson["REF"][ref_name]["matrix_iL"][dd]) - 1 ] \
                        * resultJson["REF"][ref_name]["Tref"][dd] * inputdata["REF"][ref_name]["Qref_rated"]

                    # 負荷率帯を「負荷率帯 10」にする。
                    resultJson["REF"][ref_name]["matrix_iL"][dd] = len(aveL) - 1

                    # 運転時間を書き換え ＝ 全負荷相当運転時間（熱負荷を最大負荷で除す）とする。
                    resultJson["REF"][ref_name]["Tref"][dd] = \
                        timeQmax / ( inputdata["REF"][ref_name]["Q_ref_max_total"][dd] )



    ##----------------------------------------------------------------------------------
    ## 最大入力比 xPratio （解説書 2.7.11）
    ##----------------------------------------------------------------------------------

    for ref_name in inputdata["REF"]:

        for unit_id, unit_configure in enumerate(inputdata["REF"][ref_name]["Heatsource"]):

            # 入力比（各外気温帯における最大入力）
            inputdata["REF"][ref_name]["Heatsource"][unit_id]["xPratio"] = np.zeros(365)

            # 外気温度帯マトリックス
            for dd in range(0,365):

                # 外気温度帯
                temperature = inputdata["REF"][ref_name]["Heatsource"][unit_id]["heatsource_temperature"][dd]

                # 特性式の数
                curveNum = len(unit_configure["parameter"]["入力比"])

                # 下限値
                temp_min_list = []
                for para_num in range(0,curveNum):
                    temp_min_list.append(unit_configure["parameter"]["入力比"][para_num]["下限"])
                # 上限値
                temp_max_list = []
                for para_num in range(0,curveNum):
                    temp_max_list.append(unit_configure["parameter"]["入力比"][para_num]["上限"])

                # 上限と下限を定める
                if temperature < temp_min_list[0]:
                    temperature = temp_min_list[0]
                elif temperature > temp_max_list[-1]:
                    temperature = temp_max_list[-1]

                for para_num in reversed(range(0,curveNum)):
                    if temperature <= temp_max_list[para_num]:

                        inputdata["REF"][ref_name]["Heatsource"][unit_id]["xPratio"][dd] =  \
                            unit_configure["parameter"]["入力比"][para_num]["基整促係数"] * ( \
                            unit_configure["parameter"]["入力比"][para_num]["係数"]["a4"] * temperature ** 4 + \
                            unit_configure["parameter"]["入力比"][para_num]["係数"]["a3"] * temperature ** 3 + \
                            unit_configure["parameter"]["入力比"][para_num]["係数"]["a2"] * temperature ** 2 + \
                            unit_configure["parameter"]["入力比"][para_num]["係数"]["a1"] * temperature  + \
                            unit_configure["parameter"]["入力比"][para_num]["係数"]["a0"] )


        for unit_id, unit_configure in enumerate(inputdata["REF"][ref_name]["Heatsource"]):

            inputdata["REF"][ref_name]["Heatsource"][unit_id]["E_ref_max"] = np.zeros(365)

            for dd in range(0,365):

                # 各外気温区分における最大入力 [kW]  (1次エネルギー換算値であることに注意）
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["E_ref_max"][dd] = \
                    inputdata["REF"][ref_name]["Heatsource"][unit_id]["Eref_rated_primary"] * \
                    inputdata["REF"][ref_name]["Heatsource"][unit_id]["xPratio"][dd]

            if debug: # pragma: no cover
                print( f'--- 熱源群名 {ref_name} ---')
                print( f'- {unit_id+1} 台目の熱源機器 -')
                print( f' E_ref_max {inputdata["REF"][ref_name]["Heatsource"][unit_id]["E_ref_max"]}')

    ##----------------------------------------------------------------------------------
    ## 熱源機器の運転台数（解説書 2.7.9）
    ##----------------------------------------------------------------------------------

    # 運転台数マトリックス
    for ref_name in inputdata["REF"]:

        resultJson["REF"][ref_name]["num_of_operation"] = np.zeros(365)

        for dd in range(0,365):

            if resultJson["REF"][ref_name]["Tref"][dd] > 0:  # 運転していれば

                iL = int(resultJson["REF"][ref_name]["matrix_iL"][dd]) -1

                if inputdata["REF"][ref_name]["isStagingControl"] == "無":   # 運転台数制御が「無」の場合

                    resultJson["REF"][ref_name]["num_of_operation"][dd] = inputdata["REF"][ref_name]["num_of_unit"]

                elif inputdata["REF"][ref_name]["isStagingControl"] == "有":  # 運転台数制御が「有」の場合

                    # 処理熱量 [kW]
                    tmpQ  = inputdata["REF"][ref_name]["Qref_rated"] * aveL[iL]

                    # 運転台数 num_of_operation
                    tmpQmax = 0
                    for rr in range(0, inputdata["REF"][ref_name]["num_of_unit"]):
                        tmpQmax += inputdata["REF"][ref_name]["Heatsource"][rr]["Q_ref_max"][dd]

                        if tmpQ < tmpQmax:
                            break

                    resultJson["REF"][ref_name]["num_of_operation"][dd] = rr+1

        if debug: # pragma: no cover
            print( f'--- 熱源群名 {ref_name} ---')
            print( f' num_of_operation {resultJson["REF"][ref_name]["num_of_operation"]}')

    ##----------------------------------------------------------------------------------
    ## 熱源群の運転負荷率（解説書 2.7.12）
    ##----------------------------------------------------------------------------------

    for ref_name in inputdata["REF"]:

        resultJson["REF"][ref_name]["load_ratio"] = np.zeros(365)

        for dd in range(0,365):

            if resultJson["REF"][ref_name]["Tref"][dd] > 0:  # 運転していれば

                iL = int(resultJson["REF"][ref_name]["matrix_iL"][dd]) -1

                # 処理熱量 [kW]
                tmpQ  = inputdata["REF"][ref_name]["Qref_rated"] * aveL[iL]

                Qrefr_mod_max = 0
                for unit_id in range(0, int(resultJson["REF"][ref_name]["num_of_operation"][dd])):
                    Qrefr_mod_max += inputdata["REF"][ref_name]["Heatsource"][unit_id]["Q_ref_max"][dd]

                # [iT,iL]における負荷率
                resultJson["REF"][ref_name]["load_ratio"][dd] = tmpQ / Qrefr_mod_max

                if inputdata["REF"][ref_name]["isStorage"] == "蓄熱":
                    resultJson["REF"][ref_name]["load_ratio"][dd] = 1.0

                # # 過負荷時の負荷率は 1.0 とする。ペナルティは別途乗じる。
                # if iL == divL-1:
                #     resultJson["REF"][ref_name]["load_ratio"][dd] = 1.0

        if debug: # pragma: no cover
            print( f'--- 熱源群名 {ref_name} ---')
            print( f' load_ratio {resultJson["REF"][ref_name]["load_ratio"]}')


    ##----------------------------------------------------------------------------------
    ## 部分負荷特性 （解説書 2.7.13）
    ##----------------------------------------------------------------------------------

    for ref_name in inputdata["REF"]:

        for unit_id, unit_configure in enumerate(inputdata["REF"][ref_name]["Heatsource"]):

            inputdata["REF"][ref_name]["Heatsource"][unit_id]["coeff_x"] = np.zeros(365)

        for dd in range(0,365):

            iL = int(resultJson["REF"][ref_name]["matrix_iL"][dd]) -1    # 負荷率帯のマトリックス番号

            # 部分負荷特性（各負荷率・各温度帯について）
            for unit_id in range(0, int(resultJson["REF"][ref_name]["num_of_operation"][dd])):

                # どの部分負荷特性を使うか（インバータターボなど、冷却水温度によって特性が異なる場合がある）
                xCurveNum = 0
                if len(inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["部分負荷特性"]) > 1:   # 部分負荷特性が2以上設定されている場合

                    for para_id in range(0, len(inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["部分負荷特性"])):

                        if inputdata["REF"][ref_name]["Heatsource"][unit_id]["heatsource_temperature"][dd] > inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["部分負荷特性"][para_id]["冷却水温度下限"] and \
                            inputdata["REF"][ref_name]["Heatsource"][unit_id]["heatsource_temperature"][dd] <= inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["部分負荷特性"][para_id]["冷却水温度上限"]:
                            xCurveNum = para_id

                # 機器特性による上下限を考慮した部分負荷率 tmpL
                tmpL = 0
                if resultJson["REF"][ref_name]["load_ratio"][dd] < inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["部分負荷特性"][xCurveNum]["下限"]:
                    tmpL = inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["部分負荷特性"][xCurveNum]["下限"]
                elif resultJson["REF"][ref_name]["load_ratio"][dd] > inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["部分負荷特性"][xCurveNum]["上限"]:
                    tmpL = inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["部分負荷特性"][xCurveNum]["上限"]
                else:
                    tmpL = resultJson["REF"][ref_name]["load_ratio"][dd]

                # 部分負荷特性
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["coeff_x"][dd] = \
                    inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["部分負荷特性"][xCurveNum]["基整促係数"]  * ( \
                    inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["部分負荷特性"][xCurveNum]["係数"]["a4"] * tmpL ** 4 +  \
                    inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["部分負荷特性"][xCurveNum]["係数"]["a3"] * tmpL ** 3 +  \
                    inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["部分負荷特性"][xCurveNum]["係数"]["a2"] * tmpL ** 2 +  \
                    inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["部分負荷特性"][xCurveNum]["係数"]["a1"] * tmpL + \
                    inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["部分負荷特性"][xCurveNum]["係数"]["a0"] )

                # 過負荷時のペナルティ
                if iL == divL-1:
                    inputdata["REF"][ref_name]["Heatsource"][unit_id]["coeff_x"][dd] = \
                        inputdata["REF"][ref_name]["Heatsource"][unit_id]["coeff_x"][dd] * 1.2


    ##----------------------------------------------------------------------------------
    ## 送水温度特性 （解説書 2.7.14）
    ##----------------------------------------------------------------------------------

    for ref_name in inputdata["REF"]:

        # 送水温度特性（各負荷率・各温度帯について）
        for unit_id, unit_configure in enumerate(inputdata["REF"][ref_name]["Heatsource"]):
            inputdata["REF"][ref_name]["Heatsource"][unit_id]["coeff_tw"] = np.ones(365)

        for dd in range(0,365):

            # iL = int(resultJson["REF"][ref_name]["matrix_iL"][dd]) -1    # 負荷率帯のマトリックス番号

            # 送水温度特性（各負荷率・各温度帯について）
            for unit_id in range(0, int(resultJson["REF"][ref_name]["num_of_operation"][dd])):

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
                    inputdata["REF"][ref_name]["Heatsource"][unit_id]["coeff_tw"][dd] = \
                        inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["送水温度特性"][0]["基整促係数"]  * ( \
                        inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["送水温度特性"][0]["係数"]["a4"] * TCtmp ** 4 +  \
                        inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["送水温度特性"][0]["係数"]["a3"] * TCtmp ** 3 +  \
                        inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["送水温度特性"][0]["係数"]["a2"] * TCtmp ** 2 +  \
                        inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["送水温度特性"][0]["係数"]["a1"] * TCtmp + \
                        inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["送水温度特性"][0]["係数"]["a0"] )


    #----------------------------------------------------------------------------------
    # 蓄熱システムによる運転時間の補正（解説書 2.7.15 追掛）
    #----------------------------------------------------------------------------------

    # 蓄熱槽を持つシステムの追い掛け時運転時間補正（追い掛け運転開始時に蓄熱量がすべて使われない問題を解消） 2014/1/10
    for ref_name in inputdata["REF"]:

        resultJson["REF"][ref_name]["hoseiStorage"] = np.ones(365)

        if inputdata["REF"][ref_name]["isStorage"] == "追掛":

            for dd in range(0,365):

                # iL = int(resultJson["REF"][ref_name]["matrix_iL"][dd]) -1

                if int(resultJson["REF"][ref_name]["num_of_operation"][dd]) >= 2:

                    # 2台目以降の合計最大能力（＝熱交換器以外の能力）
                    Qrefr_mod_except_HEX = 0
                    for unit_id in range(1, int(resultJson["REF"][ref_name]["num_of_operation"][dd])):
                        Qrefr_mod_except_HEX += inputdata["REF"][ref_name]["Heatsource"][unit_id]["Q_ref_max"][dd]

                    # 追い掛け時運転時間の補正率
                    # （ Q_ref_max * hosei * xL + Qrefr_mod_except_HEX = (Q_ref_max + Qrefr_mod_except_HEX) * xL ）
                    resultJson["REF"][ref_name]["hoseiStorage"][dd] = \
                        1 - ( inputdata["REF"][ref_name]["Heatsource"][0]["Q_ref_max"][dd] * \
                                (1 - resultJson["REF"][ref_name]["load_ratio"][dd]) / \
                                    (resultJson["REF"][ref_name]["load_ratio"][dd] * Qrefr_mod_except_HEX) )

            # 運転時間を補正
            for dd in range(0,365):
                if resultJson["REF"][ref_name]["Tref"][dd] > 0:
                    resultJson["REF"][ref_name]["Tref"][dd] = \
                        resultJson["REF"][ref_name]["Tref"][dd] * resultJson["REF"][ref_name]["hoseiStorage"][dd]


    ##----------------------------------------------------------------------------------
    ## 熱源機器の一次エネルギー消費量（解説書 2.7.16）
    ##----------------------------------------------------------------------------------

    for ref_name in inputdata["REF"]:

        resultJson["REF"][ref_name]["E_ref_sub"]      = np.zeros(365)
        resultJson["REF"][ref_name]["E_ref_pri_pump"] = np.zeros(365)
        resultJson["REF"][ref_name]["E_ref_ct_fan"]   = np.zeros(365)
        resultJson["REF"][ref_name]["E_ref_ct_pump"]  = np.zeros(365)

        for dd in range(0,365):

            iL = int(resultJson["REF"][ref_name]["matrix_iL"][dd]) -1

            # 熱源主機（機器毎）：エネルギー消費量 kW のマトリックス E_ref_main
            for unit_id in range(0, int(resultJson["REF"][ref_name]["num_of_operation"][dd])):

                resultJson["REF"][ref_name]["Heatsource"][unit_id]["E_ref_main"][dd] = \
                    inputdata["REF"][ref_name]["Heatsource"][unit_id]["E_ref_max"][dd] * \
                    inputdata["REF"][ref_name]["Heatsource"][unit_id]["coeff_x"][dd] * \
                    inputdata["REF"][ref_name]["Heatsource"][unit_id]["coeff_tw"][dd]

            ## 補機電力
            # 一台あたりの負荷率（熱源機器の負荷率＝最大能力を考慮した負荷率・ただし、熱源特性の上限・下限は考慮せず）
            aveLperU = resultJson["REF"][ref_name]["load_ratio"][dd]

            # 過負荷の場合は 平均負荷率＝1.2 とする。
            if iL == divL-1:
                aveLperU = 1.2

            # 発電機能付きの熱源機器が1台でもある場合
            if inputdata["REF"][ref_name]["checkGEGHP"] == 1:

                for unit_id in range(0, int(resultJson["REF"][ref_name]["num_of_operation"][dd])):

                    if "消費電力自給装置" in inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceType"]:

                        # 非発電時の消費電力 [kW]
                        if inputdata["REF"][ref_name]["mode"] == "cooling":
                            E_nonGE = inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedCapacity_total"] * 0.017
                        elif inputdata["REF"][ref_name]["mode"] == "heating":
                            E_nonGE = inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedCapacity_total"] * 0.012

                        E_GEkW = inputdata["REF"][ref_name]["Heatsource"][unit_id]["Heatsource_sub_RatedPowerConsumption_total"]  #  発電時の消費電力 [kW]

                        if aveLperU <= 0.3:
                            resultJson["REF"][ref_name]["E_ref_sub"][dd] += ( 0.3 * E_nonGE - (E_nonGE - E_GEkW) * aveLperU )
                        else:
                            resultJson["REF"][ref_name]["E_ref_sub"][dd] += ( aveLperU * E_GEkW )

                    else:

                        if aveLperU <= 0.3:
                            resultJson["REF"][ref_name]["E_ref_sub"][dd] += 0.3 * inputdata["REF"][ref_name]["Heatsource"][unit_id]["Heatsource_sub_RatedPowerConsumption_total"]
                        else:
                            resultJson["REF"][ref_name]["E_ref_sub"][dd] += aveLperU * inputdata["REF"][ref_name]["Heatsource"][unit_id]["Heatsource_sub_RatedPowerConsumption_total"]

            else:

                # 負荷に比例させる（発電機能なし）
                refset_SubPower = 0
                for unit_id in range(0, int(resultJson["REF"][ref_name]["num_of_operation"][dd])):
                    if inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedFuelConsumption_total"] > 0:
                        refset_SubPower += inputdata["REF"][ref_name]["Heatsource"][unit_id]["Heatsource_sub_RatedPowerConsumption_total"]

                if aveLperU <= 0.3:
                    resultJson["REF"][ref_name]["E_ref_sub"][dd] += 0.3 * refset_SubPower
                else:
                    resultJson["REF"][ref_name]["E_ref_sub"][dd] += aveLperU * refset_SubPower


            # 一次ポンプ
            for unit_id in range(0, int(resultJson["REF"][ref_name]["num_of_operation"][dd])):
                resultJson["REF"][ref_name]["E_ref_pri_pump"][dd] += \
                    inputdata["REF"][ref_name]["Heatsource"][unit_id]["PrimaryPumpPowerConsumption_total"]


            # 冷却塔ファン
            for unit_id in range(0, int(resultJson["REF"][ref_name]["num_of_operation"][dd])):
                resultJson["REF"][ref_name]["E_ref_ct_fan"][dd] += \
                    inputdata["REF"][ref_name]["Heatsource"][unit_id]["CoolingTowerFanPowerConsumption_total"]


            # 冷却水ポンプ
            if inputdata["REF"][ref_name]["checkCTVWV"] == 1:  # 変流量制御がある場合

                for unit_id in range(0, int(resultJson["REF"][ref_name]["num_of_operation"][dd])):

                    if "冷却水変流量" in inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceType"]:

                        if aveLperU <= 0.5:
                            resultJson["REF"][ref_name]["E_ref_ct_pump"][dd] += \
                                0.5 * inputdata["REF"][ref_name]["Heatsource"][unit_id]["CoolingTowerPumpPowerConsumption_total"]
                        else:
                            resultJson["REF"][ref_name]["E_ref_ct_pump"][dd] += \
                                aveLperU * inputdata["REF"][ref_name]["Heatsource"][unit_id]["CoolingTowerPumpPowerConsumption_total"]
                    else:
                        resultJson["REF"][ref_name]["E_ref_ct_pump"][dd] += \
                            inputdata["REF"][ref_name]["Heatsource"][unit_id]["CoolingTowerPumpPowerConsumption_total"]

            else:

                for unit_id in range(0, int(resultJson["REF"][ref_name]["num_of_operation"][dd])):
                    resultJson["REF"][ref_name]["E_ref_ct_pump"][dd] += \
                        inputdata["REF"][ref_name]["Heatsource"][unit_id]["CoolingTowerPumpPowerConsumption_total"]


    ##----------------------------------------------------------------------------------
    ## 熱源群の一次エネルギー消費量および消費電力（解説書 2.7.17）
    ##----------------------------------------------------------------------------------

    for ref_name in inputdata["REF"]:

        for dd in range(0,365):

            if resultJson["REF"][ref_name]["Tref"][dd] == 0:

                resultJson["REF"][ref_name]["E_ref_day"][dd]     =  0   # 熱源主機エネルギー消費量 [MJ]
                resultJson["REF"][ref_name]["E_ref_day_MWh"][dd] =  0   # 熱源主機電力消費量 [MWh]
                resultJson["REF"][ref_name]["E_ref_ACc_day"][dd] =  0   # 熱源補機電力 [MWh]
                resultJson["REF"][ref_name]["E_PPc_day"][dd]     =  0   # 一次ポンプ電力 [MWh]
                resultJson["REF"][ref_name]["E_CTfan_day"][dd]   =  0   # 冷却塔ファン電力 [MWh]
                resultJson["REF"][ref_name]["E_CTpump_day"][dd]  =  0   # 冷却水ポンプ電力 [MWh]

            else:

                # 熱源主機 [MJ/day]
                for unit_id in range(0,len(inputdata["REF"][ref_name]["Heatsource"])):

                    resultJson["REF"][ref_name]["E_ref_day"][dd]  += \
                        resultJson["REF"][ref_name]["Heatsource"][unit_id]["E_ref_main"][dd] *3600/1000 * resultJson["REF"][ref_name]["Tref"][dd]

                    # CGSの計算用に機種別に一次エネルギー消費量を積算 [MJ/day]
                    resultJson["REF"][ref_name]["Heatsource"][unit_id]["E_ref_day_per_unit"][dd] = \
                        resultJson["REF"][ref_name]["Heatsource"][unit_id]["E_ref_main"][dd] *3600/1000 * resultJson["REF"][ref_name]["Tref"][dd]

                    # CGSの計算用に電力のみ積算 [MWh]
                    if inputdata["REF"][ref_name]["Heatsource"][unit_id]["refInputType"] == 1:  # 燃料種類が「電力」であれば、CGS計算用に集計を行う。

                        resultJson["REF"][ref_name]["E_ref_day_MWh"][dd]  += \
                            resultJson["REF"][ref_name]["Heatsource"][unit_id]["E_ref_main"][dd] *3600/1000 * resultJson["REF"][ref_name]["Tref"][dd] / bc.fprime

                        resultJson["REF"][ref_name]["Heatsource"][unit_id]["E_ref_day_per_unit_MWh"][dd] = \
                            resultJson["REF"][ref_name]["Heatsource"][unit_id]["E_ref_main"][dd] *3600/1000 * resultJson["REF"][ref_name]["Tref"][dd] / bc.fprime

                # 補機電力 [MWh]
                resultJson["REF"][ref_name]["E_ref_ACc_day"][dd] += \
                    resultJson["REF"][ref_name]["E_ref_sub"][dd] /1000 * resultJson["REF"][ref_name]["Tref"][dd]

                # 一次ポンプ電力 [MWh]
                resultJson["REF"][ref_name]["E_PPc_day"][dd] += \
                    resultJson["REF"][ref_name]["E_ref_pri_pump"][dd] /1000 * resultJson["REF"][ref_name]["Tref"][dd]

                # 冷却塔ファン電力 [MWh]
                resultJson["REF"][ref_name]["E_CTfan_day"][dd] += \
                    resultJson["REF"][ref_name]["E_ref_ct_fan"][dd] /1000 * resultJson["REF"][ref_name]["Tref"][dd]

                # 冷却水ポンプ電力 [MWh]
                resultJson["REF"][ref_name]["E_CTpump_day"][dd] += \
                    resultJson["REF"][ref_name]["E_ref_ct_pump"][dd] /1000 * resultJson["REF"][ref_name]["Tref"][dd]


        if debug: # pragma: no cover

            print( f'--- 熱源群名 {ref_name} ---')
            print( f'熱源主機のエネルギー消費量 E_ref_day: {np.sum(resultJson["REF"][ref_name]["E_ref_day"])}' )
            print( f'熱源補機の消費電力 E_ref_ACc_day: {np.sum(resultJson["REF"][ref_name]["E_ref_ACc_day"])}' )
            print( f'一次ポンプの消費電力 E_PPc_day: {np.sum(resultJson["REF"][ref_name]["E_PPc_day"])}' )
            print( f'冷却塔ファンの消費電力 E_CTfan_day: {np.sum(resultJson["REF"][ref_name]["E_CTfan_day"])}' )
            print( f'冷却塔ポンプの消費電力 E_CTpump_day: {np.sum(resultJson["REF"][ref_name]["E_CTpump_day"])}' )


    ##----------------------------------------------------------------------------------
    ## 熱源群のエネルギー消費量（解説書 2.7.18）
    ##----------------------------------------------------------------------------------

    for ref_name in inputdata["REF"]:

        resultJson["REF"][ref_name]["熱源群熱源主機[MJ]"] = 0
        resultJson["REF"][ref_name]["熱源群熱源補機[MWh]"] = 0
        resultJson["REF"][ref_name]["熱源群一次ポンプ[MWh]"] = 0
        resultJson["REF"][ref_name]["熱源群冷却塔ファン[MWh]"] = 0
        resultJson["REF"][ref_name]["熱源群冷却水ポンプ[MWh]"] = 0

        resultJson["REF"][ref_name]["熱源群熱源主機[GJ]"] = 0
        resultJson["REF"][ref_name]["熱源群熱源補機[GJ]"] = 0
        resultJson["REF"][ref_name]["熱源群一次ポンプ[GJ]"] = 0
        resultJson["REF"][ref_name]["熱源群冷却塔ファン[GJ]"] = 0
        resultJson["REF"][ref_name]["熱源群冷却水ポンプ[GJ]"] = 0

        # 熱源主機の電力消費量 [MWh/day]
        resultJson["日別エネルギー消費量"]["E_ref_main_MWh_day"]  += resultJson["REF"][ref_name]["E_ref_day_MWh"]
        # 熱源主機以外の電力消費量 [MWh/day]
        resultJson["日別エネルギー消費量"]["E_ref_sub_MWh_day"]  += resultJson["REF"][ref_name]["E_ref_ACc_day"] \
                + resultJson["REF"][ref_name]["E_PPc_day"] + resultJson["REF"][ref_name]["E_CTfan_day"] \
                + resultJson["REF"][ref_name]["E_CTpump_day"]

        for dd in range(0,365):

            # 熱源主機のエネルギー消費量 [MJ]
            resultJson["REF"][ref_name]["熱源群熱源主機[MJ]"] += resultJson["REF"][ref_name]["E_ref_day"][dd]
            # 熱源補機電力消費量 [MWh]
            resultJson["REF"][ref_name]["熱源群熱源補機[MWh]"]  += resultJson["REF"][ref_name]["E_ref_ACc_day"][dd]
            # 一次ポンプ電力消費量 [MWh]
            resultJson["REF"][ref_name]["熱源群一次ポンプ[MWh]"]  += resultJson["REF"][ref_name]["E_PPc_day"][dd]
            # 冷却塔ファン電力消費量 [MWh]
            resultJson["REF"][ref_name]["熱源群冷却塔ファン[MWh]"]  += resultJson["REF"][ref_name]["E_CTfan_day"][dd]
            # 冷却水ポンプ電力消費量 [MWh]
            resultJson["REF"][ref_name]["熱源群冷却水ポンプ[MWh]"] += resultJson["REF"][ref_name]["E_CTpump_day"][dd]

        resultJson["REF"][ref_name]["熱源群熱源主機[GJ]"] = resultJson["REF"][ref_name]["熱源群熱源主機[MJ]"] / 1000
        resultJson["REF"][ref_name]["熱源群熱源補機[GJ]"] = resultJson["REF"][ref_name]["熱源群熱源補機[MWh]"] * bc.fprime / 1000
        resultJson["REF"][ref_name]["熱源群一次ポンプ[GJ]"] = resultJson["REF"][ref_name]["熱源群一次ポンプ[MWh]"] * bc.fprime / 1000
        resultJson["REF"][ref_name]["熱源群冷却塔ファン[GJ]"] = resultJson["REF"][ref_name]["熱源群冷却塔ファン[MWh]"] * bc.fprime / 1000
        resultJson["REF"][ref_name]["熱源群冷却水ポンプ[GJ]"] = resultJson["REF"][ref_name]["熱源群冷却水ポンプ[MWh]"] * bc.fprime / 1000

        # 建物全体
        resultJson["年間エネルギー消費量"]["熱源群熱源主機[MJ]"] += resultJson["REF"][ref_name]["熱源群熱源主機[MJ]"]
        resultJson["年間エネルギー消費量"]["熱源群熱源補機[MWh]"] += resultJson["REF"][ref_name]["熱源群熱源補機[MWh]"]
        resultJson["年間エネルギー消費量"]["熱源群一次ポンプ[MWh]"] += resultJson["REF"][ref_name]["熱源群一次ポンプ[MWh]"]
        resultJson["年間エネルギー消費量"]["熱源群冷却塔ファン[MWh]"] += resultJson["REF"][ref_name]["熱源群冷却塔ファン[MWh]"]
        resultJson["年間エネルギー消費量"]["熱源群冷却水ポンプ[MWh]"] += resultJson["REF"][ref_name]["熱源群冷却水ポンプ[MWh]"]

        resultJson["年間エネルギー消費量"]["熱源群熱源主機[GJ]"] += resultJson["REF"][ref_name]["熱源群熱源主機[GJ]"]
        resultJson["年間エネルギー消費量"]["熱源群熱源補機[GJ]"] += resultJson["REF"][ref_name]["熱源群熱源補機[GJ]"]
        resultJson["年間エネルギー消費量"]["熱源群一次ポンプ[GJ]"] += resultJson["REF"][ref_name]["熱源群一次ポンプ[GJ]"]
        resultJson["年間エネルギー消費量"]["熱源群冷却塔ファン[GJ]"] += resultJson["REF"][ref_name]["熱源群冷却塔ファン[GJ]"]
        resultJson["年間エネルギー消費量"]["熱源群冷却水ポンプ[GJ]"] += resultJson["REF"][ref_name]["熱源群冷却水ポンプ[GJ]"]


    print('熱源エネルギー計算完了')

    if debug: # pragma: no cover

        print( f'熱源主機エネルギー消費量 : {resultJson["年間エネルギー消費量"]["熱源群熱源主機[MJ]"]} MJ' )
        print( f'熱源補機電力消費量 : {resultJson["年間エネルギー消費量"]["熱源群熱源補機[MWh]"]} MWh' )
        print( f'一次ポンプ電力消費量 : {resultJson["年間エネルギー消費量"]["熱源群一次ポンプ[MWh]"]} MWh' )
        print( f'冷却塔ファン電力消費量 : {resultJson["年間エネルギー消費量"]["熱源群冷却塔ファン[MWh]"]} MWh' )
        print( f'冷却水ポンプ電力消費量 : {resultJson["年間エネルギー消費量"]["熱源群冷却水ポンプ[MWh]"]} MWh' )


    ##----------------------------------------------------------------------------------
    ## 熱源群計算結果の集約
    ##----------------------------------------------------------------------------------

    for ref_name in inputdata["REF"]:

        if inputdata["REF"][ref_name]["mode"] == "cooling":
            resultJson["REF"][ref_name]["運転モード"] = "冷房"
        elif inputdata["REF"][ref_name]["mode"] == "heating":
            resultJson["REF"][ref_name]["運転モード"] = "暖房"
        else:
            raise Exception("運転モードが不正です")

        resultJson["REF"][ref_name]["定格能力[kW]"] = inputdata["REF"][ref_name]["Qref_rated"]
        resultJson["REF"][ref_name]["熱源主機_定格消費エネルギー[kW]"] = inputdata["REF"][ref_name]["Eref_rated_primary"]
        resultJson["REF"][ref_name]["年間運転時間[時間]"] = np.sum( resultJson["REF"][ref_name]["Tref"] )
        resultJson["REF"][ref_name]["年積算熱源負荷[GJ]"] = np.sum( resultJson["REF"][ref_name]["Qref"] ) /1000
        resultJson["REF"][ref_name]["年積算過負荷[GJ]"] = np.sum( resultJson["REF"][ref_name]["Qref_OVER"] ) /1000
        resultJson["REF"][ref_name]["年積算エネルギー消費量[GJ]"] = \
            resultJson["REF"][ref_name]["熱源群熱源主機[GJ]"] \
            + resultJson["REF"][ref_name]["熱源群熱源補機[GJ]"] \
            + resultJson["REF"][ref_name]["熱源群一次ポンプ[GJ]"] \
            + resultJson["REF"][ref_name]["熱源群冷却塔ファン[GJ]"] \
            + resultJson["REF"][ref_name]["熱源群冷却水ポンプ[GJ]"] \

        resultJson["REF"][ref_name]["年間平均負荷率[-]"] = \
            (resultJson["REF"][ref_name]["年積算熱源負荷[GJ]"] *1000000 / (resultJson["REF"][ref_name]["年間運転時間[時間]"]*3600) ) \
            / resultJson["REF"][ref_name]["熱源主機_定格消費エネルギー[kW]"]

        resultJson["REF"][ref_name]["年間運転効率[-]"] = \
            resultJson["REF"][ref_name]["年積算熱源負荷[GJ]"] \
            / resultJson["REF"][ref_name]["年積算エネルギー消費量[GJ]"]


    ##----------------------------------------------------------------------------------
    ## 設計一次エネルギー消費量（解説書 2.8）
    ##----------------------------------------------------------------------------------

    resultJson["設計一次エネルギー消費量[MJ/年]"] = \
        + resultJson["年間エネルギー消費量"]["空調機群ファン[GJ]"] *1000 \
        + resultJson["年間エネルギー消費量"]["空調機群全熱交換器[GJ]"] *1000 \
        + resultJson["年間エネルギー消費量"]["二次ポンプ群[GJ]"] *1000  \
        + resultJson["年間エネルギー消費量"]["熱源群熱源主機[GJ]"] *1000 \
        + resultJson["年間エネルギー消費量"]["熱源群熱源補機[GJ]"] *1000 \
        + resultJson["年間エネルギー消費量"]["熱源群一次ポンプ[GJ]"] *1000 \
        + resultJson["年間エネルギー消費量"]["熱源群冷却塔ファン[GJ]"] *1000 \
        + resultJson["年間エネルギー消費量"]["熱源群冷却水ポンプ[GJ]"] *1000


    ##----------------------------------------------------------------------------------
    ## 基準一次エネルギー消費量 （解説書 10.1）
    ##----------------------------------------------------------------------------------
    for room_zone_name in inputdata["AirConditioningZone"]:

        # 建物用途・室用途、ゾーン面積等の取得
        buildingType = inputdata["Rooms"][room_zone_name]["buildingType"]
        roomType     = inputdata["Rooms"][room_zone_name]["roomType"]
        zoneArea     = inputdata["Rooms"][room_zone_name]["roomArea"]

        resultJson["計算対象面積"] += zoneArea
        resultJson["基準一次エネルギー消費量[MJ/年]"] += \
            bc.RoomStandardValue[buildingType][roomType]["空調"][inputdata["Building"]["Region"]+"地域"] * zoneArea


    # BEI/ACの算出
    resultJson["BEI/AC"] = resultJson["設計一次エネルギー消費量[MJ/年]"] / resultJson["基準一次エネルギー消費量[MJ/年]"]
    resultJson["BEI/AC"] = math.ceil(resultJson["BEI/AC"] * 100)/100

    resultJson["設計一次エネルギー消費量[GJ/年]"]   = resultJson["設計一次エネルギー消費量[MJ/年]"] / 1000
    resultJson["基準一次エネルギー消費量[GJ/年]"]   = resultJson["基準一次エネルギー消費量[MJ/年]"] / 1000
    resultJson["設計一次エネルギー消費量[MJ/m2年]"] = resultJson["設計一次エネルギー消費量[MJ/年]"] / resultJson["計算対象面積"]
    resultJson["基準一次エネルギー消費量[MJ/m2年]"] = resultJson["基準一次エネルギー消費量[MJ/年]"] / resultJson["計算対象面積"]


    if debug: # pragma: no cover
        print( f'空調設備の設計一次エネルギー消費量 MJ/m2 : {resultJson["設計一次エネルギー消費量[MJ/m2年]"]}' )
        print( f'空調設備の設計一次エネルギー消費量 MJ : {resultJson["設計一次エネルギー消費量[MJ/年]"]}' )
        print( f'空調設備の基準一次エネルギー消費量 MJ/m2 : {resultJson["基準一次エネルギー消費量[MJ/m2年]"]}' )
        print( f'空調設備の基準一次エネルギー消費量 MJ : {resultJson["基準一次エネルギー消費量[MJ/年]"]}' )


    ##----------------------------------------------------------------------------------
    ## CGS計算用変数 （解説書 ８章 附属書 G.10 他の設備の計算結果の読み込み）
    ##----------------------------------------------------------------------------------

    if len(inputdata["CogenerationSystems"]) == 1: # コジェネがあれば実行

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
        resultJson["for_CGS"]["E_ref_main_MWh_day"] =  resultJson["日別エネルギー消費量"]["E_ref_main_MWh_day"]  # 後半でCGSから排熱供給を受ける熱源群の電力消費量を差し引く。

        # 熱源補機の電力消費量 [MWh/day]
        resultJson["for_CGS"]["E_ref_sub_MWh_day"] = resultJson["日別エネルギー消費量"]["E_ref_sub_MWh_day"]

        # 二次ポンプ群の電力消費量 [MWh/day]
        resultJson["for_CGS"]["E_pump_MWh_day"] = resultJson["日別エネルギー消費量"]["E_pump_MWh_day"]

        # 空調機群の電力消費量 [MWh/day]
        resultJson["for_CGS"]["E_fan_MWh_day"] = resultJson["日別エネルギー消費量"]["E_fan_MWh_day"]

        ## 排熱利用熱源系統
        resultJson["for_CGS"]["E_ref_cgsC_ABS_day"] = np.zeros(365)
        resultJson["for_CGS"]["Lt_ref_cgsC_day"]    = np.zeros(365)
        resultJson["for_CGS"]["E_ref_cgsH_day"]     = np.zeros(365)
        resultJson["for_CGS"]["Q_ref_cgsH_day"]     = np.zeros(365)
        resultJson["for_CGS"]["T_ref_cgsC_day"]     = np.zeros(365)
        resultJson["for_CGS"]["T_ref_cgsH_day"]     = np.zeros(365)
        resultJson["for_CGS"]["NAC_ref_link"] = 0
        resultJson["for_CGS"]["qAC_link_c_j_rated"] = 0
        resultJson["for_CGS"]["EAC_link_c_j_rated"] = 0

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
                        resultJson["for_CGS"]["E_ref_cgsC_ABS_day"] += resultJson["REF"][ref_name]["Heatsource"][unit_id]["E_ref_day_per_unit"]

                        # 排熱投入型吸収式冷温水機jの定格冷却能力
                        resultJson["for_CGS"]["qAC_link_c_j_rated"] += inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedCapacity_total"]

                        # 排熱投入型吸収式冷温水機jの主機定格消費エネルギー
                        resultJson["for_CGS"]["EAC_link_c_j_rated"] += inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedFuelConsumption_total"]

                        resultJson["for_CGS"]["NAC_ref_link"] += 1

                # CGSの排熱利用が可能な排熱投入型吸収式冷温水機(系統)の冷熱源としての負荷率 [-]
                for dd in range(0,365):

                    if resultJson["REF"][ref_name]["Tref"][dd] == 0:
                        resultJson["for_CGS"]["Lt_ref_cgsC_day"][dd] = 0
                    elif resultJson["REF"][ref_name]["matrix_iL"][dd] == 11:
                        resultJson["for_CGS"]["Lt_ref_cgsC_day"][dd] = 1.2
                    else:
                        resultJson["for_CGS"]["Lt_ref_cgsC_day"][dd] = round(0.1*resultJson["REF"][ref_name]["matrix_iL"][dd]-0.05,2)

                # CGSの排熱利用が可能な排熱投入型吸収式冷温水機(系統)の運転時間 [h/日]
                resultJson["for_CGS"]["T_ref_cgsC_day"] = resultJson["REF"][ref_name]["Tref"]

            # CGS系統の「排熱利用する温熱源」
            if ref_name == resultJson["for_CGS"]["CGS_refName_H"]:

                # 当該温熱源群の主機の消費電力を差し引く。
                for unit_id, unit_configure in enumerate(inputdata["REF"][ref_name]["Heatsource"]):
                    resultJson["for_CGS"]["E_ref_main_MWh_day"] -= resultJson["REF"][ref_name]["Heatsource"][unit_id]["E_ref_day_per_unit_MWh"]

                # CGSの排熱利用が可能な温熱源群の主機の一次エネルギー消費量 [MJ/日]
                resultJson["for_CGS"]["E_ref_cgsH_day"] = resultJson["REF"][ref_name]["E_ref_day"]

                # CGSの排熱利用が可能な温熱源群の熱源負荷 [MJ/日]
                resultJson["for_CGS"]["Q_ref_cgsH_day"] = resultJson["REF"][ref_name]["Qref"]

                # CGSの排熱利用が可能な温熱源群の運転時間 [h/日]
                resultJson["for_CGS"]["T_ref_cgsH_day"] = resultJson["REF"][ref_name]["Tref"]

        # 空気調和設備の電力消費量 [MWh/day]
        resultJson["for_CGS"]["electric_power_consumption"] = \
            + resultJson["for_CGS"]["E_ref_main_MWh_day"] \
            + resultJson["for_CGS"]["E_ref_sub_MWh_day"] \
            + resultJson["for_CGS"]["E_pump_MWh_day"] \
            + resultJson["for_CGS"]["E_fan_MWh_day"]

    # with open("inputdataJson_AC.json",'w', encoding='utf-8') as fw:
    #     json.dump(inputdata, fw, indent=4, ensure_ascii=False, cls = bc.MyEncoder)


    ##----------------------------------------------------------------------------------
    # 不要な要素を削除
    ##----------------------------------------------------------------------------------

    for room_zone_name in resultJson["Qroom"]:
        del resultJson["Qroom"][room_zone_name]["Qwall_T"]
        del resultJson["Qroom"][room_zone_name]["Qwall_S"]
        del resultJson["Qroom"][room_zone_name]["Qwall_N"]
        del resultJson["Qroom"][room_zone_name]["Qwind_T"]
        del resultJson["Qroom"][room_zone_name]["Qwind_S"]
        del resultJson["Qroom"][room_zone_name]["Qwind_N"]
        del resultJson["Qroom"][room_zone_name]["QroomDc"]
        del resultJson["Qroom"][room_zone_name]["QroomDh"]
        del resultJson["Qroom"][room_zone_name]["QroomHc"]
        del resultJson["Qroom"][room_zone_name]["QroomHh"]

    for ahu_name in resultJson["AHU"]:
        del resultJson["AHU"][ahu_name]["schedule"]
        del resultJson["AHU"][ahu_name]["HoaDayAve"]
        del resultJson["AHU"][ahu_name]["qoaAHU"]
        del resultJson["AHU"][ahu_name]["Tahu_total"]
        del resultJson["AHU"][ahu_name]["E_fan_day"]
        del resultJson["AHU"][ahu_name]["E_fan_c_day"]
        del resultJson["AHU"][ahu_name]["E_fan_h_day"]
        del resultJson["AHU"][ahu_name]["E_AHUaex_day"]
        del resultJson["AHU"][ahu_name]["TdAHUc_total"]
        del resultJson["AHU"][ahu_name]["TdAHUh_total"]
        del resultJson["AHU"][ahu_name]["Qahu_remainC"]
        del resultJson["AHU"][ahu_name]["Qahu_remainH"]
        del resultJson["AHU"][ahu_name]["energy_consumption_each_LF"]
        del resultJson["AHU"][ahu_name]["Qroom"]
        del resultJson["AHU"][ahu_name]["Qahu"]
        del resultJson["AHU"][ahu_name]["Tahu"]
        del resultJson["AHU"][ahu_name]["Economizer"]
        del resultJson["AHU"][ahu_name]["LdAHUc"]
        del resultJson["AHU"][ahu_name]["TdAHUc"]
        del resultJson["AHU"][ahu_name]["LdAHUh"]
        del resultJson["AHU"][ahu_name]["TdAHUh"]

    dummypumplist = []
    for pump_name in resultJson["PUMP"]:
        if pump_name.startswith("dummyPump"):
            dummypumplist.append(pump_name)

    for pump_name in dummypumplist:
        del resultJson["PUMP"][pump_name]

    for pump_name in resultJson["PUMP"]:
        del resultJson["PUMP"][pump_name]["Qpsahu_fan"]
        del resultJson["PUMP"][pump_name]["pumpTime_Start"]
        del resultJson["PUMP"][pump_name]["pumpTime_Stop"]
        del resultJson["PUMP"][pump_name]["Qps"]
        del resultJson["PUMP"][pump_name]["Tps"]
        del resultJson["PUMP"][pump_name]["schedule"]
        del resultJson["PUMP"][pump_name]["LdPUMP"]
        del resultJson["PUMP"][pump_name]["TdPUMP"]
        del resultJson["PUMP"][pump_name]["Qpsahu_pump"]
        del resultJson["PUMP"][pump_name]["MxPUMPNum"]
        del resultJson["PUMP"][pump_name]["MxPUMPPower"]
        del resultJson["PUMP"][pump_name]["E_pump_day"]

    for ref_name in resultJson["REF"]:
        del resultJson["REF"][ref_name]["schedule"]
        del resultJson["REF"][ref_name]["ghsp_Rq"]
        del resultJson["REF"][ref_name]["Qref_thermal_loss"]
        del resultJson["REF"][ref_name]["Qref"]
        del resultJson["REF"][ref_name]["Tref"]
        del resultJson["REF"][ref_name]["Qref_kW"]
        del resultJson["REF"][ref_name]["Qref_OVER"]
        del resultJson["REF"][ref_name]["E_ref_day"]
        del resultJson["REF"][ref_name]["E_ref_day_MWh"]
        del resultJson["REF"][ref_name]["E_ref_ACc_day"]
        del resultJson["REF"][ref_name]["E_PPc_day"]
        del resultJson["REF"][ref_name]["E_CTfan_day"]
        del resultJson["REF"][ref_name]["E_CTpump_day"]
        del resultJson["REF"][ref_name]["Heatsource"]
        del resultJson["REF"][ref_name]["Lref"]
        del resultJson["REF"][ref_name]["matrix_iL"]
        del resultJson["REF"][ref_name]["matrix_iT"]
        del resultJson["REF"][ref_name]["num_of_operation"]
        del resultJson["REF"][ref_name]["load_ratio"]
        del resultJson["REF"][ref_name]["hoseiStorage"]
        del resultJson["REF"][ref_name]["E_ref_sub"]
        del resultJson["REF"][ref_name]["E_ref_pri_pump"]
        del resultJson["REF"][ref_name]["E_ref_ct_fan"]
        del resultJson["REF"][ref_name]["E_ref_ct_pump"]




    del resultJson["Matrix"]
    del resultJson["日別エネルギー消費量"]


    return resultJson


if __name__ == '__main__':  # pragma: no cover

    print('----- airconditioning.py -----')
    # filename = './sample/ACtest_Case001.json'
    filename = './sample/Builelib_sample_SP1_input.json'
    # filename = './sample/WEBPRO_inputSheet_sample.json'
    # filename = './sample/Builelib_sample_SP10.json'
    # filename = './sample/WEBPRO_KE14_Case01.json'
    # filename = './tests/cogeneration/Case_hospital_00.json'
    # filename = './tests/airconditioning_heatsoucetemp/airconditioning_heatsoucetemp_area_6.json'
    # filename = "./tests/airconditioning_gshp_openloop/AC_gshp_closeloop_Case001.json"


    # 入力ファイルの読み込み
    with open(filename, 'r', encoding='utf-8') as f:
        inputdata = json.load(f)

    resultJson = calc_energy(inputdata, debug=True)

    with open("resultJson_AC.json",'w', encoding='utf-8') as fw:
        json.dump(resultJson, fw, indent=4, ensure_ascii=False, cls = bc.MyEncoder)

    print( f'BEI/AC: {resultJson["BEI/AC"]}')
    print( f'設計一次エネルギー消費量 全体: {resultJson["設計一次エネルギー消費量[GJ/年]"]} GJ')
    print( f'設計一次エネルギー消費量 空調ファン: {resultJson["年間エネルギー消費量"]["空調機群ファン[GJ]"]} GJ')
    print( f'設計一次エネルギー消費量 空調全熱交換器: {resultJson["年間エネルギー消費量"]["空調機群全熱交換器[GJ]"]} GJ')
    print( f'設計一次エネルギー消費量 二次ポンプ: {resultJson["年間エネルギー消費量"]["二次ポンプ群[GJ]"]} GJ')
    print( f'設計一次エネルギー消費量 熱源主機: {resultJson["年間エネルギー消費量"]["熱源群熱源主機[GJ]"]} GJ')
    print( f'設計一次エネルギー消費量 熱源補機: {resultJson["年間エネルギー消費量"]["熱源群熱源補機[GJ]"]} GJ')
    print( f'設計一次エネルギー消費量 一次ポンプ: {resultJson["年間エネルギー消費量"]["熱源群一次ポンプ[GJ]"]} GJ')
    print( f'設計一次エネルギー消費量 冷却塔ファン: {resultJson["年間エネルギー消費量"]["熱源群冷却塔ファン[GJ]"]} GJ')
    print( f'設計一次エネルギー消費量 冷却水ポンプ: {resultJson["年間エネルギー消費量"]["熱源群冷却水ポンプ[GJ]"]} GJ')

    # デバッグ用
    # print( f'{resultJson["設計一次エネルギー消費量[MJ/年]"]}, {resultJson["ENERGY"]["E_fan"] * bc.fprime}, {resultJson["ENERGY"]["E_aex"] * bc.fprime}, {resultJson["ENERGY"]["E_pump"] * bc.fprime}, {resultJson["ENERGY"]["E_refsysr"]}, {resultJson["ENERGY"]["E_refac"] * bc.fprime}, {resultJson["ENERGY"]["E_pumpP"] * bc.fprime}, {resultJson["ENERGY"]["E_ctfan"] * bc.fprime}, {resultJson["ENERGY"]["E_ctpump"] * bc.fprime}')

    # for ref_name in inputdata["REF"]:
    #     print( f'--- 熱源群名 {ref_name} ---')
    #     print( f'熱源群の熱源負荷 Qref: {np.sum(resultJson["REF"][ref_name]["Qref"],0)}' )

    print( f'設計一次エネルギー消費量 全体: {resultJson["設計一次エネルギー消費量[MJ/年]"]}')
