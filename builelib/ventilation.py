import json
import numpy as np
import os
import math

import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import commons as bc
from . import commons as bc

# データベースファイルの保存場所
database_directory =  os.path.dirname(os.path.abspath(__file__)) + "/database/"
# 気象データファイルの保存場所
climatedata_directory =  os.path.dirname(os.path.abspath(__file__)) + "/climatedata/"


## 中間期平均外気温（附属書B.1）
def set_OutdoorTemperature(region):
    if region == "1":
        Toa_ave_design = 22.7
    elif region == "2":
        Toa_ave_design = 22.8
    elif region == "3":
        Toa_ave_design = 24.7
    elif region == "4":
        Toa_ave_design = 26.8
    elif region == "5":
        Toa_ave_design = 27.1
    elif region == "6":
        Toa_ave_design = 27.6
    elif region == "7":
        Toa_ave_design = 26.0
    elif region == "8":
        Toa_ave_design = 26.2
    else:
        raise Exception('Error!')

    return Toa_ave_design


def calc_energy(inputdata, DEBUG = False):
    
    # 計算結果を格納する変数
    resultJson = {

        "設計一次エネルギー消費量[MJ/年]": 0,    # 換気設備の設計一次エネルギー消費量 [MJ/年]
        "基準一次エネルギー消費量[MJ/年]": 0,    # 換気設備の基準一次エネルギー消費量 [MJ/年]
        "設計一次エネルギー消費量[GJ/年]": 0,    # 換気設備の設計一次エネルギー消費量 [GJ/年]
        "基準一次エネルギー消費量[GJ/年]": 0,    # 換気設備の基準一次エネルギー消費量 [GJ/年]
        "設計一次エネルギー消費量[MJ/m2年]": 0,  # 換気設備の設計一次エネルギー消費量 [MJ/年]
        "基準一次エネルギー消費量[MJ/m2年]": 0,  # 換気設備の基準一次エネルギー消費量 [MJ/年]
        "計算対象面積": 0,
        "BEI/V": 0,

        "時刻別設計一次エネルギー消費量[MJ/h]": np.zeros((365,24)),  # 時刻別設計一次エネルギー消費量 [MJ]

        "ventilation":{   
        },

        "for_CGS":{
            "Edesign_MWh_day": np.zeros(365)
        }
    }

    # 室毎（換気系統毎）のループ
    for roomID, isys in inputdata["VentilationRoom"].items():

        # 建物用途、室用途（可読性重視で一旦変数に代入する）
        buildingType = inputdata["Rooms"][roomID]["buildingType"]
        roomType     = inputdata["Rooms"][roomID]["roomType"]
        inputdata["VentilationRoom"][roomID]["buildingType"]  = buildingType
        inputdata["VentilationRoom"][roomID]["roomType"]      = roomType

        # 室面積
        inputdata["VentilationRoom"][roomID]["roomArea"] = inputdata["Rooms"][roomID]["roomArea"]
        resultJson["計算対象面積"] += inputdata["Rooms"][roomID]["roomArea"]   # 保存用

        ##----------------------------------------------------------------------------------
        ## 年間換気運転時間 （解説書 B.2）
        ##----------------------------------------------------------------------------------

        if "SpecialInputData" in inputdata:

            input_calendar = {}
            if "calender" in inputdata["SpecialInputData"]:
                input_calendar = inputdata["SpecialInputData"]["calender"]   # SP-6

            input_room_usage_condition = {}
            if "room_usage_condition" in inputdata["SpecialInputData"]:
                input_room_usage_condition = inputdata["SpecialInputData"]["room_usage_condition"]   # SP-9

            inputdata["VentilationRoom"][roomID]["opeTime_hourly"] = bc.get_dailyOpeSchedule_ventilation(buildingType, roomType, input_room_usage_condition, input_calendar)

        else:
            inputdata["VentilationRoom"][roomID]["opeTime_hourly"] = bc.get_dailyOpeSchedule_ventilation(buildingType, roomType)


        # 年間換気運転時間
        inputdata["VentilationRoom"][roomID]["opeTime"] = np.sum(np.sum(inputdata["VentilationRoom"][roomID]["opeTime_hourly"]))

        # 接続されている換気機器の種類に応じて集計処理を実行
        inputdata["VentilationRoom"][roomID]["isVentilationUsingAC"] = False
        inputdata["VentilationRoom"][roomID]["AC_CoolingCapacity_total"] = 0
        inputdata["VentilationRoom"][roomID]["totalAirVolume_supply"] = 0
        inputdata["VentilationRoom"][roomID]["totalAirVolume_exhaust"] = 0

        # 換気代替空調機があるかどうかを判定
        for unitID, iunit in inputdata["VentilationRoom"][roomID]["VentilationUnitRef"].items():
            
            if iunit["UnitType"] == "空調":

                # 換気代替空調機であるかどうかを判定（UnitTypeが「空調」である機器があれば、換気代替空調機であると判断する）
                inputdata["VentilationRoom"][roomID]["isVentilationUsingAC"]  = True

                # もし複数あれば、能力を合計する（外気冷房判定用）
                inputdata["VentilationRoom"][roomID]["AC_CoolingCapacity_total"] += inputdata["VentilationUnit"][unitID]["AC_CoolingCapacity"]

            elif iunit["UnitType"] == "給気":

                # 給気風量の合計（外気冷房判定用）
                inputdata["VentilationRoom"][roomID]["totalAirVolume_supply"] += inputdata["VentilationUnit"][unitID]["FanAirVolume"]

            elif iunit["UnitType"] == "排気":

                # 排気風量の合計（外気冷房判定用）
                inputdata["VentilationRoom"][roomID]["totalAirVolume_exhaust"] += inputdata["VentilationUnit"][unitID]["FanAirVolume"]


        # 接続されている換気機器のリストに室の情報を追加（複数室に跨がる換気送風機の計算のため）
        for unitID, iunit in inputdata["VentilationRoom"][roomID]["VentilationUnitRef"].items():
    
            # 室の名称を追加
            if "roomList" in inputdata["VentilationUnit"][unitID]:
                inputdata["VentilationUnit"][unitID]["roomList"].append(roomID)
            else:
                inputdata["VentilationUnit"][unitID]["roomList"] = [roomID]

            # 室の運転時間を追加
            if "opeTimeList" in inputdata["VentilationUnit"][unitID]:
                inputdata["VentilationUnit"][unitID]["opeTimeList"].append(inputdata["VentilationRoom"][roomID]["opeTime"])
                inputdata["VentilationUnit"][unitID]["opeTimeList_hourly"].append(inputdata["VentilationRoom"][roomID]["opeTime_hourly"])
            else:
                inputdata["VentilationUnit"][unitID]["opeTimeList"] = [inputdata["VentilationRoom"][roomID]["opeTime"]]
                inputdata["VentilationUnit"][unitID]["opeTimeList_hourly"] = [inputdata["VentilationRoom"][roomID]["opeTime_hourly"]]


            # 室の床面積を追加
            if "roomAreaList" in inputdata["VentilationUnit"][unitID]:
                inputdata["VentilationUnit"][unitID]["roomAreaList"].append(inputdata["VentilationRoom"][roomID]["roomArea"] )
            else:
                inputdata["VentilationUnit"][unitID]["roomAreaList"] = [inputdata["VentilationRoom"][roomID]["roomArea"] ]
                
            # 換気代替空調機か否かを追加
            if "isVentilationUsingAC" in inputdata["VentilationUnit"][unitID]:
                inputdata["VentilationUnit"][unitID]["isVentilationUsingAC"].append(inputdata["VentilationRoom"][roomID]["isVentilationUsingAC"])
            else:
                inputdata["VentilationUnit"][unitID]["isVentilationUsingAC"] = [inputdata["VentilationRoom"][roomID]["isVentilationUsingAC"]]


        if DEBUG:
            print( f'室名称  {roomID}')
            print( f'  - 換気代替空調の有無 {inputdata["VentilationRoom"][roomID]["isVentilationUsingAC"]}')
            print( f'  - 換換気代替空調系統の熱源容量の合計容量 {inputdata["VentilationRoom"][roomID]["AC_CoolingCapacity_total"]}')
            print( f'  - 換気代替空調系統の給気風量の合計容量 {inputdata["VentilationRoom"][roomID]["totalAirVolume_supply"]}')
            print( f'  - 換気代替空調系統の排気風量の合計容量 {inputdata["VentilationRoom"][roomID]["totalAirVolume_exhaust"]}')

    if DEBUG:
        for unitID, iunit in inputdata["VentilationUnit"].items():
            print( f'換気名称  {unitID}')
            print( f'  - 室リスト {inputdata["VentilationUnit"][unitID]["roomList"]}')
            print( f'  - 床面積リスト {inputdata["VentilationUnit"][unitID]["roomAreaList"]}')
            print( f'  - 運転時間リスト {inputdata["VentilationUnit"][unitID]["opeTimeList"]}')
            print( f'  - 換気代替空調機の有無 {inputdata["VentilationUnit"][unitID]["isVentilationUsingAC"]}')


    ##----------------------------------------------------------------------------------
    ## 送風機の制御方式に応じて定められる係数（解説書 3.2）
    ##----------------------------------------------------------------------------------
    with open( database_directory + '/ventilationControl.json', 'r', encoding='utf-8') as f:
        ventilationCtrl = json.load(f)

    
    ##----------------------------------------------------------------------------------
    ## 換気送風機の年間電力消費量（解説書 3.3）
    ##----------------------------------------------------------------------------------
    for unitID, iunit in inputdata["VentilationUnit"].items():

        # 電動機定格出力[kW]から消費電力[kW]を計算（1台あたり、制御なし）
        if iunit["PowerConsumption"] != None:
            Ekw = iunit["PowerConsumption"]
        elif iunit["MoterRatedPower"] != None:
            Ekw = iunit["MoterRatedPower"] / 0.75
        else:
            raise Exception('Error!')

        # 消費電力（制御込み）[kW]
        inputdata["VentilationUnit"][unitID]["Energy_kW"] = \
            Ekw * iunit["Number"] \
            * ventilationCtrl["HighEfficiencyMotor"][ iunit["HighEfficiencyMotor"] ] \
            * ventilationCtrl["Inverter"][ iunit["Inverter"] ] \
            * ventilationCtrl["AirVolumeControl"][ iunit["AirVolumeControl"] ]

        # 床面積の合計
        inputdata["VentilationUnit"][unitID]["roomAreaTotal"] = sum( iunit["roomAreaList"] )

        # 最大の運転時間
        inputdata["VentilationUnit"][unitID]["maxopeTime"] = 0
        inputdata["VentilationUnit"][unitID]["maxopeTime_hourly"] = np.zeros((365,24))

        for opeTime_id, opeTime_V in enumerate(iunit["opeTimeList"]):
            if inputdata["VentilationUnit"][unitID]["maxopeTime"] < opeTime_V:
                inputdata["VentilationUnit"][unitID]["maxopeTime"] = opeTime_V
                inputdata["VentilationUnit"][unitID]["maxopeTime_hourly"] = inputdata["VentilationUnit"][unitID]["opeTimeList_hourly"][opeTime_id]

        # 換気代替空調機と換気送風機が混在していないかをチェック  →  混在していたらエラー
        if not all(iunit["isVentilationUsingAC"]) and any(iunit["isVentilationUsingAC"]):
            raise Exception('Error!')


    # 再度、室毎（換気系統毎）のループ
    for roomID, isys in inputdata["VentilationRoom"].items():

        # 各室の計算結果を格納
        resultJson["ventilation"][roomID] = inputdata["VentilationRoom"][roomID]
        resultJson["ventilation"][roomID]["時刻別設計一次エネルギー消費量[MJ/h]"] = np.zeros((365,24))
        resultJson["ventilation"][roomID]["設計値[MJ]"] = 0
        resultJson["ventilation"][roomID]["基準値[MJ]"] = 0
        resultJson["ventilation"][roomID]["設計値/基準値"] = 0
        resultJson["ventilation"][roomID]["換気システムの種類"] = ""

        ##----------------------------------------------------------------------------------
        ## 換気代替空調機の年間電力消費量（解説書 3.4）
        ##----------------------------------------------------------------------------------
        if isys["isVentilationUsingAC"]:  ## 換気代替空調機の場合（仕様書 3.4）

            resultJson["ventilation"][roomID]["換気システムの種類"] = "換気代替空調機"

            # 外気取り込み量
            if isys["totalAirVolume_supply"] > 0:
                OutdoorVolume = isys["totalAirVolume_supply"]
            elif isys["totalAirVolume_exhaust"] > 0:
                OutdoorVolume = isys["totalAirVolume_exhaust"]
            else:
                OutdoorVolume = 0

            # 外気冷房に必要な外気導入量
            requiredOAVolume = 1000 * isys["AC_CoolingCapacity_total"] / (0.33 * (40 - set_OutdoorTemperature( inputdata["Building"]["Region"] )))

            # 年間稼働率（表.20）
            if OutdoorVolume > requiredOAVolume:
                Cac = 0.35
                Cfan = 0.65
            else:
                Cac = 1.00
                Cfan = 1.00               

            if DEBUG:
                print( f'室名称  {roomID}')
                print( f'  - 外気取り込み量 {OutdoorVolume}')
                print( f'  - 外気冷房に必要な外気導入量 {requiredOAVolume}')
                print( f'  - 年間稼働率 Cac {Cac}')
                print( f'  - 年間稼働率 Cfan {Cfan}')


            for unitID, iunit in inputdata["VentilationRoom"][roomID]["VentilationUnitRef"].items():
                
                if iunit["UnitType"] == "空調":  ## 換気代替空調機

                    # 熱源機とポンプ
                    if inputdata["VentilationUnit"][unitID]["VentilationRoomType"] != "":

                        # 負荷率（表.19）
                        if inputdata["VentilationUnit"][unitID]["VentilationRoomType"] == "エレベータ機械室":
                            xL = 0.3
                        elif inputdata["VentilationUnit"][unitID]["VentilationRoomType"] == "電気室":
                            xL = 0.6
                        elif inputdata["VentilationUnit"][unitID]["VentilationRoomType"] == "機械室":
                            xL = 0.6
                        elif inputdata["VentilationUnit"][unitID]["VentilationRoomType"] == "その他":
                            xL = 1.0
                        else:
                            # 直接数値を入力する場合
                            xL = float(inputdata["VentilationUnit"][unitID]["VentilationRoomType"] )

                        # 換気代替空調機本体（時刻別）
                        resultJson["ventilation"][roomID]["時刻別設計一次エネルギー消費量[MJ/h]"] += \
                            ( inputdata["VentilationUnit"][unitID]["AC_CoolingCapacity"] * xL / (2.71 * inputdata["VentilationUnit"][unitID]["AC_RefEfficiency"] )  \
                            + inputdata["VentilationUnit"][unitID]["AC_PumpPower"] /0.75 ) \
                            * inputdata["VentilationRoom"][roomID]["roomArea"] / inputdata["VentilationUnit"][unitID]["roomAreaTotal"] \
                            * inputdata["VentilationUnit"][unitID]["maxopeTime_hourly"] * bc.fprime * 10**(-3) * Cac

                    # 空調機に付属するファン（時刻別）
                    resultJson["ventilation"][roomID]["時刻別設計一次エネルギー消費量[MJ/h]"] += \
                        inputdata["VentilationUnit"][unitID]["Energy_kW"]  \
                        * inputdata["VentilationRoom"][roomID]["roomArea"] / inputdata["VentilationUnit"][unitID]["roomAreaTotal"] \
                        * inputdata["VentilationUnit"][unitID]["maxopeTime_hourly"] * bc.fprime * 10**(-3) * Cac

                else:

                    # 換気代替空調機と併設される送風機(時刻別)
                    resultJson["ventilation"][roomID]["時刻別設計一次エネルギー消費量[MJ/h]"] += \
                        inputdata["VentilationUnit"][unitID]["Energy_kW"]  \
                        * inputdata["VentilationRoom"][roomID]["roomArea"] / inputdata["VentilationUnit"][unitID]["roomAreaTotal"] \
                        * inputdata["VentilationUnit"][unitID]["maxopeTime_hourly"] * bc.fprime * 10**(-3) * Cfan


                if DEBUG:
                    print( f'室名称 {roomID}, 機器名称 {unitID}')
                    # print( f'  - 運転時間 {inputdata["VentilationUnit"][unitID]["maxopeTime"] }')
                    print( f'  - 消費電力[W/m2] {inputdata["VentilationUnit"][unitID]["Energy_kW"]/inputdata["VentilationRoom"][roomID]["roomArea"]*1000}')


        else: ## 換気送風機の場合（仕様書 3.3）

            resultJson["ventilation"][roomID]["換気システムの種類"] = "換気送風機"

            for unitID, iunit in inputdata["VentilationRoom"][roomID]["VentilationUnitRef"].items():
            
                # エネルギー消費量 [kW * m2/m2 * kJ/KWh] (時刻別)
                resultJson["ventilation"][roomID]["時刻別設計一次エネルギー消費量[MJ/h]"] += inputdata["VentilationUnit"][unitID]["Energy_kW"]  \
                    * inputdata["VentilationRoom"][roomID]["roomArea"] / inputdata["VentilationUnit"][unitID]["roomAreaTotal"] \
                    * inputdata["VentilationUnit"][unitID]["maxopeTime_hourly"] * bc.fprime * 10**(-3)


    ##----------------------------------------------------------------------------------
    ## 基準一次エネルギー消費量 [MJ] （解説書 10.2）
    ##----------------------------------------------------------------------------------
    for roomID, isys in inputdata["VentilationRoom"].items():

        # 建物用途、室用途（可読性重視で一旦変数に代入する）
        buildingType = inputdata["Rooms"][roomID]["buildingType"]
        roomType     = inputdata["Rooms"][roomID]["roomType"]
    
        resultJson["ventilation"][roomID]["基準値[MJ]"] = \
            bc.RoomStandardValue[buildingType][roomType]["換気"] * inputdata["Rooms"][roomID]["roomArea"]


    ##----------------------------------------------------------------------------------
    # 結果の集計
    ##----------------------------------------------------------------------------------

    for roomID, isys in inputdata["VentilationRoom"].items():

        resultJson["ventilation"][roomID]["設計値[MJ]"] = np.sum( np.sum( resultJson["ventilation"][roomID]["時刻別設計一次エネルギー消費量[MJ/h]"] ))
        resultJson["ventilation"][roomID]["設計値[MJ/m2]"] = resultJson["ventilation"][roomID]["設計値[MJ]"] / inputdata["Rooms"][roomID]["roomArea"]
        resultJson["ventilation"][roomID]["設計値/基準値"] = resultJson["ventilation"][roomID]["設計値[MJ]"] / resultJson["ventilation"][roomID]["基準値[MJ]"]

        resultJson["設計一次エネルギー消費量[MJ/年]"] += resultJson["ventilation"][roomID]["設計値[MJ]"]
        resultJson["基準一次エネルギー消費量[MJ/年]"] += resultJson["ventilation"][roomID]["基準値[MJ]"]
        resultJson["時刻別設計一次エネルギー消費量[MJ/h]"]  += resultJson["ventilation"][roomID]["時刻別設計一次エネルギー消費量[MJ/h]"]


    resultJson["設計一次エネルギー消費量[GJ/年]"] = resultJson["設計一次エネルギー消費量[MJ/年]"] / 1000
    resultJson["基準一次エネルギー消費量[GJ/年]"] = resultJson["基準一次エネルギー消費量[MJ/年]"] / 1000
    resultJson["設計一次エネルギー消費量[MJ/m2年]"] = resultJson["設計一次エネルギー消費量[MJ/年]"] / resultJson["計算対象面積"]
    resultJson["基準一次エネルギー消費量[MJ/m2年]"] = resultJson["基準一次エネルギー消費量[MJ/年]"] / resultJson["計算対象面積"]

    # BEI/V [-]
    if resultJson["基準一次エネルギー消費量[MJ/年]"] <= 0:
        resultJson["BEI/V"]  = None
    else:
        resultJson["BEI/V"]  = resultJson["設計一次エネルギー消費量[MJ/年]"] / resultJson["基準一次エネルギー消費量[MJ/年]"]
        resultJson["BEI/V"] = math.ceil(resultJson["BEI/V"] * 100)/100


    # コジェネ用の結果の格納 [MJ → MWh]
    for day in range(0,365):
        resultJson["for_CGS"]["Edesign_MWh_day"][day] = np.sum(resultJson["時刻別設計一次エネルギー消費量[MJ/h]"][day]) / (bc.fprime) 


    ##----------------------------------------------------------------------------------
    # 不要な要素を削除
    ##----------------------------------------------------------------------------------

    del resultJson["時刻別設計一次エネルギー消費量[MJ/h]"]

    for roomID, isys in inputdata["VentilationRoom"].items():
        del resultJson["ventilation"][roomID]["opeTime_hourly"]
        del resultJson["ventilation"][roomID]["時刻別設計一次エネルギー消費量[MJ/h]"]


    return resultJson


if __name__ == '__main__':

    print('----- ventilation.py -----')
    filename = './sample/WEBPRO_inputSheet_sample.json'

    # テンプレートjsonの読み込み
    with open(filename, 'r', encoding='utf-8') as f:
        inputdata = json.load(f)

    resultJson = calc_energy(inputdata, DEBUG = False)

    with open("resultJson_V.json",'w', encoding='utf-8') as fw:
        json.dump(resultJson, fw, indent=4, ensure_ascii=False, cls = bc.MyEncoder)
    
    print( f'設計一次エネルギー消費量[MJ] {resultJson["設計一次エネルギー消費量[MJ/年]"]}')
    print( f'基準一次エネルギー消費量[MJ] {resultJson["基準一次エネルギー消費量[MJ/年]"]}')