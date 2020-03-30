import pandas as pd
import csv
import pprint as pp
from builelib.lighting import lighting
import jsonschema

# CSVを読み込む関数
def readCSVfile(filename):
    data = pd.read_csv(
        filepath_or_buffer=filename, sep='\t'
        )
    return data

# 空欄にデフォルト値を代入する
def convert2number(x, default):
    if x == "":
        x = default
    else:
        x = float(x)
    return x

# 計算の実行
def calculation(filename):

    print(filename) # 確認用

    # テスト用データの読み込み
    with open(filename, mode='r', newline='', encoding='shift-jis') as f:
        tsv_reader = csv.reader(f, delimiter='\t')
        testdata = [row for row in tsv_reader]

    # ヘッダーを削除
    testdata.pop(0)

    for data in testdata:

        print(data) # 確認用

        # 計算モデルの作成
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
                            "RatedPower": convert2number(data[8],0),
                            "Number": convert2number(data[9],0),
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
            }
        }

        try:

            # 計算実行        
            resultJson = lighting(inputdata)

            # 期待値
            resultJson["expectedDesignValue"]   = convert2number(data[20],0)
            resultJson["expectedStandardValue"] = convert2number(data[21],0)

            assert (resultJson["E_lighting"] - resultJson["expectedDesignValue"])   < 0.000001
            assert (resultJson["Es_lighting"] - resultJson["expectedStandardValue"]) < 0.000001

        except:
        
            assert data[20] == "err"



#### テスト実行 ####

def test_roomDepth():
    calculation('./tests/lighting/◇奥行寸法_20190730-183436.txt')

def test_roomWidth():
    calculation('./tests/lighting/◇開口寸法_20190730-183436.txt')

def test_unitHeight():
    calculation('./tests/lighting/◇器具高さ_20190730-183436.txt')

def test_roomDepth():
    calculation('./tests/lighting/◇境界値エラー側_20190730-183436.txt')

def test_roomIndex():
    calculation('./tests/lighting/◇室指数_20190730-183436.txt')

def test_roomArea():
    calculation('./tests/lighting/◇室面積_20190730-183436.txt')

def test_unitEnergy():
    calculation('./tests/lighting/◇消費電力_20190730-183436.txt')

def test_unitNum():
    calculation('./tests/lighting/◇台数_20190730-183436.txt')

def test_Hotel():
    calculation('./tests/lighting/◇用途_ホテル等_20190730-183437.txt')

def test_Restraunt():
    calculation('./tests/lighting/◇用途_飲食店等_20190730-183437.txt')

def test_school():
    calculation('./tests/lighting/◇用途_学校等_20190730-183437.txt')

def test_apartment():
    calculation('./tests/lighting/◇用途_共同住宅_20190730-183437.txt')

def test_factory():
    calculation('./tests/lighting/◇用途_工場等_20190730-183437.txt')

def test_office():
    calculation('./tests/lighting/◇用途_事務所等_20190730-183436.txt')

def test_meetingplace():
    calculation('./tests/lighting/◇用途_集会所等_20190730-183437.txt')

def test_hospital():
    calculation('./tests/lighting/◇用途_病院等_20190730-183437.txt')

def test_department():
    calculation('./tests/lighting/◇用途_物品販売業を営む店舗等_20190730-183437.txt')

if __name__ == '__main__':
    print('--- test_lighting.py ---')