import csv

import pytest

from builelib import lighting

### テストファイル名 ###
# 辞書型 テスト名とファイル名

testcase_dict = {
    "room_depth": './tests/lighting/◇奥行寸法_20190730-183436.txt',
    "room_width": './tests/lighting/◇開口寸法_20190730-183436.txt',
    "unit_height": './tests/lighting/◇器具高さ_20190730-183436.txt',
    "room_depth": './tests/lighting/◇境界値エラー側_20190730-183436.txt',
    "room_index": './tests/lighting/◇室指数_20190730-183436.txt',
    "room_area": './tests/lighting/◇室面積_20190730-183436.txt',
    "unitEnergy": './tests/lighting/◇消費電力_20190730-183436.txt',
    "unitNum": './tests/lighting/◇台数_20190730-183436.txt',
    "hotel": './tests/lighting/◇用途_ホテル等_20190730-183437.txt',
    "Restraunt": './tests/lighting/◇用途_飲食店等_20190730-183437.txt',
    "school": './tests/lighting/◇用途_学校等_20190730-183437.txt',
    "apartment": './tests/lighting/◇用途_共同住宅_20190730-183437.txt',
    "factory": './tests/lighting/◇用途_工場等_20190730-183437.txt',
    "office": './tests/lighting/◇用途_事務所等_20190730-183436.txt',
    "meetingplace": './tests/lighting/◇用途_集会所等_20190730-183437.txt',
    "hospital": './tests/lighting/◇用途_病院等_20190730-183437.txt',
    "department": './tests/lighting/◇用途_物品販売業を営む店舗等_20190730-183437.txt'
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


def make_input_data(data):
    '''
    インプットデータを作成する関数
    '''
    input_data = {
        "building": {
            "region": "6"
        },
        "rooms": {
            "1F_室": {
                "floorname": "1F",
                "roomname": "室",
                "building_type": data[1],
                "room_type": data[2],
                "room_area": convert2number(data[3], None),
            }
        },
        "lighting_systems": {
            "1F_室": {
                "room_width": convert2number(data[5], None),
                "room_depth": convert2number(data[6], None),
                "unit_height": convert2number(data[4], None),
                "room_index": convert2number(data[7], None),
                "lighting_unit": {
                    "照明1": {
                        "rated_power": convert2number(data[8], None),
                        "number": convert2number(data[9], None),
                        "occupant_sensing_ctrl": data[10],
                        "illuminance_sensing_ctrl": data[11],
                        "time_schedule_ctrl": data[12],
                        "initial_illumination_correction_ctrl": data[13]
                    },
                    "照明2": {
                        "rated_power": convert2number(data[14], 0),
                        "number": convert2number(data[15], 0),
                        "occupant_sensing_ctrl": data[16],
                        "illuminance_sensing_ctrl": data[17],
                        "time_schedule_ctrl": data[18],
                        "initial_illumination_correction_ctrl": data[19]
                    }
                }
            }
        },
        "special_input_data": {
        }
    }

    return input_data


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
        # 入力データの作成
        input_data = make_input_data(testdata)
        # 期待値
        expectedvalue = (testdata[20], testdata[21])

        # テストケースの集約
        test_to_try.append((input_data, expectedvalue))
        # テストケース名
        testcase_id.append(case_name + testdata[0])


# テストの実施
@pytest.mark.parametrize('input_data, expectedvalue', test_to_try, ids=testcase_id)
def test_calc(input_data, expectedvalue):
    if expectedvalue[0] != "err":  # passが期待されるテスト

        # 計算実行        
        result_json = lighting.calc_energy(input_data, True)
        # 比較
        assert abs(result_json["E_lighting"] - convert2number(expectedvalue[0], 0)) < 0.0001
        assert abs(result_json["Es_lighting"] - convert2number(expectedvalue[1], 0)) < 0.0001

    else:

        print(expectedvalue[0])

        # # エラーが期待される場合
        # with pytest.raises(Exception):
        #     result_json = lighting.calc_energy(input_data)


if __name__ == '__main__':
    print('--- test_lighting.py ---')
