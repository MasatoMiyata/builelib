import json
import numpy as np
import os

import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import commons as bc

# データベースファイルの保存場所
database_directory =  os.path.dirname(os.path.abspath(__file__)) + "/database/"


def set_roomIndexCoeff(roomIndex):
    '''
    室の形状に応じて定められる係数（仕様書4.4）
    '''

    if roomIndex == None:
        roomIndexCoeff = 1
    else:
        if roomIndex < 0:
            roomIndexCoeff = 1
        elif roomIndex < 0.75:
            roomIndexCoeff = 0.50
        elif roomIndex < 0.95:
            roomIndexCoeff = 0.60
        elif roomIndex < 1.25:
            roomIndexCoeff = 0.70
        elif roomIndex < 1.75:
            roomIndexCoeff = 0.80
        elif roomIndex < 2.50:
            roomIndexCoeff = 0.90
        elif roomIndex >= 2.50:
            roomIndexCoeff = 1.00
    
    return roomIndexCoeff


def calc_energy(inputdata, DEBUG = False):

    # データベースjsonの読み込み
    with open( database_directory + 'lightingControl.json', 'r') as f:
        lightingCtrl = json.load(f)

    # 計算結果を格納する変数
    resultJson = {
        "E_lighting": None,
        "Es_lighting": None,
        "BEI_L": None,
        "E_lighting_hourly": None,
        "lighting":{
        }
    }

    # 変数初期化
    E_lighting = 0    # 設計一次エネルギー消費量 [GJ]
    E_lighting_hourly = np.zeros((365,24))  # 設計一次エネルギー消費量（時刻別） [GJ]
    Es_lighting = 0   # 基準一次エネルギー消費量 [GJ]


    # 室毎（照明系統毎）のループ
    for ikey, isys in inputdata["LightingSystems"].items():

        # 建物用途、室用途、室面積の取得
        buildingType = inputdata["Rooms"][ikey]["buildingType"]
        roomType     = inputdata["Rooms"][ikey]["roomType"]
        roomArea     = inputdata["Rooms"][ikey]["roomArea"]

        # 年間照明点灯時間 [時間] ← 計算には使用しない。
        opeTime = bc.RoomUsageSchedule[buildingType][roomType]["年間照明点灯時間"]
        # 時刻別スケジュールの読み込み
        opePattern_hourly_light = bc.get_dailyOpeSchedule_lighting(buildingType, roomType)

        ## 室の形状に応じて定められる係数（仕様書4.4）
        # 室指数
        if isys["roomIndex"] != None:
            roomIndex = isys["roomIndex"]
        elif isys["roomWidth"] != None and isys["roomDepth"] != None and isys["unitHeight"] != None:
            if isys["roomWidth"] > 0 and isys["roomDepth"] > 0 and isys["unitHeight"] > 0:
                roomIndex = (isys["roomWidth"] * isys["roomDepth"]) / ( (isys["roomWidth"] + isys["roomDepth"]) * isys["unitHeight"] )
            else:
                roomIndex = None
        else:
            roomIndex = None
        
        # 補正係数
        roomIndexCoeff = set_roomIndexCoeff(roomIndex)

        ## 器具毎のループ
        unitPower = 0
        for _, iunit in isys["lightingUnit"].items():
        
            # 室指数による補正
            rmIx = 1

            # 制御による効果
            ctrl = (
                lightingCtrl["OccupantSensingCTRL"][iunit["OccupantSensingCTRL"]] *
                lightingCtrl["IlluminanceSensingCTRL"][iunit["IlluminanceSensingCTRL"]] *
                lightingCtrl["TimeScheduleCTRL"][iunit["TimeScheduleCTRL"]] *
                lightingCtrl["InitialIlluminationCorrectionCTRL"][iunit["InitialIlluminationCorrectionCTRL"]]
            )

            # 照明器具の消費電力（制御込み） [W]
            unitPower += iunit["RatedPower"] * iunit["Number"] * ctrl


        # 時刻別の設計一次エネルギー消費量 [MJ]
        E_room_hourly = opePattern_hourly_light * unitPower * roomIndexCoeff * bc.fprime * 10**(-6)
    

        # 各室の年間エネルギー消費量 [MJ]
        E_room = E_room_hourly.sum()
        E_lighting_hourly = E_lighting_hourly + E_room_hourly

        E_lighting += E_room  # 出力用に積算

        # 床面積あたりの設計一次エネルギー消費量 [MJ/m2]
        if roomArea <= 0:
            PrimaryEnergyPerArea = None
        else:
            PrimaryEnergyPerArea = E_room / roomArea


        # 基準一次エネルギー消費量 [MJ]
        Es_room = bc.RoomStandardValue[buildingType][roomType]["照明"] * roomArea
        Es_lighting += Es_room  # 出力用に積算


        # 各室の計算結果を格納
        resultJson["lighting"][ikey] = {
                "buildingType": buildingType,
                "roomType": roomType,
                "roomArea": roomArea,
                "opelationTime": opeTime,
                "roomIndex": roomIndex,
                "roomIndexCoeff": roomIndexCoeff,
                "unitPower": unitPower,
                "PrimaryEnergy": E_room,
                "PrimaryEnergyPerArea": PrimaryEnergyPerArea,
                "StandardEnergy": Es_room
            }

        if DEBUG:
            print( f'室名称　{ikey}')
            print( f'　- 設計一次エネルギー消費量  {E_room} MJ')
            print( f'　- 基準一次エネルギー消費量  {Es_room} MJ')
            
    # BEI/L [-]
    if Es_lighting <= 0:
        BEI_L = None
    else:
        BEI_L = E_lighting / Es_lighting
        
    # 建物全体の計算結果
    resultJson["E_lighting"] = E_lighting
    resultJson["Es_lighting"] = Es_lighting
    resultJson["BEI_L"] = BEI_L
    resultJson["E_lighting_hourly"] = E_lighting_hourly

    return resultJson


if __name__ == '__main__':

    print('----- lighting.py -----')
    filename = './sample/sample01_WEBPRO_inputSheet_for_Ver2.5.json'

    # テンプレートjsonの読み込み
    with open(filename, 'r') as f:
        inputdata = json.load(f)

    resultJson = calc_energy(inputdata, DEBUG = True)
    print(resultJson)
