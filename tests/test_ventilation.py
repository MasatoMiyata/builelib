import pandas as pd
import csv
import pprint as pp
from builelib.ventilation import ventilation
import jsonschema
import json

# 空欄にデフォルト値を代入する
def convert2number(x, default):
    if x == "":
        x = default
    else:
        x = float(x)
    return x


# 計算の実行
def calculation_fan(filename):
    '''
    換気送風機のテスト実行
    '''

    print(filename) # 確認用

    # テスト用データの読み込み
    with open(filename, mode='r', newline='', encoding='shift-jis') as f:
        tsv_reader = csv.reader(f, delimiter=',')
        testdata = [row for row in tsv_reader]

    # ヘッダーを削除
    testdata.pop(0)

    for data in testdata:

        print(data) # 確認用

        # 計算モデルの作成（1系統の場合）
        
        inputdata = {
            "Building":{
                "Region": "6"
            },
            "Rooms": {
                data[1]+"_"+data[2]: {
                    "floorName": data[1],
                    "roomName": data[2],
                    "buildingType": data[3],
                    "roomType": data[4],
                    "roomArea": convert2number(data[5],None)
                },
                data[10]+"_"+data[11]: {
                    "floorName": data[10],
                    "roomName": data[11],
                    "buildingType": data[12],
                    "roomType": data[13],
                    "roomArea": convert2number(data[14],None)
                }
            },
            "VentilationRoom": {
                data[1]+"_"+data[2]: {
                    "VentilationType": "一種換気",
                    "VentilationUnitRef": {
                        data[7]: {
                            "UnitType": data[6],
                            "Info": ""
                        },
                        data[9]: {
                            "UnitType": data[8],
                            "Info": ""
                        }
                    }
                },
                data[10]+"_"+data[11]: {
                    "VentilationType": "一種換気",
                    "VentilationUnitRef": {
                        data[16]: {
                            "UnitType": data[15],
                            "Info": ""
                        },
                        data[18]: {
                            "UnitType": data[17],
                            "Info": ""
                        }
                    }
                },
            },
            "VentilationUnit": {
                data[19]: {
                    "Number": 1,
                    "FanAirVolume": convert2number(data[20],None),
                    "MoterRatedPower": convert2number(data[21],None),
                    "PowerConsumption": None,
                    "HighEfficiencyMotor": data[22],
                    "Inverter": data[23],
                    "AirVolumeControl": data[24],
                    "VentilationRoomType": None,
                    "AC_CoolingCapacity": None,
                    "AC_RefEfficiency": None,
                    "AC_PumpPower": None,
                    "Info": ""
                },
                data[25]: {
                    "Number": 1,
                    "FanAirVolume": convert2number(data[26],None),
                    "MoterRatedPower": convert2number(data[27],None),
                    "PowerConsumption": None,
                    "HighEfficiencyMotor": data[28],
                    "Inverter": data[29],
                    "AirVolumeControl": data[30],
                    "VentilationRoomType": None,
                    "AC_CoolingCapacity": None,
                    "AC_RefEfficiency": None,
                    "AC_PumpPower": None,
                    "Info": ""
                },
            }
        }

        try:

            # 計算実行        
            resultJson = ventilation(inputdata)

            # 期待値
            resultJson["expectedDesignValue"]   = convert2number(data[31],0)

            assert abs(resultJson["E_ventilation"] - resultJson["expectedDesignValue"])   < 0.0001

        except:
            assert data[31] == "err"


def calculation_ac(filename):
    '''
    換気代替空調機のテスト実行
    '''

    print(filename) # 確認用

    # テスト用データの読み込み
    with open(filename, mode='r', newline='', encoding='shift-jis') as f:
        tsv_reader = csv.reader(f, delimiter=',')
        testdata = [row for row in tsv_reader]

    # ヘッダーを削除
    testdata.pop(0)

    for data in testdata:

        print(data) # 確認用

        # 計算モデルの作成（1系統の場合）
        
        inputdata = {
            "Building":{
                "Region": str(data[53])
            },
            "Rooms": {
                data[1]+"_"+data[2]: {
                    "floorName": data[1],
                    "roomName": data[2],
                    "buildingType": data[3],
                    "roomType": data[4],
                    "roomArea": convert2number(data[5],None)
                }
            },
            "VentilationRoom": {
                data[1]+"_"+data[2]: {
                    "VentilationType": "一種換気",
                    "VentilationUnitRef": {
                        "PAC1": {
                            "UnitType": data[24],
                            "Info": ""
                        },
                        "FAN": {
                            "UnitType": data[30],
                            "Info": ""
                        }
                    }
                }
            },
            "VentilationUnit": {
                "PAC1": {
                    "Number": 1,
                    "FanAirVolume": convert2number(data[25],None),
                    "MoterRatedPower": convert2number(data[26],None),
                    "PowerConsumption": None,
                    "HighEfficiencyMotor": data[27],
                    "Inverter": data[28],
                    "AirVolumeControl": data[29],
                    "VentilationRoomType": data[20],
                    "AC_CoolingCapacity": convert2number(data[21],None),
                    "AC_RefEfficiency": convert2number(data[22],None),
                    "AC_PumpPower": convert2number(data[23],None),
                    "Info": ""
                },
                "FAN": {
                    "Number": 1,
                    "FanAirVolume": convert2number(data[31],None),
                    "MoterRatedPower": convert2number(data[32],None),
                    "PowerConsumption": None,
                    "HighEfficiencyMotor": data[33],
                    "Inverter": data[34],
                    "AirVolumeControl": data[35],
                    "VentilationRoomType": None,
                    "AC_CoolingCapacity": None,
                    "AC_RefEfficiency": None,
                    "AC_PumpPower": None,
                    "Info": ""
                }
            }
        }

        with open("inputdata.json",'w') as fw:
            json.dump(inputdata, fw, indent=4, ensure_ascii=False)

        try:

            # 計算実行
            print(inputdata)
            resultJson = ventilation(inputdata)

            # 期待値
            resultJson["expectedDesignValue"]   = convert2number(data[54],0)

            assert abs(resultJson["E_ventilation"] - resultJson["expectedDesignValue"])   < 0.0001

        except:
            assert data[54] == "err"




#### テスト実行 ####

def test_ventilation_Fan():
    calculation_fan('./tests/ventilation/換気送風機_仮テスト.txt')

def test_ventilation_AC():
    calculation_ac('./tests/ventilation/換気代替空調機_仮テスト.txt')

if __name__ == '__main__':
    print('--- test_vetilation.py ---')
