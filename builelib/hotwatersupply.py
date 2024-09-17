import json
import math
import os
import sys

import numpy as np

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import commons as bc
import climate

# データベースファイルの保存場所
database_directory = os.path.dirname(os.path.abspath(__file__)) + "/database/"
# 気象データファイルの保存場所
climate_data_directory = os.path.dirname(os.path.abspath(__file__)) + "/climatedata/"


def calc_energy(input_data, DEBUG=False):
    # 計算結果を格納する変数
    result_json = {

        "設計一次エネルギー消費量[MJ/年]": 0,  # 給湯設備の設計一次エネルギー消費量 [MJ/年]
        "基準一次エネルギー消費量[MJ/年]": 0,  # 給湯設備の基準一次エネルギー消費量 [MJ/年]
        "設計一次エネルギー消費量[GJ/年]": 0,  # 給湯設備の設計一次エネルギー消費量 [GJ/年]
        "基準一次エネルギー消費量[GJ/年]": 0,  # 給湯設備の基準一次エネルギー消費量 [GJ/年]
        "設計一次エネルギー消費量[MJ/m2年]": 0,  # 給湯設備の設計一次エネルギー消費量 [MJ/年]
        "基準一次エネルギー消費量[MJ/m2年]": 0,  # 給湯設備の基準一次エネルギー消費量 [MJ/年]
        "BEI/hW": 0,
        "計算対象面積": 0,

        "hot_water_supply_systems": {
        },

        "for_cgs": {
            "edesign_mwh_ele_day": 0,  # 給湯設備（エネルギー源を電力とする給湯機器のみが対象）の電力消費量
            "Edesign_MJ_CGS_day": 0,  # 排熱利用する給湯系統の一次エネルギー消費量
            "Q_eqp_CGS_day": 0  # 排熱が利用できる系統の給湯設備の給湯負荷
        }
    }

    # 地域別データの読み込み
    with open(database_directory + 'area.json', 'r', encoding='utf-8') as f:
        area = json.load(f)

    ##----------------------------------------------------------------------------------
    ## 気象データの読み込み
    ##----------------------------------------------------------------------------------
    tout, _, iod, ios, inn = climate.read_hasp_climate_data(climate_data_directory + "/" +
                                                         area[input_data["building"]["region"] + "地域"][
                                                             "気象データファイル名"])

    ##----------------------------------------------------------------------------------
    ## 任意入力 （SP-6: カレンダーパターン)
    ##----------------------------------------------------------------------------------
    input_calendar = []
    if "calender" in input_data["special_input_data"]:
        input_calendar = input_data["special_input_data"]["calender"]

    ##----------------------------------------------------------------------------------
    ## 任意入力 （SP-9: 室使用条件)
    ##----------------------------------------------------------------------------------
    input_room_usage_condition = {}
    if "room_usage_condition" in input_data["special_input_data"]:
        input_room_usage_condition = input_data["special_input_data"]["room_usage_condition"]

        # ----------------------------------------------------------------------------------
    # 入力データの整理（計算準備）
    # ----------------------------------------------------------------------------------

    # 台数をかけて、加熱能力等を算出する。
    for unit_name in input_data["hot_water_supply_systems"]:

        for unit_id, unit_configure in enumerate(input_data["hot_water_supply_systems"][unit_name]["heat_sourceUnit"]):

            # 加熱能力 kW/台 × 台
            input_data["hot_water_supply_systems"][unit_name]["heat_sourceUnit"][unit_id]["rated_capacity_total"] = \
                unit_configure["rated_capacity"] * unit_configure["number"]

            # 消費エネルギー kW/台 × 台
            input_data["hot_water_supply_systems"][unit_name]["heat_sourceUnit"][unit_id]["RatedEnergyConsumption_total"] = \
                unit_configure["rated_power_consumption"] * unit_configure["number"] * 9760 / 3600 + \
                unit_configure["rated_fuel_consumption"] * unit_configure["number"]

            # 機器効率
            input_data["hot_water_supply_systems"][unit_name]["heat_sourceUnit"][unit_id]["RatedEfficiency"] = \
                input_data["hot_water_supply_systems"][unit_name]["heat_sourceUnit"][unit_id]["rated_capacity_total"] / \
                input_data["hot_water_supply_systems"][unit_name]["heat_sourceUnit"][unit_id]["RatedEnergyConsumption_total"]

            if DEBUG:
                print(f'機器名称 {unit_name} の {unit_id + 1} 台目')
                print(
                    f'  - 給湯機器の効率 {input_data["hot_water_supply_systems"][unit_name]["heat_sourceUnit"][unit_id]["RatedEfficiency"]}')

    # 機器全体の合計加熱能力と重み付け平均効率を算出する。
    for unit_name in input_data["hot_water_supply_systems"]:

        # 合計加熱能力 [kW]
        input_data["hot_water_supply_systems"][unit_name]["rated_capacity_total"] = 0

        tmp_Capacity_efficiency = 0

        for unit_id, unit_configure in enumerate(input_data["hot_water_supply_systems"][unit_name]["heat_sourceUnit"]):
            # 加熱能力の合計
            input_data["hot_water_supply_systems"][unit_name]["rated_capacity_total"] += \
                unit_configure["rated_capacity_total"]

            # 加熱能力 × 効率
            tmp_Capacity_efficiency += \
                unit_configure["rated_capacity_total"] * \
                unit_configure["RatedEfficiency"]

        # 加熱能力で重み付けした平均効率 [-]
        input_data["hot_water_supply_systems"][unit_name]["RatedEfficiency_total"] = \
            tmp_Capacity_efficiency / \
            input_data["hot_water_supply_systems"][unit_name]["rated_capacity_total"]

    # ----------------------------------------------------------------------------------
    # 解説書 D.1 標準日積算湯使用量（標準室使用条件）
    # ----------------------------------------------------------------------------------

    for room_name in input_data["hot_water_room"]:

        # 日積算湯使用利用 [L/m2/day]
        hotwater_demand, hotwater_demand_wasroom_enthalpy_setting, hotwater_demand_shower, hotwater_demand_kitchen, hotwater_demand_other = \
            bc.get_room_hot_water_demand(
                input_data["rooms"][room_name]["building_type"],
                input_data["rooms"][room_name]["room_type"],
                input_room_usage_condition

            )

        # 日積算給湯量参照値 [L/day]
        input_data["hot_water_room"][room_name]["hotwater_demand"] = hotwater_demand * input_data["rooms"][room_name][
            "room_area"]
        input_data["hot_water_room"][room_name]["hotwater_demand_wasroom_enthalpy_setting"] = hotwater_demand_wasroom_enthalpy_setting * \
                                                                           input_data["rooms"][room_name]["room_area"]
        input_data["hot_water_room"][room_name]["hotwater_demand_shower"] = hotwater_demand_shower * \
                                                                         input_data["rooms"][room_name]["room_area"]
        input_data["hot_water_room"][room_name]["hotwater_demand_kitchen"] = hotwater_demand_kitchen * \
                                                                          input_data["rooms"][room_name]["room_area"]
        input_data["hot_water_room"][room_name]["hotwater_demand_other"] = hotwater_demand_other * \
                                                                        input_data["rooms"][room_name]["room_area"]

        # 各室の室使用スケジュール （＝室の同時使用率。 給湯需要がある室は、必ず空調されている前提とする）
        room_schedule_room, _, _, _, _ = \
            bc.get_room_usage_schedule(input_data["rooms"][room_name]["building_type"],
                                     input_data["rooms"][room_name]["room_type"], input_calendar)

        input_data["hot_water_room"][room_name]["hotwaterSchedule"] = np.zeros(365)
        input_data["hot_water_room"][room_name]["hotwaterSchedule"][np.sum(room_schedule_room, 1) > 0] = 1

        # 日別の給湯量 [L/day] (365×1)
        input_data["hot_water_room"][room_name]["hotwater_demand_daily"] = \
            input_data["hot_water_room"][room_name]["hotwater_demand"] * input_data["hot_water_room"][room_name][
                "hotwaterSchedule"]

        input_data["hot_water_room"][room_name]["hotwater_demand_wasroom_enthalpy_setting_daily"] = \
            input_data["hot_water_room"][room_name]["hotwater_demand_wasroom_enthalpy_setting"] * input_data["hot_water_room"][room_name][
                "hotwaterSchedule"]

        input_data["hot_water_room"][room_name]["hotwater_demand_shower_daily"] = \
            input_data["hot_water_room"][room_name]["hotwater_demand_shower"] * input_data["hot_water_room"][room_name][
                "hotwaterSchedule"]

        input_data["hot_water_room"][room_name]["hotwater_demand_kitchen_daily"] = \
            input_data["hot_water_room"][room_name]["hotwater_demand_kitchen"] * input_data["hot_water_room"][room_name][
                "hotwaterSchedule"]

        input_data["hot_water_room"][room_name]["hotwater_demand_other_daily"] = \
            input_data["hot_water_room"][room_name]["hotwater_demand_other"] * input_data["hot_water_room"][room_name][
                "hotwaterSchedule"]

        # 日別の給湯量 [L/day] (365×1) の任意入力 （SP-11: 日積算湯使用量)
        if "hotwater_demand_daily" in input_data["special_input_data"]:
            if room_name in input_data["special_input_data"]["hotwater_demand_daily"]:

                if "洗面" in input_data["special_input_data"]["hotwater_demand_daily"][room_name]:
                    input_data["hot_water_room"][room_name]["hotwater_demand_wasroom_enthalpy_setting_daily"] = \
                        np.array(input_data["special_input_data"]["hotwater_demand_daily"][room_name]["洗面"])

                if "シャワー" in input_data["special_input_data"]["hotwater_demand_daily"][room_name]:
                    input_data["hot_water_room"][room_name]["hotwater_demand_shower_daily"] = \
                        np.array(input_data["special_input_data"]["hotwater_demand_daily"][room_name]["シャワー"])

                if "厨房" in input_data["special_input_data"]["hotwater_demand_daily"][room_name]:
                    input_data["hot_water_room"][room_name]["hotwater_demand_kitchen_daily"] = \
                        np.array(input_data["special_input_data"]["hotwater_demand_daily"][room_name]["厨房"])

                if "その他" in input_data["special_input_data"]["hotwater_demand_daily"][room_name]:
                    input_data["hot_water_room"][room_name]["hotwater_demand_other_daily"] = \
                        np.array(input_data["special_input_data"]["hotwater_demand_daily"][room_name]["その他"])

                # 合計を更新
                input_data["hot_water_room"][room_name]["hotwater_demand_daily"] = \
                    np.array(input_data["hot_water_room"][room_name]["hotwater_demand_wasroom_enthalpy_setting_daily"]) + \
                    np.array(input_data["hot_water_room"][room_name]["hotwater_demand_shower_daily"]) + \
                    np.array(input_data["hot_water_room"][room_name]["hotwater_demand_kitchen_daily"]) + \
                    np.array(input_data["hot_water_room"][room_name]["hotwater_demand_other_daily"])

        if DEBUG:
            print(f'室名称 {room_name}')
            print(f'  - 給湯使用量参照値 L/day {input_data["hot_water_room"][room_name]["hotwater_demand"]}')
            print(f'  - 給湯日数 {np.sum(input_data["hot_water_room"][room_name]["hotwaterSchedule"])}')
            print(f'  - 日別給湯使用量 {np.sum(input_data["hot_water_room"][room_name]["hotwater_demand_daily"])}')
            print(
                f'  - 日別給湯使用量（手洗い） {np.sum(input_data["hot_water_room"][room_name]["hotwater_demand_wasroom_enthalpy_setting_daily"])}')
            print(
                f'  - 日別給湯使用量（シャワー） {np.sum(input_data["hot_water_room"][room_name]["hotwater_demand_shower_daily"])}')
            print(
                f'  - 日別給湯使用量（厨房） {np.sum(input_data["hot_water_room"][room_name]["hotwater_demand_kitchen_daily"])}')
            print(
                f'  - 日別給湯使用量（その他） {np.sum(input_data["hot_water_room"][room_name]["hotwater_demand_other_daily"])}')

    # ----------------------------------------------------------------------------------
    # 解説書 D.5 給湯配管の線熱損失係数
    # ----------------------------------------------------------------------------------

    # 給湯配管の線熱損失係数の読み込み
    with open(database_directory + 'thermal_conductivity_piping.json', 'r', encoding='utf-8') as f:
        thermal_conductivity_dict = json.load(f)

    for unit_name in input_data["hot_water_supply_systems"]:

        # 接続口径の種類
        if input_data["hot_water_supply_systems"][unit_name]["pipe_size"] <= 13:
            input_data["hot_water_supply_systems"][unit_name]["pipe_sizetype"] = "13A以下"
        elif input_data["hot_water_supply_systems"][unit_name]["pipe_size"] <= 20:
            input_data["hot_water_supply_systems"][unit_name]["pipe_sizetype"] = "20A以下"
        elif input_data["hot_water_supply_systems"][unit_name]["pipe_size"] <= 25:
            input_data["hot_water_supply_systems"][unit_name]["pipe_sizetype"] = "25A以下"
        elif input_data["hot_water_supply_systems"][unit_name]["pipe_size"] <= 30:
            input_data["hot_water_supply_systems"][unit_name]["pipe_sizetype"] = "30A以下"
        elif input_data["hot_water_supply_systems"][unit_name]["pipe_size"] <= 40:
            input_data["hot_water_supply_systems"][unit_name]["pipe_sizetype"] = "40A以下"
        elif input_data["hot_water_supply_systems"][unit_name]["pipe_size"] <= 50:
            input_data["hot_water_supply_systems"][unit_name]["pipe_sizetype"] = "50A以下"
        elif input_data["hot_water_supply_systems"][unit_name]["pipe_size"] <= 60:
            input_data["hot_water_supply_systems"][unit_name]["pipe_sizetype"] = "60A以下"
        elif input_data["hot_water_supply_systems"][unit_name]["pipe_size"] <= 75:
            input_data["hot_water_supply_systems"][unit_name]["pipe_sizetype"] = "75A以下"
        elif input_data["hot_water_supply_systems"][unit_name]["pipe_size"] <= 80:
            input_data["hot_water_supply_systems"][unit_name]["pipe_sizetype"] = "80A以下"
        elif input_data["hot_water_supply_systems"][unit_name]["pipe_size"] <= 100:
            input_data["hot_water_supply_systems"][unit_name]["pipe_sizetype"] = "100A以下"
        elif input_data["hot_water_supply_systems"][unit_name]["pipe_size"] <= 125:
            input_data["hot_water_supply_systems"][unit_name]["pipe_sizetype"] = "125A以下"
        else:
            input_data["hot_water_supply_systems"][unit_name]["pipe_sizetype"] = "125Aより大きい"

        # 線熱損失係数
        input_data["hot_water_supply_systems"][unit_name]["heatloss_coefficient"] = \
            thermal_conductivity_dict[input_data["hot_water_supply_systems"][unit_name]["pipe_sizetype"]][
                input_data["hot_water_supply_systems"][unit_name]["insulation_type"]]

        if DEBUG:
            print(f'機器名称 {unit_name}')
            print(f'  - 配管接続口径 {input_data["hot_water_supply_systems"][unit_name]["pipe_sizetype"]}')
            print(f'  - 線熱損失係数 {input_data["hot_water_supply_systems"][unit_name]["heatloss_coefficient"]}')

    # ----------------------------------------------------------------------------------
    # 解説書 D.6 日平均給水温度
    # ----------------------------------------------------------------------------------

    # 日平均外気温の算出
    toa_ave = np.mean(tout, 1)

    # 空調運転モード
    with open(database_directory + 'ac_operation_mode.json', 'r', encoding='utf-8') as f:
        ac_operation_mode = json.load(f)

    # 各日の冷暖房期間の種類（冷房期、暖房期、中間期）（365×1の行列）
    ac_mode = ac_operation_mode[area[input_data["building"]["region"] + "地域"]["空調運転モードタイプ"]]

    if input_data["building"]["region"] == '1' or input_data["building"]["region"] == '2':
        TWdata = 0.6639 * toa_ave + 3.466
    elif input_data["building"]["region"] == '3' or input_data["building"]["region"] == '4':
        TWdata = 0.6054 * toa_ave + 4.515
    elif input_data["building"]["region"] == '5':
        TWdata = 0.8660 * toa_ave + 1.665
    elif input_data["building"]["region"] == '6':
        TWdata = 0.8516 * toa_ave + 2.473
    elif input_data["building"]["region"] == '7':
        TWdata = 0.9223 * toa_ave + 2.097
    elif input_data["building"]["region"] == '8':
        TWdata = 0.6921 * toa_ave + 7.167

    # ----------------------------------------------------------------------------------
    # 解説書 5.2 日積算湯使用量
    # ----------------------------------------------------------------------------------

    # 各室熱源の容量比を求める。
    for room_name in input_data["hot_water_room"]:

        input_data["hot_water_room"][room_name]["rated_capacity_All"] = 0

        for unit_id, unit_configure in enumerate(input_data["hot_water_room"][room_name]["hot_water_system"]):
            input_data["hot_water_room"][room_name]["hot_water_system"][unit_id]["rated_capacity_total"] = \
                input_data["hot_water_supply_systems"][unit_configure["system_name"]]["rated_capacity_total"]

            input_data["hot_water_room"][room_name]["rated_capacity_All"] += \
                input_data["hot_water_room"][room_name]["hot_water_system"][unit_id]["rated_capacity_total"]

    for room_name in input_data["hot_water_room"]:

        for unit_id, unit_configure in enumerate(input_data["hot_water_room"][room_name]["hot_water_system"]):

            input_data["hot_water_room"][room_name]["hot_water_system"][unit_id]["roomPowerRatio"] = \
                input_data["hot_water_room"][room_name]["hot_water_system"][unit_id]["rated_capacity_total"] / \
                input_data["hot_water_room"][room_name]["rated_capacity_All"]

            if DEBUG:
                print(f'機器名称 {unit_id}')
                print(f'熱源比率 {input_data["hot_water_room"][room_name]["hot_water_system"][unit_id]["roomPowerRatio"]}')

    # 給湯対象室rの節湯器具による湯使用量削減効果を加味した日付dにおける室rの日積算湯使用量
    for unit_name in input_data["hot_water_supply_systems"]:

        input_data["hot_water_supply_systems"][unit_name]["Qsr_eqp_daily"] = np.zeros(365)
        input_data["hot_water_supply_systems"][unit_name]["qs_eqp_daily"] = np.zeros(365)

        for room_name in input_data["hot_water_room"]:
            for unit_id, unit_configure in enumerate(input_data["hot_water_room"][room_name]["hot_water_system"]):
                if unit_name == unit_configure["system_name"]:

                    # 標準日積算給湯量 [L/day] →　配管長さ算出に必要
                    input_data["hot_water_supply_systems"][unit_name]["Qsr_eqp_daily"] += \
                        input_data["hot_water_room"][room_name]["hotwater_demand_daily"] * unit_configure["roomPowerRatio"]

                    # 節湯効果を加味した日積算給湯量 [L/day]
                    # 係数は 解説書 附属書 D.3 節湯器具による湯使用量削減率
                    if unit_configure["hot_water_saving_system"] == "無":

                        input_data["hot_water_supply_systems"][unit_name]["qs_eqp_daily"] += \
                            input_data["hot_water_room"][room_name]["hotwater_demand_wasroom_enthalpy_setting_daily"] * 1.0 * \
                            unit_configure["roomPowerRatio"] + \
                            input_data["hot_water_room"][room_name]["hotwater_demand_shower_daily"] * 1.0 * unit_configure[
                                "roomPowerRatio"] + \
                            input_data["hot_water_room"][room_name]["hotwater_demand_kitchen_daily"] * 1.0 * \
                            unit_configure["roomPowerRatio"] + \
                            input_data["hot_water_room"][room_name]["hotwater_demand_other_daily"] * 1.0 * unit_configure[
                                "roomPowerRatio"]

                    elif unit_configure["hot_water_saving_system"] == "自動給湯栓":

                        input_data["hot_water_supply_systems"][unit_name]["qs_eqp_daily"] += \
                            input_data["hot_water_room"][room_name]["hotwater_demand_wasroom_enthalpy_setting_daily"] * 0.6 * \
                            unit_configure["roomPowerRatio"] + \
                            input_data["hot_water_room"][room_name]["hotwater_demand_shower_daily"] * 1.0 * unit_configure[
                                "roomPowerRatio"] + \
                            input_data["hot_water_room"][room_name]["hotwater_demand_kitchen_daily"] * 1.0 * \
                            unit_configure["roomPowerRatio"] + \
                            input_data["hot_water_room"][room_name]["hotwater_demand_other_daily"] * 1.0 * unit_configure[
                                "roomPowerRatio"]

                    elif unit_configure["hot_water_saving_system"] == "節湯B1":

                        input_data["hot_water_supply_systems"][unit_name]["qs_eqp_daily"] += \
                            input_data["hot_water_room"][room_name]["hotwater_demand_wasroom_enthalpy_setting_daily"] * 1.0 * \
                            unit_configure["roomPowerRatio"] + \
                            input_data["hot_water_room"][room_name]["hotwater_demand_shower_daily"] * 0.75 * \
                            unit_configure["roomPowerRatio"] + \
                            input_data["hot_water_room"][room_name]["hotwater_demand_kitchen_daily"] * 1.0 * \
                            unit_configure["roomPowerRatio"] + \
                            input_data["hot_water_room"][room_name]["hotwater_demand_other_daily"] * 1.0 * unit_configure[
                                "roomPowerRatio"]

        if DEBUG:
            print(f'機器名称 {unit_name}')
            print(f'  - 日積算湯供給量 {np.sum(input_data["hot_water_supply_systems"][unit_name]["Qsr_eqp_daily"])}')
            print(
                f'  - 日積算湯供給量（節湯込み） {np.sum(input_data["hot_water_supply_systems"][unit_name]["qs_eqp_daily"])}')

    # ----------------------------------------------------------------------------------
    # 解説書 5.3 配管長さ
    # ----------------------------------------------------------------------------------

    for unit_name in input_data["hot_water_supply_systems"]:

        input_data["hot_water_supply_systems"][unit_name]["L_eqp"] = \
            np.max(input_data["hot_water_supply_systems"][unit_name]["Qsr_eqp_daily"]) * 7 / 1000

        if DEBUG:
            print(f'機器名称 {unit_name}')
            print(f'  - 配管長さ {input_data["hot_water_supply_systems"][unit_name]["L_eqp"]}')

    # ----------------------------------------------------------------------------------
    # 解説書 5.4 年間配管熱損失量
    # ----------------------------------------------------------------------------------

    # 室内設定温度
    Troom = np.zeros(365)
    Taround = np.zeros(365)

    for dd in range(0, 365):
        if ac_mode[dd] == "冷房":
            Troom[dd] = 26
        elif ac_mode[dd] == "中間":
            Troom[dd] = 24
        elif ac_mode[dd] == "暖房":
            Troom[dd] = 22

    # 配管熱損失 [kJ/day]
    for unit_name in input_data["hot_water_supply_systems"]:

        input_data["hot_water_supply_systems"][unit_name]["qp_eqp"] = np.zeros(365)

        for dd in range(0, 365):

            # デバッグ出力用
            Taround[dd] = (toa_ave[dd] + Troom[dd]) / 2

            if input_data["hot_water_supply_systems"][unit_name]["qs_eqp_daily"][dd] > 0:
                input_data["hot_water_supply_systems"][unit_name]["qp_eqp"][dd] = \
                    input_data["hot_water_supply_systems"][unit_name]["L_eqp"] * \
                    input_data["hot_water_supply_systems"][unit_name]["heatloss_coefficient"] * \
                    (60 - (toa_ave[dd] + Troom[dd]) / 2) * 24 * 3600 * 0.001

        if DEBUG:
            print(f'機器名称 {unit_name}')
            print(f'  - 配管熱損失 {np.sum(input_data["hot_water_supply_systems"][unit_name]["qp_eqp"])}')
            print(f'  - 配管熱損失係数 {input_data["hot_water_supply_systems"][unit_name]["heatloss_coefficient"]}')

            # np.savetxt("配管周囲温度.txt", Taround)

    # ----------------------------------------------------------------------------------
    # 解説書 5.5 太陽熱利用システムの熱利用量
    # ----------------------------------------------------------------------------------

    for unit_name in input_data["hot_water_supply_systems"]:

        # 太陽熱利用量 [KJ/day]
        input_data["hot_water_supply_systems"][unit_name]["qs_solar_gain"] = np.zeros(365)

        if (input_data["hot_water_supply_systems"][unit_name]["solar_system_area"] != "") and (
                input_data["hot_water_supply_systems"][unit_name]["solar_system_area"] is not None):
            # 日積算日射量 [Wh/m2/day]
            Id, _, Is, _ = climate.solar_radiation_by_azimuth( \
                input_data["hot_water_supply_systems"][unit_name]["solar_system_direction"], \
                input_data["hot_water_supply_systems"][unit_name]["solar_system_angle"], \
                area[input_data["building"]["region"] + "地域"]["緯度"], \
                area[input_data["building"]["region"] + "地域"]["経度"], \
                iod, ios, inn)

            # 太陽熱利用量 [KJ/day]
            input_data["hot_water_supply_systems"][unit_name]["qs_solar_gain"] = \
                (input_data["hot_water_supply_systems"][unit_name]["solar_system_area"] * 0.4 * 0.85) * \
                (Id + Is) * 3600 / 1000000 * 1000

        if DEBUG:
            print(f'機器名称 {unit_name}')
            print(
                f'  - 太陽熱利用システムの熱利用量 {np.sum(input_data["hot_water_supply_systems"][unit_name]["qs_solar_gain"])}')

    # ----------------------------------------------------------------------------------
    # 解説書 5.6 年間給湯負荷
    # ----------------------------------------------------------------------------------

    for unit_name in input_data["hot_water_supply_systems"]:

        input_data["hot_water_supply_systems"][unit_name]["qh_eqp_daily"] = np.zeros(365)

        if input_data["hot_water_supply_systems"][unit_name]["solar_system_area"] is None:

            # 太陽熱利用が無い場合
            input_data["hot_water_supply_systems"][unit_name]["qh_eqp_daily"] = \
                4.2 * input_data["hot_water_supply_systems"][unit_name]["qs_eqp_daily"] * (43 - TWdata)

        else:

            # 太陽熱利用がある場合
            tmp_qh = 4.2 * input_data["hot_water_supply_systems"][unit_name]["qs_eqp_daily"] * (43 - TWdata)

            for dd in range(0, 365):
                if (toa_ave[dd] > 5) and (tmp_qh[dd] > 0):  # 日平均外気温が５度を超えていれば集熱

                    if tmp_qh[dd] * 0.1 > (
                            tmp_qh[dd] - input_data["hot_water_supply_systems"][unit_name]["qs_solar_gain"][dd]):

                        input_data["hot_water_supply_systems"][unit_name]["qh_eqp_daily"][dd] = tmp_qh[dd] * 0.1

                    else:
                        input_data["hot_water_supply_systems"][unit_name]["qh_eqp_daily"][dd] = \
                            tmp_qh[dd] - input_data["hot_water_supply_systems"][unit_name]["qs_solar_gain"][dd]

                else:
                    input_data["hot_water_supply_systems"][unit_name]["qh_eqp_daily"][dd] = tmp_qh[dd]

        if DEBUG:
            print(f'機器名称 {unit_name}')
            print(f'  - 日積算給湯負荷 {np.sum(input_data["hot_water_supply_systems"][unit_name]["qh_eqp_daily"])}')

    # ----------------------------------------------------------------------------------
    # 解説書 5.7 給湯設備の設計一次エネルギー消費量
    # ----------------------------------------------------------------------------------

    for unit_name in input_data["hot_water_supply_systems"]:

        # 日別給湯負荷＋配管熱損失（＝給湯加熱負荷） [kJ/day]
        input_data["hot_water_supply_systems"][unit_name]["Q_eqp"] = \
            input_data["hot_water_supply_systems"][unit_name]["qh_eqp_daily"] + \
            input_data["hot_water_supply_systems"][unit_name]["qp_eqp"] * 2.5

        # 日別消費エネルギー消費量 [kJ/day]
        input_data["hot_water_supply_systems"][unit_name]["E_eqp"] = \
            input_data["hot_water_supply_systems"][unit_name]["Q_eqp"] / input_data["hot_water_supply_systems"][unit_name][
                "RatedEfficiency_total"]

        # 設計一次エネルギー消費量 [MJ/day]
        result_json["設計一次エネルギー消費量[MJ/年]"] += np.sum(
            input_data["hot_water_supply_systems"][unit_name]["E_eqp"]) / 1000

        if DEBUG:
            print(f'機器名称 {unit_name}')
            print(f'  - 日別給湯負荷と配管熱損失 {np.sum(input_data["hot_water_supply_systems"][unit_name]["Q_eqp"])}')
            print(f'  - 日別消費エネルギー消費量 {np.sum(input_data["hot_water_supply_systems"][unit_name]["E_eqp"])}')

    if DEBUG:
        print(f'設計一次エネルギー消費量 {result_json["設計一次エネルギー消費量[MJ/年]"]} MJ/年')

    # ----------------------------------------------------------------------------------
    # 結果の保存
    # ----------------------------------------------------------------------------------

    for unit_name in input_data["hot_water_supply_systems"]:
        result_json["hot_water_supply_systems"][unit_name] = input_data["hot_water_supply_systems"][unit_name]

        result_json["hot_water_supply_systems"][unit_name]["湯使用量（節湯込）[L/年]"] = np.sum(
            input_data["hot_water_supply_systems"][unit_name]["qs_eqp_daily"] / 1000)
        result_json["hot_water_supply_systems"][unit_name]["太陽熱利用量[MJ/年]"] = np.sum(
            input_data["hot_water_supply_systems"][unit_name]["qs_solar_gain"] / 1000)
        result_json["hot_water_supply_systems"][unit_name]["給湯加熱負荷[MJ/年]"] = np.sum(
            input_data["hot_water_supply_systems"][unit_name]["Q_eqp"] / 1000)
        result_json["hot_water_supply_systems"][unit_name]["配管熱損失[MJ/年]"] = np.sum(
            input_data["hot_water_supply_systems"][unit_name]["qp_eqp"] / 1000)
        result_json["hot_water_supply_systems"][unit_name]["設計一次エネルギー消費量[MJ/年]"] = np.sum(
            input_data["hot_water_supply_systems"][unit_name]["E_eqp"] / 1000)

        # 初期化　→ 次の処理で値を代入
        result_json["hot_water_supply_systems"][unit_name]["基準一次エネルギー消費量[MJ/年]"] = 0

    # ----------------------------------------------------------------------------------
    # 解説書 10.4 給湯設備の基準一次エネルギー消費量
    # ----------------------------------------------------------------------------------

    result_json["基準一次エネルギー消費量[MJ/年]"] = 0
    for room_name in input_data["hot_water_room"]:

        # 建物用途、室用途（可読性重視で一旦変数に代入する）
        building_type = input_data["rooms"][room_name]["building_type"]
        room_type = input_data["rooms"][room_name]["room_type"]

        # 　計算対象面積[m2]
        result_json["計算対象面積"] += input_data["rooms"][room_name]["room_area"]

        input_data["hot_water_room"][room_name]["基準一次エネルギー消費量[MJ/年]"] = \
            bc.room_standard_value[building_type][room_type]["給湯"][input_data["building"]["region"] + "地域"] * \
            input_data["rooms"][room_name]["room_area"]

        # 積算する
        result_json["基準一次エネルギー消費量[MJ/年]"] += input_data["hot_water_room"][room_name]["基準一次エネルギー消費量[MJ/年]"]

        # 熱源単位に振り分け（参考情報）
        for unit_id, unit_configure in enumerate(input_data["hot_water_room"][room_name]["hot_water_system"]):
            unit_name = unit_configure["system_name"]

            result_json["hot_water_supply_systems"][unit_name]["基準一次エネルギー消費量[MJ/年]"] += \
                input_data["hot_water_room"][room_name]["基準一次エネルギー消費量[MJ/年]"] * unit_configure["roomPowerRatio"]

    # BEI/hW
    result_json["BEI/hW"] = result_json["設計一次エネルギー消費量[MJ/年]"] / result_json["基準一次エネルギー消費量[MJ/年]"]
    result_json["BEI/hW"] = math.ceil(result_json["BEI/hW"] * 100) / 100

    result_json["設計一次エネルギー消費量[GJ/年]"] = result_json["設計一次エネルギー消費量[MJ/年]"] / 1000
    result_json["基準一次エネルギー消費量[GJ/年]"] = result_json["基準一次エネルギー消費量[MJ/年]"] / 1000
    result_json["設計一次エネルギー消費量[MJ/m2年]"] = result_json["設計一次エネルギー消費量[MJ/年]"] / result_json["計算対象面積"]
    result_json["基準一次エネルギー消費量[MJ/m2年]"] = result_json["基準一次エネルギー消費量[MJ/年]"] / result_json["計算対象面積"]

    for unit_name in input_data["hot_water_supply_systems"]:
        result_json["hot_water_supply_systems"][unit_name]["設計値/基準値"] = \
            result_json["hot_water_supply_systems"][unit_name]["設計一次エネルギー消費量[MJ/年]"] / \
            result_json["hot_water_supply_systems"][unit_name]["基準一次エネルギー消費量[MJ/年]"]

    # ----------------------------------------------------------------------------------
    # CGS計算用変数 （解説書 ８章 附属書 G.10 他の設備の計算結果の読み込み）
    # ----------------------------------------------------------------------------------

    Edesign_MWh_Ele_hour = np.zeros((365, 24))
    Edesign_MJ_CGS_hour = np.zeros((365, 24))
    Q_eqp_CGS_hour = np.zeros((365, 24))

    if len(input_data["cogeneration_systems"]) == 1:  # コジェネがあれば実行

        for cgs_name in input_data["cogeneration_systems"]:

            # コジェネ系統にない給湯設備の電力消費量を積算
            for unit_name in input_data["hot_water_supply_systems"]:

                if input_data["cogeneration_systems"][cgs_name]["hot_water_system"] != "" and \
                        input_data["cogeneration_systems"][cgs_name]["hot_water_system"] == unit_name:

                    # コジェネの排熱利用先であれば
                    for dd in range(0, 365):
                        Edesign_MJ_CGS_hour[dd] += input_data["hot_water_supply_systems"][unit_name]["E_eqp"][
                                                       dd] / 24 / 1000 * np.ones(24)
                        Q_eqp_CGS_hour[dd] += input_data["hot_water_supply_systems"][unit_name]["Q_eqp"][
                                                  dd] / 24 / 1000 * np.ones(24)

                else:

                    # コジェネの排熱利用先以外であれば
                    for unit_id, unit_configure in enumerate(
                            input_data["hot_water_supply_systems"][unit_name]["heat_sourceUnit"]):

                        if unit_configure["usage_type"] == "給湯負荷用":
                            if unit_configure["heat_source_type"] == "電気瞬間湯沸器" or unit_configure[
                                "heat_source_type"] == "貯湯式電気温水器" or \
                                    unit_configure["heat_source_type"] == "業務用ヒートポンプ給湯機" or unit_configure[
                                "heat_source_type"] == "家庭用ヒートポンプ給湯機":

                                for dd in range(0, 365):
                                    Edesign_MWh_Ele_hour[dd] += input_data["hot_water_supply_systems"][unit_name]["E_eqp"][
                                                                    dd] / 24 / 1000 / 9760 * np.ones(24)

        result_json["for_cgs"]["edesign_mwh_ele_day"] = np.sum(Edesign_MWh_Ele_hour, 1)
        result_json["for_cgs"]["Edesign_MJ_CGS_day"] = np.sum(Edesign_MJ_CGS_hour, 1)
        result_json["for_cgs"]["Q_eqp_CGS_day"] = np.sum(Q_eqp_CGS_hour, 1)

    ##----------------------------------------------------------------------------------
    # 不要な要素を削除
    ##----------------------------------------------------------------------------------

    for unit_id, isys in result_json["hot_water_supply_systems"].items():
        del result_json["hot_water_supply_systems"][unit_id]["Qsr_eqp_daily"]
        del result_json["hot_water_supply_systems"][unit_id]["qs_eqp_daily"]
        del result_json["hot_water_supply_systems"][unit_id]["L_eqp"]
        del result_json["hot_water_supply_systems"][unit_id]["qp_eqp"]
        del result_json["hot_water_supply_systems"][unit_id]["qs_solar_gain"]
        del result_json["hot_water_supply_systems"][unit_id]["qh_eqp_daily"]
        del result_json["hot_water_supply_systems"][unit_id]["Q_eqp"]
        del result_json["hot_water_supply_systems"][unit_id]["E_eqp"]

    return result_json


# %%
if __name__ == '__main__':
    print('----- hotwatersupply.py -----')
    # filename = './sample/CGS_case_office_00.json'
    filename = './sample/Builelib_sample_SP11.json'

    # 入力データ（json）の読み込み
    with open(filename, 'r', encoding='utf-8') as f:
        input_data = json.load(f)

    result_json = calc_energy(input_data, DEBUG=True)

    with open("result_json_HW.json", 'w', encoding='utf-8') as fw:
        json.dump(result_json, fw, indent=4, ensure_ascii=False, cls=bc.MyEncoder)
