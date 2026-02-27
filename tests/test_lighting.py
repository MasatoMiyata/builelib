
import pytest
from builelib.systems import lighting
from tests import test_utils

# テストケースの定義
testcase_dict = {
    "roomDepth": 'lighting/◇奥行寸法_20190730-183436.txt',
    "roomWidth": 'lighting/◇開口寸法_20190730-183436.txt',
    "unitHeight": 'lighting/◇器具高さ_20190730-183436.txt',
    "roomDepth_error": 'lighting/◇境界値エラー側_20190730-183436.txt',
    "roomIndex": 'lighting/◇室指数_20190730-183436.txt',
    "roomArea": 'lighting/◇室面積_20190730-183436.txt',
    "unitEnergy": 'lighting/◇消費電力_20190730-183436.txt',
    "unitNum": 'lighting/◇台数_20190730-183436.txt',
    "Hotel": 'lighting/◇用途_ホテル等_20190730-183437.txt',
    "Restraunt": 'lighting/◇用途_飲食店等_20190730-183437.txt',
    "school": 'lighting/◇用途_学校等_20190730-183437.txt',
    "apartment": 'lighting/◇用途_共同住宅_20190730-183437.txt',
    "factory": 'lighting/◇用途_工場等_20190730-183437.txt',
    "office": 'lighting/◇用途_事務所等_20190730-183436.txt',
    "meetingplace": 'lighting/◇用途_集会所等_20190730-183437.txt',
    "hospital": 'lighting/◇用途_病院等_20190730-183437.txt',
    "department": 'lighting/◇用途_物品販売業を営む店舗等_20190730-183437.txt'
}

def make_inputdata(data):
    """
    照明計算用の入力データ構造を作成します。
    """
    inputdata = {
        "Building": {
            "Region": "6"
        },
        "Rooms": {
            "1F_Room": {
                "floorName": "1F",
                "roomName": "Room",
                "buildingType": data[1],
                "roomType": data[2],
                "roomArea": test_utils.convert2number(data[3], None),
            }
        },
        "LightingSystems": {
            "1F_Room": {
                "roomWidth": test_utils.convert2number(data[5], None),
                "roomDepth": test_utils.convert2number(data[6], None),
                "unitHeight": test_utils.convert2number(data[4], None),
                "roomIndex": test_utils.convert2number(data[7], None),
                "lightingUnit": {
                    "Unit1": {
                        "RatedPower": test_utils.convert2number(data[8], None),
                        "Number": test_utils.convert2number(data[9], None),
                        "OccupantSensingCTRL": data[10],
                        "IlluminanceSensingCTRL": data[11],
                        "TimeScheduleCTRL": data[12],
                        "InitialIlluminationCorrectionCTRL": data[13]
                    },
                    "Unit2": {
                        "RatedPower": test_utils.convert2number(data[14], 0),
                        "Number": test_utils.convert2number(data[15], 0),
                        "OccupantSensingCTRL": data[16],
                        "IlluminanceSensingCTRL": data[17],
                        "TimeScheduleCTRL": data[18],
                        "InitialIlluminationCorrectionCTRL": data[19]
                    }
                }
            }
        },
        "SpecialInputData": {}
    }
    return inputdata

# テストケースの準備
test_to_try = []
testcase_id = []

for case_name, file_path in testcase_dict.items():
    # テストケースファイルの読み込み
    full_path = test_utils.get_test_file_path(file_path)
    testfiledata = test_utils.read_csv(full_path, delimiter='\t')

    # ヘッダーの削除
    testfiledata.pop(0)

    # テストケースのループ
    for testdata in testfiledata:
        # 入力データの作成
        inputdata = make_inputdata(testdata)
        # 期待値
        expectedvalue = (testdata[20], testdata[21])

        # テストケースの追加
        test_to_try.append((inputdata, expectedvalue))
        # テストケースIDの追加
        testcase_id.append(case_name + testdata[0])

# テスト関数の定義
@pytest.mark.parametrize('inputdata, expectedvalue', test_to_try, ids=testcase_id)
def test_calc(inputdata, expectedvalue):
    if expectedvalue[0] != "err":
        # 計算の実行
        resultJson = lighting.calc_energy(inputdata, False)
        
        # アサーション
        assert resultJson["E_lighting"] == pytest.approx(test_utils.convert2number(expectedvalue[0], 0))
        assert resultJson["Es_lighting"] == pytest.approx(test_utils.convert2number(expectedvalue[1], 0))
    else:
        # 例外のテスト
        with pytest.raises(Exception):
            lighting.calc_energy(inputdata)

if __name__ == '__main__':
    print('--- test_lighting.py ---')
