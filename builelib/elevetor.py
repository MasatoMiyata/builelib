import json
import numpy as np
import os

import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import commons as bc


def calc_energy(inputdata, DEBUG = False):


    #----------------------------------------------------------------------------------
    # 計算結果を格納する変数
    #----------------------------------------------------------------------------------
    resultJson = {
        "E_elevetor": 0,
        "Es_elevetor": 0,
        "BEI_EV": 0,
        "Elevators": {}
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
        else:
            inputdata["Elevators"][room_name]["operation_time"] = bc.RoomUsageSchedule[buildingType][roomType]["年間照明点灯時間"]
        
        if DEBUG:
            print(f'室 {room_name} に設置された昇降機')
            print(f'  - 昇降機運転時間 {inputdata["Elevators"][room_name]["operation_time"]}')


    # エネルギー消費量計算 [kWh/年]
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


    #----------------------------------------------------------------------------------
    # 解説書 6.4 昇降機の設計一次エネルギー消費量
    #----------------------------------------------------------------------------------

    # 設計一次エネルギー消費量計算 [MJ/年]
    for room_name in inputdata["Elevators"]:
        for unit_id, unit_configure in enumerate(inputdata["Elevators"][room_name]["Elevator"]):

            resultJson["E_elevetor"] += unit_configure["energy_consumption"] * 9760 / 1000

    if DEBUG:
        print(f'昇降機の設計一次エネルギー消費量  {resultJson["E_elevetor"]}  MJ/年')


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

            # 基準一次エネルギー消費量計算 [MJ/年]
            resultJson["Es_elevetor"] += inputdata["Elevators"][room_name]["Elevator"][unit_id]["Es"] * 9760 / 1000

    if DEBUG:
        print(f'昇降機の基準一次エネルギー消費量  {resultJson["Es_elevetor"]}  MJ/年')


    # 入力データも出力
    resultJson["Elevetors"] = inputdata["Elevators"]

    # BEI/Vの計算
    resultJson["BEI_EV"] = resultJson["E_elevetor"] / resultJson["Es_elevetor"]

    return resultJson


if __name__ == '__main__':

    print('----- elevetor.py -----')
    filename = './sample/sample01_WEBPRO_inputSheet_for_Ver2.5.json'

    # 入力ファイルの読み込み
    with open(filename, 'r') as f:
        inputdata = json.load(f)

    resultJson = calc_energy(inputdata)
    print(resultJson)
