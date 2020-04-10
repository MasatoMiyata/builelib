#%%
import csv
import numpy as np

# hasファイルを読み込む関数
def readHaspClimateData(filename):

    # hasファイルの読み込み
    with open(filename) as f:
        hasData = f.readlines()

    Tout = list()   # 最終的に365×24の行列になる。
    Xout = list()   # 最終的に365×24の行列になる。
    Iod  = list()   # 最終的に365×24の行列になる。
    Ios  = list()   # 最終的に365×24の行列になる。
    Inn  = list()   # 最終的に365×24の行列になる。

    for line in hasData:

        # 初期化
        tmp = []

        if line[-2] == '1':    # 外気温 [℃]

            # 時刻別の気温を読み込み、格納
            for hh in range(0,24):
                tmp.append((float(line[3*hh:3*(hh+1)])-500)/10)
            Tout.append(tmp)

        elif line[-2] == '2':    # 外気絶対湿度 [kg/kgDA]

            # 時刻別の湿度を読み込み、格納
            for hh in range(0,24):
                tmp.append((float(line[3*hh:3*(hh+1)])/1000)/10)
            Xout.append(tmp)

        elif line[-2] == '3':    # 法線面直達日射量 [kcal/m2h]

            # 時刻別の湿度を読み込み、格納
            for hh in range(0,24):
                tmp.append((float(line[3*hh:3*(hh+1)])))
            Iod.append(tmp)

        elif line[-2] == '4':    # 水平面天空日射量 [kcal/m2h]

            # 時刻別の湿度を読み込み、格納
            for hh in range(0,24):
                tmp.append((float(line[3*hh:3*(hh+1)])))
            Ios.append(tmp)

        elif line[-2] == '5':    # 水平面夜間放射量 [kcal/m2h]

            # 時刻別の湿度を読み込み、格納
            for hh in range(0,24):
                tmp.append((float(line[3*hh:3*(hh+1)])))
            Inn.append(tmp)

    return Tout, Xout, Iod, Ios, Inn


#%%
if __name__ == '__main__':

    filename = "./climatedata/C1_0598195.has"
    
    [Tout, Xout, Iod, Ios, Inn] = readHaspClimateData(filename)




# %%
