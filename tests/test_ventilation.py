import csv

import pytest

from builelib import ventilation

### テストファイル名 ###
# 辞書型 テスト名とファイル名

testcase_dict_fan = {
    "fan_1unit_2rooms": "./tests/ventilation/◇1台2室.txt",
    "fan_2units_1room": "./tests/ventilation/◇2台1室.txt",
    "fan_2units_2rooms": "./tests/ventilation/◇2台2室.txt",
    "fan_inverter": "./tests/ventilation/◇インバータ.txt",
    "fan_moter": "./tests/ventilation/◇高効率電動機.txt",
    "fan_volume_ctrl": "./tests/ventilation/◇送風量制御.txt",
    "fan_power": "./tests/ventilation/◇定格出力.txt",
    "fan_hotel": "./tests/ventilation/◇用途別_ホテル等.txt",
    "fan_restraunt": "./tests/ventilation/◇用途別_飲食店等.txt",
    "fan_school": "./tests/ventilation/◇用途別_学校等.txt",
    "fan_apartment": "./tests/ventilation/◇用途別_共同住宅.txt",
    "fan_factory": "./tests/ventilation/◇用途別_工場等.txt",
    "fan_office": "./tests/ventilation/◇用途別_事務所等.txt",
    "fan_meeting": "./tests/ventilation/◇用途別_集会所等.txt",
    "fan_hospital": "./tests/ventilation/◇用途別_病院等.txt",
    "fan_shop": "./tests/ventilation/◇用途別_物品販売業を営む店舗等.txt",
}
testcase_dict_ac = {
    "AC_office": "./tests/ventilation/換気代替空調機_事務所テスト.txt",
    "AC_spec": "./tests/ventilation/換気代替空調機_仕様.txt"
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


def make_input_data_fan(data):
    if data[3] == "物品販売業を営む店舗等":
        data[3] = "物販店舗等"
    if data[12] == "物品販売業を営む店舗等":
        data[12] = "物販店舗等"

    input_data = {
        "building": {
            "region": "6"
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
        "ventilation_room": {
            data[1] + "_" + data[2]: {
                "ventilation_type": "一種換気",
                "ventilation_unit_ref": {
                    data[7]: {
                        "unit_type": data[6],
                        "info": ""
                    }
                }
            },
        },
        "ventilation_unit": {
            data[19]: {
                "number": 1,
                "fan_air_volume": convert2number(data[20], None),
                "motor_rated_power": convert2number(data[21], None),
                "power_consumption": None,
                "high_efficiency_motor": data[22],
                "inverter": data[23],
                "air_volume_control": data[24],
                "ventilation_room_type": None,
                "ac_cooling_capacity": None,
                "ac_ref_efficiency": None,
                "ac_pump_power": None,
                "info": ""
            }
        }
    }

    # 1室目の2台目追加
    if data[9] != "":
        input_data["ventilation_room"][data[1] + "_" + data[2]]["ventilation_unit_ref"][data[9]] = {
            "unit_type": data[8],
            "info": ""
        }

    # 2室目追加
    if data[11] != "":
        input_data["rooms"][data[10] + "_" + data[11]] = {
            "floorname": data[10],
            "roomname": data[11],
            "building_type": data[12],
            "room_type": data[13],
            "room_area": convert2number(data[14], None)
        }

        input_data["ventilation_room"][data[10] + "_" + data[11]] = {
            "ventilation_type": "一種換気",
            "ventilation_unit_ref": {
                data[16]: {
                    "unit_type": data[15],
                    "info": ""
                }
            }
        }

    # 2室目の2台目追加
    if data[18] != "":
        input_data["ventilation_room"][data[10] + "_" + data[11]]["ventilation_unit_ref"][data[18]] = {
            "unit_type": data[17],
            "info": ""
        }

    # 2機種目の追加
    if data[25] != "":
        input_data["ventilation_unit"][data[25]] = {
            "number": 1,
            "fan_air_volume": convert2number(data[26], None),
            "motor_rated_power": convert2number(data[27], None),
            "power_consumption": None,
            "high_efficiency_motor": data[28],
            "inverter": data[29],
            "air_volume_control": data[30],
            "ventilation_room_type": None,
            "ac_cooling_capacity": None,
            "ac_ref_efficiency": None,
            "ac_pump_power": None,
            "info": ""
        }

    return input_data


def make_input_data_ac(data):
    print(data)

    if data[4] == "物品販売業を営む店舗等":
        data[4] = "物販店舗等"
    if data[12] == "物品販売業を営む店舗等":
        data[12] = "物販店舗等"

    input_data = {
        "building": {
            "region": str(data[53])
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
        "ventilation_room": {
            data[1] + "_" + data[2]: {
                "ventilation_type": "一種換気",
                "ventilation_unit_ref": {
                    data[7]: {
                        "unit_type": data[6],
                        "info": ""
                    }
                }
            }
        },
        "ventilation_unit": {
        }
    }

    # 1室目の2台目追加
    if data[9] != "":
        input_data["ventilation_room"][data[1] + "_" + data[2]]["ventilation_unit_ref"][data[9]] = {
            "unit_type": data[8],
            "info": ""
        }

    # 2室目追加
    if data[11] != "":
        input_data["rooms"][data[10] + "_" + data[11]] = {
            "floorname": data[10],
            "roomname": data[11],
            "building_type": data[12],
            "room_type": data[13],
            "room_area": convert2number(data[14], None)
        }

        input_data["ventilation_room"][data[10] + "_" + data[11]] = {
            "ventilation_type": "一種換気",
            "ventilation_unit_ref": {
                data[16]: {
                    "unit_type": data[15],
                    "info": ""
                }
            }
        }

    # 2室目の2台目追加
    if data[18] != "":
        input_data["ventilation_room"][data[10] + "_" + data[11]]["ventilation_unit_ref"][data[18]] = {
            "unit_type": data[17],
            "info": ""
        }

    # 換気代替空調機1台目
    if data[19] != "":

        if data[24] == "空調":

            input_data["ventilation_unit"][data[19]] = {
                "number": 1,
                "fan_air_volume": convert2number(data[25], None),
                "motor_rated_power": convert2number(data[26], None),
                "power_consumption": None,
                "high_efficiency_motor": data[27],
                "inverter": data[28],
                "air_volume_control": data[29],
                "ventilation_room_type": data[20],
                "ac_cooling_capacity": convert2number(data[21], None),
                "ac_ref_efficiency": convert2number(data[22], None),
                "ac_pump_power": convert2number(data[23], None),
                "info": ""
            }

        elif data[30] == "空調":

            input_data["ventilation_unit"][data[19]] = {
                "number": 1,
                "fan_air_volume": convert2number(data[31], None),
                "motor_rated_power": convert2number(data[32], None),
                "power_consumption": None,
                "high_efficiency_motor": data[33],
                "inverter": data[34],
                "air_volume_control": data[35],
                "ventilation_room_type": data[20],
                "ac_cooling_capacity": convert2number(data[21], None),
                "ac_ref_efficiency": convert2number(data[22], None),
                "ac_pump_power": convert2number(data[23], None),
                "info": ""
            }

        else:
            raise Exception("換気代替空調機には種類「空調」の要素が必要です")

        # ファンの追加
        if data[24] != "" and data[24] != "空調":

            input_data["ventilation_unit"][data[19] + "_fan"] = {
                "number": 1,
                "fan_air_volume": convert2number(data[25], None),
                "motor_rated_power": convert2number(data[26], None),
                "power_consumption": None,
                "high_efficiency_motor": data[27],
                "inverter": data[28],
                "air_volume_control": data[29],
                "ventilation_room_type": None,
                "ac_cooling_capacity": None,
                "ac_ref_efficiency": None,
                "ac_pump_power": None,
                "info": ""
            }

            # ventilation_room要素に追加
            if data[19] == data[7] or data[19] == data[9]:

                input_data["ventilation_room"][data[1] + "_" + data[2]]["ventilation_unit_ref"][data[19] + "_fan"] = {
                    "unit_type": data[24],
                    "info": ""
                }

            elif data[19] == data[16] or data[19] == data[18]:

                input_data["ventilation_room"][data[10] + "_" + data[11]]["ventilation_unit_ref"][data[19] + "_fan"] = {
                    "unit_type": data[24],
                    "info": ""
                }

            else:
                raise Exception("室と換気代替空調機が適切にリンクされていません")


        elif data[30] != "" and data[30] != "空調":

            input_data["ventilation_unit"][data[19] + "_fan"] = {
                "number": 1,
                "fan_air_volume": convert2number(data[31], None),
                "motor_rated_power": convert2number(data[32], None),
                "power_consumption": None,
                "high_efficiency_motor": data[33],
                "inverter": data[34],
                "air_volume_control": data[35],
                "ventilation_room_type": None,
                "ac_cooling_capacity": None,
                "ac_ref_efficiency": None,
                "ac_pump_power": None,
                "info": ""
            }

            # ventilation_room要素に追加
            if data[19] == data[7] or data[19] == data[9]:

                input_data["ventilation_room"][data[1] + "_" + data[2]]["ventilation_unit_ref"][data[19] + "_fan"] = {
                    "unit_type": data[30],
                    "info": ""
                }

            elif data[19] == data[16] or data[19] == data[18]:

                input_data["ventilation_room"][data[10] + "_" + data[11]]["ventilation_unit_ref"][data[19] + "_fan"] = {
                    "unit_type": data[30],
                    "info": ""
                }

            else:
                raise Exception("室と換気代替空調機が適切にリンクされていません")

    # 換気代替空調機2台目
    if data[36] != "":

        if data[41] == "空調":

            input_data["ventilation_unit"][data[36]] = {
                "number": 1,
                "fan_air_volume": convert2number(data[42], None),
                "motor_rated_power": convert2number(data[43], None),
                "power_consumption": None,
                "high_efficiency_motor": data[44],
                "inverter": data[45],
                "air_volume_control": data[46],
                "ventilation_room_type": data[37],
                "ac_cooling_capacity": convert2number(data[38], None),
                "ac_ref_efficiency": convert2number(data[39], None),
                "ac_pump_power": convert2number(data[40], None),
                "info": ""
            }

        elif data[47] == "空調":

            input_data["ventilation_unit"][data[36]] = {
                "number": 1,
                "fan_air_volume": convert2number(data[48], None),
                "motor_rated_power": convert2number(data[49], None),
                "power_consumption": None,
                "high_efficiency_motor": data[50],
                "inverter": data[51],
                "air_volume_control": data[52],
                "ventilation_room_type": data[37],
                "ac_cooling_capacity": convert2number(data[38], None),
                "ac_ref_efficiency": convert2number(data[39], None),
                "ac_pump_power": convert2number(data[40], None),
                "info": ""
            }

        else:
            raise Exception("換気代替空調機には種類「空調」の要素が必要です")

        # ファンの追加
        if data[41] != "" and data[41] != "空調":

            input_data["ventilation_unit"][data[36] + "_fan"] = {
                "number": 1,
                "fan_air_volume": convert2number(data[42], None),
                "motor_rated_power": convert2number(data[43], None),
                "power_consumption": None,
                "high_efficiency_motor": data[44],
                "inverter": data[45],
                "air_volume_control": data[46],
                "ventilation_room_type": None,
                "ac_cooling_capacity": None,
                "ac_ref_efficiency": None,
                "ac_pump_power": None,
                "info": ""
            }

            # ventilation_room要素に追加
            if data[36] == data[7] or data[36] == data[9]:

                input_data["ventilation_room"][data[1] + "_" + data[2]]["ventilation_unit_ref"][data[36] + "_fan"] = {
                    "unit_type": data[41],
                    "info": ""
                }

            elif data[36] == data[16] or data[36] == data[18]:

                input_data["ventilation_room"][data[10] + "_" + data[11]]["ventilation_unit_ref"][data[36] + "_fan"] = {
                    "unit_type": data[41],
                    "info": ""
                }

            else:
                raise Exception("室と換気代替空調機が適切にリンクされていません")


        elif data[47] != "" and data[47] != "空調":

            input_data["ventilation_unit"][data[36] + "_fan"] = {
                "number": 1,
                "fan_air_volume": convert2number(data[48], None),
                "motor_rated_power": convert2number(data[49], None),
                "power_consumption": None,
                "high_efficiency_motor": data[50],
                "inverter": data[51],
                "air_volume_control": data[52],
                "ventilation_room_type": None,
                "ac_cooling_capacity": None,
                "ac_ref_efficiency": None,
                "ac_pump_power": None,
                "info": ""
            }

            # ventilation_room要素に追加
            if data[36] == data[7] or data[36] == data[9]:

                input_data["ventilation_room"][data[1] + "_" + data[2]]["ventilation_unit_ref"][data[36] + "_fan"] = {
                    "unit_type": data[47],
                    "info": ""
                }

            elif data[36] == data[16] or data[36] == data[18]:

                input_data["ventilation_room"][data[10] + "_" + data[11]]["ventilation_unit_ref"][data[36] + "_fan"] = {
                    "unit_type": data[47],
                    "info": ""
                }

            else:
                raise Exception("室と換気代替空調機が適切にリンクされていません")

    return input_data


#### テストケースファイルの読み込み（換気送風機）

test_to_try = []  # テスト用入力ファイルと期待値のリスト
testcase_id = []  # テスト名称のリスト

for case_name in testcase_dict_fan:

    # テストファイルの読み込み
    testfiledata = read_testcasefile(testcase_dict_fan[case_name])

    # ヘッダーの削除
    testfiledata.pop(0)

    # テストケース（行）に対するループ
    for testdata in testfiledata:
        # 入力データの作成
        input_data = make_input_data_fan(testdata)
        # 期待値
        expectedvalue = convert2number(testdata[31], 0)

        # テストケースの集約
        test_to_try.append((input_data, expectedvalue))
        # テストケース名
        testcase_id.append(case_name + testdata[0])

for case_name in testcase_dict_ac:

    # テストファイルの読み込み
    testfiledata = read_testcasefile(testcase_dict_ac[case_name])

    # ヘッダーの削除
    testfiledata.pop(0)

    # テストケース（行）に対するループ
    for testdata in testfiledata:
        # 入力データの作成
        input_data = make_input_data_ac(testdata)
        # 期待値
        expectedvalue = convert2number(testdata[54], 0)

        # テストケースの集約
        test_to_try.append((input_data, expectedvalue))
        # テストケース名
        testcase_id.append(case_name + testdata[0])


# テストの実施
@pytest.mark.parametrize('input_data, expectedvalue', test_to_try, ids=testcase_id)
def test_calc(input_data, expectedvalue):
    if expectedvalue != "err":  # passが期待されるテスト
        # 計算実行        
        result_json = ventilation.calc_energy(input_data)

        # 比較
        assert abs(result_json["E_ventilation"] - expectedvalue) < 0.0001

    else:

        # エラーが期待される場合
        with pytest.raises(Exception):
            result_json = ventilation.calc_energy(input_data)


if __name__ == '__main__':
    print('--- test_vetilation.py ---')
