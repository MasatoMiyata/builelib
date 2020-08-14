import pandas as pd
import csv
import pprint as pp
from builelib.hotwatersupply import hotwatersupply
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

        # 計算モデルの作成（1系統の場合）
        
        inputdata = {
            "Building":{
                "Region": str(data[41])
            },
            "Rooms": {
                data[1]+"_"+data[2]: {
                    "floorName": data[1],
                    "roomName": data[2],
                    "buildingType": data[3],
                    "roomType": data[4],
                    "roomArea": convert2number(data[5],None)
                },
                data[12]+"_"+data[13]: {
                    "floorName": data[12],
                    "roomName": data[13],
                    "buildingType": data[14],
                    "roomType": data[15],
                    "roomArea": convert2number(data[16],None)
                }
            },
            "HotwaterRoom": {
                data[1]+"_"+data[2]: {
                    "HotwaterSystem": [
                        {
                            "UsageType": "便所",
                            "SystemName": data[8],
                            "HotWaterSavingSystem": data[7],
                            "Info": ""
                        },
                        {
                            "UsageType": "便所",
                            "SystemName": data[11],
                            "HotWaterSavingSystem": data[10],
                            "Info": ""
                        }
                    ]
                },
                data[12]+"_"+data[13]: {
                    "HotwaterSystem": [
                        {
                            "UsageType": "便所",
                            "SystemName": data[19],
                            "HotWaterSavingSystem": data[18],
                            "Info": ""
                        },
                        {
                            "UsageType": "便所",
                            "SystemName": data[22],
                            "HotWaterSavingSystem": data[21],
                            "Info": ""
                        }
                    ]
                }
            },
            "HotwaterSupplySystems":{
                data[23]: {
                    "HeatSourceUnit": [
                        {
                            "UsageType": "給湯負荷用",
                            "HeatSourceType": "ガス給湯機",
                            "Number": 1,
                            "RatedCapacity": convert2number(data[25],None),
                            "RatedPowerConsumption": 0,
                            "RatedFuelConsumption": convert2number(data[25],None) / convert2number(data[26],None)
                        }
                    ],
                    "InsulationType": data[27],
                    "PipeSize": convert2number(data[28],None),
                    "SolarSystemArea": convert2number(data[29],None),
                    "SolarSystemDirection": convert2number(data[30],None),
                    "SolarSystemAngle": convert2number(data[31],None),
                    "Info": ""
                },
                data[32]: {
                    "HeatSourceUnit": [
                        {
                            "UsageType": "給湯負荷用",
                            "HeatSourceType": "ガス給湯機",
                            "Number": 1,
                            "RatedCapacity": convert2number(data[34],None),
                            "RatedPowerConsumption": 0,
                            "RatedFuelConsumption": convert2number(data[34],None) / convert2number(data[35],None)
                        }
                    ],
                    "InsulationType": data[36],
                    "PipeSize": convert2number(data[37],None),
                    "SolarSystemArea": convert2number(data[38],None),
                    "SolarSystemDirection": convert2number(data[39],None),
                    "SolarSystemAngle": convert2number(data[40],None),
                    "Info": ""
                },
            }
        }

        # try:

        # 計算実行        
        resultJson = hotwatersupply(inputdata)

        # 期待値
        resultJson["expectedDesignValue"]   = convert2number(data[42],0)

        assert abs(resultJson["E_hotwatersupply"] - resultJson["expectedDesignValue"])   < 0.0001

        # except:
        #     assert data[42] == "err"


#### テスト実行 ####

def test_hotwatersupply_clumate_area():
    calculation('./tests/hotwatersupply/◇地域区分.txt')


if __name__ == '__main__':
    print('--- test_hotwatersupply.py ---')
