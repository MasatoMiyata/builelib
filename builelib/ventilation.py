import json
import numpy as np
import os

import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import commons as bc

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

## 中間期平均外気温（附属書B.1）
def set_OutdoorTemperature(region):
    if region == "1":
        Toa_ave_design = 22.7
    elif region == "2":
        Toa_ave_design = 22.5
    elif region == "3":
        Toa_ave_design = 24.7
    elif region == "4":
        Toa_ave_design = 27.1
    elif region == "5":
        Toa_ave_design = 26.7
    elif region == "6":
        Toa_ave_design = 27.5
    elif region == "7":
        Toa_ave_design = 25.8
    elif region == "8":
        Toa_ave_design = 26.2
    else:
        raise Exception('Error!')

    return Toa_ave_design


def calc_energy(inputdata, DEBUG = False):
    
    # 計算結果を格納する変数
    resultJson = {
        "E_ventilation": 0,  # 設計一次エネルギー消費量 [GJ]
        "Es_ventilation": 0, # 基準一次エネルギー消費量 [GJ]
        "BEI_V": 0,
        "ventilation":{   
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

        ##----------------------------------------------------------------------------------
        ## 年間換気運転時間 （解説書 B.2）
        ##----------------------------------------------------------------------------------
        inputdata["VentilationRoom"][roomID]["opeTime"] = bc.RoomUsageSchedule[buildingType][roomType]["年間換気時間"]

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
            else:
                inputdata["VentilationUnit"][unitID]["opeTimeList"] = [inputdata["VentilationRoom"][roomID]["opeTime"]]

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
            print( f'室名称　{roomID}')
            print( f'　- 換気代替空調の有無 {inputdata["VentilationRoom"][roomID]["isVentilationUsingAC"]}')
            print( f'　- 換換気代替空調系統の熱源容量の合計容量 {inputdata["VentilationRoom"][roomID]["AC_CoolingCapacity_total"]}')
            print( f'　- 換気代替空調系統の給気風量の合計容量 {inputdata["VentilationRoom"][roomID]["totalAirVolume_supply"]}')
            print( f'　- 換気代替空調系統の排気風量の合計容量 {inputdata["VentilationRoom"][roomID]["totalAirVolume_exhaust"]}')

    if DEBUG:
        for unitID, iunit in inputdata["VentilationUnit"].items():
            print( f'換気名称　{unitID}')
            print( f'　- 室リスト {inputdata["VentilationUnit"][unitID]["roomList"]}')
            print( f'　- 床面積リスト {inputdata["VentilationUnit"][unitID]["roomAreaList"]}')
            print( f'　- 運転時間リスト {inputdata["VentilationUnit"][unitID]["opeTimeList"]}')
            print( f'　- 換気代替空調機の有無 {inputdata["VentilationUnit"][unitID]["isVentilationUsingAC"]}')


    ##----------------------------------------------------------------------------------
    ## 送風機の制御方式に応じて定められる係数（解説書 3.2）
    ##----------------------------------------------------------------------------------
    with open( database_directory + '/ventilationControl.json', 'r') as f:
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
        inputdata["VentilationUnit"][unitID]["maxopeTime"] = max( iunit["opeTimeList"] )

        # 換気代替空調機と換気送風機が混在していないかをチェック　→　混在していたらエラー
        if not all(iunit["isVentilationUsingAC"]) and any(iunit["isVentilationUsingAC"]):
            raise Exception('Error!')


    # 再度、室毎（換気系統毎）のループ
    for roomID, isys in inputdata["VentilationRoom"].items():

        # 各室の計算結果を格納
        resultJson["ventilation"][roomID] = {
                "PrimaryEnergy": 0,
                "StandardEnergy": 0
        }

        ##----------------------------------------------------------------------------------
        ## 換気代替空調機の年間電力消費量（解説書 3.4）
        ##----------------------------------------------------------------------------------
        if isys["isVentilationUsingAC"]:  ## 換気代替空調機の場合（仕様書 3.4）

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
                print( f'室名称　{roomID}')
                print( f'　- 外気取り込み量 {OutdoorVolume}')
                print( f'　- 外気冷房に必要な外気導入量 {requiredOAVolume}')
                print( f'　- 年間稼働率 Cac {Cac}')
                print( f'　- 年間稼働率 Cfan {Cfan}')


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
                            raise Exception('Error!')

                        resultJson["ventilation"][roomID]["PrimaryEnergy"] += \
                            ( inputdata["VentilationUnit"][unitID]["AC_CoolingCapacity"] * xL / (2.71 * inputdata["VentilationUnit"][unitID]["AC_RefEfficiency"] )  \
                            + inputdata["VentilationUnit"][unitID]["AC_PumpPower"] /0.75 ) \
                            * inputdata["VentilationUnit"][unitID]["maxopeTime"] * bc.fprime * 10**(-3) * Cac

                    # 空調機に付属するファン
                    resultJson["ventilation"][roomID]["PrimaryEnergy"] += \
                        inputdata["VentilationUnit"][unitID]["Energy_kW"]  \
                        * inputdata["VentilationRoom"][roomID]["roomArea"] / inputdata["VentilationUnit"][unitID]["roomAreaTotal"] \
                        * inputdata["VentilationUnit"][unitID]["maxopeTime"] * bc.fprime * 10**(-3) * Cac

                    print(inputdata["VentilationUnit"][unitID]["Energy_kW"])

                else: ## 換気代替空調機と併設される送風機

                    resultJson["ventilation"][roomID]["PrimaryEnergy"] += \
                        inputdata["VentilationUnit"][unitID]["Energy_kW"]  \
                        * inputdata["VentilationRoom"][roomID]["roomArea"] / inputdata["VentilationUnit"][unitID]["roomAreaTotal"] \
                        * inputdata["VentilationUnit"][unitID]["maxopeTime"] * bc.fprime * 10**(-3) * Cfan


                if DEBUG:
                    print( f'室名称 {roomID}, 機器名称 {unitID}')
                    print( f'　- 運転時間 {inputdata["VentilationUnit"][unitID]["maxopeTime"] }')
                    print( f'　- 消費電力[W/m2] {inputdata["VentilationUnit"][unitID]["Energy_kW"]/inputdata["VentilationRoom"][roomID]["roomArea"]*1000}')


        else: ## 換気送風機の場合（仕様書 3.3）

            for unitID, iunit in inputdata["VentilationRoom"][roomID]["VentilationUnitRef"].items():
                
                # エネルギー消費量 [kW * hour * m2/m2 * kJ/KWh]
                resultJson["ventilation"][roomID]["PrimaryEnergy"] += inputdata["VentilationUnit"][unitID]["Energy_kW"]  \
                    * inputdata["VentilationRoom"][roomID]["roomArea"] / inputdata["VentilationUnit"][unitID]["roomAreaTotal"] \
                    * inputdata["VentilationUnit"][unitID]["maxopeTime"] * bc.fprime * 10**(-3)


    ##----------------------------------------------------------------------------------
    ## 基準一次エネルギー消費量 [MJ] （解説書 10）
    ##----------------------------------------------------------------------------------
    for roomID, isys in inputdata["VentilationRoom"].items():

        # 建物用途、室用途（可読性重視で一旦変数に代入する）
        buildingType = inputdata["Rooms"][roomID]["buildingType"]
        roomType     = inputdata["Rooms"][roomID]["roomType"]
    
        resultJson["ventilation"][roomID]["StandardEnergy"] = \
            bc.RoomStandardValue[buildingType][roomType]["換気"] * inputdata["Rooms"][roomID]["roomArea"]


    # 結果の集計
    for roomID, isys in inputdata["VentilationRoom"].items():
        resultJson["E_ventilation"]  += resultJson["ventilation"][roomID]["PrimaryEnergy"]
        resultJson["Es_ventilation"] += resultJson["ventilation"][roomID]["StandardEnergy"]



    # BEI/V [-]
    if resultJson["Es_ventilation"] <= 0:
        resultJson["BEI_V"]  = None
    else:
        resultJson["BEI_V"]  = resultJson["E_ventilation"] / resultJson["Es_ventilation"]

    if DEBUG:
        with open("resultJson_V.json",'w') as fw:
            json.dump(resultJson, fw, indent=4, ensure_ascii=False, cls = MyEncoder)

        print( f'設計一次エネルギー消費量[MJ] {resultJson["E_ventilation"]}')
        print( f'基準一次エネルギー消費量[MJ] {resultJson["Es_ventilation"]}')


    return resultJson


if __name__ == '__main__':

    print('----- ventilation.py -----')
    filename = './sample/sample01_WEBPRO_inputSheet_for_Ver2.5.json'

    # テンプレートjsonの読み込み
    with open(filename, 'r') as f:
        inputdata = json.load(f)

    resultJson = calc_energy(inputdata, DEBUG = True)
    print(resultJson)