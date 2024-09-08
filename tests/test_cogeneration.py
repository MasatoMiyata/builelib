import json

import other_energy
import pytest
import xlrd

import airconditioning
import cogeneration
import elevetor
import hotwatersupply
import lighting
import photovoltaic
import ventilation

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

test_to_try = []  # テスト用入力ファイルと期待値のリスト
testcase_id = []  # テスト名称のリスト

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
            input_data = json.load(f)

        if "special_input_data" not in input_data:
            input_data["special_input_data"] = {}

        # 期待値
        expectedvalue = (testdata[16])

        # テストケースの集約
        test_to_try.append((input_data, expectedvalue))
        # テストケース名
        testcase_id.append(case_name + testdata[0])


# テストの実施
@pytest.mark.parametrize('input_data, expectedvalue', test_to_try, ids=testcase_id)
def test_calc(input_data, expectedvalue):
    # 検証用
    # with open("input_data.json",'w', encoding='utf-8') as fw:
    #     json.dump(input_data, fw, indent=4, ensure_ascii=False)

    # 各設備の計算
    result_json_for_cgs = {
        "AC": {},
        "V": {},
        "L": {},
        "HW": {},
        "EV": {},
        "PV": {},
        "OT": {},
    }

    # 計算実行
    if input_data["air_conditioning_zone"]:
        result_jsonAC = airconditioning.calc_energy(input_data, DEBUG=False)
        result_json_for_cgs["AC"] = result_jsonAC["for_cgs"]
    if input_data["ventilation_room"]:
        result_jsonV = ventilation.calc_energy(input_data, DEBUG=False)
        result_json_for_cgs["V"] = result_jsonV["for_cgs"]
    if input_data["lighting_systems"]:
        result_jsonL = lighting.calc_energy(input_data, DEBUG=False)
        result_json_for_cgs["L"] = result_jsonL["for_cgs"]
    if input_data["hot_water_room"]:
        result_jsonhW = hotwatersupply.calc_energy(input_data, DEBUG=False)
        result_json_for_cgs["HW"] = result_jsonhW["for_cgs"]
    if input_data["elevators"]:
        result_jsonEV = elevetor.calc_energy(input_data, DEBUG=False)
        result_json_for_cgs["EV"] = result_jsonEV["for_cgs"]
    if input_data["photovoltaic_systems"]:
        result_jsonPV = photovoltaic.calc_energy(input_data, DEBUG=False)
        result_json_for_cgs["PV"] = result_jsonPV["for_cgs"]
    if input_data["rooms"]:
        result_jsonOT = other_energy.calc_energy(input_data, DEBUG=False)
        result_json_for_cgs["OT"] = result_jsonOT["for_cgs"]

    result_json = cogeneration.calc_energy(input_data, result_json_for_cgs, DEBUG=False)

    if abs(expectedvalue) == 0:
        diff_Eac = (abs(result_json["年間一次エネルギー削減量"] - expectedvalue))
    else:
        diff_Eac = (abs(result_json["年間一次エネルギー削減量"] - expectedvalue)) / abs(expectedvalue)

    # 比較（0.01%まで）
    assert diff_Eac < 0.0001


if __name__ == '__main__':
    print('--- test_cogeneration.py ---')
