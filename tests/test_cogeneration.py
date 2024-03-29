import pandas as pd
import csv
import pytest
import json
import xlrd

import airconditioning
import ventilation
import lighting
import hotwatersupply
import elevetor
import photovoltaic
import other_energy
import cogeneration

### テストファイル名 ###
# 辞書型 テスト名とファイル名

testcase_dict = {
    "CGS_basic": "./tests/cogeneration/★CGSテストケース一覧.xlsx",
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
    wb = xlrd.open_workbook(filename)
    sheet = wb.sheet_by_name("Sheet1")
    testdata = [sheet.row_values(row) for row in range(sheet.nrows)]

    return testdata


#### テストケースファイルの読み込み

test_to_try  = []  # テスト用入力ファイルと期待値のリスト
testcase_id  = []  # テスト名称のリスト

for case_name in testcase_dict:

    # テストファイルの読み込み
    testfiledata = read_testcasefile(testcase_dict[case_name])

    # ヘッダーの削除
    testfiledata.pop(0)

    # テストケース（行）に対するループ
    for testdata in testfiledata:

        filename = "./tests/cogeneration/" + testdata[0] + ".json"
        # 入力データの作成
        with open(filename, 'r', encoding='utf-8') as f:
            inputdata = json.load(f)

        if "SpecialInputData" not in inputdata:
            inputdata["SpecialInputData"] = {}

        # 期待値
        expectedvalue = (testdata[16])

        # テストケースの集約
        test_to_try.append( (inputdata, expectedvalue) )
        # テストケース名
        testcase_id.append(case_name + testdata[0])


# テストの実施
@pytest.mark.parametrize('inputdata, expectedvalue', test_to_try, ids=testcase_id)
def test_calc(inputdata, expectedvalue):

    # 検証用
    # with open("inputdata.json",'w', encoding='utf-8') as fw:
    #     json.dump(inputdata, fw, indent=4, ensure_ascii=False)

# 各設備の計算
    resultJson_for_CGS = {
        "AC":{},
        "V":{},
        "L":{},
        "HW":{},
        "EV":{},
        "PV":{},
        "OT":{},
    }

    # 計算実行
    if inputdata["AirConditioningZone"]:
        resultJsonAC = airconditioning.calc_energy(inputdata, DEBUG = False)
        resultJson_for_CGS["AC"] = resultJsonAC["for_CGS"]
    if inputdata["VentilationRoom"]:
        resultJsonV = ventilation.calc_energy(inputdata, DEBUG = False)
        resultJson_for_CGS["V"] = resultJsonV["for_CGS"]
    if inputdata["LightingSystems"]:
        resultJsonL = lighting.calc_energy(inputdata, DEBUG = False)
        resultJson_for_CGS["L"] = resultJsonL["for_CGS"]
    if inputdata["HotwaterRoom"]:
        resultJsonHW = hotwatersupply.calc_energy(inputdata, DEBUG = False)
        resultJson_for_CGS["HW"] = resultJsonHW["for_CGS"]
    if inputdata["Elevators"]: 
        resultJsonEV = elevetor.calc_energy(inputdata, DEBUG = False)
        resultJson_for_CGS["EV"] = resultJsonEV["for_CGS"]
    if inputdata["PhotovoltaicSystems"]:
        resultJsonPV = photovoltaic.calc_energy(inputdata, DEBUG = False)
        resultJson_for_CGS["PV"] = resultJsonPV["for_CGS"]
    if inputdata["Rooms"]:
        resultJsonOT = other_energy.calc_energy(inputdata, DEBUG = False)
        resultJson_for_CGS["OT"] = resultJsonOT["for_CGS"]

    resultJson = cogeneration.calc_energy(inputdata, resultJson_for_CGS, DEBUG = False)

    if abs( expectedvalue ) == 0:
        diff_Eac = (abs(resultJson["年間一次エネルギー削減量"] - expectedvalue)) 
    else:
        diff_Eac = (abs(resultJson["年間一次エネルギー削減量"] - expectedvalue)) / abs( expectedvalue )

    # 比較（0.01%まで）
    assert diff_Eac < 0.0001


if __name__ == '__main__':
    print('--- test_cogeneration.py ---')
