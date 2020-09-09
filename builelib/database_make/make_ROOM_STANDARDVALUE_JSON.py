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

def convert_CSV2DICT(d):
    addData = {
        "空調": {
            "1地域": int(d[2]),
            "2地域": int(d[3]),
            "3地域": int(d[4]),
            "4地域": int(d[5]),
            "5地域": int(d[6]),
            "6地域": int(d[7]),
            "7地域": int(d[8]),
            "8地域": int(d[9])
        },
        "換気": int(d[19]),
        "照明": int(d[18]),
        "給湯": {
            "1地域": int(d[10]),
            "2地域": int(d[11]),
            "3地域": int(d[12]),
            "4地域": int(d[13]),
            "5地域": int(d[14]),
            "6地域": int(d[15]),
            "7地域": int(d[16]),
            "8地域": int(d[17])
        }
    }
    return addData

# %%

# CSVファイル読み込み
with open('ROOM_STANDARDVALUE.csv',encoding='Shift_JIS') as f:
    reader = csv.reader(f)
    csvdata = [row for row in reader]

for d in csvdata:
    if d[0] == "事務所等":
        DictData["事務所等"][d[1]]= convert_CSV2DICT(d)
    elif d[0] == "ホテル等":
        DictData["ホテル等"][d[1]]= convert_CSV2DICT(d)
    elif d[0] == "病院等":
        DictData["病院等"][d[1]]= convert_CSV2DICT(d)
    elif d[0] == "物販店舗等":
        DictData["物販店舗等"][d[1]]= convert_CSV2DICT(d)
    elif d[0] == "学校等":
        DictData["学校等"][d[1]]= convert_CSV2DICT(d)
    elif d[0] == "飲食店等":
        DictData["飲食店等"][d[1]]= convert_CSV2DICT(d)
    elif d[0] == "集会所等":
        DictData["集会所等"][d[1]]= convert_CSV2DICT(d)
    elif d[0] == "工場等":
        DictData["工場等"][d[1]]= convert_CSV2DICT(d)
    elif d[0] == "共同住宅":
        DictData["共同住宅"][d[1]]= convert_CSV2DICT(d)


# JSONに書き込み
fw = open('standardvalue.json','w')
json.dump(DictData, fw, indent=4, ensure_ascii=False)
