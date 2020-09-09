import pandas as pd
import csv
import pprint as pp
import pytest
import json
import numpy as np

from builelib import climate

### テストファイル名 ###
# 辞書型 テスト名とファイル名

testcase_dict = {
    "solar": "./tests/climate/basic_test.txt"
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
        inputdata = (
            convert2number(testdata[1],None), 
            convert2number(testdata[2],None), 
            testdata[3]
            )

        # 期待値
        expectedvalue = (
            convert2number(testdata[4],None),
            convert2number(testdata[5],None),
            convert2number(testdata[6],None),
            convert2number(testdata[7],None)
            )

        # テストケースの集約
        test_to_try.append( (inputdata, expectedvalue) )
        # テストケース名
        testcase_id.append(case_name + testdata[0])


def caclulation(inputdata):

    # 入力
    alp = inputdata[0]  # alp : 方位角（0が南、45が南西、180が北）
    bet = inputdata[1]  # bet : 傾斜角（0が水平、90が垂直）
    climate_area = inputdata[2]

    print(alp)
    print(bet)

    database_directory = "./builelib/database/"
    climate_directory = "./builelib/climatedata/"

    # 地域別データの読み込み
    with open(database_directory + 'AREA.json', 'r') as f:
        Area = json.load(f)

    # 直達日射量、天空日射量 [W/m2]
    _, _, Iod, Ios, Inn = climate.readHaspClimateData(climate_directory + "C1_" +
                                    Area[climate_area+"地域"]["気象データファイル名"])

    # np.savetxt("直達日射量.txt", Iod)
    # np.savetxt("天空日射量.txt", Ios)
    # print(Area[climate_area+"地域"]["緯度"])
    # print(Area[climate_area+"地域"]["経度"])

    # 日積算日射量 [Wh/m2/day]
    Id, _, Is, _  = climate.solarRadiationByAzimuth( \
        alp, \
        bet, \
        Area[climate_area+"地域"]["緯度"], \
        Area[climate_area+"地域"]["経度"], \
        Iod, Ios, Inn)

    # np.savetxt("積算直達日射量.txt", Id)
    # np.savetxt("積算天空日射量.txt", Is)

    # 方位面日射量 [MJ/m2day], 方位面日射量 [Wh/m2day],方位面直達日射量 [Wh/m2day],方位面天空日射量 [Wh/m2day],  
    return np.sum( (Id + Is)*3600/1000000 ), np.sum(Id + Is), np.sum(Id), np.sum(Is)


# テストの実施
@pytest.mark.parametrize('inputdata, expectedvalue', test_to_try, ids=testcase_id)
def test_calc(inputdata, expectedvalue):

    # 計算実行        
    IdIs_MJ, IdIs, Id, Is  = caclulation(inputdata)

    # 比較
    assert abs(IdIs_MJ - expectedvalue[0]) < 0.0001
    assert abs(IdIs - expectedvalue[1]) < 0.0001
    assert abs(Id - expectedvalue[2]) < 0.0001
    assert abs(Is - expectedvalue[3]) < 0.0001

if __name__ == '__main__':
    print('--- test_climate.py ---')