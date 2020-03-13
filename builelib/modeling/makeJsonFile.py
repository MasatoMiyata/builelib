#%%
import xlrd
import json
import jsonschema


#%%
inputfileName = './sample/WEBPRO_inputSheet_for_Ver3.xlsx'

# 入力シートの読み込み
wb = xlrd.open_workbook(inputfileName)

# テンプレートjsonの読み込み
with open('./builelib/modeling/template.json', 'r') as f:
    data = json.load(f)

# スキーマの読み込み
with open('./builelib/modeling/webproJsonSchema.json', 'r') as f:
    schema_data = json.load(f)


# デフォルトを設定する関数
def set_default(x,default):
    if x == "":
        x = default
    return x

# %%
# 様式BLの読み込み
if "様式BL" in wb.sheet_names():

    # シートの読み込み
    sheet_BL = wb.sheet_by_name("様式BL")

    # BL-1	建築物の名称
    data["Building"]["Name"] = str(sheet_BL.cell(10, 4).value)
    # BL-2	都道府県	(選択)
    data["Building"]["BuildingAddress"]["Prefecture"] = str(sheet_BL.cell(11, 4).value)
    # BL-3	建築物所在地	市区町村	(選択)
    data["Building"]["BuildingAddress"]["City"]  = str(sheet_BL.cell(12, 4).value)
    # BL-4	丁目、番地等
    data["Building"]["BuildingAddress"]["Address"]  = str(sheet_BL.cell(13, 4).value)
    # BL-5	地域の区分		(自動)
    data["Building"]["Region"] = str(int(sheet_BL.cell(14, 4).value))
    # BL-6	年間日射地域区分		(自動)
    data["Building"]["AnnualSolarRegion"] = str(sheet_BL.cell(15, 4).value)
    # BL-7	延べ面積 	[㎡]	(数値)
    data["Building"]["BuildingFloorArea"] = float(sheet_BL.cell(16, 4).value)
    # BL-8	「他人から供給された熱」	冷熱	(数値)
    data["Building"]["Coefficient_DHC"]["Cooling"] = float(sheet_BL.cell(17, 4).value)
    # BL-9	の一次エネルギー換算係数	温熱	(数値)
    data["Building"]["Coefficient_DHC"]["Heating"] = float(sheet_BL.cell(18, 4).value)

#%%
# 様式RMの読み込み
if "様式RM" in wb.sheet_names():

    # シートの読み込み
    sheet_BL = wb.sheet_by_name("様式RM")

    # 行のループ
    for i in range(10,sheet_BL.nrows):

        # シートから「行」の読み込み
        dataBL = sheet_BL.row_values(i)

        # 階と室名が空欄でない場合
        if (dataBL[0] != "") and (dataBL[1] != ""):

            addDic = {
                "floorName": str(dataBL[0]),
                "roomName": str(dataBL[1]),
                "buildingType": str(dataBL[2]),               
                "roomType": str(dataBL[3]),
                "roomArea": float(dataBL[4]),
                "floorHeight": float(dataBL[5]),
                "ceilingHeight": float(dataBL[6])
            }

            # リストを追加
            data["Rooms"].append(addDic)


#%% 
if "様式L" in wb.sheet_names():
    
    # シートの読み込み
    sheet_L = wb.sheet_by_name("様式L")

    # 行のループ
    for i in range(10,sheet_L.nrows):

        # シートから「行」の読み込み
        dataL = sheet_L.row_values(i)

        # 階と室名が空欄でない場合
        if (dataL[0] != "") and (dataL[1] != ""):

            addDic = {
                "floorName": str(dataL[0]),
                "roomName": str(dataL[1]),
                "roomWidth": set_default(dataL[2],None),
                "roomDepth": set_default(dataL[3],None),
                "unitHeight": set_default(dataL[4],None),
                "roomIndex": set_default(dataL[5],None),
                "lightingUnit":[
                    {
                        "UnitName": str(dataL[6]),
                        "RatedPower": float(dataL[7]),
                        "Number": float(dataL[8]),
                        "OccupantSensingCTRL": set_default(str(dataL[9]),schema_data["definitions"]["LightingUnit"]["properties"]["OccupantSensingCTRL"]["default"]),
                        "IlluminanceSensingCTRL": set_default(str(dataL[10]),schema_data["definitions"]["LightingUnit"]["properties"]["IlluminanceSensingCTRL"]["default"]),
                        "TimeScheduleCTRL": set_default(str(dataL[11]),schema_data["definitions"]["LightingUnit"]["properties"]["TimeScheduleCTRL"]["default"]),
                        "InitialIlluminationCorrectionCTRL": set_default(str(dataL[12]),schema_data["definitions"]["LightingUnit"]["properties"]["InitialIlluminationCorrectionCTRL"]["default"])
                    }
                ]
            }

            # リストを追加
            data["LightingSystems"].append(addDic)
            
        # 階と室名が空欄である場合
        if (dataL[0] == "") and (dataL[1] == ""):

            addDic = {
                "UnitName": str(dataL[6]),
                "RatedPower": float(dataL[7]),
                "Number": float(dataL[8]),
                "OccupantSensingCTRL": set_default(str(dataL[9]),schema_data["definitions"]["LightingUnit"]["properties"]["OccupantSensingCTRL"]["default"]),
                "IlluminanceSensingCTRL": set_default(str(dataL[10]),schema_data["definitions"]["LightingUnit"]["properties"]["IlluminanceSensingCTRL"]["default"]),
                "TimeScheduleCTRL": set_default(str(dataL[11]),schema_data["definitions"]["LightingUnit"]["properties"]["TimeScheduleCTRL"]["default"]),
                "InitialIlluminationCorrectionCTRL": set_default(str(dataL[12]),schema_data["definitions"]["LightingUnit"]["properties"]["InitialIlluminationCorrectionCTRL"]["default"])
            }

            # リストの最後の追加する。
            data["LightingSystems"][-1]["lightingUnit"].append(addDic)


# バリデーションの実行
jsonschema.validate(data, schema_data)

# json出力
fw = open('inputdata.json','w')
json.dump(data,fw,indent=4,ensure_ascii=False)
