import json
import numpy as np
import os
import math

import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import commons as bc

# データベースファイルの保存場所
database_directory =  os.path.dirname(os.path.abspath(__file__)) + "/database/"


def set_roomIndexCoeff(roomIndex):
    '''
    室の形状に応じて定められる係数（仕様書4.4）
    '''

    if (roomIndex == "") or (roomIndex == None):
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
    with open( database_directory + 'lightingControl.json', 'r', encoding='utf-8') as f:
        lightingCtrl = json.load(f)

    # 計算結果を格納する変数
    resultJson = {
        "E_lighting": None,
        "Es_lighting": None,
        "BEI_L": None,
        "E_lighting_hourly": None,
        "lighting":{
        },
        "for_CGS":{
            "Edesign_MWh_day": np.zeros(365)
        }
    }

    # 変数初期化
    E_lighting = 0    # 設計一次エネルギー消費量 [GJ]
    E_lighting_hourly = np.zeros((365,24))  # 設計一次エネルギー消費量（時刻別） [GJ]
    Es_lighting = 0   # 基準一次エネルギー消費量 [GJ]
    total_area = 0    # 建物全体の床面積

    ##----------------------------------------------------------------------------------
    ## 任意評定 （SP-6: カレンダーパターン)
    ##----------------------------------------------------------------------------------
    input_calendar = []
    if "calender" in inputdata["SpecialInputData"]:
        input_calendar = inputdata["SpecialInputData"]["calender"]

        
    # 室毎（照明系統毎）のループ
    for room_zone_name in inputdata["LightingSystems"]:

        # 建物用途、室用途、室面積の取得
        buildingType = inputdata["Rooms"][room_zone_name]["buildingType"]
        roomType     = inputdata["Rooms"][room_zone_name]["roomType"]
        roomArea     = inputdata["Rooms"][room_zone_name]["roomArea"]

        # 年間照明点灯時間 [時間] ← 計算には使用しない。
        # opeTime = bc.RoomUsageSchedule[buildingType][roomType]["年間照明点灯時間"]

        # 時刻別スケジュールの読み込み
        opePattern_hourly_light = bc.get_dailyOpeSchedule_lighting(buildingType, roomType, input_calendar)
        opeTime = np.sum( np.sum(opePattern_hourly_light))


        ##----------------------------------------------------------------------------------
        ## 任意評定 （SP-7: 室スケジュール)
        ##----------------------------------------------------------------------------------

        if "room_schedule" in inputdata["SpecialInputData"]:

            # SP-7に入力されていれば
            if room_zone_name in inputdata["SpecialInputData"]["room_schedule"]:

                if "照明発熱密度比率" in inputdata["SpecialInputData"]["room_schedule"][room_zone_name]["schedule"]:
                    opePattern_hourly_light = np.array(inputdata["SpecialInputData"]["room_schedule"][room_zone_name]["schedule"]["照明発熱密度比率"])
                    
                    # SP-7の場合は、発熱比率をそのまま使用することにする。
                    # opePattern_hourly_light = np.where(opePattern_hourly_light > 0, 1, 0)


        ## 室の形状に応じて定められる係数（仕様書4.4）
        # 室指数
        if inputdata["LightingSystems"][room_zone_name]["roomIndex"] != None:
            roomIndex = inputdata["LightingSystems"][room_zone_name]["roomIndex"]
        elif inputdata["LightingSystems"][room_zone_name]["roomWidth"] != None and inputdata["LightingSystems"][room_zone_name]["roomDepth"] != None and inputdata["LightingSystems"][room_zone_name]["unitHeight"] != None:
            if inputdata["LightingSystems"][room_zone_name]["roomWidth"] > 0 and inputdata["LightingSystems"][room_zone_name]["roomDepth"] > 0 and inputdata["LightingSystems"][room_zone_name]["unitHeight"] > 0:
                roomIndex = (inputdata["LightingSystems"][room_zone_name]["roomWidth"] * inputdata["LightingSystems"][room_zone_name]["roomDepth"]) / ( (inputdata["LightingSystems"][room_zone_name]["roomWidth"] + inputdata["LightingSystems"][room_zone_name]["roomDepth"]) * inputdata["LightingSystems"][room_zone_name]["unitHeight"] )
            else:
                roomIndex = None
        else:
            roomIndex = None
        
        # 補正係数
        roomIndexCoeff = set_roomIndexCoeff(roomIndex)


        ## 器具毎のループ
        unitPower = 0
        for unit_name in inputdata["LightingSystems"][room_zone_name]["lightingUnit"]:

            # 在室検知制御方式の効果係数
            ctrl_occupant_sensing = 1
            if inputdata["LightingSystems"][room_zone_name]["lightingUnit"][unit_name]["OccupantSensingCTRL"] in lightingCtrl["OccupantSensingCTRL"]:
                # データベースから検索して効果係数を決定
                ctrl_occupant_sensing = lightingCtrl["OccupantSensingCTRL"][ inputdata["LightingSystems"][room_zone_name]["lightingUnit"][unit_name]["OccupantSensingCTRL"] ]
            else:
                # 直接入力された効果係数を使用
                ctrl_occupant_sensing = float( inputdata["LightingSystems"][room_zone_name]["lightingUnit"][unit_name]["OccupantSensingCTRL"] )


            # 明るさ検知制御方式の効果係数
            ctrl_illuminance_sensing = 1
            if inputdata["LightingSystems"][room_zone_name]["lightingUnit"][unit_name]["IlluminanceSensingCTRL"] in lightingCtrl["IlluminanceSensingCTRL"]:
                # データベースから検索して効果係数を決定
                ctrl_illuminance_sensing = lightingCtrl["IlluminanceSensingCTRL"][ inputdata["LightingSystems"][room_zone_name]["lightingUnit"][unit_name]["IlluminanceSensingCTRL"] ]
            else:
                # 直接入力された効果係数を使用
                ctrl_illuminance_sensing = float( inputdata["LightingSystems"][room_zone_name]["lightingUnit"][unit_name]["IlluminanceSensingCTRL"] )


            # タイムスケジュール制御方式の効果係数
            ctrl_time_schedule = 1
            if inputdata["LightingSystems"][room_zone_name]["lightingUnit"][unit_name]["TimeScheduleCTRL"] in lightingCtrl["TimeScheduleCTRL"]:
                # データベースから検索して効果係数を決定
                ctrl_time_schedule = lightingCtrl["TimeScheduleCTRL"][ inputdata["LightingSystems"][room_zone_name]["lightingUnit"][unit_name]["TimeScheduleCTRL"] ]
            else:
                # 直接入力された効果係数を使用
                ctrl_time_schedule = float( inputdata["LightingSystems"][room_zone_name]["lightingUnit"][unit_name]["TimeScheduleCTRL"] )


            # 初期照度補正の効果係数
            initial_illumination_correction = 1
            if inputdata["LightingSystems"][room_zone_name]["lightingUnit"][unit_name]["InitialIlluminationCorrectionCTRL"] in lightingCtrl["InitialIlluminationCorrectionCTRL"]:
                # データベースから検索して効果係数を決定
                initial_illumination_correction = lightingCtrl["InitialIlluminationCorrectionCTRL"][ inputdata["LightingSystems"][room_zone_name]["lightingUnit"][unit_name]["InitialIlluminationCorrectionCTRL"] ]
            else:
                # 直接入力された効果係数を使用
                initial_illumination_correction = float( inputdata["LightingSystems"][room_zone_name]["lightingUnit"][unit_name]["InitialIlluminationCorrectionCTRL"] )


            # 照明器具の消費電力（制御込み） [W]
            unitPower += inputdata["LightingSystems"][room_zone_name]["lightingUnit"][unit_name]["RatedPower"]  \
                            * inputdata["LightingSystems"][room_zone_name]["lightingUnit"][unit_name]["Number"] \
                            * ctrl_occupant_sensing * ctrl_illuminance_sensing * ctrl_time_schedule * initial_illumination_correction


        # 時刻別の設計一次エネルギー消費量 [MJ]
        E_room_hourly = opePattern_hourly_light * unitPower * roomIndexCoeff * bc.fprime * 10**(-6)

        # 各室の年間エネルギー消費量 [MJ]
        E_room = E_room_hourly.sum()

        # 出力用に積算
        E_lighting += E_room  
        E_lighting_hourly += E_room_hourly

        total_area += roomArea

        # 床面積あたりの設計一次エネルギー消費量 [MJ/m2]
        if roomArea <= 0:
            PrimaryEnergyPerArea = None
        else:
            PrimaryEnergyPerArea = E_room / roomArea


        # 基準一次エネルギー消費量 [MJ]
        Es_room = bc.RoomStandardValue[buildingType][roomType]["照明"] * roomArea
        Es_lighting += Es_room  # 出力用に積算


        # 各室の計算結果を格納
        resultJson["lighting"][room_zone_name] = {
                "buildingType": buildingType,
                "roomType": roomType,
                "roomArea": roomArea,
                "opelationTime": opeTime,
                "roomIndex": roomIndex,
                "roomIndexCoeff": roomIndexCoeff,
                "unitPower": unitPower,
                "primaryEnergy": E_room,
                "standardEnergy": Es_room,
                "primaryEnergyPerArea": PrimaryEnergyPerArea,
                "energyRatio": E_room / Es_room
            }

        if DEBUG:
            print( f'室名称　{room_zone_name}')
            print( f'　- 設計一次エネルギー消費量  {E_room} MJ')
            print( f'　- 基準一次エネルギー消費量  {Es_room} MJ')
    
    # BEI/L [-]
    if Es_lighting <= 0:
        BEI_L = None
    else:
        BEI_L = math.ceil( (E_lighting / Es_lighting) * 100)/100
        
    # 建物全体の計算結果
    resultJson["BEI_L"] = BEI_L
    resultJson["total_area"] = total_area
    resultJson["E_lighting"] = E_lighting
    resultJson["E_lighting_GJ"] = E_lighting /1000
    resultJson["E_lighting_MJ_m2"] = E_lighting /total_area
    resultJson["Es_lighting"] = Es_lighting
    resultJson["Es_lighting_GJ"] = Es_lighting /1000
    resultJson["Es_lighting_MJ_m2"] = Es_lighting /total_area
    # resultJson["E_lighting_hourly"] = E_lighting_hourly

    # 日積算値
    resultJson["for_CGS"]["Edesign_MWh_day"] = np.sum(E_lighting_hourly/9760,1)

    return resultJson


if __name__ == '__main__':

    print('----- lighting.py -----')
    filename = './sample/WEBPRO_inputSheet_sample.json'
    # filename = './tests/cogeneration/Case_hotel_00.json'

    # テンプレートjsonの読み込み
    with open(filename, 'r', encoding='utf-8') as f:
        inputdata = json.load(f)

    resultJson = calc_energy(inputdata, DEBUG = False)

    print(f'設計値: {resultJson["E_lighting"]}')
    print(f'基準値: {resultJson["Es_lighting"]}')

    with open("resultJson_L.json",'w', encoding='utf-8') as fw:
        json.dump(resultJson, fw, indent=4, ensure_ascii=False, cls = bc.MyEncoder)
