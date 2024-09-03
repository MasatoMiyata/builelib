import csv

import pytest

from builelib import elevetor

### テストファイル名 ###
# 辞書型 テスト名とファイル名

testcase_dict = {
    "office": "./tests/elevetor/◇事務所テスト.txt",
    "office_2units": "./tests/elevetor/◇事務所テスト1室2系.txt"
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
    '''
    インプットデータを作成する関数
    '''

    if (data[11] == "") and (data[16] == ""):

        # 計算モデルの作成（1室1系統）
        input_data = {
            "building": {
                "region": "6"
            },
            "rooms": {
                "1F_室": {
                    "floorname": data[1],
                    "roomname": data[2],
                    "building_type": data[3],
                    "room_type": data[4],
                    "room_area": 100,
                }
            },
            "elevators": {
                "1F_室": {
                    "elevator": [
                        {
                            "elevator_name": data[5],
                            "number": convert2number(data[6], 0),
                            "load_limit": convert2number(data[7], 0),
                            "velocity": convert2number(data[8], 0),
                            "transport_capacity_factor": convert2number(data[9], 0),
                            "control_type": data[10],
                            "info": ""
                        }
                    ]
                }
            }
        }

    elif (data[11] == ""):

        # 計算モデルの作成（1室2系統）
        input_data = {
            "building": {
                "region": "6"
            },
            "rooms": {
                "1F_室": {
                    "floorname": data[1],
                    "roomname": data[2],
                    "building_type": data[3],
                    "room_type": data[4],
                    "room_area": 100,
                }
            },
            "elevators": {
                "1F_室": {
                    "elevator": [
                        {
                            "elevator_name": data[5],
                            "number": convert2number(data[6], 0),
                            "load_limit": convert2number(data[7], 0),
                            "velocity": convert2number(data[8], 0),
                            "transport_capacity_factor": convert2number(data[9], 0),
                            "control_type": data[10],
                            "info": ""
                        },
                        {
                            "elevator_name": data[15],
                            "number": convert2number(data[16], 0),
                            "load_limit": convert2number(data[17], 0),
                            "velocity": convert2number(data[18], 0),
                            "transport_capacity_factor": convert2number(data[19], 0),
                            "control_type": data[20],
                            "info": ""
                        }
                    ]
                }
            }
        }

    else:

        # 計算モデルの作成（2室の場合）
        input_data = {
            "building": {
                "region": "6"
            },
            "rooms": {
                "1F_室": {
                    "floorname": data[1],
                    "roomname": data[2],
                    "building_type": data[3],
                    "room_type": data[4],
                    "room_area": 100,
                },
                "2F_室": {
                    "floorname": data[11],
                    "roomname": data[12],
                    "building_type": data[13],
                    "room_type": data[14],
                    "room_area": 100,
                },
            },
            "elevators": {
                "1F_室": {
                    "elevator": [
                        {
                            "elevator_name": data[5],
                            "number": convert2number(data[6], 0),
                            "load_limit": convert2number(data[7], 0),
                            "velocity": convert2number(data[8], 0),
                            "transport_capacity_factor": convert2number(data[9], 0),
                            "control_type": data[10],
                            "info": ""
                        }
                    ]
                },
                "2F_室": {
                    "elevator": [
                        {
                            "elevator_name": data[15],
                            "number": convert2number(data[16], 0),
                            "load_limit": convert2number(data[17], 0),
                            "velocity": convert2number(data[18], 0),
                            "transport_capacity_factor": convert2number(data[19], 0),
                            "control_type": data[20],
                            "info": ""
                        }
                    ]
                },
            }
        }

    return input_data


#### テストケースファイルの読み込み

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
        expectedvalue = convert2number(testdata[21], 0)

        # テストケースの集約
        test_to_try.append((input_data, expectedvalue))
        # テストケース名
        testcase_id.append(case_name + testdata[0])


# テストの実施
@pytest.mark.parametrize('input_data, expectedvalue', test_to_try, ids=testcase_id)
def test_calc(input_data, expectedvalue):
    if expectedvalue != "err":  # passが期待されるテスト
        # 計算実行        
        result_json = elevetor.calc_energy(input_data)

        # 比較
        assert abs(result_json["E_elevetor"] - expectedvalue) < 0.0001

    else:

        # エラーが期待される場合
        with pytest.raises(Exception):
            result_json = elevetor(input_data)


if __name__ == '__main__':
    print('--- test_elevetor.py ---')
