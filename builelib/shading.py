# 日除け効果係数を求めるプログラム

import numpy as np
import math
import json
import os

import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import climate

# データベースファイルの保存場所
database_directory =  os.path.dirname(os.path.abspath(__file__)) + "/database/"
# 気象データファイルの保存場所
climatedata_directory =  os.path.dirname(os.path.abspath(__file__)) + "/climatedata/"


# 定数（deg→radへの変換係数）
deg2rad = math.pi/180 
# 定数（rad→degへの変換係数）
rad2deg = 180/math.pi 


## 日射量を10分間隔の値に変換する関数
# 入力01: I_ALL 日射量(365, 24)
# 入力02: sin_hsdt_ALL 太陽高度(365, 24*6)
def func_03(I_ALL, sin_hsdt_ALL):

    # 日射量
    S = np.array(I_ALL).reshape((365*24,1))
    S = np.append(S,S[0:3])

    # 太陽高度
    H = np.array(sin_hsdt_ALL).reshape((52560,1))
    H = np.append(H,H[0:3])

    # 変数初期化
    n_all = np.zeros((365,24))

    for dd in range(0,365):
        for hh in range(0,24):
            
            # 時刻（1時を0とする）
            mm = (24*dd+(hh+1)) * 6 - 1
            n = 0
            
            if H[mm-3] > 0:
                n = n + 1/2

            if H[mm-2] > 0:
                n = n + 1
                
            if H[mm-1] > 0:
                n = n + 1

            if H[mm] > 0:
                n = n + 1

            if H[mm+1] > 0:
                n = n + 1

            if H[mm+2] > 0:
                n = n + 1

            if H[mm+3] > 0:
                n = n + 1/2
            
            n_all[dd][hh] = n


    Smin = np.zeros((365*24*6,1))
    for dd in range(0,365):
        for hh in range(0,24):
            
            mm60 = 24*dd + hh             # 1時間間隔データの列数
            mm10 = (24*dd + hh+1) * 6 - 1 # 10分間隔データの列数
            
            if H[mm10-3] > 0:
                Smin[mm10-3] = Smin[mm10-3] + S[mm60] / n_all[dd][hh] / 2

            if H[mm10-2] > 0:
                Smin[mm10-2] = Smin[mm10-2] + S[mm60] / n_all[dd][hh]

            if H[mm10-1] > 0:
                Smin[mm10-1] = Smin[mm10-1] + S[mm60] / n_all[dd][hh]

            if H[mm10] > 0:
                Smin[mm10]   = Smin[mm10]   + S[mm60] / n_all[dd][hh]

            if H[mm10+1] > 0:
                Smin[mm10+1] = Smin[mm10+1] + S[mm60] / n_all[dd][hh]

            if H[mm10+2] > 0:
                Smin[mm10+2] = Smin[mm10+2] + S[mm60] / n_all[dd][hh]

            if H[mm10+3] > 0:
                Smin[mm10+3] = Smin[mm10+3] + S[mm60] / n_all[dd][hh] / 2


    # 単位を kcal/(10min)m2 から　kcal/hm2　に変換
    I_ALL_10min = np.zeros((365,24*6))
    for dd in range(0,365):
        for hh in range(0,24*6):
            I_ALL_10min[dd][hh] = Smin[ (24*6*dd + hh) ] * 6

    return I_ALL_10min

def func_15(x, y, zyPlus, x3, x2, y1, y2, tanh_Sdt, cosA_ZWjdt, tanA_ZWjdt):

    X = x3 + x2 / 2 - x
    Y = y1 + y2 / 2 - y
    A = zyPlus * tanA_ZWjdt
    B = zyPlus * tanh_Sdt / cosA_ZWjdt

    if (zyPlus == 0):
        Aoh0p =  0
    else:
        if (X >= A and Y >= B):
            Aoh0p =  (X - 1/2 * A) * B
        elif (X < A and Y * A  >= B * X):
            Aoh0p =  1/2 * X * B / A * X
        elif (Y < B) or (Y * A  >= B * X):
            Aoh0p =  (X - 1/2 * Y * A / B) * Y
        else:
            raise Exception('Error!')

    return Aoh0p

def func_16(x, y, zxPlus, x3, x2, y1, y2, tanh_Sdt, cosA_ZWjdt, tanA_ZWjdt):

    Y = x3 + x2 / 2 - x
    X = y1 + y2 / 2 - y
    B = zxPlus * tanA_ZWjdt
    A = zxPlus * tanh_Sdt / cosA_ZWjdt

    if (zxPlus == 0):
        Asf0p =  0
    else:
        if (X >= A and Y >= B):
            Asf0p =  (X - 1/2 * A) * B
        elif (X < A and Y * A >= B * X):
            Asf0p =  1/2 * X * B / A * X
        elif (Y < B) or (Y * A >= B * X):
            Asf0p =  (X - 1/2 * Y * A / B) * Y
        else:
            raise Exception('Error!')

    return Asf0p

def func_14(x2, x3, y1, y2, zxPlus, zyPlus, tanh_Sdt, cosA_ZWjdt, tanA_ZWjdt):

    if tanh_Sdt > 0:
        
        inputAs = [zxPlus, x3, x2, y1, y2, tanh_Sdt, cosA_ZWjdt, tanA_ZWjdt]
        
        Awind_j_xp_t = (x2 + x3) * (y1 + y2) \
            - func_15(-x2/2, -y2/2, zyPlus, x3, x2, y1, y2, tanh_Sdt, cosA_ZWjdt, tanA_ZWjdt) \
            - func_16(-x2/2, -y2/2, zxPlus, x3, x2, y1, y2, tanh_Sdt, cosA_ZWjdt, tanA_ZWjdt) \
            - ( (x2+x3)*y1 \
            - func_15(-x2/2, y2/2, zyPlus, x3, x2, y1, y2, tanh_Sdt, cosA_ZWjdt, tanA_ZWjdt) \
            - func_16(-x2/2, y2/2, zxPlus, x3, x2, y1, y2, tanh_Sdt, cosA_ZWjdt, tanA_ZWjdt) ) \
            - ( x3*(y1+y2) \
            - func_15(x2/2, -y2/2, zyPlus, x3, x2, y1, y2, tanh_Sdt, cosA_ZWjdt, tanA_ZWjdt) \
            - func_16(x2/2, -y2/2, zxPlus, x3, x2, y1, y2, tanh_Sdt, cosA_ZWjdt, tanA_ZWjdt) ) \
            + x3*y1 \
            - func_15(x2/2, y2/2, zyPlus, x3, x2, y1, y2, tanh_Sdt, cosA_ZWjdt, tanA_ZWjdt) \
            - func_16(x2/2, y2/2, zxPlus, x3, x2, y1, y2, tanh_Sdt, cosA_ZWjdt, tanA_ZWjdt)
            
    else:
        
        Awind_j_xp_t = 0

    return Awind_j_xp_t

def func_19(x, y, zyPlus, x1, x2, y1, y2, tanh_Sdt, cosA_ZWjdt, tanA_ZWjdt):

    X = x1 + x2 / 2 + x
    Y = y1 + y2 / 2 - y
    A = zyPlus * tanA_ZWjdt
    B = zyPlus * tanh_Sdt / cosA_ZWjdt

    if (zyPlus == 0):
        Aoh0m =  0
    else:
        if (X >= A and Y >= B):
            Aoh0m =  (X - 1/2 * A) * B
        elif (X < A and Y * A >= B * X):
            Aoh0m =  1/2 * X * B / A * X
        elif (Y < B) or (Y * A >= B * X):
            Aoh0m =  (X - 1/2 * Y * A / B) * Y
        else:
            raise Exception('Error!')


    return Aoh0m

def func_20(x, y, zxMinus, x1, x2, y1, y2, tanh_Sdt, cosA_ZWjdt, tanA_ZWjdt):

    Y = x1 + x2 / 2 + x
    X = y1 + y2 / 2 - y
    B = zxMinus * tanA_ZWjdt
    A = zxMinus * tanh_Sdt / cosA_ZWjdt

    if (zxMinus == 0):
        Asf0m =  0
    else:
        if (X >= A and Y >= B):
            Asf0m =  (X - 1/2 * A) * B
        elif (X < A and Y * A >= B * X):
            Asf0m =  1/2 * X * B / A * X
        elif (Y < B) or (Y * A >= B * X):
            Asf0m =  (X - 1/2 * Y * A / B) * Y
        else:
            raise Exception('Error!')

    return Asf0m

def func_18(x2, x1, y1, y2, zxMinus, zyPlus, tanh_Sdt, cosA_ZWjdt, tanA_ZWjdt):

    if tanh_Sdt > 0:
        
        inputAo = [zyPlus, x1, x2, y1, y2, tanh_Sdt, cosA_ZWjdt, tanA_ZWjdt]
        inputAs = [zxMinus, x1, x2, y1, y2, tanh_Sdt, cosA_ZWjdt, tanA_ZWjdt]
            
        Awind_j_xm_t = (x1 + x2) * (y1 + y2) \
        - func_19(x2/2, -y2/2, zyPlus, x1, x2, y1, y2, tanh_Sdt, cosA_ZWjdt, tanA_ZWjdt) \
        - func_20(x2/2, -y2/2, zxMinus, x1, x2, y1, y2, tanh_Sdt, cosA_ZWjdt, tanA_ZWjdt) \
        - ( (x1+x2)*y1 \
        - func_19(x2/2, y2/2, zyPlus, x1, x2, y1, y2, tanh_Sdt, cosA_ZWjdt, tanA_ZWjdt) \
        - func_20(x2/2, y2/2, zxMinus, x1, x2, y1, y2, tanh_Sdt, cosA_ZWjdt, tanA_ZWjdt) ) \
        - ( x1*(y1+y2) \
        - func_19(-x2/2, -y2/2, zyPlus, x1, x2, y1, y2, tanh_Sdt, cosA_ZWjdt, tanA_ZWjdt) \
        - func_20(-x2/2, -y2/2, zxMinus, x1, x2, y1, y2, tanh_Sdt, cosA_ZWjdt, tanA_ZWjdt) ) \
        + x1*y1 \
        - func_19(-x2/2, y2/2, zyPlus, x1, x2, y1, y2, tanh_Sdt, cosA_ZWjdt, tanA_ZWjdt) \
        - func_20(-x2/2, y2/2, zxMinus, x1, x2, y1, y2, tanh_Sdt, cosA_ZWjdt, tanA_ZWjdt) 
        
    else:
        
        Awind_j_xm_t = 0

    return Awind_j_xm_t

def calc_fa_atan(x, y, z):

    if y**2 + z**2 > 0:
        fa_atan = x * math.sqrt( y**2 + z**2 ) / 2 * math.atan( x / math.sqrt( y**2 + z**2 ) )
    else:
        fa_atan = 0

    return fa_atan

def calc_fa_log(x, y, z):

    if x**2 + y**2 + z**2 > 0:
        fa_log = ( x**2 - y**2 - z**2 ) / 8 * math.log( x**2 + y**2 + z**2 )
    else:
        fa_log = 0

    return fa_log

def func_23(xa,xb,ya,yb,za):

    fa =  calc_fa_atan(xb, yb, za) - calc_fa_atan(xb, ya, za) \
        - calc_fa_atan(xa, yb, za) + calc_fa_atan(xa, ya, za) \
        + calc_fa_log(xb, yb, za)  - calc_fa_log(xb, ya, za) \
        - calc_fa_log(xa, yb, za)  + calc_fa_log(xa, ya, za) 

    return fa

# 天空日射に対する日除け効果係数
def func_22(x1,x2,x3,y1,y2,zxp,zxm,zyp):

    # 窓の面積[m2]
    Awind = x2*y2

    tmp = func_23(x3, x2+x3, y1, y1+y2, zyp) \
        + func_23(y1, y1+y2, x3, x2+x3, zxp) \
        + func_23(x1, x1+x2, y1, y1+y2, zyp) \
        + func_23(y1, y1+y2, x1, x1+x2, zxm)
        
    r_isr_j_yp = 1/(math.pi*Awind) * tmp

    return r_isr_j_yp

# 反射日射に対する日除け効果係数
def func_25(x1,x2,x3,y3,y2,zxp,zxm,zym):

    # 窓の面積[m2]
    Awind = x2*y2

    tmp = func_23(x3, x2+x3, y3, y3+y2, zym) \
        + func_23(y3, y3+y2, x3, x2+x3, zxp) \
        + func_23(x1, x1+x2, y3, y3+y2, zym) \
        + func_23(y3, y3+y2, x1, x1+x2, zxm)
        
    r_isr_j_ym = 1/(math.pi*Awind) * tmp

    return r_isr_j_ym


def calc_shadingCoefficient(AREA, Direction, x1,x2,x3,y1,y2,y3,zxp,zxm,zyp,zym):

    ## 入力チェック
    if x1 < 0 or x2 < 0 or x3 < 0:
        raise Exception('Error!')
    if y1 < 0 or y2 < 0 or y3 < 0:
        raise Exception('Error!')
    if zxp < 0 or zxm < 0 or zyp < 0 or zym < 0:
        raise Exception('Error!')

    ## 地域別データ読み込み

    with open(database_directory + 'AREA.json', 'r') as f:
        areaDB = json.load(f)
    climatefilename = climatedata_directory + '/C1_' + areaDB[AREA+"地域"]["気象データファイル名"] # 気象データ

    # 気象データ読み込み
    # IodALL : 法線面直達日射量[W/m2]
    # IosALL : 水平面天空日射量[W/m2]
    [_,_,Iod_ALL,Ios_ALL,_] = climate.readHaspClimateData(climatefilename)

    phi = areaDB[AREA+"地域"]["緯度"] # 緯度 [deg]
    L   = areaDB[AREA+"地域"]["経度"] # 経度 [deg]
    
    # 暖冷房期間
    if AREA == "1" or AREA == "2":
        SUM = list(range(121,304+1)) # 冷房期間
        WIN = list(range(1,120+1))
        WIN.extend(list(range(305,365+1))) # 暖房期間
    elif AREA == "3" or AREA == "4" or AREA == "5" or AREA == "6" or AREA == "7":
        SUM = list(range(91,334+1)) # 冷房期間
        WIN = list(range(1,90+1))
        WIN.extend(list(range(335,365+1))) # 暖房期間
    elif AREA == "8":
        SUM = list(range(91,365+1)) # 冷房期間
        WIN = list(range(1,90+1)) # 暖房期間
    else:
        raise Exception('Error!')

    # 窓面積 [m2]
    Awind = x2 * y2

    # 方位
    if Direction == '南':
        Azw = 0
    elif Direction == '南西':
        Azw = 45
    elif Direction == '西':
        Azw = 90
    elif Direction == '北西':
        Azw = 135
    elif Direction == '北':
        Azw = 180
    elif Direction == '北東':
        Azw = -135
    elif Direction == '東':
        Azw = -90
    elif Direction == '南東':
        Azw = -45
    else:
        raise Exception('Error!')


    ##------------------ 太陽高度、太陽方位角の計算 ------------------##
    Azs_ALL      = np.zeros((365,24*6))
    Azwj_ALL     = np.zeros((365,24*6))
    hsdt_ALL     = np.zeros((365,24*6))
    sin_hsdt_ALL = np.zeros((365,24*6))
    cos_hsdt_ALL = np.zeros((365,24*6))
    tan_hsdt_ALL = np.zeros((365,24*6))
    sin_Azwj_ALL = np.zeros((365,24*6))
    cos_Azwj_ALL = np.zeros((365,24*6))
    tan_Azwj_ALL = np.zeros((365,24*6))
    tan_Azwj_ab_ALL = np.zeros((365,24*6))
    Ita_ALL  = np.zeros((365,24*6))

    for dd in range(0,365):  # 日のループ
        for hh in range(0,24*6):   # 時刻のループ（10分間隔）
            
            Nday = dd+1  # 通し日
            t = (hh+1)/6   # 時刻（小数）

            # 日赤緯 [deg]　式(4),(5)
            delta = 180/math.pi * ( 0.006322 - 0.405748 * math.cos(2*math.pi*Nday/366 + 0.153231 ) \
                - 0.005880 * math.cos(4*math.pi*Nday/366 + 0.207099) \
                - 0.003233 * math.cos(6*math.pi*Nday/366 + 0.620129))
            
            # 均時差 [時間] 式(6)
            ed = -0.000279 + 0.122772 * math.cos(2*math.pi*Nday/366 + 1.498311) \
                - 0.165458 * math.cos(4*math.pi*Nday/366 - 1.261546) \
                - 0.005354 * math.cos(6*math.pi*Nday/366 - 1.1571)
            
            # 時角 [deg]　式(7)
            Td = (t+ed-12) * 15 + (L-135)
            
            # 太陽高度 [deg] 式(8),(9)
            sin_hsdt = max(0, math.sin(deg2rad*phi)*math.sin(deg2rad*delta) + math.cos(deg2rad*phi)*math.cos(deg2rad*delta)*math.cos(deg2rad*Td))
            cos_hsdt = math.sqrt(1-sin_hsdt**2)
            tan_hsdt = sin_hsdt / cos_hsdt
            
            hsdt = math.asin(sin_hsdt)*rad2deg  # 太陽高度 [deg]
            
            # 太陽方位角 Azs [deg]　式(10),(11),(12)
            sin_Azs = math.cos(deg2rad*delta)*math.sin(deg2rad*Td) / cos_hsdt
            cos_Azs = (sin_hsdt*math.sin(deg2rad*phi) - math.sin(deg2rad*delta)) / (cos_hsdt*math.cos(deg2rad*phi))
            tan_Azs = sin_Azs/cos_Azs
            
            if (sin_Azs > 0) and (cos_Azs < 0):
                Azs = math.atan( sin_Azs / cos_Azs )*rad2deg + 180
            elif (sin_Azs < 0) and (cos_Azs < 0):
                Azs = math.atan( sin_Azs / cos_Azs )*rad2deg - 180
            elif (sin_Azs == 1) and (cos_Azs == 0):
                Azs = 90
            elif (sin_Azs == -1) and (cos_Azs == 0):
                Azs = -90
            else:
                Azs = math.atan( sin_Azs / cos_Azs )*180/math.pi
            
            angle = Azs-Azw
            if angle > 180:
                psi = -1
            elif angle > 0:
                psi = 1
            elif angle > -180:
                psi = -1
            else:
                psi = 1

            
            Azwj = psi* min( abs(angle), abs(360+angle), abs(-360+angle) )
            
            cos_Azwj = math.cos(deg2rad*Azwj)
            sin_Azwj = psi * math.sqrt(1-cos_Azwj**2)
            tan_Azwj = math.tan(deg2rad*Azwj)
            tan_Azwj_ab = math.tan(abs(deg2rad*Azwj))
            
            # 入射角特性　式(2.1.28)
            if (sin_hsdt > 0) and (Azwj >= -90 and Azwj <= 90):
                theta = min(cos_Azwj*cos_hsdt, math.pi/2)
                Ita = 2.3920 * theta - 3.8636 * theta**3 + 3.7568 * theta**5 - 1.3952 * theta**7
            else:
                Ita = 1.0

            # 結果の格納
            Azs_ALL[dd][hh]      = Azs
            Azwj_ALL[dd][hh]     = Azwj
            hsdt_ALL[dd][hh]     = hsdt
            sin_hsdt_ALL[dd][hh] = sin_hsdt
            cos_hsdt_ALL[dd][hh] = cos_hsdt
            tan_hsdt_ALL[dd][hh] = tan_hsdt
            sin_Azwj_ALL[dd][hh] = sin_Azwj
            cos_Azwj_ALL[dd][hh] = cos_Azwj
            tan_Azwj_ALL[dd][hh] = tan_Azwj
            tan_Azwj_ab_ALL[dd][hh] = tan_Azwj_ab
            Ita_ALL[dd][hh]      = Ita


    # 直達日射量 10分間隔 [kcal/m2h]
    Iod_ALL_10min = func_03(Iod_ALL,sin_hsdt_ALL)
    # 天空日射量 10分間隔 [kcal/m2h]
    Ios_ALL_10min = func_03(Ios_ALL,sin_hsdt_ALL)


    ##------------------ 直達日射に関する日除け効果係数 ------------------##

    # 日の当たる面積
    Awind_j_xp = np.zeros((365,24*6))
    Awind_j_xm = np.zeros((365,24*6))
    for dd in range(0,365):  # 日のループ
        for hh in range(0,24*6):   # 時刻のループ（10分間隔）
            
            if sin_hsdt_ALL[dd][hh] > 0 and Iod_ALL_10min[dd][hh] > 0:

                if (Azwj_ALL[dd][hh] >= -90 and Azwj_ALL[dd][hh] <= 0 ):  # x+側
                    Awind_j_xp[dd][hh] = func_14(x2, x3, y1, y2, zxp, zyp, tan_hsdt_ALL[dd][hh], cos_Azwj_ALL[dd][hh], tan_Azwj_ab_ALL[dd][hh])

                elif (Azwj_ALL[dd][hh] > 0 and Azwj_ALL[dd][hh] <= 90 ): # x-側
                    Awind_j_xm[dd][hh] = func_18(x2, x1, y1, y2, zxm, zyp, tan_hsdt_ALL[dd][hh], cos_Azwj_ALL[dd][hh], tan_Azwj_ALL[dd][hh])


    # 直達日射に関する日除け効果係数（式13、式17）
    S_shade_xp_SUM = 0
    S_xp_SUM = 0
    S_shade_xp_WIN = 0
    S_xp_WIN = 0
    S_shade_xm_SUM = 0
    S_xm_SUM = 0
    S_shade_xm_WIN = 0
    S_xm_WIN = 0

    temp = np.zeros((365,24*6))
    for dd in range(0,365):  # 日のループ
        for hh in range(0,24*6):   # 時刻のループ（10分間隔）
            
            if sin_hsdt_ALL[dd][hh] > 0 and Iod_ALL_10min[dd][hh] > 0 and (Azwj_ALL[dd][hh] >= -90 and Azwj_ALL[dd][hh] <= 90):
                
                # 日射量 [kcal/m2]
                S_dt = (Iod_ALL_10min[dd][hh] * Ita_ALL[dd][hh] * cos_hsdt_ALL[dd][hh] * cos_Azwj_ALL[dd][hh])
                
                temp[dd][hh] = S_dt
                
                if (Azwj_ALL[dd][hh] >= -90 and Azwj_ALL[dd][hh] <= 0 ): # x+側
                    
                    if dd+1 in SUM:
                        S_shade_xp_SUM = S_shade_xp_SUM + Awind_j_xp[dd][hh] * S_dt
                        S_xp_SUM       = S_xp_SUM + S_dt            
                    elif dd+1 in WIN:
                        S_shade_xp_WIN = S_shade_xp_WIN + Awind_j_xp[dd][hh] * S_dt
                        S_xp_WIN       = S_xp_WIN + S_dt
                    else:
                        raise Exception('Error!')

                elif (Azwj_ALL[dd][hh] > 0 and Azwj_ALL[dd][hh] <= 90 ): # x-側
                    
                    if dd+1 in SUM:
                        S_shade_xm_SUM = S_shade_xm_SUM + Awind_j_xm[dd][hh] * S_dt
                        S_xm_SUM       = S_xm_SUM + S_dt
                    elif dd+1 in WIN:
                        S_shade_xm_WIN = S_shade_xm_WIN + Awind_j_xm[dd][hh] * S_dt
                        S_xm_WIN       = S_xm_WIN + S_dt
                    else:
                        raise Exception('Error!')


    if S_xp_SUM > 0 and Awind > 0:
        r_dsr_j_xp_SUM = S_shade_xp_SUM / (Awind * S_xp_SUM)
    else:
        r_dsr_j_xp_SUM = 0

    if S_xm_SUM > 0 and Awind > 0:
        r_dsr_j_xm_SUM = S_shade_xm_SUM / (Awind * S_xm_SUM)
    else:
        r_dsr_j_xm_SUM = 0

    if S_xp_WIN > 0 and Awind > 0:
        r_dsr_j_xp_WIN = S_shade_xp_WIN / (Awind * S_xp_WIN)
    else:
        r_dsr_j_xp_WIN = 0

    if S_xm_WIN > 0 and Awind > 0:
        r_dsr_j_xm_WIN = S_shade_xm_WIN / (Awind * S_xm_WIN)
    else:
        r_dsr_j_xm_WIN = 0


    ## 天空日射に関する日除け効果係数（式22）
    r_isr_j_yp = 2 * func_22(x1,x2,x3,y1,y2,zxp,zxm,zyp)

    ## 反射日射に関する日除け効果係数（式25）
    r_isr_j_ym = 2 * func_25(x1,x2,x3,y3,y2,zxp,zxm,zym)


    ## 日除け効果係数計算（式２）
    ST_xp_SUM = 0
    ST_xm_SUM = 0
    ST_st_SUM = 0
    ST_rt_SUM = 0
    ST_xp_WIN = 0
    ST_xm_WIN = 0
    ST_st_WIN = 0
    ST_rt_WIN = 0

    # 日射量集計
    for dd in range(0,365):  # 日のループ
        for hh in range(0,24*6):   # 時刻のループ（10分間隔）
            
            # 直達日射量 [kcal/m2]
            S_dt = Iod_ALL_10min[dd][hh] * Ita_ALL[dd][hh] * cos_hsdt_ALL[dd][hh] * cos_Azwj_ALL[dd][hh]
            # 天空日射量 [kcal/m2]
            S_st = 0.808*0.5*Ios_ALL_10min[dd][hh]
            # 反射日射量 [kcal/m2]
            S_rt = 0.808*0.1*0.5*(Ios_ALL_10min[dd][hh] + Iod_ALL_10min[dd][hh]*sin_hsdt_ALL[dd][hh] )
            
            if dd+1 in SUM:
                    
                if sin_hsdt_ALL[dd][hh] > 0 and Iod_ALL_10min[dd][hh] > 0:
                    if (Azwj_ALL[dd][hh] >= -90 and Azwj_ALL[dd][hh] <= 0 ): # 直達日射（x+側）
                        ST_xp_SUM = ST_xp_SUM + S_dt
                    elif (Azwj_ALL[dd][hh] > 0 and Azwj_ALL[dd][hh] <= 90 ): # 直達日射（x-側）
                        ST_xm_SUM = ST_xm_SUM + S_dt
                
                ST_st_SUM = ST_st_SUM + S_st  # 天空日射
                ST_rt_SUM = ST_rt_SUM + S_rt  # 反射日射
                    
            elif dd+1 in WIN:
                    
                if sin_hsdt_ALL[dd][hh] > 0 and Iod_ALL_10min[dd][hh] > 0:
                    if (Azwj_ALL[dd][hh] >= -90 and Azwj_ALL[dd][hh] <= 0 ): # 直達日射（x+側）
                        ST_xp_WIN = ST_xp_WIN + S_dt
                    elif (Azwj_ALL[dd][hh] > 0 and Azwj_ALL[dd][hh] <= 90 ): # 直達日射（x-側）
                        ST_xm_WIN = ST_xm_WIN + S_dt

                ST_st_WIN = ST_st_WIN + S_st  # 天空日射
                ST_rt_WIN = ST_rt_WIN + S_rt  # 反射日射
                    
            else:
                raise Exception('Error!')


    ## 日除け効果係数（冷房期、暖房期）
    r_wind_SUM = ( r_dsr_j_xp_SUM*ST_xp_SUM + r_dsr_j_xm_SUM*ST_xm_SUM + r_isr_j_yp*ST_st_SUM + r_isr_j_ym*ST_rt_SUM ) \
        / (ST_xp_SUM + ST_xm_SUM + ST_st_SUM + ST_rt_SUM)
    r_wind_WIN = ( r_dsr_j_xp_WIN*ST_xp_WIN + r_dsr_j_xm_WIN*ST_xm_WIN + r_isr_j_yp*ST_st_WIN + r_isr_j_ym*ST_rt_WIN ) \
        / (ST_xp_WIN + ST_xm_WIN + ST_st_WIN + ST_rt_WIN)

    return r_wind_SUM, r_wind_WIN


#%%
if __name__ == '__main__':

    # AREA = "6"
    # Direction = "南"
    # x1=0
    # x2=5
    # x3=0
    # y1=0
    # y2=2
    # y3=0
    # zxp=2
    # zxm=2
    # zyp=2
    # zym=0
    
    AREA ="7"	
    Direction ="北東"
    x1=0.2
    x2=1
    x3=0.2
    y1=0.3
    y2=1.5
    y3=0.4
    zxp=0.05
    zxm=0.4
    zyp=0.2
    zym=0.35
    
    r_wind_SUM, r_wind_WIN = calc_shadingCoefficient(AREA, Direction, x1,x2,x3,y1,y2,y3,zxp,zxm,zyp,zym)

    print("日よけ効果係数（冷房）：" + str(r_wind_SUM))
    print("日よけ効果係数（暖房）：" + str(r_wind_WIN))

