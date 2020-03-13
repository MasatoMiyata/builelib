#%%
import json
import pprint as pp

# 室の形状に応じて定められる係数（仕様書4.4）
def set_roomIndexCoeff(roomIndex):

    if roomIndex == None:
        roomIndexCoeff = 1
    else:
        if roomIndex < 0:
            roomIndexCoeff = 1
        elif roomIndex < 0.75:
            roomIndexCoeff = 0.50
        elif roomIndex < 0.95:
            roomIndexCoeff = 0.60
        elif roomIndex < 1.25:
            roomIndexCoeff = 0.70
        elif roomIndex < 1.75:
            roomIndexCoeff = 0.80
        elif roomIndex < 2.50:
            roomIndexCoeff = 0.90
        elif roomIndex >= 2.50:
            roomIndexCoeff = 1.00
    
    return roomIndexCoeff

# 室の情報を取得する関数
def get_roomSpec(floorName,roomName,roomsdata):
    for room in roomsdata:
        if room["floorName"] == floorName and room["roomName"] == roomName:
            buildingType = room["buildingType"]
            roomType = room["roomType"]
            roomArea = room["roomArea"]
            break
    
    return (buildingType,roomType,roomArea)



#%%
def lighting(inputdata):

    # データベースjsonの読み込み
    with open('./builelib/database/RoomUsageSchedule.json', 'r') as f:
        RoomUsageSchedule = json.load(f)
    with open('./builelib/database/lightingControl.json', 'r') as f:
        lightingCtrl = json.load(f)
    with open('./builelib/database/ROOM_STANDARDVALUE.json', 'r') as f:
        RoomStandardValue = json.load(f)

    # 電気の量1キロワット時を熱量に換算する係数
    fprime = 9760

    # 計算結果モデル
    resultJson = {
        "E_lighting": None,
        "Es_lighting": None,
        "BEI_L": None,
        "lighting":[
        ]
    }

    # 室毎（照明系統毎）にループ
    E_lighting = 0    # 設計一次エネルギー消費量 [GJ]
    Es_lighting = 0   # 基準一次エネルギー消費量 [GJ]


    for isys in inputdata["LightingSystems"]:

        # 建物用途、室用途、室面積の取得
        (buildingType, roomType, roomArea) = get_roomSpec(isys["floorName"],isys["roomName"],inputdata["Rooms"])

        # 基準一次エネルギー消費量 [MJ]
        Es_room = RoomStandardValue[buildingType][roomType]["照明"] * roomArea
        Es_lighting += Es_room  # 出力用に積算

        # 年間照明点灯時間 [時間]
        opeTime = RoomUsageSchedule[buildingType][roomType]["年間照明点灯時間"]

        ## 室の形状に応じて定められる係数（仕様書4.4）
        # 室指数
        if isys["roomIndex"] != None:
            roomIndex = isys["roomIndex"]
        elif isys["roomWidth"] != None and isys["roomDepth"] != None and isys["unitHeight"] != None:
            if isys["roomWidth"] > 0 and isys["roomDepth"] > 0 and isys["unitHeight"] > 0:
                roomIndex = (isys["roomWidth"] * isys["roomDepth"]) / ( (isys["roomWidth"] + isys["roomDepth"]) * isys["unitHeight"] )
            else:
                roomIndex = None
        else:
            roomIndex = None
        
        # 補正係数
        roomIndexCoeff = set_roomIndexCoeff(roomIndex)

        ## 器具毎のループ
        unitPower = 0
        for iunit in isys["lightingUnit"]:
        
            # 室指数による補正
            rmIx = 1

            # 制御による効果
            ctrl = (
                lightingCtrl["OccupantSensingCTRL"][iunit["OccupantSensingCTRL"]] *
                lightingCtrl["IlluminanceSensingCTRL"][iunit["IlluminanceSensingCTRL"]] *
                lightingCtrl["TimeScheduleCTRL"][iunit["TimeScheduleCTRL"]] *
                lightingCtrl["InitialIlluminationCorrectionCTRL"][iunit["InitialIlluminationCorrectionCTRL"]]
            )

            # 照明器具の消費電力（制御込み） [W]
            unitPower += iunit["RatedPower"] * iunit["Number"] * ctrl

        # 設計一次エネルギー消費量 [MJ]
        E_room = unitPower * roomIndexCoeff * opeTime * fprime * 10**(-6)
        E_lighting += E_room  # 出力用に積算


        if roomArea <= 0:
            PrimaryEnergyPerArea = None
        else:
            PrimaryEnergyPerArea = E_room/roomArea

        if Es_lighting <= 0:
            BEI_L = None
        else:
            BEI_L = E_lighting / Es_lighting

        # 計算結果を格納
        resultJson["lighting"].append(
            {
                "floorName": isys["floorName"],
                "roomName": isys["roomName"],
                "buildingType": buildingType,
                "roomType": roomType,
                "roomArea": roomArea,
                "opelationTime": opeTime,
                "roomIndex": roomIndex,
                "roomIndexCoeff": roomIndexCoeff,
                "unitPower": unitPower,
                "PrimaryEnergy": E_room,
                "PrimaryEnergyPerArea": PrimaryEnergyPerArea,
                "StandardEnergy": Es_room
            })

    # 建物全体の計算結果
    resultJson["E_lighting"] = E_lighting
    resultJson["Es_lighting"] = Es_lighting
    resultJson["BEI_L"] = BEI_L

    return resultJson



if __name__ == '__main__':

    print('----- lighting.py -----')
    
    filename = './sample/inputdata.json'

    # テンプレートjsonの読み込み
    with open(filename, 'r') as f:
        inputdata = json.load(f)

    resultJson = lighting(inputdata)
    pp.pprint(resultJson)