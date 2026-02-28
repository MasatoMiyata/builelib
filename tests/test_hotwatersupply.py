import csv
import pytest
from pathlib import Path
from builelib.systems import hotwatersupply
from tests.test_utils import convert2number

# テストケースファイルのディレクトリ
TEST_DATA_DIR = Path(__file__).parent / "hotwatersupply"

# テストケースの定義
TEST_CASES = {
    "basic_test": "◇基本ケース.txt",
    "office": "◇事務所ケース.txt",
    "office_complex": "◇事務所_複合ケース.txt",
}

def read_testcasefile(filename):
    """テストケースファイルを読み込む関数"""
    with open(filename, mode='r', newline='', encoding='shift-jis') as f:
        tsv_reader = csv.reader(f, delimiter=',')
        # ヘッダーをスキップ
        next(tsv_reader)
        return [row for row in tsv_reader]

def make_inputdata(data):
    """CSVの行データから入力データを作成する"""
    # データのコピーを作成して元のデータを変更しないようにする
    row = list(data)
    
    if row[3] == "物品販売業を営む店舗等":
        row[3] = "物販店舗等"
    if row[14] == "物品販売業を営む店舗等":
        row[14] = "物販店舗等"

    inputdata = {
        "Building": {
            "Region": str(row[41])
        },
        "Rooms": {
            f"{row[1]}_{row[2]}": {
                "floorName": row[1],
                "roomName": row[2],
                "buildingType": row[3],
                "roomType": row[4],
                "roomArea": convert2number(row[5], None)
            }
        },
        "HotwaterRoom": {
            f"{row[1]}_{row[2]}": {
                "HotwaterSystem": [
                    {
                        "UsageType": row[6],
                        "SystemName": row[8],
                        "HotWaterSavingSystem": row[7],
                        "Info": ""
                    }
                ]
            }
        },
        "HotwaterSupplySystems": {},
        "CogenerationSystems": {},
        "SpecialInputData": {}
    }

    # 2つ目の給湯システム（部屋1）
    if row[9] != "":
        inputdata["HotwaterRoom"][f"{row[1]}_{row[2]}"]["HotwaterSystem"].append(
            {
                "UsageType": row[9],
                "SystemName": row[11],
                "HotWaterSavingSystem": row[10],
                "Info": ""
            }
        )

    # 2つ目の部屋
    if row[13] != "":
        inputdata["Rooms"][f"{row[12]}_{row[13]}"] = {
            "floorName": row[12],
            "roomName": row[13],
            "buildingType": row[14],
            "roomType": row[15],
            "roomArea": convert2number(row[16], None)
        }

        inputdata["HotwaterRoom"][f"{row[12]}_{row[13]}"] = {
            "HotwaterSystem": [
                {
                    "UsageType": row[17],
                    "SystemName": row[19],
                    "HotWaterSavingSystem": row[18],
                    "Info": ""
                }
            ]
        }

    # 2つ目の給湯システム（部屋2）
    if row[20] != "":
        inputdata["HotwaterRoom"][f"{row[12]}_{row[13]}"]["HotwaterSystem"].append(
            {
                "UsageType": row[20],
                "SystemName": row[22],
                "HotWaterSavingSystem": row[21],
                "Info": ""
            }
        )

    # 給湯設備1
    if row[23] != "":
        inputdata["HotwaterSupplySystems"][row[23]] = {
            "HeatSourceUnit": [
                {
                    "UsageType": "給湯負荷用",
                    "HeatSourceType": "ガス給湯機",
                    "Number": 1,
                    "RatedCapacity": convert2number(row[25], None),
                    "RatedPowerConsumption": 0,
                    "RatedFuelConsumption": convert2number(row[25], None) / convert2number(row[26], None)
                }
            ],
            "InsulationType": row[27],
            "PipeSize": convert2number(row[28], None),
            "SolarSystemArea": convert2number(row[29], None),
            "SolarSystemDirection": convert2number(row[30], None),
            "SolarSystemAngle": convert2number(row[31], None),
            "Info": ""
        }

    # 給湯設備2
    if row[32] != "":
        inputdata["HotwaterSupplySystems"][row[32]] = {
            "HeatSourceUnit": [
                {
                    "UsageType": "給湯負荷用",
                    "HeatSourceType": "ガス給湯機",
                    "Number": 1,
                    "RatedCapacity": convert2number(row[34], None),
                    "RatedPowerConsumption": 0,
                    "RatedFuelConsumption": convert2number(row[34], None) / convert2number(row[35], None)
                }
            ],
            "InsulationType": row[36],
            "PipeSize": convert2number(row[37], None),
            "SolarSystemArea": convert2number(row[38], None),
            "SolarSystemDirection": convert2number(row[39], None),
            "SolarSystemAngle": convert2number(row[40], None),
            "Info": ""
        }

    return inputdata

def get_test_data():
    """テストデータを生成する"""
    test_to_try = []
    testcase_ids = []

    for case_name, filename in TEST_CASES.items():
        filepath = TEST_DATA_DIR / filename
        if not filepath.exists():
            continue

        testfiledata = read_testcasefile(filepath)

        for row in testfiledata:
            # 入力データの作成
            inputdata = make_inputdata(row)
            # 期待値
            expectedvalue = row[42]

            test_to_try.append((inputdata, expectedvalue))
            testcase_ids.append(f"{case_name}_{row[0]}")
            
    return test_to_try, testcase_ids

# テストデータの読み込み
test_data, test_ids = get_test_data()

@pytest.mark.parametrize("inputdata, expectedvalue", test_data, ids=test_ids)
def test_calc(inputdata, expectedvalue):
    if expectedvalue != "err":
        # 計算実行
        resultJson = hotwatersupply.calc_energy(inputdata)
        # 比較
        assert resultJson["設計一次エネルギー消費量[GJ/年]"] == pytest.approx(convert2number(expectedvalue, 0))
    else:
        # エラーが期待される場合
        with pytest.raises(Exception):
            hotwatersupply.calc_energy(inputdata)

if __name__ == '__main__':
    pytest.main(["-q", __file__])
