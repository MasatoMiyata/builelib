import csv
import json

import pytest

from builelib import airconditioning

### テストファイル名 ###
# 辞書型 テスト名とファイル名

testcase_dict = {
    "basic_test": "./tests/airconditioning_load/負荷_基本テスト.txt",
    "detail_test": "./tests/airconditioning_load/負荷_詳細テスト.txt",
}


def convert2number(x, default):
    '''
    空欄にデフォルト値を代入する
    '''
    if x == "":
        x = default
    else:
        x = float(x)
    return x


def read_testcasefile(filename):
    '''
    テストケースファイルを読み込む関数
    '''
    with open(filename, mode='r', newline='', encoding='shift-jis') as f:
        tsv_reader = csv.reader(f, delimiter=',')
        testdata = [row for row in tsv_reader]
    return testdata


def make_input_data(data):
    if data[2] == "物品販売業を営む店舗等":
        data[2] = "物販店舗等"

    if data[6] == "外壁":
        data[6] = "日の当たる外壁"
    elif data[6] == "接地壁":
        data[6] = "地盤に接する外壁_Ver2"

    if data[7] == "水平":
        data[7] = "水平（上）"

    input_data = {
        "building": {
            "region": str(data[1]),
            "coefficient_dhc": {
                "cooling": 1.36,
                "heating": 1.36
            },
        },
        "rooms": {
            "1F_room1": {
                "floorname": "1F",
                "roomname": "room1",
                "building_type": data[2],
                "room_type": data[3],
                "room_area": convert2number(data[4], None),
                "zone": None,
            }
        },
        "envelope_set": {
            "1F_room1": {
                "is_airconditioned": "有",
                "wall_list": [
                    {
                        "direction": data[7],
                        "envelope_area": convert2number(data[10], None),
                        "envelope_width": None,
                        "envelope_height": None,
                        "wall_spec": "OW1",
                        "wall_type": data[6],
                        "window_list": [
                            {
                                "window_id": "WIND1",
                                "window_number": 1,
                                "is_blind": "無",
                                "eaves_id": "日よけ1",
                                "info": "無"
                            }
                        ]
                    }
                ]
            }
        },
        "wall_configure": {
            "OW1": {
                "structure_type": "木造",
                "solar_absorption_ratio": None,
                "input_method": "熱貫流率を入力",
                "u_value": convert2number(data[12], None),
                "info": "無"
            }
        },
        "window_configure": {
            "WIND1": {
                "window_area": convert2number(data[11], None),
                "window_width": None,
                "window_height": None,
                "input_method": "性能値を入力",
                "windowu_value": convert2number(data[13], None),
                "windowi_value": convert2number(data[14], None),
                "layer_type": "単層",
                "glassu_value": None,
                "glassi_value": None,
                "info": "無"
            }
        },
        "shading_config": {
            "日よけ1": {
                "shading_effect_C": convert2number(data[8], None),
                "shading_effect_H": convert2number(data[9], None),
                "x1": None,
                "x2": None,
                "x3": None,
                "y1": None,
                "y2": None,
                "y3": None,
                "zxplus": None,
                "zxminus": None,
                "zyplus": None,
                "zyminus": None,
                "info": "無"
            },
        },
        "air_conditioning_zone": {
            "1F_room1": {
                "is_natual_ventilation": "無",
                "is_simultaneous_supply": "無",
                "ahu_cooling_inside_load": "ACP1",
                "ahu_cooling_outdoor_load": "ACP1",
                "ahu_heating_inside_load": "ACP1",
                "ahu_heating_outdoor_load": "ACP1",
                "info": ""
            }
        },
        "heat_source_system": {
            "PAC1": {
                "冷房": {
                    "storage_type": None,
                    "storage_size": None,
                    "is_staging_control": "有",
                    "heat_source": [
                        {
                            "heat_source_type": "パッケージエアコンディショナ(空冷式)",
                            "number": 1.0,
                            "supply_water_temp_summer": 7.0,
                            "supply_water_temp_middle": 11.0,
                            "supply_water_temp_winter": 16.0,
                            "heat_source_rated_capacity": 22.4,
                            "heat_source_rated_power_consumption": 6.0,
                            "heat_source_rated_fuel_consumption": 0,
                            "primary_pump_power_consumption": 0,
                            "primary_pump_control_type": "無",
                            "cooling_tower_capacity": 0,
                            "cooling_tower_fan_power_consumption": 0,
                            "cooling_tower_pump_power_consumption": 0,
                            "cooling_tower_control_type": "無",
                            "info": ""
                        }
                    ]
                },
                "暖房": {
                    "storage_type": None,
                    "storage_size": None,
                    "is_staging_control": "有",
                    "heat_source": [
                        {
                            "heat_source_type": "パッケージエアコンディショナ(空冷式)",
                            "number": 1.0,
                            "supply_water_temp_summer": 40,
                            "supply_water_temp_middle": 40,
                            "supply_water_temp_winter": 40,
                            "heat_source_rated_capacity": 22.4,
                            "heat_source_rated_power_consumption": 5,
                            "heat_source_rated_fuel_consumption": 0,
                            "primary_pump_power_consumption": 0,
                            "primary_pump_control_type": "無",
                            "cooling_tower_capacity": 0,
                            "cooling_tower_fan_power_consumption": 0,
                            "cooling_tower_pump_power_consumption": 0,
                            "cooling_tower_control_type": "無",
                            "info": ""
                        }
                    ]
                }
            },
        },
        "secondary_pump_system": {
        },
        "air_handling_system": {
            "ACP1": {
                "is_economizer": "無",
                "economizer_max_air_volume": None,
                "is_outdoor_air_cut": "無",
                "pump_cooling": None,
                "pump_heating": None,
                "HeatSorce_cooling": "PAC1",
                "HeatSorce_heating": "PAC1",
                "air_handling_unit": [
                    {
                        "type": "室内機",
                        "number": 1.0,
                        "rated_capacity_cooling": 22,
                        "rated_capacity_heating": 24,
                        "fan_type": "給気",
                        "fan_air_volume": 3000.0,
                        "fan_power_consumption": 2.2,
                        "fan_control_type": "回転数制御",
                        "fan_min_opening_rate": 80.0,
                        "air_heat_exchange_ratio_cooling": None,
                        "air_heat_exchange_ratio_heating": None,
                        "AirHeatExchangerEffectiveAirVolume": None,
                        "air_heat_exchanger_control": "無",
                        "air_heat_exchanger_power_consumption": None,
                        "info": ""
                    }
                ]
            }
        }
    }

    if data[15] != "":

        if data[15] == "外壁":
            data[15] = "日の当たる外壁"
        elif data[15] == "接地壁":
            data[15] = "地盤に接する外壁_Ver2"

        if data[16] == "水平":
            data[16] = "水平（上）"

        input_data["envelope_set"]["1F_room1"]["wall_list"].append(
            {
                "direction": data[16],
                "envelope_area": convert2number(data[19], None),
                "envelope_width": None,
                "envelope_height": None,
                "wall_spec": "OW2",
                "wall_type": data[15],
                "window_list": [
                    {
                        "window_id": "WIND2",
                        "window_number": 1,
                        "is_blind": "無",
                        "eaves_id": "日よけ2",
                        "info": "無"
                    }
                ]
            }
        )
        input_data["wall_configure"]["OW2"] = {
            "structure_type": "木造",
            "solar_absorption_ratio": None,
            "input_method": "熱貫流率を入力",
            "u_value": convert2number(data[21], None),
            "info": "無"
        }
        input_data["window_configure"]["WIND2"] = {
            "window_area": convert2number(data[20], None),
            "window_width": None,
            "window_height": None,
            "input_method": "性能値を入力",
            "windowu_value": convert2number(data[22], None),
            "windowi_value": convert2number(data[23], None),
            "layer_type": "単層",
            "glassu_value": None,
            "glassi_value": None,
            "info": "無"
        }
        input_data["shading_config"]["日よけ2"] = {
            "shading_effect_C": convert2number(data[17], None),
            "shading_effect_H": convert2number(data[18], None),
            "x1": None,
            "x2": None,
            "x3": None,
            "y1": None,
            "y2": None,
            "y3": None,
            "zxplus": None,
            "zxminus": None,
            "zyplus": None,
            "zyminus": None,
            "info": "無"
        }

    return input_data


#### テストケースファイルの読み込み（換気送風機）

test_to_try = []  # テスト用入力ファイルと期待値のリスト
testcase_id = []  # テスト名称のリスト

for case_name in testcase_dict:

    # テストファイルの読み込み
    testfiledata = read_testcasefile(testcase_dict[case_name])

    # ヘッダーの削除
    testfiledata.pop(0)

    # テストケース（行）に対するループ
    for testdata in testfiledata:
        # 入力データの作成
        input_data = make_input_data(testdata)
        # 期待値
        expectedvalue = (testdata[24], testdata[25])

        # テストケースの集約
        test_to_try.append((input_data, expectedvalue))
        # テストケース名
        testcase_id.append(case_name + testdata[0])


# テストの実施
@pytest.mark.parametrize('input_data, expectedvalue', test_to_try, ids=testcase_id)
def test_calc(input_data, expectedvalue):
    # 検証用
    with open("input_data.json", 'w', encoding='utf-8') as fw:
        json.dump(input_data, fw, indent=4, ensure_ascii=False)

    if expectedvalue[0] != "err":  # passが期待されるテスト

        # 計算実行        
        result_json = airconditioning.calc_energy(input_data)

        if convert2number(expectedvalue[0], 0) == 0:
            diff_Dc = 0
        else:
            diff_Dc = (abs(
                result_json["q_room"]["1F_room1"]["q_room_daily_cooling_anual"] - convert2number(expectedvalue[0], 0))) / abs(
                convert2number(expectedvalue[0], 0))

        if convert2number(expectedvalue[1], 0) == 0:
            diff_Dh = 0
        else:
            diff_Dh = (abs(
                result_json["q_room"]["1F_room1"]["q_room_daily_heating_anual"] - convert2number(expectedvalue[1], 0))) / abs(
                convert2number(expectedvalue[1], 0))

        # 比較（0.01%まで）
        assert diff_Dc < 0.0001
        assert diff_Dh < 0.0001

    else:

        # エラーが期待される場合
        with pytest.raises(Exception):
            result_json = airconditioning.calc_energy(input_data)


if __name__ == '__main__':
    print('--- test_airconditioning_load.py ---')
