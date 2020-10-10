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

def calc_energy(inputdata, DEBUG = False):

    # 計算結果を格納する変数
    resultJson = {
        "E_other": 0,        # 基準一次エネルギー消費量 [MJ]
        "E_other_room": {}
    }

    ##----------------------------------------------------------------------------------
    ## その他一次エネルギー消費量の原単位を求める（整数で丸める）
    ##----------------------------------------------------------------------------------
    
    # 機器発熱スケジュールを抽出
    roomScheduleOAapp  = {}
    roomHeatGain_OAapp  = {}

    for room_name in inputdata["Rooms"]:
    
        resultJson["E_other_room"][room_name] = {
            "E_other_standard"   : 0,              # 告示の値 [MJ/m2]
            "E_other": 0,                          # その他一次エネルギー消費量 [MJ/年]
            "roomHeatGain_daily" : np.zeros(365)   # 日別の機器発熱量 [MJ/m2/day]
        }

        # 365日×24時間分のスケジュール （365×24の行列を格納した dict型）
        _, _, _, roomScheduleOAapp[room_name], _ = \
            bc.get_roomUsageSchedule(inputdata["Rooms"][room_name]["buildingType"], inputdata["Rooms"][room_name]["roomType"])

        # 発熱量参照値 [W/m2]
        (_, _, roomHeatGain_OAapp[room_name]) = \
            bc.get_roomHeatGain(inputdata["Rooms"][room_name]["buildingType"], inputdata["Rooms"][room_name]["roomType"])

        if roomHeatGain_OAapp[room_name] != None:

            # 機器からの発熱（日積算）（365日分） [MJ/m2/day]
            resultJson["E_other_room"][room_name]["roomHeatGain_daily"]  = \
                np.sum(roomScheduleOAapp[room_name],1) * roomHeatGain_OAapp[room_name] / 1000000 * bc.fprime

            # その他一次エネルギー消費量原単位（告示の値） [MJ/m2]
            resultJson["E_other_room"][room_name]["E_other_standard"] = \
                round(np.sum(resultJson["E_other_room"][room_name]["roomHeatGain_daily"]))

        if DEBUG:
            print(f'室名: {room_name}')
            print(f'その他一次エネ原単位 MJ/m2: {resultJson["E_other_room"][room_name]["E_other_standard"]}')


    ##----------------------------------------------------------------------------------
    ## その他一次エネルギー消費量
    ##----------------------------------------------------------------------------------
    for room_name in inputdata["Rooms"]:

        # その他一次エネルギー消費量 [MJ]
        resultJson["E_other_room"][room_name]["E_other"] = \
            resultJson["E_other_room"][room_name]["E_other_standard"] * inputdata["Rooms"][room_name]["roomArea"]

        resultJson["E_other"] += resultJson["E_other_room"][room_name]["E_other"]

    if DEBUG:
        print(f'その他一次エネルギー消費量 MJ: {resultJson["E_other"]}')


    return resultJson


if __name__ == '__main__':

    print('----- other_energy.py -----')
    filename = './sample/sample01_WEBPRO_inputSheet_for_Ver2.5.json'

    # 入力ファイルの読み込み
    with open(filename, 'r') as f:
        inputdata = json.load(f)

    resultJson = calc_energy(inputdata, DEBUG=True)

    with open("resultJson.json",'w') as fw:
        json.dump(resultJson, fw, indent=4, ensure_ascii=False, cls = MyEncoder)