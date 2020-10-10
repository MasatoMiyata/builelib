import json
import numpy as np
import math
import os
import copy

import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import commons as bc
import climate
import shading

# データベースファイルの保存場所
database_directory =  os.path.dirname(os.path.abspath(__file__)) + "/database/"
# 気象データファイルの保存場所
climatedata_directory =  os.path.dirname(os.path.abspath(__file__)) + "/climatedata/"


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


def count_Matrix(x, mxL):
    """
    負荷率 X がマトリックス mxL の何番目（ix）のセルに入るかをカウント
    """

    # 初期値
    ix = 0

    # C#の処理に合わせる。
    x = math.floor(x*10)/10+0.05

    # 該当するマトリックスを探査
    while x >= mxL[ix]:
        ix += 1

        if ix == len(mxL)-1:
            break

    return ix+1


def calc_energy(inputdata, DEBUG = False):

    inputdata["PUMP"] = {}
    inputdata["REF"] = {}

    # 計算結果を格納する変数
    resultJson = {
        "E_airconditioning": 0,
        "Es_airconditioning": 0,
        "BEI_AC": 0,
        "Qroom": {
        },
        "AHU":{
        },
        "PUMP":{
        },
        "REF":{
        },
        "ENERGY":{
            "E_fan": 0,     # 空調機群の一次エネルギー消費量 [GJ]
            "E_aex": 0,     # 全熱交換器の一次エネルギー消費量 [GJ]
            "E_pump": 0,    # 二次ポンプ群の一次エネルギー消費量 [GJ]
            "E_refsysr": 0, # 熱源群主機の一次エネルギー消費量 [GJ]
            "E_refac": 0,   # 熱源群補機の一次エネルギー消費量 [GJ]
            "E_pumpP": 0,   # 熱源群一次ポンプの一次エネルギー消費量 [GJ]
            "E_ctfan": 0,   # 熱源群冷却塔ファンの一次エネルギー消費量 [GJ]
            "E_ctpump": 0,  # 熱源群冷却水ポンプの一次エネルギー消費量 [GJ]
            "E_ref_source_day": {
                "電力": 0,
                "ガス": 0,
                "重油": 0,
                "灯油": 0,
                "液化石油ガス": 0,
                "蒸気": 0,
                "温水": 0,
                "冷水": 0,
            }
        }
    }

    ##----------------------------------------------------------------------------------
    ## 定数の設定
    ##----------------------------------------------------------------------------------
    k_heatup = 0.84        # ファン・ポンプの発熱比率
    Cw = 4.186             # 水の比熱 [kJ/kg・K]
    divL = 10             # 負荷帯マトリックス分割数
    divT =  6             # 温度帯マトリックス分割数

    ##----------------------------------------------------------------------------------
    ## マトリックスの設定
    ##----------------------------------------------------------------------------------

    # 地域別データの読み込み
    with open(database_directory + 'AREA.json', 'r') as f:
        Area = json.load(f)

    # 負荷率帯マトリックス mxL = array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.2])
    mxL = np.arange(1/divL, 1.01, 1/divL)
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
    ## 他人から供給された熱の一次エネルギー換算係数（デフォルト）
    ##----------------------------------------------------------------------------------

    if inputdata["Building"]["Coefficient_DHC"]["Cooling"] == None:
        inputdata["Building"]["Coefficient_DHC"]["Cooling"] = 1.36

    if inputdata["Building"]["Coefficient_DHC"]["Heating"] == None:
        inputdata["Building"]["Coefficient_DHC"]["Heating"] = 1.36


    ##----------------------------------------------------------------------------------
    ## 気象データ（解説書 2.2.1）
    ##----------------------------------------------------------------------------------

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
    with open(database_directory + 'ACoperationMode.json', 'r') as f:
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

    Hoa_ave = bc.air_enenthalpy(Toa_ave, Xoa_ave)
    Hoa_day = bc.air_enenthalpy(Toa_day, Xoa_day)
    Hoa_ngt = bc.air_enenthalpy(Toa_ngt, Xoa_ngt)


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
            inputdata["AirConditioningZone"][room_zone_name]["buildingType"] = inputdata["Rooms"][room_zone_name]["buildingType"]
            inputdata["AirConditioningZone"][room_zone_name]["roomType"]     = inputdata["Rooms"][room_zone_name]["roomType"]
            inputdata["AirConditioningZone"][room_zone_name]["zoneArea"]     = inputdata["Rooms"][room_zone_name]["roomArea"]
                
        else:

            # 各室のゾーンを検索
            for room_name in inputdata["Rooms"]:
                if inputdata["Rooms"][room_name]["zone"] != None:   # ゾーンがあれば
                    for zone_name  in inputdata["Rooms"][room_name]["zone"]:   # ゾーン名を検索
                        if room_zone_name == (room_name+"_"+zone_name):

                            inputdata["AirConditioningZone"][room_zone_name]["buildingType"] = inputdata["Rooms"][room_name]["buildingType"]
                            inputdata["AirConditioningZone"][room_zone_name]["roomType"]     = inputdata["Rooms"][room_name]["roomType"]
                            inputdata["AirConditioningZone"][room_zone_name]["zoneArea"]     = inputdata["Rooms"][room_name]["zone"][zone_name]["zoneArea"]

                            break

        # 365日×24時間分のスケジュール （365×24の行列を格納した dict型）
        roomScheduleRoom[room_zone_name], roomScheduleLight[room_zone_name], roomSchedulePerson[room_zone_name], roomScheduleOAapp[room_zone_name], roomDayMode[room_zone_name] = \
            bc.get_roomUsageSchedule(inputdata["AirConditioningZone"][room_zone_name]["buildingType"], inputdata["AirConditioningZone"][room_zone_name]["roomType"])


        # 空調対象面積の合計
        roomAreaTotal += inputdata["AirConditioningZone"][room_zone_name]["zoneArea"]



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
            "QroomDc": np.zeros(365),  # 冷房熱取得　[MJ/day]
            "QroomDh": np.zeros(365)   # 暖房熱取得　[MJ/day]
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
    with open(database_directory + 'HeatThermalConductivity.json', 'r') as f:
        HeatThermalConductivity = json.load(f)

    # モデル建物法建材データの読み込み
    with open(database_directory + 'HeatThermalConductivity_model.json', 'r') as f:
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
    with open(database_directory + 'WindowHeatTransferPerformance.json', 'r') as f:
        WindowHeatTransferPerformance = json.load(f)

    with open(database_directory + 'glass2window.json', 'r') as f:
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
            if wall_configure["EnvelopeArea"] > window_total:
                inputdata["EnvelopeSet"][room_zone_name]["WallList"][wall_id]["WallArea"] = wall_configure["EnvelopeArea"] - window_total
            else:
                print(room_zone_name)
                print(wall_configure)
                raise Exception('窓面積が外皮面積よりも大きくなっています')


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

        Qwall_T  = np.zeros(365)  # 壁からの温度差による熱取得 [W/m2]
        Qwall_S  = np.zeros(365)  # 壁からの日射による熱取得 [W/m2]
        Qwall_N  = np.zeros(365)  # 壁からの夜間放射による熱取得（マイナス）[W/m2]
        Qwind_T  = np.zeros(365)  # 窓からの温度差による熱取得 [W/m2]
        Qwind_S  = np.zeros(365)  # 窓からの日射による熱取得 [W/m2]
        Qwind_N  = np.zeros(365)  # 窓からの夜間放射による熱取得（マイナス）[W/m2]

        # 外壁があれば以下を実行
        if room_zone_name in inputdata["EnvelopeSet"]:

            # 壁毎にループ
            for (wall_id, wall_configure) in enumerate( inputdata["EnvelopeSet"][room_zone_name]["WallList"]):

                if wall_configure["WallType"] == "日の当たる外壁":
                
                    ## ① 温度差による熱取得
                    Qwall_T = Qwall_T + wall_configure["UA_wall"] * (Toa_ave - TroomSP) * 24

                    ## ② 日射による熱取得
                    if wall_configure["Direction"] == "水平（上）" or wall_configure["Direction"] == "水平（下）":
                        Qwall_S = Qwall_S + wall_configure["UA_wall"] * 0.8 * 0.04 * \
                            (solor_radiation["直達"]["水平"]+solor_radiation["天空"]["水平"])
                    else:
                        Qwall_S = Qwall_S + wall_configure["UA_wall"] * 0.8 * 0.04 * \
                            (solor_radiation["直達"][ wall_configure["Direction"] ]+solor_radiation["天空"]["垂直"])

                    ## ③ 夜間放射による熱取得（マイナス）
                    if wall_configure["Direction"] == "水平（上）" or wall_configure["Direction"] == "水平（下）":
                        Qwall_N = Qwall_N - wall_configure["UA_wall"] * 0.9 * 0.04 * \
                            (solor_radiation["夜間"]["水平"])
                    else:
                        Qwall_N = Qwall_N - wall_configure["UA_wall"] * 0.9 * 0.04 * \
                            (solor_radiation["夜間"]["垂直"])                    

                elif wall_configure["WallType"] == "日の当たらない外壁":

                    ## ① 温度差による熱取得
                    Qwall_T = Qwall_T + wall_configure["UA_wall"] * (Toa_ave - TroomSP) * 24

                    ## ③ 夜間放射による熱取得（マイナス）
                    if wall_configure["Direction"] == "水平（上）" or wall_configure["Direction"] == "水平（下）":
                        Qwall_N = Qwall_N - wall_configure["UA_wall"] * 0.9 * 0.04 * \
                            (solor_radiation["夜間"]["水平"])
                    else:
                        Qwall_N = Qwall_N - wall_configure["UA_wall"] * 0.9 * 0.04 * \
                            (solor_radiation["夜間"]["垂直"])                    

                elif wall_configure["WallType"] == "地盤に接する外壁":
                
                    ## ① 温度差による熱取得
                    Qwall_T = Qwall_T + wall_configure["UA_wall"] * (np.mean(Toa_ave)* np.ones(365) - TroomSP) * 24

                    ## ③ 夜間放射による熱取得（マイナス） ：　本当はこれは不要。Webproの実装と合わせるために追加。
                    Qwall_N = Qwall_N - wall_configure["UA_wall"] * 0.9 * 0.04 * (solor_radiation["夜間"]["垂直"])   

                elif wall_configure["WallType"] == "地盤に接する外壁_Ver2":  # Webpro Ver2の互換のための処理
                
                    ## ① 温度差による熱取得
                    Qwall_T = Qwall_T + wall_configure["UA_wall"] * (np.mean(Toa_ave)* np.ones(365) - TroomSP) * 24

                    ## ② 日射による熱取得
                    if wall_configure["Direction"] == "水平（上）" or wall_configure["Direction"] == "水平（下）":
                        Qwall_S = Qwall_S + wall_configure["UA_wall"] * 0.8 * 0.04 * \
                            (solor_radiation["直達"]["水平"]+solor_radiation["天空"]["水平"])
                    else:
                        Qwall_S = Qwall_S + wall_configure["UA_wall"] * 0.8 * 0.04 * \
                            (solor_radiation["直達"][ wall_configure["Direction"] ]+solor_radiation["天空"]["垂直"])

                    ## ③ 夜間放射による熱取得（マイナス）
                    if wall_configure["Direction"] == "水平（上）" or wall_configure["Direction"] == "水平（下）":
                        Qwall_N = Qwall_N - wall_configure["UA_wall"] * 0.9 * 0.04 * \
                            (solor_radiation["夜間"]["水平"])
                    else:
                        Qwall_N = Qwall_N - wall_configure["UA_wall"] * 0.9 * 0.04 * \
                            (solor_radiation["夜間"]["垂直"])   


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
                                    
                            if wall_configure["Direction"] == "水平（上）" or wall_configure["Direction"] == "水平（下）":

                                Qwind_S = Qwind_S + shading_daily * \
                                    (window_configure["IA_window"] / 0.88) * \
                                    (solor_radiation["直達_入射角特性込"]["水平"]*0.89 + solor_radiation["天空"]["水平"]*0.808)

                            else:

                                Qwind_S = Qwind_S + shading_daily * \
                                    (window_configure["IA_window"] / 0.88) * \
                                    (solor_radiation["直達_入射角特性込"][ wall_configure["Direction"] ]*0.89 + solor_radiation["天空"]["垂直"]*0.808)


                            ## ③ 夜間放射による熱取得（マイナス）
                            if wall_configure["Direction"] == "水平（上）" or wall_configure["Direction"] == "水平（下）":
                                Qwind_N = Qwind_N - window_configure["UA_window"] * 0.9 * 0.04 * solor_radiation["夜間"]["水平"]
                            else:
                                Qwind_N = Qwind_N - window_configure["UA_window"] * 0.9 * 0.04 * solor_radiation["夜間"]["垂直"]


                        elif wall_configure["WallType"] == "日の当たらない外壁":

                            ## ③ 夜間放射による熱取得（マイナス）
                            Qwind_N = Qwind_N - window_configure["UA_window"] * 0.9 * 0.04 * solor_radiation["夜間"]["水平"]




        #  室面積あたりの熱量に変換 [Wh/m2/日]
        resultJson["Qroom"][room_zone_name]["Qwall_T"] = Qwall_T / inputdata["AirConditioningZone"][room_zone_name]["zoneArea"]
        resultJson["Qroom"][room_zone_name]["Qwall_S"] = Qwall_S / inputdata["AirConditioningZone"][room_zone_name]["zoneArea"]
        resultJson["Qroom"][room_zone_name]["Qwall_N"] = Qwall_N / inputdata["AirConditioningZone"][room_zone_name]["zoneArea"]
        resultJson["Qroom"][room_zone_name]["Qwind_T"] = Qwind_T / inputdata["AirConditioningZone"][room_zone_name]["zoneArea"]
        resultJson["Qroom"][room_zone_name]["Qwind_S"] = Qwind_S / inputdata["AirConditioningZone"][room_zone_name]["zoneArea"]
        resultJson["Qroom"][room_zone_name]["Qwind_N"] = Qwind_N / inputdata["AirConditioningZone"][room_zone_name]["zoneArea"]



    ##----------------------------------------------------------------------------------
    ## 室負荷の計算（解説書 2.4.3、2.4.4）
    ##----------------------------------------------------------------------------------

    ## 室負荷計算のための係数（解説書 A.3）
    with open(database_directory + 'QROOM_COEFFI_AREA'+ inputdata["Building"]["Region"] +'.json', 'r') as f:
        QROOM_COEFFI = json.load(f)


    for room_zone_name in inputdata["AirConditioningZone"]:

        Qroom_CTC = np.zeros(365)
        Qroom_CTH = np.zeros(365)
        Qroom_CSR = np.zeros(365)

        Qcool     = np.zeros(365)
        Qheat     = np.zeros(365)

        # 室が使用されているか否か＝空調運転時間（365日分）
        room_usage = np.sum(roomScheduleRoom[room_zone_name],1)

        btype = inputdata["AirConditioningZone"][room_zone_name]["buildingType"]
        rtype = inputdata["AirConditioningZone"][room_zone_name]["roomType"]

        # 発熱量参照値を読み込む関数（空調）
        (roomHeatGain_Light, roomHeatGain_Person, roomHeatGain_OAapp) = bc.get_roomHeatGain(btype, rtype)

        Heat_light_daily  = np.sum(roomScheduleLight[room_zone_name],1) * roomHeatGain_Light   # 照明からの発熱（日積算）（365日分）
        Heat_person_daily = np.sum(roomSchedulePerson[room_zone_name],1) * roomHeatGain_Person # 人体からの発熱（日積算）（365日分）
        Heat_OAapp_daily  = np.sum(roomScheduleOAapp[room_zone_name],1) * roomHeatGain_OAapp   # 機器からの発熱（日積算）（365日分）

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
                
                # 内部発熱を暖房負荷 Qheat に足す
                Qheat[dd] = Qheat[dd] + ( Heat_light_daily[dd] + Heat_person_daily[dd] + Heat_OAapp_daily[dd] )
                
                # 内部発熱によって暖房負荷がプラスになった場合は、超過分を冷房負荷に加算
                if Qheat[dd] > 0:
                    Qcool[dd] = Qcool[dd] + Qheat[dd]
                    Qheat[dd] = 0
            
            else:

                # 空調OFF時は 0 とする
                Qcool[dd] = 0
                Qheat[dd] = 0


        resultJson["Qroom"][room_zone_name]["QroomDc"] = Qcool * (3600/1000000) * inputdata["AirConditioningZone"][room_zone_name]["zoneArea"]
        resultJson["Qroom"][room_zone_name]["QroomDh"] = Qheat * (3600/1000000) * inputdata["AirConditioningZone"][room_zone_name]["zoneArea"]

        resultJson["Qroom"][room_zone_name]["QroomDc_anual"] = np.sum(Qcool,0)
        resultJson["Qroom"][room_zone_name]["QroomDh_anual"] = np.sum(Qheat,0)


    print('室負荷計算完了')

    if DEBUG:

        for room_zone_name in inputdata["AirConditioningZone"]:

            print( f'--- ゾーン名 {room_zone_name} ---')

            print( f'熱取得_壁温度 Qwall_T: {np.sum(resultJson["Qroom"][room_zone_name]["Qwall_T"],0)}' )
            print( f'熱取得_壁日射 Qwall_S: {np.sum(resultJson["Qroom"][room_zone_name]["Qwall_S"],0)}' )
            print( f'熱取得_壁放射 Qwall_N: {np.sum(resultJson["Qroom"][room_zone_name]["Qwall_N"],0)}' )
            print( f'熱取得_窓温度 Qwind_T: {np.sum(resultJson["Qroom"][room_zone_name]["Qwind_T"],0)}' )
            print( f'熱取得_窓日射 Qwind_S: {np.sum(resultJson["Qroom"][room_zone_name]["Qwind_S"],0)}' )
            print( f'熱取得_窓放射 Qwind_N: {np.sum(resultJson["Qroom"][room_zone_name]["Qwind_N"],0)}' )
            print( f'室負荷（冷房要求）の合計 QroomDc: {np.sum(resultJson["Qroom"][room_zone_name]["QroomDc"],0)}' )
            print( f'室負荷（暖房要求）の合計 QroomDh: {np.sum(resultJson["Qroom"][room_zone_name]["QroomDh"],0)}' )
            print( f'室負荷（冷房要求）の合計 QroomDc_anual: {resultJson["Qroom"][room_zone_name]["QroomDc_anual"]}' )
            print( f'室負荷（暖房要求）の合計 QroomDh_anual: {resultJson["Qroom"][room_zone_name]["QroomDh_anual"]}' )


    #%%
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
            "LdAHUc": np.zeros((365,2)),       # 空調機群の冷房負荷率帯（冷却コイル負荷発生時）
            "TdAHUc": np.zeros((365,2)),       # 空調機群の冷房運転時間（冷却コイル負荷発生時）
            "LdAHUh": np.zeros((365,2)),       # 空調機群の暖房負荷率帯（加熱コイル負荷発生時）
            "TdAHUh": np.zeros((365,2)),       # 空調機群の暖房運転時間（加熱コイル負荷発生時）

            "E_fan_day": np.zeros(365),        # 空調機群のエネルギー消費量
            "E_fan_c_day": np.zeros(365),      # 空調機群のエネルギー消費量（冷房）
            "E_fan_h_day": np.zeros(365),      # 空調機群のエネルギー消費量（暖房）
            "E_AHUaex_day": np.zeros(365),     # 全熱交換器のエネルギー消費量
            
            "TdAHUc_total": np.zeros(365),     # 空調機群の冷房運転時間の合計
            "TdAHUh_total": np.zeros(365),     # 空調機群の暖房運転時間の合計

            "Qahu_remainC": np.zeros(365),     # 空調機群の未処理負荷（冷房）[MJ/day]
            "Qahu_remainH": np.zeros(365),     # 空調機群の未処理負荷（暖房）[MJ/day]

            "energy_consumption_each_LF": np.zeros(len(aveL)), 

            "cooling":{
                "QroomAHU": np.zeros(365),     # 日積算室負荷（冷房要求） [MJ/day]
                "Tahu": np.zeros(365),         # 室負荷が冷房要求である場合の空調機群の運転時間 [h/day]
                "AHUVovc": np.zeros(365),      # 外気冷房運転時の外気風量 [kg/s]
                "Qahu_oac": np.zeros(365),     # 外気冷房による負荷削減効果 [MJ/day]
                "Qahu": np.zeros(365)          # 室負荷が正（冷房要求）であるときの空調負荷（正であれば冷却コイル負荷、負であれば加熱コイル負荷）[MJ/day]
            },
            "heating":{
                "QroomAHU": np.zeros(365),     # 日積算室負荷（暖房要求） [MJ/day]
                "Tahu": np.zeros(365),         # 室負荷が暖房要求である場合の空調機群の運転時間 [h/day]
                "Qahu": np.zeros(365)          # 室負荷が負（暖房要求）であるときの空調負荷（正であれば冷却コイル負荷、負であれば加熱コイル負荷） [MJ/day]
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


    # 両方とも冷暖同時なら、その空調機群は冷暖同時運転可能とする。
    for ahu_name in inputdata["AirHandlingSystem"]:

        if (inputdata["AirHandlingSystem"][ ahu_name ]["isSimultaneousSupply_cooling"] == "有") and \
            (inputdata["AirHandlingSystem"][ ahu_name ]["isSimultaneousSupply_heating"] == "有"):

            inputdata["AirHandlingSystem"][ ahu_name ]["isSimultaneousSupply"] = "有"


    ##----------------------------------------------------------------------------------
    ## 空調機群が処理する日積算室負荷（解説書 2.5.1）
    ##----------------------------------------------------------------------------------
    for room_zone_name in inputdata["AirConditioningZone"]:

        ahu_name = inputdata["AirConditioningZone"][room_zone_name]["AHU_cooling_insideLoad"]

        # 当該空調機群が熱を供給する室の室負荷（冷房要求）を積算する。
        resultJson["AHU"][ ahu_name ]["cooling"]["QroomAHU"] += \
            resultJson["Qroom"][room_zone_name]["QroomDc"]

        # 当該空調機群が熱を供給する室の室負荷（暖房要求）を積算する。
        resultJson["AHU"][ ahu_name ]["heating"]["QroomAHU"] += \
            resultJson["Qroom"][room_zone_name]["QroomDh"]


    ##----------------------------------------------------------------------------------
    ## 空調機群の運転時間（解説書 2.5.2）
    ##----------------------------------------------------------------------------------

    ## 各時刻における運転の有無（365×24の行列）
    for room_zone_name in inputdata["AirConditioningZone"]:

        ahu_name = inputdata["AirConditioningZone"][room_zone_name]["AHU_cooling_insideLoad"]

        # 室の空調有無 roomScheduleRoom（365×24）を加算
        resultJson["AHU"][ ahu_name ]["schedule"] += roomScheduleRoom[room_zone_name]

        # 運転時間帯
        resultJson["AHU"][ ahu_name ]["day_mode"].append( roomDayMode[room_zone_name] )

    for room_zone_name in inputdata["AirConditioningZone"]:

        ahu_name = inputdata["AirConditioningZone"][room_zone_name]["AHU_cooling_outdoorLoad"]

        # 室の空調有無 roomScheduleRoom（365×24）を加算
        resultJson["AHU"][ ahu_name ]["schedule"] += roomScheduleRoom[room_zone_name]

        # 運転時間帯
        resultJson["AHU"][ ahu_name ]["day_mode"].append( roomDayMode[room_zone_name] )



    # 各空調機群の運転時間
    for ahu_name in inputdata["AirHandlingSystem"]:

        # 運転スケジュールの和が「1以上（どこか一部屋は動いている）」であれば、空調機は稼働しているとする。
        resultJson["AHU"][ahu_name]["schedule"][   resultJson["AHU"][ahu_name]["schedule"] > 1   ] = 1

        # 空調機群の日積算運転時間（冷暖合計）
        resultJson["AHU"][ahu_name]["Tahu_total"] = np.sum(resultJson["AHU"][ahu_name]["schedule"], 1)

        # 空調機の運転モード と　外気エンタルピー
        if "終日" in resultJson["AHU"][ahu_name]["day_mode"]:
            # 一つでも「終日」があれば
            resultJson["AHU"][ahu_name]["day_mode"] = "終日"
            resultJson["AHU"][ahu_name]["HoaDayAve"] = Hoa_ave
        elif resultJson["AHU"][ahu_name]["day_mode"].count("昼") == len(resultJson["AHU"][ahu_name]["day_mode"]):
            # 全て「昼」であれば
            resultJson["AHU"][ahu_name]["day_mode"] = "昼"
            resultJson["AHU"][ahu_name]["HoaDayAve"] = Hoa_day
        elif resultJson["AHU"][ahu_name]["day_mode"].count("夜") == len(resultJson["AHU"][ahu_name]["day_mode"]): 
            # 全て夜であれば
            resultJson["AHU"][ahu_name]["day_mode"] = "夜"
            resultJson["AHU"][ahu_name]["HoaDayAve"] = Hoa_ngt
        else: 
            # 「昼」と「夜」が混在する場合は「終日とする。
            resultJson["AHU"][ahu_name]["day_mode"]  = "終日"
            resultJson["AHU"][ahu_name]["HoaDayAve"] = Hoa_ave


        for dd in range(0,365):

            if resultJson["AHU"][ahu_name]["Tahu_total"][dd] == 0:

                # 日空調時間が0であれば、冷暖房空調時間は0とする。
                resultJson["AHU"][ahu_name]["cooling"]["Tahu"][dd] = 0
                resultJson["AHU"][ahu_name]["heating"]["Tahu"][dd] = 0

            else:

                if (resultJson["AHU"][ahu_name]["cooling"]["QroomAHU"][dd] == 0) and \
                    (resultJson["AHU"][ahu_name]["heating"]["QroomAHU"][dd] == 0):

                    # 外調機を想定（空調機は動いているが、冷房のTahuも暖房のTahuも0である場合）
                    resultJson["AHU"][ahu_name]["cooling"]["Tahu"][dd] = resultJson["AHU"][ahu_name]["Tahu_total"][dd]   # 外調機の場合は「冷房側」に運転時間を押しつける。
                    resultJson["AHU"][ahu_name]["heating"]["Tahu"][dd] = 0
            
                elif resultJson["AHU"][ahu_name]["cooling"]["QroomAHU"][dd] == 0:

                    resultJson["AHU"][ahu_name]["cooling"]["Tahu"][dd] = 0
                    resultJson["AHU"][ahu_name]["heating"]["Tahu"][dd] = resultJson["AHU"][ahu_name]["Tahu_total"][dd]
        
                elif resultJson["AHU"][ahu_name]["heating"]["QroomAHU"][dd] == 0:

                    resultJson["AHU"][ahu_name]["cooling"]["Tahu"][dd] = resultJson["AHU"][ahu_name]["Tahu_total"][dd]
                    resultJson["AHU"][ahu_name]["heating"]["Tahu"][dd] = 0

                else:

                    if abs(resultJson["AHU"][ahu_name]["cooling"]["QroomAHU"][dd]) < abs(resultJson["AHU"][ahu_name]["heating"]["QroomAHU"][dd]):
                        
                        # 暖房負荷の方が大きい場合
                        ratio = abs(resultJson["AHU"][ahu_name]["cooling"]["QroomAHU"][dd]) / \
                            ( abs(resultJson["AHU"][ahu_name]["cooling"]["QroomAHU"][dd]) + abs(resultJson["AHU"][ahu_name]["heating"]["QroomAHU"][dd]) )

                        resultJson["AHU"][ahu_name]["cooling"]["Tahu"][dd] = math.ceil( resultJson["AHU"][ahu_name]["Tahu_total"][dd] * ratio )
                        resultJson["AHU"][ahu_name]["heating"]["Tahu"][dd] = resultJson["AHU"][ahu_name]["Tahu_total"][dd] - resultJson["AHU"][ahu_name]["cooling"]["Tahu"][dd]

                    else:

                        # 冷房負荷の方が大きい場合
                        ratio = abs(resultJson["AHU"][ahu_name]["heating"]["QroomAHU"][dd]) / \
                            ( abs(resultJson["AHU"][ahu_name]["cooling"]["QroomAHU"][dd]) + abs(resultJson["AHU"][ahu_name]["heating"]["QroomAHU"][dd]) )

                        resultJson["AHU"][ahu_name]["heating"]["Tahu"][dd] = math.ceil( resultJson["AHU"][ahu_name]["Tahu_total"][dd] * ratio )
                        resultJson["AHU"][ahu_name]["cooling"]["Tahu"][dd] = resultJson["AHU"][ahu_name]["Tahu_total"][dd] - resultJson["AHU"][ahu_name]["heating"]["Tahu"][dd]


    ##----------------------------------------------------------------------------------
    ## 外気負荷[kW]の算出（解説書 2.5.3）
    ##----------------------------------------------------------------------------------

    # 外気導入量 [m3/h]
    for ahu_name in inputdata["AirHandlingSystem"]:
        inputdata["AirHandlingSystem"][ ahu_name ]["outdoorAirVolume_cooling"] = 0
        inputdata["AirHandlingSystem"][ ahu_name ]["outdoorAirVolume_heating"] = 0

    for room_zone_name in inputdata["AirConditioningZone"]:

        # 各室の外気導入量 [m3/h]
        inputdata["AirConditioningZone"][room_zone_name]["outdoorAirVolume"] = \
            bc.get_roomOutdoorAirVolume( inputdata["AirConditioningZone"][room_zone_name]["buildingType"], inputdata["AirConditioningZone"][room_zone_name]["roomType"] ) * \
            inputdata["AirConditioningZone"][room_zone_name]["zoneArea"]

        # 冷房運転時の外気風量 [m3/h]
        inputdata["AirHandlingSystem"][ inputdata["AirConditioningZone"][room_zone_name]["AHU_cooling_outdoorLoad"] ]["outdoorAirVolume_cooling"] += \
            inputdata["AirConditioningZone"][room_zone_name]["outdoorAirVolume"]

        # 暖房運転時の外気風量 [m3/h]
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

            if resultJson["AHU"][ahu_name]["Tahu_total"][dd] > 0:

                # 運転モードによって場合分け
                if ac_mode[dd] == "暖房":
                    
                    ahuVoa  = inputdata["AirHandlingSystem"][ahu_name]["outdoorAirVolume_heating"]
                    ahuaexV = inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangerAirVolume"]

                    # 全熱交換機を通過する風量 [m3/h]
                    if ahuaexV > ahuVoa:
                        inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangerAirVolume"] = ahuVoa
                    elif ahuaexV <= 0:
                        inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangerAirVolume"] = 0
                    else:
                        inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangerAirVolume"] = ahuaexV
                    
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
                                    inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangerAirVolume"] * inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioHeating"] ) *1.293/3600


                elif (ac_mode[dd] == "中間") or (ac_mode[dd] == "冷房"):
                    
                    ahuVoa  = inputdata["AirHandlingSystem"][ahu_name]["outdoorAirVolume_cooling"]
                    ahuaexV = inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangerAirVolume"]

                    # 全熱交換機を通過する風量 [m3/h]
                    if ahuaexV > ahuVoa:
                        inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangerAirVolume"] = ahuVoa
                    elif ahuaexV <= 0:
                        inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangerAirVolume"] = 0
                    else:
                        inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangerAirVolume"] = ahuaexV

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
                                    inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangerAirVolume"] * inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangeRatioCooling"] ) *1.293/3600


    ##----------------------------------------------------------------------------------
    ## 外気冷房制御による負荷削減量（解説書 2.5.4）
    ##----------------------------------------------------------------------------------

    for ahu_name in inputdata["AirHandlingSystem"]:

        for dd in range(0,365):

            if resultJson["AHU"][ahu_name]["Tahu_total"][dd] > 0:

                # 外気冷房効果の推定
                if (inputdata["AirHandlingSystem"][ahu_name]["isEconomizer"] == "有") and (resultJson["AHU"][ahu_name]["cooling"]["Tahu"][dd]>0):   # 外気冷房ONで冷房運転がされていたら
                    
                    # 外気冷房運転時の外気風量 [kg/s]
                    resultJson["AHU"][ahu_name]["cooling"]["AHUVovc"][dd] = \
                        resultJson["AHU"][ahu_name]["cooling"]["QroomAHU"][dd] / \
                        ((Hroom[dd]-resultJson["AHU"][ahu_name]["HoaDayAve"][dd]) * (3600/1000) * resultJson["AHU"][ahu_name]["cooling"]["Tahu"][dd])
                    
                    # 上限・下限
                    if resultJson["AHU"][ahu_name]["cooling"]["AHUVovc"][dd] < inputdata["AirHandlingSystem"][ahu_name]["outdoorAirVolume_cooling"] *1.293/3600:
                        resultJson["AHU"][ahu_name]["cooling"]["AHUVovc"][dd] = inputdata["AirHandlingSystem"][ahu_name]["outdoorAirVolume_cooling"] *1.293/3600  # 下限（外気取入量）
                    elif resultJson["AHU"][ahu_name]["cooling"]["AHUVovc"][dd] > inputdata["AirHandlingSystem"][ahu_name]["EconomizerMaxAirVolume"] *1.293/3600:
                        resultJson["AHU"][ahu_name]["cooling"]["AHUVovc"][dd] = inputdata["AirHandlingSystem"][ahu_name]["EconomizerMaxAirVolume"] *1.293/3600  # 上限（給気風量 [m3/h]→[kg/s]）
                    
                    # 追加すべき外気量（外気冷房用の追加分のみ）[kg/s]
                    resultJson["AHU"][ahu_name]["cooling"]["AHUVovc"][dd] = \
                        resultJson["AHU"][ahu_name]["cooling"]["AHUVovc"][dd] - inputdata["AirHandlingSystem"][ahu_name]["outdoorAirVolume_cooling"] *1.293/3600

                # 外気冷房による負荷削減効果 [MJ/day]
                if (inputdata["AirHandlingSystem"][ahu_name]["isEconomizer"] == "有"): # 外気冷房があれば

                    if resultJson["AHU"][ahu_name]["cooling"]["AHUVovc"][dd] > 0: # 外冷時風量＞０であれば

                        resultJson["AHU"][ahu_name]["cooling"]["Qahu_oac"][dd] = \
                            resultJson["AHU"][ahu_name]["cooling"]["AHUVovc"][dd] * (Hroom[dd]-resultJson["AHU"][ahu_name]["HoaDayAve"][dd])*3600/1000*\
                            resultJson["AHU"][ahu_name]["cooling"]["Tahu"][dd]


    ##----------------------------------------------------------------------------------
    ## 日積算空調負荷 Qahu_c, Qahu_h の算出（解説書 2.5.5）
    ##----------------------------------------------------------------------------------

    for ahu_name in inputdata["AirHandlingSystem"]:

        for dd in range(0,365):

            # 外気負荷のみの処理が要求される空調機群である場合(処理上、「室負荷が冷房要求である場合」 として扱う)
            if (resultJson["AHU"][ahu_name]["cooling"]["Tahu"][dd] == 0) and (resultJson["AHU"][ahu_name]["heating"]["Tahu"][dd] == 0):

                if (inputdata["AirHandlingSystem"][ahu_name]["isOutdoorAirCut"] == "無"):

                    resultJson["AHU"][ahu_name]["cooling"]["Qahu"][dd] = \
                        resultJson["AHU"][ahu_name]["qoaAHU"][dd] * resultJson["AHU"][ahu_name]["Tahu_total"][dd] * 3600/1000

                else:

                    if resultJson["AHU"][ahu_name]["Tahu_total"][dd] > 1:
                        resultJson["AHU"][ahu_name]["cooling"]["Qahu"][dd] = \
                            resultJson["AHU"][ahu_name]["qoaAHU"][dd] * (resultJson["AHU"][ahu_name]["Tahu_total"][dd]-1) * 3600/1000

                    else:

                        resultJson["AHU"][ahu_name]["cooling"]["Qahu"][dd] = \
                            resultJson["AHU"][ahu_name]["qoaAHU"][dd] * resultJson["AHU"][ahu_name]["Tahu_total"][dd] * 3600/1000

                resultJson["AHU"][ahu_name]["heating"]["Qahu"][dd] = 0

            else:  # 室負荷と外気負荷の両方を処理が要求される空調機群である場合

                # 冷房要求の室負荷を処理する必要がある場合
                if resultJson["AHU"][ahu_name]["cooling"]["Tahu"][dd] > 0:
                    
                    if (inputdata["AirHandlingSystem"][ahu_name]["isOutdoorAirCut"] == "有") and \
                        (resultJson["AHU"][ahu_name]["cooling"]["Tahu"][dd] > 1) and \
                        (resultJson["AHU"][ahu_name]["cooling"]["Tahu"][dd] >= resultJson["AHU"][ahu_name]["heating"]["Tahu"][dd]):

                        # 室負荷が正（冷房要求）であるときの空調負荷（正であれば冷却コイル負荷、負であれば加熱コイル負荷）
                        resultJson["AHU"][ahu_name]["cooling"]["Qahu"][dd] = \
                            resultJson["AHU"][ahu_name]["cooling"]["QroomAHU"][dd] + \
                            resultJson["AHU"][ahu_name]["qoaAHU"][dd] * (resultJson["AHU"][ahu_name]["cooling"]["Tahu"][dd] - 1) * 3600/1000
        
                    else:

                        # 室負荷が正（冷房要求）であるときの空調負荷（正であれば冷却コイル負荷、負であれば加熱コイル負荷）
                        resultJson["AHU"][ahu_name]["cooling"]["Qahu"][dd] = \
                            resultJson["AHU"][ahu_name]["cooling"]["QroomAHU"][dd] + \
                            resultJson["AHU"][ahu_name]["qoaAHU"][dd] * (resultJson["AHU"][ahu_name]["cooling"]["Tahu"][dd]) * 3600/1000

                # 暖房要求の室負荷を処理する必要がある場合
                if resultJson["AHU"][ahu_name]["heating"]["Tahu"][dd] > 0:

                    if (inputdata["AirHandlingSystem"][ahu_name]["isOutdoorAirCut"] == "有") and \
                        (resultJson["AHU"][ahu_name]["heating"]["Tahu"][dd] > 1) and \
                        (resultJson["AHU"][ahu_name]["cooling"]["Tahu"][dd] < resultJson["AHU"][ahu_name]["heating"]["Tahu"][dd]):

                        # 室負荷が負（暖房要求）であるときの空調負荷（正であれば冷却コイル負荷、負であれば加熱コイル負荷）
                        resultJson["AHU"][ahu_name]["heating"]["Qahu"][dd] = \
                            resultJson["AHU"][ahu_name]["heating"]["QroomAHU"][dd] + \
                            resultJson["AHU"][ahu_name]["qoaAHU"][dd] * (resultJson["AHU"][ahu_name]["heating"]["Tahu"][dd] - 1) * 3600/1000
        
                    else:

                        # 室負荷が負（暖房要求）であるときの空調負荷（正であれば冷却コイル負荷、負であれば加熱コイル負荷）
                        resultJson["AHU"][ahu_name]["heating"]["Qahu"][dd] = \
                            resultJson["AHU"][ahu_name]["heating"]["QroomAHU"][dd] + \
                            resultJson["AHU"][ahu_name]["qoaAHU"][dd] * (resultJson["AHU"][ahu_name]["heating"]["Tahu"][dd]) * 3600/1000


    print('空調負荷計算完了')

    if DEBUG:

        for ahu_name in inputdata["AirHandlingSystem"]:

            print( f'--- 空調機群名 {ahu_name} ---')

            print( f'外気負荷 qoaAHU {np.sum(resultJson["AHU"][ahu_name]["qoaAHU"],0)}' )
            print( f'外気導入量 outdoorAirVolume_cooling {inputdata["AirHandlingSystem"][ahu_name]["outdoorAirVolume_cooling"]} m3/h' )
            print( f'外気冷房時最大風量 EconomizerMaxAirVolume {inputdata["AirHandlingSystem"][ahu_name]["EconomizerMaxAirVolume"]} m3/h' )
            print( f'外気冷房時風量 AHUVovc {np.sum(resultJson["AHU"][ahu_name]["cooling"]["AHUVovc"],0)}' )
            print( f'外気冷房効果 Qahu_oac： {np.sum(resultJson["AHU"][ahu_name]["cooling"]["Qahu_oac"],0)}' )
            print( f'室負荷が正（冷房要求）であるときの空調機群の運転時間 Tahu： {np.sum(resultJson["AHU"][ahu_name]["cooling"]["Tahu"],0)} 時間' )
            print( f'室負荷が負（暖房要求）であるときの空調機群の運転時間 Tahu： {np.sum(resultJson["AHU"][ahu_name]["heating"]["Tahu"],0)} 時間' )
            print( f'室負荷が正（冷房要求）であるときの空調負荷 Qahu： {np.sum(resultJson["AHU"][ahu_name]["cooling"]["Qahu"],0)}' )
            print( f'室負荷が負（暖房要求）であるときの空調負荷 Qahu： {np.sum(resultJson["AHU"][ahu_name]["heating"]["Qahu"],0)}' )

            print( f'空調機群 冷暖同時供給の有無： {inputdata["AirHandlingSystem"][ahu_name]["isSimultaneousSupply"]}' )


    ##----------------------------------------------------------------------------------
    ## 空調機群の負荷率（解説書 2.5.6）
    ##----------------------------------------------------------------------------------

    for ahu_name in inputdata["AirHandlingSystem"]:

        Tdc = np.zeros((365,2))
        Tdh = np.zeros((365,2))
        Mxc = np.zeros((365,2)) # 日別データ
        Mxh = np.zeros((365,2)) # 日別データ

        for requirement_type in ["cooling", "heating"]:

            La  = np.zeros(365)

            # 負荷率の算出
            if requirement_type == "cooling": # 室負荷が正（冷房要求）であるとき

                # 室負荷が正（冷房要求）であるときの平均負荷率 La [-]
                for dd in range(0,365):
                    if resultJson["AHU"][ahu_name]["cooling"]["Qahu"][dd] >= 0 and resultJson["AHU"][ahu_name]["cooling"]["Tahu"][dd] != 0:
                        # 空調負荷が正（冷却コイル負荷）である場合　→　定格冷却能力で除して負荷率を求める。
                        La[dd] = (resultJson["AHU"][ahu_name]["cooling"]["Qahu"][dd] / resultJson["AHU"][ahu_name]["cooling"]["Tahu"][dd] *1000/3600) / \
                            inputdata["AirHandlingSystem"][ahu_name]["RatedCapacityCooling"]   
                    elif resultJson["AHU"][ahu_name]["cooling"]["Tahu"][dd] != 0:
                        # 空調負荷が負（加熱コイル負荷）である場合　→　定格加熱能力で除して負荷率を求める。
                        La[dd] = (resultJson["AHU"][ahu_name]["cooling"]["Qahu"][dd] / resultJson["AHU"][ahu_name]["cooling"]["Tahu"][dd] *1000/3600) / \
                            inputdata["AirHandlingSystem"][ahu_name]["RatedCapacityHeating"]

                # 日積算運転時間 Ta [時間]
                Ta = resultJson["AHU"][ahu_name]["cooling"]["Tahu"]
                
                if DEBUG:
                    resultJson["AHU"][ahu_name]["Ta_cooling"] = copy.deepcopy(Ta)


            elif requirement_type == "heating": # 室負荷が負（暖房要求）であるとき
                
                # 室負荷が負（暖房要求）であるときの平均負荷率 La [-]
                for dd in range(0,365):
                    if resultJson["AHU"][ahu_name]["heating"]["Qahu"][dd] <= 0 and resultJson["AHU"][ahu_name]["heating"]["Tahu"][dd] != 0:
                        # 空調負荷が負（加熱コイル負荷）である場合　→　定格加熱能力で除して負荷率を求める。
                        La[dd] = (resultJson["AHU"][ahu_name]["heating"]["Qahu"][dd] / resultJson["AHU"][ahu_name]["heating"]["Tahu"][dd] *1000/3600) / \
                            inputdata["AirHandlingSystem"][ahu_name]["RatedCapacityHeating"]   
                    elif resultJson["AHU"][ahu_name]["heating"]["Tahu"][dd] != 0:
                        # 空調負荷が正（冷却コイル負荷）である場合　→　定格冷却能力で除して負荷率を求める。
                        La[dd] = (resultJson["AHU"][ahu_name]["heating"]["Qahu"][dd] / resultJson["AHU"][ahu_name]["heating"]["Tahu"][dd] *1000/3600) / \
                            inputdata["AirHandlingSystem"][ahu_name]["RatedCapacityCooling"]

                # 日積算運転時間 Ta [時間]
                Ta = resultJson["AHU"][ahu_name]["heating"]["Tahu"]

                if DEBUG:
                    resultJson["AHU"][ahu_name]["Ta_heating"] = copy.deepcopy(Ta)
                    

            # 定格能力＞０　→　AHU or FCU があれば
            if (inputdata["AirHandlingSystem"][ahu_name]["RatedCapacityCooling"] > 0) or (inputdata["AirHandlingSystem"][ahu_name]["RatedCapacityHeating"] > 0):
                
                # 冷暖同時運転が「有」である場合（季節に依らず、冷却コイル負荷も加熱コイル負荷も処理する）
                if inputdata["AirHandlingSystem"][ahu_name]["isSimultaneousSupply"] == "有":  
                    
                    for dd in range(0,365):
                        
                        if np.isnan(La[dd]) == False:

                            if La[dd] > 0:    # 負荷率が正（冷却コイル負荷）である場合
                                
                                # 負荷率帯インデックスの決定
                                ix = count_Matrix(La[dd], mxL)
                                
                                if requirement_type == "cooling":     # 室負荷が正（冷房要求）である場合
                                    Mxc[dd,0] = ix                    # 0列目は、室負荷が正（冷房要求）であるときの冷却コイル負荷の負荷率帯インデックス
                                    Tdc[dd,0] += Ta[dd]               # 0列目は、室負荷が正（冷房要求）であるときの空調運転時間
                                elif requirement_type == "heating":   # 室負荷が負（暖房要求）である場合
                                    Mxc[dd,1] = ix                    # 1列目は、室負荷が負（暖房要求）であるときの冷却コイル負荷の負荷率帯インデックス
                                    Tdc[dd,1] += Ta[dd]               # 1列目は、室負荷が負（暖房要求）であるときの空調運転時間
                                
                            elif La[dd] < 0:  # 負荷率が負（加熱コイル負荷）である場合

                                # 負荷率帯インデックスの決定
                                ix = count_Matrix((-1)*La[dd], mxL)
                                
                                if requirement_type == "cooling":     # 室負荷が正（冷房要求）である場合
                                    Mxh[dd,0] = ix                    # 0列目は、室負荷が正（冷房要求）であるときの加熱コイル負荷の負荷率帯インデックス
                                    Tdh[dd,0] += Ta[dd]               # 0列目は、室負荷が正（冷房要求）であるときの空調運転時間
                                elif requirement_type == "heating":   # 室負荷が負（暖房要求）である場合
                                    Mxh[dd,1] = ix                    # 1列目は、室負荷が負（暖房要求）であるときの加熱コイル負荷の負荷率帯インデックス
                                    Tdh[dd,1] += Ta[dd]               # 1列目は、室負荷が負（暖房要求）であるときの空調運転時間


                # 冷暖同時供給が「無」である場合（季節により、冷却コイル負荷か加熱コイル負荷のどちらか一方を処理する）
                elif inputdata["AirHandlingSystem"][ahu_name]["isSimultaneousSupply"] == "無":  

                    for dd in range(0,365):

                        if np.isnan(La[dd]) == False:   # 日付dの負荷率が NaN で無い場合

                            # 冷房モード で動く期間の場合、かつ、空調負荷（冷却コイル負荷か加熱コイル負荷）が発生しているとき
                            if (La[dd] != 0) and (ac_mode[dd] == "冷房" or ac_mode[dd] == "中間"):   

                                # 負荷率帯インデックスの決定
                                ix = count_Matrix(La[dd], mxL)

                                if requirement_type == "cooling":     # 室負荷が正（冷房要求）である場合
                                    Mxc[dd,0] = ix                    # 0列目は、室負荷が正（冷房要求）であるときの空調負荷の負荷率帯インデックス（ただし、加熱コイル負荷は 負荷率帯 0　となる）
                                    Tdc[dd,0] += Ta[dd]               # 0列目は、室負荷が正（冷房要求）であるときの空調運転時間(加熱コイル負荷発生時も 負荷率=0として送風機は動く想定)
                                elif requirement_type == "heating":   # 室負荷が負（暖房要求）である場合
                                    Mxc[dd,1] = ix                    # 1列目は、室負荷が負（暖房要求）であるときの空調負荷の負荷率帯インデックス（ただし、加熱コイル負荷は 負荷率帯 0　となる）
                                    Tdc[dd,1] += Ta[dd]               # 1列目は、室負荷が負（暖房要求）であるときの空調運転時間(加熱コイル負荷発生時も 負荷率=0として送風機は動く想定)

                            # 暖房モード で動く期間の場合、かつ、空調負荷（冷却コイル負荷か加熱コイル負荷）が発生しているとき
                            elif (La[dd] != 0) and (ac_mode[dd] == "暖房"):  

                                # 負荷率帯インデックスの決定
                                ix = count_Matrix((-1)*La[dd], mxL)

                                if requirement_type == "cooling":     # 室負荷が正（冷房要求）である場合
                                    Mxh[dd,0] = ix                    # 0列目は、室負荷が正（冷房要求）であるときの空調負荷の負荷率帯インデックス（ただし、冷却コイル負荷は 負荷率帯 0　となる）
                                    Tdh[dd,0] += Ta[dd]               # 0列目は、室負荷が正（冷房要求）であるときの空調運転時間(冷却コイル負荷発生時も 負荷率=0として送風機は動く想定)
                                elif requirement_type == "heating":   # 室負荷が負（暖房要求）である場合
                                    Mxh[dd,1] = ix                    # 1列目は、室負荷が負（暖房要求）であるときの空調負荷の負荷率帯インデックス（ただし、冷却コイル負荷は 負荷率帯 0　となる）
                                    Tdh[dd,1] += Ta[dd]               # 1列目は、室負荷が負（暖房要求）であるときの空調運転時間(冷却コイル負荷発生時も 負荷率=0として送風機は動く想定)


        resultJson["AHU"][ahu_name]["LdAHUc"] = Mxc   # 空調負荷が正（冷却コイル負荷）である場合の負荷率帯インデックス（0列目：室負荷が正である場合、1列目：室負荷が負である場合）
        resultJson["AHU"][ahu_name]["TdAHUc"] = Tdc   # 空調負荷が正（冷却コイル負荷）である場合の運転時間（0列目：室負荷が正である場合、1列目：室負荷が負である場合）
        resultJson["AHU"][ahu_name]["LdAHUh"] = Mxh   # 空調負荷が負（加熱コイル負荷）である場合の負荷率帯インデックス（0列目：室負荷が正である場合、1列目：室負荷が負である場合）
        resultJson["AHU"][ahu_name]["TdAHUh"] = Tdh   # 空調負荷が負（加熱コイル負荷）である場合の運転時間（0列目：室負荷が正である場合、1列目：室負荷が負である場合）


    if DEBUG:

        for ahu_name in inputdata["AirHandlingSystem"]:

            print( f'空調負荷が正（冷却コイル負荷）である場合の負荷率帯インデックス LdAHUc {np.sum(resultJson["AHU"][ahu_name]["LdAHUc"],0)}' )
            print( f'空調負荷が正（冷却コイル負荷）である場合の運転時間 TdAHUc {np.sum(resultJson["AHU"][ahu_name]["TdAHUc"],0)}' )
            print( f'空調負荷が負（加熱コイル負荷）である場合の負荷率帯インデックス LdAHUh {np.sum(resultJson["AHU"][ahu_name]["LdAHUh"],0)}' )
            print( f'空調負荷が負（加熱コイル負荷）である場合の運転時間 TdAHUh {np.sum(resultJson["AHU"][ahu_name]["TdAHUh"],0)}' )


            # マトリックスの再現
            LAHUc0 = np.zeros(11)
            LAHUc1 = np.zeros(11)
            LAHUh0 = np.zeros(11)
            LAHUh1 = np.zeros(11)
            for dd in range(0,365):
                LAHUc0[ int(resultJson["AHU"][ahu_name]["LdAHUc"][dd][0]-1) ] += resultJson["AHU"][ahu_name]["TdAHUc"][dd][0]
                LAHUc1[ int(resultJson["AHU"][ahu_name]["LdAHUc"][dd][1]-1) ] += resultJson["AHU"][ahu_name]["TdAHUc"][dd][1]
                LAHUh0[ int(resultJson["AHU"][ahu_name]["LdAHUh"][dd][0]-1) ] += resultJson["AHU"][ahu_name]["TdAHUh"][dd][0]
                LAHUh1[ int(resultJson["AHU"][ahu_name]["LdAHUh"][dd][1]-1) ] += resultJson["AHU"][ahu_name]["TdAHUh"][dd][1]

            # np.savetxt("Tac.txt", resultJson["AHU"][ahu_name]["Ta_cooling"])
            # np.savetxt("Tah.txt", resultJson["AHU"][ahu_name]["Ta_heating"])
            # np.savetxt("LdAHUc.txt", resultJson["AHU"][ahu_name]["LdAHUc"])
            # np.savetxt("TdAHUc.txt", resultJson["AHU"][ahu_name]["TdAHUc"])
            # np.savetxt("LdAHUh.txt", resultJson["AHU"][ahu_name]["LdAHUh"])
            # np.savetxt("TdAHUh.txt", resultJson["AHU"][ahu_name]["TdAHUh"])
            
    ##----------------------------------------------------------------------------------
    ## 風量制御方式によって定まる係数（解説書 2.5.7）
    ##----------------------------------------------------------------------------------

    ## 搬送系制御に関する係数
    with open(database_directory + 'FLOWCONTROL.json', 'r') as f:
        FLOWCONTROL = json.load(f)

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

    if DEBUG:

        for ahu_name in inputdata["AirHandlingSystem"]:
            print( f'--- 空調機群名 {ahu_name} ---')
            for unit_id, unit_configure in enumerate(inputdata["AirHandlingSystem"][ahu_name]["AirHandlingUnit"]):
                print( f'--- {unit_id+1} 台目の送風機 ---')
                print(f'負荷率帯毎のエネルギー消費量 energy_consumption_ratio {inputdata["AirHandlingSystem"][ahu_name]["AirHandlingUnit"][unit_id]["energy_consumption_ratio"]}')


    ##----------------------------------------------------------------------------------
    ## 送風機単体の定格消費電力（解説書 2.5.8）
    ##----------------------------------------------------------------------------------

    for ahu_name in inputdata["AirHandlingSystem"]:

        for unit_id, unit_configure in enumerate(inputdata["AirHandlingSystem"][ahu_name]["AirHandlingUnit"]):

            inputdata["AirHandlingSystem"][ahu_name]["AirHandlingUnit"][unit_id]["FanPowerConsumption_total"] = 0

            if unit_configure["FanPowerConsumption"] != None:

                # 送風機の定格消費電力 kW = 1台あたりの消費電力 kW × 台数
                inputdata["AirHandlingSystem"][ahu_name]["AirHandlingUnit"][unit_id]["FanPowerConsumption_total"] = \
                    unit_configure["FanPowerConsumption"] * unit_configure["Number"]

            if DEBUG:
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

            if DEBUG:
                print( f'負荷率帯別の送風機消費電力: \n {resultJson["AHU"][ahu_name]["energy_consumption_each_LF"]}')

    ##----------------------------------------------------------------------------------
    ## 全熱交換器の消費電力 （解説書 2.5.11）
    ##----------------------------------------------------------------------------------

    for ahu_name in inputdata["AirHandlingSystem"]:
        for dd in range(0,365):

            # 冷房負荷が暖房負荷が発生していれば、全熱交換器は動いたとみなす。
            if (resultJson["AHU"][ahu_name]["LdAHUc"][dd,0] > 0) or (resultJson["AHU"][ahu_name]["LdAHUc"][dd,1] > 0) or \
                (resultJson["AHU"][ahu_name]["LdAHUh"][dd,0] > 0) or (resultJson["AHU"][ahu_name]["LdAHUh"][dd,1] > 0):

                # 全熱交換器の消費電力量 MWh = 運転時間 h × 消費電力 kW
                resultJson["AHU"][ahu_name]["E_AHUaex_day"][dd] += \
                    resultJson["AHU"][ahu_name]["Tahu_total"][dd] * inputdata["AirHandlingSystem"][ahu_name]["AirHeatExchangerPowerConsumption"] / 1000


    ##----------------------------------------------------------------------------------
    ## 空調機群の年間一次エネルギー消費量 （解説書 2.5.12）
    ##----------------------------------------------------------------------------------

    for ahu_name in inputdata["AirHandlingSystem"]:
        for dd in range(0,365):

            # 室負荷が正（冷房要求）であり、空調負荷が正（冷却コイル負荷）である場合
            if resultJson["AHU"][ahu_name]["LdAHUc"][dd,0] > 0:

                # 負荷率帯番号
                iL = int(resultJson["AHU"][ahu_name]["LdAHUc"][dd,0] - 1)

                # 空調負荷が正（冷却コイル負荷）の時の送風機等の消費電力　MWh
                resultJson["AHU"][ahu_name]["E_fan_c_day"][dd] += \
                    resultJson["AHU"][ahu_name]["energy_consumption_each_LF"][iL] / 1000 * resultJson["AHU"][ahu_name]["TdAHUc"][dd,0]

                # 運転時間の合計 h
                resultJson["AHU"][ahu_name]["TdAHUc_total"][dd] += resultJson["AHU"][ahu_name]["TdAHUc"][dd,0]


            # 室負荷が負（暖房要求）であり、空調負荷が正（冷却コイル負荷）である場合
            if resultJson["AHU"][ahu_name]["LdAHUc"][dd,1] > 0:

                # 負荷率帯番号
                iL = int(resultJson["AHU"][ahu_name]["LdAHUc"][dd,1] - 1)

                # 空調負荷が正（冷却コイル負荷）の時の送風機等の消費電力　MWh
                resultJson["AHU"][ahu_name]["E_fan_c_day"][dd] += \
                    resultJson["AHU"][ahu_name]["energy_consumption_each_LF"][iL] / 1000 * resultJson["AHU"][ahu_name]["TdAHUc"][dd,1]

                # 運転時間の合計 h
                resultJson["AHU"][ahu_name]["TdAHUc_total"][dd] += resultJson["AHU"][ahu_name]["TdAHUc"][dd,1]


            # 室負荷が正（冷房要求）であり、空調負荷が負（加熱コイル負荷）である場合
            if resultJson["AHU"][ahu_name]["LdAHUh"][dd,0] > 0:

                # 負荷率帯番号
                iL = int(resultJson["AHU"][ahu_name]["LdAHUh"][dd,0] - 1)

                # 空調負荷が負（加熱コイル負荷）の時の送風機等の消費電力　MWh
                resultJson["AHU"][ahu_name]["E_fan_h_day"][dd] += \
                    resultJson["AHU"][ahu_name]["energy_consumption_each_LF"][iL] / 1000 * resultJson["AHU"][ahu_name]["TdAHUh"][dd,0]

                # 運転時間の合計 h
                resultJson["AHU"][ahu_name]["TdAHUh_total"][dd] += resultJson["AHU"][ahu_name]["TdAHUh"][dd,0]


            # 室負荷が負（暖房要求）であり、空調負荷が負（加熱コイル負荷）である場合
            if resultJson["AHU"][ahu_name]["LdAHUh"][dd,1] > 0:

                # 負荷率帯番号
                iL = int(resultJson["AHU"][ahu_name]["LdAHUh"][dd,1] - 1)

                # 空調負荷が負（加熱コイル負荷）の時の送風機等の消費電力　MWh
                resultJson["AHU"][ahu_name]["E_fan_h_day"][dd] += \
                    resultJson["AHU"][ahu_name]["energy_consumption_each_LF"][iL] / 1000 * resultJson["AHU"][ahu_name]["TdAHUh"][dd,1]

                # 運転時間の合計 h
                resultJson["AHU"][ahu_name]["TdAHUh_total"][dd] += resultJson["AHU"][ahu_name]["TdAHUh"][dd,1]


            # 空調負荷が正（冷却コイル負荷）のときと負（加熱コイル負荷）のときを合計する。
            resultJson["AHU"][ahu_name]["E_fan_day"][dd] = resultJson["AHU"][ahu_name]["E_fan_c_day"][dd] + resultJson["AHU"][ahu_name]["E_fan_h_day"][dd]


    # 合計
    for ahu_name in inputdata["AirHandlingSystem"]:

        # 空調機群（送風機）のエネルギー消費量 MWh
        resultJson["ENERGY"]["E_fan"] += np.sum(resultJson["AHU"][ahu_name]["E_fan_day"],0)

        # 空調機群（全熱交換器）のエネルギー消費量 MWh
        resultJson["ENERGY"]["E_aex"] += np.sum(resultJson["AHU"][ahu_name]["E_AHUaex_day"],0)

        # ファン発熱量計算用
        resultJson["AHU"][ahu_name]["TcAHU"] = np.sum(resultJson["AHU"][ahu_name]["TdAHUc_total"],0)
        resultJson["AHU"][ahu_name]["ThAHU"] = np.sum(resultJson["AHU"][ahu_name]["TdAHUh_total"],0)
        resultJson["AHU"][ahu_name]["MxAHUcE"] = np.sum(resultJson["AHU"][ahu_name]["E_fan_c_day"],0)
        resultJson["AHU"][ahu_name]["MxAHUhE"] = np.sum(resultJson["AHU"][ahu_name]["E_fan_h_day"],0)


    print('空調機群のエネルギー消費量計算完了')


    if DEBUG:

        for ahu_name in inputdata["AirHandlingSystem"]:

            print( f'空調機群運転時間（冷房） TcAHU {np.sum(resultJson["AHU"][ahu_name]["TcAHU"],0)}' )
            print( f'空調機群運転時間（暖房） ThAHU {np.sum(resultJson["AHU"][ahu_name]["ThAHU"],0)}' )

            print( f'空調機群エネルギー消費量（冷房） MxAHUcE {np.sum(resultJson["AHU"][ahu_name]["MxAHUcE"],0)}' )
            print( f'空調機群エネルギー消費量（暖房） MxAHUcE {np.sum(resultJson["AHU"][ahu_name]["MxAHUhE"],0)}' )

        print( f'空調機群（送風機）のエネルギー消費量: {resultJson["ENERGY"]["E_fan"]} MWh' )
        print( f'空調機群（全熱交換器）のエネルギー消費量: {resultJson["ENERGY"]["E_aex"]} MWh' )



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
                    "TempelatureDifference": 0,
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
                    "TempelatureDifference": 0,
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


    for pump_name in inputdata["PUMP"]:

        resultJson["PUMP"][pump_name] = {}
        resultJson["PUMP"][pump_name]["Qpsahu_fan"]       = np.zeros(365)   # ファン発熱量 [MJ/day]
        resultJson["PUMP"][pump_name]["Qpsahu_fan_AHU_C"] = np.zeros(365)   # ファン発熱量 [MJ/day]
        resultJson["PUMP"][pump_name]["Qpsahu_fan_AHU_H"] = np.zeros(365)   # ファン発熱量 [MJ/day]
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
            inputdata["PUMP"][pump_name]["ContolType"] = "無"
        elif "定流量制御" in inputdata["PUMP"][pump_name]["ContolType"]:
            inputdata["PUMP"][pump_name]["ContolType"] = "定流量制御"
        elif "回転数制御" in inputdata["PUMP"][pump_name]["ContolType"]:
            inputdata["PUMP"][pump_name]["ContolType"] = "回転数制御"
        else:
            raise Exception('制御方式が対応していません。')


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

            if ac_mode[dd] == "暖房":

                # 暖房期に冷房負荷の処理ができない場合
                if (resultJson["AHU"][ahu_name]["cooling"]["Qahu"][dd] > 0) and \
                    (inputdata["AirHandlingSystem"][ahu_name]["isSimultaneousSupply_heating"] == "無"):   

                    resultJson["AHU"][ahu_name]["Qahu_remainC"][dd] += abs( resultJson["AHU"][ahu_name]["cooling"]["Qahu"][dd] )
                    resultJson["AHU"][ahu_name]["cooling"]["Qahu"][dd] = 0

                if (resultJson["AHU"][ahu_name]["heating"]["Qahu"][dd] > 0) and \
                    (inputdata["AirHandlingSystem"][ahu_name]["isSimultaneousSupply_heating"] == "無"):

                    resultJson["AHU"][ahu_name]["Qahu_remainC"][dd] += abs( resultJson["AHU"][ahu_name]["heating"]["Qahu"][dd] )
                    resultJson["AHU"][ahu_name]["heating"]["Qahu"][dd] = 0

            elif (ac_mode[dd] == "冷房") or (ac_mode[dd] == "中間"):

                # 冷房期に暖房負荷の処理ができない場合
                if (resultJson["AHU"][ahu_name]["cooling"]["Qahu"][dd] < 0) and \
                    (inputdata["AirHandlingSystem"][ahu_name]["isSimultaneousSupply_cooling"] == "無"):   

                    resultJson["AHU"][ahu_name]["Qahu_remainH"][dd] += abs( resultJson["AHU"][ahu_name]["cooling"]["Qahu"][dd] )
                    resultJson["AHU"][ahu_name]["cooling"]["Qahu"][dd] = 0

                if (resultJson["AHU"][ahu_name]["heating"]["Qahu"][dd] < 0) and \
                    (inputdata["AirHandlingSystem"][ahu_name]["isSimultaneousSupply_cooling"] == "無"):

                    resultJson["AHU"][ahu_name]["Qahu_remainH"][dd] += abs( resultJson["AHU"][ahu_name]["heating"]["Qahu"][dd] )
                    resultJson["AHU"][ahu_name]["heating"]["Qahu"][dd] = 0


    # ポンプ負荷の積算
    for pump_name in inputdata["PUMP"]:

        for ahu_name in inputdata["PUMP"][pump_name]["AHU_list"]:

            for dd in range(0,365):

                if inputdata["PUMP"][pump_name]["mode"] == "cooling":  # 冷水ポンプの場合

                    # ファン発熱量 Qpsahu_fan [MJ/day] の算出（解説書 2.5.10）
                    tmpC = 0
                    tmpH = 0

                    if inputdata["AirHandlingSystem"][ahu_name]["AHU_type"] == "空調機":

                        if resultJson["AHU"][ahu_name]["cooling"]["Qahu"][dd] > 0:
                            tmpC = k_heatup * resultJson["AHU"][ahu_name]["MxAHUcE"] * \
                                resultJson["AHU"][ahu_name]["cooling"]["Tahu"][dd] / resultJson["AHU"][ahu_name]["TcAHU"] * 3600

                            resultJson["PUMP"][pump_name]["Qpsahu_fan"]  += tmpC
                            resultJson["PUMP"][pump_name]["Qpsahu_fan_AHU_C"] += tmpC

                        if resultJson["AHU"][ahu_name]["heating"]["Qahu"][dd] > 0:
                            tmpH = k_heatup * resultJson["AHU"][ahu_name]["MxAHUhE"] * \
                                resultJson["AHU"][ahu_name]["heating"]["Tahu"][dd] / resultJson["AHU"][ahu_name]["ThAHU"] * 3600

                            resultJson["PUMP"][pump_name]["Qpsahu_fan"]  += tmpC
                            resultJson["PUMP"][pump_name]["Qpsahu_fan_AHU_C"] += tmpC


                    # 日積算ポンプ負荷 Qps [MJ/day] の算出
                    if resultJson["AHU"][ahu_name]["cooling"]["Qahu"][dd] > 0:
                        if resultJson["AHU"][ahu_name]["cooling"]["Qahu_oac"][dd] > 0: # 外冷時はファン発熱量足さない ⇒ 小さな負荷が出てしまう
                            if abs(resultJson["AHU"][ahu_name]["cooling"]["Qahu"][dd] - resultJson["AHU"][ahu_name]["cooling"]["Qahu_oac"][dd]) < 1:
                                resultJson["PUMP"][pump_name]["Qps"][dd] += 0
                            else:
                                resultJson["PUMP"][pump_name]["Qps"][dd] += \
                                    resultJson["AHU"][ahu_name]["cooling"]["Qahu"][dd] - resultJson["AHU"][ahu_name]["cooling"]["Qahu_oac"][dd]
                        else:
                            resultJson["PUMP"][pump_name]["Qps"][dd] += \
                                resultJson["AHU"][ahu_name]["cooling"]["Qahu"][dd] - resultJson["AHU"][ahu_name]["cooling"]["Qahu_oac"][dd] + tmpC + tmpH

                    if resultJson["AHU"][ahu_name]["heating"]["Qahu"][dd] > 0:
                        resultJson["PUMP"][pump_name]["Qps"][dd] += \
                            resultJson["AHU"][ahu_name]["heating"]["Qahu"][dd] - resultJson["AHU"][ahu_name]["cooling"]["Qahu_oac"][dd] + tmpC + tmpH


                elif inputdata["PUMP"][pump_name]["mode"] == "heating":

                    # ファン発熱量 Qpsahu_fan [MJ/day] の算出
                    tmpC = 0
                    tmpH = 0

                    if inputdata["AirHandlingSystem"][ahu_name]["AHU_type"] == "空調機":

                        if resultJson["AHU"][ahu_name]["cooling"]["Qahu"][dd] < 0:
                            tmpC = k_heatup * resultJson["AHU"][ahu_name]["MxAHUcE"] * \
                                resultJson["AHU"][ahu_name]["cooling"]["Tahu"][dd] / resultJson["AHU"][ahu_name]["TcAHU"] * 3600

                            resultJson["PUMP"][pump_name]["Qpsahu_fan"]  += tmpC
                            resultJson["PUMP"][pump_name]["Qpsahu_fan_AHU_H"] += tmpC

                        if resultJson["AHU"][ahu_name]["heating"]["Qahu"][dd] < 0:
                            tmpH = k_heatup * resultJson["AHU"][ahu_name]["MxAHUhE"] * \
                                resultJson["AHU"][ahu_name]["heating"]["Tahu"][dd] / resultJson["AHU"][ahu_name]["ThAHU"] * 3600

                            resultJson["PUMP"][pump_name]["Qpsahu_fan"]  += tmpC
                            resultJson["PUMP"][pump_name]["Qpsahu_fan_AHU_H"] += tmpC


                    # 日積算ポンプ負荷 Qps [MJ/day] の算出<符号逆転させる>
                    if resultJson["AHU"][ahu_name]["cooling"]["Qahu"][dd] < 0:

                        resultJson["PUMP"][pump_name]["Qps"][dd] += \
                            (-1) * ( resultJson["AHU"][ahu_name]["cooling"]["Qahu"][dd] + tmpC + tmpH )

                    if resultJson["AHU"][ahu_name]["heating"]["Qahu"][dd] < 0:

                        resultJson["PUMP"][pump_name]["Qps"][dd] += \
                            (-1) * ( resultJson["AHU"][ahu_name]["heating"]["Qahu"][dd] + tmpC + tmpH )


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


    if DEBUG:

        for ahu_name in inputdata["AirHandlingSystem"]:

            print( f'--- 空調機群名 {ahu_name} ---')

            print( f'未処理負荷（冷房）: {np.sum(resultJson["AHU"][ahu_name]["Qahu_remainC"])} MJ' )
            print( f'未処理負荷（暖房）: {np.sum(resultJson["AHU"][ahu_name]["Qahu_remainH"])} MJ' )

        for pump_name in inputdata["PUMP"]:

            print( f'--- 二次ポンプ群名 {pump_name} ---')

            print( f'二次ポンプ負荷 Tps: {np.sum(resultJson["PUMP"][pump_name]["Qps"],0)}' )
            print( f'二次ポンプ運転時間 Tps: {np.sum(resultJson["PUMP"][pump_name]["Tps"],0)}' )


    ##----------------------------------------------------------------------------------
    ## 二次ポンプ群の仮想定格能力（解説書 2.6.3）
    ##----------------------------------------------------------------------------------
    for pump_name in inputdata["PUMP"]:

        for unit_id, unit_configure in enumerate(inputdata["PUMP"][pump_name]["SecondaryPump"]):

            # 二次ポンプの定格処理能力[kW] = [K] * [m3/h] * [kJ/kg・K] * [kg/m3] * [h/s]
            inputdata["PUMP"][pump_name]["SecondaryPump"][unit_id]["Qpsr"] = \
                inputdata["PUMP"][pump_name]["TempelatureDifference"]* unit_configure["RatedWaterFlowRate_total"] *4.1860*1000/3600
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
                        ix = count_Matrix(Lpump[dd],mxL)

                        Mxc[dd] = ix
                        Tdc[dd] = resultJson["PUMP"][pump_name]["Tps"][dd]

        resultJson["PUMP"][pump_name]["LdPUMP"] = Mxc
        resultJson["PUMP"][pump_name]["TdPUMP"] = Tdc
        

    ##----------------------------------------------------------------------------------
    ## 流量制御方式によって定まる係数（解説書 2.6.7）
    ##----------------------------------------------------------------------------------

    for pump_name in inputdata["PUMP"]:

        for unit_id, unit_configure in enumerate(inputdata["PUMP"][pump_name]["SecondaryPump"]):

            if unit_configure["ContolType"] in FLOWCONTROL.keys():

                inputdata["PUMP"][pump_name]["SecondaryPump"][unit_id]["a4"] = FLOWCONTROL[ unit_configure["ContolType"] ]["a4"]
                inputdata["PUMP"][pump_name]["SecondaryPump"][unit_id]["a3"] = FLOWCONTROL[ unit_configure["ContolType"] ]["a3"]
                inputdata["PUMP"][pump_name]["SecondaryPump"][unit_id]["a2"] = FLOWCONTROL[ unit_configure["ContolType"] ]["a2"]
                inputdata["PUMP"][pump_name]["SecondaryPump"][unit_id]["a1"] = FLOWCONTROL[ unit_configure["ContolType"] ]["a1"]
                inputdata["PUMP"][pump_name]["SecondaryPump"][unit_id]["a0"] = FLOWCONTROL[ unit_configure["ContolType"] ]["a0"]

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

        MxPUMPNum = np.zeros(len(mxL))
        MxPUMPPower = np.zeros(len(mxL))
        PUMPvwvfac = np.zeros(len(mxL))

        if inputdata["PUMP"][pump_name]["Qpsr"] != 0:   # 仮想ポンプ（二次ポンプがないシステム用の仮想ポンプ）は除く

            if inputdata["PUMP"][pump_name]["isStagingControl"] == "無":    # 台数制御なし
            
                # 運転台数
                MxPUMPNum = np.ones(len(mxL)) * inputdata["PUMP"][pump_name]["number_of_pumps"]

                # 流量制御方式
                if inputdata["PUMP"][pump_name]["ContolType"] == "回転数制御":  # 全台VWVであれば

                    for iL in range(0,len(mxL)):

                        # 最小負荷率による下限を設ける。
                        if aveL[iL] < (inputdata["PUMP"][pump_name]["MinOpeningRate"] /100):
                            tmpL = inputdata["PUMP"][pump_name]["MinOpeningRate"] / 100
                        else:
                            tmpL = aveL[iL]

                        # VWVの効果率曲線(1番目の特性を代表して使う)
                        
                        if iL == len(mxL):
                            PUMPvwvfac[iL] = 1.2
                        else:
                            PUMPvwvfac[iL] = \
                                inputdata["PUMP"][pump_name]["SecondaryPump"][0]["a4"] * tmpL ** 4 + \
                                inputdata["PUMP"][pump_name]["SecondaryPump"][0]["a3"] * tmpL ** 3 + \
                                inputdata["PUMP"][pump_name]["SecondaryPump"][0]["a2"] * tmpL ** 2 + \
                                inputdata["PUMP"][pump_name]["SecondaryPump"][0]["a1"] * tmpL + \
                                inputdata["PUMP"][pump_name]["SecondaryPump"][0]["a0"]

                else: # 全台VWVであれば、定流量とみなす。
                    PUMPvwvfac = np.ones(len(mxL))
                    PUMPvwvfac[len(mxL)] = 1.2


                # 消費電力（部分負荷特性×定格消費電力）[kW]
                MxPUMPPower = PUMPvwvfac * inputdata["PUMP"][pump_name]["RatedPowerConsumption_total"]


            elif inputdata["PUMP"][pump_name]["isStagingControl"] == "有":   # 台数制御あり

                for iL in range(0,len(mxL)):

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
                    numVWV = MxPUMPNum[iL]  # MxPUMPNum[iL]は、変流量時の最大運転台数

                    for rr in range(0, int(MxPUMPNum[iL])):
                        
                        if (inputdata["PUMP"][pump_name]["SecondaryPump"][rr]["ContolType"] == "無") or \
                            (inputdata["PUMP"][pump_name]["SecondaryPump"][rr]["ContolType"] == "定流量制御"):

                            Qtmp_CWV += inputdata["PUMP"][pump_name]["SecondaryPump"][rr]["Qpsr"]
                            numVWV = numVWV -1


                    # 制御を加味した消費エネルギー MxPUMPPower [kW]
                    for rr in range(0, int(MxPUMPNum[iL])):

                        if (inputdata["PUMP"][pump_name]["SecondaryPump"][rr]["ContolType"] == "無") or \
                            (inputdata["PUMP"][pump_name]["SecondaryPump"][rr]["ContolType"] == "定流量制御"):

                            if aveL[iL] > 1.0:
                                MxPUMPPower[iL] += inputdata["PUMP"][pump_name]["SecondaryPump"][rr]["RatedPowerConsumption_total"] * 1.2
                            else:
                                MxPUMPPower[iL] += inputdata["PUMP"][pump_name]["SecondaryPump"][rr]["RatedPowerConsumption_total"]


                        elif inputdata["PUMP"][pump_name]["SecondaryPump"][rr]["ContolType"] == "回転数制御":

                            # 変流量ポンプjの負荷率 [-]
                            tmpL = ( (Qpsr_iL - Qtmp_CWV)/numVWV ) / inputdata["PUMP"][pump_name]["SecondaryPump"][rr]["Qpsr"]

                            # 最小流量の制限
                            if tmpL < inputdata["PUMP"][pump_name]["SecondaryPump"][rr]["MinOpeningRate"]/100:
                                tmpL = inputdata["PUMP"][pump_name]["SecondaryPump"][rr]["MinOpeningRate"]/100
                            
                            # 変流量制御による省エネ効果
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
        resultJson["PUMP"][pump_name]["PUMPvwvfac"]  = PUMPvwvfac


    ##----------------------------------------------------------------------------------
    ## 二次ポンプ群の消費電力（解説書 2.6.8）
    ##----------------------------------------------------------------------------------

    for pump_name in inputdata["PUMP"]:

        for dd in range(0,365):

            if resultJson["PUMP"][pump_name]["TdPUMP"][dd] > 0:

                resultJson["PUMP"][pump_name]["E_pump_day"][dd] = \
                    resultJson["PUMP"][pump_name]["MxPUMPPower"][ int(resultJson["PUMP"][pump_name]["LdPUMP"][dd])-1 ] / 1000 * \
                    resultJson["PUMP"][pump_name]["TdPUMP"][dd]


    ##----------------------------------------------------------------------------------
    ## 二次ポンプ群の年間一次エネルギー消費量（解説書 2.6.10）
    ##----------------------------------------------------------------------------------

    resultJson["ENERGY"]["E_pump"] = 0

    for pump_name in inputdata["PUMP"]:

        resultJson["ENERGY"]["E_pump"] += np.sum(resultJson["PUMP"][pump_name]["E_pump_day"], 0)
        resultJson["PUMP"][pump_name]["TcPUMP"]  = np.sum(resultJson["PUMP"][pump_name]["TdPUMP"], 0)
        resultJson["PUMP"][pump_name]["MxPUMPE"]  = np.sum(resultJson["PUMP"][pump_name]["E_pump_day"], 0)


    print('二次ポンプ群のエネルギー消費量計算完了')


    if DEBUG:

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
        
        print( f'二次ポンプ群の年間一次エネルギー消費量 E_pump: {resultJson["ENERGY"]["E_pump"]}' )



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

        if DEBUG:
            print( f'--- 二次ポンプ群名 {pump_name} ---')
            print( f'二次ポンプ群のポンプ発熱量 Qpsahu_fan: {np.sum(resultJson["PUMP"][pump_name]["Qpsahu_pump"],0)}' )



    ##----------------------------------------------------------------------------------
    ## 熱源群の一次エネルギー消費量（解説書 2.7）
    ##----------------------------------------------------------------------------------

    # モデル格納用変数

    # 冷房と暖房の熱源群に分ける。
    for ref_original_name in inputdata["HeatsourceSystem"]:

        if "冷房" in inputdata["HeatsourceSystem"][ref_original_name]:
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
    ## 熱源群全体のスペックを整理する。
    ##----------------------------------------------------------------------------------

    for ref_name in inputdata["REF"]:

        inputdata["REF"][ref_name]["pump_list"] = set()
        inputdata["REF"][ref_name]["refsetRnum"] = 0
        

        # 熱源群全体の性能
        inputdata["REF"][ref_name]["QrefrMax"] = 0
        for unit_id, unit_configure in enumerate(inputdata["REF"][ref_name]["Heatsource"]):

            # 定格能力（台数×能力）
            inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedCapacity_total"] = \
                unit_configure["HeatsourceRatedCapacity"] * unit_configure["Number"]

            # 定格消費電力（台数×消費電力）
            inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedPowerConsumption_total"] = \
                unit_configure["HeatsourceRatedPowerConsumption"] * unit_configure["Number"]

            # 定格燃料消費量（台数×燃料消費量）
            inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedFuelConsumption_total"] = \
                unit_configure["HeatsourceRatedFuelConsumption"] * unit_configure["Number"]

            # 熱源機器の台数
            inputdata["REF"][ref_name]["refsetRnum"] += 1

            # 一次ポンプの消費電力の合計
            inputdata["REF"][ref_name]["Heatsource"][unit_id]["PrimaryPumpPowerConsumption_total"] = \
                unit_configure["PrimaryPumpPowerConsumption"] * unit_configure["Number"]

            # 冷却塔ファンの消費電力の合計
            inputdata["REF"][ref_name]["Heatsource"][unit_id]["CoolingTowerFanPowerConsumption_total"] = \
                unit_configure["CoolingTowerFanPowerConsumption"] * unit_configure["Number"]
            
            # 冷却塔ポンプの消費電力の合計
            inputdata["REF"][ref_name]["Heatsource"][unit_id]["CoolingTowerPumpPowerConsumption_total"] = \
                unit_configure["CoolingTowerPumpPowerConsumption"] * unit_configure["Number"]


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
        
        # 放熱器の制約
        if inputdata["REF"][ref_name]["isStorage"] == "追掛":

            tmpCapacity = inputdata["REF"][ref_name]["storageEffratio"] * inputdata["REF"][ref_name]["StorageSize"]/8*(1000/3600)

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
        resultJson["REF"][ref_name]["Qref"]          = np.zeros(365)      # 日積算熱源負荷 [MJ/Day]
        resultJson["REF"][ref_name]["Lref"]          = np.zeros(365)      # 日積算熱源負荷 [MJ/Day]
        resultJson["REF"][ref_name]["schedule"]      = np.zeros((365,24)) # 運転スケジュール
        resultJson["REF"][ref_name]["Tref"]          = np.zeros(365)      # 日積算運転時間
        resultJson["REF"][ref_name]["Qref_kW"]       = np.zeros(365)      # 熱源平均負荷 kW
        resultJson["REF"][ref_name]["Qref_OVER"]     = np.zeros(365)      # 過負荷分
        resultJson["REF"][ref_name]["ghsp_Rq"]       = 0                  # 冷房負荷と暖房負荷の比率（地中熱ヒートポンプ用）← 冷房用と暖房用熱源は順に並んでいる
        resultJson["REF"][ref_name]["LdREF"]         = np.zeros(365)      # 熱源の負荷率区分
        resultJson["REF"][ref_name]["TdREF"]         = np.zeros(365)      # 熱源の温度区分
        resultJson["REF"][ref_name]["E_ref_day"]     =  np.zeros(365)     # 熱源群エネルギー消費量 [MJ]
        resultJson["REF"][ref_name]["E_ref_ACc_day"] =  np.zeros(365)     # 補機電力 [MWh]
        resultJson["REF"][ref_name]["E_PPc_day"]     =  np.zeros(365)     # 一次ポンプ電力 [MWh]
        resultJson["REF"][ref_name]["E_CTfan_day"]   =  np.zeros(365)     # 冷却塔ファン電力 [MWh]
        resultJson["REF"][ref_name]["E_CTpump_day"]  =  np.zeros(365)     # 冷却水ポンプ電力 [MWh]
        resultJson["REF"][ref_name]["MxREFperE"]     = np.zeros( [divT, divL+1] )   # 熱源群全体で集計した値
        
        resultJson["REF"][ref_name]["Heatsource"]    = {}
        for unit_id, unit_configure in enumerate(inputdata["REF"][ref_name]["Heatsource"]):

            # 熱源群に属する各熱源機器の値
            resultJson["REF"][ref_name]["Heatsource"][unit_id] = {}
            resultJson["REF"][ref_name]["Heatsource"][unit_id]["MxREFSUBperE"]  = np.zeros( [divT, divL+1] ) 


    ##----------------------------------------------------------------------------------
    ## 熱源群の定格能力 （解説書 2.7.5）
    ##----------------------------------------------------------------------------------
    # 熱源群の合計定格能力
    for ref_name in inputdata["REF"]:
        inputdata["REF"][ref_name]["QrefrMax"] = 0
        for unit_id, unit_configure in enumerate(inputdata["REF"][ref_name]["Heatsource"]):    
            inputdata["REF"][ref_name]["QrefrMax"] += inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedCapacity_total"]


    ##----------------------------------------------------------------------------------
    ## 蓄熱総の熱損失 （解説書 2.7.1）
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
            if resultJson["REF"][ref_name]["Qref_kW"][dd] > inputdata["REF"][ref_name]["QrefrMax"]:

                resultJson["REF"][ref_name]["Qref_OVER"][dd] = \
                    (resultJson["REF"][ref_name]["Qref_kW"][dd] -inputdata["REF"][ref_name]["QrefrMax"] ) * \
                    resultJson["REF"][ref_name]["Tref"][dd]*3600/1000


    print('熱源負荷計算完了')


    if DEBUG:

        for ref_name in inputdata["REF"]:

            print( f'--- 熱源群名 {ref_name} ---')

            print( f'熱源群の熱源負荷 Qref: {np.sum(resultJson["REF"][ref_name]["Qref"],0)}' )
            print( f'熱源群の平均負荷 Qref_kW: {np.sum(resultJson["REF"][ref_name]["Qref_kW"],0)}' )
            print( f'熱源群の過負荷 Qref_OVER: {np.sum(resultJson["REF"][ref_name]["Qref_OVER"],0)}' )
            print( f'熱源群の運転時間 Tref: {np.sum(resultJson["REF"][ref_name]["Tref"],0)}' )


    ##----------------------------------------------------------------------------------
    ## 熱源機器の特性の読み込み（解説書 附属書A.4）
    ##----------------------------------------------------------------------------------

    ## 熱源機器特性
    with open(database_directory + "HeatSourcePerformance.json", 'r') as f:
        HeatSourcePerformance = json.load(f)

    for ref_name in inputdata["REF"]:

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
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["refset_MainPowerELE"] = (9760/3600) * inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedPowerConsumption_total"] 
            elif fuel_type == "ガス":
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["refInputType"] = 2
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["refset_MainPowerELE"] = inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedFuelConsumption_total"] 
            elif fuel_type == "重油":
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["refInputType"] = 3
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["refset_MainPowerELE"] = inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedFuelConsumption_total"] 
            elif fuel_type == "灯油":
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["refInputType"] = 4
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["refset_MainPowerELE"] = inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedFuelConsumption_total"]        
            elif fuel_type == "液化石油ガス":
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["refInputType"] = 5
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["refset_MainPowerELE"] = inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedFuelConsumption_total"]     
            elif fuel_type == "蒸気":
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["refInputType"] = 6
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedFuelConsumption_total"] = inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedCapacity_total"]  
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["refset_MainPowerELE"] = \
                    (inputdata["Building"]["Coefficient_DHC"]["Heating"]) * inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedCapacity_total"]  
            elif fuel_type == "温水":
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["refInputType"] = 7
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedFuelConsumption_total"] = inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedCapacity_total"]  
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["refset_MainPowerELE"] = \
                    (inputdata["Building"]["Coefficient_DHC"]["Heating"])*inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedCapacity_total"]  
            elif fuel_type == "冷水":
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["refInputType"] = 8
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedFuelConsumption_total"] = inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedCapacity_total"]  
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["refset_MainPowerELE"] = \
                    (inputdata["Building"]["Coefficient_DHC"]["Cooling"])*inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedCapacity_total"]  


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


    ##----------------------------------------------------------------------------------
    ## 湿球温度 （解説書 2.7.4.2）
    ##----------------------------------------------------------------------------------

    ToawbC = Area[inputdata["Building"]["Region"]+"地域"]["湿球温度係数_冷房a1"] * ToadbC + Area[inputdata["Building"]["Region"]+"地域"]["湿球温度係数_冷房a0"]
    ToawbH = Area[inputdata["Building"]["Region"]+"地域"]["湿球温度係数_暖房a1"] * ToadbH + Area[inputdata["Building"]["Region"]+"地域"]["湿球温度係数_暖房a0"]


    ##----------------------------------------------------------------------------------
    ## 冷却水温度 （解説書 2.7.4.3）
    ##----------------------------------------------------------------------------------
    
    TctwC  = ToawbC + 3  # 冷却水温度 [℃]
    TctwH  = 15.5 * np.ones(6)  #  水冷式の暖房時熱源水温度（暫定） [℃]


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
            Qcmax = abs( np.max( resultJson["REF"][ref_original_name + "_冷房"]["Qref"] , 0) )

        Qhmax = 0
        if "暖房" in inputdata["HeatsourceSystem"][ref_original_name]:
            Qhmax = abs( np.max( resultJson["REF"][ref_original_name + "_暖房"]["Qref"] , 0) )

        if Qcmax != 0 and Qhmax != 0:

            resultJson["REF"][ref_original_name + "_冷房"]["ghsp_Rq"] = (Qcmax-Qhmax)/(Qcmax+Qhmax)
            resultJson["REF"][ref_original_name + "_暖房"]["ghsp_Rq"] = (Qcmax-Qhmax)/(Qcmax+Qhmax)

        elif Qcmax == 0 and Qhmax != 0:
            Qcmax = Qhmax
            resultJson["REF"][ref_original_name + "_暖房"]["ghsp_Rq"] = (Qcmax-Qhmax)/(Qcmax+Qhmax)

        elif Qcmax != 0 and Qhmax == 0:
            Qhmax = Qcmax
            resultJson["REF"][ref_original_name + "_冷房"]["ghsp_Rq"] = (Qcmax-Qhmax)/(Qcmax+Qhmax)


    ##----------------------------------------------------------------------------------
    ## 熱源水等の温度 xTALL （解説書 2.7.4）
    ##----------------------------------------------------------------------------------
    # 外気温度の軸（マトリックスの縦軸）

    for ref_name in inputdata["REF"]:

        for unit_id, unit_configure in enumerate(inputdata["REF"][ref_name]["Heatsource"]):

            if unit_configure["parameter"]["熱源種類"] == "水" and inputdata["REF"][ref_name]["mode"] == "cooling":
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["xTALL"] = TctwC   # 冷却水温度
            elif unit_configure["parameter"]["熱源種類"] == "水" and inputdata["REF"][ref_name]["mode"] == "heating":
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["xTALL"] = TctwH   # 冷却水温度
            elif unit_configure["parameter"]["熱源種類"] == "空気" and inputdata["REF"][ref_name]["mode"] == "cooling":
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["xTALL"] = ToadbC  # 乾球温度
            elif unit_configure["parameter"]["熱源種類"] == "空気" and inputdata["REF"][ref_name]["mode"] == "heating":
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["xTALL"] = ToawbH  # 湿球温度
            elif unit_configure["parameter"]["熱源種類"] == "不要" and inputdata["REF"][ref_name]["mode"] == "cooling":
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["xTALL"] = ToadbC  # 乾球温度
            elif unit_configure["parameter"]["熱源種類"] == "不要" and inputdata["REF"][ref_name]["mode"] == "heating":
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["xTALL"] = ToadbH  # 乾球温度

            for gound_type in range(1,6):

                if unit_configure["parameter"]["熱源種類"] == "地盤"+str(int(gound_type)) and inputdata["REF"][ref_name]["mode"] == "cooling":
                    igsType = int(gound_type)-1
                    iAREA = int(inputdata["Building"]["Region"])-1
                    # 地盤からの還り温度（冷房）
                    inputdata["REF"][ref_name]["Heatsource"][unit_id]["xTALL"] = \
                        ( gshp_cc[igsType] * resultJson["REF"][ref_name]["ghsp_Rq"] + gshp_dc[igsType] ) * ( ToadbC - gshpToa_c[iAREA] ) + \
                        (ghspToa_ave[iAREA] + gshp_ac[igsType] * resultJson["REF"][ref_name]["ghsp_Rq"] + gshp_bc[igsType])
                
                elif unit_configure["parameter"]["熱源種類"] == "地盤"+str(int(gound_type)) and inputdata["REF"][ref_name]["mode"] == "heating":
                    igsType = int(gound_type)-1
                    iAREA = int(inputdata["Building"]["Region"])-1
                    # 地盤からの還り温度（暖房）
                    inputdata["REF"][ref_name]["Heatsource"][unit_id]["xTALL"] = \
                        ( gshp_ch[igsType] * resultJson["REF"][ref_name]["ghsp_Rq"] + gshp_dh[igsType] ) * ( ToadbH - gshpToa_h[iAREA] ) + \
                        (ghspToa_ave[iAREA] + gshp_ah[igsType] * resultJson["REF"][ref_name]["ghsp_Rq"] + gshp_bh[igsType])


    ##----------------------------------------------------------------------------------
    ## 蓄熱槽からの放熱を加味した補正定格能力 （解説書 2.7.6）
    ##----------------------------------------------------------------------------------

    # 蓄熱槽がある場合の放熱用熱交換器の容量の補正
    for ref_name in inputdata["REF"]:

        tmpCapacityHEX = 0

        if inputdata["REF"][ref_name]["isStorage"] == "追掛":
            if inputdata["REF"][ref_name]["Heatsource"][0]["HeatsourceType"] == "熱交換器":

                # 熱源運転時間の最大値で補正した容量
                tmpCapacityHEX = inputdata["REF"][ref_name]["Heatsource"][0]["HeatsourceRatedCapacity_total"] * (8 / np.max(resultJson["REF"][ref_name]["Tref"]))

                # 定格容量の合計値を更新
                inputdata["REF"][ref_name]["QrefrMax"] = inputdata["REF"][ref_name]["QrefrMax"] +  tmpCapacityHEX - inputdata["REF"][ref_name]["Heatsource"][0]["HeatsourceRatedCapacity_total"]

                # 熱交換器の容量を修正
                inputdata["REF"][ref_name]["Heatsource"][0]["HeatsourceRatedCapacity_total"] = tmpCapacityHEX

            else:
                raise Exception('熱交換機が設定されていません')

        if DEBUG:
                
            print( f'--- 熱源群名 {ref_name} ---')
            print( f'熱交換器の容量: {inputdata["REF"][ref_name]["Heatsource"][0]["HeatsourceRatedCapacity_total"]}')
            print( f'熱源群の定格能力の合計 QrefrMax: {inputdata["REF"][ref_name]["QrefrMax"]}' )


    ##----------------------------------------------------------------------------------
    ## 熱源群の負荷率（解説書 2.7.7）
    ##----------------------------------------------------------------------------------

    for ref_name in inputdata["REF"]:

        mxT = []
        if inputdata["REF"][ref_name]["mode"] == "cooling":
            mxT = mxTC
        elif inputdata["REF"][ref_name]["mode"] == "heating":
            mxT = mxTH
        else:
            raise Exception('運転モードが不正です')


        for dd in range(0,365):
            
            # 負荷率算出 [-]
            if resultJson["REF"][ref_name]["Tref"][dd] > 0:
                resultJson["REF"][ref_name]["Lref"][dd] = \
                    (resultJson["REF"][ref_name]["Qref"][dd] / resultJson["REF"][ref_name]["Tref"][dd] *1000/3600) / \
                    inputdata["REF"][ref_name]["QrefrMax"]
        
            if np.isnan(resultJson["REF"][ref_name]["Lref"][dd]) == True:
                resultJson["REF"][ref_name]["Lref"][dd] = 0

            if resultJson["REF"][ref_name]["Lref"][dd] > 0:
                
                # 負荷率帯マトリックス
                resultJson["REF"][ref_name]["LdREF"][dd] = count_Matrix(resultJson["REF"][ref_name]["Lref"][dd], mxL)
                # 外気温帯マトリックス
                resultJson["REF"][ref_name]["TdREF"][dd] = count_Matrix(Toa_ave[dd], mxT) 


    ##----------------------------------------------------------------------------------
    ## 最大能力比 xQratio （解説書 2.7.8）
    ##----------------------------------------------------------------------------------

    for ref_name in inputdata["REF"]:

        for unit_id, unit_configure in enumerate(inputdata["REF"][ref_name]["Heatsource"]):

            ## 能力比（各外気温帯における最大能力）
            inputdata["REF"][ref_name]["Heatsource"][unit_id]["xQratio"] = np.zeros(len(inputdata["REF"][ref_name]["Heatsource"][unit_id]["xTALL"]))

            for i in range(0,len(ToadbC)):

                x = inputdata["REF"][ref_name]["Heatsource"][unit_id]["xTALL"][i]

                # 特性式の数
                curveNum = len(unit_configure["parameter"]["能力比"])

                # 下限値
                minX = []
                for j in range(0,curveNum):
                    minX.append(unit_configure["parameter"]["能力比"][j]["下限"])
                # 上限値
                maxX = []
                for j in range(0,curveNum):
                    maxX.append(unit_configure["parameter"]["能力比"][j]["上限"])

                # 上限と下限を定める
                if x < minX[0]:
                    x = minX[0]
                elif x > maxX[-1]:
                    x = maxX[-1]

                for j in reversed(range(0,curveNum)):
                    if x <= maxX[j]:

                        inputdata["REF"][ref_name]["Heatsource"][unit_id]["xQratio"][i] =  \
                            unit_configure["parameter"]["能力比"][j]["基整促係数"] * ( \
                            unit_configure["parameter"]["能力比"][j]["係数"]["a4"] * x ** 4 + \
                            unit_configure["parameter"]["能力比"][j]["係数"]["a3"] * x ** 3 + \
                            unit_configure["parameter"]["能力比"][j]["係数"]["a2"] * x ** 2 + \
                            unit_configure["parameter"]["能力比"][j]["係数"]["a1"] * x  + \
                            unit_configure["parameter"]["能力比"][j]["係数"]["a0"] )


        for unit_id, unit_configure in enumerate(inputdata["REF"][ref_name]["Heatsource"]):

            inputdata["REF"][ref_name]["Heatsource"][unit_id]["Qrefr_mod"] = np.zeros(len(ToadbC))
            
            for iX in range(0,len(ToadbC)):
                
                # 各外気温区分における最大能力 [kW]
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["Qrefr_mod"][iX] = \
                    inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedCapacity_total"] * \
                    inputdata["REF"][ref_name]["Heatsource"][unit_id]["xQratio"][iX]
            
            if DEBUG:
                print( f'--- 熱源群名 {ref_name} の {unit_id+1} 台目---')
                print( f'各外気温区分における最大能力 Qrefr_mod: \n {inputdata["REF"][ref_name]["Heatsource"][unit_id]["Qrefr_mod"]}' )

    
    ##----------------------------------------------------------------------------------
    ## 最大入力比 xPratio （解説書 2.7.11）
    ##----------------------------------------------------------------------------------

    for ref_name in inputdata["REF"]:

        for unit_id, unit_configure in enumerate(inputdata["REF"][ref_name]["Heatsource"]):

            ## 入力比（各外気温帯における最大入力）
            inputdata["REF"][ref_name]["Heatsource"][unit_id]["xPratio"] = np.zeros(len(inputdata["REF"][ref_name]["Heatsource"][unit_id]["xTALL"]))

            for i in range(0,len(ToadbC)):

                x = inputdata["REF"][ref_name]["Heatsource"][unit_id]["xTALL"][i]

                # 特性式の数
                curveNum = len(unit_configure["parameter"]["入力比"])

                # 下限値
                minX = []
                for j in range(0,curveNum):
                    minX.append(unit_configure["parameter"]["入力比"][j]["下限"])
                # 上限値
                maxX = []
                for j in range(0,curveNum):
                    maxX.append(unit_configure["parameter"]["入力比"][j]["上限"])

                # 上限と下限を定める
                if x < minX[0]:
                    x = minX[0]
                elif x > maxX[-1]:
                    x = maxX[-1]

                for j in reversed(range(0,curveNum)):
                    if x <= maxX[j]:

                        inputdata["REF"][ref_name]["Heatsource"][unit_id]["xPratio"][i] =  \
                            unit_configure["parameter"]["入力比"][j]["基整促係数"] * ( \
                            unit_configure["parameter"]["入力比"][j]["係数"]["a4"] * x ** 4 + \
                            unit_configure["parameter"]["入力比"][j]["係数"]["a3"] * x ** 3 + \
                            unit_configure["parameter"]["入力比"][j]["係数"]["a2"] * x ** 2 + \
                            unit_configure["parameter"]["入力比"][j]["係数"]["a1"] * x  + \
                            unit_configure["parameter"]["入力比"][j]["係数"]["a0"] )


        for unit_id, unit_configure in enumerate(inputdata["REF"][ref_name]["Heatsource"]):

            inputdata["REF"][ref_name]["Heatsource"][unit_id]["Erefr_mod"] = np.zeros(len(ToadbC))

            for iX in range(0,len(ToadbC)):

                # 各外気温区分における最大入力 [kW]  (1次エネルギー換算値であることに注意）
                inputdata["REF"][ref_name]["Heatsource"][unit_id]["Erefr_mod"][iX] = \
                    inputdata["REF"][ref_name]["Heatsource"][unit_id]["refset_MainPowerELE"] * \
                    inputdata["REF"][ref_name]["Heatsource"][unit_id]["xPratio"][iX]

            if DEBUG:
                print( f'--- 熱源群名 {ref_name} の {unit_id+1} 台目---')
                print( f'各外気温区分における最大入力 Erefr_mod: \n {inputdata["REF"][ref_name]["Heatsource"][unit_id]["Erefr_mod"]}' )


    ##----------------------------------------------------------------------------------
    ## 熱源機器の運転台数（解説書 2.7.9）
    ##----------------------------------------------------------------------------------

    # 運転台数マトリックス
    for ref_name in inputdata["REF"]:

        resultJson["REF"][ref_name]["MxREFnum"] = np.ones( [len(mxT), len(mxL)] ) 

        if inputdata["REF"][ref_name]["isStagingControl"] == "無":   # 運転台数制御が「無」の場合

            resultJson["REF"][ref_name]["MxREFnum"] = np.ones( [len(mxT), len(mxL)] ) * inputdata["REF"][ref_name]["refsetRnum"]
        
        elif inputdata["REF"][ref_name]["isStagingControl"] == "有":  # 運転台数制御が「有」の場合

            for ioa in range(0, len(mxT)):
                for iL in range(0, len(mxL)):

                    # 処理熱量 [kW]
                    tmpQ  = inputdata["REF"][ref_name]["QrefrMax"] * aveL[iL]
        
                    # 運転台数 MxREFnum
                    tmpQmax = 0
                    for rr in range(0, inputdata["REF"][ref_name]["refsetRnum"]):
                        tmpQmax += inputdata["REF"][ref_name]["Heatsource"][rr]["Qrefr_mod"][ioa]

                        if tmpQ < tmpQmax:
                            break
                    
                    resultJson["REF"][ref_name]["MxREFnum"][ioa][iL] = rr+1


        if DEBUG:

            print( f'--- 熱源群名 {ref_name} ---')
            print( f'各外気温区分における運転台数 MxREFnum: {resultJson["REF"][ref_name]["MxREFnum"]}' )
        

    ##----------------------------------------------------------------------------------
    ## 熱源群の運転負荷率（解説書 2.7.12）
    ##----------------------------------------------------------------------------------

    for ref_name in inputdata["REF"]:

        resultJson["REF"][ref_name]["MxREFxL"] = np.zeros( [len(mxT), len(mxL)] ) 
        resultJson["REF"][ref_name]["MxREFxL_real"] = np.zeros( [len(mxT), len(mxL)] ) 

        for ioa in range(0, len(mxT)):
            for iL in range(0, len(mxL)):

                # 処理熱量 [kW]
                tmpQ  = inputdata["REF"][ref_name]["QrefrMax"] * aveL[iL]
                
                Qrefr_mod_max = 0
                for unit_id in range(0, int(resultJson["REF"][ref_name]["MxREFnum"][ioa][iL])):
                    Qrefr_mod_max += inputdata["REF"][ref_name]["Heatsource"][unit_id]["Qrefr_mod"][ioa]

                # [ioa,iL]における負荷率
                resultJson["REF"][ref_name]["MxREFxL"][ioa][iL] = tmpQ / Qrefr_mod_max

                if inputdata["REF"][ref_name]["isStorage"] == "蓄熱":
                    resultJson["REF"][ref_name]["MxREFxL"][ioa][iL] = 1.0


    ##----------------------------------------------------------------------------------
    ## 部分負荷特性 （解説書 2.7.13）
    ##----------------------------------------------------------------------------------

    for ref_name in inputdata["REF"]:

        for unit_id, unit_configure in enumerate(inputdata["REF"][ref_name]["Heatsource"]):
            inputdata["REF"][ref_name]["Heatsource"][unit_id]["coeff_x"] = np.zeros( [len(mxT), len(mxL)] ) 

        for ioa in range(0, len(mxT)):
            for iL in range(0, len(mxL)):

                # 部分負荷特性（各負荷率・各温度帯について）
                for unit_id in range(0, int(resultJson["REF"][ref_name]["MxREFnum"][ioa][iL])):

                    # どの部分負荷特性を使うか（インバータターボなど、冷却水温度によって特性が異なる場合がある）
                    xCurveNum = 0
                    if len(inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["部分負荷特性"]) > 1:   # 部分負荷特性が2以上設定されている場合

                        for para_id in range(0, len(inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["部分負荷特性"])):

                            if inputdata["REF"][ref_name]["Heatsource"][unit_id]["xTALL"][i] > inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["部分負荷特性"][para_id]["冷却水温度下限"] and \
                                inputdata["REF"][ref_name]["Heatsource"][unit_id]["xTALL"][i] >= inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["部分負荷特性"][para_id]["冷却水温度上限"]:
                                xCurveNum = para_id
                
                    # 部分負荷特性の上下限
                    resultJson["REF"][ref_name]["MxREFxL_real"][ioa][iL] = resultJson["REF"][ref_name]["MxREFxL"][ioa][iL] 

                    if resultJson["REF"][ref_name]["MxREFxL"][ioa][iL] < inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["部分負荷特性"][xCurveNum]["下限"]:
                        resultJson["REF"][ref_name]["MxREFxL"][ioa][iL] = inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["部分負荷特性"][xCurveNum]["下限"]
                    elif resultJson["REF"][ref_name]["MxREFxL"][ioa][iL] > inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["部分負荷特性"][xCurveNum]["上限"] or iL == len(mxL):
                        resultJson["REF"][ref_name]["MxREFxL"][ioa][iL] = inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["部分負荷特性"][xCurveNum]["上限"]
                    tmpL = resultJson["REF"][ref_name]["MxREFxL"][ioa][iL]


                    # 部分負荷特性
                    inputdata["REF"][ref_name]["Heatsource"][unit_id]["coeff_x"][ioa][iL] = \
                        inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["部分負荷特性"][xCurveNum]["係数"]["a4"] * tmpL ** 4 +  \
                        inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["部分負荷特性"][xCurveNum]["係数"]["a3"] * tmpL ** 3 +  \
                        inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["部分負荷特性"][xCurveNum]["係数"]["a2"] * tmpL ** 2 +  \
                        inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["部分負荷特性"][xCurveNum]["係数"]["a1"] * tmpL + \
                        inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["部分負荷特性"][xCurveNum]["係数"]["a0"]

                    # 過負荷時のペナルティ（要検討）
                    if iL == len(mxL)-1:
                        inputdata["REF"][ref_name]["Heatsource"][unit_id]["coeff_x"][ioa][iL] = inputdata["REF"][ref_name]["Heatsource"][unit_id]["coeff_x"][ioa][iL] * 1.2


        if DEBUG:
            print( f'--- 熱源群名 {ref_name} ---')
            print( f'熱源群の運転負荷率 MxREFxL: \n {resultJson["REF"][ref_name]["MxREFxL"]}' )
            print( f'熱源群の運転負荷率 MxREFxL_real: \n {resultJson["REF"][ref_name]["MxREFxL_real"]}' )


    ##----------------------------------------------------------------------------------
    ## 熱源群の運転負荷率 （解説書 2.7.14）
    ##----------------------------------------------------------------------------------

    for ref_name in inputdata["REF"]:

        # 送水温度特性（各負荷率・各温度帯について）
        for unit_id in range(0, int(resultJson["REF"][ref_name]["MxREFnum"][ioa][iL])):
            inputdata["REF"][ref_name]["Heatsource"][unit_id]["coeff_tw"] = np.ones( [len(mxT), len(mxL)] ) 

        for ioa in range(0, len(mxT)):
            for iL in range(0, len(mxL)):

                # 送水温度特性（各負荷率・各温度帯について）
                for unit_id in range(0, int(resultJson["REF"][ref_name]["MxREFnum"][ioa][iL])):

                    # 送水温度 TCtmp
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

                    if inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["送水温度特性"] != []:

                        # 送水温度特性の上下限
                        if TCtmp < inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["送水温度特性"][0]["下限"]:
                            TCtmp = inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["送水温度特性"][0]["下限"]
                        elif TCtmp > inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["送水温度特性"][0]["上限"]:
                            TCtmp = inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["送水温度特性"][0]["上限"]

                        # 送水温度特性
                        inputdata["REF"][ref_name]["Heatsource"][unit_id]["coeff_tw"][ioa][iL] = \
                            inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["送水温度特性"][0]["係数"]["a4"] * TCtmp ** 4 +  \
                            inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["送水温度特性"][0]["係数"]["a3"] * TCtmp ** 3 +  \
                            inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["送水温度特性"][0]["係数"]["a2"] * TCtmp ** 2 +  \
                            inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["送水温度特性"][0]["係数"]["a1"] * TCtmp + \
                            inputdata["REF"][ref_name]["Heatsource"][unit_id]["parameter"]["送水温度特性"][0]["係数"]["a0"]


    #----------------------------------------------------------------------------------
    # 蓄熱システムによる運転時間の補正（解説書 2.7.15）
    #----------------------------------------------------------------------------------

    # 蓄熱の場合のマトリックス操作（負荷率１に集約＋外気温を１レベル変える）
    for ref_name in inputdata["REF"]:

        inputdata["REF"][ref_name]["Qrefr_mod_sum"] = np.zeros(len(ToadbC))

        if inputdata["REF"][ref_name]["isStorage"] == "蓄熱":

            for unit_id, unit_configure in enumerate(inputdata["REF"][ref_name]["Heatsource"]):

                for iX in range(0,len(ToadbC)):

                    # 各外気温区分における最大能力の合計を算出[kW]
                    inputdata["REF"][ref_name]["Qrefr_mod_sum"][iX] += \
                        inputdata["REF"][ref_name]["Heatsource"][unit_id]["Qrefr_mod"][iX]


            for dd in range(0,365):
            
                if resultJson["REF"][ref_name]["LdREF"][dd] > 0:   # これを入れないと aveL(LdREF)でエラーとなる。
                
                    # 負荷率帯 LdREF のときの熱負荷
                    timeQmax =  aveL[ int(resultJson["REF"][ref_name]["LdREF"][dd]) - 1 ] \
                        * resultJson["REF"][ref_name]["Tref"][dd] * inputdata["REF"][ref_name]["QrefrMax"]
                
                    # 全負荷相当運転時間（熱負荷を最大負荷で除す）
                    if resultJson["REF"][ref_name]["TdREF"][dd] > 1:

                        resultJson["REF"][ref_name]["Tref"][dd] = timeQmax / ( inputdata["REF"][ref_name]["Qrefr_mod_sum"][ int(resultJson["REF"][ref_name]["TdREF"][dd]) - 2] )

                    elif resultJson["REF"][ref_name]["TdREF"][dd] == 1:

                        resultJson["REF"][ref_name]["Tref"][dd] = timeQmax / ( inputdata["REF"][ref_name]["Qrefr_mod_sum"][ int(resultJson["REF"][ref_name]["TdREF"][dd]) - 1] )                 

                    # 最大負荷率帯（負荷率帯 10）にする。
                    resultJson["REF"][ref_name]["LdREF"][dd] = len(aveL) - 1 
                
                    if resultJson["REF"][ref_name]["TdREF"][dd] > 1:
                        resultJson["REF"][ref_name]["TdREF"][dd] = resultJson["REF"][ref_name]["TdREF"][dd] - 1   # 外気温帯を1つ下げる。
                    elif resultJson["REF"][ref_name]["TdREF"][dd] == 1:
                        resultJson["REF"][ref_name]["TdREF"][dd] = resultJson["REF"][ref_name]["TdREF"][dd]


            if DEBUG:
                print( f'--- 熱源群名 {ref_name} ---')
                print( f'各外気温区分における最大能力の合計 Qrefr_mod_sum: \n {inputdata["REF"][ref_name]["Qrefr_mod_sum"]}' )


    # 蓄熱槽を持つシステムの追い掛け時運転時間補正（追い掛け運転開始時に蓄熱量がすべて使われない問題を解消） 2014/1/10
    for ref_name in inputdata["REF"]:

        resultJson["REF"][ref_name]["hoseiStorage"] = np.ones( [len(mxT), len(mxL)] ) 

        if inputdata["REF"][ref_name]["isStorage"] == "追掛":

            for ioa in range(0, len(mxT)):
                for iL in range(0, len(mxL)):

                    if int(resultJson["REF"][ref_name]["MxREFnum"][ioa][iL]) >= 2:

                        # 2台目以降の合計最大能力（＝熱交換器以外の能力）
                        Qrefr_mod_except_HEX = 0
                        for unit_id in range(1, int(resultJson["REF"][ref_name]["MxREFnum"][ioa][iL])):
                            Qrefr_mod_except_HEX += inputdata["REF"][ref_name]["Heatsource"][unit_id]["Qrefr_mod"][ioa]

                        resultJson["REF"][ref_name]["hoseiStorage"][ioa][iL] = \
                            1 - ( inputdata["REF"][ref_name]["Heatsource"][0]["Qrefr_mod"][ioa] * \
                                    (1 - resultJson["REF"][ref_name]["MxREFxL_real"][ioa][iL]) / \
                                    (resultJson["REF"][ref_name]["MxREFxL_real"][ioa][iL] * Qrefr_mod_except_HEX) )

            # 運転時間を補正
            for dd in range(0,365):
                if resultJson["REF"][ref_name]["Tref"][dd] > 0:
                    resultJson["REF"][ref_name]["Tref"][dd] = \
                        resultJson["REF"][ref_name]["Tref"][dd] * \
                        resultJson["REF"][ref_name]["hoseiStorage"][ int(resultJson["REF"][ref_name]["TdREF"][dd])-1 ][ int(resultJson["REF"][ref_name]["LdREF"][dd])-1 ]

        if DEBUG:

            print( f'--- 熱源群名 {ref_name} ---')
            print( f'蓄熱補正係数 hoseiStorage: {resultJson["REF"][ref_name]["hoseiStorage"]}' )
            print( f'負荷率帯マトリックス（蓄熱補正後） LdREF: \n {resultJson["REF"][ref_name]["LdREF"]}' )
            print( f'外気温帯マトリックス（蓄熱補正後） TdREF: \n {resultJson["REF"][ref_name]["TdREF"]}' )
            print( f'運転時間（蓄熱補正後） Tref:  {np.sum(resultJson["REF"][ref_name]["Tref"])}' )


    ##----------------------------------------------------------------------------------
    ## 熱源機器の一次エネルギー消費量（解説書 2.7.16）
    ##----------------------------------------------------------------------------------

    for ref_name in inputdata["REF"]:

        resultJson["REF"][ref_name]["ErefaprALL"]  = np.zeros( [len(mxT), len(mxL)] ) 
        resultJson["REF"][ref_name]["EpprALL"]     = np.zeros( [len(mxT), len(mxL)] ) 
        resultJson["REF"][ref_name]["EctfanrALL"]  = np.zeros( [len(mxT), len(mxL)] ) 
        resultJson["REF"][ref_name]["EctpumprALL"] = np.zeros( [len(mxT), len(mxL)] ) 

        for ioa in range(0, len(mxT)):
            for iL in range(0, len(mxL)):

                # 熱源主機：エネルギー消費量のマトリックス MxREFSUBperE
                for unit_id in range(0, int(resultJson["REF"][ref_name]["MxREFnum"][ioa][iL])):

                    resultJson["REF"][ref_name]["Heatsource"][unit_id]["MxREFSUBperE"][ioa][iL] = \
                        inputdata["REF"][ref_name]["Heatsource"][unit_id]["Erefr_mod"][ioa] * \
                        inputdata["REF"][ref_name]["Heatsource"][unit_id]["coeff_x"][ioa][iL] * \
                        inputdata["REF"][ref_name]["Heatsource"][unit_id]["coeff_tw"][ioa][iL]

                    resultJson["REF"][ref_name]["MxREFperE"][ioa][iL] += resultJson["REF"][ref_name]["Heatsource"][unit_id]["MxREFSUBperE"][ioa][iL]


                # 一台あたりの負荷率（熱源機器の負荷率＝最大能力を考慮した負荷率・ただし、熱源特性の上限・下限は考慮せず）
                aveLperU = resultJson["REF"][ref_name]["MxREFxL_real"][ioa][iL]

                if iL == len(mxL)-1:   
                    aveLperU = 1.2
            
                # 補機電力（燃焼系熱源のみ）
                # 発電機能付きの熱源機器が1台でもある場合
                if inputdata["REF"][ref_name]["checkGEGHP"] == 1:

                    for unit_id in range(0, int(resultJson["REF"][ref_name]["MxREFnum"][ioa][iL])):

                        if "消費電力自給装置" in inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceType"]:

                            # 非発電時の消費電力 [kW]
                            if inputdata["REF"][ref_name]["mode"] == "cooling":
                                E_nonGE = inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedCapacity_total"] * 0.017
                            elif inputdata["REF"][ref_name]["mode"] == "heating":
                                E_nonGE = inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedCapacity_total"] * 0.012

                            E_GEkW = inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedPowerConsumption_total"]  #  発電時の消費電力 [kW]
                
                            if aveLperU <= 0.3:
                                resultJson["REF"][ref_name]["ErefaprALL"][ioa][iL] += ( 0.3 * E_nonGE - (E_nonGE - E_GEkW) * aveLperU )
                            else:
                                resultJson["REF"][ref_name]["ErefaprALL"][ioa][iL] += ( aveLperU * E_GEkW )

                        else:

                            if aveLperU <= 0.3:
                                resultJson["REF"][ref_name]["ErefaprALL"][ioa][iL] += 0.3 * inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedPowerConsumption_total"] 
                            else:
                                resultJson["REF"][ref_name]["ErefaprALL"][ioa][iL] += aveLperU * inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedPowerConsumption_total"] 

                else:
                    
                    # 負荷に比例させる（発電機能なし）
                    refset_SubPower = 0
                    for unit_id in range(0, int(resultJson["REF"][ref_name]["MxREFnum"][ioa][iL])):
                        if inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedFuelConsumption_total"] > 0:
                            refset_SubPower += inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceRatedPowerConsumption_total"]

                    if aveLperU <= 0.3:
                        resultJson["REF"][ref_name]["ErefaprALL"][ioa][iL] += 0.3 * refset_SubPower
                    else:
                        resultJson["REF"][ref_name]["ErefaprALL"][ioa][iL] += aveLperU * refset_SubPower


                # 一次ポンプ
                for unit_id in range(0, int(resultJson["REF"][ref_name]["MxREFnum"][ioa][iL])):
                    resultJson["REF"][ref_name]["EpprALL"][ioa][iL] += \
                        inputdata["REF"][ref_name]["Heatsource"][unit_id]["PrimaryPumpPowerConsumption_total"]


                # 冷却塔ファン
                for unit_id in range(0, int(resultJson["REF"][ref_name]["MxREFnum"][ioa][iL])):
                    resultJson["REF"][ref_name]["EctfanrALL"][ioa][iL] += \
                        inputdata["REF"][ref_name]["Heatsource"][unit_id]["CoolingTowerFanPowerConsumption_total"]
                            
                
                # 冷却水ポンプ
                if inputdata["REF"][ref_name]["checkCTVWV"] == 1:  # 変流量制御がある場合

                    for unit_id in range(0, int(resultJson["REF"][ref_name]["MxREFnum"][ioa][iL])):

                        if "冷却水変流量" in inputdata["REF"][ref_name]["Heatsource"][unit_id]["HeatsourceType"]:

                            if aveLperU <= 0.5:
                                resultJson["REF"][ref_name]["EctpumprALL"][ioa][iL] += \
                                    0.5 * inputdata["REF"][ref_name]["Heatsource"][unit_id]["CoolingTowerPumpPowerConsumption_total"]
                            else:
                                resultJson["REF"][ref_name]["EctpumprALL"][ioa][iL] += \
                                    aveLperU * inputdata["REF"][ref_name]["Heatsource"][unit_id]["CoolingTowerPumpPowerConsumption_total"]
                        else:
                            resultJson["REF"][ref_name]["EctpumprALL"][ioa][iL] += \
                                inputdata["REF"][ref_name]["Heatsource"][unit_id]["CoolingTowerPumpPowerConsumption_total"]

                else:

                    for unit_id in range(0, int(resultJson["REF"][ref_name]["MxREFnum"][ioa][iL])):
                        resultJson["REF"][ref_name]["EctpumprALL"][ioa][iL] += \
                            inputdata["REF"][ref_name]["Heatsource"][unit_id]["CoolingTowerPumpPowerConsumption_total"]

        if DEBUG:

            print( f'--- 熱源群名 {ref_name} ---')

            print( f'熱源主機のエネルギー消費量 MxREFSUBperE: \n {resultJson["REF"][ref_name]["MxREFperE"]}' )
            print( f'熱源補機の消費電力 ErefaprALL: \n {resultJson["REF"][ref_name]["ErefaprALL"]}' )
            print( f'一次ポンプの消費電力 EpprALL: \n {resultJson["REF"][ref_name]["EpprALL"]}' )
            print( f'冷却塔ファンの消費電力 EctfanrALL: \n {resultJson["REF"][ref_name]["EctfanrALL"]}' )
            print( f'冷却水ポンプの消費電力 EctpumprALL: \n {resultJson["REF"][ref_name]["EctpumprALL"]}' )



    ##----------------------------------------------------------------------------------
    ## 熱熱源群の一次エネルギー消費量および消費電力（解説書 2.7.17）
    ##----------------------------------------------------------------------------------

    for ref_name in inputdata["REF"]:

        for dd in range(0,365):

            if resultJson["REF"][ref_name]["LdREF"][dd] == 0:
                
                resultJson["REF"][ref_name]["E_ref_ACc_day"][dd] =  0   # 補機電力 [MWh]
                resultJson["REF"][ref_name]["E_PPc_day"][dd]     =  0   # 一次ポンプ電力 [MWh]
                resultJson["REF"][ref_name]["E_CTfan_day"][dd]   =  0   # 冷却塔ファン電力 [MWh]
                resultJson["REF"][ref_name]["E_CTpump_day"][dd]  =  0   # 冷却水ポンプ電力 [MWh]
                
            else:

                iT = int(resultJson["REF"][ref_name]["TdREF"][dd]) -1
                iL = int(resultJson["REF"][ref_name]["LdREF"][dd]) -1
                
                # 熱源主機 [MJ/day]
                for unit_id in range(0,len(inputdata["REF"][ref_name]["Heatsource"])):

                    resultJson["REF"][ref_name]["E_ref_day"][dd]  += \
                        resultJson["REF"][ref_name]["Heatsource"][unit_id]["MxREFSUBperE"] [ iT ][ iL ] *3600/1000 * resultJson["REF"][ref_name]["Tref"][dd]

                # 補機電力 [MWh]
                resultJson["REF"][ref_name]["E_ref_ACc_day"][dd] += \
                    resultJson["REF"][ref_name]["ErefaprALL"][ iT ][ iL ] /1000 * resultJson["REF"][ref_name]["Tref"][dd]

                # 一次ポンプ電力 [MWh]
                resultJson["REF"][ref_name]["E_PPc_day"][dd] += \
                    resultJson["REF"][ref_name]["EpprALL"][ iT ][ iL ] /1000 * resultJson["REF"][ref_name]["Tref"][dd]

                # 冷却塔ファン電力 [MWh]
                resultJson["REF"][ref_name]["E_CTfan_day"][dd] += \
                    resultJson["REF"][ref_name]["EctfanrALL"][ iT ][ iL ] /1000 * resultJson["REF"][ref_name]["Tref"][dd]

                # 冷却水ポンプ電力 [MWh]
                resultJson["REF"][ref_name]["E_CTpump_day"][dd] += \
                    resultJson["REF"][ref_name]["EctpumprALL"][ iT ][ iL ] /1000 * resultJson["REF"][ref_name]["Tref"][dd]


        if DEBUG:

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

        resultJson["REF"][ref_name]["E_ref_source_Ele_day"] = np.zeros(365)

        for dd in range(0,365):

            # 熱源主機のエネルギー消費量 [MJ]
            resultJson["ENERGY"]["E_refsysr"]  += resultJson["REF"][ref_name]["E_ref_day"][dd]
            # 熱源補機電力消費量 [MWh]
            resultJson["ENERGY"]["E_refac"]  += resultJson["REF"][ref_name]["E_ref_ACc_day"][dd]
            # 一次ポンプ電力消費量 [MWh]
            resultJson["ENERGY"]["E_pumpP"]  += resultJson["REF"][ref_name]["E_PPc_day"][dd]
            # 冷却塔ファン電力消費量 [MWh]
            resultJson["ENERGY"]["E_ctfan"]  += resultJson["REF"][ref_name]["E_CTfan_day"][dd]
            # 冷却水ポンプ電力消費量 [MWh]
            resultJson["ENERGY"]["E_ctpump"] += resultJson["REF"][ref_name]["E_CTpump_day"][dd]


    print('熱源エネルギー計算完了')

    if DEBUG:

        print( f'熱源主機エネルギー消費量 E_refsysr: {resultJson["ENERGY"]["E_refsysr"]}' )
        print( f'熱源補機電力消費量 E_refac: {resultJson["ENERGY"]["E_refac"]}' )
        print( f'一次ポンプ電力消費量 E_pumpP: {resultJson["ENERGY"]["E_pumpP"]}' )
        print( f'冷却塔ファン電力消費量 E_ctfan: {resultJson["ENERGY"]["E_ctfan"]}' )
        print( f'冷却水ポンプ電力消費量 E_ctpump: {resultJson["ENERGY"]["E_ctpump"]}' )


    ##----------------------------------------------------------------------------------
    ## 設計一次エネルギー消費量（解説書 2.8）
    ##----------------------------------------------------------------------------------

    resultJson["E_airconditioning"] = \
        + resultJson["ENERGY"]["E_fan"] * 9760 \
        + resultJson["ENERGY"]["E_aex"] * 9760 \
        + resultJson["ENERGY"]["E_pump"]  * 9760 \
        + resultJson["ENERGY"]["E_refsysr"] \
        + resultJson["ENERGY"]["E_refac"] * 9760 \
        + resultJson["ENERGY"]["E_pumpP"] * 9760 \
        + resultJson["ENERGY"]["E_ctfan"] * 9760 \
        + resultJson["ENERGY"]["E_ctpump"] * 9760

    if DEBUG:
        print( f'空調設備の設計一次エネルギー消費量 MJ/m2 : {resultJson["E_airconditioning"]/roomAreaTotal}' )
        print( f'空調設備の設計一次エネルギー消費量 MJ : {resultJson["E_airconditioning"]}' )


    ##----------------------------------------------------------------------------------
    ## 基準一次エネルギー消費量 （解説書 10.1）
    ##----------------------------------------------------------------------------------    
    for room_zone_name in inputdata["AirConditioningZone"]:
    
        # 建物用途・室用途、ゾーン面積等の取得
        buildingType = inputdata["Rooms"][room_zone_name]["buildingType"]
        roomType     = inputdata["Rooms"][room_zone_name]["roomType"]
        zoneArea     = inputdata["Rooms"][room_zone_name]["roomArea"]

        resultJson["Es_airconditioning"] += \
            bc.RoomStandardValue[buildingType][roomType]["空調"][inputdata["Building"]["Region"]+"地域"] * zoneArea

    if DEBUG:
        print( f'空調設備の基準一次エネルギー消費量 MJ/m2 : {resultJson["Es_airconditioning"]/roomAreaTotal}' )
        print( f'空調設備の基準一次エネルギー消費量 MJ : {resultJson["Es_airconditioning"]}' )

    # BEI/ACの算出
    resultJson["BEI_AC"] = resultJson["E_airconditioning"] / resultJson["Es_airconditioning"]

    return resultJson


if __name__ == '__main__':

    print('----- airconditioning.py -----')
    # filename = './tests/airconditioning/ACtest_Case001.json'
    filename = './sample/sample01_WEBPRO_inputSheet_for_Ver2.5.json'


    # 入力ファイルの読み込み
    with open(filename, 'r') as f:
        inputdata = json.load(f)

    resultJson = calc_energy(inputdata, DEBUG=True)

    with open("resultJson.json",'w') as fw:
        json.dump(resultJson, fw, indent=4, ensure_ascii=False, cls = MyEncoder)

    print( f'BEI/AC: {resultJson["BEI_AC"]}')        
    print( f'設計一次エネルギー消費量 全体: {resultJson["Es_airconditioning"]}')
    print( f'設計一次エネルギー消費量 空調ファン: {resultJson["ENERGY"]["E_fan"] * 9760}')
    print( f'設計一次エネルギー消費量 空調全熱交換器: {resultJson["ENERGY"]["E_aex"] * 9760}')
    print( f'設計一次エネルギー消費量 二次ポンプ: {resultJson["ENERGY"]["E_pump"] * 9760}')
    print( f'設計一次エネルギー消費量 熱源主機: {resultJson["ENERGY"]["E_refsysr"]}')
    print( f'設計一次エネルギー消費量 熱源補機: {resultJson["ENERGY"]["E_refac"] * 9760}')
    print( f'設計一次エネルギー消費量 一次ポンプ: {resultJson["ENERGY"]["E_pumpP"] * 9760}')
    print( f'設計一次エネルギー消費量 冷却塔ファン: {resultJson["ENERGY"]["E_ctfan"] * 9760}')
    print( f'設計一次エネルギー消費量 冷却水ポンプ: {resultJson["ENERGY"]["E_ctpump"] * 9760}')

    # デバッグ用
    print( f'{resultJson["Es_airconditioning"]}, {resultJson["ENERGY"]["E_fan"] * 9760}, {resultJson["ENERGY"]["E_aex"] * 9760}, {resultJson["ENERGY"]["E_pump"] * 9760}, {resultJson["ENERGY"]["E_refsysr"]}, {resultJson["ENERGY"]["E_refac"] * 9760}, {resultJson["ENERGY"]["E_pumpP"] * 9760}, {resultJson["ENERGY"]["E_ctfan"] * 9760}, {resultJson["ENERGY"]["E_ctpump"] * 9760}')

