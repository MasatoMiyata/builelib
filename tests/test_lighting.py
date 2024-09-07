import pandas as pd
import csv
import pprint as pp
import pytest

from builelib import lighting

### テストファイル名 ###
# 辞書型 テスト名とファイル名

testcase_dict = {
    "roomDepth":'./tests/lighting/◇奥行寸法_20190730-183436.txt',
    "roomWidth":'./tests/lighting/◇開口寸法_20190730-183436.txt',
    "unitHeight":'./tests/lighting/◇器具高さ_20190730-183436.txt',
    "roomDepth":'./tests/lighting/◇境界値エラー側_20190730-183436.txt',
    "roomIndex":'./tests/lighting/◇室指数_20190730-183436.txt',
    "roomArea":'./tests/lighting/◇室面積_20190730-183436.txt',
    "unitEnergy":'./tests/lighting/◇消費電力_20190730-183436.txt',
    "unitNum":'./tests/lighting/◇台数_20190730-183436.txt',
    "Hotel":'./tests/lighting/◇用途_ホテル等_20190730-183437.txt',
    "Restraunt":'./tests/lighting/◇用途_飲食店等_20190730-183437.txt',
    "school":'./tests/lighting/◇用途_学校等_20190730-183437.txt',
    "apartment":'./tests/lighting/◇用途_共同住宅_20190730-183437.txt',
    "factory":'./tests/lighting/◇用途_工場等_20190730-183437.txt',
    "office":'./tests/lighting/◇用途_事務所等_20190730-183436.txt',
    "meetingplace":'./tests/lighting/◇用途_集会所等_20190730-183437.txt',
    "hospital":'./tests/lighting/◇用途_病院等_20190730-183437.txt',
    "department":'./tests/lighting/◇用途_物品販売業を営む店舗等_20190730-183437.txt'
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
        tsv_reader = csv.reader(f, delimiter='\t')
        testdata = [row for row in tsv_reader]
    return testdata


def make_inputdata(data):
    '''
    インプットデータを作成する関数
    '''
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
                "roomArea": convert2number(data[3],None),
            }
        },
        "LightingSystems": {
            "1F_室": {
                "roomWidth": convert2number(data[5],None),
                "roomDepth": convert2number(data[6],None),
                "unitHeight": convert2number(data[4],None),
                "roomIndex": convert2number(data[7],None),
                "lightingUnit": {
                    "照明1": {
                        "RatedPower": convert2number(data[8],None),
                        "Number": convert2number(data[9],None),
                        "OccupantSensingCTRL": data[10],
                        "IlluminanceSensingCTRL": data[11],
                        "TimeScheduleCTRL": data[12],
                        "InitialIlluminationCorrectionCTRL": data[13]
                    },
                    "照明2": {
                        "RatedPower": convert2number(data[14],0),
                        "Number": convert2number(data[15],0),
                        "OccupantSensingCTRL": data[16],
                        "IlluminanceSensingCTRL": data[17],
                        "TimeScheduleCTRL": data[18],
                        "InitialIlluminationCorrectionCTRL": data[19]
                    }
                }
            }
        },
        "SpecialInputData":{
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
        expectedvalue = (testdata[20], testdata[21])

        # テストケースの集約
        test_to_try.append( (inputdata, expectedvalue) )
        # テストケース名
        testcase_id.append(case_name + testdata[0])


# テストの実施
@pytest.mark.parametrize('inputdata, expectedvalue', test_to_try, ids=testcase_id)
def test_calc(inputdata, expectedvalue):

    if expectedvalue[0] != "err":  # passが期待されるテスト

        # 計算実行        
        resultJson = lighting.calc_energy(inputdata, True)
        # 比較
        assert abs(resultJson["E_lighting"] - convert2number(expectedvalue[0],0))   < 0.0001
        assert abs(resultJson["Es_lighting"] - convert2number(expectedvalue[1],0))   < 0.0001

    else:

        print(expectedvalue[0])

        # # エラーが期待される場合
        # with pytest.raises(Exception):
        #     resultJson = lighting.calc_energy(inputdata)


if __name__ == '__main__':
    print('--- test_lighting.py ---')