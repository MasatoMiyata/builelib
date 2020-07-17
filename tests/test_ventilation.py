import pandas as pd
import csv
import pprint as pp
from builelib.ventilation import ventilation
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

        if data[9] == "":

            # 計算モデルの作成（1系統の場合）
            inputdata = {
                "Building":{
                    "Region": "6"
                },
                "Rooms": {
                    "1F_室": {
                        "floorName": "1F",
                        "roomName": "室",
                        "buildingType": data[1],
                        "roomType": data[2],
                        "roomArea": 100,
                    }
                },
                "VentilationRoom": {
                    "1F_室": {
                        "VentilationType": "一種換気",
                        "VentilationUnitRef": {
                            "SF-1": {
                                "UnitType": "給気",
                                "Info": ""
                            }
                        }
                    }
                },
                "VentilationUnit": {
                    "SF-1": {
                        "Number": 1.0,
                        "FanAirVolume": 200.0,
                        "MoterRatedPower": convert2number(data[4],None),
                        "PowerConsumption": None,
                        "HighEfficiencyMotor": data[5],
                        "Inverter": data[6],
                        "AirVolumeControl": data[7],
                        "VentilationRoomType": None,
                        "AC_CoolingCapacity": None,
                        "AC_RefEfficiency": None,
                        "AC_PumpPower": None,
                        "Info": ""
                    }
                }
            }

        else:

            # 計算モデルの作成（2系統の場合）
            inputdata = {
                "Building":{
                    "Region": "6"
                },
                "Rooms": {
                    "1F_室": {
                        "floorName": "1F",
                        "roomName": "室",
                        "buildingType": data[1],
                        "roomType": data[2],
                        "roomArea": 100,
                    },
                    "2F_室": {
                        "floorName": "2F",
                        "roomName": "室",
                        "buildingType": data[9],
                        "roomType": data[10],
                        "roomArea": 100,
                    }
                },
                "VentilationRoom": {
                    "1F_室": {
                        "VentilationType": "一種換気",
                        "VentilationUnitRef": {
                            "SF-1": {
                                "UnitType": "給気",
                                "Info": ""
                            }
                        }
                    },
                    "2F_室": {
                        "VentilationType": "一種換気",
                        "VentilationUnitRef": {
                            "SF-2": {
                                "UnitType": "給気",
                                "Info": ""
                            }
                        }
                    }
                },
                "VentilationUnit": {
                    "SF-1": {
                        "Number": 1.0,
                        "FanAirVolume": 200.0,
                        "MoterRatedPower": convert2number(data[4],None),
                        "PowerConsumption": None,
                        "HighEfficiencyMotor": data[5],
                        "Inverter": data[6],
                        "AirVolumeControl": data[7],
                        "VentilationRoomType": None,
                        "AC_CoolingCapacity": None,
                        "AC_RefEfficiency": None,
                        "AC_PumpPower": None,
                        "Info": ""
                    },
                    "SF-2": {
                        "Number": 1.0,
                        "FanAirVolume": 200.0,
                        "MoterRatedPower": convert2number(data[12],None),
                        "PowerConsumption": None,
                        "HighEfficiencyMotor": data[13],
                        "Inverter": data[14],
                        "AirVolumeControl": data[15],
                        "VentilationRoomType": None,
                        "AC_CoolingCapacity": None,
                        "AC_RefEfficiency": None,
                        "AC_PumpPower": None,
                        "Info": ""
                    }
                }
            }


        try:

            # 計算実行        
            resultJson = ventilation(inputdata)

            # 期待値
            resultJson["expectedDesignValue"]   = convert2number(data[17],0)

            assert abs(resultJson["E_ventilation"] - resultJson["expectedDesignValue"])   < 0.0001

        except:
            assert data[17] == "err"



#### テスト実行 ####

def test_ventilation_Fan():
    calculation('./tests/ventilation/◇建物室用途_事務所.txt')


if __name__ == '__main__':
    print('--- test_vetilation.py ---')
    calculation('./tests/ventilation/◇建物室用途_事務所.txt')
