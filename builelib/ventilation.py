import json
import pprint as pp
import numpy as np

if __name__ == '__main__':
    import builelib_common as bc
else:
    import builelib.builelib_common as bc

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

## 負荷率
def set_HeatLoadRatio(VentilationRoomType):
    if VentilationRoomType == "エレベータ機械室":
        xL = 0.3
    elif VentilationRoomType == "電気室":
        xL = 0.6
    elif VentilationRoomType == "機械室":
        xL = 0.6
    elif VentilationRoomType == "その他":
        xL = 1.0
    else:
        raise Exception('Error!')

    return xL


def ventilation(inputdata):

    # 入力ファイルの検証
    bc.inputdata_validation(inputdata)

    # データベースjsonの読み込み（仕様書 3.2）
    with open('./builelib/database/ventilationControl.json', 'r') as f:
        ventilationCtrl = json.load(f)
    
    # 計算結果を格納する変数
    resultJson = {
        "E_ventilation": None,
        "Es_ventilation": None,
        "BEI_V": None,
        "E_ventilation_hourly": None,
        "ventilation":{   
        }
    }

    # 変数初期化
    E_ventilation = 0    # 設計一次エネルギー消費量 [GJ]
    E_ventilation_hourly = np.zeros((365,24))  # 設計一次エネルギー消費量（時刻別） [GJ]
    Es_ventilation = 0   # 基準一次エネルギー消費量 [GJ]


    # 室毎（換気系統毎）のループ
    for roomID, isys in inputdata["VentilationRoom"].items():

        # 建物用途、室用途（可読性重視で一旦変数に代入する）
        buildingType = inputdata["Rooms"][roomID]["buildingType"]
        roomType     = inputdata["Rooms"][roomID]["roomType"]
        inputdata["VentilationRoom"][roomID]["buildingType"]  = buildingType
        inputdata["VentilationRoom"][roomID]["roomType"]      = roomType

        # 室面積
        inputdata["VentilationRoom"][roomID]["roomArea"] = inputdata["Rooms"][roomID]["roomArea"]

        # 年間換気運転時間 [時間]
        inputdata["VentilationRoom"][roomID]["opeTime"] = bc.RoomUsageSchedule[buildingType][roomType]["年間換気時間"]

        # 接続されている換気機器の種類に応じて集計処理を実行
        inputdata["VentilationRoom"][roomID]["isVentilationUsingAC"] = False
        inputdata["VentilationRoom"][roomID]["totalAirVolume_supply"] = 0
        inputdata["VentilationRoom"][roomID]["totalAirVolume_exhaust"] = 0
        inputdata["VentilationRoom"][roomID]["AC_CoolingCapacity_total"] = 0
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


    # 換気機器毎のループ
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

            # 年間稼働率
            if OutdoorVolume > requiredOAVolume:
                Cac = 0.35
                Cfan = 0.65
            else:
                Cac = 1.00
                Cfan = 1.00               

            E_room = 0
            for unitID, iunit in inputdata["VentilationRoom"][roomID]["VentilationUnitRef"].items():
                
                if iunit["UnitType"] == "空調":  ## 換気代替空調機

                    # 熱源機とポンプ
                    if inputdata["VentilationUnit"][unitID]["VentilationRoomType"] != "":

                        # 負荷率
                        xL = set_HeatLoadRatio( inputdata["VentilationUnit"][unitID]["VentilationRoomType"] )

                        E_room += \
                            ( inputdata["VentilationUnit"][unitID]["AC_CoolingCapacity"] * xL / (2.71 * inputdata["VentilationUnit"][unitID]["AC_RefEfficiency"] )  \
                            + inputdata["VentilationUnit"][unitID]["AC_PumpPower"] /0.75 ) \
                            * inputdata["VentilationUnit"][unitID]["maxopeTime"] * bc.fprime * 10**(-3) * Cac

                    # 空調機に付属するファン
                    E_room += \
                        inputdata["VentilationUnit"][unitID]["Energy_kW"]  \
                        * inputdata["VentilationRoom"][roomID]["roomArea"] / inputdata["VentilationUnit"][unitID]["roomAreaTotal"] \
                        * inputdata["VentilationUnit"][unitID]["maxopeTime"] * bc.fprime * 10**(-3) * Cfan

                else: ## 換気代替空調機と併設される送風機

                    E_room += \
                        inputdata["VentilationUnit"][unitID]["Energy_kW"]  \
                        * inputdata["VentilationRoom"][roomID]["roomArea"] / inputdata["VentilationUnit"][unitID]["roomAreaTotal"] \
                        * inputdata["VentilationUnit"][unitID]["maxopeTime"] * bc.fprime * 10**(-3) * Cfan


        else: ## 換気送風機の場合（仕様書 3.3）

            E_room = 0
            for unitID, iunit in inputdata["VentilationRoom"][roomID]["VentilationUnitRef"].items():
                
                # エネルギー消費量 [kW * hour * m2/m2 * kJ/KWh]
                E_room += inputdata["VentilationUnit"][unitID]["Energy_kW"]  \
                    * inputdata["VentilationRoom"][roomID]["roomArea"] / inputdata["VentilationUnit"][unitID]["roomAreaTotal"] \
                    * inputdata["VentilationUnit"][unitID]["maxopeTime"] * bc.fprime * 10**(-3)

        # 結果を積算
        E_ventilation += E_room
    
        # 基準一次エネルギー消費量 [MJ]
        Es_room = bc.RoomStandardValue[buildingType][roomType]["換気"] * inputdata["VentilationRoom"][roomID]["roomArea"]
        Es_ventilation += Es_room  # 出力用に積算

        # 各室の計算結果を格納
        resultJson["ventilation"][roomID] = {
                "PrimaryEnergy": E_room,
                "StandardEnergy": Es_room
            }

    # 結果の格納
    resultJson["E_ventilation"]  = E_ventilation
    resultJson["Es_ventilation"] = Es_ventilation

    # BEI/V [-]
    if Es_ventilation <= 0:
        resultJson["BEI_V"]  = None
    else:
        resultJson["BEI_V"]  = E_ventilation / Es_ventilation

    # # json出力
    # fw = open('model.json','w')
    # json.dump(inputdata,fw,indent=4,ensure_ascii=False)

    return resultJson


if __name__ == '__main__':

    print('----- ventilation.py -----')
    filename = './sample/inputdata.json'

    # テンプレートjsonの読み込み
    with open(filename, 'r') as f:
        inputdata = json.load(f)

    resultJson = ventilation(inputdata)
    print(resultJson)