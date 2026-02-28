
import pytest
import json
import numpy as np

from builelib.climate import climate
from tests import test_utils

# テストケースの定義
testcase_dict = {
    "solar": "climate/basic_test.txt"
}

# テストケースの準備
test_to_try = []
testcase_id = []

for case_name, file_path in testcase_dict.items():
    # テストケースファイルの読み込み
    full_path = test_utils.get_test_file_path(file_path)
    testfiledata = test_utils.read_csv(full_path, delimiter=',')

    # ヘッダーの削除
    testfiledata.pop(0)

    # テストケースのループ
    for testdata in testfiledata:
        # 入力データの作成
        inputdata = (
            test_utils.convert2number(testdata[1], None),
            test_utils.convert2number(testdata[2], None),
            testdata[3]
        )

        # 期待値
        expectedvalue = (
            test_utils.convert2number(testdata[4], None),
            test_utils.convert2number(testdata[5], None),
            test_utils.convert2number(testdata[6], None),
            test_utils.convert2number(testdata[7], None)
        )

        # テストケースの追加
        test_to_try.append((inputdata, expectedvalue))
        # テストケースIDの追加
        testcase_id.append(case_name + testdata[0])


def caclulation(inputdata):
    # 入力
    alp = inputdata[0]  # alp : 方位角（真南=0, 90=西, -90=東）
    bet = inputdata[1]  # bet : 傾斜角（水平=0, 垂直=90）
    climate_area = inputdata[2]

    # データベースと気象データのディレクトリ
    # TODO: これらのパスはテストの実行場所に依存するため、より堅牢な方法で解決する必要があります。
    database_directory = "./src/builelib/database/"
    climate_directory = "./src/builelib/climate/climatedata/"

    # 地域区分データの読み込み
    with open(database_directory + 'common_area.json', 'r', encoding='utf-8') as f:
        Area = json.load(f)

    # HASP気象データの読み込み
    _, _, Iod, Ios, Inn = climate.readHaspClimateData(climate_directory +
                                    Area[climate_area + "地域"]["気象データファイル名"])

    # 方位・傾斜ごとの日射量を取得
    longi_std = 135.0  # 標準子午線の経度
    Id, _, Is, _ = climate.solarRadiationByAzimuth(
        alp,
        bet,
        Area[climate_area + "地域"]["緯度"],
        Area[climate_area + "地域"]["経度"],
        longi_std,
        Iod, Ios, Inn)

    # 年間の合計日射量 [MJ/m2], [Wh/m2], [Wh/m2], [Wh/m2]
    return np.sum((Id + Is) * 3600 / 1000000), np.sum(Id + Is), np.sum(Id), np.sum(Is)


# テスト関数の定義
@pytest.mark.parametrize('inputdata, expectedvalue', test_to_try, ids=testcase_id)
def test_calc(inputdata, expectedvalue):
    # 計算の実行
    IdIs_MJ, IdIs, Id, Is = caclulation(inputdata)

    # アサーション
    assert IdIs_MJ == pytest.approx(expectedvalue[0])
    assert IdIs == pytest.approx(expectedvalue[1])
    assert Id == pytest.approx(expectedvalue[2])
    assert Is == pytest.approx(expectedvalue[3])

if __name__ == '__main__':
    print('--- test_climate.py ---')
