#%%
import csv
import json

#%%
DictData = {
    "事務所等":{     
    },
    "ホテル等":{
    },
    "病院等":{
    },
    "物販店舗等":{
    },
    "学校等":{
    },
    "飲食店等":{
    },
    "集会所等":{
    },
    "工場等":{
    },
    "共同住宅":{
    }
}

def empty2null(x):
    if x=="":
        y = None
    elif x == '-':
        y = None
    else:
        y = x
    return y

def nullfloat(x):
    if x=="":
        y = None
    elif x == '-':
        y = None
    else:
        y = float(x)
    return y

def convert_CSV2DICT(d):

    addData = {
        "id": d[0],
        "カレンダーパターン": d[6],
        "空調運転パターン": empty2null(d[35]),
        "照明発熱参照値": nullfloat(d[8]),
        "人体発熱参照値": nullfloat(d[9]),
        "機器発熱参照値": nullfloat(d[10]),
        "作業強度指数": nullfloat(d[11]),
        "外気導入量": nullfloat(d[12]),
        "年間空調時間": nullfloat(d[21]),
        "年間換気時間": nullfloat(d[25]),
        "標準換気風量": nullfloat(d[27]),
        "基準設定換気方式": empty2null(d[26]),
        "基準設定全圧損失": nullfloat(d[28]),
        "年間照明点灯時間": nullfloat(d[22]),
        "設定照度": nullfloat(d[23]),
        "基準設定照明消費電力": nullfloat(d[24]),
        "年間給湯日数": nullfloat(d[31]),
        "年間湯使用量の単位": empty2null(d[30]),
        "年間湯使用量": nullfloat(d[29]),
        "年間湯使用量（洗面）": nullfloat(d[36]),
        "年間湯使用量（シャワー）": nullfloat(d[37]),
        "年間湯使用量（厨房）": nullfloat(d[38]),
        "年間湯使用量（その他）":nullfloat(d[39]),
        "スケジュール":{
            "室同時使用率":{
                "パターン1":[],
                "パターン2":[],
                "パターン3":[]
            },
            "照明発熱密度比率":{
                "パターン1":[],
                "パターン2":[],
                "パターン3":[]
            },
            "人体発熱密度比率":{
                "パターン1":[],
                "パターン2":[],
                "パターン3":[]
            },
            "機器発熱密度比率":{
                "パターン1":[],
                "パターン2":[],
                "パターン3":[]
            }
        },
        "newhASP": {
                "WSCパターン": empty2null(d[7]),
                "パターン1空調開始時刻1": nullfloat(d[13]),
                "パターン1空調終了時刻1": nullfloat(d[14]),
                "パターン1空調開始時刻2": nullfloat(d[15]),
                "パターン1空調終了時刻2": nullfloat(d[16]),
                "パターン2空調開始時刻1": nullfloat(d[17]),
                "パターン2空調終了時刻1": nullfloat(d[18]),
                "パターン2空調開始時刻2": nullfloat(d[19]),
                "パターン2空調終了時刻2": nullfloat(d[20]),
                "照明発熱密度比率":{
                    "パターン1":[],
                    "パターン2":[],
                    "パターン3":[]
                },
                "人体発熱密度比率":{
                    "パターン1":[],
                    "パターン2":[],
                    "パターン3":[]
                },
                "機器発熱密度比率":{
                    "パターン1":[],
                    "パターン2":[],
                    "パターン3":[]
                }
            }
        }


    return addData

# %%

# CSVファイル読み込み
with open('ROOM_SPEC.csv',encoding='Shift_JIS') as f:
    reader = csv.reader(f)
    specdata = [row for row in reader]

for d in specdata:

    # 処理を実行
    if d[3] == "事務所等":
        DictData["事務所等"][d[4]] = convert_CSV2DICT(d)   
    elif d[3] == "ホテル等":
        DictData["ホテル等"][d[4]] = convert_CSV2DICT(d)
    elif d[3] == "病院等":
        DictData["病院等"][d[4]] = convert_CSV2DICT(d)
    elif d[3] == "物品販売業を営む店舗等":
        DictData["物販店舗等"][d[4]] = convert_CSV2DICT(d)
    elif d[3] == "学校等":
        DictData["学校等"][d[4]] = convert_CSV2DICT(d)
    elif d[3] == "飲食店等":
        DictData["飲食店等"][d[4]] = convert_CSV2DICT(d)
    elif d[3] == "集会所等":
        DictData["集会所等"][d[4]] = convert_CSV2DICT(d)
    elif d[3] == "工場等":
        DictData["工場等"][d[4]] = convert_CSV2DICT(d)
    elif d[3] == "共同住宅":
        DictData["共同住宅"][d[4]] = convert_CSV2DICT(d)


#%%
# CSVファイル読み込み
with open('ROOM_COND.csv',encoding='Shift_JIS') as f:
    reader = csv.reader(f)
    conddata = [row for row in reader]

# ヘッダー列を削除
conddata.pop(0)

def timelist(x):
    y = []
    for i in x:
        if i != "":
            y.append(float(i))
    return y

for d in conddata:
    
    # IDを検索
    Btype = ""
    Rtype = ""
    for building in DictData:
        for room in DictData[building]:
            if (DictData[building][room]["id"] == d[0]):
                Btype = building
                Rtype = room
                break
    
    if Btype != "":

        if float(d[3]) == 1:
            if float(d[4]) == 1:
                DictData[Btype][Rtype]["スケジュール"]["室同時使用率"]["パターン1"] = [float(n) for n in d[7:31]]
            elif float(d[4]) == 2:
                DictData[Btype][Rtype]["スケジュール"]["室同時使用率"]["パターン2"] = [float(n) for n in d[7:31]]
            elif float(d[4]) == 3:
                DictData[Btype][Rtype]["スケジュール"]["室同時使用率"]["パターン3"] = [float(n) for n in d[7:31]]

        elif float(d[3]) == 2:
            if float(d[4]) == 1:
                DictData[Btype][Rtype]["スケジュール"]["照明発熱密度比率"]["パターン1"] = [float(n) for n in d[7:31]]
                DictData[Btype][Rtype]["newhASP"]["照明発熱密度比率"]["パターン1"] = timelist(d[31:54])
            elif float(d[4]) == 2:
                DictData[Btype][Rtype]["スケジュール"]["照明発熱密度比率"]["パターン2"] = [float(n) for n in d[7:31]]
                DictData[Btype][Rtype]["newhASP"]["照明発熱密度比率"]["パターン2"] = timelist(d[31:54])
            elif float(d[4]) == 3:
                DictData[Btype][Rtype]["スケジュール"]["照明発熱密度比率"]["パターン3"] = [float(n) for n in d[7:31]]
                DictData[Btype][Rtype]["newhASP"]["照明発熱密度比率"]["パターン3"] = timelist(d[31:54])

        elif float(d[3]) == 3:
            if float(d[4]) == 1:
                DictData[Btype][Rtype]["スケジュール"]["人体発熱密度比率"]["パターン1"] = [float(n) for n in d[7:31]]
                DictData[Btype][Rtype]["newhASP"]["人体発熱密度比率"]["パターン1"] = timelist(d[31:54])
            elif float(d[4]) == 2:
                DictData[Btype][Rtype]["スケジュール"]["人体発熱密度比率"]["パターン2"] = [float(n) for n in d[7:31]]
                DictData[Btype][Rtype]["newhASP"]["人体発熱密度比率"]["パターン2"] = timelist(d[31:54])
            elif float(d[4]) == 3:
                DictData[Btype][Rtype]["スケジュール"]["人体発熱密度比率"]["パターン3"] = [float(n) for n in d[7:31]]
                DictData[Btype][Rtype]["newhASP"]["人体発熱密度比率"]["パターン3"] = timelist(d[31:54])

        elif float(d[3]) == 4:
            if float(d[4]) == 1:
                DictData[Btype][Rtype]["スケジュール"]["機器発熱密度比率"]["パターン1"] = [float(n) for n in d[7:31]]
                DictData[Btype][Rtype]["newhASP"]["機器発熱密度比率"]["パターン1"] = timelist(d[31:54])
            elif float(d[4]) == 2:
                DictData[Btype][Rtype]["スケジュール"]["機器発熱密度比率"]["パターン2"] = [float(n) for n in d[7:31]]
                DictData[Btype][Rtype]["newhASP"]["機器発熱密度比率"]["パターン2"] = timelist(d[31:54])
            elif float(d[4]) == 3:
                DictData[Btype][Rtype]["スケジュール"]["機器発熱密度比率"]["パターン3"] = [float(n) for n in d[7:31]]
                DictData[Btype][Rtype]["newhASP"]["機器発熱密度比率"]["パターン3"] = timelist(d[31:54])








#%%
# JSONに書き込み
fw = open('ROOM_SPEC.json','w')
json.dump(DictData, fw, indent=4, ensure_ascii=False)

