
import pytest
from builelib.systems import elevator as elevetor
from tests import test_utils

# テストケースの定義
testcase_dict = {
    "office": "elevetor/◇事務所テスト.txt",
    "office_2units": "elevetor/◇事務所テスト1室2系.txt"
}

def make_inputdata(data):
    """
    テストデータから入力辞書を作成します。
    """
    if (data[11] == "") and (data[16] == ""):
        # 設計モデルの作成（1室1系統の場合）
        inputdata = {
            "Building": {"Region": "6"},
            "Rooms": {
                "1F_Room": {
                    "floorName": data[1],
                    "roomName": data[2],
                    "buildingType": data[3],
                    "roomType": data[4],
                    "roomArea": 100,
                }
            },
            "Elevators": {
                "1F_Room": {
                    "Elevator": [
                        {
                            "ElevatorName": data[5],
                            "Number": test_utils.convert2number(data[6], 0),
                            "LoadLimit": test_utils.convert2number(data[7], 0),
                            "Velocity": test_utils.convert2number(data[8], 0),
                            "TransportCapacityFactor": test_utils.convert2number(data[9], 0),
                            "ControlType": data[10],
                            "Info": ""
                        }
                    ]
                }
            },
            "SpecialInputData": {}
        }
    elif (data[11] == ""):
        # 設計モデルの作成（1室2系統の場合）
        inputdata = {
            "Building": {"Region": "6"},
            "Rooms": {
                "1F_Room": {
                    "floorName": data[1],
                    "roomName": data[2],
                    "buildingType": data[3],
                    "roomType": data[4],
                    "roomArea": 100,
                }
            },
            "Elevators": {
                "1F_Room": {
                    "Elevator": [
                        {
                            "ElevatorName": data[5],
                            "Number": test_utils.convert2number(data[6], 0),
                            "LoadLimit": test_utils.convert2number(data[7], 0),
                            "Velocity": test_utils.convert2number(data[8], 0),
                            "TransportCapacityFactor": test_utils.convert2number(data[9], 0),
                            "ControlType": data[10],
                            "Info": ""
                        },
                        {
                            "ElevatorName": data[15],
                            "Number": test_utils.convert2number(data[16], 0),
                            "LoadLimit": test_utils.convert2number(data[17], 0),
                            "Velocity": test_utils.convert2number(data[18], 0),
                            "TransportCapacityFactor": test_utils.convert2number(data[19], 0),
                            "ControlType": data[20],
                            "Info": ""
                        }
                    ]
                }
            },
            "SpecialInputData": {}
        }
    else:
        # 設計モデルの作成（複数室の場合）
        inputdata = {
            "Building": {"Region": "6"},
            "Rooms": {
                "1F_Room": {
                    "floorName": data[1],
                    "roomName": data[2],
                    "buildingType": data[3],
                    "roomType": data[4],
                    "roomArea": 100,
                },
                "2F_Room": {
                    "floorName": data[11],
                    "roomName": data[12],
                    "buildingType": data[13],
                    "roomType": data[14],
                    "roomArea": 100,
                },
            },
            "Elevators": {
                "1F_Room": {
                    "Elevator": [
                        {
                            "ElevatorName": data[5],
                            "Number": test_utils.convert2number(data[6], 0),
                            "LoadLimit": test_utils.convert2number(data[7], 0),
                            "Velocity": test_utils.convert2number(data[8], 0),
                            "TransportCapacityFactor": test_utils.convert2number(data[9], 0),
                            "ControlType": data[10],
                            "Info": ""
                        }
                    ]
                },
                "2F_Room": {
                    "Elevator": [
                        {
                            "ElevatorName": data[15],
                            "Number": test_utils.convert2number(data[16], 0),
                            "LoadLimit": test_utils.convert2number(data[17], 0),
                            "Velocity": test_utils.convert2number(data[18], 0),
                            "TransportCapacityFactor": test_utils.convert2number(data[19], 0),
                            "ControlType": data[20],
                            "Info": ""
                        }
                    ]
                },
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
    testfiledata = test_utils.read_csv(full_path, delimiter=',')
    
    # ヘッダーの削除
    testfiledata.pop(0)

    # テストケースのループ
    for testdata in testfiledata:
        # 入力データの作成
        inputdata = make_inputdata(testdata)
        # 期待値
        expectedvalue = test_utils.convert2number(testdata[21], 0)

        # テストケースの追加
        test_to_try.append((inputdata, expectedvalue))
        # テストケースIDの追加
        testcase_id.append(case_name + testdata[0])

# テスト関数の定義
@pytest.mark.parametrize('inputdata, expectedvalue', test_to_try, ids=testcase_id)
def test_calc(inputdata, expectedvalue):
    if expectedvalue != "err":
        # 計算の実行
        resultJson = elevetor.calc_energy(inputdata)
        # アサーション
        assert resultJson["E_elevator"] == pytest.approx(expectedvalue)
    else:
        # 例外のテスト
        with pytest.raises(Exception):
            elevetor.calc_energy(inputdata)

if __name__ == '__main__':
    print('--- test_elevetor.py ---')
