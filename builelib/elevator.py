import json
import numpy as np
import os
import math
import pandas as pd

import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import commons as bc


def calc_energy(inputdata, DEBUG = False, output_dir = ""):

    # 一次エネルギー換算係数
    fprime = 9760
    if "CalculationMode" in inputdata:
        if isinstance(inputdata["CalculationMode"]["一次エネルギー換算係数"], (int, float)):
            fprime = inputdata["CalculationMode"]["一次エネルギー換算係数"]

    #----------------------------------------------------------------------------------
    # 計算結果を格納する変数
    #----------------------------------------------------------------------------------
    resultJson = {
        "E_elevator": 0,
        "Es_elevator": 0,
        "BEI_EV": 0,
        "Elevators": {},
        "for_CGS":{
            "Edesign_MWh_day": np.zeros(365)
        }
    }

    #----------------------------------------------------------------------------------
    # 解説書 6.2 速度制御方式に応じて定められる係数
    #----------------------------------------------------------------------------------

    for room_name in inputdata["Elevators"]:
        for unit_id, unit_configure in enumerate(inputdata["Elevators"][room_name]["Elevator"]):
            
            if unit_configure["ControlType"] ==  "交流帰還制御":
                inputdata["Elevators"][room_name]["Elevator"][unit_id]["ControlTypeCoefficient"] = 1/20

            elif unit_configure["ControlType"] ==  "VVVF(電力回生なし)" or unit_configure["ControlType"] ==  "VVVF（電力回生なし）":
                inputdata["Elevators"][room_name]["Elevator"][unit_id]["ControlTypeCoefficient"] = 1/40

            elif unit_configure["ControlType"] ==  "VVVF(電力回生あり)" or unit_configure["ControlType"] ==  "VVVF（電力回生あり）":
                inputdata["Elevators"][room_name]["Elevator"][unit_id]["ControlTypeCoefficient"] = 1/45

            elif unit_configure["ControlType"] ==  "VVVF(電力回生なし、ギアレス)" or unit_configure["ControlType"] ==  "VVVF（電力回生なし、ギアレス）":
                inputdata["Elevators"][room_name]["Elevator"][unit_id]["ControlTypeCoefficient"] = 1/45

            elif unit_configure["ControlType"] ==  "VVVF(電力回生あり、ギアレス)" or unit_configure["ControlType"] ==  "VVVF（電力回生あり、ギアレス）":
                inputdata["Elevators"][room_name]["Elevator"][unit_id]["ControlTypeCoefficient"] = 1/50
            
            else:
                raise Exception("速度制御方式 が不正です。")

    #----------------------------------------------------------------------------------
    # 解説書 6.3 昇降機系統に属する昇降機1台あたりの年間電力消費量
    #----------------------------------------------------------------------------------

    for room_name in inputdata["Elevators"]:

        # 建物用途、室用途、室面積の取得
        buildingType = inputdata["Rooms"][room_name]["buildingType"]
        roomType     = inputdata["Rooms"][room_name]["roomType"]

        # 年間照明点灯時間 [時間] 
        if buildingType == "共同住宅":
            inputdata["Elevators"][room_name]["operation_time"] = 5480
            inputdata["Elevators"][room_name]["operation_schedule_hourly"] = 5480/8760 * np.ones((365,24))
        else:

            if "SpecialInputData" in inputdata:
                inputdata["Elevators"][room_name]["operation_schedule_hourly"] = bc.get_operation_schedule_lighting(buildingType, roomType, inputdata["SpecialInputData"])
            else:
                inputdata["Elevators"][room_name]["operation_schedule_hourly"] = bc.get_operation_schedule_lighting(buildingType, roomType)

            inputdata["Elevators"][room_name]["operation_time"] = np.sum( np.sum(inputdata["Elevators"][room_name]["operation_schedule_hourly"]))


        if DEBUG:
            print(f'室 {room_name} に設置された昇降機')
            print(f'  - 昇降機運転時間 {inputdata["Elevators"][room_name]["operation_time"]}')


    # エネルギー消費量計算 [kWh/年]
    Edesign_MWh_hour = np.zeros((365,24))
    for room_name in inputdata["Elevators"]:
        for unit_id, unit_configure in enumerate(inputdata["Elevators"][room_name]["Elevator"]):

            inputdata["Elevators"][room_name]["Elevator"][unit_id]["energy_consumption"] = \
                unit_configure["Number"] * \
                unit_configure["Velocity"] * unit_configure["LoadLimit"] * unit_configure["ControlTypeCoefficient"] * \
                inputdata["Elevators"][room_name]["operation_time"] / 860 

            if DEBUG:
                print(f'室 {room_name} に設置された {unit_id+1} 台目の昇降機')
                print(f'　- 台数  {unit_configure["Number"]}')
                print(f'　- 速度  {unit_configure["Velocity"]}')
                print(f'　- 積載量  {unit_configure["LoadLimit"]}')
                print(f'　- 速度制御方式による係数  {unit_configure["ControlTypeCoefficient"]}')
                print(f'　- エネルギー消費量 kWh/年 {inputdata["Elevators"][room_name]["Elevator"][unit_id]["energy_consumption"]}')

            # 時刻別エネルギー消費量 [MWh]
            Edesign_MWh_hour += \
                unit_configure["Number"] * \
                unit_configure["Velocity"] * unit_configure["LoadLimit"] * unit_configure["ControlTypeCoefficient"] * \
                inputdata["Elevators"][room_name]["operation_schedule_hourly"] / 860 /1000


    #----------------------------------------------------------------------------------
    # 解説書 6.4 昇降機の設計一次エネルギー消費量
    #----------------------------------------------------------------------------------

    # 設計一次エネルギー消費量計算 [MJ/年]
    for room_name in inputdata["Elevators"]:
        for unit_id, unit_configure in enumerate(inputdata["Elevators"][room_name]["Elevator"]):

            resultJson["E_elevator"] += unit_configure["energy_consumption"] * fprime / 1000

    if DEBUG:
        print(f'昇降機の設計一次エネルギー消費量  {resultJson["E_elevator"]}  MJ/年')


    #----------------------------------------------------------------------------------
    # 解説書 10.5 昇降機の基準一次エネルギー消費量
    #----------------------------------------------------------------------------------

    # エネルギー消費量計算 [kWh/年]
    for room_name in inputdata["Elevators"]:
        for unit_id, unit_configure in enumerate(inputdata["Elevators"][room_name]["Elevator"]):

            inputdata["Elevators"][room_name]["Elevator"][unit_id]["Es"] = \
                unit_configure["Number"] * \
                unit_configure["Velocity"] * unit_configure["LoadLimit"] * (1/40) * \
                unit_configure["TransportCapacityFactor"] * \
                inputdata["Elevators"][room_name]["operation_time"] / 860 

            inputdata["Elevators"][room_name]["Elevator"][unit_id]["energyRatio"] = \
                inputdata["Elevators"][room_name]["Elevator"][unit_id]["energy_consumption"] / inputdata["Elevators"][room_name]["Elevator"][unit_id]["Es"]

            # 基準一次エネルギー消費量計算 [MJ/年]
            resultJson["Es_elevator"] += inputdata["Elevators"][room_name]["Elevator"][unit_id]["Es"] * fprime / 1000

    if DEBUG:
        print(f'昇降機の基準一次エネルギー消費量  {resultJson["Es_elevator"]}  MJ/年')


    # 単位変換
    resultJson["E_elevator_GJ"]  = resultJson["E_elevator"] /1000
    resultJson["Es_elevator_GJ"] = resultJson["Es_elevator"] /1000

    # 入力データも出力
    resultJson["Elevators"] = inputdata["Elevators"]

    # BEI/EVの計算
    if resultJson["Es_elevator"] != 0:
        resultJson["BEI_EV"] = resultJson["E_elevator"] / resultJson["Es_elevator"]
        resultJson["BEI_EV"] = math.ceil(resultJson["BEI_EV"] * 100)/100
    else:
        resultJson["BEI_EV"] = np.nan

    # 日積算値
    resultJson["for_CGS"]["Edesign_MWh_day"] = np.sum(Edesign_MWh_hour,1)


    ##----------------------------------------------------------------------------------
    # CSV出力
    ##----------------------------------------------------------------------------------
    if output_dir != "":
        output_dir = output_dir + "_"

    df_daily_energy = pd.DataFrame({
        '一次エネルギー消費量（昇降機）[GJ]'  : resultJson["for_CGS"]["Edesign_MWh_day"] *  (fprime) /1000,
        '電力消費量（昇降機）[MWh]'  : resultJson["for_CGS"]["Edesign_MWh_day"],
    }, index=bc.date_1year)

    df_daily_energy.to_csv(output_dir + 'result_EV_Energy_daily.csv', index_label="日時", encoding='CP932')


    return resultJson


if __name__ == '__main__':

    # 現在のスクリプトファイルのディレクトリを取得
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 1つ上の階層のディレクトリパスを取得
    parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))


    print('----- elevator.py -----')
    filename = parent_dir + '/sample/Baguio_Ayala_Land_Technohub_BPO-B_001_ベースモデル.json'

    # 入力ファイルの読み込み
    with open(filename, 'r', encoding='utf-8') as f:
        inputdata = json.load(f)

    resultJson = calc_energy(inputdata, DEBUG = True)

    with open("resultJson_EV.json",'w', encoding='utf-8') as fw:
        json.dump(resultJson, fw, indent=4, ensure_ascii=False, cls = bc.MyEncoder)

