import xlrd
import json
import jsonschema
import os

# テンプレートファイルの保存場所
template_directory =  os.path.dirname(os.path.abspath(__file__)) + "/inputdata/"

# デフォルトを設定する関数
def set_default(value,default,type):
    if value == "":
        out = default
    else:
        if type == "str":
            out = str(value)
        elif type == "float":
            out = float(value)
        elif type == "int":
            out = int(value)
        else:
            out = value
    return out

# 計算対象設備があるかどうかを判定する関数
def set_isCalculatedEquipment(input):
    if input == "■":
        isEquip = True
    else:
        isEquip = False

    return isEquip


def make_jsondata_from_Ver4_sheet(inputfileName, validation = False):
    """
    WEBPRO Ver4 用の入力シートから 入力データ（辞書型）を生成するプログラム
    """

    # 入力シートの読み込み
    wb = xlrd.open_workbook(inputfileName)

    # テンプレートjsonの読み込み
    with open( template_directory + 'template.json', 'r') as f:
        data = json.load(f)

    # スキーマの読み込み
    with open( template_directory + 'webproJsonSchema.json', 'r') as f:
        schema_data = json.load(f)

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

    
    # 様式RMの読み込み
    if "様式RM" in wb.sheet_names():

        # シートの読み込み
        sheet_BL = wb.sheet_by_name("様式RM")
        # 初期化
        roomKey = None

        # 行のループ
        for i in range(10,sheet_BL.nrows):

            # シートから「行」の読み込み
            dataBL = sheet_BL.row_values(i)

            # 階と室名が空欄でない場合
            if (dataBL[0] != "") and (dataBL[1] != ""):

                # 階＋室をkeyとする
                roomKey = str(dataBL[0]) + '_' + str(dataBL[1])

                # ゾーンがある場合
                if (dataBL[7] != ""):

                    data["Rooms"][roomKey] = {
                            "buildingType": str(dataBL[2]),               
                            "roomType": str(dataBL[3]),
                            "floorHeight": float(dataBL[4]),
                            "ceilingHeight": float(dataBL[5]),
                            "roomArea": float(dataBL[6]),
                            "zone":{
                                str(dataBL[7]):{
                                    "zoneArea": set_default(str(dataBL[8]),None, "float"),
                                    "Info": str(dataBL[11])
                                }
                            },
                            "modelBuildingType": str(dataBL[9]),  
                            "buildingGroup": str(dataBL[10])
                    }

                else:

                    data["Rooms"][roomKey] = {
                            "buildingType": str(dataBL[2]),               
                            "roomType": str(dataBL[3]),
                            "floorHeight": float(dataBL[4]),
                            "ceilingHeight": float(dataBL[5]),
                            "roomArea": float(dataBL[6]),
                            "zone": None,
                            "modelBuildingType": str(dataBL[9]),  
                            "buildingGroup": str(dataBL[10]),
                            "Info": str(dataBL[11])
                    }

            # 複数のゾーンがある場合
            elif (dataBL[7] != ""):

                data["Rooms"][roomKey]["zone"][str(dataBL[7])] = {
                        "zoneArea": set_default(str(dataBL[8]),None, "float"),
                        "Info": str(dataBL[11])
                    }


    ## 外皮
    if "様式BE1" in wb.sheet_names():

        # シートの読み込み
        sheet_BE1 = wb.sheet_by_name("様式BE1")
        # 初期化
        roomKey = None

        # 行のループ
        for i in range(10,sheet_BE1.nrows):

            # シートから「行」の読み込み
            dataBE1 = sheet_BE1.row_values(i)

            # 階と室名が空欄でない場合
            if (dataBE1[0] != "") and (dataBE1[1] != ""):

                # 階＋室＋ゾーン名をkeyとする（上書き）
                if (dataBE1[2] != ""):
                    roomKey = str(dataBE1[0]) + '_' + str(dataBE1[1]) + '_' + str(dataBE1[2])
                else:
                    roomKey = str(dataBE1[0]) + '_' + str(dataBE1[1])

                data["EnvelopeSet"][roomKey] = {
                        "isAirconditioned": set_default(str(dataBE1[3]),'無', "str"),
                        "WallList": [
                            {
                                "Direction": str(dataBE1[4]),
                                "EnvelopeArea": set_default(str(dataBE1[5]),None, "float"),
                                "EnvelopeWidth": set_default(str(dataBE1[6]),None, "float"),
                                "EnvelopeHeight": set_default(str(dataBE1[7]),None, "float"),
                                "WallSpec": set_default(str(dataBE1[8]),"無","str"),
                                "WallType": set_default(str(dataBE1[9]),"無","str"),
                                "WindowList":[
                                    {
                                        "WindowID": set_default(str(dataBE1[10]),"無","str"),
                                        "WindowNumber": set_default(str(dataBE1[11]),None, "float"),
                                        "isBlind": set_default(str(dataBE1[12]),"無","str"),
                                        "EavesID": set_default(str(dataBE1[13]),"無","str"),
                                        "Info": set_default(str(dataBE1[14]),"無","str"),
                                    }
                                ]       
                            }
                        ],
                    }

            else: # 階と室名が空欄である場合

                if (str(dataBE1[4]) == "") and (str(dataBE1[10]) != ""): ## 方位に入力がなく、建具種類に入力がある場合

                    data["EnvelopeSet"][roomKey]["WallList"][-1]["WindowList"].append(
                        {
                            "WindowID": str(dataBE1[10]),
                            "WindowNumber": set_default(str(dataBE1[11]),None, "float"),
                            "isBlind": set_default(str(dataBE1[12]),"無","str"),
                            "EavesID": set_default(str(dataBE1[13]),"無","str"),
                            "Info": set_default(str(dataBE1[14]),"無","str")
                        }
                    )                     

                elif (str(dataBE1[4]) != ""):  ## 方位に入力がある場合

                    data["EnvelopeSet"][roomKey]["WallList"].append(
                        {
                            "Direction": str(dataBE1[4]),
                            "EnvelopeArea": set_default(str(dataBE1[5]),None, "float"),
                            "EnvelopeWidth": set_default(str(dataBE1[6]),None, "float"),
                            "EnvelopeHeight": set_default(str(dataBE1[7]),None, "float"),
                            "WallSpec": set_default(str(dataBE1[8]),"無","str"),
                            "WallType": set_default(str(dataBE1[9]),"無","str"),
                            "WindowList":[
                                {
                                    "WindowID": set_default(str(dataBE1[10]),"無","str"),
                                    "WindowNumber": set_default(str(dataBE1[11]),None, "float"),
                                    "isBlind": set_default(str(dataBE1[12]),"無","str"),
                                    "EavesID": set_default(str(dataBE1[13]),"無","str"),
                                    "Info": set_default(str(dataBE1[14]),"無","str")
                                }
                            ]       
                        }
                    )

    if "様式BE2" in wb.sheet_names():

        # シートの読み込み
        sheet_BE2 = wb.sheet_by_name("様式BE2")
        # 初期化
        eltKey = None
        inputMethod = None

        # 行のループ
        for i in range(10,sheet_BE2.nrows):

            # シートから「行」の読み込み
            dataBE2 = sheet_BE2.row_values(i)

            # 断熱仕様名称が空欄でない場合
            if (dataBE2[0] != ""):

                # 断熱仕様名称をkeyとする（上書き）
                eltKey = str(dataBE2[0]) 

                # 入力方法を識別
                if dataBE2[9] != "":
                    inputMethod = "熱貫流率を入力"
                elif (dataBE2[6] != "") or (dataBE2[7] != ""):
                    inputMethod = "建材構成を入力"
                elif (dataBE2[3] != "") or (dataBE2[4] != ""):
                    inputMethod = "断熱材種類を入力"
                else:
                    raise Exception('Error!')
                
                if inputMethod == "熱貫流率を入力":

                    data["WallConfigure"][eltKey] = {
                            "structureType": str(dataBE2[1]),
                            "solarAbsorptionRatio": set_default(dataBE2[2], None, "float"),
                            "inputMethod": inputMethod,
                            "Uvalue": set_default(dataBE2[9], None, "float"),
                            "Info": set_default(dataBE2[10], "無","str"),
                        }

                elif inputMethod == "建材構成を入力":

                    data["WallConfigure"][eltKey] = {
                            "structureType": str(dataBE2[1]),
                            "solarAbsorptionRatio": set_default(dataBE2[2], None, "float"),
                            "inputMethod": inputMethod,
                            "layers": [
                                {
                                "materialID": set_default(dataBE2[6], None, "str"),
                                "conductivity": set_default(dataBE2[7], None, "float"),
                                "thickness": set_default(dataBE2[8], None, "float"),
                                "Info": set_default(dataBE2[10], "無", "str")
                                }
                            ]
                        }

                elif inputMethod == "断熱材種類を入力":

                    data["WallConfigure"][eltKey] = {
                            "structureType": str(dataBE2[1]),
                            "solarAbsorptionRatio": set_default(dataBE2[2], None, "float"),
                            "inputMethod": inputMethod,
                            "materialID": set_default(dataBE2[3], None, "str"),
                            "conductivity": set_default(dataBE2[4], None, "float"),
                            "thickness": set_default(dataBE2[5], None, "float"),
                            "Info": set_default(dataBE2[10], "無","str"),
                        }
            else:

                if inputMethod == "建材構成を入力":

                    data["WallConfigure"][eltKey]["layers"].append(
                        {
                            "materialID": set_default(dataBE2[6], None, "str"),
                            "conductivity": set_default(dataBE2[7], None, "float"),
                            "thickness": set_default(dataBE2[8], None, "float"),
                            "Info": set_default(dataBE2[10], "無", "str")
                        }
                    )

    if "様式BE3" in wb.sheet_names():

        # シートの読み込み
        sheet_BE3 = wb.sheet_by_name("様式BE3")
        # 初期化
        eltKey = None
        inputMethod = None

        # 行のループ
        for i in range(10,sheet_BE3.nrows):

            # シートから「行」の読み込み
            dataBE3 = sheet_BE3.row_values(i)

            # 開口部仕様名称が空欄でない場合
            if (dataBE3[0] != ""):

                # 開口部仕様名称をkeyとする（上書き）
                eltKey = str(dataBE3[0]) 

                # 入力方法を識別
                if (dataBE3[9] != "") and (dataBE3[10] != ""):
                    inputMethod = "性能値を入力"
                elif (dataBE3[7] != "") and (dataBE3[8] != ""):
                    inputMethod = "ガラスの性能を入力"
                elif (dataBE3[5] != ""):
                    inputMethod = "ガラスの種類を入力"
                else:
                    raise Exception('Error!')

                if inputMethod == "性能値を入力":

                    data["WindowConfigure"][eltKey] = {
                            "windowArea": set_default(str(dataBE3[1]),None, "float"),
                            "windowWidth": set_default(str(dataBE3[2]),None, "float"),
                            "windowHeight": set_default(str(dataBE3[3]),None, "float"),
                            "inputMethod": inputMethod,
                            "windowUvalue": set_default(dataBE3[9], None, "float"),
                            "windowIvalue": set_default(dataBE3[10], None, "float"),
                            "layerType": set_default(dataBE3[6], "単層", "str"),
                            "glassUvalue": set_default(dataBE3[7], None, "float"),
                            "glassIvalue": set_default(dataBE3[8], None, "float"),
                            "Info": set_default(dataBE3[11], "無","str"),
                        }

                elif inputMethod == "ガラスの性能を入力":

                    data["WindowConfigure"][eltKey] = {
                            "windowArea": set_default(str(dataBE3[1]),None, "float"),
                            "windowWidth": set_default(str(dataBE3[2]),None, "float"),
                            "windowHeight": set_default(str(dataBE3[3]),None, "float"),
                            "inputMethod": inputMethod,
                            "frameType": set_default(dataBE3[4], "金属製", "str"),
                            "layerType": set_default(dataBE3[6], "単層", "str"),
                            "glassUvalue": set_default(dataBE3[7], None, "float"),
                            "glassIvalue": set_default(dataBE3[8], None, "float"),
                            "Info": set_default(dataBE3[11], "無","str"),
                        }

                elif inputMethod == "ガラスの種類を入力":

                    data["WindowConfigure"][eltKey] = {
                            "windowArea": set_default(str(dataBE3[1]),None, "float"),
                            "windowWidth": set_default(str(dataBE3[2]),None, "float"),
                            "windowHeight": set_default(str(dataBE3[3]),None, "float"),
                            "inputMethod": inputMethod,
                            "frameType": set_default(dataBE3[4], "金属製", "str"),
                            "glassID": set_default(dataBE3[5], None, "str"),
                            "Info": set_default(dataBE3[11], "無","str"),
                        }

    if "様式BE4" in wb.sheet_names():

        # シートの読み込み
        sheet_BE4 = wb.sheet_by_name("様式BE4")
        # 初期化
        eltKey = None

        # 行のループ
        for i in range(10,sheet_BE4.nrows):

            # シートから「行」の読み込み
            dataBE4 = sheet_BE4.row_values(i)

            # 日よけの名称が空欄でない場合
            if (dataBE4[0] != ""):

                # 日よけの名称名称をkeyとする（上書き）
                eltKey = str(dataBE4[0]) 

                data["ShadingConfigure"][eltKey] = {
                        "shadingEffect_C": set_default(str(dataBE4[1]),None, "float"),
                        "shadingEffect_H": set_default(str(dataBE4[2]),None, "float"),
                        "x1": set_default(str(dataBE4[3]),None, "float"),
                        "x2": set_default(str(dataBE4[4]),None, "float"),
                        "x3": set_default(str(dataBE4[5]),None, "float"),
                        "y1": set_default(str(dataBE4[6]),None, "float"),
                        "y2": set_default(str(dataBE4[7]),None, "float"),
                        "y3": set_default(str(dataBE4[8]),None, "float"),
                        "zxPlus": set_default(str(dataBE4[9]),None, "float"),
                        "zxMinus": set_default(str(dataBE4[10]),None, "float"),
                        "zyPlus": set_default(str(dataBE4[11]),None, "float"),
                        "zyMinus": set_default(str(dataBE4[12]),None, "float"),
                        "Info": set_default(dataBE4[13], "無","str"),
                    }

    ## 空調設備
    if "様式AC1" in wb.sheet_names():
        
        # シートの読み込み
        sheet_AC1 = wb.sheet_by_name("様式AC1")
        # 初期化
        roomKey = None

        # 行のループ
        for i in range(10,sheet_AC1.nrows):

            # シートから「行」の読み込み
            dataAC1 = sheet_AC1.row_values(i)

            # 階と室名が空欄でない場合
            if (dataAC1[0] != "") and (dataAC1[1] != ""):

                # 階＋室+ゾーン名をkeyとする
                if (dataAC1[2] != ""):
                    roomKey = str(dataAC1[0]) + '_' + str(dataAC1[1]) + '_' + str(dataAC1[2])
                else:
                    roomKey = str(dataAC1[0]) + '_' + str(dataAC1[1])

                data["AirConditioningZone"][roomKey] = {
                    "isNatualVentilation": set_default(dataAC1[3], "無", "str"),
                    "isSimultaneousSupply": set_default(dataAC1[4], "無", "str"),
                    "AHU_cooling_insideLoad": set_default(dataAC1[5], None, "str"),
                    "AHU_cooling_outdoorLoad": set_default(dataAC1[6], None, "str"),
                    "AHU_heating_insideLoad": set_default(dataAC1[7], None, "str"),
                    "AHU_heating_outdoorLoad": set_default(dataAC1[8], None, "str"),
                    "Info": str(dataAC1[9])
                }

    if "様式AC2" in wb.sheet_names():
        
        # シートの読み込み
        sheet_AC2 = wb.sheet_by_name("様式AC2")
        # 初期化
        unitKey = None
        modeKey = None

        # 行のループ
        for i in range(10,sheet_AC2.nrows):

            # シートから「行」の読み込み
            dataAC2 = sheet_AC2.row_values(i)

            # 熱源群名称と運転モードが空欄でない場合
            if (dataAC2[0] != "") and (dataAC2[1] != ""):      
                
                unitKey = str(dataAC2[0])
                modeKey = str(dataAC2[1])

                data["HeatsourceSystem"][unitKey] = {
                    modeKey : {
                        "StorageType": set_default(dataAC2[2], None, "str"),
                        "StorageSize": set_default(dataAC2[3], None, "float"),
                        "isStagingControl": set_default(dataAC2[4], "無", "str"),
                        "Heatsource" :[
                            {
                                "HeatsourceType": str(dataAC2[5]),
                                "Number": float(dataAC2[6]),
                                "SupplyWaterTempSummer": set_default(dataAC2[7], None, "float"),
                                "SupplyWaterTempMiddle": set_default(dataAC2[8], None, "float"),
                                "SupplyWaterTempWinter": set_default(dataAC2[9], None, "float"),
                                "HeatsourceRatedCapacity": float(dataAC2[10]),
                                "HeatsourceRatedPowerConsumption": set_default(dataAC2[11], 0, "float"),
                                "HeatsourceRatedFuelConsumption": set_default(dataAC2[12], 0, "float"),
                                "PrimaryPumpPowerConsumption": set_default(dataAC2[13], 0, "float"),
                                "PrimaryPumpContolType": set_default(dataAC2[14], "無", "str"),
                                "CoolingTowerCapacity": set_default(dataAC2[15], 0, "float"),
                                "CoolingTowerFanPowerConsumption": set_default(dataAC2[16], 0, "float"),
                                "CoolingTowerPumpPowerConsumption": set_default(dataAC2[17], 0, "float"),
                                "CoolingTowerContolType": set_default(dataAC2[18], "無", "str"),
                                "Info": str(dataAC2[19])
                            }
                        ]
                    }
                }

            elif (dataAC2[1] == "") and (dataAC2[5] != ""):  # 熱源機種を追加（複数台設置されている場合）

                data["HeatsourceSystem"][unitKey][modeKey]["Heatsource"].append(
                    {
                        "HeatsourceType": str(dataAC2[5]),
                        "Number": float(dataAC2[6]),
                        "SupplyWaterTempSummer": set_default(dataAC2[7], None, "float"),
                        "SupplyWaterTempMiddle": set_default(dataAC2[8], None, "float"),
                        "SupplyWaterTempWinter": set_default(dataAC2[9], None, "float"),
                        "HeatsourceRatedCapacity": float(dataAC2[10]),
                        "HeatsourceRatedPowerConsumption": set_default(dataAC2[11], 0, "float"),
                        "HeatsourceRatedFuelConsumption": set_default(dataAC2[12], 0, "float"),
                        "PrimaryPumpPowerConsumption": set_default(dataAC2[13], 0, "float"),
                        "PrimaryPumpContolType": set_default(dataAC2[14], "無", "str"),
                        "CoolingTowerCapacity": set_default(dataAC2[15], 0, "float"),
                        "CoolingTowerFanPowerConsumption": set_default(dataAC2[16], 0, "float"),
                        "CoolingTowerPumpPowerConsumption": set_default(dataAC2[17], 0, "float"),
                        "CoolingTowerContolType": set_default(dataAC2[18], "無", "str"),
                        "Info": str(dataAC2[19])
                    }
                )

            elif (dataAC2[1] != ""):  # 熱源機種を追加（複数のモードがある場合）

                modeKey = str(dataAC2[1])

                data["HeatsourceSystem"][unitKey][modeKey] = {
                    "StorageType": set_default(dataAC2[2], None, "str"),
                    "StorageSize": set_default(dataAC2[3], None, "float"),
                    "isStagingControl": set_default(dataAC2[4], "無", "str"),
                    "Heatsource" :[
                        {
                            "HeatsourceType": str(dataAC2[5]),
                            "Number": float(dataAC2[6]),
                            "SupplyWaterTempSummer": set_default(dataAC2[7], None, "float"),
                            "SupplyWaterTempMiddle": set_default(dataAC2[8], None, "float"),
                            "SupplyWaterTempWinter": set_default(dataAC2[9], None, "float"),
                            "HeatsourceRatedCapacity": float(dataAC2[10]),
                            "HeatsourceRatedPowerConsumption": set_default(dataAC2[11], 0, "float"),
                            "HeatsourceRatedFuelConsumption": set_default(dataAC2[12], 0, "float"),
                            "PrimaryPumpPowerConsumption": set_default(dataAC2[13], 0, "float"),
                            "PrimaryPumpContolType": set_default(dataAC2[14], "無", "str"),
                            "CoolingTowerCapacity": set_default(dataAC2[15], 0, "float"),
                            "CoolingTowerFanPowerConsumption": set_default(dataAC2[16], 0, "float"),
                            "CoolingTowerPumpPowerConsumption": set_default(dataAC2[17], 0, "float"),
                            "CoolingTowerContolType": set_default(dataAC2[18], "無", "str"),
                            "Info": str(dataAC2[19])
                        }
                    ]
                }


    if "様式AC3" in wb.sheet_names():
        
        # シートの読み込み
        sheet_AC3 = wb.sheet_by_name("様式AC3")
        # 初期化
        unitKey = None
        modeKey = None

        # 行のループ
        for i in range(10,sheet_AC3.nrows):

            # シートから「行」の読み込み
            dataAC3 = sheet_AC3.row_values(i)

            # 二次ポンプ群名称と運転モードが空欄でない場合
            if (dataAC3[0] != "") and (dataAC3[1] != ""):      
                
                unitKey = str(dataAC3[0])
                modeKey = str(dataAC3[1])

                data["SecondaryPumpSystem"][unitKey] = {
                    modeKey : {
                        "TempelatureDifference": float(dataAC3[2]),
                        "isStagingControl": set_default(dataAC3[3], "無", "str"),
                        "SecondaryPump" :[
                            {
                                "Number": float(dataAC3[4]),
                                "RatedWaterFlowRate": float(dataAC3[5]),
                                "RatedPowerConsumption": float(dataAC3[6]),
                                "ContolType": set_default(dataAC3[7], "無", "str"),
                                "MinOpeningRate": set_default(dataAC3[8], None, "float"),
                                "Info": str(dataAC3[9])
                            }
                        ]
                    }
                }
            
            elif (dataAC3[1] == "") and (dataAC3[4] != ""):

                data["SecondaryPumpSystem"][unitKey][modeKey]["SecondaryPump"].append(
                    {
                        "Number": float(dataAC3[4]),
                        "RatedWaterFlowRate": float(dataAC3[5]),
                        "RatedPowerConsumption": float(dataAC3[6]),
                        "ContolType": set_default(dataAC3[7], "無", "str"),
                        "MinOpeningRate": set_default(dataAC3[8], None, "float"),
                        "Info": str(dataAC3[9])
                    }
                )

            elif (dataAC3[2] != ""):

                modeKey = str(dataAC3[1])

                data["SecondaryPumpSystem"][unitKey][modeKey] = {
                    "TempelatureDifference": float(dataAC3[2]),
                    "isStagingControl": set_default(dataAC3[3], "無", "str"),
                    "SecondaryPump" :[
                        {
                            "Number": float(dataAC3[4]),
                            "RatedWaterFlowRate": float(dataAC3[5]),
                            "RatedPowerConsumption": float(dataAC3[6]),
                            "ContolType": set_default(dataAC3[7], "無", "str"),
                            "MinOpeningRate": set_default(dataAC3[8], None, "float"),
                            "Info": str(dataAC3[9])
                        }
                    ]
                }
    
    if "様式AC4" in wb.sheet_names():
        
        # シートの読み込み
        sheet_AC4 = wb.sheet_by_name("様式AC4")
        # 初期化
        unitKey = None

        # 行のループ
        for i in range(10,sheet_AC4.nrows):

            # シートから「行」の読み込み
            dataAC4 = sheet_AC4.row_values(i)

            # 空調機群名称が空欄でない場合
            if (dataAC4[0] != ""):      
                
                unitKey = str(dataAC4[0])

                data["AirHandlingSystem"][unitKey] = {
                    "isEconomizer": set_default(dataAC4[15], "無", "str"),
                    "EconomizerMaxAirVolume": set_default(dataAC4[16], None, "float"),
                    "isOutdoorAirCut": set_default(dataAC4[17], "無", "str"),
                    "Pump_cooling": set_default(dataAC4[18], None, "str"),
                    "Pump_heating": set_default(dataAC4[19], None, "str"),
                    "HeatSource_cooling": set_default(dataAC4[20], None, "str"),
                    "HeatSource_heating": set_default(dataAC4[21], None, "str"),
                    "AirHandlingUnit" :[
                        {
                            "Type": str(dataAC4[1]),
                            "Number": float(dataAC4[2]),
                            "RatedCapacityCooling": set_default(dataAC4[3], None, "float"),
                            "RatedCapacityHeating": set_default(dataAC4[4], None, "float"),
                            "FanType": set_default(dataAC4[5], None, "str"),
                            "FanAirVolume": set_default(dataAC4[6], None, "float"),
                            "FanPowerConsumption": set_default(dataAC4[7], None, "float"),
                            "FanControlType": set_default(dataAC4[8], "無", "str"),
                            "FanMinOpeningRate": set_default(dataAC4[9], None, "float"),
                            "AirHeatExchangeRatioCooling": set_default(dataAC4[10], None, "float"),
                            "AirHeatExchangeRatioHeating": set_default(dataAC4[11], None, "float"),
                            "AirHeatExchangerEffectiveAirVolumeRatio": set_default(dataAC4[12], None, "float"),
                            "AirHeatExchangerControl": set_default(dataAC4[13], "無", "str"),
                            "AirHeatExchangerPowerConsumption": set_default(dataAC4[14], None, "float"),
                            "Info": str(dataAC4[22])
                        }
                    ]
                }

            elif (dataAC4[4] != ""):      

                data["AirHandlingSystem"][unitKey]["AirHandlingUnit"].append(
                    {
                        "Type": str(dataAC4[1]),
                        "Number": float(dataAC4[2]),
                        "RatedCapacityCooling": set_default(dataAC4[3], None, "float"),
                        "RatedCapacityHeating": set_default(dataAC4[4], None, "float"),
                        "FanType": set_default(dataAC4[5], None, "str"),
                        "FanAirVolume": set_default(dataAC4[6], None, "float"),
                        "FanPowerConsumption": set_default(dataAC4[7], None, "float"),
                        "FanControlType": set_default(dataAC4[8], "無", "str"),
                        "FanMinOpeningRate": set_default(dataAC4[9], None, "float"),
                        "AirHeatExchangeRatioCooling": set_default(dataAC4[10], None, "float"),
                        "AirHeatExchangeRatioHeating": set_default(dataAC4[11], None, "float"),
                        "AirHeatExchangerEffectiveAirVolumeRatio": set_default(dataAC4[12], None, "float"),
                        "AirHeatExchangerControl": set_default(dataAC4[13], "無", "str"),
                        "AirHeatExchangerPowerConsumption": set_default(dataAC4[14], None, "float"),
                        "Info": str(dataAC4[22])
                    }
                )

    ## 機械換気設備
    if "様式V1" in wb.sheet_names():
        
        # シートの読み込み
        sheet_V1 = wb.sheet_by_name("様式V1")
        # 初期化
        roomKey = None

        # 行のループ
        for i in range(10,sheet_V1.nrows):

            # シートから「行」の読み込み
            dataV = sheet_V1.row_values(i)

            # 階と室名が空欄でない場合
            if (dataV[0] != "") and (dataV[1] != ""):

                # 階＋室をkeyとする
                roomKey = str(dataV[0]) + '_' + str(dataV[1])

                data["VentilationRoom"][roomKey] = {
                        "VentilationType": str(dataV[2]),
                        "VentilationUnitRef":{
                            str(dataV[4]):{
                                "UnitType": str(dataV[3]),
                                "Info": str(dataV[5])
                            }
                        }
                }

            # 階と室名が空欄であり、かつ、機器名称に入力がある場合
            # 上記 if文 内で定義された roomKey をkeyとして、機器を追加する。
            elif (dataV[0] == "") and (dataV[1] == "") and (dataV[4] != ""):

                data["VentilationRoom"][roomKey]["VentilationUnitRef"][str(dataV[4])]  = {
                    "UnitType": str(dataV[3]),
                    "Info": str(dataV[5])
                }               

    if "様式V2" in wb.sheet_names():
        
        # シートの読み込み
        sheet_V2 = wb.sheet_by_name("様式V2")
        # 初期化
        unitKey = None

        # 行のループ
        for i in range(10,sheet_V2.nrows):

            # シートから「行」の読み込み
            dataV = sheet_V2.row_values(i)

            # 換気機器名称が空欄でない場合
            if (dataV[0] != ""):
                
                data["VentilationUnit"][str(dataV[0])] = {
                    "Number": set_default(dataV[1], 1, "float"),
                    "FanAirVolume": set_default(dataV[2], None, "float"),
                    "MoterRatedPower": set_default(dataV[3], None, "float"),
                    "PowerConsumption": set_default(dataV[4], None, "float"),
                    "HighEfficiencyMotor": set_default(str(dataV[5]),'無', "str"),
                    "Inverter": set_default(str(dataV[6]),'無', "str"),
                    "AirVolumeControl": set_default(str(dataV[7]),'無', "str"),
                    "VentilationRoomType": set_default(str(dataV[8]),None, "str"),
                    "AC_CoolingCapacity": set_default(dataV[9], None, "float"),
                    "AC_RefEfficiency": set_default(dataV[10], None, "float"),
                    "AC_PumpPower": set_default(dataV[11], None, "float"),
                    "Info": str(dataV[12])
                }

    if "様式L" in wb.sheet_names():
        
        # シートの読み込み
        sheet_L = wb.sheet_by_name("様式L")
        # 初期化
        roomKey = None

        # 行のループ
        for i in range(10,sheet_L.nrows):

            # シートから「行」の読み込み
            dataL = sheet_L.row_values(i)

            # 階と室名が空欄でない場合
            if (dataL[0] != "") and (dataL[1] != ""):

                # 階＋室+ゾーン名をkeyとする
                if (dataL[2] != ""):
                    roomKey = str(dataL[0]) + '_' + str(dataL[1]) + '_' + str(dataL[2])
                else:
                    roomKey = str(dataL[0]) + '_' + str(dataL[1])

                data["LightingSystems"][roomKey] = {
                    "roomWidth": set_default(dataL[3],None, "float"),
                    "roomDepth": set_default(dataL[4],None, "float"),
                    "unitHeight": set_default(dataL[5],None, "float"),
                    "roomIndex": set_default(dataL[6],None, "float"),
                    "lightingUnit": {
                        str(dataL[7]): {
                            "RatedPower": float(dataL[8]),
                            "Number": float(dataL[9]),
                            "OccupantSensingCTRL": set_default(str(dataL[10]),schema_data["definitions"]["Lighting_OccupantSensingCTRL"]["default"], "str"),
                            "IlluminanceSensingCTRL": set_default(str(dataL[11]),schema_data["definitions"]["Lighting_IlluminanceSensingCTRL"]["default"], "str"),
                            "TimeScheduleCTRL": set_default(str(dataL[12]),schema_data["definitions"]["Lighting_TimeScheduleCTRL"]["default"], "str"),
                            "InitialIlluminationCorrectionCTRL": set_default(str(dataL[13]),schema_data["definitions"]["Lighting_InitialIlluminationCorrectionCTRL"]["default"], "str")
                        }
                    }
                }

            # 階と室名が空欄であり、かつ、消費電力の入力がある場合
            elif (dataL[0] == "") and (dataL[1] == "") and (dataL[8] != ""):

                data["LightingSystems"][roomKey]["lightingUnit"][str(dataL[7])] = {
                    "RatedPower": float(dataL[8]),
                    "Number": float(dataL[9]),
                    "OccupantSensingCTRL": set_default(str(dataL[10]),schema_data["definitions"]["Lighting_OccupantSensingCTRL"]["default"], "str"),
                    "IlluminanceSensingCTRL": set_default(str(dataL[11]),schema_data["definitions"]["Lighting_IlluminanceSensingCTRL"]["default"], "str"),
                    "TimeScheduleCTRL": set_default(str(dataL[12]),schema_data["definitions"]["Lighting_TimeScheduleCTRL"]["default"], "str"),
                    "InitialIlluminationCorrectionCTRL": set_default(str(dataL[13]),schema_data["definitions"]["Lighting_InitialIlluminationCorrectionCTRL"]["default"], "str")
                }

    if "様式HW1" in wb.sheet_names():

        # シートの読み込み
        sheet_HW1 = wb.sheet_by_name("様式HW1")
        # 初期化
        roomKey = None

        # 行のループ
        for i in range(10,sheet_HW1.nrows):

            # シートから「行」の読み込み
            dataHW1 = sheet_HW1.row_values(i)

            # 階と室名が空欄でない場合
            if (dataHW1[0] != "") and (dataHW1[1] != "") :

                # 階＋室をkeyとする
                roomKey = str(dataHW1[0]) + '_' + str(dataHW1[1])

                data["HotwaterRoom"][roomKey] = {
                    "HotwaterSystem":[
                        {
                            "UsageType": str(dataHW1[2]),
                            "SystemName": str(dataHW1[3]),
                            "HotWaterSavingSystem": set_default(str(dataHW1[4]),"無","str"),
                            "Info": str(dataHW1[5])
                        }
                    ]
                }

            elif (dataHW1[2] != "") and (dataHW1[3] != "") :

                data["HotwaterRoom"][roomKey]["HotwaterSystem"].append(
                    {
                        "UsageType": str(dataHW1[2]),
                        "SystemName": str(dataHW1[3]),
                        "HotWaterSavingSystem": set_default(str(dataHW1[4]),"無","str"),
                        "Info": str(dataHW1[5])
                    }
                )

    if "様式HW2" in wb.sheet_names():

        # シートの読み込み
        sheet_HW2 = wb.sheet_by_name("様式HW2")
        # 初期化
        unitKey = None

        # 行のループ
        for i in range(10,sheet_HW2.nrows):

            # シートから「行」の読み込み
            dataHW2 = sheet_HW2.row_values(i)

            # 給湯システム名称が空欄でない場合
            if (dataHW2[0] != ""):

                # 給湯システム名称をkeyとする
                unitKey = str(dataHW2[0])

                data["HotwaterSupplySystems"][unitKey] = {
                    "HeatSourceUnit":[
                        {
                            "UsageType": str(dataHW2[1]),
                            "HeatSourceType": str(dataHW2[2]),
                            "Number": float(dataHW2[3]),
                            "RatedCapacity": float(dataHW2[4]),
                            "RatedPowerConsumption": float(dataHW2[5]),
                            "RatedFuelConsumption": float(dataHW2[6]),
                        }
                    ],
                    "InsulationType": str(dataHW2[7]),
                    "PipeSize": float(dataHW2[8]),
                    "SolarSystemArea": set_default(dataHW2[9], None, "float"),
                    "SolarSystemDirection": set_default(dataHW2[10], None, "float"),
                    "SolarSystemAngle": set_default(dataHW2[11], None, "float"),
                    "Info": str(dataHW2[12])
                }

            elif (dataHW2[1] != "") and (dataHW2[2] != ""):

                data["HotwaterSupplySystems"][unitKey]["HeatSourceUnit"].append(
                    {
                        "UsageType": str(dataHW2[1]),
                        "HeatSourceType": str(dataHW2[2]),
                        "Number": float(dataHW2[3]),
                        "RatedCapacity": float(dataHW2[4]),
                        "RatedPowerConsumption": float(dataHW2[5]),
                        "RatedFuelConsumption": float(dataHW2[6]),
                    }
                )

    if "様式EV" in wb.sheet_names():

        # シートの読み込み
        sheet_EV = wb.sheet_by_name("様式EV")
        # 初期化
        roomKey = None

        # 行のループ
        for i in range(10,sheet_EV.nrows):

            # シートから「行」の読み込み
            dataEV = sheet_EV.row_values(i)

            # 階と室名が空欄でない場合
            if (dataEV[0] != "") and (dataEV[1] != "") :

                # 階＋室をkeyとする
                roomKey = str(dataEV[0]) + '_' + str(dataEV[1])

                data["Elevators"][roomKey] = {
                    "Elevator": [
                        {
                            "ElevatorName": set_default(str(dataEV[2]),"-","str"),
                            "Number": float(dataEV[3]),
                            "LoadLimit": float(dataEV[4]),
                            "Velocity": float(dataEV[5]),
                            "TransportCapacityFactor": set_default(str(dataEV[6]),1,"float"),
                            "ControlType": set_default(str(dataEV[7]),"交流帰還制御","str"),
                            "Info": str(dataEV[8])
                        }
                    ]
                }

            elif (dataEV[3] != "") or (dataEV[4] != ""):

                data["Elevators"][roomKey]["Elevator"].append(
                    {
                        "ElevatorName": set_default(str(dataEV[2]),"-","str"),
                        "Number": float(dataEV[3]),
                        "LoadLimit": float(dataEV[4]),
                        "Velocity": float(dataEV[5]),
                        "TransportCapacityFactor": set_default(str(dataEV[6]),1,"float"),
                        "ControlType": set_default(str(dataEV[7]),"交流帰還制御","str"),
                        "Info": str(dataEV[8])
                    }
                )

    if "様式PV" in wb.sheet_names():

        # シートの読み込み
        sheet_PV = wb.sheet_by_name("様式PV")
        # 初期化
        unitKey = None

        # 行のループ
        for i in range(10,sheet_PV.nrows):

            # シートから「行」の読み込み
            dataPV = sheet_PV.row_values(i)

            # 太陽光発電システム名称が空欄でない場合
            if (dataPV[0] != ""):

                data["PhotovoltaicSystems"][dataPV[0]] = {
                    "PowerConditionerEfficiency": set_default(dataPV[1], None, "float"),
                    "CellType": str(dataPV[2]),
                    "ArraySetupType": str(dataPV[3]),
                    "ArrayCapacity": float(dataPV[4]),
                    "Direction": float(dataPV[5]),
                    "Angle": float(dataPV[6]),
                    "Info": str(dataPV[7])
                }

    
    if "様式CG" in wb.sheet_names():

        # シートの読み込み
        sheet_CG = wb.sheet_by_name("様式CG")
        # 初期化
        unitKey = None

        # 行のループ
        for i in range(10,sheet_CG.nrows):

            # シートから「行」の読み込み
            dataCG = sheet_CG.row_values(i)

            # コージェネレーション設備名称が空欄でない場合
            if (dataCG[0] != ""):

                data["CogenerationSystems"][dataCG[0]] = {
                    "RatedCapacity": float(dataCG[1]),
                    "Number": float(dataCG[2]),
                    "PowerGenerationEfficiency_100": float(dataCG[3]),
                    "PowerGenerationEfficiency_75": float(dataCG[4]),
                    "PowerGenerationEfficiency_50": float(dataCG[5]),
                    "HeatGenerationEfficiency_100": float(dataCG[6]),
                    "HeatGenerationEfficiency_75": float(dataCG[7]),
                    "HeatGenerationEfficiency_50": float(dataCG[8]),
                    "HeatRecoveryPriorityCooling": set_default(dataCG[9], None, "str"),
                    "HeatRecoveryPriorityHeating": set_default(dataCG[10], None, "str"),
                    "HeatRecoveryPriorityHotWater": set_default(dataCG[11], None, "str"),
                    "24hourOperation": set_default(dataCG[12],'無', "str"),
                    "CoolingSystem": set_default(dataCG[13], None, "str"),
                    "HeatingSystem": set_default(dataCG[14], None, "str"),
                    "HowWaterSystem": set_default(dataCG[15], None, "str"),
                    "Info": str(dataCG[16])
                }

    # バリデーションの実行
    if validation:
        jsonschema.validate(data, schema_data)

    return data



def make_jsondata_from_Ver2_sheet(inputfileName, validation = False):
    """
    WEBPRO Ver2 用の入力シートから 入力データ（辞書型）を生成するプログラム
    """

    # 入力シートの読み込み
    wb = xlrd.open_workbook(inputfileName)

    # テンプレートjsonの読み込み
    with open( template_directory + 'template.json', 'r') as f:
        data = json.load(f)

    # スキーマの読み込み
    with open( template_directory + 'webproJsonSchema.json', 'r') as f:
        schema_data = json.load(f)
    
    # %%
    # 様式0の読み込み
    if "0) 基本情報" in wb.sheet_names():

        # シートの読み込み
        sheet_BL = wb.sheet_by_name("0) 基本情報")

        # BL-1	建築物の名称
        data["Building"]["Name"] = str(sheet_BL.cell(8, 2).value)
        # BL-2	都道府県	(選択)
        data["Building"]["BuildingAddress"]["Prefecture"] = str(sheet_BL.cell(9, 3).value)
        # BL-3	建築物所在地	市区町村	(選択)
        data["Building"]["BuildingAddress"]["City"]  = str(sheet_BL.cell(9, 5).value)
        # BL-4	丁目、番地等
        data["Building"]["BuildingAddress"]["Address"]  = str(sheet_BL.cell(10, 2).value)
        # BL-5	地域の区分		(自動)
        data["Building"]["Region"] = str(int(sheet_BL.cell(11, 2).value))
        # BL-6	年間日射地域区分		(自動)
        data["Building"]["AnnualSolarRegion"] = str(sheet_BL.cell(17, 2).value)
        # BL-7	延べ面積 	[㎡]	(数値)
        data["Building"]["BuildingFloorArea"] = float(sheet_BL.cell(16, 2).value)
        # BL-8	「他人から供給された熱」	冷熱	(数値)
        data["Building"]["Coefficient_DHC"]["Cooling"] = float(sheet_BL.cell(18, 2).value)
        # BL-9	の一次エネルギー換算係数	温熱	(数値)
        data["Building"]["Coefficient_DHC"]["Heating"] = float(sheet_BL.cell(19, 2).value)


    # 様式1の読み込み
    # 室用途の扱いが異なる。Ver3では様式1に記された建物用途・室用途が正となる。
    if "1) 室仕様" in wb.sheet_names():

        # シートの読み込み
        sheet_BL = wb.sheet_by_name("1) 室仕様")
        # 初期化
        roomKey = None

        # 行のループ
        for i in range(10,sheet_BL.nrows):

            # シートから「行」の読み込み
            dataBL = sheet_BL.row_values(i)

            # 階と室名が空欄でない場合
            if (dataBL[0] != "") and (dataBL[1] != ""):

                # 階＋室をkeyとする
                roomKey = str(dataBL[0]) + '_' + str(dataBL[1])

                # ゾーンはないと想定。
                data["Rooms"][roomKey] = {
                        "buildingType": str(dataBL[2]),               
                        "roomType": str(dataBL[3]),
                        "floorHeight": float(dataBL[5]),
                        "ceilingHeight": float(dataBL[6]),
                        "roomArea": float(dataBL[4]),
                        "zone": None,
                        "modelBuildingType": str(dataBL[11]),  
                        "buildingGroup": None,
                        "Info": str(dataBL[12])
                }


    ## 外皮
    # 窓面積 →　窓の枚数と読み替え。

    if "2-4) 外皮 " in wb.sheet_names():

        # シートの読み込み
        sheet_BE1 = wb.sheet_by_name("2-4) 外皮 ")
        # 初期化
        roomKey = None

        # 庇の番号
        evaes_num = 0

        # 行のループ
        for i in range(10,sheet_BE1.nrows):

            # シートから「行」の読み込み
            dataBE1 = sheet_BE1.row_values(i)

            # 階と室名が空欄でない場合
            if (dataBE1[0] != "") and (dataBE1[1] != ""):

                # 階＋室＋ゾーン名をkeyとする（上書き）
                roomKey = str(dataBE1[0]) + '_' + str(dataBE1[1])

                # 外壁の種類の判定（Ver.2のみ）
                if str(dataBE1[2]) == "日陰":
                    dataBE1[2] = "北"
                    wallType = "日の当たらない外壁"
                elif str(dataBE1[2]) == "水平":
                    dataBE1[2] = "水平（下）"
                    wallType = "日の当たる外壁"
                else:
                    wallType = "日の当たる外壁"

                # 日よけ効果係数
                if dataBE1[3] != "" and dataBE1[4] != "":
                    EavesID = "庇" + str(int(evaes_num))
                    evaes_num += 1

                    data["ShadingConfigure"][EavesID] = {
                        "shadingEffect_C": set_default(str(dataBE1[3]),None, "float"),
                        "shadingEffect_H": set_default(str(dataBE1[4]),None, "float"),
                        "x1": None,
                        "x2": None,
                        "x3": None,
                        "y1": None,
                        "y2": None,
                        "y3": None,
                        "zxPlus":  None,
                        "zxMinus": None,
                        "zyPlus":  None,
                        "zyMinus": None,
                        "Info": None
                    }
                else:
                    EavesID = "無"

                data["EnvelopeSet"][roomKey] = {
                        "isAirconditioned": "有",
                        "WallList": [
                            {
                                "Direction": str(dataBE1[2]),
                                "EnvelopeArea": set_default(str(dataBE1[6]),None, "float"),
                                "EnvelopeWidth": None,
                                "EnvelopeHeight": None,
                                "WallSpec": set_default(str(dataBE1[5]),"無","str"),
                                "WallType": wallType,
                                "WindowList":[
                                    {
                                        "WindowID": set_default(str(dataBE1[7]),"無","str"),
                                        "WindowNumber": set_default(str(dataBE1[8]),None, "float"),
                                        "isBlind": set_default(str(dataBE1[9]),"無","str"),
                                        "EavesID": EavesID,
                                        "Info": set_default(str(dataBE1[10]),"無","str"),
                                    }
                                ]       
                            }
                        ],
                    }

            else: # 階と室名が空欄である場合

                # 外壁の種類の判定（Ver.2のみ）
                if str(dataBE1[2]) == "日陰":
                    dataBE1[2] = "南"
                    wallType = "日の当たらない外壁"
                elif str(dataBE1[2]) == "水平":
                    dataBE1[2] = "水平（下）"
                    wallType = "日の当たる外壁"
                else:
                    wallType = "日の当たる外壁"

                # 日よけ効果係数
                if dataBE1[3] != "" and dataBE1[4] != "":
                    EavesID = "庇" + str(int(evaes_num))
                    evaes_num += 1

                    data["ShadingConfigure"][EavesID] = {
                        "shadingEffect_C": set_default(str(dataBE1[3]),None, "float"),
                        "shadingEffect_H": set_default(str(dataBE1[4]),None, "float"),
                        "x1": None,
                        "x2": None,
                        "x3": None,
                        "y1": None,
                        "y2": None,
                        "y3": None,
                        "zxPlus":  None,
                        "zxMinus": None,
                        "zyPlus":  None,
                        "zyMinus": None,
                        "Info": None
                    }
                else:
                    EavesID = "無"

                data["EnvelopeSet"][roomKey]["WallList"].append(
                    {
                        "Direction": str(dataBE1[2]),
                        "EnvelopeArea": set_default(str(dataBE1[6]),None, "float"),
                        "EnvelopeWidth": None,
                        "EnvelopeHeight": None,
                        "WallSpec": set_default(str(dataBE1[5]),"無","str"),
                        "WallType": wallType,
                        "WindowList":[
                            {
                                "WindowID": set_default(str(dataBE1[7]),"無","str"),
                                "WindowNumber": set_default(str(dataBE1[8]),None, "float"),
                                "isBlind": set_default(str(dataBE1[9]),"無","str"),
                                "EavesID": EavesID,
                                "Info": set_default(str(dataBE1[10]),"無","str"),
                            }
                        ]       
                    }
                )

    if "2-2) 外壁構成 " in wb.sheet_names():

        # シートの読み込み
        sheet_BE2 = wb.sheet_by_name("2-2) 外壁構成 ")
        # 初期化
        eltKey = None
        inputMethod = None

        # 行のループ
        for i in range(10,sheet_BE2.nrows):

            # シートから「行」の読み込み
            dataBE2 = sheet_BE2.row_values(i)

            # 断熱仕様名称が空欄でない場合
            if (dataBE2[0] != ""):

                # 断熱仕様名称をkeyとする（上書き）
                eltKey = str(dataBE2[0]) 

                # 接地壁の扱い
                if dataBE2[1] == "接地壁":
                    for room_name in data["EnvelopeSet"]:
                        for wall_id, wall_conf in enumerate(data["EnvelopeSet"][room_name]["WallList"]):
                            if wall_conf["WallSpec"] == eltKey:
                                data["EnvelopeSet"][room_name]["WallList"][wall_id]["WallType"] = "地盤に接する外壁"

                # 入力方法を識別
                if dataBE2[2] != "":
                    inputMethod = "熱貫流率を入力"
                else:
                    inputMethod = "建材構成を入力"
                
                if inputMethod == "熱貫流率を入力":

                    data["WallConfigure"][eltKey] = {
                            "structureType": "その他",
                            "solarAbsorptionRatio": None,
                            "inputMethod": inputMethod,
                            "Uvalue": set_default(dataBE2[2], None, "float"),
                            "Info": set_default(dataBE2[6], "無","str"),
                        }

                elif inputMethod == "建材構成を入力":

                    # 次の行を読み込み
                    dataBE2 = sheet_BE2.row_values(i+1)

                    if dataBE2[4] != "":

                        data["WallConfigure"][eltKey] = {
                                "structureType": "その他",
                                "solarAbsorptionRatio": None,
                                "inputMethod": inputMethod,
                                "layers": [
                                    {
                                    "materialID": set_default(dataBE2[4].replace(' ', ''), None, "str"),
                                    "conductivity": None,
                                    "thickness": set_default(dataBE2[5], None, "float"),
                                    "Info": set_default(dataBE2[6], "無", "str")
                                    }
                                ]
                            }

                    for loop in range(2,10):

                        # 次の行を読み込み
                        dataBE2 = sheet_BE2.row_values(i+loop)
                        
                        if dataBE2[4] != "":
                            data["WallConfigure"][eltKey]["layers"].append(
                                {
                                "materialID": set_default(dataBE2[4], None, "str"),
                                "conductivity": None,
                                "thickness": set_default(dataBE2[5], None, "float"),
                                "Info": set_default(dataBE2[6], "無", "str")
                                }
                            )


    if "2-3) 窓仕様" in wb.sheet_names():

        # シートの読み込み
        sheet_BE3 = wb.sheet_by_name("2-3) 窓仕様")
        # 初期化
        eltKey = None
        inputMethod = None

        # 行のループ
        for i in range(10,sheet_BE3.nrows):

            # シートから「行」の読み込み
            dataBE3 = sheet_BE3.row_values(i)

            # 開口部仕様名称が空欄でない場合
            if (dataBE3[0] != ""):

                # 開口部仕様名称をkeyとする（上書き）
                eltKey = str(dataBE3[0]) 

                # 入力方法を識別
                if (dataBE3[1] != "") and (dataBE3[2] != ""):
                    inputMethod = "性能値を入力"
                elif (dataBE3[5] != "") and (dataBE3[6] != ""):
                    inputMethod = "ガラスの性能を入力"
                elif (dataBE3[4] != ""):
                    inputMethod = "ガラスの種類を入力"
                else:
                    raise Exception('Error!')

                if inputMethod == "性能値を入力":

                    data["WindowConfigure"][eltKey] = {
                            "windowArea": 1,
                            "windowWidth": None,
                            "windowHeight": None,
                            "inputMethod": inputMethod,
                            "windowUvalue": set_default(dataBE3[1], None, "float"),
                            "windowIvalue": set_default(dataBE3[2], None, "float"),
                            "layerType": "単層",
                            "glassUvalue": set_default(dataBE3[5], None, "float"),
                            "glassIvalue": set_default(dataBE3[6], None, "float"),
                            "Info": set_default(dataBE3[7], "無","str"),
                        }

                elif inputMethod == "ガラスの性能を入力":

                    if dataBE3[3] == "木製(単板ガラス)":
                        frameType = "木製"
                        layerType = "単層"
                    elif dataBE3[3] == "木製(複層ガラス)":
                        frameType = "木製"
                        layerType = "複層"
                    elif dataBE3[3] == "樹脂製(単板ガラス)":
                        frameType = "樹脂製"
                        layerType = "単層"
                    elif dataBE3[3] == "樹脂製(複層ガラス)":
                        frameType = "樹脂製"
                        layerType = "複層"
                    elif dataBE3[3] == "金属木複合製(単板ガラス)":
                        frameType = "金属木複合製"
                        layerType = "単層"
                    elif dataBE3[3] == "金属木複合製(複層ガラス)":
                        frameType = "金属木複合製"
                        layerType = "複層"
                    elif dataBE3[3] == "金属樹脂複合製(単板ガラス)":
                        frameType = "金属樹脂複合製"
                        layerType = "単層"
                    elif dataBE3[3] == "金属樹脂複合製(複層ガラス)":
                        frameType = "金属樹脂複合製"
                        layerType = "複層"
                    elif dataBE3[3] == "金属製(単板ガラス)":
                        frameType = "金属製"
                        layerType = "単層"
                    elif dataBE3[3] == "金属製(複層ガラス)":
                        frameType = "金属製"
                        layerType = "複層"
                    else:
                        frameType = None
                        layerType = None

                    data["WindowConfigure"][eltKey] = {
                            "windowArea": 1,
                            "windowWidth": None,
                            "windowHeight": None,
                            "inputMethod": inputMethod,
                            "frameType": frameType,
                            "layerType": layerType,
                            "glassUvalue": set_default(dataBE3[5], None, "float"),
                            "glassIvalue": set_default(dataBE3[6], None, "float"),
                            "Info": set_default(dataBE3[7], "無","str"),
                        }

                elif inputMethod == "ガラスの種類を入力":

                    if dataBE3[3] == "木製(単板ガラス)":
                        frameType = "木製"
                        layerType = "単層"
                    elif dataBE3[3] == "木製(複層ガラス)":
                        frameType = "木製"
                        layerType = "複層"
                    elif dataBE3[3] == "樹脂製(単板ガラス)":
                        frameType = "樹脂製"
                        layerType = "単層"
                    elif dataBE3[3] == "樹脂製(複層ガラス)":
                        frameType = "樹脂製"
                        layerType = "複層"
                    elif dataBE3[3] == "金属木複合製(単板ガラス)":
                        frameType = "金属木複合製"
                        layerType = "単層"
                    elif dataBE3[3] == "金属木複合製(複層ガラス)":
                        frameType = "金属木複合製"
                        layerType = "複層"
                    elif dataBE3[3] == "金属樹脂複合製(単板ガラス)":
                        frameType = "金属樹脂複合製"
                        layerType = "単層"
                    elif dataBE3[3] == "金属樹脂複合製(複層ガラス)":
                        frameType = "金属樹脂複合製"
                        layerType = "複層"
                    elif dataBE3[3] == "金属製(単板ガラス)":
                        frameType = "金属製"
                        layerType = "単層"
                    elif dataBE3[3] == "金属製(複層ガラス)":
                        frameType = "金属製"
                        layerType = "複層"
                    else:
                        frameType = None
                        layerType = None
                        
                    data["WindowConfigure"][eltKey] = {
                            "windowArea": 1,
                            "windowWidth": None,
                            "windowHeight": None,
                            "inputMethod": inputMethod,
                            "frameType": frameType,
                            "glassID": set_default(dataBE3[4], None, "str"),
                            "Info": set_default(dataBE3[7], "無","str"),
                        }


    ## 空調設備
    if "2-1) 空調ゾーン" in wb.sheet_names():
        
        # シートの読み込み
        sheet_AC1 = wb.sheet_by_name("2-1) 空調ゾーン")
        # 初期化
        roomKey = None

        # 行のループ
        for i in range(10,sheet_AC1.nrows):

            # シートから「行」の読み込み
            dataAC1 = sheet_AC1.row_values(i)

            # 階と室名が空欄でない場合
            if (dataAC1[7] != "") and (dataAC1[8] != ""):

                # 階＋室+ゾーン名をkeyとする
                roomKey = str(dataAC1[7]) + '_' + str(dataAC1[8])
                
                # 冷暖同時供給については、暫定で「無」を入れておく。後に再度判定。
                data["AirConditioningZone"][roomKey] = {
                    "isNatualVentilation": "無",
                    "isSimultaneousSupply": "無",
                    "AHU_cooling_insideLoad": set_default(dataAC1[9], None, "str"),
                    "AHU_cooling_outdoorLoad": set_default(dataAC1[10], None, "str"),
                    "AHU_heating_insideLoad": set_default(dataAC1[9], None, "str"),
                    "AHU_heating_outdoorLoad": set_default(dataAC1[10], None, "str"),
                    "Info": str(dataAC1[9])
                }

    if "2-5) 熱源" in wb.sheet_names():
        
        # シートの読み込み
        sheet_AC2 = wb.sheet_by_name("2-5) 熱源")
        # 初期化
        unitKey = None
        modeKey_C = None
        modeKey_H = None

        # 行のループ
        for i in range(10,sheet_AC2.nrows):

            # シートから「行」の読み込み
            dataAC2 = sheet_AC2.row_values(i)

            # 熱源群名称と運転モードが空欄でない場合
            if (dataAC2[0] != ""):      
                
                unitKey = str(dataAC2[0])

                # 熱源群名称が入力されている箇所は、蓄熱有無を判定する。
                if dataAC2[3] == "氷蓄熱" or dataAC2[3] == "水蓄熱(成層型)" or dataAC2[3] == "水蓄熱(混合型)":
                    storage_flag = True
                elif dataAC2[3] == "追掛":
                    storage_flag = False
                else:
                    storage_flag = False

                # 台数制御の有無
                if dataAC2[2] == "有":
                    staging_control_flag = "有"
                else:
                    staging_control_flag = "無"

                # 冷暖同時供給の有無
                if dataAC2[1] == "有":
                    isSimultaneous_flag = "有"
                else:
                    isSimultaneous_flag = "無"


                if (dataAC2[5] != "") and (dataAC2[6] != ""):     # 冷熱源
                
                    if storage_flag:
                        modeKey_C = "冷房(蓄熱)"
                        StorageType = set_default(dataAC2[3], None, "str")
                        StorageSize = set_default(dataAC2[4], None, "float")
                    else:
                        modeKey_C = "冷房"
                        StorageType = None
                        StorageSize = None

                    if dataAC2[11] == "" or dataAC2[11] == 0:   # 補機電力が0であれば
                        HeatsourceRatedPowerConsumption = set_default(dataAC2[10], 0, "float")
                        HeatsourceRatedFuelConsumption  = 0
                    else:
                        HeatsourceRatedPowerConsumption = set_default(dataAC2[11], 0, "float")
                        HeatsourceRatedFuelConsumption  = set_default(dataAC2[10], 0, "float")
                        

                    data["HeatsourceSystem"][unitKey] = {
                        modeKey_C : {
                            "StorageType": StorageType,
                            "StorageSize": StorageSize,
                            "isStagingControl": staging_control_flag,
                            "isSimultaneous_for_ver2" : isSimultaneous_flag,
                            "Heatsource" :[
                                {
                                    "HeatsourceType": str(dataAC2[5]),
                                    "Number": float(dataAC2[7]),
                                    "SupplyWaterTempSummer": set_default(dataAC2[8], None, "float"),
                                    "SupplyWaterTempMiddle": set_default(dataAC2[8], None, "float"),
                                    "SupplyWaterTempWinter": set_default(dataAC2[8], None, "float"),
                                    "HeatsourceRatedCapacity": float(dataAC2[9]),
                                    "HeatsourceRatedPowerConsumption": HeatsourceRatedPowerConsumption,
                                    "HeatsourceRatedFuelConsumption": HeatsourceRatedFuelConsumption,
                                    "PrimaryPumpPowerConsumption": set_default(dataAC2[12], 0, "float"),
                                    "PrimaryPumpContolType": "無",
                                    "CoolingTowerCapacity": set_default(dataAC2[13], 0, "float"),
                                    "CoolingTowerFanPowerConsumption": set_default(dataAC2[14], 0, "float"),
                                    "CoolingTowerPumpPowerConsumption": set_default(dataAC2[15], 0, "float"),
                                    "CoolingTowerContolType": "無",
                                    "Info": str(dataAC2[23])
                                }
                            ]
                        }
                    }

                if (dataAC2[5] != "") and (dataAC2[16] != ""):     # 温熱源
                    
                    if storage_flag:
                        modeKey_H = "暖房(蓄熱)"
                        StorageType = set_default(dataAC2[3], None, "str")
                        StorageSize = set_default(dataAC2[4], None, "float")
                    else:
                        modeKey_H = "暖房"
                        StorageType = None
                        StorageSize = None

                    if dataAC2[21] == "" or dataAC2[21] == 0:   # 補機電力が0であれば
                        HeatsourceRatedPowerConsumption = set_default(dataAC2[20], 0, "float")
                        HeatsourceRatedFuelConsumption  = 0
                    else:
                        HeatsourceRatedPowerConsumption = set_default(dataAC2[21], 0, "float")
                        HeatsourceRatedFuelConsumption  = set_default(dataAC2[20], 0, "float")
                        
                    if unitKey in data["HeatsourceSystem"]:

                        data["HeatsourceSystem"][unitKey][modeKey_H] = \
                            {
                                "StorageType": StorageType,
                                "StorageSize": StorageSize,
                                "isStagingControl": staging_control_flag,
                                "isSimultaneous_for_ver2" : isSimultaneous_flag,
                                "Heatsource" :[
                                    {
                                        "HeatsourceType": str(dataAC2[5]),
                                        "Number": float(dataAC2[17]),
                                        "SupplyWaterTempSummer": set_default(dataAC2[18], None, "float"),
                                        "SupplyWaterTempMiddle": set_default(dataAC2[18], None, "float"),
                                        "SupplyWaterTempWinter": set_default(dataAC2[18], None, "float"),
                                        "HeatsourceRatedCapacity": float(dataAC2[19]),
                                        "HeatsourceRatedPowerConsumption": HeatsourceRatedPowerConsumption,
                                        "HeatsourceRatedFuelConsumption": HeatsourceRatedFuelConsumption,
                                        "PrimaryPumpPowerConsumption": set_default(dataAC2[22], 0, "float"),
                                        "PrimaryPumpContolType": "無",
                                        "CoolingTowerCapacity": 0,
                                        "CoolingTowerFanPowerConsumption": 0,
                                        "CoolingTowerPumpPowerConsumption": 0,
                                        "CoolingTowerContolType": "無",
                                        "Info": str(dataAC2[23])
                                    }
                                ]
                            }

                    else:
                        data["HeatsourceSystem"][unitKey] = {
                            modeKey_H : {
                                "StorageType": StorageType,
                                "StorageSize": StorageSize,
                                "isStagingControl": set_default(dataAC2[2], "無", "str"),
                                "isSimultaneous_for_ver2" : isSimultaneous_flag,
                                "Heatsource" :[
                                    {
                                        "HeatsourceType": str(dataAC2[5]),
                                        "Number": float(dataAC2[17]),
                                        "SupplyWaterTempSummer": set_default(dataAC2[18], None, "float"),
                                        "SupplyWaterTempMiddle": set_default(dataAC2[18], None, "float"),
                                        "SupplyWaterTempWinter": set_default(dataAC2[18], None, "float"),
                                        "HeatsourceRatedCapacity": float(dataAC2[19]),
                                        "HeatsourceRatedPowerConsumption": HeatsourceRatedPowerConsumption,
                                        "HeatsourceRatedFuelConsumption": HeatsourceRatedFuelConsumption,
                                        "PrimaryPumpPowerConsumption": set_default(dataAC2[22], 0, "float"),
                                        "PrimaryPumpContolType": "無",
                                        "CoolingTowerCapacity": 0,
                                        "CoolingTowerFanPowerConsumption": 0,
                                        "CoolingTowerPumpPowerConsumption": 0,
                                        "CoolingTowerContolType": "無",
                                        "Info": str(dataAC2[23])
                                    }
                                ]
                            }
                        }

            elif (dataAC2[3] == ""):  # 熱源機種を追加（複数台設置されている場合）

                if (dataAC2[5] != "") and (dataAC2[6] != ""):     # 冷熱源
    
                    if dataAC2[11] == "" or dataAC2[11] == 0:   # 補機電力が0であれば
                        HeatsourceRatedPowerConsumption = set_default(dataAC2[10], 0, "float")
                        HeatsourceRatedFuelConsumption  = 0
                    else:
                        HeatsourceRatedPowerConsumption = set_default(dataAC2[11], 0, "float")
                        HeatsourceRatedFuelConsumption  = set_default(dataAC2[10], 0, "float")
                    
                    data["HeatsourceSystem"][unitKey][modeKey_C]["Heatsource"].append(
                        {
                            "HeatsourceType": str(dataAC2[5]),
                            "Number": float(dataAC2[7]),
                            "SupplyWaterTempSummer": set_default(dataAC2[8], None, "float"),
                            "SupplyWaterTempMiddle": set_default(dataAC2[8], None, "float"),
                            "SupplyWaterTempWinter": set_default(dataAC2[8], None, "float"),
                            "HeatsourceRatedCapacity": float(dataAC2[9]),
                            "HeatsourceRatedPowerConsumption": HeatsourceRatedPowerConsumption,
                            "HeatsourceRatedFuelConsumption": HeatsourceRatedFuelConsumption,
                            "PrimaryPumpPowerConsumption": set_default(dataAC2[12], 0, "float"),
                            "PrimaryPumpContolType": "無",
                            "CoolingTowerCapacity": set_default(dataAC2[13], 0, "float"),
                            "CoolingTowerFanPowerConsumption": set_default(dataAC2[14], 0, "float"),
                            "CoolingTowerPumpPowerConsumption": set_default(dataAC2[15], 0, "float"),
                            "CoolingTowerContolType": "無",
                            "Info": str(dataAC2[23])
                        }
                    )

                if (dataAC2[5] != "") and (dataAC2[16] != ""):     # 温熱源
                    
                    if dataAC2[21] == "" or dataAC2[21] == 0:   # 補機電力が0であれば
                        HeatsourceRatedPowerConsumption = set_default(dataAC2[20], 0, "float")
                        HeatsourceRatedFuelConsumption  = 0
                    else:
                        HeatsourceRatedPowerConsumption = set_default(dataAC2[21], 0, "float")
                        HeatsourceRatedFuelConsumption  = set_default(dataAC2[20], 0, "float")

                    data["HeatsourceSystem"][unitKey][modeKey_H]["Heatsource"].append(
                        {
                            "HeatsourceType": str(dataAC2[5]),
                            "Number": float(dataAC2[17]),
                            "SupplyWaterTempSummer": set_default(dataAC2[18], None, "float"),
                            "SupplyWaterTempMiddle": set_default(dataAC2[18], None, "float"),
                            "SupplyWaterTempWinter": set_default(dataAC2[18], None, "float"),
                            "HeatsourceRatedCapacity": float(dataAC2[19]),
                            "HeatsourceRatedPowerConsumption": HeatsourceRatedPowerConsumption,
                            "HeatsourceRatedFuelConsumption": HeatsourceRatedFuelConsumption,
                            "PrimaryPumpPowerConsumption": set_default(dataAC2[22], 0, "float"),
                            "PrimaryPumpContolType": "無",
                            "CoolingTowerCapacity": 0,
                            "CoolingTowerFanPowerConsumption": 0,
                            "CoolingTowerPumpPowerConsumption": 0,
                            "CoolingTowerContolType": "無",
                            "Info": str(dataAC2[23])
                        }
                    )

            elif (dataAC2[3] != ""):  # 熱源機種を追加（複数のモードがある場合）

                # 熱源群名称が入力されている箇所は、蓄熱有無を判定する。
                if dataAC2[3] == "氷蓄熱" or dataAC2[3] == "水蓄熱(成層型)" or dataAC2[3] == "水蓄熱(混合型)":
                    storage_flag = True
                elif dataAC2[3] == "追掛":
                    storage_flag = False
                else:
                    storage_flag = False

                if (dataAC2[5] != "") and (dataAC2[6] != ""):     # 冷熱源
                
                    if storage_flag:
                        modeKey_C = "冷房(蓄熱)"
                        StorageType = set_default(dataAC2[3], None, "str")
                        StorageSize = set_default(dataAC2[4], None, "float")
                    else:
                        modeKey_C = "冷房"
                        StorageType = None
                        StorageSize = None

                    if dataAC2[11] == "" or dataAC2[11] == 0:   # 補機電力が0であれば
                        HeatsourceRatedPowerConsumption = set_default(dataAC2[10], 0, "float")
                        HeatsourceRatedFuelConsumption  = 0
                    else:
                        HeatsourceRatedPowerConsumption = set_default(dataAC2[11], 0, "float")
                        HeatsourceRatedFuelConsumption  = set_default(dataAC2[10], 0, "float")
                        
                    if unitKey in data["HeatsourceSystem"]:

                        data["HeatsourceSystem"][unitKey][modeKey_C] = \
                            {
                                "StorageType": StorageType,
                                "StorageSize": StorageSize,
                                "isStagingControl": staging_control_flag,
                                "isSimultaneous_for_ver2" : isSimultaneous_flag,
                                "Heatsource" :[
                                    {
                                        "HeatsourceType": str(dataAC2[5]),
                                        "Number": float(dataAC2[7]),
                                        "SupplyWaterTempSummer": set_default(dataAC2[8], None, "float"),
                                        "SupplyWaterTempMiddle": set_default(dataAC2[8], None, "float"),
                                        "SupplyWaterTempWinter": set_default(dataAC2[8], None, "float"),
                                        "HeatsourceRatedCapacity": float(dataAC2[9]),
                                        "HeatsourceRatedPowerConsumption": HeatsourceRatedPowerConsumption,
                                        "HeatsourceRatedFuelConsumption": HeatsourceRatedFuelConsumption,
                                        "PrimaryPumpPowerConsumption": set_default(dataAC2[12], 0, "float"),
                                        "PrimaryPumpContolType": "無",
                                        "CoolingTowerCapacity": set_default(dataAC2[13], 0, "float"),
                                        "CoolingTowerFanPowerConsumption": set_default(dataAC2[14], 0, "float"),
                                        "CoolingTowerPumpPowerConsumption": set_default(dataAC2[15], 0, "float"),
                                        "CoolingTowerContolType": "無",
                                        "Info": str(dataAC2[23])
                                    }
                                ]
                            }

                    else:
                        data["HeatsourceSystem"][unitKey] = {
                            modeKey_C : {
                                "StorageType": StorageType,
                                "StorageSize": StorageSize,
                                "isStagingControl": staging_control_flag,
                                "isSimultaneous_for_ver2" : isSimultaneous_flag,
                                "Heatsource" :[
                                    {
                                        "HeatsourceType": str(dataAC2[5]),
                                        "Number": float(dataAC2[7]),
                                        "SupplyWaterTempSummer": set_default(dataAC2[8], None, "float"),
                                        "SupplyWaterTempMiddle": set_default(dataAC2[8], None, "float"),
                                        "SupplyWaterTempWinter": set_default(dataAC2[8], None, "float"),
                                        "HeatsourceRatedCapacity": float(dataAC2[9]),
                                        "HeatsourceRatedPowerConsumption": HeatsourceRatedPowerConsumption,
                                        "HeatsourceRatedFuelConsumption": HeatsourceRatedFuelConsumption,
                                        "PrimaryPumpPowerConsumption": set_default(dataAC2[12], 0, "float"),
                                        "PrimaryPumpContolType": "無",
                                        "CoolingTowerCapacity": set_default(dataAC2[13], 0, "float"),
                                        "CoolingTowerFanPowerConsumption": set_default(dataAC2[14], 0, "float"),
                                        "CoolingTowerPumpPowerConsumption": set_default(dataAC2[15], 0, "float"),
                                        "CoolingTowerContolType": "無",
                                        "Info": str(dataAC2[23])
                                    }
                                ]
                            }
                        }

                if (dataAC2[5] != "") and (dataAC2[16] != ""):     # 温熱源
                    
                    if storage_flag:
                        modeKey_H = "暖房(蓄熱)"
                        StorageType = set_default(dataAC2[3], None, "str")
                        StorageSize = set_default(dataAC2[4], None, "float")
                    else:
                        modeKey_H = "暖房"
                        StorageType = None
                        StorageSize = None

                    if dataAC2[21] == "" or dataAC2[21] == 0:   # 補機電力が0であれば
                        HeatsourceRatedPowerConsumption = set_default(dataAC2[20], 0, "float")
                        HeatsourceRatedFuelConsumption  = 0
                    else:
                        HeatsourceRatedPowerConsumption = set_default(dataAC2[21], 0, "float")
                        HeatsourceRatedFuelConsumption  = set_default(dataAC2[20], 0, "float")
                        
                    if unitKey in data["HeatsourceSystem"]:

                        data["HeatsourceSystem"][unitKey][modeKey_H] = \
                            {
                                "StorageType": StorageType,
                                "StorageSize": StorageSize,
                                "isStagingControl": staging_control_flag,
                                "isSimultaneous_for_ver2" : isSimultaneous_flag,
                                "Heatsource" :[
                                    {
                                        "HeatsourceType": str(dataAC2[5]),
                                        "Number": float(dataAC2[17]),
                                        "SupplyWaterTempSummer": set_default(dataAC2[18], None, "float"),
                                        "SupplyWaterTempMiddle": set_default(dataAC2[18], None, "float"),
                                        "SupplyWaterTempWinter": set_default(dataAC2[18], None, "float"),
                                        "HeatsourceRatedCapacity": float(dataAC2[19]),
                                        "HeatsourceRatedPowerConsumption": HeatsourceRatedPowerConsumption,
                                        "HeatsourceRatedFuelConsumption": HeatsourceRatedFuelConsumption,
                                        "PrimaryPumpPowerConsumption": set_default(dataAC2[22], 0, "float"),
                                        "PrimaryPumpContolType": "無",
                                        "CoolingTowerCapacity": 0,
                                        "CoolingTowerFanPowerConsumption": 0,
                                        "CoolingTowerPumpPowerConsumption": 0,
                                        "CoolingTowerContolType": "無",
                                        "Info": str(dataAC2[23])
                                    }
                                ]
                            }

                    else:
                        
                        data["HeatsourceSystem"][unitKey] = {
                            modeKey_H : {
                                "StorageType": StorageType,
                                "StorageSize": StorageSize,
                                "isStagingControl": staging_control_flag,
                                "isSimultaneous_for_ver2" : isSimultaneous_flag,
                                "Heatsource" :[
                                    {
                                        "HeatsourceType": str(dataAC2[5]),
                                        "Number": float(dataAC2[17]),
                                        "SupplyWaterTempSummer": set_default(dataAC2[18], None, "float"),
                                        "SupplyWaterTempMiddle": set_default(dataAC2[18], None, "float"),
                                        "SupplyWaterTempWinter": set_default(dataAC2[18], None, "float"),
                                        "HeatsourceRatedCapacity": float(dataAC2[19]),
                                        "HeatsourceRatedPowerConsumption": HeatsourceRatedPowerConsumption,
                                        "HeatsourceRatedFuelConsumption": HeatsourceRatedFuelConsumption,
                                        "PrimaryPumpPowerConsumption": set_default(dataAC2[22], 0, "float"),
                                        "PrimaryPumpContolType": "無",
                                        "CoolingTowerCapacity": 0,
                                        "CoolingTowerFanPowerConsumption": 0,
                                        "CoolingTowerPumpPowerConsumption": 0,
                                        "CoolingTowerContolType": "無",
                                        "Info": str(dataAC2[23])
                                    }
                                ]
                            }
                        }


    if "2-6) 2次ﾎﾟﾝﾌﾟ" in wb.sheet_names():
        
        # シートの読み込み
        sheet_AC3 = wb.sheet_by_name("2-6) 2次ﾎﾟﾝﾌﾟ")
        # 初期化
        unitKey = None
        modeKey = None

        # 行のループ
        for i in range(10,sheet_AC3.nrows):

            # シートから「行」の読み込み
            dataAC3 = sheet_AC3.row_values(i)

            # 二次ポンプ群名称と運転モードが空欄でない場合
            if (dataAC3[0] != "") and ( (dataAC3[2] != "") or (dataAC3[3] != "") ):      
                
                unitKey = str(dataAC3[0])

                if dataAC3[2] != "":
                    modeKey = "冷房"

                    data["SecondaryPumpSystem"][unitKey] = {
                        modeKey : {
                            "TempelatureDifference": float(dataAC3[2]),
                            "isStagingControl": set_default(dataAC3[1], "無", "str"),
                            "SecondaryPump" :[
                                {
                                    "Number": float(dataAC3[5]),
                                    "RatedWaterFlowRate": float(dataAC3[6]),
                                    "RatedPowerConsumption": float(dataAC3[7]),
                                    "ContolType": set_default(dataAC3[8], "無", "str"),
                                    "MinOpeningRate": set_default(dataAC3[9], None, "float"),
                                    "Info": str(dataAC3[10])
                                }
                            ]
                        }
                    }
            
                if dataAC3[3] != "":

                    modeKey = "暖房"

                    if unitKey in data["SecondaryPumpSystem"]:

                        data["SecondaryPumpSystem"][unitKey][modeKey] = \
                            {
                                "TempelatureDifference": float(dataAC3[3]),
                                "isStagingControl": set_default(dataAC3[1], "無", "str"),
                                "SecondaryPump" :[
                                    {
                                        "Number": float(dataAC3[5]),
                                        "RatedWaterFlowRate": float(dataAC3[6]),
                                        "RatedPowerConsumption": float(dataAC3[7]),
                                        "ContolType": set_default(dataAC3[8], "無", "str"),
                                        "MinOpeningRate": set_default(dataAC3[9], None, "float"),
                                        "Info": str(dataAC3[10])
                                    }
                                ]
                            }

                    else:
                            
                        data["SecondaryPumpSystem"][unitKey] = {
                            modeKey : {
                                "TempelatureDifference": float(dataAC3[3]),
                                "isStagingControl": set_default(dataAC3[1], "無", "str"),
                                "SecondaryPump" :[
                                    {
                                        "Number": float(dataAC3[5]),
                                        "RatedWaterFlowRate": float(dataAC3[6]),
                                        "RatedPowerConsumption": float(dataAC3[7]),
                                        "ContolType": set_default(dataAC3[8], "無", "str"),
                                        "MinOpeningRate": set_default(dataAC3[9], None, "float"),
                                        "Info": str(dataAC3[10])
                                    }
                                ]
                            }
                        }

            elif (dataAC3[0] == "") and (dataAC3[4] != ""):

                if "冷房" in data["SecondaryPumpSystem"][unitKey]:

                    data["SecondaryPumpSystem"][unitKey]["冷房"]["SecondaryPump"].append(
                        {
                            "Number": float(dataAC3[5]),
                            "RatedWaterFlowRate": float(dataAC3[6]),
                            "RatedPowerConsumption": float(dataAC3[7]),
                            "ContolType": set_default(dataAC3[8], "無", "str"),
                            "MinOpeningRate": set_default(dataAC3[9], None, "float"),
                            "Info": str(dataAC3[10])
                        }
                    )

                if "暖房" in data["SecondaryPumpSystem"][unitKey]:

                    data["SecondaryPumpSystem"][unitKey]["暖房"]["SecondaryPump"].append(
                        {
                            "Number": float(dataAC3[5]),
                            "RatedWaterFlowRate": float(dataAC3[6]),
                            "RatedPowerConsumption": float(dataAC3[7]),
                            "ContolType": set_default(dataAC3[8], "無", "str"),
                            "MinOpeningRate": set_default(dataAC3[9], None, "float"),
                            "Info": str(dataAC3[10])
                        }
                    )
    
    
    if "2-7) 空調機" in wb.sheet_names():
        
        # シートの読み込み
        sheet_AC4 = wb.sheet_by_name("2-7) 空調機")
        # 初期化
        unitKey = None

        # 行のループ
        for i in range(10,sheet_AC4.nrows):

            # シートから「行」の読み込み
            dataAC4 = sheet_AC4.row_values(i)

            # 空調機群名称が空欄でない場合
            if (dataAC4[0] != ""):      
                
                unitKey = str(dataAC4[0])

                E_fan1 = set_default(dataAC4[6], 0, "float")
                E_fan2 = set_default(dataAC4[7], 0, "float")
                E_fan3 = set_default(dataAC4[8], 0, "float")
                E_fan4 = set_default(dataAC4[9], 0, "float")

                data["AirHandlingSystem"][unitKey] = {
                    "isEconomizer": set_default(dataAC4[13], "無", "str"),
                    "EconomizerMaxAirVolume": set_default(dataAC4[5], None, "float"),
                    "isOutdoorAirCut": set_default(dataAC4[12], "無", "str"),
                    "Pump_cooling": set_default(dataAC4[19], None, "str"),
                    "Pump_heating": set_default(dataAC4[20], None, "str"),
                    "HeatSource_cooling": set_default(dataAC4[21], None, "str"),
                    "HeatSource_heating": set_default(dataAC4[22], None, "str"),
                    "AirHandlingUnit" :[
                        {
                            "Type": str(dataAC4[2]),
                            "Number": float(dataAC4[1]),
                            "RatedCapacityCooling": set_default(dataAC4[3], None, "float"),
                            "RatedCapacityHeating": set_default(dataAC4[4], None, "float"),
                            "FanType": None,
                            "FanAirVolume": set_default(dataAC4[15], None, "float"),
                            "FanPowerConsumption": set_default(E_fan1+E_fan2+E_fan3+E_fan4, None, "float"),
                            "FanControlType": set_default(dataAC4[10], "無", "str"),
                            "FanMinOpeningRate": set_default(dataAC4[11], None, "float"),
                            "AirHeatExchangeRatioCooling": set_default(dataAC4[16], None, "float"),
                            "AirHeatExchangeRatioHeating": set_default(dataAC4[16], None, "float"),
                            "AirHeatExchangerEffectiveAirVolumeRatio": None,
                            "AirHeatExchangerControl": set_default(dataAC4[17], "無", "str"),
                            "AirHeatExchangerPowerConsumption": set_default(dataAC4[18], None, "float"),
                            "Info": str(dataAC4[22])
                        }
                    ]
                }


            elif (dataAC4[2] != ""):     

                E_fan1 = set_default(dataAC4[6], 0, "float")
                E_fan2 = set_default(dataAC4[7], 0, "float")
                E_fan3 = set_default(dataAC4[8], 0, "float")
                E_fan4 = set_default(dataAC4[9], 0, "float")

                data["AirHandlingSystem"][unitKey]["AirHandlingUnit"].append(
                    {
                        "Type": str(dataAC4[2]),
                        "Number": float(dataAC4[1]),
                        "RatedCapacityCooling": set_default(dataAC4[3], None, "float"),
                        "RatedCapacityHeating": set_default(dataAC4[4], None, "float"),
                        "FanType": None,
                        "FanAirVolume": set_default(dataAC4[15], None, "float"),
                        "FanPowerConsumption": set_default(E_fan1+E_fan2+E_fan3+E_fan4, None, "float"),
                        "FanControlType": set_default(dataAC4[10], "無", "str"),
                        "FanMinOpeningRate": set_default(dataAC4[11], None, "float"),
                        "AirHeatExchangeRatioCooling": set_default(dataAC4[16], None, "float"),
                        "AirHeatExchangeRatioHeating": set_default(dataAC4[16], None, "float"),
                        "AirHeatExchangerEffectiveAirVolumeRatio": None,
                        "AirHeatExchangerControl": set_default(dataAC4[17], "無", "str"),
                        "AirHeatExchangerPowerConsumption": set_default(dataAC4[18], None, "float"),
                        "Info": str(dataAC4[22])
                    }
                )

                # 外気冷房制御等
                if dataAC4[13] == "有" and dataAC4[5] != "":
                    data["AirHandlingSystem"][unitKey]["isEconomizer"] = dataAC4[13]
                    data["AirHandlingSystem"][unitKey]["EconomizerMaxAirVolume"] = set_default(dataAC4[5], None, "float")
                if dataAC4[12] == "有":
                    data["AirHandlingSystem"][unitKey]["isOutdoorAirCut"] = dataAC4[12]


    # 冷暖同時供給の有無の判定（冷房暖房ともに「有」であれば「有」とする）

    for iZONE in data["AirConditioningZone"]:

        # 接続している空調機群
        AHU_c_insideload  = data["AirConditioningZone"][iZONE]["AHU_cooling_insideLoad"]
        AHU_c_outdoorload = data["AirConditioningZone"][iZONE]["AHU_cooling_outdoorLoad"]
        AHU_h_insideload  = data["AirConditioningZone"][iZONE]["AHU_heating_insideLoad"]
        AHU_h_outdoorload = data["AirConditioningZone"][iZONE]["AHU_heating_outdoorLoad"]

        # 冷熱源機群
        iREF_c_i = data["AirHandlingSystem"][AHU_c_insideload]["HeatSource_cooling"]
        iREF_c_o = data["AirHandlingSystem"][AHU_c_outdoorload]["HeatSource_cooling"]

        # 温熱源機群
        iREF_h_i = data["AirHandlingSystem"][AHU_h_insideload]["HeatSource_heating"]
        iREF_h_o = data["AirHandlingSystem"][AHU_h_outdoorload]["HeatSource_heating"]

        # 両方とも冷暖同時供給有無が「有」であったら
        if data["HeatsourceSystem"][iREF_c_i]["冷房"]["isSimultaneous_for_ver2"] == "有" and \
            data["HeatsourceSystem"][iREF_c_o]["冷房"]["isSimultaneous_for_ver2"] == "有" and \
            data["HeatsourceSystem"][iREF_h_i]["暖房"]["isSimultaneous_for_ver2"] == "有" and \
            data["HeatsourceSystem"][iREF_h_o]["暖房"]["isSimultaneous_for_ver2"] == "有":

            data["AirConditioningZone"][iZONE]["isSimultaneousSupply"] = "有"

    # isSimultaneous_for_ver2 要素　を削除
    for iREF in data["HeatsourceSystem"]:
        if "冷房" in data["HeatsourceSystem"][iREF]:
            del data["HeatsourceSystem"][iREF]["冷房"]["isSimultaneous_for_ver2"]
        if "暖房" in data["HeatsourceSystem"][iREF]:
            del data["HeatsourceSystem"][iREF]["暖房"]["isSimultaneous_for_ver2"]


    ## 機械換気設備
    if "3-1) 換気室" in wb.sheet_names():
        
        # シートの読み込み
        sheet_V1 = wb.sheet_by_name("3-1) 換気室")
        # 初期化
        roomKey = None

        # 行のループ
        for i in range(10,sheet_V1.nrows):

            # シートから「行」の読み込み
            dataV = sheet_V1.row_values(i)

            # 階と室名が空欄でない場合
            if (dataV[0] != "") and (dataV[1] != ""):

                # 階＋室をkeyとする
                roomKey = str(dataV[0]) + '_' + str(dataV[1])

                data["VentilationRoom"][roomKey] = {
                        "VentilationType": None,
                        "VentilationUnitRef":{
                            str(dataV[6]):{
                                "UnitType": str(dataV[5]),
                                "Info": str(dataV[7])
                            }
                        }
                }

            # 階と室名が空欄であり、かつ、機器名称に入力がある場合
            # 上記 if文 内で定義された roomKey をkeyとして、機器を追加する。
            elif (dataV[0] == "") and (dataV[1] == "") and (dataV[6] != ""):

                data["VentilationRoom"][roomKey]["VentilationUnitRef"][str(dataV[6])]  = {
                    "UnitType": str(dataV[5]),
                    "Info": str(dataV[7])
                }               

    if "3-2) 換気送風機" in wb.sheet_names():
        
        # シートの読み込み
        sheet_V2 = wb.sheet_by_name("3-2) 換気送風機")
        # 初期化
        unitKey = None

        # 行のループ
        for i in range(10,sheet_V2.nrows):

            # シートから「行」の読み込み
            dataV = sheet_V2.row_values(i)

            # 換気機器名称が空欄でない場合
            if (dataV[0] != ""):

                unitKey = str(dataV[0])
                
                data["VentilationUnit"][unitKey] = {
                    "Number": 1,
                    "FanAirVolume": set_default(dataV[1], None, "float"),
                    "MoterRatedPower": set_default(dataV[2], None, "float"),
                    "PowerConsumption": None,
                    "HighEfficiencyMotor": set_default(str(dataV[3]),'無', "str"),
                    "Inverter": set_default(str(dataV[4]),'無', "str"),
                    "AirVolumeControl": set_default(str(dataV[5]),'無', "str"),
                    "VentilationRoomType": None,
                    "AC_CoolingCapacity": None,
                    "AC_RefEfficiency": None,
                    "AC_PumpPower": None,
                    "Info": str(dataV[6])
                }


    if "3-3) 換気空調機" in wb.sheet_names():
        
        # シートの読み込み
        sheet_V3 = wb.sheet_by_name("3-3) 換気空調機")
        # 初期化
        unitKey = None
        unitNum = 0

        # 行のループ
        for i in range(10,sheet_V3.nrows):

            # シートから「行」の読み込み
            dataV = sheet_V3.row_values(i)

            # 換気機器名称が空欄でない場合
            if (dataV[0] != ""):

                unitKey = str(dataV[0])
                unitNum = 0

                if dataV[5] == "空調":
                    
                    data["VentilationUnit"][unitKey] = {
                        "Number": 1,
                        "FanAirVolume": set_default(dataV[6], None, "float"),
                        "MoterRatedPower": set_default(dataV[7], None, "float"),
                        "PowerConsumption": None,
                        "HighEfficiencyMotor": set_default(str(dataV[8]),'無', "str"),
                        "Inverter": set_default(str(dataV[9]),'無', "str"),
                        "AirVolumeControl": set_default(str(dataV[10]),'無', "str"),
                        "VentilationRoomType": set_default(dataV[1],'無', "str"),
                        "AC_CoolingCapacity": set_default(dataV[2], 0, "float"),
                        "AC_RefEfficiency": set_default(dataV[3], 0, "float"),
                        "AC_PumpPower": set_default(dataV[4], 0, "float"),
                        "Info": str(dataV[11])
                    }
                
                else:

                    unitNum += 1

                    data["VentilationUnit"][unitKey + "_fan" + str(unitNum)] = {
                        "Number": 1,
                        "FanAirVolume": set_default(dataV[6], None, "float"),
                        "MoterRatedPower": set_default(dataV[7], None, "float"),
                        "PowerConsumption": None,
                        "HighEfficiencyMotor": set_default(str(dataV[8]),'無', "str"),
                        "Inverter": set_default(str(dataV[9]),'無', "str"),
                        "AirVolumeControl": set_default(str(dataV[10]),'無', "str"),
                        "VentilationRoomType": None,
                        "AC_CoolingCapacity": None,
                        "AC_RefEfficiency": None,
                        "AC_PumpPower": None,
                        "Info": str(dataV[11])
                    }

                    for room_name in data["VentilationRoom"]:
                        if unitKey in data["VentilationRoom"][room_name]["VentilationUnitRef"]:
                            data["VentilationRoom"][room_name]["VentilationUnitRef"][unitKey + "_fan" + str(unitNum)] = {
                                "UnitType": dataV[5],
                                "Info": ""
                            }

            else:


                if dataV[5] == "空調":
                    
                    data["VentilationUnit"][unitKey] = {
                        "Number": 1,
                        "FanAirVolume": set_default(dataV[6], None, "float"),
                        "MoterRatedPower": set_default(dataV[7], None, "float"),
                        "PowerConsumption": None,
                        "HighEfficiencyMotor": set_default(str(dataV[8]),'無', "str"),
                        "Inverter": set_default(str(dataV[9]),'無', "str"),
                        "AirVolumeControl": set_default(str(dataV[10]),'無', "str"),
                        "VentilationRoomType": set_default(dataV[1],'無', "str"),
                        "AC_CoolingCapacity": set_default(dataV[2], 0, "float"),
                        "AC_RefEfficiency": set_default(dataV[3], 0, "float"),
                        "AC_PumpPower": set_default(dataV[4], 0, "float"),
                        "Info": str(dataV[11])
                    }
                
                else:

                    unitNum += 1

                    data["VentilationUnit"][unitKey + "_fan" + str(unitNum)] = {
                        "Number": 1,
                        "FanAirVolume": set_default(dataV[6], None, "float"),
                        "MoterRatedPower": set_default(dataV[7], None, "float"),
                        "PowerConsumption": None,
                        "HighEfficiencyMotor": set_default(str(dataV[8]),'無', "str"),
                        "Inverter": set_default(str(dataV[9]),'無', "str"),
                        "AirVolumeControl": set_default(str(dataV[10]),'無', "str"),
                        "VentilationRoomType": None,
                        "AC_CoolingCapacity": None,
                        "AC_RefEfficiency": None,
                        "AC_PumpPower": None,
                        "Info": str(dataV[11])
                    }

                    for room_name in data["VentilationRoom"]:
                        if unitKey in data["VentilationRoom"][room_name]["VentilationUnitRef"]:
                            data["VentilationRoom"][room_name]["VentilationUnitRef"][unitKey + "_fan" + str(unitNum)] = {
                                "UnitType": dataV[5],
                                "Info": ""
                            }


    if "4) 照明" in wb.sheet_names():
        
        # シートの読み込み
        sheet_L = wb.sheet_by_name("4) 照明")
        # 初期化
        roomKey = None

        # 行のループ
        for i in range(10,sheet_L.nrows):

            # シートから「行」の読み込み
            dataL = sheet_L.row_values(i)

            # 階と室名が空欄でない場合
            if (dataL[0] != "") and (dataL[1] != ""):

                roomKey = str(dataL[0]) + '_' + str(dataL[1])

                data["LightingSystems"][roomKey] = {
                    "roomWidth": set_default(dataL[7],None, "float"),
                    "roomDepth": set_default(dataL[8],None, "float"),
                    "unitHeight": set_default(dataL[6],None, "float"),
                    "roomIndex": set_default(dataL[9],None, "float"),
                    "lightingUnit": {
                        str(dataL[10]): {
                            "RatedPower": float(dataL[11]),
                            "Number": float(dataL[12]),
                            "OccupantSensingCTRL": set_default(str(dataL[13]),schema_data["definitions"]["Lighting_OccupantSensingCTRL"]["default"], "str"),
                            "IlluminanceSensingCTRL": set_default(str(dataL[14]),schema_data["definitions"]["Lighting_IlluminanceSensingCTRL"]["default"], "str"),
                            "TimeScheduleCTRL": set_default(str(dataL[15]),schema_data["definitions"]["Lighting_TimeScheduleCTRL"]["default"], "str"),
                            "InitialIlluminationCorrectionCTRL": set_default(str(dataL[16]),schema_data["definitions"]["Lighting_InitialIlluminationCorrectionCTRL"]["default"], "str")
                        }
                    }
                }

            # 階と室名が空欄であり、かつ、消費電力の入力がある場合
            elif (dataL[0] == "") and (dataL[1] == "") and (dataL[10] != ""):

                data["LightingSystems"][roomKey]["lightingUnit"][str(dataL[10])] = {
                    "RatedPower": float(dataL[11]),
                    "Number": float(dataL[12]),
                    "OccupantSensingCTRL": set_default(str(dataL[13]),schema_data["definitions"]["Lighting_OccupantSensingCTRL"]["default"], "str"),
                    "IlluminanceSensingCTRL": set_default(str(dataL[14]),schema_data["definitions"]["Lighting_IlluminanceSensingCTRL"]["default"], "str"),
                    "TimeScheduleCTRL": set_default(str(dataL[15]),schema_data["definitions"]["Lighting_TimeScheduleCTRL"]["default"], "str"),
                    "InitialIlluminationCorrectionCTRL": set_default(str(dataL[16]),schema_data["definitions"]["Lighting_InitialIlluminationCorrectionCTRL"]["default"], "str")
                }


    if "5-1) 給湯室" in wb.sheet_names():

        # シートの読み込み
        sheet_HW1 = wb.sheet_by_name("5-1) 給湯室")
        # 初期化
        roomKey = None

        # 行のループ
        for i in range(10,sheet_HW1.nrows):

            # シートから「行」の読み込み
            dataHW1 = sheet_HW1.row_values(i)

            # 階と室名が空欄でない場合
            if (dataHW1[0] != "") and (dataHW1[1] != "") :

                # 階＋室をkeyとする
                roomKey = str(dataHW1[0]) + '_' + str(dataHW1[1])

                data["HotwaterRoom"][roomKey] = {
                    "HotwaterSystem":[
                        {
                            "UsageType": None,
                            "SystemName": str(dataHW1[7]),
                            "HotWaterSavingSystem": set_default(str(dataHW1[6]),"無","str"),
                            "Info": str(dataHW1[8])
                        }
                    ]
                }

            elif (dataHW1[5] != "") and (dataHW1[7] != "") :

                data["HotwaterRoom"][roomKey]["HotwaterSystem"].append(
                    {
                        "UsageType": None,
                        "SystemName": str(dataHW1[7]),
                        "HotWaterSavingSystem": set_default(str(dataHW1[6]),"無","str"),
                        "Info": str(dataHW1[8])
                    }
                )

    if "5-2) 給湯機器" in wb.sheet_names():

        # シートの読み込み
        sheet_HW2 = wb.sheet_by_name("5-2) 給湯機器")
        # 初期化
        unitKey = None

        # 行のループ
        for i in range(10,sheet_HW2.nrows):

            # シートから「行」の読み込み
            dataHW2 = sheet_HW2.row_values(i)

            # 給湯システム名称が空欄でない場合
            if (dataHW2[0] != ""):

                # 給湯システム名称をkeyとする
                unitKey = str(dataHW2[0])

                data["HotwaterSupplySystems"][unitKey] = {
                    "HeatSourceUnit":[
                        {
                            "UsageType": None,
                            "HeatSourceType": None,
                            "Number": 1,
                            "RatedCapacity": float(dataHW2[2]),
                            "RatedPowerConsumption": 0,
                            "RatedFuelConsumption": float(dataHW2[2]/dataHW2[3]),
                        }
                    ],
                    "InsulationType": str(dataHW2[4]),
                    "PipeSize": float(dataHW2[5]),
                    "SolarSystemArea": set_default(dataHW2[6], None, "float"),
                    "SolarSystemDirection": set_default(dataHW2[7], None, "float"),
                    "SolarSystemAngle": set_default(dataHW2[8], None, "float"),
                    "Info": str(dataHW2[9])
                }


    if "6) 昇降機" in wb.sheet_names():

        # シートの読み込み
        sheet_EV = wb.sheet_by_name("6) 昇降機")
        # 初期化
        roomKey = None

        # 行のループ
        for i in range(10,sheet_EV.nrows):

            # シートから「行」の読み込み
            dataEV = sheet_EV.row_values(i)

            # 全角括弧と半角括弧の置換
            if str(dataEV[9]) == "VVVF（電力回生なし）":
                dataEV[9] = "VVVF(電力回生なし)"
            elif str(dataEV[9]) == "VVVF（電力回生あり）":
                dataEV[9] = "VVVF(電力回生なし)"
            elif str(dataEV[9]) == "VVVF（電力回生なし、ギアレス）":
                dataEV[9] = "VVVF(電力回生なし)"
            elif str(dataEV[9]) == "VVVF（電力回生あり、ギアレス）":
                dataEV[9] = "VVVF(電力回生なし)"
            
            # 階と室名が空欄でない場合
            if (dataEV[0] != "") and (dataEV[1] != "") :

                # 階＋室をkeyとする
                roomKey = str(dataEV[0]) + '_' + str(dataEV[1])

                data["Elevators"][roomKey] = {
                    "Elevator": [
                        {
                            "ElevatorName": set_default(str(dataEV[4]),"-","str"),
                            "Number": float(dataEV[5]),
                            "LoadLimit": float(dataEV[6]),
                            "Velocity": float(dataEV[7]),
                            "TransportCapacityFactor": set_default(str(dataEV[8]),1,"float"),
                            "ControlType": set_default(str(dataEV[9]),"交流帰還制御","str"),
                            "Info": str(dataEV[8])
                        }
                    ]
                }

            elif (dataEV[4] != ""):

                data["Elevators"][roomKey]["Elevator"].append(
                    {
                        "ElevatorName": set_default(str(dataEV[4]),"-","str"),
                        "Number": float(dataEV[5]),
                        "LoadLimit": float(dataEV[6]),
                        "Velocity": float(dataEV[7]),
                        "TransportCapacityFactor": set_default(str(dataEV[8]),1,"float"),
                        "ControlType": set_default(str(dataEV[9]),"交流帰還制御","str"),
                        "Info": str(dataEV[8])
                    }
                )

    if "7-1) 太陽光発電" in wb.sheet_names():

        # シートの読み込み
        sheet_PV = wb.sheet_by_name("7-1) 太陽光発電")
        # 初期化
        unitKey = None

        # 行のループ
        for i in range(10,sheet_PV.nrows):

            # シートから「行」の読み込み
            dataPV = sheet_PV.row_values(i)

            # 太陽光発電システム名称が空欄でない場合
            if (dataPV[0] != ""):

                data["PhotovoltaicSystems"][dataPV[0]] = {
                    "PowerConditionerEfficiency": set_default(dataPV[1], None, "float"),
                    "CellType": str(dataPV[2]),
                    "ArraySetupType": str(dataPV[3]),
                    "ArrayCapacity": float(dataPV[4]),
                    "Direction": float(dataPV[5]),
                    "Angle": float(dataPV[6]),
                    "Info": str(dataPV[7])
                }

    
    if "7-3) コージェネレーション設備" in wb.sheet_names():

        # シートの読み込み
        sheet_CG = wb.sheet_by_name("7-3) コージェネレーション設備")
        # 初期化
        unitKey = None

        # 行のループ
        for i in range(10,sheet_CG.nrows):

            # シートから「行」の読み込み
            dataCG = sheet_CG.row_values(i)

            # コージェネレーション設備名称が空欄でない場合
            if (dataCG[0] != ""):

                data["CogenerationSystems"][dataCG[0]] = {
                    "RatedCapacity": float(dataCG[1]),
                    "Number": float(dataCG[2]),
                    "PowerGenerationEfficiency_100": float(dataCG[3]),
                    "PowerGenerationEfficiency_75": float(dataCG[4]),
                    "PowerGenerationEfficiency_50": float(dataCG[5]),
                    "HeatGenerationEfficiency_100": float(dataCG[6]),
                    "HeatGenerationEfficiency_75": float(dataCG[7]),
                    "HeatGenerationEfficiency_50": float(dataCG[8]),
                    "HeatRecoveryPriorityCooling": set_default(dataCG[9], None, "str"),
                    "HeatRecoveryPriorityHeating": set_default(dataCG[10], None, "str"),
                    "HeatRecoveryPriorityHotWater": set_default(dataCG[11], None, "str"),
                    "24hourOperation": set_default(dataCG[12],'無', "str"),
                    "CoolingSystem": set_default(dataCG[13], None, "str"),
                    "HeatingSystem": set_default(dataCG[14], None, "str"),
                    "HowWaterSystem": set_default(dataCG[15], None, "str"),
                    "Info": str(dataCG[16])
                }

    # バリデーションの実行
    if validation:
        jsonschema.validate(data, schema_data)

    return data


if __name__ == '__main__':

    print('----- make_inputdata.py -----')

    #-----------------------
    # WEBPRO Ver3シートの例
    #-----------------------
    # directory = "./sample/"
    # case_name = 'Builelib_inputSheet'

    # inputdata = make_jsondata_from_Ver4_sheet(directory + case_name + ".xlsx")

    # # json出力
    # with open(directory + case_name + ".json",'w') as fw:
    #     json.dump(inputdata,fw,indent=4,ensure_ascii=False)

    #-----------------------
    # WEBPRO Ver2シートの例
    #-----------------------
    directory = "./sample/"

    case_name = 'sample01_WEBPRO_inputSheet_for_Ver2.5'

    inputdata = make_jsondata_from_Ver2_sheet(directory + case_name + ".xlsm", True)

    # json出力
    with open(directory + case_name + ".json",'w') as fw:
        json.dump(inputdata,fw,indent=4,ensure_ascii=False)


    #-----------------------
    # WEBPRO Ver2シートの例（連続）
    #-----------------------
    # directory = "./tests/airconditioning/"

    # for id in range(1,44):
    #     if id < 10:
    #         case_name = 'ACtest_Case00' + str(int(id))
    #     else:
    #         case_name = 'ACtest_Case0' + str(int(id))

    #     inputdata = make_jsondata_from_Ver2_sheet(directory + case_name + ".xlsm", True)

    #     # json出力
    #     with open(directory + case_name + ".json",'w') as fw:
    #         json.dump(inputdata,fw,indent=4,ensure_ascii=False)



# %%
