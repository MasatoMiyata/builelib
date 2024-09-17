import json
import math
import os
import sys

import numpy as np

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import commons as bc

# データベースファイルの保存場所
database_directory = os.path.dirname(os.path.abspath(__file__)) + "/database/"


def set_room_indexCoeff(room_index):
    '''
    室の形状に応じて定められる係数（仕様書4.4）
    '''

    if (room_index == "") or (room_index is None):
        room_indexCoeff = 1
    else:
        if room_index < 0:
            room_indexCoeff = 1
        elif room_index < 0.75:
            room_indexCoeff = 0.50
        elif room_index < 0.95:
            room_indexCoeff = 0.60
        elif room_index < 1.25:
            room_indexCoeff = 0.70
        elif room_index < 1.75:
            room_indexCoeff = 0.80
        elif room_index < 2.50:
            room_indexCoeff = 0.90
        elif room_index >= 2.50:
            room_indexCoeff = 1.00

    return room_indexCoeff


def calc_energy(input_data, DEBUG=False):
    # データベースjsonの読み込み
    with open(database_directory + 'lighting_control.json', 'r', encoding='utf-8') as f:
        lightingCtrl = json.load(f)

    # 計算結果を格納する変数
    result_json = {
        "E_lighting": None,
        "Es_lighting": None,
        "BEI_L": None,
        "E_lighting_hourly": None,
        "lighting": {
        },
        "for_cgs": {
            "Edesign_MWh_day": np.zeros(365)
        }
    }

    # 変数初期化
    E_lighting = 0  # 設計一次エネルギー消費量 [GJ]
    E_lighting_hourly = np.zeros((365, 24))  # 設計一次エネルギー消費量（時刻別） [GJ]
    Es_lighting = 0  # 基準一次エネルギー消費量 [GJ]
    total_area = 0  # 建物全体の床面積

    ##----------------------------------------------------------------------------------
    ## 任意評定 （SP-6: カレンダーパターン)
    ##----------------------------------------------------------------------------------
    input_calendar = []
    if "calender" in input_data["special_input_data"]:
        input_calendar = input_data["special_input_data"]["calender"]

    # 室毎（照明系統毎）のループ
    for room_zone_name in input_data["lighting_systems"]:

        # 建物用途、室用途、室面積の取得
        building_type = input_data["rooms"][room_zone_name]["building_type"]
        room_type = input_data["rooms"][room_zone_name]["room_type"]
        room_area = input_data["rooms"][room_zone_name]["room_area"]

        # 年間照明点灯時間 [時間] ← 計算には使用しない。
        # opeTime = bc.RoomUsageSchedule[building_type][room_type]["年間照明点灯時間"]

        # 時刻別スケジュールの読み込み
        opePattern_hourly_light = bc.get_dailyOpeSchedule_lighting(building_type, room_type, input_calendar)
        opeTime = np.sum(np.sum(opePattern_hourly_light))

        ##----------------------------------------------------------------------------------
        ## 任意評定 （SP-7: 室スケジュール)
        ##----------------------------------------------------------------------------------

        if "room_schedule" in input_data["special_input_data"]:

            # SP-7に入力されていれば
            if room_zone_name in input_data["special_input_data"]["room_schedule"]:

                if "照明発熱密度比率" in input_data["special_input_data"]["room_schedule"][room_zone_name]["schedule"]:
                    opePattern_hourly_light = np.array(
                        input_data["special_input_data"]["room_schedule"][room_zone_name]["schedule"]["照明発熱密度比率"])

                    # SP-7の場合は、発熱比率をそのまま使用することにする。
                    # opePattern_hourly_light = np.where(opePattern_hourly_light > 0, 1, 0)

        ## 室の形状に応じて定められる係数（仕様書4.4）
        # 室指数
        if input_data["lighting_systems"][room_zone_name]["room_index"] is not None:
            room_index = input_data["lighting_systems"][room_zone_name]["room_index"]
        elif input_data["lighting_systems"][room_zone_name]["room_width"] is not None and \
                input_data["lighting_systems"][room_zone_name]["room_depth"] is not None and \
                input_data["lighting_systems"][room_zone_name]["unit_height"] is not None:
            if input_data["lighting_systems"][room_zone_name]["room_width"] > 0 and \
                    input_data["lighting_systems"][room_zone_name]["room_depth"] > 0 and \
                    input_data["lighting_systems"][room_zone_name]["unit_height"] > 0:
                room_index = (input_data["lighting_systems"][room_zone_name]["room_width"] *
                             input_data["lighting_systems"][room_zone_name]["room_depth"]) / ((input_data[
                                                                                                "lighting_systems"][
                                                                                                room_zone_name][
                                                                                                "room_width"] +
                                                                                            input_data[
                                                                                                "lighting_systems"][
                                                                                                room_zone_name][
                                                                                                "room_depth"]) *
                                                                                           input_data["lighting_systems"][
                                                                                               room_zone_name][
                                                                                               "unit_height"])
            else:
                room_index = None
        else:
            room_index = None

        # 補正係数
        room_indexCoeff = set_room_indexCoeff(room_index)

        ## 器具毎のループ
        unitPower = 0
        for unit_name in input_data["lighting_systems"][room_zone_name]["lighting_unit"]:

            # 在室検知制御方式の効果係数
            ctrl_occupant_sensing = 1
            if input_data["lighting_systems"][room_zone_name]["lighting_unit"][unit_name]["occupant_sensing_ctrl"] in \
                    lightingCtrl["occupant_sensing_ctrl"]:
                # データベースから検索して効果係数を決定
                ctrl_occupant_sensing = lightingCtrl["occupant_sensing_ctrl"][
                    input_data["lighting_systems"][room_zone_name]["lighting_unit"][unit_name]["occupant_sensing_ctrl"]]
            else:
                # 直接入力された効果係数を使用
                ctrl_occupant_sensing = float(
                    input_data["lighting_systems"][room_zone_name]["lighting_unit"][unit_name]["occupant_sensing_ctrl"])

            # 明るさ検知制御方式の効果係数
            ctrl_illuminance_sensing = 1
            if input_data["lighting_systems"][room_zone_name]["lighting_unit"][unit_name]["illuminance_sensing_ctrl"] in \
                    lightingCtrl["illuminance_sensing_ctrl"]:
                # データベースから検索して効果係数を決定
                ctrl_illuminance_sensing = lightingCtrl["illuminance_sensing_ctrl"][
                    input_data["lighting_systems"][room_zone_name]["lighting_unit"][unit_name]["illuminance_sensing_ctrl"]]
            else:
                # 直接入力された効果係数を使用
                ctrl_illuminance_sensing = float(
                    input_data["lighting_systems"][room_zone_name]["lighting_unit"][unit_name]["illuminance_sensing_ctrl"])

            # タイムスケジュール制御方式の効果係数
            ctrl_time_schedule = 1
            if input_data["lighting_systems"][room_zone_name]["lighting_unit"][unit_name]["time_schedule_ctrl"] in \
                    lightingCtrl["time_schedule_ctrl"]:
                # データベースから検索して効果係数を決定
                ctrl_time_schedule = lightingCtrl["time_schedule_ctrl"][
                    input_data["lighting_systems"][room_zone_name]["lighting_unit"][unit_name]["time_schedule_ctrl"]]
            else:
                # 直接入力された効果係数を使用
                ctrl_time_schedule = float(
                    input_data["lighting_systems"][room_zone_name]["lighting_unit"][unit_name]["time_schedule_ctrl"])

            # 初期照度補正の効果係数
            initial_illumination_correction = 1
            if input_data["lighting_systems"][room_zone_name]["lighting_unit"][unit_name][
                "initial_illumination_correction_ctrl"] in lightingCtrl["initial_illumination_correction_ctrl"]:
                # データベースから検索して効果係数を決定
                initial_illumination_correction = lightingCtrl["initial_illumination_correction_ctrl"][
                    input_data["lighting_systems"][room_zone_name]["lighting_unit"][unit_name][
                        "initial_illumination_correction_ctrl"]]
            else:
                # 直接入力された効果係数を使用
                initial_illumination_correction = float(
                    input_data["lighting_systems"][room_zone_name]["lighting_unit"][unit_name][
                        "initial_illumination_correction_ctrl"])

            # 照明器具の消費電力（制御込み） [W]
            unitPower += input_data["lighting_systems"][room_zone_name]["lighting_unit"][unit_name]["rated_power"] \
                         * input_data["lighting_systems"][room_zone_name]["lighting_unit"][unit_name]["number"] \
                         * ctrl_occupant_sensing * ctrl_illuminance_sensing * ctrl_time_schedule * initial_illumination_correction

        # 時刻別の設計一次エネルギー消費量 [MJ]
        E_room_hourly = opePattern_hourly_light * unitPower * room_indexCoeff * bc.fprime * 10 ** (-6)

        # 各室の年間エネルギー消費量 [MJ]
        E_room = E_room_hourly.sum()

        # 出力用に積算
        E_lighting += E_room
        E_lighting_hourly += E_room_hourly

        total_area += room_area

        # 床面積あたりの設計一次エネルギー消費量 [MJ/m2]
        if room_area <= 0:
            primary_energy_per_area = None
        else:
            primary_energy_per_area = E_room / room_area

        # 基準一次エネルギー消費量 [MJ]
        Es_room = bc.room_standard_value[building_type][room_type]["照明"] * room_area
        Es_lighting += Es_room  # 出力用に積算

        # 各室の計算結果を格納
        result_json["lighting"][room_zone_name] = {
            "building_type": building_type,
            "room_type": room_type,
            "room_area": room_area,
            "opelationTime": opeTime,
            "room_index": room_index,
            "room_indexCoeff": room_indexCoeff,
            "unitPower": unitPower,
            "primaryEnergy": E_room,
            "standardEnergy": Es_room,
            "primary_energy_per_area": primary_energy_per_area,
            "energyRatio": E_room / Es_room
        }

        if DEBUG:
            print(f'室名称　{room_zone_name}')
            print(f'　- 設計一次エネルギー消費量  {E_room} MJ')
            print(f'　- 基準一次エネルギー消費量  {Es_room} MJ')

    # BEI/L [-]
    if Es_lighting <= 0:
        BEI_L = None
    else:
        BEI_L = math.ceil((E_lighting / Es_lighting) * 100) / 100

    # 建物全体の計算結果
    result_json["BEI_L"] = BEI_L
    result_json["total_area"] = total_area
    result_json["E_lighting"] = E_lighting
    result_json["E_lighting_GJ"] = E_lighting / 1000
    result_json["E_lighting_MJ_m2"] = E_lighting / total_area
    result_json["Es_lighting"] = Es_lighting
    result_json["Es_lighting_GJ"] = Es_lighting / 1000
    result_json["Es_lighting_MJ_m2"] = Es_lighting / total_area
    # result_json["E_lighting_hourly"] = E_lighting_hourly

    # 日積算値
    result_json["for_cgs"]["Edesign_MWh_day"] = np.sum(E_lighting_hourly / 9760, 1)

    return result_json


if __name__ == '__main__':
    print('----- lighting.py -----')
    filename = './sample/WEBPRO_inputSheet_sample.json'
    # filename = './tests/cogeneration/Case_hotel_00.json'

    # テンプレートjsonの読み込み
    with open(filename, 'r', encoding='utf-8') as f:
        input_data = json.load(f)

    result_json = calc_energy(input_data, DEBUG=False)

    print(f'設計値: {result_json["E_lighting"]}')
    print(f'基準値: {result_json["Es_lighting"]}')

    with open("result_json_L.json", 'w', encoding='utf-8') as fw:
        json.dump(result_json, fw, indent=4, ensure_ascii=False, cls=bc.MyEncoder)
