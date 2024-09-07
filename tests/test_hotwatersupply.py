import csv

import pytest

from builelib import hotwatersupply

### テストファイル名 ###
# 辞書型 テスト名とファイル名

testcase_dict = {
    "basic_test": "./tests/hotwatersupply/◇基本ケース.txt",
    "office": "./tests/hotwatersupply/◇事務所ケース.txt",
    "office_complex": "./tests/hotwatersupply/◇事務所_複合ケース.txt",
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
    if data[3] == "物品販売業を営む店舗等":
        data[3] = "物販店舗等"
    if data[14] == "物品販売業を営む店舗等":
        data[14] = "物販店舗等"

    input_data = {
        "building": {
            "region": str(data[41])
        },
        "rooms": {
            data[1] + "_" + data[2]: {
                "floorname": data[1],
                "roomname": data[2],
                "building_type": data[3],
                "room_type": data[4],
                "room_area": convert2number(data[5], None)
            }
        },
        "hot_water_room": {
            data[1] + "_" + data[2]: {
                "hot_water_system": [
                    {
                        "usage_type": "便所",
                        "system_name": data[8],
                        "hot_water_saving_system": data[7],
                        "info": data[6]
                    }
                ]
            }
        },
        "hot_water_supply_systems": {
        },
        "cogeneration_systems": {
        },
        "special_input_data": {
        }
    }

    if data[9] != "":
        input_data["hot_water_room"][data[1] + "_" + data[2]]["hot_water_system"].append(
            {
                "usage_type": "便所",
                "system_name": data[11],
                "hot_water_saving_system": data[10],
                "info": data[9]
            }
        )

    if data[13] != "":
        input_data["rooms"][data[12] + "_" + data[13]] = {
            "floorname": data[12],
            "roomname": data[13],
            "building_type": data[14],
            "room_type": data[15],
            "room_area": convert2number(data[16], None)
        }

        input_data["hot_water_room"][data[12] + "_" + data[13]] = {
            "hot_water_system": [
                {
                    "usage_type": "便所",
                    "system_name": data[19],
                    "hot_water_saving_system": data[18],
                    "info": data[17]
                }
            ]
        }

    if data[20] != "":
        input_data["hot_water_room"][data[12] + "_" + data[13]]["hot_water_system"].append(
            {
                "usage_type": "便所",
                "system_name": data[22],
                "hot_water_saving_system": data[21],
                "info": data[20]
            }
        )

    if data[23] != "":
        input_data["hot_water_supply_systems"][data[23]] = {
            "heat_sourceUnit": [
                {
                    "usage_type": "給湯負荷用",
                    "heat_source_type": "ガス給湯機",
                    "number": 1,
                    "rated_capacity": convert2number(data[25], None),
                    "rated_power_consumption": 0,
                    "rated_fuel_consumption": convert2number(data[25], None) / convert2number(data[26], None)
                }
            ],
            "insulation_type": data[27],
            "pipe_size": convert2number(data[28], None),
            "solar_system_area": convert2number(data[29], None),
            "solar_system_direction": convert2number(data[30], None),
            "solar_system_angle": convert2number(data[31], None),
            "info": ""
        }

    if data[32] != "":
        input_data["hot_water_supply_systems"][data[32]] = {
            "heat_sourceUnit": [
                {
                    "usage_type": "給湯負荷用",
                    "heat_source_type": "ガス給湯機",
                    "number": 1,
                    "rated_capacity": convert2number(data[34], None),
                    "rated_power_consumption": 0,
                    "rated_fuel_consumption": convert2number(data[34], None) / convert2number(data[35], None)
                }
            ],
            "insulation_type": data[36],
            "pipe_size": convert2number(data[37], None),
            "solar_system_area": convert2number(data[38], None),
            "solar_system_direction": convert2number(data[39], None),
            "solar_system_angle": convert2number(data[40], None),
            "info": ""
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
        expectedvalue = testdata[42]

        # テストケースの集約
        test_to_try.append((input_data, expectedvalue))
        # テストケース名
        testcase_id.append(case_name + testdata[0])


# テストの実施
@pytest.mark.parametrize('input_data, expectedvalue', test_to_try, ids=testcase_id)
def test_calc(input_data, expectedvalue):
    if expectedvalue != "err":  # passが期待されるテスト
        # 計算実行        
        result_json = hotwatersupply.calc_energy(input_data)

        # 比較
        assert abs(result_json["E_hotwatersupply"] - convert2number(expectedvalue, 0)) < 0.0001

    else:

        # エラーが期待される場合
        with pytest.raises(Exception):
            result_json = hotwatersupply.calc_energy(input_data)


if __name__ == '__main__':
    print('--- test_hotwatersupply.py ---')
