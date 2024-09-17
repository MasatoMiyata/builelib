import json
import os
import sys

import numpy as np

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import commons as bc

# データベースファイルの保存場所
database_directory = os.path.dirname(os.path.abspath(__file__)) + "/database/"


def calc_energy(input_data, DEBUG=False):
    # 計算結果を格納する変数
    result_json = {
        "E_other": 0,  # 基準一次エネルギー消費量 [MJ]
        "E_other_room": {},
        "for_cgs": {
            "Edesign_MWh_day": np.zeros(365),
            "ratio_area_weighted_schedule_AC": np.zeros((365, 24)),  # 空調
            "ratio_area_weighted_schedule_LT": np.zeros((365, 24)),  # 照明
            "ratio_area_weighted_schedule_OA": np.zeros((365, 24))  # 機器発熱
        }
    }

    ##----------------------------------------------------------------------------------
    ## その他一次エネルギー消費量の原単位を求める（整数で丸める）
    ##----------------------------------------------------------------------------------

    # 機器発熱スケジュールを抽出
    room_schedule_room = {}
    room_schedule_light = {}
    room_schedule_person = {}
    room_schedule_oa_app = {}
    room_heat_gain_oaapp = {}

    for room_name in input_data["rooms"]:

        result_json["E_other_room"][room_name] = {
            "E_other_standard": 0,  # 告示の値 [MJ/m2]
            "E_other": 0,  # その他一次エネルギー消費量 [MJ/年]
            "E_ratio": 1,
            "room_heat_gain_daily": np.zeros(365)  # 日別の機器発熱量 [MJ/m2/day]
        }

        ##----------------------------------------------------------------------------------
        ## 任意評定 （SP-6: カレンダーパターン)
        ##----------------------------------------------------------------------------------
        input_calendar = []
        if "calender" in input_data["special_input_data"]:
            input_calendar = input_data["special_input_data"]["calender"]

        ##----------------------------------------------------------------------------------
        ## 任意評定 （SP-9: 室使用条件)
        ##----------------------------------------------------------------------------------
        input_room_usage_condition = {}
        if "room_usage_condition" in input_data["special_input_data"]:
            input_room_usage_condition = input_data["special_input_data"]["room_usage_condition"]

        # 365日×24時間分のスケジュール （365×24の行列を格納した dict型）
        if input_data["rooms"][room_name]["building_type"] == "共同住宅":

            # 共同住宅共用部は 0 とする。
            room_schedule_room[room_name] = np.zeros((365, 24))
            room_schedule_light[room_name] = np.zeros((365, 24))
            room_schedule_person[room_name] = np.zeros((365, 24))
            room_schedule_oa_app[room_name] = np.zeros((365, 24))
            room_heat_gain_oaapp[room_name] = 0

        else:

            # 標準室使用条件から時刻別の発熱密度比率（0～1。365×24の行列）を作成。SP-6に入力がある場合、任意のカレンダーを反映。
            room_schedule_room[room_name], room_schedule_light[room_name], room_schedule_person[room_name], room_schedule_oa_app[
                room_name], _ = \
                bc.get_room_usage_schedule(input_data["rooms"][room_name]["building_type"],
                                         input_data["rooms"][room_name]["room_type"], input_calendar)

            # 機器発熱量参照値 [W/m2]の読み込み。SP-9に入力がある場合、任意の値を使用。
            (_, _, room_heat_gain_oaapp[room_name], _) = \
                bc.get_room_heat_gain(input_data["rooms"][room_name]["building_type"],
                                    input_data["rooms"][room_name]["room_type"], input_room_usage_condition)

            ##----------------------------------------------------------------------------------
            ## 任意評定 （SP-7: 室スケジュール)
            ##----------------------------------------------------------------------------------
            if "room_schedule" in input_data["special_input_data"]:

                # SP-7に入力されていれば、時刻別の発熱密度比率を上書きする。
                if room_name in input_data["special_input_data"]["room_schedule"]:

                    if "室の同時使用率" in input_data["special_input_data"]["room_schedule"][room_name]["schedule"]:
                        room_schedule_room_tmp = np.array(
                            input_data["special_input_data"]["room_schedule"][room_name]["schedule"][
                                "室の同時使用率"]).astype("float")
                        room_schedule_room_tmp = np.where(room_schedule_room_tmp < 1, 0, room_schedule_room_tmp)  # 同時使用率は考えない
                        room_schedule_room[room_name] = room_schedule_room_tmp
                    if "照明発熱密度比率" in input_data["special_input_data"]["room_schedule"][room_name]["schedule"]:
                        room_schedule_light[room_name] = np.array(
                            input_data["special_input_data"]["room_schedule"][room_name]["schedule"]["照明発熱密度比率"])
                    if "人体発熱密度比率" in input_data["special_input_data"]["room_schedule"][room_name]["schedule"]:
                        room_schedule_person[room_name] = np.array(
                            input_data["special_input_data"]["room_schedule"][room_name]["schedule"]["人体発熱密度比率"])
                    if "機器発熱密度比率" in input_data["special_input_data"]["room_schedule"][room_name]["schedule"]:
                        room_schedule_oa_app[room_name] = np.array(
                            input_data["special_input_data"]["room_schedule"][room_name]["schedule"]["機器発熱密度比率"])

        if room_heat_gain_oaapp[room_name] is not None:

            # 機器からの発熱（日積算）（365日分） [MJ/m2/day]
            result_json["E_other_room"][room_name]["room_heat_gain_daily"] = \
                np.sum(room_schedule_oa_app[room_name], 1) * room_heat_gain_oaapp[room_name] / 1000000 * bc.fprime

            # その他一次エネルギー消費量原単位（告示の値） [MJ/m2] の算出（端数処理）
            result_json["E_other_room"][room_name]["E_other_standard"] = \
                round(np.sum(result_json["E_other_room"][room_name]["room_heat_gain_daily"]))

            # 年積算値（端数調整前）が告示の値と一致するように補正する係数を求める（コジェネ計算時に日別消費電力を年積算値と一致させるために必要）。
            if np.sum(result_json["E_other_room"][room_name]["room_heat_gain_daily"]) == 0:
                result_json["E_other_room"][room_name]["E_ratio"] = 1
            else:
                result_json["E_other_room"][room_name]["E_ratio"] = \
                    result_json["E_other_room"][room_name]["E_other_standard"] / np.sum(
                        result_json["E_other_room"][room_name]["room_heat_gain_daily"])

        if DEBUG:
            print(f'室名: {room_name}')
            print(f'その他一次エネ原単位 MJ/m2 : {result_json["E_other_room"][room_name]["E_other_standard"]}')
            print(f'補正係数 E_ratio : {result_json["E_other_room"][room_name]["E_ratio"]}')

    ##----------------------------------------------------------------------------------
    ## その他一次エネルギー消費量
    ##----------------------------------------------------------------------------------
    for room_name in input_data["rooms"]:
        # その他一次エネルギー消費量 [MJ]
        result_json["E_other_room"][room_name]["E_other"] = \
            result_json["E_other_room"][room_name]["E_other_standard"] * input_data["rooms"][room_name]["room_area"]

        result_json["E_other"] += result_json["E_other_room"][room_name]["E_other"]

        # 日別の電力消費量（告示に掲載の年積算値と一致させるために E_ratio で一律補正する）
        result_json["for_cgs"]["Edesign_MWh_day"] += \
            result_json["E_other_room"][room_name]["room_heat_gain_daily"] * input_data["rooms"][room_name]["room_area"] * \
            result_json["E_other_room"][room_name]["E_ratio"] / bc.fprime

    ##----------------------------------------------------------------------------------
    # コジェネ計算用のスケジュール
    ##----------------------------------------------------------------------------------
    area_weighted_schedule_AC = np.zeros((365, 24))
    area_weighted_schedule_LT = np.zeros((365, 24))
    area_weighted_schedule_OA = np.zeros((365, 24))

    # 空調スケジュール
    for room_zone_name in input_data["air_conditioning_zone"]:
        if room_zone_name in input_data["rooms"]:  # ゾーン分けがない場合

            area_weighted_schedule_AC += room_schedule_room[room_zone_name] * input_data["rooms"][room_zone_name]["room_area"]

        else:

            # 各室のゾーンを検索
            for room_name in input_data["rooms"]:
                if input_data["rooms"][room_name]["zone"] is not None:  # ゾーンがあれば
                    for zone_name in input_data["rooms"][room_name]["zone"]:  # ゾーン名を検索
                        if room_zone_name == (room_name + "_" + zone_name):
                            area_weighted_schedule_AC += room_schedule_room[room_name] * \
                                                       input_data["rooms"][room_name]["zone"][zone_name]["zone_area"]

    # 照明スケジュール
    for room_zone_name in input_data["lighting_systems"]:
        if room_zone_name in input_data["rooms"]:  # ゾーン分けがない場合

            area_weighted_schedule_LT += room_schedule_light[room_zone_name] * input_data["rooms"][room_zone_name][
                "room_area"]

        else:

            # 各室のゾーンを検索
            for room_name in input_data["rooms"]:
                if input_data["rooms"][room_name]["zone"] is not None:  # ゾーンがあれば
                    for zone_name in input_data["rooms"][room_name]["zone"]:  # ゾーン名を検索
                        if room_zone_name == (room_name + "_" + zone_name):
                            area_weighted_schedule_LT += room_schedule_light[room_name] * \
                                                       input_data["rooms"][room_name]["zone"][zone_name]["zone_area"]

                            # 機器発熱スケジュール
    for room_name in input_data["rooms"]:
        area_weighted_schedule_OA += room_schedule_oa_app[room_name] * input_data["rooms"][room_name]["room_area"]

    for dd in range(0, 365):
        if np.sum(area_weighted_schedule_AC[dd]) != 0:
            result_json["for_cgs"]["ratio_area_weighted_schedule_AC"][dd] = \
                area_weighted_schedule_AC[dd] / np.sum(area_weighted_schedule_AC[dd])
        if np.sum(area_weighted_schedule_LT[dd]) != 0:
            result_json["for_cgs"]["ratio_area_weighted_schedule_LT"][dd] = \
                area_weighted_schedule_LT[dd] / np.sum(area_weighted_schedule_LT[dd])
        if np.sum(area_weighted_schedule_OA[dd]) != 0:
            result_json["for_cgs"]["ratio_area_weighted_schedule_OA"][dd] = \
                area_weighted_schedule_OA[dd] / np.sum(area_weighted_schedule_OA[dd])

    if DEBUG:
        print(f'その他一次エネルギー消費量 MJ: {result_json["E_other"]}')

    ##----------------------------------------------------------------------------------
    # 不要な要素を削除
    ##----------------------------------------------------------------------------------

    for room_id, isys in result_json["E_other_room"].items():
        del result_json["E_other_room"][room_id]["room_heat_gain_daily"]

    return result_json


if __name__ == '__main__':
    print('----- other_energy.py -----')
    filename = './sample/WEBPRO_inputSheet_sample.json'

    # 入力ファイルの読み込み
    with open(filename, 'r', encoding='utf-8') as f:
        input_data = json.load(f)

    result_json = calc_energy(input_data, DEBUG=True)

    with open("result_json_OT.json", 'w', encoding='utf-8') as fw:
        json.dump(result_json, fw, indent=4, ensure_ascii=False, cls=bc.MyEncoder)
