import pandas as pd
import csv
import pprint as pp
from builelib.ventilation import ventilation
import pytest

### テストファイル名 ###
# 辞書型 テスト名とファイル名

testcase_dict_fan = {
    "fan_basic": "./tests/ventilation/換気送風機_仮テスト.txt",
}
testcase_dict_ac = {
    "AC_basic": "./tests/ventilation/換気代替空調機_仮テスト.txt"
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


def make_inputdata_fan(data):

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

    return inputdata


def make_inputdata_ac(data):

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

    return inputdata

#### テストケースファイルの読み込み（換気送風機）

test_to_try  = []  # テスト用入力ファイルと期待値のリスト
testcase_id  = []  # テスト名称のリスト

for case_name in testcase_dict_fan:

    # テストファイルの読み込み
    testfiledata = read_testcasefile(testcase_dict_fan[case_name])

    # ヘッダーの削除
    testfiledata.pop(0)

    # テストケース（行）に対するループ
    for testdata in testfiledata:

        # 入力データの作成
        inputdata = make_inputdata_fan(testdata)
        # 期待値
        expectedvalue = convert2number(testdata[31],0)

        # テストケースの集約
        test_to_try.append( (inputdata, expectedvalue) )
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
        inputdata = make_inputdata_ac(testdata)
        # 期待値
        expectedvalue = convert2number(testdata[54],0)

        # テストケースの集約
        test_to_try.append( (inputdata, expectedvalue) )
        # テストケース名
        testcase_id.append(case_name + testdata[0])



# テストの実施
@pytest.mark.parametrize('inputdata, expectedvalue', test_to_try, ids=testcase_id)
def test_calc(inputdata, expectedvalue):

    if expectedvalue != "err":  # passが期待されるテスト
        # 計算実行        
        resultJson = ventilation(inputdata)

        # 比較
        assert abs(resultJson["E_ventilation"] - expectedvalue)   < 0.0001

    else:

        # エラーが期待される場合
        with pytest.raises(Exception):
            resultJson = ventilation(inputdata)



if __name__ == '__main__':
    print('--- test_vetilation.py ---')
