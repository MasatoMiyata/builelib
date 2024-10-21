import json
import math
import os
import sys

import numpy as np

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import commons as bc

# データベースファイルの保存場所
database_directory = os.path.dirname(os.path.abspath(__file__)) + "/database/"
# 気象データファイルの保存場所
climate_data_directory = os.path.dirname(os.path.abspath(__file__)) + "/climatedata/"


## 中間期平均外気温（附属書B.1）
def set_outdoor_temperature(region):
    if region == "1":
        toa_ave_design = 22.7
    elif region == "2":
        toa_ave_design = 22.8
    elif region == "3":
        toa_ave_design = 24.7
    elif region == "4":
        toa_ave_design = 26.8
    elif region == "5":
        toa_ave_design = 27.1
    elif region == "6":
        toa_ave_design = 27.6
    elif region == "7":
        toa_ave_design = 26.0
    elif region == "8":
        toa_ave_design = 26.2
    else:
        raise Exception('Error!')

    return toa_ave_design


def calc_energy(input_data, ventilation_ctrl, DEBUG=False):
    # 計算結果を格納する変数
    result_json = {

        "設計一次エネルギー消費量[MJ/年]": 0,  # 換気設備の設計一次エネルギー消費量 [MJ/年]
        "基準一次エネルギー消費量[MJ/年]": 0,  # 換気設備の基準一次エネルギー消費量 [MJ/年]
        "設計一次エネルギー消費量[GJ/年]": 0,  # 換気設備の設計一次エネルギー消費量 [GJ/年]
        "基準一次エネルギー消費量[GJ/年]": 0,  # 換気設備の基準一次エネルギー消費量 [GJ/年]
        "設計一次エネルギー消費量[MJ/m2年]": 0,  # 換気設備の設計一次エネルギー消費量 [MJ/年]
        "基準一次エネルギー消費量[MJ/m2年]": 0,  # 換気設備の基準一次エネルギー消費量 [MJ/年]
        "計算対象面積": 0,
        "BEI/V": 0,

        "時刻別設計一次エネルギー消費量[MJ/h]": np.zeros((365, 24)),  # 時刻別設計一次エネルギー消費量 [MJ]

        "ventilation": {
        },

        "for_cgs": {
            "Edesign_MWh_day": np.zeros(365)
        }
    }

    # 室毎（換気系統毎）のループ
    for room_id, isys in input_data["ventilation_room"].items():

        # 建物用途、室用途（可読性重視で一旦変数に代入する）
        building_type = input_data["rooms"][room_id]["building_type"]
        room_type = input_data["rooms"][room_id]["room_type"]
        input_data["ventilation_room"][room_id]["building_type"] = building_type
        input_data["ventilation_room"][room_id]["room_type"] = room_type

        # 室面積
        input_data["ventilation_room"][room_id]["room_area"] = input_data["rooms"][room_id]["room_area"]
        result_json["計算対象面積"] += input_data["rooms"][room_id]["room_area"]  # 保存用

        ##----------------------------------------------------------------------------------
        ## 年間換気運転時間 （解説書 B.2）
        ##----------------------------------------------------------------------------------

        input_data["ventilation_room"][room_id]["ope_time_hourly"] = bc.get_daily_ope_schedule_ventilation(
            building_type, room_type)

        # 年間換気運転時間
        input_data["ventilation_room"][room_id]["opeTime"] = np.sum(
            np.sum(input_data["ventilation_room"][room_id]["ope_time_hourly"]))

        # 接続されている換気機器の種類に応じて集計処理を実行
        input_data["ventilation_room"][room_id]["is_ventilation_using_ac"] = False
        input_data["ventilation_room"][room_id]["ac_cooling_capacity_total"] = 0
        input_data["ventilation_room"][room_id]["total_air_volume_supply"] = 0
        input_data["ventilation_room"][room_id]["total_air_volume_exhaust"] = 0

        # 換気代替空調機があるかどうかを判定
        for unit_id, iunit in input_data["ventilation_room"][room_id]["ventilation_unit_ref"].items():

            if iunit["unit_type"] == "空調":

                # 換気代替空調機であるかどうかを判定（unit_typeが「空調」である機器があれば、換気代替空調機であると判断する）
                input_data["ventilation_room"][room_id]["is_ventilation_using_ac"] = True

                # もし複数あれば、能力を合計する（外気冷房判定用）
                input_data["ventilation_room"][room_id]["ac_cooling_capacity_total"] += \
                    input_data["ventilation_unit"][unit_id]["ac_cooling_capacity"]

            elif iunit["unit_type"] == "給気":

                # 給気風量の合計（外気冷房判定用）
                input_data["ventilation_room"][room_id]["total_air_volume_supply"] += \
                input_data["ventilation_unit"][unit_id][
                    "fan_air_volume"]

            elif iunit["unit_type"] == "排気":

                # 排気風量の合計（外気冷房判定用）
                input_data["ventilation_room"][room_id]["total_air_volume_exhaust"] += \
                input_data["ventilation_unit"][unit_id][
                    "fan_air_volume"]

        # 接続されている換気機器のリストに室の情報を追加（複数室に跨がる換気送風機の計算のため）
        for unit_id, iunit in input_data["ventilation_room"][room_id]["ventilation_unit_ref"].items():

            # 室の名称を追加
            if "roomList" in input_data["ventilation_unit"][unit_id]:
                input_data["ventilation_unit"][unit_id]["roomList"].append(room_id)
            else:
                input_data["ventilation_unit"][unit_id]["roomList"] = [room_id]

            # 室の運転時間を追加
            if "ope_time_list" in input_data["ventilation_unit"][unit_id]:
                input_data["ventilation_unit"][unit_id]["ope_time_list"].append(
                    input_data["ventilation_room"][room_id]["opeTime"])
                input_data["ventilation_unit"][unit_id]["ope_time_list_hourly"].append(
                    input_data["ventilation_room"][room_id]["ope_time_hourly"])
            else:
                input_data["ventilation_unit"][unit_id]["ope_time_list"] = [
                    input_data["ventilation_room"][room_id]["opeTime"]]
                input_data["ventilation_unit"][unit_id]["ope_time_list_hourly"] = [
                    input_data["ventilation_room"][room_id]["ope_time_hourly"]]

            # 室の床面積を追加
            if "room_areaList" in input_data["ventilation_unit"][unit_id]:
                input_data["ventilation_unit"][unit_id]["room_areaList"].append(
                    input_data["ventilation_room"][room_id]["room_area"])
            else:
                input_data["ventilation_unit"][unit_id]["room_areaList"] = [
                    input_data["ventilation_room"][room_id]["room_area"]]

            # 換気代替空調機か否かを追加
            if "is_ventilation_using_ac" in input_data["ventilation_unit"][unit_id]:
                input_data["ventilation_unit"][unit_id]["is_ventilation_using_ac"].append(
                    input_data["ventilation_room"][room_id]["is_ventilation_using_ac"])
            else:
                input_data["ventilation_unit"][unit_id]["is_ventilation_using_ac"] = [
                    input_data["ventilation_room"][room_id]["is_ventilation_using_ac"]]

        if DEBUG:
            print(f'室名称  {room_id}')
            print(f'  - 換気代替空調の有無 {input_data["ventilation_room"][room_id]["is_ventilation_using_ac"]}')
            print(
                f'  - 換換気代替空調系統の熱源容量の合計容量 {input_data["ventilation_room"][room_id]["ac_cooling_capacity_total"]}')
            print(
                f'  - 換気代替空調系統の給気風量の合計容量 {input_data["ventilation_room"][room_id]["total_air_volume_supply"]}')
            print(
                f'  - 換気代替空調系統の排気風量の合計容量 {input_data["ventilation_room"][room_id]["total_air_volume_exhaust"]}')

    if DEBUG:
        for unit_id, iunit in input_data["ventilation_unit"].items():
            print(f'換気名称  {unit_id}')
            print(f'  - 室リスト {input_data["ventilation_unit"][unit_id]["roomList"]}')
            print(f'  - 床面積リスト {input_data["ventilation_unit"][unit_id]["room_areaList"]}')
            print(f'  - 運転時間リスト {input_data["ventilation_unit"][unit_id]["ope_time_list"]}')
            print(f'  - 換気代替空調機の有無 {input_data["ventilation_unit"][unit_id]["is_ventilation_using_ac"]}')

    ##----------------------------------------------------------------------------------
    ## 換気送風機の年間電力消費量（解説書 3.3）
    ##----------------------------------------------------------------------------------
    for unit_id, iunit in input_data["ventilation_unit"].items():

        # 電動機定格出力[kW]から消費電力[kW]を計算（1台あたり、制御なし）
        if iunit["power_consumption"] is not None:
            Ekw = iunit["power_consumption"]
        elif iunit["motor_rated_power"] is not None:
            Ekw = iunit["motor_rated_power"] / 0.75
        else:
            raise Exception('Error!')

        # 消費電力（制御込み）[kW]
        input_data["ventilation_unit"][unit_id]["energy_kw"] = \
            Ekw * iunit["number"] \
            * ventilation_ctrl["high_efficiency_motor"][iunit["high_efficiency_motor"]] \
            * ventilation_ctrl["inverter"][iunit["inverter"]] \
            * ventilation_ctrl["air_volume_control"][iunit["air_volume_control"]]

        # 床面積の合計
        input_data["ventilation_unit"][unit_id]["room_area_total"] = sum(iunit["room_areaList"])

        # 最大の運転時間
        input_data["ventilation_unit"][unit_id]["max_ope_time"] = 0
        input_data["ventilation_unit"][unit_id]["max_ope_time_hourly"] = np.zeros((365, 24))

        for opeTime_id, opeTime_V in enumerate(iunit["ope_time_list"]):
            if input_data["ventilation_unit"][unit_id]["max_ope_time"] < opeTime_V:
                input_data["ventilation_unit"][unit_id]["max_ope_time"] = opeTime_V
                input_data["ventilation_unit"][unit_id]["max_ope_time_hourly"] = \
                    input_data["ventilation_unit"][unit_id]["ope_time_list_hourly"][opeTime_id]

        # 換気代替空調機と換気送風機が混在していないかをチェック  →  混在していたらエラー
        if not all(iunit["is_ventilation_using_ac"]) and any(iunit["is_ventilation_using_ac"]):
            raise Exception('Error!')

    # 再度、室毎（換気系統毎）のループ
    for room_id, isys in input_data["ventilation_room"].items():

        # 各室の計算結果を格納
        result_json["ventilation"][room_id] = input_data["ventilation_room"][room_id]
        result_json["ventilation"][room_id]["時刻別設計一次エネルギー消費量[MJ/h]"] = np.zeros((365, 24))
        result_json["ventilation"][room_id]["設計値[MJ]"] = 0
        result_json["ventilation"][room_id]["基準値[MJ]"] = 0
        result_json["ventilation"][room_id]["設計値/基準値"] = 0
        result_json["ventilation"][room_id]["換気システムの種類"] = ""

        ##----------------------------------------------------------------------------------
        ## 換気代替空調機の年間電力消費量（解説書 3.4）
        ##----------------------------------------------------------------------------------
        if isys["is_ventilation_using_ac"]:  ## 換気代替空調機の場合（仕様書 3.4）

            result_json["ventilation"][room_id]["換気システムの種類"] = "換気代替空調機"

            # 外気取り込み量
            if isys["total_air_volume_supply"] > 0:
                outdoor_volume = isys["total_air_volume_supply"]
            elif isys["total_air_volume_exhaust"] > 0:
                outdoor_volume = isys["total_air_volume_exhaust"]
            else:
                outdoor_volume = 0

            # 外気冷房に必要な外気導入量
            required_oa_volume = 1000 * isys["ac_cooling_capacity_total"] / (
                    0.33 * (40 - set_outdoor_temperature(input_data["building"]["region"])))

            # 年間稼働率（表.20）
            if outdoor_volume > required_oa_volume:
                Cac = 0.35
                Cfan = 0.65
            else:
                Cac = 1.00
                Cfan = 1.00

            if DEBUG:
                print(f'室名称  {room_id}')
                print(f'  - 外気取り込み量 {outdoor_volume}')
                print(f'  - 外気冷房に必要な外気導入量 {required_oa_volume}')
                print(f'  - 年間稼働率 Cac {Cac}')
                print(f'  - 年間稼働率 Cfan {Cfan}')

            for unit_id, iunit in input_data["ventilation_room"][room_id]["ventilation_unit_ref"].items():

                if iunit["unit_type"] == "空調":  ## 換気代替空調機

                    # 熱源機とポンプ
                    if input_data["ventilation_unit"][unit_id]["ventilation_room_type"] != "":

                        # 負荷率（表.19）
                        if input_data["ventilation_unit"][unit_id]["ventilation_room_type"] == "エレベータ機械室":
                            xL = 0.3
                        elif input_data["ventilation_unit"][unit_id]["ventilation_room_type"] == "電気室":
                            xL = 0.6
                        elif input_data["ventilation_unit"][unit_id]["ventilation_room_type"] == "機械室":
                            xL = 0.6
                        elif input_data["ventilation_unit"][unit_id]["ventilation_room_type"] == "その他":
                            xL = 1.0
                        else:
                            # 直接数値を入力する場合
                            xL = float(input_data["ventilation_unit"][unit_id]["ventilation_room_type"])

                        # 換気代替空調機本体（時刻別）
                        result_json["ventilation"][room_id]["時刻別設計一次エネルギー消費量[MJ/h]"] += \
                            (input_data["ventilation_unit"][unit_id]["ac_cooling_capacity"] * xL / (
                                    2.71 * input_data["ventilation_unit"][unit_id]["ac_ref_efficiency"]) \
                             + input_data["ventilation_unit"][unit_id]["ac_pump_power"] / 0.75) \
                            * input_data["ventilation_room"][room_id]["room_area"] / \
                            input_data["ventilation_unit"][unit_id][
                                "room_area_total"] \
                            * input_data["ventilation_unit"][unit_id]["max_ope_time_hourly"] * bc.fprime * 10 ** (
                                -3) * Cac

                    # 空調機に付属するファン（時刻別）
                    result_json["ventilation"][room_id]["時刻別設計一次エネルギー消費量[MJ/h]"] += \
                        input_data["ventilation_unit"][unit_id]["energy_kw"] \
                        * input_data["ventilation_room"][room_id]["room_area"] / \
                        input_data["ventilation_unit"][unit_id][
                            "room_area_total"] \
                        * input_data["ventilation_unit"][unit_id]["max_ope_time_hourly"] * bc.fprime * 10 ** (-3) * Cac

                else:

                    # 換気代替空調機と併設される送風機(時刻別)
                    result_json["ventilation"][room_id]["時刻別設計一次エネルギー消費量[MJ/h]"] += \
                        input_data["ventilation_unit"][unit_id]["energy_kw"] \
                        * input_data["ventilation_room"][room_id]["room_area"] / \
                        input_data["ventilation_unit"][unit_id][
                            "room_area_total"] \
                        * input_data["ventilation_unit"][unit_id]["max_ope_time_hourly"] * bc.fprime * 10 ** (-3) * Cfan

                if DEBUG:
                    print(f'室名称 {room_id}, 機器名称 {unit_id}')
                    # print( f'  - 運転時間 {input_data["ventilation_unit"][unit_id]["max_ope_time"] }')
                    print(
                        f'  - 消費電力[W/m2] {input_data["ventilation_unit"][unit_id]["energy_kw"] / input_data["ventilation_room"][room_id]["room_area"] * 1000}')


        else:  ## 換気送風機の場合（仕様書 3.3）

            result_json["ventilation"][room_id]["換気システムの種類"] = "換気送風機"

            for unit_id, iunit in input_data["ventilation_room"][room_id]["ventilation_unit_ref"].items():
                # エネルギー消費量 [kW * m2/m2 * kJ/KWh] (時刻別)
                result_json["ventilation"][room_id]["時刻別設計一次エネルギー消費量[MJ/h]"] += \
                    input_data["ventilation_unit"][unit_id]["energy_kw"] \
                    * input_data["ventilation_room"][room_id]["room_area"] / input_data["ventilation_unit"][unit_id][
                        "room_area_total"] \
                    * input_data["ventilation_unit"][unit_id]["max_ope_time_hourly"] * bc.fprime * 10 ** (-3)

    ##----------------------------------------------------------------------------------
    ## 基準一次エネルギー消費量 [MJ] （解説書 10.2）
    ##----------------------------------------------------------------------------------
    for room_id, isys in input_data["ventilation_room"].items():
        # 建物用途、室用途（可読性重視で一旦変数に代入する）
        building_type = input_data["rooms"][room_id]["building_type"]
        room_type = input_data["rooms"][room_id]["room_type"]

        result_json["ventilation"][room_id]["基準値[MJ]"] = \
            bc.room_standard_value[building_type][room_type]["換気"] * input_data["rooms"][room_id]["room_area"]

    ##----------------------------------------------------------------------------------
    # 結果の集計
    ##----------------------------------------------------------------------------------

    for room_id, isys in input_data["ventilation_room"].items():
        result_json["ventilation"][room_id]["設計値[MJ]"] = np.sum(
            np.sum(result_json["ventilation"][room_id]["時刻別設計一次エネルギー消費量[MJ/h]"]))
        result_json["ventilation"][room_id]["設計値[MJ/m2]"] = result_json["ventilation"][room_id]["設計値[MJ]"] / \
                                                               input_data["rooms"][room_id]["room_area"]
        if result_json["ventilation"][room_id]["基準値[MJ]"] != 0:
            result_json["ventilation"][room_id]["設計値/基準値"] = result_json["ventilation"][room_id]["設計値[MJ]"] / \
                                                                   result_json["ventilation"][room_id]["基準値[MJ]"]
        else:
            result_json["ventilation"][room_id]["設計値/基準値"] = 0

        result_json["設計一次エネルギー消費量[MJ/年]"] += result_json["ventilation"][room_id]["設計値[MJ]"]
        result_json["基準一次エネルギー消費量[MJ/年]"] += result_json["ventilation"][room_id]["基準値[MJ]"]
        result_json["時刻別設計一次エネルギー消費量[MJ/h]"] += result_json["ventilation"][room_id][
            "時刻別設計一次エネルギー消費量[MJ/h]"]

    result_json["設計一次エネルギー消費量[GJ/年]"] = result_json["設計一次エネルギー消費量[MJ/年]"] / 1000
    result_json["基準一次エネルギー消費量[GJ/年]"] = result_json["基準一次エネルギー消費量[MJ/年]"] / 1000
    result_json["設計一次エネルギー消費量[MJ/m2年]"] = result_json["設計一次エネルギー消費量[MJ/年]"] / result_json[
        "計算対象面積"]
    result_json["基準一次エネルギー消費量[MJ/m2年]"] = result_json["基準一次エネルギー消費量[MJ/年]"] / result_json[
        "計算対象面積"]

    # BEI/V [-]
    if result_json["基準一次エネルギー消費量[MJ/年]"] <= 0:
        result_json["BEI/V"] = None
    else:
        result_json["BEI/V"] = result_json["設計一次エネルギー消費量[MJ/年]"] / result_json["基準一次エネルギー消費量[MJ/年]"]
        result_json["BEI/V"] = math.ceil(result_json["BEI/V"] * 100) / 100

    # コジェネ用の結果の格納 [MJ → MWh]
    for day in range(0, 365):
        result_json["for_cgs"]["Edesign_MWh_day"][day] = np.sum(result_json["時刻別設計一次エネルギー消費量[MJ/h]"][day]) / (
            bc.fprime)

        ##----------------------------------------------------------------------------------
    # 不要な要素を削除
    ##----------------------------------------------------------------------------------

    del result_json["時刻別設計一次エネルギー消費量[MJ/h]"]

    for room_id, isys in input_data["ventilation_room"].items():
        del result_json["ventilation"][room_id]["ope_time_hourly"]
        del result_json["ventilation"][room_id]["時刻別設計一次エネルギー消費量[MJ/h]"]

    return result_json


if __name__ == '__main__':
    # 現在のスクリプトファイルのディレクトリを取得
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 1つ上の階層のディレクトリパスを取得
    parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))

    print('----- ventilation.py -----')
    filename = parent_dir + '/sample/WEBPRO_inputSheet_sample_input.json'

    # テンプレートjsonの読み込み
    with open(filename, 'r', encoding='utf-8') as f:
        input_data = json.load(f)

    result_json = calc_energy(input_data, DEBUG=False)

    with open("result_json_V.json", 'w', encoding='utf-8') as fw:
        json.dump(result_json, fw, indent=4, ensure_ascii=False, cls=bc.MyEncoder)

    print(f'設計一次エネルギー消費量[MJ] {result_json["設計一次エネルギー消費量[MJ/年]"]}')
    print(f'基準一次エネルギー消費量[MJ] {result_json["基準一次エネルギー消費量[MJ/年]"]}')
