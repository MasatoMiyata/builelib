import json
import numpy as np
import os
import math
import pandas as pd
import copy

import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import commons as bc

# データベースファイルの保存場所
database_directory =  os.path.dirname(os.path.abspath(__file__)) + "/database/"

# 室使用条件データの読み込み
with open(database_directory + 'RoomUsageSchedule.json', 'r', encoding='utf-8') as f:
    _RoomUsageSchedule = json.load(f)

# カレンダーパターンの読み込み
with open(database_directory + 'CALENDAR.json', 'r', encoding='utf-8') as f:
    _Calendar = json.load(f)



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


def calc_energy(inputdata, DEBUG = False, output_dir = ""):

    ## 標準室使用条件の読み込み＋更新
    RoomUsageSchedule = copy.deepcopy(_RoomUsageSchedule)
    if "room_usage_condition" in inputdata["SpecialInputData"]:
        for buildling_type in inputdata["SpecialInputData"]["room_usage_condition"]:
            for room_type in inputdata["SpecialInputData"]["room_usage_condition"][buildling_type]:
                RoomUsageSchedule[buildling_type][room_type] = inputdata["SpecialInputData"]["room_usage_condition"][buildling_type][room_type]

    ## カレンダーパターンの読み込み＋更新
    Calendar = copy.deepcopy(_Calendar)
    if "calender" in inputdata["SpecialInputData"]:
        for pattern_name in inputdata["SpecialInputData"]["calender"]:
            # データベースに追加
            Calendar[pattern_name] = inputdata["SpecialInputData"]["calender"][pattern_name]

    # 一次エネルギー換算係数
    fprime = 9760
    if "CalculationMode" in inputdata:
        if isinstance(inputdata["CalculationMode"]["一次エネルギー換算係数"], (int, float)):
            fprime = inputdata["CalculationMode"]["一次エネルギー換算係数"]

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
    E_lighting = 0    # 設計一次エネルギー消費量 [MJ]
    E_lighting_hourly = np.zeros((365,24))  # 設計一次エネルギー消費量（時刻別） [MJ]
    Es_lighting = 0   # 基準一次エネルギー消費量 [MJ]
    total_area = 0    # 建物全体の床面積

    # 基準値
    if "SpecialInputData" in inputdata:
        RoomStandardValue = bc.get_standard_value(inputdata["SpecialInputData"])
    else:
        RoomStandardValue = bc.get_standard_value({})


    # 室毎（照明系統毎）のループ
    for room_zone_name in inputdata["LightingSystems"]:

        # 建物用途、室用途、室面積の取得
        buildingType = inputdata["Rooms"][room_zone_name]["buildingType"]
        roomType     = inputdata["Rooms"][room_zone_name]["roomType"]
        roomArea     = inputdata["Rooms"][room_zone_name]["roomArea"]

        # 時刻別スケジュールの読み込み
        opePattern_hourly_light = bc.get_operation_schedule_lighting(buildingType, roomType, Calendar, RoomUsageSchedule)        
        opeTime = np.sum( np.sum(opePattern_hourly_light))


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
        E_room_hourly = opePattern_hourly_light * unitPower * roomIndexCoeff * fprime * 10**(-6)

        # 各室の年間エネルギー消費量 [MJ]
        E_room = E_room_hourly.sum()

        # 出力用に積算
        E_lighting += E_room  
        E_lighting_hourly += E_room_hourly

        total_area += roomArea

        # 床面積あたりの照明器具消費電力[W/m2]と設計一次エネルギー消費量 [MJ/m2]
        if roomArea <= 0:
            PrimaryEnergyPerArea = None
            unitPower_per_area = None
        else:
            PrimaryEnergyPerArea = E_room / roomArea
            unitPower_per_area   = unitPower / roomArea


        # 基準一次エネルギー消費量 [MJ]
        Es_room = RoomStandardValue[buildingType][roomType]["照明"] * roomArea
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
                "unitPowerPerArea": unitPower_per_area,
                "primaryEnergy": E_room,
                "standardEnergy": Es_room,
                "primaryEnergyPerArea": PrimaryEnergyPerArea,
                "energyRatio": E_room / Es_room
            }

        if DEBUG:
            print( f'室名称　{room_zone_name}')
            print( f'　- 設計一次エネルギー消費量  {E_room} MJ')
            print( f'　- 基準一次エネルギー消費量  {Es_room} MJ')
    

    # 基準値の任意入力
    if "SpecialInputData" in inputdata:
        if "reference_energy" in inputdata["SpecialInputData"]:
            if "照明[MJ/年]" in inputdata["SpecialInputData"]["reference_energy"]:
                if inputdata["SpecialInputData"]["reference_energy"]["照明[MJ/年]"] != "":
                    reference_value = float(inputdata["SpecialInputData"]["reference_energy"]["照明[MJ/年]"])
                    if reference_value <= 0:
                        raise Exception('入力された基準一次エネルギー消費量が不正です。')
                    else:
                        Es_lighting = reference_value

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
    resultJson["for_CGS"]["Edesign_MWh_day"] = np.sum(E_lighting_hourly/fprime,1)

    # エネルギー消費量の比率
    for room_zone_name in  resultJson["lighting"]:
        resultJson["lighting"][room_zone_name]["primaryEnergyRario"] = \
            resultJson["lighting"][room_zone_name]["primaryEnergy"] / resultJson["E_lighting"]


    ##----------------------------------------------------------------------------------
    # CSV出力
    ##----------------------------------------------------------------------------------
    if output_dir != "":
        output_dir = output_dir + "_"

    # 日別一次エネルギー消費量
    df_daily_energy = pd.DataFrame({
        '一次エネルギー消費量（照明設備）[GJ]'  : resultJson["for_CGS"]["Edesign_MWh_day"] *  (fprime) /1000,
        '電力消費量（照明設備）[MWh]'  : resultJson["for_CGS"]["Edesign_MWh_day"],
    }, index=bc.date_1year)

    df_daily_energy.to_csv(output_dir + 'result_L_Energy_daily.csv', index_label="日時", encoding='CP932')

    # 室毎の計算結果
    df_room_result = pd.DataFrame.from_dict(resultJson["lighting"], orient='index')

    rename_columns = {
        "buildingType": "建物用途",
        "roomType": "室用途",
        "roomArea": "室面積",
        "opelationTime": "年間点灯時間",
        "roomIndex": "室指数",
        "roomIndexCoeff": "室指数補正係数",
        "unitPower": "定格消費電力[W]",
        "unitPowerPerArea": "床面積あたりの定格消費電力[W/m2]",
        "primaryEnergy": "設計一次エネルギー消費量[MJ]",
        "standardEnergy": "基準一次エネルギー消費量[MJ]",
        "primaryEnergyPerArea": "床面積あたりの設計値[MJ/m2]",
        "energyRatio": "設計値/基準値",
        "primaryEnergyRario": "設計値の比率[-]"
    }

    df_room_result = df_room_result.rename(columns=rename_columns)
    df_room_result.to_csv(output_dir + 'result_L_room.csv', index_label="室名", encoding='CP932')

    return resultJson


if __name__ == '__main__':

    # 現在のスクリプトファイルのディレクトリを取得
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 1つ上の階層のディレクトリパスを取得
    parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))

    print('----- lighting.py -----')
    filename = parent_dir + '/sample/Baguio_Ayala_Land_Technohub_BPO-B_001_ベースモデル.json'

    # テンプレートjsonの読み込み
    with open(filename, 'r', encoding='utf-8') as f:
        inputdata = json.load(f)

    resultJson = calc_energy(inputdata, DEBUG = False)

    with open("resultJson_L.json",'w', encoding='utf-8') as fw:
        json.dump(resultJson, fw, indent=4, ensure_ascii=False, cls = bc.MyEncoder)

    print(f'設計一次エネルギー消費量[MJ]: {resultJson["E_lighting"]}')
    print(f'基準一次エネルギー消費量[MJ]: {resultJson["Es_lighting"]}')