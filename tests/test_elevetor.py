import pandas as pd
import csv
import pprint as pp
from builelib.elevetor import elevetor
import pytest

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


def make_inputdata(data):
    '''
    インプットデータを作成する関数
    '''

    if (data[11] == "") and (data[16] == ""):

        # 計算モデルの作成（1室1系統）
        inputdata = {
            "Building":{
                "Region": "6"
            },
            "Rooms": {
                "1F_室": {
                    "floorName": data[1],
                    "roomName": data[2],
                    "buildingType": data[3],
                    "roomType": data[4],
                    "roomArea": 100,
                }
            },
            "Elevators": {
                "1F_室": {
                    "Elevator": [
                        {
                            "ElevatorName": data[5],
                            "Number": convert2number(data[6],0),
                            "LoadLimit": convert2number(data[7],0),
                            "Velocity": convert2number(data[8],0),
                            "TransportCapacityFactor": convert2number(data[9],0),
                            "ControlType": data[10],
                            "Info": ""
                        }
                    ]
                }
            }
        }

    elif (data[11] == ""):

        # 計算モデルの作成（1室2系統）
        inputdata = {
            "Building":{
                "Region": "6"
            },
            "Rooms": {
                "1F_室": {
                    "floorName": data[1],
                    "roomName": data[2],
                    "buildingType": data[3],
                    "roomType": data[4],
                    "roomArea": 100,
                }
            },
            "Elevators": {
                "1F_室": {
                    "Elevator": [
                        {
                            "ElevatorName": data[5],
                            "Number": convert2number(data[6],0),
                            "LoadLimit": convert2number(data[7],0),
                            "Velocity": convert2number(data[8],0),
                            "TransportCapacityFactor": convert2number(data[9],0),
                            "ControlType": data[10],
                            "Info": ""
                        },
                        {
                            "ElevatorName": data[15],
                            "Number": convert2number(data[16],0),
                            "LoadLimit": convert2number(data[17],0),
                            "Velocity": convert2number(data[18],0),
                            "TransportCapacityFactor": convert2number(data[19],0),
                            "ControlType": data[20],
                            "Info": ""
                        }
                    ]
                }
            }
        }

    else:

        # 計算モデルの作成（2室の場合）
        inputdata = {
            "Building":{
                "Region": "6"
            },
            "Rooms": {
                "1F_室": {
                    "floorName": data[1],
                    "roomName": data[2],
                    "buildingType": data[3],
                    "roomType": data[4],
                    "roomArea": 100,
                },
                "2F_室": {
                    "floorName": data[11],
                    "roomName": data[12],
                    "buildingType": data[13],
                    "roomType": data[14],
                    "roomArea": 100,
                },
            },
            "Elevators": {
                "1F_室": {
                    "Elevator": [
                        {
                            "ElevatorName": data[5],
                            "Number": convert2number(data[6],0),
                            "LoadLimit": convert2number(data[7],0),
                            "Velocity": convert2number(data[8],0),
                            "TransportCapacityFactor": convert2number(data[9],0),
                            "ControlType": data[10],
                            "Info": ""
                        }
                    ]
                },
                "2F_室": {
                    "Elevator": [
                        {
                            "ElevatorName": data[15],
                            "Number": convert2number(data[16],0),
                            "LoadLimit": convert2number(data[17],0),
                            "Velocity": convert2number(data[18],0),
                            "TransportCapacityFactor": convert2number(data[19],0),
                            "ControlType": data[20],
                            "Info": ""
                        }
                    ]
                },
            }
        }

    return inputdata


#### テストケースファイルの読み込み

test_to_try = []   # テスト用入力ファイルと期待値のリスト
testcase_id  = []  # テスト名称のリスト

for case_name in testcase_dict:

    # テストファイルの読み込み
    testfiledata = read_testcasefile(testcase_dict[case_name])

    # ヘッダーの削除
    testfiledata.pop(0)

    # テストケース（行）に対するループ
    for testdata in testfiledata:

        # 入力データの作成
        inputdata = make_inputdata(testdata)
        # 期待値
        expectedvalue = convert2number(testdata[21],0)

        # テストケースの集約
        test_to_try.append( (inputdata, expectedvalue) )
        # テストケース名
        testcase_id.append(case_name + testdata[0])


# テストの実施
@pytest.mark.parametrize('inputdata, expectedvalue', test_to_try, ids=testcase_id)
def test_calc(inputdata, expectedvalue):

    # 計算実行        
    resultJson = elevetor(inputdata)

    # 比較
    assert abs(resultJson["E_elevetor"] - expectedvalue)   < 0.0001


if __name__ == '__main__':
    print('--- test_elevetor.py ---')