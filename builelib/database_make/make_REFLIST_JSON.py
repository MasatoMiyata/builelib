#%%
import csv
import json

# CSVファイル読み込み
with open('./builelib/database_make/csv/REFLIST.csv',encoding='Shift_JIS') as f:
    reader = csv.reader(f)
    REFLIST = [row for row in reader]

with open('./builelib/database_make/csv/REFCURVE.csv',encoding='Shift_JIS') as f:
    reader = csv.reader(f)
    REFCURVE = [row for row in reader]

#%%
# 機種名称リストの作成

refNameList = []
for i in range(1,len(REFLIST)):
    refNameList.append(REFLIST[i][1])

#重複削除(set)してループ
DictData = {}
for unitName in set(refNameList):
    DictData[unitName] = {
        "ID": "",
        "冷房時の特性": {
            "燃料種類": "",
            "熱源種類": "",
            "能力比": [],
            "入力比": [],
            "部分負荷特性": [],
            "送水温度特性": []
        },
        "暖房時の特性": {
            "燃料種類": "",
            "熱源種類": "",
            "能力比": [],
            "入力比": [],
            "部分負荷特性": [],
            "送水温度特性": []
        }
    }

def convert_curveID2dict(REFCURVE,ID):
    for para in REFCURVE:
        if para[1] == ID:
            addData = {
                "a4": float(para[3]),
                "a3": float(para[4]),
                "a2": float(para[5]),
                "a1": float(para[6]),
                "a0": float(para[7]),
            }

    return addData


# %%
for d in REFLIST:
    
    if d[0] != "名称":  # 先頭行はスキップ

        # 機種名称を格納
        DictData[d[1]]["ID"] = d[0]


        # 冷却水温度の上下限があるかないかで場合分け
        if d[10] == "":
            addDict = {
                "下限": float(d[6]),
                "上限": float(d[7]),
                "冷却水温度下限": None,
                "冷却水温度上限": None,
                "係数": convert_curveID2dict(REFCURVE,d[8]),
                "基整促係数": float(d[9])
            }
        else:
            addDict = {
                "下限": float(d[6]),
                "上限": float(d[7]),
                "冷却水温度下限": float(d[10]),
                "冷却水温度上限": float(d[11]),
                "係数": convert_curveID2dict(REFCURVE,d[8]),
                "基整促係数": float(d[9])
            }

        if (d[4] == "Cooling") and (d[5] == "能力比"):
            DictData[d[1]]["冷房時の特性"]["燃料種類"] = d[2]
            DictData[d[1]]["冷房時の特性"]["熱源種類"] = d[3]
            DictData[d[1]]["冷房時の特性"]["能力比"].append(addDict)
        elif (d[4] == "Cooling") and (d[5] == "入力比"):
            DictData[d[1]]["冷房時の特性"]["燃料種類"] = d[2]
            DictData[d[1]]["冷房時の特性"]["熱源種類"] = d[3]
            DictData[d[1]]["冷房時の特性"]["入力比"].append(addDict)
        elif (d[4] == "Cooling") and (d[5] == "部分負荷特性"):
            DictData[d[1]]["冷房時の特性"]["燃料種類"] = d[2]
            DictData[d[1]]["冷房時の特性"]["熱源種類"] = d[3]
            DictData[d[1]]["冷房時の特性"]["部分負荷特性"].append(addDict)
        elif (d[4] == "Cooling") and (d[5] == "送水温度特性"):
            DictData[d[1]]["冷房時の特性"]["燃料種類"] = d[2]
            DictData[d[1]]["冷房時の特性"]["熱源種類"] = d[3]
            DictData[d[1]]["冷房時の特性"]["送水温度特性"].append(addDict)
        elif (d[4] == "Heating") and (d[5] == "能力比"):
            DictData[d[1]]["暖房時の特性"]["燃料種類"] = d[2]
            DictData[d[1]]["暖房時の特性"]["熱源種類"] = d[3]
            DictData[d[1]]["暖房時の特性"]["能力比"].append(addDict)
        elif (d[4] == "Heating") and (d[5] == "入力比"):
            DictData[d[1]]["暖房時の特性"]["燃料種類"] = d[2]
            DictData[d[1]]["暖房時の特性"]["熱源種類"] = d[3]
            DictData[d[1]]["暖房時の特性"]["入力比"].append(addDict)
        elif (d[4] == "Heating") and (d[5] == "部分負荷特性"):
            DictData[d[1]]["暖房時の特性"]["燃料種類"] = d[2]
            DictData[d[1]]["暖房時の特性"]["熱源種類"] = d[3]
            DictData[d[1]]["暖房時の特性"]["部分負荷特性"].append(addDict)
        elif (d[4] == "Heating") and (d[5] == "送水温度特性"):
            DictData[d[1]]["暖房時の特性"]["燃料種類"] = d[2]
            DictData[d[1]]["暖房時の特性"]["熱源種類"] = d[3]
            DictData[d[1]]["暖房時の特性"]["送水温度特性"].append(addDict)


# JSONに書き込み
fw = open('heat_source_performance.json','w')
json.dump(DictData, fw, indent=4, ensure_ascii=False)
