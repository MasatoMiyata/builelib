import json
import numpy as np
import os
import pandas as pd

import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import commons as bc

# データベースファイルの保存場所
database_directory =  os.path.dirname(os.path.abspath(__file__)) + "/database/"


def calc_energy(inputdata, DEBUG = False, output_dir = ""):
    
    # 一次エネルギー換算係数
    fprime = 9760
    if "CalculationMode" in inputdata:
        if isinstance(inputdata["CalculationMode"]["一次エネルギー換算係数"], (int, float)):
            fprime = inputdata["CalculationMode"]["一次エネルギー換算係数"]

    # 計算結果を格納する変数
    resultJson = {
        "E_other": 0,        # 基準一次エネルギー消費量 [MJ]
        "E_other_room": {},
        "for_CGS":{
            "Edesign_MWh_day": np.zeros(365),
            "ratio_AreaWeightedSchedule_AC": np.zeros((365,24)),   # 空調
            "ratio_AreaWeightedSchedule_LT": np.zeros((365,24)),   # 照明
            "ratio_AreaWeightedSchedule_OA": np.zeros((365,24))    # 機器発熱
        }
    }

    ##----------------------------------------------------------------------------------
    ## その他一次エネルギー消費量の原単位を求める（整数で丸める）
    ##----------------------------------------------------------------------------------
    
    # 機器発熱スケジュールを抽出
    roomScheduleRoom  = {}
    roomScheduleLight  = {}
    roomSchedulePerson  = {}
    roomScheduleOAapp  = {}
    roomHeatGain_OAapp  = {}

    for room_name in inputdata["Rooms"]:
    
        resultJson["E_other_room"][room_name] = {
            "E_other_standard"   : 0,              # 告示の値 [MJ/m2]
            "E_other": 0,                          # その他一次エネルギー消費量 [MJ/年]
            "E_ratio": 1,
            "roomHeatGain_daily" : np.zeros(365)   # 日別の機器発熱量 [MJ/m2/day]
        }


        # 365日×24時間分のスケジュール （365×24の行列を格納した dict型）
        if inputdata["Rooms"][room_name]["buildingType"] == "共同住宅":

            # 共同住宅共用部は 0 とする。
            roomScheduleRoom[room_name] = np.zeros((365,24))
            roomScheduleLight[room_name] = np.zeros((365,24))
            roomSchedulePerson[room_name] = np.zeros((365,24))
            roomScheduleOAapp[room_name] = np.zeros((365,24))
            roomHeatGain_OAapp[room_name] = 0

        else:

            # 標準室使用条件から時刻別の発熱密度比率（0～1。365×24の行列）を作成。
            if "SpecialInputData" in inputdata:
                roomScheduleRoom[room_name], roomScheduleLight[room_name], roomSchedulePerson[room_name], roomScheduleOAapp[room_name], _ = \
                    bc.get_roomUsageSchedule(inputdata["Rooms"][room_name]["buildingType"], inputdata["Rooms"][room_name]["roomType"], inputdata["SpecialInputData"])
            else:
                roomScheduleRoom[room_name], roomScheduleLight[room_name], roomSchedulePerson[room_name], roomScheduleOAapp[room_name], _ = \
                    bc.get_roomUsageSchedule(inputdata["Rooms"][room_name]["buildingType"], inputdata["Rooms"][room_name]["roomType"])

            # 機器発熱量参照値 [W/m2]の読み込み。SP-9に入力がある場合、任意の値を使用。
            if "SpecialInputData" in inputdata:
                (_, _, roomHeatGain_OAapp[room_name],_) = \
                    bc.get_roomHeatGain(inputdata["Rooms"][room_name]["buildingType"], inputdata["Rooms"][room_name]["roomType"], inputdata["SpecialInputData"])
            else:
                (_, _, roomHeatGain_OAapp[room_name],_) = \
                    bc.get_roomHeatGain(inputdata["Rooms"][room_name]["buildingType"], inputdata["Rooms"][room_name]["roomType"])


        if roomHeatGain_OAapp[room_name] != None:

            # 機器からの発熱（日積算）（365日分） [MJ/m2/day]
            resultJson["E_other_room"][room_name]["roomHeatGain_daily"]  = \
                np.sum(roomScheduleOAapp[room_name],1) * roomHeatGain_OAapp[room_name] / 1000000 * fprime

            # その他一次エネルギー消費量原単位（告示の値） [MJ/m2] の算出（端数処理）
            resultJson["E_other_room"][room_name]["E_other_standard"] = \
                round(np.sum(resultJson["E_other_room"][room_name]["roomHeatGain_daily"]))

            # 年積算値（端数調整前）が告示の値と一致するように補正する係数を求める（コジェネ計算時に日別消費電力を年積算値と一致させるために必要）。
            if np.sum(resultJson["E_other_room"][room_name]["roomHeatGain_daily"]) == 0:
                resultJson["E_other_room"][room_name]["E_ratio"] = 1
            else:
                resultJson["E_other_room"][room_name]["E_ratio"] = \
                    resultJson["E_other_room"][room_name]["E_other_standard"] / np.sum(resultJson["E_other_room"][room_name]["roomHeatGain_daily"])


        if DEBUG:
            print(f'室名: {room_name}')
            print(f'その他一次エネ原単位 MJ/m2 : {resultJson["E_other_room"][room_name]["E_other_standard"]}')
            print(f'補正係数 E_ratio : {resultJson["E_other_room"][room_name]["E_ratio"]}')


    ##----------------------------------------------------------------------------------
    ## その他一次エネルギー消費量
    ##----------------------------------------------------------------------------------
    for room_name in inputdata["Rooms"]:

        # その他一次エネルギー消費量 [MJ]
        resultJson["E_other_room"][room_name]["E_other"] = \
            resultJson["E_other_room"][room_name]["E_other_standard"] * inputdata["Rooms"][room_name]["roomArea"]

        resultJson["E_other"] += resultJson["E_other_room"][room_name]["E_other"]

        # 日別の電力消費量（告示に掲載の年積算値と一致させるために E_ratio で一律補正する）
        resultJson["for_CGS"]["Edesign_MWh_day"]  += \
            resultJson["E_other_room"][room_name]["roomHeatGain_daily"] * inputdata["Rooms"][room_name]["roomArea"] * resultJson["E_other_room"][room_name]["E_ratio"] / fprime


    ##----------------------------------------------------------------------------------
    # コジェネ計算用のスケジュール
    ##----------------------------------------------------------------------------------
    AreaWeightedSchedule_AC = np.zeros((365,24))
    AreaWeightedSchedule_LT = np.zeros((365,24))
    AreaWeightedSchedule_OA = np.zeros((365,24))

    # 空調スケジュール
    for room_zone_name in inputdata["AirConditioningZone"]:
        if room_zone_name in inputdata["Rooms"]:  # ゾーン分けがない場合

            AreaWeightedSchedule_AC += roomScheduleRoom[room_zone_name] * inputdata["Rooms"][room_zone_name]["roomArea"]

        else:

            # 各室のゾーンを検索
            for room_name in inputdata["Rooms"]:
                if inputdata["Rooms"][room_name]["zone"] != None:   # ゾーンがあれば
                    for zone_name  in inputdata["Rooms"][room_name]["zone"]:   # ゾーン名を検索
                        if room_zone_name == (room_name+"_"+zone_name):
                            
                            AreaWeightedSchedule_AC += roomScheduleRoom[room_name] * inputdata["Rooms"][room_name]["zone"][zone_name]["zoneArea"]

    # 照明スケジュール
    for room_zone_name in inputdata["LightingSystems"]:
        if room_zone_name in inputdata["Rooms"]:  # ゾーン分けがない場合

            AreaWeightedSchedule_LT += roomScheduleLight[room_zone_name] * inputdata["Rooms"][room_zone_name]["roomArea"]

        else:

            # 各室のゾーンを検索
            for room_name in inputdata["Rooms"]:
                if inputdata["Rooms"][room_name]["zone"] != None:   # ゾーンがあれば
                    for zone_name  in inputdata["Rooms"][room_name]["zone"]:   # ゾーン名を検索
                        if room_zone_name == (room_name+"_"+zone_name):
                            
                            AreaWeightedSchedule_LT += roomScheduleLight[room_name] * inputdata["Rooms"][room_name]["zone"][zone_name]["zoneArea"]               

    # 機器発熱スケジュール                   
    for room_name in inputdata["Rooms"]:
        AreaWeightedSchedule_OA += roomScheduleOAapp[room_name] * inputdata["Rooms"][room_name]["roomArea"]

    for dd in range(0,365):
        if np.sum(AreaWeightedSchedule_AC[dd]) != 0:
            resultJson["for_CGS"]["ratio_AreaWeightedSchedule_AC"][dd] = \
                AreaWeightedSchedule_AC[dd] / np.sum(AreaWeightedSchedule_AC[dd])
        if np.sum(AreaWeightedSchedule_LT[dd]) != 0:
            resultJson["for_CGS"]["ratio_AreaWeightedSchedule_LT"][dd] = \
                AreaWeightedSchedule_LT[dd] / np.sum(AreaWeightedSchedule_LT[dd])
        if np.sum(AreaWeightedSchedule_OA[dd]) != 0:
            resultJson["for_CGS"]["ratio_AreaWeightedSchedule_OA"][dd] = \
                AreaWeightedSchedule_OA[dd] / np.sum(AreaWeightedSchedule_OA[dd])

    if DEBUG:
        print(f'その他一次エネルギー消費量 MJ: {resultJson["E_other"]}')
            

    ##----------------------------------------------------------------------------------
    # CSV出力
    ##----------------------------------------------------------------------------------
    if output_dir != "":
        output_dir = output_dir + "_"

    df_daily_energy = pd.DataFrame({
        '一次エネルギー消費量（その他）[GJ]'  : resultJson["for_CGS"]["Edesign_MWh_day"] *  (fprime) /1000,
        '電力消費量（その他）[MWh]'  : resultJson["for_CGS"]["Edesign_MWh_day"],
    }, index=bc.date_1year)

    df_daily_energy.to_csv(output_dir + 'result_OT_Energy_daily.csv', index_label="日時", encoding='CP932')


    ##----------------------------------------------------------------------------------
    # 不要な要素を削除
    ##----------------------------------------------------------------------------------

    for roomID, isys in resultJson["E_other_room"].items():
        del resultJson["E_other_room"][roomID]["roomHeatGain_daily"]
        
    return resultJson


if __name__ == '__main__':

    # 現在のスクリプトファイルのディレクトリを取得
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 1つ上の階層のディレクトリパスを取得
    parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))

    print('----- other_energy.py -----')
    filename = parent_dir + '/sample/Baguio_Ayala_Land_Technohub_BPO-B_001_ベースモデル.json'

    # 入力ファイルの読み込み
    with open(filename, 'r', encoding='utf-8') as f:
        inputdata = json.load(f)

    resultJson = calc_energy(inputdata, DEBUG=True)

    with open("resultJson_OT.json",'w', encoding='utf-8') as fw:
        json.dump(resultJson, fw, indent=4, ensure_ascii=False, cls = bc.MyEncoder)