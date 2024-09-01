import re
import sys
import json
import numpy as np
import os
import math

import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from . import commons as bc
from . import climate

# データベースファイルの保存場所
database_directory =  os.path.dirname(os.path.abspath(__file__)) + "/database/"
# 気象データファイルの保存場所
climatedata_directory =  os.path.dirname(os.path.abspath(__file__)) + "/climatedata/"

def calc_energy(inputdata, DEBUG = False):

    # 計算結果を格納する変数
    resultJson = {

        "設計一次エネルギー消費量[MJ/年]": 0,   # 給湯設備の設計一次エネルギー消費量 [MJ/年]
        "基準一次エネルギー消費量[MJ/年]": 0,   # 給湯設備の基準一次エネルギー消費量 [MJ/年]
        "設計一次エネルギー消費量[GJ/年]": 0,   # 給湯設備の設計一次エネルギー消費量 [GJ/年]
        "基準一次エネルギー消費量[GJ/年]": 0,   # 給湯設備の基準一次エネルギー消費量 [GJ/年]
        "設計一次エネルギー消費量[MJ/m2年]": 0,   # 給湯設備の設計一次エネルギー消費量 [MJ/年]
        "基準一次エネルギー消費量[MJ/m2年]": 0,   # 給湯設備の基準一次エネルギー消費量 [MJ/年]
        "BEI/HW": 0,
        "計算対象面積": 0,
        
        "HotwaterSupplySystems":{
        },
        
        "for_CGS":{
            "Edesign_MWh_Ele_day": 0, # 給湯設備（エネルギー源を電力とする給湯機器のみが対象）の電力消費量
            "Edesign_MJ_CGS_day": 0,  # 排熱利用する給湯系統の一次エネルギー消費量
            "Q_eqp_CGS_day": 0        # 排熱が利用できる系統の給湯設備の給湯負荷
        }
    }
    
    # 地域別データの読み込み
    with open(database_directory + 'AREA.json', 'r', encoding='utf-8') as f:
        Area = json.load(f)


    ##----------------------------------------------------------------------------------
    ## 任意入力 （SP-6: カレンダーパターン)
    ##----------------------------------------------------------------------------------
    input_calendar = []
    if "calender" in inputdata["SpecialInputData"]:
        input_calendar = inputdata["SpecialInputData"]["calender"]

    ##----------------------------------------------------------------------------------
    ## 任意入力 （SP-9: 室使用条件)
    ##----------------------------------------------------------------------------------
    input_room_usage_condition = {}
    if "room_usage_condition" in inputdata["SpecialInputData"]:
        input_room_usage_condition = inputdata["SpecialInputData"]["room_usage_condition"] 

    #----------------------------------------------------------------------------------
    # 入力データの整理（計算準備）
    #----------------------------------------------------------------------------------

    # 台数をかけて、加熱能力等を算出する。
    for unit_name in inputdata["HotwaterSupplySystems"]:

        for unit_id, unit_configure in enumerate(inputdata["HotwaterSupplySystems"][unit_name]["HeatSourceUnit"]):

            # 加熱能力 kW/台 × 台
            inputdata["HotwaterSupplySystems"][unit_name]["HeatSourceUnit"][unit_id]["RatedCapacity_total"] = \
                unit_configure["RatedCapacity"] * unit_configure["Number"]

            # 消費エネルギー kW/台 × 台
            inputdata["HotwaterSupplySystems"][unit_name]["HeatSourceUnit"][unit_id]["RatedEnergyConsumption_total"] = \
                unit_configure["RatedPowerConsumption"] * unit_configure["Number"] * 9760/3600 + \
                unit_configure["RatedFuelConsumption"] * unit_configure["Number"]

            # 機器効率
            inputdata["HotwaterSupplySystems"][unit_name]["HeatSourceUnit"][unit_id]["RatedEfficiency"] = \
                inputdata["HotwaterSupplySystems"][unit_name]["HeatSourceUnit"][unit_id]["RatedCapacity_total"] / \
                inputdata["HotwaterSupplySystems"][unit_name]["HeatSourceUnit"][unit_id]["RatedEnergyConsumption_total"]

            if DEBUG:
                print(f'機器名称 {unit_name} の {unit_id+1} 台目')
                print(f'  - 給湯機器の効率 {inputdata["HotwaterSupplySystems"][unit_name]["HeatSourceUnit"][unit_id]["RatedEfficiency"]}')


    # 機器全体の合計加熱能力と重み付け平均効率を算出する。
    for unit_name in inputdata["HotwaterSupplySystems"]:

        # 合計加熱能力 [kW]
        inputdata["HotwaterSupplySystems"][unit_name]["RatedCapacity_total"] = 0

        tmp_Capacity_efficiency = 0

        for unit_id, unit_configure in enumerate(inputdata["HotwaterSupplySystems"][unit_name]["HeatSourceUnit"]):

            # 加熱能力の合計
            inputdata["HotwaterSupplySystems"][unit_name]["RatedCapacity_total"] += \
                unit_configure["RatedCapacity_total"]

            # 加熱能力 × 効率
            tmp_Capacity_efficiency += \
                unit_configure["RatedCapacity_total"] * \
                unit_configure["RatedEfficiency"]

        # 加熱能力で重み付けした平均効率 [-]
        inputdata["HotwaterSupplySystems"][unit_name]["RatedEfficiency_total"] = \
            tmp_Capacity_efficiency / \
            inputdata["HotwaterSupplySystems"][unit_name]["RatedCapacity_total"]

    #----------------------------------------------------------------------------------
    # 解説書 D.1 標準日積算湯使用量（標準室使用条件）
    #----------------------------------------------------------------------------------
    
    for room_name in inputdata["HotwaterRoom"]:

        # 日積算湯使用利用 [L/m2/day]
        hotwater_demand, hotwater_demand_washroom, hotwater_demand_shower, hotwater_demand_kitchen, hotwater_demand_other = \
            bc.get_roomHotwaterDemand(
                inputdata["Rooms"][room_name]["buildingType"], 
                inputdata["Rooms"][room_name]["roomType"],
                input_room_usage_condition
                
            )

        # 日積算給湯量参照値 [L/day]
        inputdata["HotwaterRoom"][room_name]["hotwater_demand"] = hotwater_demand * inputdata["Rooms"][room_name]["roomArea"]
        inputdata["HotwaterRoom"][room_name]["hotwater_demand_washroom"] = hotwater_demand_washroom * inputdata["Rooms"][room_name]["roomArea"]
        inputdata["HotwaterRoom"][room_name]["hotwater_demand_shower"]   = hotwater_demand_shower * inputdata["Rooms"][room_name]["roomArea"]
        inputdata["HotwaterRoom"][room_name]["hotwater_demand_kitchen"]  = hotwater_demand_kitchen * inputdata["Rooms"][room_name]["roomArea"]
        inputdata["HotwaterRoom"][room_name]["hotwater_demand_other"]    = hotwater_demand_other * inputdata["Rooms"][room_name]["roomArea"]

        # 各室の室使用スケジュール （＝室の同時使用率。 給湯需要がある室は、必ず空調されている前提とする）
        roomScheduleRoom, _, _, _, _ = \
            bc.get_roomUsageSchedule(inputdata["Rooms"][room_name]["buildingType"], inputdata["Rooms"][room_name]["roomType"], input_calendar)

        inputdata["HotwaterRoom"][room_name]["hotwaterSchedule"] = np.zeros(365)
        inputdata["HotwaterRoom"][room_name]["hotwaterSchedule"][ np.sum(roomScheduleRoom,1) > 0 ] = 1

        # 日別の給湯量 [L/day] (365×1)
        inputdata["HotwaterRoom"][room_name]["hotwater_demand_daily"] = \
            inputdata["HotwaterRoom"][room_name]["hotwater_demand"] * inputdata["HotwaterRoom"][room_name]["hotwaterSchedule"]

        inputdata["HotwaterRoom"][room_name]["hotwater_demand_washroom_daily"] = \
            inputdata["HotwaterRoom"][room_name]["hotwater_demand_washroom"] * inputdata["HotwaterRoom"][room_name]["hotwaterSchedule"]

        inputdata["HotwaterRoom"][room_name]["hotwater_demand_shower_daily"] = \
            inputdata["HotwaterRoom"][room_name]["hotwater_demand_shower"] * inputdata["HotwaterRoom"][room_name]["hotwaterSchedule"]

        inputdata["HotwaterRoom"][room_name]["hotwater_demand_kitchen_daily"] = \
            inputdata["HotwaterRoom"][room_name]["hotwater_demand_kitchen"] * inputdata["HotwaterRoom"][room_name]["hotwaterSchedule"]

        inputdata["HotwaterRoom"][room_name]["hotwater_demand_other_daily"] = \
            inputdata["HotwaterRoom"][room_name]["hotwater_demand_other"] * inputdata["HotwaterRoom"][room_name]["hotwaterSchedule"]


        # 日別の給湯量 [L/day] (365×1) の任意入力 （SP-11: 日積算湯使用量)
        if "hotwater_demand_daily" in inputdata["SpecialInputData"]:
            if room_name in inputdata["SpecialInputData"]["hotwater_demand_daily"]:

                if "洗面" in inputdata["SpecialInputData"]["hotwater_demand_daily"][room_name]:
                    inputdata["HotwaterRoom"][room_name]["hotwater_demand_washroom_daily"] = \
                        np.array(inputdata["SpecialInputData"]["hotwater_demand_daily"][room_name]["洗面"])

                if "シャワー" in inputdata["SpecialInputData"]["hotwater_demand_daily"][room_name]:
                    inputdata["HotwaterRoom"][room_name]["hotwater_demand_shower_daily"] = \
                        np.array(inputdata["SpecialInputData"]["hotwater_demand_daily"][room_name]["シャワー"])

                if "厨房" in inputdata["SpecialInputData"]["hotwater_demand_daily"][room_name]:
                    inputdata["HotwaterRoom"][room_name]["hotwater_demand_kitchen_daily"] = \
                        np.array(inputdata["SpecialInputData"]["hotwater_demand_daily"][room_name]["厨房"])

                if "その他" in inputdata["SpecialInputData"]["hotwater_demand_daily"][room_name]:
                    inputdata["HotwaterRoom"][room_name]["hotwater_demand_other_daily"] = \
                        np.array(inputdata["SpecialInputData"]["hotwater_demand_daily"][room_name]["その他"])

                # 合計を更新
                inputdata["HotwaterRoom"][room_name]["hotwater_demand_daily"]  = \
                    np.array(inputdata["HotwaterRoom"][room_name]["hotwater_demand_washroom_daily"]) + \
                    np.array(inputdata["HotwaterRoom"][room_name]["hotwater_demand_shower_daily"]) + \
                    np.array(inputdata["HotwaterRoom"][room_name]["hotwater_demand_kitchen_daily"]) + \
                    np.array(inputdata["HotwaterRoom"][room_name]["hotwater_demand_other_daily"])
                

        if DEBUG:
            print(f'室名称 {room_name}')
            print(f'  - 給湯使用量参照値 L/day {inputdata["HotwaterRoom"][room_name]["hotwater_demand"]}')
            print(f'  - 給湯日数 {np.sum(inputdata["HotwaterRoom"][room_name]["hotwaterSchedule"])}')
            print(f'  - 日別給湯使用量 {np.sum(inputdata["HotwaterRoom"][room_name]["hotwater_demand_daily"])}')
            print(f'  - 日別給湯使用量（手洗い） {np.sum(inputdata["HotwaterRoom"][room_name]["hotwater_demand_washroom_daily"])}')
            print(f'  - 日別給湯使用量（シャワー） {np.sum(inputdata["HotwaterRoom"][room_name]["hotwater_demand_shower_daily"])}')
            print(f'  - 日別給湯使用量（厨房） {np.sum(inputdata["HotwaterRoom"][room_name]["hotwater_demand_kitchen_daily"])}')
            print(f'  - 日別給湯使用量（その他） {np.sum(inputdata["HotwaterRoom"][room_name]["hotwater_demand_other_daily"])}')


    #----------------------------------------------------------------------------------
    # 解説書 D.5 給湯配管の線熱損失係数
    #----------------------------------------------------------------------------------

    # 給湯配管の線熱損失係数の読み込み
    with open(database_directory + 'ThermalConductivityPiping.json', 'r', encoding='utf-8') as f:
        thermal_conductivity_dict = json.load(f)

    for unit_name in inputdata["HotwaterSupplySystems"]:

        # 接続口径の種類
        if inputdata["HotwaterSupplySystems"][unit_name]["PipeSize"] <= 13:
            inputdata["HotwaterSupplySystems"][unit_name]["PipeSizeType"] = "13A以下"
        elif inputdata["HotwaterSupplySystems"][unit_name]["PipeSize"] <= 20:
            inputdata["HotwaterSupplySystems"][unit_name]["PipeSizeType"] = "20A以下"
        elif inputdata["HotwaterSupplySystems"][unit_name]["PipeSize"] <= 25:
            inputdata["HotwaterSupplySystems"][unit_name]["PipeSizeType"] = "25A以下"
        elif inputdata["HotwaterSupplySystems"][unit_name]["PipeSize"] <= 30:
            inputdata["HotwaterSupplySystems"][unit_name]["PipeSizeType"] = "30A以下"
        elif inputdata["HotwaterSupplySystems"][unit_name]["PipeSize"] <= 40:
            inputdata["HotwaterSupplySystems"][unit_name]["PipeSizeType"] = "40A以下"
        elif inputdata["HotwaterSupplySystems"][unit_name]["PipeSize"] <= 50:
            inputdata["HotwaterSupplySystems"][unit_name]["PipeSizeType"] = "50A以下"
        elif inputdata["HotwaterSupplySystems"][unit_name]["PipeSize"] <= 60:
            inputdata["HotwaterSupplySystems"][unit_name]["PipeSizeType"] = "60A以下"
        elif inputdata["HotwaterSupplySystems"][unit_name]["PipeSize"] <= 75:
            inputdata["HotwaterSupplySystems"][unit_name]["PipeSizeType"] = "75A以下"
        elif inputdata["HotwaterSupplySystems"][unit_name]["PipeSize"] <= 80:
            inputdata["HotwaterSupplySystems"][unit_name]["PipeSizeType"] = "80A以下"
        elif inputdata["HotwaterSupplySystems"][unit_name]["PipeSize"] <= 100:
            inputdata["HotwaterSupplySystems"][unit_name]["PipeSizeType"] = "100A以下"
        elif inputdata["HotwaterSupplySystems"][unit_name]["PipeSize"] <= 125:
            inputdata["HotwaterSupplySystems"][unit_name]["PipeSizeType"] = "125A以下"
        else:
            inputdata["HotwaterSupplySystems"][unit_name]["PipeSizeType"] = "125Aより大きい"

        # 線熱損失係数
        inputdata["HotwaterSupplySystems"][unit_name]["heatloss_coefficient"] = \
            thermal_conductivity_dict[inputdata["HotwaterSupplySystems"][unit_name]["PipeSizeType"]][inputdata["HotwaterSupplySystems"][unit_name]["InsulationType"]]

        if DEBUG:
            print(f'機器名称 {unit_name}')
            print(f'  - 配管接続口径 {inputdata["HotwaterSupplySystems"][unit_name]["PipeSizeType"]}')
            print(f'  - 線熱損失係数 {inputdata["HotwaterSupplySystems"][unit_name]["heatloss_coefficient"]}')


    #----------------------------------------------------------------------------------
    # 解説書 D.6 日平均給水温度
    #----------------------------------------------------------------------------------

    # 外気温データ（DAT形式）読み込み ＜365の行列＞
    Toa_ave = climate.readDatClimateData(climatedata_directory + "/" +
                                    Area[inputdata["Building"]["Region"]+"地域"]["気象データファイル名（給湯）"])

    # 空調運転モード
    with open(database_directory + 'ACoperationMode.json', 'r', encoding='utf-8') as f:
        ACoperationMode = json.load(f)

    # 各日の冷暖房期間の種類（冷房期、暖房期、中間期）（365×1の行列）
    ac_mode = ACoperationMode[Area[inputdata["Building"]["Region"]+"地域"]["空調運転モードタイプ"]]

    if inputdata["Building"]["Region"] == '1' or inputdata["Building"]["Region"] == '2':
        TWdata = 0.6639*Toa_ave + 3.466
    elif inputdata["Building"]["Region"] == '3' or inputdata["Building"]["Region"] == '4':
        TWdata = 0.6054*Toa_ave + 4.515
    elif inputdata["Building"]["Region"] == '5':
        TWdata = 0.8660*Toa_ave + 1.665
    elif inputdata["Building"]["Region"] == '6':
        TWdata = 0.8516*Toa_ave + 2.473
    elif inputdata["Building"]["Region"] == '7':
        TWdata = 0.9223*Toa_ave + 2.097
    elif inputdata["Building"]["Region"] == '8':
        TWdata = 0.6921*Toa_ave + 7.167


    #----------------------------------------------------------------------------------
    # 解説書 5.2 日積算湯使用量
    #----------------------------------------------------------------------------------

    # 各室熱源の容量比を求める。
    for room_name in inputdata["HotwaterRoom"]:

        inputdata["HotwaterRoom"][room_name]["RatedCapacity_All"] = 0

        for unit_id, unit_configure in enumerate(inputdata["HotwaterRoom"][room_name]["HotwaterSystem"]):

            inputdata["HotwaterRoom"][room_name]["HotwaterSystem"][unit_id]["RatedCapacity_total"] = \
                inputdata["HotwaterSupplySystems"][ unit_configure["SystemName"] ]["RatedCapacity_total"]

            inputdata["HotwaterRoom"][room_name]["RatedCapacity_All"] += \
                inputdata["HotwaterRoom"][room_name]["HotwaterSystem"][unit_id]["RatedCapacity_total"]

    for room_name in inputdata["HotwaterRoom"]:

        for unit_id, unit_configure in enumerate(inputdata["HotwaterRoom"][room_name]["HotwaterSystem"]):

            inputdata["HotwaterRoom"][room_name]["HotwaterSystem"][unit_id]["roomPowerRatio"] = \
                inputdata["HotwaterRoom"][room_name]["HotwaterSystem"][unit_id]["RatedCapacity_total"] / \
                inputdata["HotwaterRoom"][room_name]["RatedCapacity_All"]

            if DEBUG:
                print(f'機器名称 {unit_id}')
                print(f'熱源比率 {inputdata["HotwaterRoom"][room_name]["HotwaterSystem"][unit_id]["roomPowerRatio"]}')


    # 給湯対象室rの節湯器具による湯使用量削減効果を加味した日付dにおける室rの日積算湯使用量 
    for unit_name in inputdata["HotwaterSupplySystems"]:

        inputdata["HotwaterSupplySystems"][unit_name]["Qsr_eqp_daily"] = np.zeros(365)
        inputdata["HotwaterSupplySystems"][unit_name]["Qs_eqp_daily"] = np.zeros(365)

        for room_name in inputdata["HotwaterRoom"]:
            for unit_id, unit_configure in enumerate(inputdata["HotwaterRoom"][room_name]["HotwaterSystem"]):
                if unit_name == unit_configure["SystemName"]:

                    # 標準日積算給湯量 [L/day] →　配管長さ算出に必要
                    inputdata["HotwaterSupplySystems"][unit_name]["Qsr_eqp_daily"] += \
                        inputdata["HotwaterRoom"][room_name]["hotwater_demand_daily"] * unit_configure["roomPowerRatio"]

                    # 節湯効果を加味した日積算給湯量 [L/day]
                    # 係数は 解説書 附属書 D.3 節湯器具による湯使用量削減率
                    if unit_configure["HotWaterSavingSystem"] == "無":

                        inputdata["HotwaterSupplySystems"][unit_name]["Qs_eqp_daily"] += \
                            inputdata["HotwaterRoom"][room_name]["hotwater_demand_washroom_daily"] * 1.0 * unit_configure["roomPowerRatio"] + \
                            inputdata["HotwaterRoom"][room_name]["hotwater_demand_shower_daily"]   * 1.0 * unit_configure["roomPowerRatio"] + \
                            inputdata["HotwaterRoom"][room_name]["hotwater_demand_kitchen_daily"]  * 1.0 * unit_configure["roomPowerRatio"] + \
                            inputdata["HotwaterRoom"][room_name]["hotwater_demand_other_daily"]    * 1.0 * unit_configure["roomPowerRatio"]

                    elif unit_configure["HotWaterSavingSystem"] == "自動給湯栓":

                        inputdata["HotwaterSupplySystems"][unit_name]["Qs_eqp_daily"] += \
                            inputdata["HotwaterRoom"][room_name]["hotwater_demand_washroom_daily"] * 0.6 * unit_configure["roomPowerRatio"] + \
                            inputdata["HotwaterRoom"][room_name]["hotwater_demand_shower_daily"]   * 1.0 * unit_configure["roomPowerRatio"] + \
                            inputdata["HotwaterRoom"][room_name]["hotwater_demand_kitchen_daily"]  * 1.0 * unit_configure["roomPowerRatio"] + \
                            inputdata["HotwaterRoom"][room_name]["hotwater_demand_other_daily"]    * 1.0 * unit_configure["roomPowerRatio"]

                    elif unit_configure["HotWaterSavingSystem"] == "節湯B1":

                        inputdata["HotwaterSupplySystems"][unit_name]["Qs_eqp_daily"] += \
                            inputdata["HotwaterRoom"][room_name]["hotwater_demand_washroom_daily"] * 1.0  * unit_configure["roomPowerRatio"] + \
                            inputdata["HotwaterRoom"][room_name]["hotwater_demand_shower_daily"]   * 0.75 * unit_configure["roomPowerRatio"] + \
                            inputdata["HotwaterRoom"][room_name]["hotwater_demand_kitchen_daily"]  * 1.0  * unit_configure["roomPowerRatio"] + \
                            inputdata["HotwaterRoom"][room_name]["hotwater_demand_other_daily"]    * 1.0  * unit_configure["roomPowerRatio"]

        if DEBUG:
            print(f'機器名称 {unit_name}')
            print(f'  - 日積算湯供給量 {np.sum(inputdata["HotwaterSupplySystems"][unit_name]["Qsr_eqp_daily"])}')
            print(f'  - 日積算湯供給量（節湯込み） {np.sum(inputdata["HotwaterSupplySystems"][unit_name]["Qs_eqp_daily"])}')

            

    #----------------------------------------------------------------------------------
    # 解説書 5.3 配管長さ
    #----------------------------------------------------------------------------------

    for unit_name in inputdata["HotwaterSupplySystems"]:

        inputdata["HotwaterSupplySystems"][unit_name]["L_eqp"] = \
            np.max(inputdata["HotwaterSupplySystems"][unit_name]["Qsr_eqp_daily"]) * 7 / 1000

        if DEBUG:
            print(f'機器名称 {unit_name}')
            print(f'  - 配管長さ {inputdata["HotwaterSupplySystems"][unit_name]["L_eqp"]}')


    #----------------------------------------------------------------------------------
    # 解説書 5.4 年間配管熱損失量
    #----------------------------------------------------------------------------------

    # 室内設定温度
    Troom = np.zeros(365)
    Taround = np.zeros(365)

    for dd in range(0, 365):
        if ac_mode[dd] == "冷房":
            Troom[dd] = 26
        elif ac_mode[dd] == "中間":
            Troom[dd] = 24
        elif ac_mode[dd] == "暖房":
            Troom[dd] = 22

    # 配管熱損失 [kJ/day]
    for unit_name in inputdata["HotwaterSupplySystems"]:

        inputdata["HotwaterSupplySystems"][unit_name]["Qp_eqp"] = np.zeros(365)

        for dd in range(0,365):

            # デバッグ出力用
            Taround[dd] = (Toa_ave[dd]+Troom[dd])/2
            
            if inputdata["HotwaterSupplySystems"][unit_name]["Qs_eqp_daily"][dd] > 0:

                inputdata["HotwaterSupplySystems"][unit_name]["Qp_eqp"][dd] = \
                    inputdata["HotwaterSupplySystems"][unit_name]["L_eqp"] * \
                    inputdata["HotwaterSupplySystems"][unit_name]["heatloss_coefficient"] * \
                    ( 60 - (Toa_ave[dd]+Troom[dd])/2 ) * 24 * 3600 * 0.001

        if DEBUG:
            print(f'機器名称 {unit_name}')
            print(f'  - 配管熱損失 {np.sum(inputdata["HotwaterSupplySystems"][unit_name]["Qp_eqp"])}')
            print(f'  - 配管熱損失係数 {inputdata["HotwaterSupplySystems"][unit_name]["heatloss_coefficient"]}')

            # np.savetxt("配管周囲温度.txt", Taround)


    # ----------------------------------------------------------------------------------
    # 解説書 5.5 太陽熱利用システムの熱利用量
    # ----------------------------------------------------------------------------------

    # 日射量の計算
    _, _, Iod, Ios, Inn = climate.readHaspClimateData(climatedata_directory + "/C1_" +
                                    Area[inputdata["Building"]["Region"]+"地域"]["気象データファイル名"])

    for unit_name in inputdata["HotwaterSupplySystems"]:

        # 太陽熱利用量 [KJ/day]
        inputdata["HotwaterSupplySystems"][unit_name]["Qs_solargain"] = np.zeros(365)

        if (inputdata["HotwaterSupplySystems"][unit_name]["SolarSystemArea"] != "") and (inputdata["HotwaterSupplySystems"][unit_name]["SolarSystemArea"] != None):

            # 日積算日射量 [Wh/m2/day]
            Id, _, Is, _ = climate.solarRadiationByAzimuth( \
                inputdata["HotwaterSupplySystems"][unit_name]["SolarSystemDirection"], \
                inputdata["HotwaterSupplySystems"][unit_name]["SolarSystemAngle"], \
                Area[inputdata["Building"]["Region"]+"地域"]["緯度"], \
                Area[inputdata["Building"]["Region"]+"地域"]["経度"], \
                Iod, Ios, Inn)

            # 太陽熱利用量 [KJ/day]
            inputdata["HotwaterSupplySystems"][unit_name]["Qs_solargain"] = \
                (inputdata["HotwaterSupplySystems"][unit_name]["SolarSystemArea"]*0.4*0.85)*\
                    (Id + Is)*3600/1000000 * 1000

        if DEBUG:
            print(f'機器名称 {unit_name}')
            print(f'  - 太陽熱利用システムの熱利用量 {np.sum(inputdata["HotwaterSupplySystems"][unit_name]["Qs_solargain"])}')


    #----------------------------------------------------------------------------------
    # 解説書 5.6 年間給湯負荷
    #----------------------------------------------------------------------------------

    for unit_name in inputdata["HotwaterSupplySystems"]:

        inputdata["HotwaterSupplySystems"][unit_name]["Qh_eqp_daily"] = np.zeros(365)

        if inputdata["HotwaterSupplySystems"][unit_name]["SolarSystemArea"] == None:

            # 太陽熱利用が無い場合
            inputdata["HotwaterSupplySystems"][unit_name]["Qh_eqp_daily"] = \
                4.2 * inputdata["HotwaterSupplySystems"][unit_name]["Qs_eqp_daily"] * (43-TWdata)

        else:

            # 太陽熱利用がある場合
            tmpQh = 4.2 * inputdata["HotwaterSupplySystems"][unit_name]["Qs_eqp_daily"] * (43-TWdata)

            for dd in range(0,365):
                if (Toa_ave[dd] > 5) and (tmpQh[dd] > 0): # 日平均外気温が５度を超えていれば集熱
                
                    if tmpQh[dd]*0.1 > (tmpQh[dd] - inputdata["HotwaterSupplySystems"][unit_name]["Qs_solargain"][dd]):
                        
                        inputdata["HotwaterSupplySystems"][unit_name]["Qh_eqp_daily"][dd] = tmpQh[dd]*0.1

                    else:
                        inputdata["HotwaterSupplySystems"][unit_name]["Qh_eqp_daily"][dd] = \
                            tmpQh[dd] - inputdata["HotwaterSupplySystems"][unit_name]["Qs_solargain"][dd]

                else:
                    inputdata["HotwaterSupplySystems"][unit_name]["Qh_eqp_daily"][dd] = tmpQh[dd]


        if DEBUG:
            print(f'機器名称 {unit_name}')
            print(f'  - 日積算給湯負荷 {np.sum(inputdata["HotwaterSupplySystems"][unit_name]["Qh_eqp_daily"])}')


    #----------------------------------------------------------------------------------
    # 解説書 5.7 給湯設備の設計一次エネルギー消費量
    #----------------------------------------------------------------------------------

    for unit_name in inputdata["HotwaterSupplySystems"]:

        # 日別給湯負荷＋配管熱損失（＝給湯加熱負荷） [kJ/day]
        inputdata["HotwaterSupplySystems"][unit_name]["Q_eqp"] = \
            inputdata["HotwaterSupplySystems"][unit_name]["Qh_eqp_daily"] + \
            inputdata["HotwaterSupplySystems"][unit_name]["Qp_eqp"] * 2.5

        # 日別消費エネルギー消費量 [kJ/day]
        inputdata["HotwaterSupplySystems"][unit_name]["E_eqp"] = \
            inputdata["HotwaterSupplySystems"][unit_name]["Q_eqp"] / inputdata["HotwaterSupplySystems"][unit_name]["RatedEfficiency_total"]

        # 設計一次エネルギー消費量 [MJ/day]
        resultJson["設計一次エネルギー消費量[MJ/年]"] += np.sum(inputdata["HotwaterSupplySystems"][unit_name]["E_eqp"])/1000

        if DEBUG:
            print(f'機器名称 {unit_name}')
            print(f'  - 日別給湯負荷と配管熱損失 {np.sum(inputdata["HotwaterSupplySystems"][unit_name]["Q_eqp"])}')
            print(f'  - 日別消費エネルギー消費量 {np.sum(inputdata["HotwaterSupplySystems"][unit_name]["E_eqp"])}')

    if DEBUG:
        print(f'設計一次エネルギー消費量 {resultJson["設計一次エネルギー消費量[MJ/年]"]} MJ/年')


    #----------------------------------------------------------------------------------
    # 結果の保存
    #----------------------------------------------------------------------------------

    for unit_name in inputdata["HotwaterSupplySystems"]:

        resultJson["HotwaterSupplySystems"][unit_name] = inputdata["HotwaterSupplySystems"][unit_name]

        resultJson["HotwaterSupplySystems"][unit_name]["湯使用量（節湯込）[L/年]"] = np.sum(inputdata["HotwaterSupplySystems"][unit_name]["Qs_eqp_daily"]/1000)
        resultJson["HotwaterSupplySystems"][unit_name]["太陽熱利用量[MJ/年]"] = np.sum(inputdata["HotwaterSupplySystems"][unit_name]["Qs_solargain"]/1000)
        resultJson["HotwaterSupplySystems"][unit_name]["給湯加熱負荷[MJ/年]"] = np.sum(inputdata["HotwaterSupplySystems"][unit_name]["Q_eqp"]/1000)
        resultJson["HotwaterSupplySystems"][unit_name]["配管熱損失[MJ/年]"] = np.sum(inputdata["HotwaterSupplySystems"][unit_name]["Qp_eqp"]/1000)
        resultJson["HotwaterSupplySystems"][unit_name]["設計一次エネルギー消費量[MJ/年]"] = np.sum(inputdata["HotwaterSupplySystems"][unit_name]["E_eqp"]/1000)

        # 初期化　→ 次の処理で値を代入
        resultJson["HotwaterSupplySystems"][unit_name]["基準一次エネルギー消費量[MJ/年]"] = 0


    #----------------------------------------------------------------------------------
    # 解説書 10.4 給湯設備の基準一次エネルギー消費量
    #----------------------------------------------------------------------------------

    resultJson["基準一次エネルギー消費量[MJ/年]"] = 0
    for room_name in inputdata["HotwaterRoom"]:

        # 建物用途、室用途（可読性重視で一旦変数に代入する）
        buildingType = inputdata["Rooms"][room_name]["buildingType"]
        roomType     = inputdata["Rooms"][room_name]["roomType"]
    
        #　計算対象面積[m2]
        resultJson["計算対象面積"] += inputdata["Rooms"][room_name]["roomArea"]

        inputdata["HotwaterRoom"][room_name]["基準一次エネルギー消費量[MJ/年]"] = \
            bc.RoomStandardValue[buildingType][roomType]["給湯"][inputdata["Building"]["Region"]+"地域"] * \
            inputdata["Rooms"][room_name]["roomArea"]

        # 積算する
        resultJson["基準一次エネルギー消費量[MJ/年]"] += inputdata["HotwaterRoom"][room_name]["基準一次エネルギー消費量[MJ/年]"] 

        # 熱源単位に振り分け（参考情報）
        for unit_id, unit_configure in enumerate(inputdata["HotwaterRoom"][room_name]["HotwaterSystem"]):

            unit_name = unit_configure["SystemName"]

            resultJson["HotwaterSupplySystems"][unit_name]["基準一次エネルギー消費量[MJ/年]"] += \
                inputdata["HotwaterRoom"][room_name]["基準一次エネルギー消費量[MJ/年]"] * unit_configure["roomPowerRatio"]



    # BEI/HW
    resultJson["BEI/HW"] = resultJson["設計一次エネルギー消費量[MJ/年]"] / resultJson["基準一次エネルギー消費量[MJ/年]"]
    resultJson["BEI/HW"] = math.ceil(resultJson["BEI/HW"] * 100)/100

    resultJson["設計一次エネルギー消費量[GJ/年]"] = resultJson["設計一次エネルギー消費量[MJ/年]"] /1000
    resultJson["基準一次エネルギー消費量[GJ/年]"] = resultJson["基準一次エネルギー消費量[MJ/年]"] /1000
    resultJson["設計一次エネルギー消費量[MJ/m2年]"] = resultJson["設計一次エネルギー消費量[MJ/年]"] / resultJson["計算対象面積"]
    resultJson["基準一次エネルギー消費量[MJ/m2年]"] = resultJson["基準一次エネルギー消費量[MJ/年]"] / resultJson["計算対象面積"]


    for unit_name in inputdata["HotwaterSupplySystems"]:
        resultJson["HotwaterSupplySystems"][unit_name]["設計値/基準値"] = \
            resultJson["HotwaterSupplySystems"][unit_name]["設計一次エネルギー消費量[MJ/年]"] / resultJson["HotwaterSupplySystems"][unit_name]["基準一次エネルギー消費量[MJ/年]"]



    #----------------------------------------------------------------------------------
    # CGS計算用変数 （解説書 ８章 附属書 G.10 他の設備の計算結果の読み込み）
    #----------------------------------------------------------------------------------

    Edesign_MWh_Ele_hour = np.zeros((365,24))
    Edesign_MJ_CGS_hour  = np.zeros((365,24))
    Q_eqp_CGS_hour       = np.zeros((365,24))

    if len(inputdata["CogenerationSystems"]) == 1: # コジェネがあれば実行
    
        for cgs_name in inputdata["CogenerationSystems"]:

            # コジェネ系統にない給湯設備の電力消費量を積算
            for unit_name in inputdata["HotwaterSupplySystems"]:
                
                if inputdata["CogenerationSystems"][cgs_name]["HowWaterSystem"] != "" and \
                    inputdata["CogenerationSystems"][cgs_name]["HowWaterSystem"] == unit_name:

                    # コジェネの排熱利用先であれば
                    for dd in range(0,365):
                        Edesign_MJ_CGS_hour[dd] += inputdata["HotwaterSupplySystems"][unit_name]["E_eqp"][dd]/24/1000 * np.ones(24)
                        Q_eqp_CGS_hour[dd] += inputdata["HotwaterSupplySystems"][unit_name]["Q_eqp"][dd]/24/1000 * np.ones(24)

                else:

                    # コジェネの排熱利用先以外であれば
                    for unit_id, unit_configure in enumerate(inputdata["HotwaterSupplySystems"][unit_name]["HeatSourceUnit"]):
                    
                        if unit_configure["UsageType"] == "給湯負荷用":
                            if unit_configure["HeatSourceType"] == "電気瞬間湯沸器" or unit_configure["HeatSourceType"] == "貯湯式電気温水器" or \
                                unit_configure["HeatSourceType"] == "業務用ヒートポンプ給湯機" or unit_configure["HeatSourceType"] == "家庭用ヒートポンプ給湯機":

                                for dd in range(0,365):
                                    Edesign_MWh_Ele_hour[dd] += inputdata["HotwaterSupplySystems"][unit_name]["E_eqp"][dd]/24/1000/9760 * np.ones(24)


        resultJson["for_CGS"]["Edesign_MWh_Ele_day"] = np.sum(Edesign_MWh_Ele_hour,1)
        resultJson["for_CGS"]["Edesign_MJ_CGS_day"]  = np.sum(Edesign_MJ_CGS_hour,1)
        resultJson["for_CGS"]["Q_eqp_CGS_day"]       = np.sum(Q_eqp_CGS_hour,1)


    ##----------------------------------------------------------------------------------
    # 不要な要素を削除
    ##----------------------------------------------------------------------------------

    for unitID, isys in resultJson["HotwaterSupplySystems"].items():
        del resultJson["HotwaterSupplySystems"][unitID]["Qsr_eqp_daily"]
        del resultJson["HotwaterSupplySystems"][unitID]["Qs_eqp_daily"]
        del resultJson["HotwaterSupplySystems"][unitID]["L_eqp"]
        del resultJson["HotwaterSupplySystems"][unitID]["Qp_eqp"]
        del resultJson["HotwaterSupplySystems"][unitID]["Qs_solargain"]
        del resultJson["HotwaterSupplySystems"][unitID]["Qh_eqp_daily"]
        del resultJson["HotwaterSupplySystems"][unitID]["Q_eqp"]
        del resultJson["HotwaterSupplySystems"][unitID]["E_eqp"]


    return resultJson


#%%
if __name__ == '__main__':

    print('----- hotwatersupply.py -----')
    # filename = './sample/CGS_case_office_00.json'
    filename = './sample/Builelib_sample_SP11.json'

    # 入力データ（json）の読み込み
    with open(filename, 'r', encoding='utf-8') as f:
        inputdata = json.load(f)

    resultJson = calc_energy(inputdata, DEBUG = True)

    with open("resultJson_HW.json",'w', encoding='utf-8') as fw:
        json.dump(resultJson, fw, indent=4, ensure_ascii=False, cls = bc.MyEncoder)

