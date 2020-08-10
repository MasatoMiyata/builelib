import pandas as pd
import csv
import pprint as pp
from builelib.elevetor import elevetor
import jsonschema

# 空欄にデフォルト値を代入する
def convert2number(x, default):
    if x == "":
        x = default
    else:
        x = float(x)
    return x

# 計算の実行
def calculation(filename):

    print(filename) # 確認用

    # テスト用データの読み込み
    with open(filename, mode='r', newline='', encoding='shift-jis') as f:
        tsv_reader = csv.reader(f, delimiter=',')
        testdata = [row for row in tsv_reader]

    # ヘッダーを削除
    testdata.pop(0)

    for data in testdata:

        print(data) # 確認用

        if (data[11] == ""):

            # 計算モデルの作成（一部屋の場合）
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

        else:

            # 計算モデルの作成（二部屋の場合）
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

        try:
            
            # 計算実行        
            resultJson = elevetor(inputdata)

            # 期待値
            resultJson["expectedDesignValue"]   = convert2number(data[21],0)
            # resultJson["expectedStandardValue"] = convert2number(data[22],0)

            assert abs(resultJson["E_elevetor"] - resultJson["expectedDesignValue"])   < 0.0001
            # assert abs(resultJson["Es_elevetor"] - resultJson["expectedStandardValue"]) < 0.0001

        except:
            assert data[21] == "err"


#### テスト実行 ####

def test_basic_condition():
    calculation('./tests/elevetor/基本テスト.txt')


if __name__ == '__main__':
    print('--- test_elevetor.py ---')