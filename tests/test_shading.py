import csv

from builelib import shading


# 計算の実行
def calculation(filename):
    print(filename)  # 確認用

    # テスト用データの読み込み
    with open(filename, mode='r', newline='', encoding='utf-8') as f:
        tsv_reader = csv.reader(f, delimiter=',')
        testdata = [row for row in tsv_reader]

    # ヘッダーを削除
    testdata.pop(0)

    for data in testdata:

        print("ケース " + str(data[0]) + "を実行中")  # 確認用

        AREA = str(data[1])
        Direction = str(data[2])
        x1 = float(data[3])
        x2 = float(data[4])
        x3 = float(data[5])
        y1 = float(data[6])
        y2 = float(data[7])
        y3 = float(data[8])
        zxp = float(data[9])
        zxm = float(data[10])
        zyp = float(data[11])
        zym = float(data[12])

        try:

            # 計算実行        
            r_wind_SUM, r_wind_WIN = shading.calc_shadingCoefficient(AREA, Direction, x1, x2, x3, y1, y2, y3, zxp, zxm,
                                                                     zyp, zym)

            # 期待値
            expected_r_wind_SUM = float(data[14])
            expected_r_wind_WIN = float(data[15])

            assert (r_wind_SUM - expected_r_wind_SUM) < 0.0001
            assert (r_wind_WIN - expected_r_wind_WIN) < 0.0001

        except:

            print("ケース " + str(data[0]) + "でエラー発生")  # 確認用
            print(data[13])
            assert data[13] == "ERR"


# 5分かかります
def test_case1():
    calculation('./tests/shading/shading_test1.csv')


# 25分かかります
# def test_case2():
#     calculation('./tests/shading/shading_test2.csv')

if __name__ == '__main__':
    print('--- test_shading.py ---')
    calculation('./tests/shading/shading_test1.csv')
