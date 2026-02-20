import pandas as pd
import csv
import pytest
import json

from builelib.systems import airconditioning

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


def make_inputdata(data):

    if data[2] == "物品販売業を営む店舗等":
        data[2] = "物販店舗等"

    if data[6] == "外壁":
        data[6] = "日の当たる外壁"
    elif data[6] == "接地壁":
        data[6] = "地盤に接する外壁_Ver2"

    if data[7] == "水平":
        data[7] = "水平（上）"

    inputdata = {
        "Building":{
            "Region": str(data[1]),
            "Coefficient_DHC": {
                "Cooling": 1.36,
                "Heating": 1.36
            },
        },
        "Rooms": {
            "1F_room1": {
                "floorName": "1F",
                "roomName": "room1",
                "buildingType": data[2],
                "roomType": data[3],
                "roomArea": convert2number(data[4],None),
                "zone": None,
            }
        },
        "EnvelopeSet": {
            "1F_room1": {
                "isAirconditioned": "有",
                "WallList": [
                    {
                        "Direction": data[7],
                        "EnvelopeArea": convert2number(data[10],None),
                        "EnvelopeWidth": None,
                        "EnvelopeHeight": None,
                        "WallSpec": "OW1",
                        "WallType": data[6],
                        "WindowList": [
                            {
                                "WindowID": "WIND1",
                                "WindowNumber": 1,
                                "isBlind": "無",
                                "EavesID": "日よけ1",
                                "Info": "無"
                            }
                        ]
                    }
                ]
            }
        },
        "WallConfigure": {
            "OW1": {
                "structureType": "木造",
                "solarAbsorptionRatio": None,
                "inputMethod": "熱貫流率を入力",
                "Uvalue": convert2number(data[12],None),
                "Info": "無"
            }
        },
        "WindowConfigure": {
            "WIND1": {
                "windowArea": convert2number(data[11],None),
                "windowWidth": None,
                "windowHeight": None,
                "inputMethod": "性能値を入力",
                "windowUvalue": convert2number(data[13],None),
                "windowIvalue": convert2number(data[14],None),
                "layerType": "単層",
                "glassUvalue": None,
                "glassIvalue": None,
                "Info": "無"
            }
        },
        "ShadingConfigure": {
            "日よけ1": {
                "shadingEffect_C": convert2number(data[8],None),
                "shadingEffect_H": convert2number(data[9],None),
                "x1": None,
                "x2": None,
                "x3": None,
                "y1": None,
                "y2": None,
                "y3": None,
                "zxPlus": None,
                "zxMinus": None,
                "zyPlus": None,
                "zyMinus": None,
                "Info": "無"
            },
        },
        "AirConditioningZone": {
            "1F_room1": {
                "isNatualVentilation": "無",
                "isSimultaneousSupply": "無",
                "AHU_cooling_insideLoad": "ACP1",
                "AHU_cooling_outdoorLoad": "ACP1",
                "AHU_heating_insideLoad": "ACP1",
                "AHU_heating_outdoorLoad": "ACP1",
                "Info": ""
            }
        },
        "HeatsourceSystem":{
            "PAC1": {
                "冷房": {
                    "StorageType": None,
                    "StorageSize": None,
                    "isStagingControl": "有",
                    "Heatsource": [
                        {
                            "HeatsourceType": "パッケージエアコンディショナ(空冷式)",
                            "Number": 1.0,
                            "SupplyWaterTempSummer": 7.0,
                            "SupplyWaterTempMiddle": 11.0,
                            "SupplyWaterTempWinter": 16.0,
                            "HeatsourceRatedCapacity": 22.4,
                            "HeatsourceRatedPowerConsumption": 6.0,
                            "HeatsourceRatedFuelConsumption": 0,
                            "PrimaryPumpPowerConsumption": 0,
                            "PrimaryPumpContolType": "無",
                            "CoolingTowerCapacity": 0,
                            "CoolingTowerFanPowerConsumption": 0,
                            "CoolingTowerPumpPowerConsumption": 0,
                            "CoolingTowerContolType": "無",
                            "Info": ""
                        }
                    ]
                },
                "暖房": {
                    "StorageType": None,
                    "StorageSize": None,
                    "isStagingControl": "有",
                    "Heatsource": [
                        {
                            "HeatsourceType": "パッケージエアコンディショナ(空冷式)",
                            "Number": 1.0,
                            "SupplyWaterTempSummer": 40,
                            "SupplyWaterTempMiddle": 40,
                            "SupplyWaterTempWinter": 40,
                            "HeatsourceRatedCapacity": 22.4,
                            "HeatsourceRatedPowerConsumption": 5,
                            "HeatsourceRatedFuelConsumption": 0,
                            "PrimaryPumpPowerConsumption": 0,
                            "PrimaryPumpContolType": "無",
                            "CoolingTowerCapacity": 0,
                            "CoolingTowerFanPowerConsumption": 0,
                            "CoolingTowerPumpPowerConsumption": 0,
                            "CoolingTowerContolType": "無",
                            "Info": ""
                        }
                    ]
                }
            },
        },
        "SecondaryPumpSystem": {
        },
        "AirHandlingSystem": {
            "ACP1": {
                "isEconomizer": "無",
                "EconomizerMaxAirVolume": None,
                "isOutdoorAirCut": "無",
                "Pump_cooling": None,
                "Pump_heating": None,
                "HeatSorce_cooling": "PAC1",
                "HeatSorce_heating": "PAC1",
                "AirHandlingUnit": [
                    {
                        "Type": "室内機",
                        "Number": 1.0,
                        "RatedCapacityCooling": 22,
                        "RatedCapacityHeating": 24,
                        "FanType": "給気",
                        "FanAirVolume": 3000.0,
                        "FanPowerConsumption": 2.2,
                        "FanControlType": "回転数制御",
                        "FanMinOpeningRate": 80.0,
                        "AirHeatExchangeRatioCooling": None,
                        "AirHeatExchangeRatioHeating": None,
                        "AirHeatExchangerEffectiveAirVolume": None,
                        "AirHeatExchangerControl": "無",
                        "AirHeatExchangerPowerConsumption": None,
                        "Info": ""
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
            
        inputdata["EnvelopeSet"]["1F_room1"]["WallList"].append(
            {
                "Direction": data[16],
                "EnvelopeArea": convert2number(data[19],None),
                "EnvelopeWidth": None,
                "EnvelopeHeight": None,
                "WallSpec": "OW2",
                "WallType": data[15],
                "WindowList": [
                    {
                        "WindowID": "WIND2",
                        "WindowNumber": 1,
                        "isBlind": "無",
                        "EavesID": "日よけ2",
                        "Info": "無"
                    }
                ]
            }
        )
        inputdata["WallConfigure"]["OW2"] = {
            "structureType": "木造",
            "solarAbsorptionRatio": None,
            "inputMethod": "熱貫流率を入力",
            "Uvalue": convert2number(data[21],None),
            "Info": "無"
        }
        inputdata["WindowConfigure"]["WIND2"] = {
            "windowArea": convert2number(data[20],None),
            "windowWidth": None,
            "windowHeight": None,
            "inputMethod": "性能値を入力",
            "windowUvalue": convert2number(data[22],None),
            "windowIvalue": convert2number(data[23],None),
            "layerType": "単層",
            "glassUvalue": None,
            "glassIvalue": None,
            "Info": "無"
        }
        inputdata["ShadingConfigure"]["日よけ2"] = {
            "shadingEffect_C": convert2number(data[17],None),
            "shadingEffect_H": convert2number(data[18],None),
            "x1": None,
            "x2": None,
            "x3": None,
            "y1": None,
            "y2": None,
            "y3": None,
            "zxPlus": None,
            "zxMinus": None,
            "zyPlus": None,
            "zyMinus": None,
            "Info": "無"
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
        expectedvalue = (testdata[24],testdata[25])

        # テストケースの集約
        test_to_try.append( (inputdata, expectedvalue) )
        # テストケース名
        testcase_id.append(case_name + testdata[0])


# テストの実施
@pytest.mark.parametrize('inputdata, expectedvalue', test_to_try, ids=testcase_id)
def test_calc(inputdata, expectedvalue):

    # 検証用
    with open("inputdata.json",'w', encoding='utf-8') as fw:
        json.dump(inputdata, fw, indent=4, ensure_ascii=False)

    if expectedvalue[0] != "err":  # passが期待されるテスト

        # 計算実行        
        resultJson = airconditioning.calc_energy(inputdata)

        if convert2number(expectedvalue[0],0) == 0:
            diff_Dc = 0
        else:
            diff_Dc = (abs(resultJson["Qroom"]["1F_room1"]["QroomDc_anual"] - convert2number(expectedvalue[0],0))) / abs( convert2number(expectedvalue[0],0) )

        if convert2number(expectedvalue[1],0) == 0:
            diff_Dh = 0
        else:
            diff_Dh = (abs(resultJson["Qroom"]["1F_room1"]["QroomDh_anual"] - convert2number(expectedvalue[1],0))) / abs( convert2number(expectedvalue[1],0) )

        # 比較（0.01%まで）
        assert diff_Dc < 0.0001
        assert diff_Dh < 0.0001

    else:

        # エラーが期待される場合
        with pytest.raises(Exception):
            resultJson = airconditioning.calc_energy(inputdata)


if __name__ == '__main__':
    print('--- test_airconditioning_load.py ---')
