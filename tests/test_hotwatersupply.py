import pandas as pd
import csv
import pprint as pp
import pytest

from builelib.systems import hotwatersupply

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


def make_inputdata(data):

    if data[3] == "物品販売業を営む店舗等":
        data[3] = "物販店舗等"
    if data[14] == "物品販売業を営む店舗等":
        data[14] = "物販店舗等"

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
            }
        },
        "HotwaterRoom": {
            data[1]+"_"+data[2]: {
                "HotwaterSystem": [
                    {
                        "UsageType": "便所",
                        "SystemName": data[8],
                        "HotWaterSavingSystem": data[7],
                        "Info": data[6]
                    }
                ]
            }
        },
        "HotwaterSupplySystems":{
        },
        "CogenerationSystems":{
        },
        "SpecialInputData":{
        }
    }

    if data[9] != "":

        inputdata["HotwaterRoom"][data[1]+"_"+data[2]]["HotwaterSystem"].append(
                {
                    "UsageType": "便所",
                    "SystemName": data[11],
                    "HotWaterSavingSystem": data[10],
                    "Info": data[9]
                }
            )

    if data[13] != "":

        inputdata["Rooms"][data[12]+"_"+data[13]] = {
                "floorName": data[12],
                "roomName": data[13],
                "buildingType": data[14],
                "roomType": data[15],
                "roomArea": convert2number(data[16],None)
            }

        inputdata["HotwaterRoom"][data[12]+"_"+data[13]] = {
                "HotwaterSystem": [
                        {
                            "UsageType": "便所",
                            "SystemName": data[19],
                            "HotWaterSavingSystem": data[18],
                            "Info": data[17]
                        }
                    ]
            }

    if data[20] != "":

        inputdata["HotwaterRoom"][data[12]+"_"+data[13]]["HotwaterSystem"].append(
                {
                    "UsageType": "便所",
                    "SystemName": data[22],
                    "HotWaterSavingSystem": data[21],
                    "Info": data[20]
                }
            )

    if data[23] != "":

        inputdata["HotwaterSupplySystems"][data[23]] = {
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
            }

    if data[32] != "":

        inputdata["HotwaterSupplySystems"][data[32]] = {
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
            }

    return inputdata


#### テストケースファイルの読み込み（換気送風機）

test_to_try  = []  # テスト用入力ファイルと期待値のリスト
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
        expectedvalue = testdata[42]

        # テストケースの集約
        test_to_try.append( (inputdata, expectedvalue) )
        # テストケース名
        testcase_id.append(case_name + testdata[0])


# テストの実施
@pytest.mark.parametrize('inputdata, expectedvalue', test_to_try, ids=testcase_id)
def test_calc(inputdata, expectedvalue):

    if expectedvalue != "err":  # passが期待されるテスト
        # 計算実行        
        resultJson = hotwatersupply.calc_energy(inputdata)

        # 比較
        assert abs(resultJson["E_hotwatersupply"] - convert2number(expectedvalue,0))   < 0.0001

    else:

        # エラーが期待される場合
        with pytest.raises(Exception):
            resultJson = hotwatersupply.calc_energy(inputdata)


if __name__ == '__main__':
    print('--- test_hotwatersupply.py ---')
