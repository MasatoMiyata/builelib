import json

import pytest
import xlrd

from builelib import airconditioning
from builelib import commons as bc

### テストファイル名 ###
# 辞書型 テスト名とファイル名

testcase_dict = {
    "basic": "./tests/airconditioning_gshp_openloop/★地中熱クローズループ_テストケース一覧.xlsx",
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

test_to_try = []  # テスト用入力ファイルと期待値のリスト
testcase_id = []  # テスト名称のリスト

for case_name in testcase_dict:

    # テストファイルの読み込み
    testfiledata = read_testcasefile(testcase_dict[case_name])

    # ヘッダーの削除
    testfiledata.pop(0)

    resultALL = {}

    # テストケース（行）に対するループ
    for testdata in testfiledata:
        filename = "./tests/airconditioning_gshp_openloop/AC_gshp_closeloop_base.json"
        # 入力データの読み込み
        with open(filename, 'r', encoding='utf-8') as f:
            inputdata = json.load(f)

        # 地域
        inputdata["Building"]["Region"] = str(testdata[3]).replace("地域", "")
        # 冷熱源
        inputdata["HeatsourceSystem"]["PAC1"]["冷房"]["Heatsource"][0]["HeatsourceType"] = testdata[1]
        # 温熱源
        inputdata["HeatsourceSystem"]["PAC1"]["暖房"]["Heatsource"][0]["HeatsourceType"] = testdata[2]

        # 期待値
        expectedvalue = (testdata[4])

        # テストケースの集約
        test_to_try.append((inputdata, expectedvalue))
        # テストケース名
        testcase_id.append(case_name + testdata[0])


# テストの実施
@pytest.mark.parametrize('inputdata, expectedvalue', test_to_try, ids=testcase_id)
def test_calc(inputdata, expectedvalue):
    # 計算実行
    resultJson = airconditioning.calc_energy(inputdata)

    diff_Eac = (abs(resultJson["E_airconditioning"] - expectedvalue)) / abs(expectedvalue)

    # 比較（0.01%まで）
    assert diff_Eac < 0.0001


if __name__ == '__main__':

    print('--- test_airconditioning_openloop.py ---')

    ### 期待値の作成（親ディレクトリに移動してから実行すること）

    for case_name in testcase_dict:

        # テストファイルの読み込み
        testfiledata = read_testcasefile(testcase_dict[case_name])

        # ヘッダーの削除
        testfiledata.pop(0)

        resultALL = {}

        # テストケース（行）に対するループ
        for testdata in testfiledata:
            filename = "./tests/airconditioning_gshp_openloop/AC_gshp_closeloop_base.json"
            # 入力データの読み込み
            with open(filename, 'r', encoding='utf-8') as f:
                inputdata = json.load(f)

            # 地域
            inputdata["Building"]["Region"] = str(testdata[3]).replace("地域", "")
            # 冷熱源
            inputdata["HeatsourceSystem"]["PAC1"]["冷房"]["Heatsource"][0]["HeatsourceType"] = testdata[1]
            # 温熱源
            inputdata["HeatsourceSystem"]["PAC1"]["暖房"]["Heatsource"][0]["HeatsourceType"] = testdata[2]

            # 実行
            resultJson = airconditioning.calc_energy(inputdata)

            # 結果
            resultALL = [
                str(resultJson["E_airconditioning"]),
                str(resultJson["ENERGY"]["E_fan"] * bc.fprime),
                str(resultJson["ENERGY"]["E_aex"] * bc.fprime),
                str(resultJson["ENERGY"]["E_pump"] * bc.fprime),
                str(resultJson["ENERGY"]["E_refsysr"]),
                str(resultJson["ENERGY"]["E_refac"] * bc.fprime),
                str(resultJson["ENERGY"]["E_pumpP"] * bc.fprime),
                str(resultJson["ENERGY"]["E_ctfan"] * bc.fprime),
                str(resultJson["ENERGY"]["E_ctpump"] * bc.fprime)
            ]

            with open("resultALL.txt", 'a', encoding='utf-8') as fw:
                fw.write(testdata[0] + ",")
                fw.write(",".join(resultALL))
                fw.write("\n")
