import xlrd
import json
import jsonschema
import os

import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import commons as bc

# テンプレートファイルの保存場所
template_directory =  os.path.dirname(os.path.abspath(__file__)) + "/inputdata/"

# 入力値の選択肢一覧
input_options = {
    "有無": ["有","無"],
    "地域区分": ["1","2","3","4","5","6","7","8"],
    "年間日射地域区分": ["A1","A2","A3","A4","A5"],
    "建物用途": ["事務所等","ホテル等","病院等","物販店舗等","学校等","飲食店等","集会所等","工場等","共同住宅"],
    "室用途": {
        "事務所等":["事務室","電子計算機器事務室","会議室","喫茶室","社員食堂","中央監視室","更衣室又は倉庫","廊下","ロビー","便所","喫煙室","厨房","屋内駐車場","機械室","電気室","湯沸室等","食品庫等","印刷室等","廃棄物保管場所等","非主要室"],
        "ホテル等":["客室","客室内の浴室等","終日利用されるフロント","終日利用される事務室","終日利用される廊下","終日利用されるロビー","終日利用される共用部の便所","終日利用される喫煙室","宴会場","会議室","結婚式場","レストラン","ラウンジ","バー","店舗","社員食堂","更衣室又は倉庫","日中のみ利用されるフロント","日中のみ利用される事務室","日中のみ利用される廊下","日中のみ利用されるロビー","日中のみ利用される共用部の便所","日中のみ利用される喫煙室","厨房","屋内駐車場","機械室","電気室","湯沸室等","食品庫等","印刷室等","廃棄物保管場所等","非主要室"],
        "病院等":["病室","浴室等","看護職員室","終日利用される廊下","終日利用されるロビー","終日利用される共用部の便所","終日利用される喫煙室","診察室","待合室","手術室","検査室","集中治療室","解剖室等","レストラン","事務室","更衣室又は倉庫","日中のみ利用される廊下","日中のみ利用されるロビー","日中のみ利用される共用部の便所","日中のみ利用される喫煙室","厨房","屋内駐車場","機械室","電気室","湯沸室等","食品庫等","印刷室等","廃棄物保管場所等","非主要室"],
        "物販店舗等":["大型店の売場","専門店の売場","スーパーマーケットの売場","荷さばき場","事務室","更衣室又は倉庫","ロビー","便所","喫煙室","厨房","屋内駐車場","機械室","電気室","湯沸室等","食品庫等","印刷室等","廃棄物保管場所等","非主要室"],
        "学校等":["小中学校の教室","高等学校の教室","職員室","小中学校又は高等学校の食堂","大学の教室","大学の食堂","事務室","研究室","電子計算機器演習室","実験室","実習室","講堂又は体育館","宿直室","更衣室又は倉庫","廊下","ロビー","便所","喫煙室","厨房","屋内駐車場","機械室","電気室","湯沸室等","食品庫等","印刷室等","廃棄物保管場所等","非主要室"],
        "飲食店等":["レストランの客室","軽食店の客室","喫茶店の客室","バー","フロント","事務室","更衣室又は倉庫","廊下","ロビー","便所","喫煙室","厨房","屋内駐車場","機械室","電気室","湯沸室等","食品庫等","印刷室等","廃棄物保管場所等","非主要室"],
        # "集会所等":["アスレチック場の運動室","アスレチック場のロビー","アスレチック場の便所","アスレチック場の喫煙室","公式競技用スケート場","公式競技用体育館","一般競技用スケート場","一般競技用体育館","レクリエーション用スケート場","レクリエーション用体育館","競技場の客席","競技場のロビー","競技場の便所","競技場の喫煙室","公衆浴場の浴室","公衆浴場の脱衣所","公衆浴場の休憩室","公衆浴場のロビー","公衆浴場の便所","公衆浴場の喫煙室","映画館の客席","映画館のロビー","映画館の便所","映画館の喫煙室","図書館の図書室","図書館のロビー","図書館の便所","図書館の喫煙室","博物館の展示室","博物館のロビー","博物館の便所","博物館の喫煙室","劇場の楽屋","劇場の舞台","劇場の客席","劇場のロビー","劇場の便所","劇場の喫煙室","カラオケボックス","ボーリング場","ぱちんこ屋","競馬場又は競輪場の客席","競馬場又は競輪場の券売場","競馬場又は競輪場の店舗","競馬場又は競輪場のロビー","競馬場又は競輪場の便所","競馬場又は競輪場の喫煙室","社寺の本殿","社寺のロビー","社寺の便所","社寺の喫煙室","厨房","屋内駐車場","機械室","電気室","湯沸室等","食品庫等","印刷室等","廃棄物保管場所等","非主要室"],
        "工場等":["倉庫","屋外駐車場又は駐輪場"],
        "共同住宅":["屋内廊下","ロビー","管理人室","集会室","屋外廊下","屋内駐車場","機械室","電気室","廃棄物保管場所等"]
    },
    "方位": ["北","北東","東","南東","南","南西","西","北西","水平（上）","水平（下）"],
    "外壁の種類": ["日の当たる外壁","日の当たらない外壁","地盤に接する外壁","内壁"],
    "構造種別": ["木造","鉄筋コンクリート造等","鉄骨造","その他"],
    "断熱性能の入力方法": ["熱貫流率を入力","建材構成を入力","断熱材種類を入力"],
    "断熱材番号":["1","2","3","4","21","22","41","42","43","44","45","46","47","48","61","62","63","64","65","66","67","68","69","70","71","72","73","81","82","83","84","85","86","87","88","89","90","101","102","103","104","105","106","107","121","122","123","124","125","126","127","128","129","130","131","132","133","134","141","142","143","144","145","146","161","162","163","181","182","183","184","185","186","187","188","189","190","201","202","203","204","221","222","301","302"],
    "窓性能の入力方法": ["性能値を入力","ガラスの性能を入力","ガラスの種類を入力"],
    "建具の種類": ["樹脂製","木製","金属樹脂複合製","金属木複合製","金属製","樹脂製(単板ガラス)","樹脂製(複層ガラス)","木製(単板ガラス)","木製(複層ガラス)","金属樹脂複合製(単板ガラス)","金属樹脂複合製(複層ガラス)","金属木複合製(単板ガラス)","金属木複合製(複層ガラス)","金属製(単板ガラス)","金属製(複層ガラス)"],
    "ガラスの層数": ["複層","単層"],
    "ガラスの種類": ["3WgG06","3WgG07","3WgG08","3WgG09","3WgG10","3WgG11","3WgG12","3WgG13","3WgG14","3WgG15","3WgG16","3WsG06","3WsG07","3WsG08","3WsG09","3WsG10","3WsG11","3WsG12","3WsG13","3WsG14","3WsG15","3WsG16","3WgA06","3WgA07","3WgA08","3WgA09","3WgA10","3WgA11","3WgA12","3WgA13","3WgA14","3WgA15","3WgA16","3WsA06","3WsA07","3WsA08","3WsA09","3WsA10","3WsA11","3WsA12","3WsA13","3WsA14","3WsA15","3WsA16","3LgG06","3LgG07","3LgG08","3LgG09","3LgG10","3LgG11","3LgG12","3LgG13","3LgG14","3LgG15","3LgG16","3LsG06","3LsG07","3LsG08","3LsG09","3LsG10","3LsG11","3LsG12","3LsG13","3LsG14","3LsG15","3LsG16","3LgA06","3LgA07","3LgA08","3LgA09","3LgA10","3LgA11","3LgA12","3LgA13","3LgA14","3LgA15","3LgA16","3LsA06","3LsA07","3LsA08","3LsA09","3LsA10","3LsA11","3LsA12","3LsA13","3LsA14","3LsA15","3LsA16","3FA06","3FA07","3FA08","3FA09","3FA10","3FA11","3FA12","3FA13","3FA14","3FA15","3FA16","2LgG06","2LgG07","2LgG08","2LgG09","2LgG10","2LgG11","2LgG12","2LgG13","2LgG14","2LgG15","2LgG16","2LsG06","2LsG07","2LsG08","2LsG09","2LsG10","2LsG11","2LsG12","2LsG13","2LsG14","2LsG15","2LsG16","2LgA06","2LgA07","2LgA08","2LgA09","2LgA10","2LgA11","2LgA12","2LgA13","2LgA14","2LgA15","2LgA16","2LsA06","2LsA07","2LsA08","2LsA09","2LsA10","2LsA11","2LsA12","2LsA13","2LsA14","2LsA15","2LsA16","2FA06","2FA07","2FA08","2FA09","2FA10","2FA11","2FA12","2FA13","2FA14","2FA15","2FA16","T","S"],
    "冷暖同時供給の有無": ["無","有","有（室負荷）","有（外気負荷）"],
    "蓄熱の種類": ["水蓄熱(混合型)","水蓄熱(成層型)","氷蓄熱"],
    "流量制御方式": ["無","定流量制御","回転数制御"],               
    "空調機群の構成機器の種類": ["空調機","FCU","送風機","室内機","全熱交ユニット","放熱器","天井放射冷暖房パネル"],
    "送風機の種類": ["給気","還気","外気","排気","循環","ポンプ"],
    "風量制御方式": ["無","定風量制御","回転数制御"],
    "換気方式": ["一種換気","二種換気","三種換気"],
    "換気送風機の種類": ["給気","排気","空調","循環"],
    "換気送風量制御": ["無","CO濃度制御","温度制御"],
    "換気代替空調対象室の用途": ["電気室","機械室","エレベータ機械室","その他"],
    "照明在室検知制御": ["無","下限調光方式","点滅方式","減光方式"],
    "照明明るさ検知制御": ["無","調光方式","調光方式BL","調光方式W15","調光方式W15BL","調光方式W20","調光方式W20BL","調光方式W25","調光方式W25BL","点滅方式"],
    "照明タイムスケジュール制御": ["無","減光方式","点滅方式"],
    "照明初期照度補正機能": ["無","タイマ方式(LED)","タイマ方式(蛍光灯)","センサ方式(LED)","センサ方式(蛍光灯)"],
    "給湯負荷": ["便所","浴室","厨房","その他"],
    "節湯器具": ["自動給湯栓","節湯B1","無"],
    "給湯熱源の用途": ["給湯負荷用","配管保温用","貯湯槽保温用","その他"],
    "給湯熱源機種": ["ガス給湯機","ガス給湯暖房機","ボイラ","石油給湯機(給湯単機能)","石油給湯機(給湯機付ふろがま)","家庭用ヒートポンプ給湯機","業務用ヒートポンプ給湯機","貯湯式電気温水器","電気瞬間湯沸器","真空式温水発生機","無圧式温水発生機","地域熱供給"],
    "配管保温仕様": ["保温仕様1","保温仕様2","保温仕様3","裸管"],
    "速度制御方式": ["VVVF(電力回生なし)","VVVF(電力回生あり)","VVVF(電力回生なし、ギアレス)","VVVF(電力回生あり、ギアレス)","交流帰還制御"],
    "太陽電池の種類": ["結晶系","結晶系以外"],
    "アレイ設置方式": ["架台設置形","屋根置き形","その他"],
    "排熱利用優先順位": ["1番目","2番目","3番目"],

}

# 検証結果メッセージ （global変数）
validation = {
    "error": [],
    "warning": []
}

def check_duplicates(seq):
    """
    リストの要素の重複をチェックする関数
    """
    return len(seq) != len(set(seq))


def check_value(input_data, item_name, required=False, default=None, data_type=None, options=None, lower_limit=None, upper_limit=None):
    """
    データのチェックをし、値を返す関数 
        引数：入力値、入力値の名称、必須か否か、デフォルト値、型、選択肢、下限値、上限値
        不整合が生じた場合、グローバル変数 validation にメッセージを格納する。
    """

    # 必須項目のチェック
    if required and (input_data == "") and (default == None):
        
        validation["error"].append( item_name + "が入力されていません。必須項目です。")
    
    else:
        
        # 空欄チェック
        if (default != None) and (input_data == ""):
            input_data = default
            if type(default) is str:
                if input_data != "無":
                    validation["warning"].append( item_name + "が空欄であったため、デフォルト値 " + default +  " を使用しました。")
            else:
                validation["warning"].append( item_name + "が空欄であったため、デフォルト値 " + str(default) +  " を使用しました。")

        # 型チェック
        if data_type != None and (input_data != ""):
            if data_type == "文字列":
                input_data = str(input_data)
            elif data_type == "数値":
                try:
                    input_data = float(input_data)
                except:
                    input_data = None
                    validation["error"].append( item_name + "の入力が不正です。数値を入力してください。")
            elif data_type == "文字列か数値":
                if type(input_data) is not float:
                    input_data = str(input_data)
                else:
                    input_data = float(input_data)
            else:
                raise Exception('データ型の指定が不正です')

        # 選択肢チェック
        if options != None:
            if (input_data != "") and type(input_data) is str:
                if input_data not in options:
                    validation["error"].append( item_name + "の入力が不正です。選択肢から正しく選択（もしくは転記）してください。")

        # 閾値チェック（下限）
        if lower_limit != None:
            if (input_data != "") and type(input_data) is str:
                if len(input_data) < float(lower_limit):
                    validation["error"].append( item_name + "の文字数が下限(" + str(lower_limit) + "文字）を下回っています。")
            elif type(input_data) is float:
                if input_data <= float(lower_limit):
                    validation["error"].append( item_name + "の値が下限(" + str(lower_limit) + "）を下回っています。")

        # 閾値チェック（上限）
        if upper_limit != None:
            if (input_data != "") and type(input_data) is str:
                if len(input_data) > float(upper_limit):
                    validation["error"].append( item_name + "の文字数が上限(" + str(upper_limit) + "文字）を超えています。")
            elif type(input_data) is float:
                if input_data > float(upper_limit):
                    validation["error"].append( item_name + "の値が上限(" + str(upper_limit) + "）を超えています。")

    return input_data


def set_default(value,default,datatype):
    """
    型をチェックし、デフォルト値を設定する関数
    → 期待された型と異なれば、"error"を返す。
    この関数は将来的には削除する。check_value に移行する。
    """
    if value == "":

        out = default

    else:

        if datatype == "str":
            try:
                out = str(value)
            except:
                out = "type error string"

        elif datatype == "float":
            try:
                out = float(value)
            except:
                out = "type error float"

        elif datatype == "int":
            try:
                out = int(value)
            except:
                out = "type error int"

        elif datatype == "float_or_str":
            try:
                out = float(value)
            except:
                out = str(value)

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


def make_jsondata_from_Ver4_sheet(inputfileName):
    """
    WEBPRO Ver4 用の入力シートから 入力データ（辞書型）を生成するプログラム
    """

    # 入力シートの読み込み
    wb = xlrd.open_workbook(inputfileName)

    # テンプレートjsonの読み込み
    with open( template_directory + 'template.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    # スキーマの読み込み
    with open( template_directory + 'webproJsonSchema.json', 'r', encoding='utf-8') as f:
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
                                "Heatsource_sub_RatedPowerConsumption": set_default(dataAC2[13], 0, "float"),
                                "PrimaryPumpPowerConsumption": set_default(dataAC2[14], 0, "float"),
                                "PrimaryPumpContolType": set_default(dataAC2[15], "無", "str"),
                                "CoolingTowerCapacity": set_default(dataAC2[16], 0, "float"),
                                "CoolingTowerFanPowerConsumption": set_default(dataAC2[17], 0, "float"),
                                "CoolingTowerPumpPowerConsumption": set_default(dataAC2[18], 0, "float"),
                                "CoolingTowerContolType": set_default(dataAC2[19], "無", "str"),
                                "Info": str(dataAC2[20])
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
                        "Heatsource_sub_RatedPowerConsumption": set_default(dataAC2[13], 0, "float"),
                        "PrimaryPumpPowerConsumption": set_default(dataAC2[14], 0, "float"),
                        "PrimaryPumpContolType": set_default(dataAC2[15], "無", "str"),
                        "CoolingTowerCapacity": set_default(dataAC2[16], 0, "float"),
                        "CoolingTowerFanPowerConsumption": set_default(dataAC2[17], 0, "float"),
                        "CoolingTowerPumpPowerConsumption": set_default(dataAC2[18], 0, "float"),
                        "CoolingTowerContolType": set_default(dataAC2[19], "無", "str"),
                        "Info": str(dataAC2[20])
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
                            "Heatsource_sub_RatedPowerConsumption": set_default(dataAC2[13], 0, "float"),
                            "PrimaryPumpPowerConsumption": set_default(dataAC2[14], 0, "float"),
                            "PrimaryPumpContolType": set_default(dataAC2[15], "無", "str"),
                            "CoolingTowerCapacity": set_default(dataAC2[16], 0, "float"),
                            "CoolingTowerFanPowerConsumption": set_default(dataAC2[17], 0, "float"),
                            "CoolingTowerPumpPowerConsumption": set_default(dataAC2[18], 0, "float"),
                            "CoolingTowerContolType": set_default(dataAC2[19], "無", "str"),
                            "Info": str(dataAC2[20])
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
                        "TemperatureDifference": float(dataAC3[2]),
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
                    "TemperatureDifference": float(dataAC3[2]),
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
    # if validation:
    #     jsonschema.validate(data, schema_data)

    return data, validation


def make_jsondata_from_Ver2_sheet(inputfileName):
    """
    WEBPRO Ver2 用の入力シートから 入力データ（辞書型）を生成するプログラム
    """

    # 入力シートの読み込み
    wb = xlrd.open_workbook(inputfileName)

    # テンプレートjsonの読み込み
    with open( template_directory + 'template.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    

    if "SP-2) 熱源特性" in wb.sheet_names():

        data["SpecialInputData"]["heatsource_performance"] = {}

        # シートの読み込み
        sheet_SP2 = wb.sheet_by_name("SP-2) 熱源特性")

        ref_name = ""
        operation_mode = ""
        curve_type = ""

        # 行のループ（nrowsが10より小さいと空行列になる）
        for i in range(10,sheet_SP2.nrows):

            # シートから「行」の読み込み
            dataSP2 = sheet_SP2.row_values(i)

            # 「熱源機種名称」が空白でなければ。
            if (dataSP2[0] != ""):

                ref_name = dataSP2[0]  # 熱源機種名の更新

                # データがなければ作成
                if ref_name not in data["SpecialInputData"]["heatsource_performance"]:

                    data["SpecialInputData"]["heatsource_performance"][ref_name] = {
                        "ID": "任意評定",
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

            # 「冷房／暖房」が空白でなければ。
            if (dataSP2[1] != ""):

                if dataSP2[1] == "冷房":
                    operation_mode = "冷房時の特性"
                elif dataSP2[1] == "暖房":
                    operation_mode = "暖房時の特性"
                else:
                    raise Exception("予期せぬ選択肢です。")

                data["SpecialInputData"]["heatsource_performance"][ref_name][operation_mode]["燃料種類"] = dataSP2[2]
                data["SpecialInputData"]["heatsource_performance"][ref_name][operation_mode]["熱源種類"] = dataSP2[3]

            # 「特性の種類」が空白でなければ。
            if (dataSP2[4] != ""):

                curve_type = dataSP2[4]

                data["SpecialInputData"]["heatsource_performance"][ref_name][operation_mode][curve_type]=[
                    {
                        "下限": set_default(dataSP2[5], 0, "float"),
                        "上限": set_default(dataSP2[6], 0, "float"),
                        "冷却水温度下限": set_default(dataSP2[7], None, "float"),
                        "冷却水温度上限": set_default(dataSP2[8], None, "float"),
                        "係数": {
                            "a4": set_default(dataSP2[9], 0, "float"),
                            "a3": set_default(dataSP2[10], 0, "float"),
                            "a2": set_default(dataSP2[11], 0, "float"),
                            "a1": set_default(dataSP2[12], 0, "float"),
                            "a0": set_default(dataSP2[13], 0, "float")
                        },
                        "基整促係数": set_default(dataSP2[14], 1.0, "float")
                    }
                ]

            else:
                
                data["SpecialInputData"]["heatsource_performance"][ref_name][operation_mode][curve_type].append(
                    {
                        "下限": set_default(dataSP2[5], 0, "float"),
                        "上限": set_default(dataSP2[6], 0, "float"),
                        "冷却水温度下限": set_default(dataSP2[7], None, "float"),
                        "冷却水温度上限": set_default(dataSP2[8], None, "float"),
                        "係数": {
                            "a4": set_default(dataSP2[9], 0, "float"),
                            "a3": set_default(dataSP2[10], 0, "float"),
                            "a2": set_default(dataSP2[11], 0, "float"),
                            "a1": set_default(dataSP2[12], 0, "float"),
                            "a0": set_default(dataSP2[13], 0, "float")
                        },
                        "基整促係数": set_default(dataSP2[14], 1.0, "float")
                    }
                )


    # %%
    # 様式0の読み込み
    if "0) 基本情報" in wb.sheet_names():

        try:

            # シートの読み込み
            sheet_BL = wb.sheet_by_name("0) 基本情報")

            # BL-1	建築物の名称
            data["Building"]["Name"] = \
                check_value(sheet_BL.cell(8, 2).value, "様式0.基本情報 9行目:「③建築物の名称」", True, None, "文字列", None, 0, 100)

            # BL-2	都道府県 (選択)
            data["Building"]["BuildingAddress"]["Prefecture"] = \
                check_value(str(sheet_BL.cell(9, 3).value), "様式0.基本情報 10行目:「④都道府県」", False, None, "文字列", None, 0, 100)
            
            # BL-3	建築物所在地 市区町村 (選択)
            if sheet_BL.ncols <= 5:
                data["Building"]["BuildingAddress"]["City"] = None
            else:
                data["Building"]["BuildingAddress"]["City"] = \
                    check_value(str(sheet_BL.cell(9, 5).value), "様式0.基本情報 10行目:「④市区町村」", False, None, "文字列", None, 0, 100)
            
            # BL-4	丁目、番地等
            data["Building"]["BuildingAddress"]["Address"] = \
                check_value(str(sheet_BL.cell(10, 2).value), "様式0.基本情報 11行目:「④所在地（詳細）」", False, None, "文字列", None, 0, 100)
            
            # BL-5	地域の区分	(自動)
            area_num = sheet_BL.cell(11, 2).value
            if type(area_num) is str and (area_num.endswith("地域")):  # 
                area_num = area_num.replace("地域","")
            elif type(area_num) is not str:
                area_num = str(int(area_num))

            data["Building"]["Region"] = \
                check_value(area_num, "様式0.基本情報 12行目:「⑤地域の区分」", True, None, "文字列", input_options["地域区分"], None, None)

            # BL-6	年間日射地域区分 (自動)
            data["Building"]["AnnualSolarRegion"] = \
                check_value(str(sheet_BL.cell(17, 2).value), "様式0.基本情報 18行目:「⑪年間日射地域区分」", True, "A3", "文字列", input_options["年間日射地域区分"], None, None)
            
            # BL-7	延べ面積  [㎡]	(数値)
            data["Building"]["BuildingFloorArea"] = \
                check_value(str(sheet_BL.cell(16, 2).value), "様式0.基本情報 17行目:「⑩延べ面積」", True, None, "数値", None, 0, None)

            # BL-8	「他人から供給された熱」	冷熱	(数値)
            data["Building"]["Coefficient_DHC"]["Cooling"] = \
                check_value(str(sheet_BL.cell(18, 2).value), "様式0.基本情報 19行目:「⑫他人から供給された熱（冷熱）の一次エネ換算係数」", None, None, "数値", None, 0, None)
                        
            # BL-9	の一次エネルギー換算係数	温熱	(数値)
            data["Building"]["Coefficient_DHC"]["Heating"] = \
                check_value(str(sheet_BL.cell(19, 2).value), "様式0.基本情報 20行目:「⑬他人から供給された熱（温熱）の一次エネ換算係数」", None, None, "数値", None, 0, None)

        except:

            validation["error"].append("様式0.基本情報: 読み込み時に予期せぬエラーが発生しました。")


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

                if str(dataBL[3]) == "ゴミ置場等":
                    roomType = "廃棄物保管場所等"
                else:
                    roomType = str(dataBL[3])

                # ゾーンはないと想定。
                data["Rooms"][roomKey] = {
                        "buildingType": str(dataBL[2]),               
                        "roomType": roomType,
                        "floorHeight": float(dataBL[5]),
                        "ceilingHeight": float(dataBL[6]),
                        "roomArea": float(dataBL[4]),
                        "zone": None,
                        "modelBuildingType": str(dataBL[11]),  
                        "buildingGroup": None,
                        "Info": str(dataBL[12])
                }

        #------------------
        # validation
        #------------------





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

                if (dataBE1[2] == ""):  # 方位が空白である場合。

                    if (dataBE1[5] != ""): # もし方位が空白で外壁名称に入力があったらエラー 
                        raise Exception("外壁名称が入力されている場合は方位の入力が必要です。")

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
                    
                    data["EnvelopeSet"][roomKey]["WallList"][-1]["WindowList"].append(
                        {
                            "WindowID": set_default(str(dataBE1[7]),"無","str"),
                            "WindowNumber": set_default(str(dataBE1[8]),None, "float"),
                            "isBlind": set_default(str(dataBE1[9]),"無","str"),
                            "EavesID": EavesID,
                            "Info": set_default(str(dataBE1[10]),"無","str"),
                        }
                    )

                else: # 方位が空白ではない場合。

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

                        if dataBE2[4].replace(' ', '') == "吹付け硬質ウレタンフォームＡ種1":
                            dataBE2[4] = "吹付け硬質ウレタンフォームA種1"
                        elif dataBE2[4].replace(' ', '') == "吹付け硬質ウレタンフォームＡ種3":
                            dataBE2[4] = "吹付け硬質ウレタンフォームA種3"

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

                            if dataBE2[4].replace(' ', '') == "吹付け硬質ウレタンフォームＡ種1":
                                dataBE2[4] = "吹付け硬質ウレタンフォームA種1"
                            elif dataBE2[4].replace(' ', '') == "吹付け硬質ウレタンフォームＡ種3":
                                dataBE2[4] = "吹付け硬質ウレタンフォームA種3"
                                
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
                    elif dataBE3[3] == "樹脂製(複層ガラス)" or dataBE3[3] == "樹脂":
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
                    elif dataBE3[3] == "金属樹脂複合製(複層ガラス)" or dataBE3[3] == "アルミ樹脂複合":
                        frameType = "金属樹脂複合製"
                        layerType = "複層"
                    elif dataBE3[3] == "金属製(単板ガラス)":
                        frameType = "金属製"
                        layerType = "単層"
                    elif dataBE3[3] == "金属製(複層ガラス)" or dataBE3[3] == "アルミ":
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
                    elif dataBE3[3] == "樹脂製(複層ガラス)" or dataBE3[3] == "樹脂":
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
                    elif dataBE3[3] == "金属樹脂複合製(複層ガラス)" or dataBE3[3] == "アルミ樹脂複合":
                        frameType = "金属樹脂複合製"
                        layerType = "複層"
                    elif dataBE3[3] == "金属製(単板ガラス)":
                        frameType = "金属製"
                        layerType = "単層"
                    elif dataBE3[3] == "金属製(複層ガラス)" or dataBE3[3] == "アルミ":
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
        
        # データベースファイルの保存場所
        database_directory =  os.path.dirname(os.path.abspath(__file__)) + "/database/"
        ## 熱源機器特性
        with open(database_directory + "HeatSourcePerformance.json", 'r', encoding='utf-8') as f:
            HeatSourcePerformance = json.load(f)

        # SP-2で作成した機種を追加
        if "SpecialInputData" in data:
            if "heatsource_performance" in data["SpecialInputData"]:
                HeatSourcePerformance.update(data["SpecialInputData"]["heatsource_performance"])

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

                    if HeatSourcePerformance[str(dataAC2[5])]["冷房時の特性"]["燃料種類"] == "電力":    # 燃料種類が電力であれば
                        HeatsourceRatedPowerConsumption = set_default(dataAC2[10], 0, "float")
                        Heatsource_sub_RatedPowerConsumption = set_default(dataAC2[11], 0, "float")
                        HeatsourceRatedFuelConsumption  = 0
                    else:
                        HeatsourceRatedPowerConsumption = 0
                        Heatsource_sub_RatedPowerConsumption = set_default(dataAC2[11], 0, "float")
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
                                    "Heatsource_sub_RatedPowerConsumption": Heatsource_sub_RatedPowerConsumption,
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

                    if HeatSourcePerformance[str(dataAC2[5])]["暖房時の特性"]["燃料種類"] == "電力":    # 燃料種類が電力であれば
                        HeatsourceRatedPowerConsumption = set_default(dataAC2[20], 0, "float")
                        Heatsource_sub_RatedPowerConsumption = set_default(dataAC2[21], 0, "float")
                        HeatsourceRatedFuelConsumption  = 0
                    else:
                        HeatsourceRatedPowerConsumption = 0
                        Heatsource_sub_RatedPowerConsumption = set_default(dataAC2[21], 0, "float")
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
                                        "Heatsource_sub_RatedPowerConsumption": Heatsource_sub_RatedPowerConsumption,
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
                                        "Heatsource_sub_RatedPowerConsumption": Heatsource_sub_RatedPowerConsumption,
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
    
                    if HeatSourcePerformance[str(dataAC2[5])]["冷房時の特性"]["燃料種類"] == "電力":    # 燃料種類が電力であれば
                        HeatsourceRatedPowerConsumption = set_default(dataAC2[10], 0, "float")
                        Heatsource_sub_RatedPowerConsumption = set_default(dataAC2[11], 0, "float")
                        HeatsourceRatedFuelConsumption  = 0
                    else:
                        HeatsourceRatedPowerConsumption = 0
                        Heatsource_sub_RatedPowerConsumption = set_default(dataAC2[11], 0, "float")
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
                            "Heatsource_sub_RatedPowerConsumption": Heatsource_sub_RatedPowerConsumption,
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
                    
                    if HeatSourcePerformance[str(dataAC2[5])]["暖房時の特性"]["燃料種類"] == "電力":    # 燃料種類が電力であれば
                        HeatsourceRatedPowerConsumption = set_default(dataAC2[20], 0, "float")
                        Heatsource_sub_RatedPowerConsumption = set_default(dataAC2[21], 0, "float")
                        HeatsourceRatedFuelConsumption  = 0
                    else:
                        HeatsourceRatedPowerConsumption = 0
                        Heatsource_sub_RatedPowerConsumption = set_default(dataAC2[21], 0, "float")
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
                            "Heatsource_sub_RatedPowerConsumption": Heatsource_sub_RatedPowerConsumption,
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

                    if HeatSourcePerformance[str(dataAC2[5])]["冷房時の特性"]["燃料種類"] == "電力":    # 燃料種類が電力であれば
                        HeatsourceRatedPowerConsumption = set_default(dataAC2[10], 0, "float")
                        Heatsource_sub_RatedPowerConsumption = set_default(dataAC2[11], 0, "float")
                        HeatsourceRatedFuelConsumption  = 0
                    else:
                        HeatsourceRatedPowerConsumption = 0
                        Heatsource_sub_RatedPowerConsumption = set_default(dataAC2[11], 0, "float")
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
                                        "Heatsource_sub_RatedPowerConsumption": Heatsource_sub_RatedPowerConsumption,
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
                                        "Heatsource_sub_RatedPowerConsumption": Heatsource_sub_RatedPowerConsumption,
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

                    if HeatSourcePerformance[str(dataAC2[5])]["暖房時の特性"]["燃料種類"] == "電力":    # 燃料種類が電力であれば
                        HeatsourceRatedPowerConsumption = set_default(dataAC2[20], 0, "float")
                        Heatsource_sub_RatedPowerConsumption = set_default(dataAC2[21], 0, "float")
                        HeatsourceRatedFuelConsumption  = 0
                    else:
                        HeatsourceRatedPowerConsumption = 0
                        Heatsource_sub_RatedPowerConsumption = set_default(dataAC2[21], 0, "float")
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
                                        "Heatsource_sub_RatedPowerConsumption": Heatsource_sub_RatedPowerConsumption,
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
                                        "Heatsource_sub_RatedPowerConsumption": Heatsource_sub_RatedPowerConsumption,
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
                            "TemperatureDifference": float(dataAC3[2]),
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
                                "TemperatureDifference": float(dataAC3[3]),
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
                                "TemperatureDifference": float(dataAC3[3]),
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

        # 外調系統だけ冷暖同時であれば（暫定措置）
        elif data["HeatsourceSystem"][iREF_c_i]["冷房"]["isSimultaneous_for_ver2"] == "無" and \
            data["HeatsourceSystem"][iREF_c_o]["冷房"]["isSimultaneous_for_ver2"] == "有" and \
            data["HeatsourceSystem"][iREF_h_i]["暖房"]["isSimultaneous_for_ver2"] == "無" and \
            data["HeatsourceSystem"][iREF_h_o]["暖房"]["isSimultaneous_for_ver2"] == "有":

            data["AirConditioningZone"][iZONE]["isSimultaneousSupply"] = "有（外気負荷）"

        # 室負荷系統だけ冷暖同時であれば（暫定措置）
        elif data["HeatsourceSystem"][iREF_c_i]["冷房"]["isSimultaneous_for_ver2"] == "有" and \
            data["HeatsourceSystem"][iREF_c_o]["冷房"]["isSimultaneous_for_ver2"] == "無" and \
            data["HeatsourceSystem"][iREF_h_i]["暖房"]["isSimultaneous_for_ver2"] == "有" and \
            data["HeatsourceSystem"][iREF_h_o]["暖房"]["isSimultaneous_for_ver2"] == "無":

            data["AirConditioningZone"][iZONE]["isSimultaneousSupply"] = "有（室負荷）"


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
                        "VentilationRoomType": set_default(dataV[1],'無', "float_or_str"),
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
                        "VentilationRoomType": set_default(dataV[1],'無', "float_or_str"),
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

                if roomKey in data["LightingSystems"]:

                    validation["error"].append( "様式4.照明:「①照明対象室」に重複があります（"+ str(i+1) +"行目「"+ roomKey +"」）。") 

                else:

                    unit_name = check_value(dataL[10], "様式4.照明 "+ str(i+1) +"行目:「④機器名称」", True, "器具A", "文字列", None, None, None)

                    data["LightingSystems"][roomKey] = {
                        "roomWidth": 
                            check_value(dataL[7], "様式4.照明 "+ str(i+1) +"行目:「②室の間口」", False, None, "数値", None, 0, None),
                        "roomDepth":
                            check_value(dataL[8], "様式4.照明 "+ str(i+1) +"行目:「③室の奥行」", False, None, "数値", None, 0, None),
                        "unitHeight":
                            check_value(dataL[6], "様式4.照明 "+ str(i+1) +"行目:「①天井高」", False, None, "数値", None, 0, None),
                        "roomIndex":
                            check_value(dataL[9], "様式4.照明 "+ str(i+1) +"行目:「④室指数」", False, None, "数値", None, 0, None),
                        "lightingUnit": {
                            unit_name: {
                                "RatedPower":
                                    check_value(dataL[11], "様式4.照明 "+ str(i+1) +"行目:「⑥定格消費電力」", True, None, "数値", None, 0, None),
                                "Number":
                                    check_value(dataL[12], "様式4.照明 "+ str(i+1) +"行目:「⑦台数」", True, None, "数値", None, 0, None),
                                "OccupantSensingCTRL":
                                    check_value(dataL[13], "様式4.照明 "+ str(i+1) +"行目:「⑧在室検知制御」", False, "無", "文字列か数値", input_options["照明在室検知制御"], None, None),
                                "IlluminanceSensingCTRL":
                                    check_value(dataL[14], "様式4.照明 "+ str(i+1) +"行目:「⑨明るさ検知制御」", False, "無", "文字列か数値", input_options["照明明るさ検知制御"], None, None),
                                "TimeScheduleCTRL":
                                    check_value(dataL[15], "様式4.照明 "+ str(i+1) +"行目:「⑨明るさ検知制御」", False, "無", "文字列か数値", input_options["照明タイムスケジュール制御"], None, None),
                                "InitialIlluminationCorrectionCTRL":
                                    check_value(dataL[16], "様式4.照明 "+ str(i+1) +"行目:「⑨明るさ検知制御」", False, "無", "文字列か数値", input_options["照明初期照度補正機能"], None, None),
                            }
                        }
                    }

            # 階と室名が空欄であり、かつ、消費電力の入力がある場合
            elif (dataL[0] == "") and (dataL[1] == "") and (dataL[10] != ""):

                unit_name = check_value(dataL[10], "様式4.照明 "+ str(i+1) +"行目:「④機器名称」", True, "器具A", "文字列", None, None, None)

                if unit_name in data["LightingSystems"][roomKey]["lightingUnit"]:

                    validation["error"].append( "様式4.照明:「⑤機器名称」に重複があります（"+ str(i+1) +"行目「"+ unit_name +"」）。")

                else:

                    data["LightingSystems"][roomKey]["lightingUnit"][unit_name] = {
                        "RatedPower":
                            check_value(dataL[11], "様式4.照明 "+ str(i+1) +"行目:「⑥定格消費電力」", True, None, "数値", None, 0, None),
                        "Number":
                            check_value(dataL[12], "様式4.照明 "+ str(i+1) +"行目:「⑦台数」", True, None, "数値", None, 0, None),
                        "OccupantSensingCTRL":
                            check_value(dataL[13], "様式4.照明 "+ str(i+1) +"行目:「⑧在室検知制御」", False, "無", "文字列か数値", input_options["照明在室検知制御"], None, None),
                        "IlluminanceSensingCTRL":
                            check_value(dataL[14], "様式4.照明 "+ str(i+1) +"行目:「⑨明るさ検知制御」", False, "無", "文字列か数値", input_options["照明明るさ検知制御"], None, None),
                        "TimeScheduleCTRL":
                            check_value(dataL[15], "様式4.照明 "+ str(i+1) +"行目:「⑨明るさ検知制御」", False, "無", "文字列か数値", input_options["照明タイムスケジュール制御"], None, None),
                        "InitialIlluminationCorrectionCTRL":
                            check_value(dataL[16], "様式4.照明 "+ str(i+1) +"行目:「⑨明るさ検知制御」", False, "無", "文字列か数値", input_options["照明初期照度補正機能"], None, None),
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

                if roomKey in data["HotwaterRoom"]:

                    validation["error"].append( "様式5-1.給湯対象室:「①給湯対象室」に重複があります（"+ str(i+1) +"行目「"+ roomKey +"」）。") 

                else:

                    data["HotwaterRoom"][roomKey] = {
                        "HotwaterSystem":[
                            {
                                "UsageType": None,
                                "SystemName":
                                    check_value(dataHW1[7], "様式5-1.給湯対象室 "+ str(i+1) +"行目:「④給湯機器名称」", True, None, "文字列", None, None, None),
                                "HotWaterSavingSystem":
                                    check_value(dataHW1[6], "様式5-1.給湯対象室 "+ str(i+1) +"行目:「③節湯器具」", True, "無", "文字列", input_options["節湯器具"], None, None),
                                "Info":
                                    check_value(dataHW1[8], "様式5-1.給湯対象室 "+ str(i+1) +"行目:「⑤備考」", False, None, "文字列", None, 0, None),
                            }
                        ]
                    }

            elif (dataHW1[6] != "") and (dataHW1[7] != "") :

                data["HotwaterRoom"][roomKey]["HotwaterSystem"].append(
                    {
                        "UsageType": None,
                        "SystemName":
                            check_value(dataHW1[7], "様式5-1.給湯対象室 "+ str(i+1) +"行目:「④給湯機器名称」", True, None, "文字列", None, None, None),
                        "HotWaterSavingSystem":
                            check_value(dataHW1[6], "様式5-1.給湯対象室 "+ str(i+1) +"行目:「③節湯器具」", True, "無", "文字列", input_options["節湯器具"], None, None),
                        "Info":
                            check_value(dataHW1[8], "様式5-1.給湯対象室 "+ str(i+1) +"行目:「⑤備考」", False, None, "文字列", None, 0, None),
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

                if unitKey in data["HotwaterSupplySystems"]:

                    validation["error"].append( "様式5-2.給湯機器:「①給湯機器名称」に重複があります（"+ str(i+1) +"行目「"+ unitKey +"」）。") 

                else:

                    if str(dataHW2[1]) == "電力" or str(dataHW2[1]) == "電気":
                        HeatSourceType = "電気瞬間湯沸器"
                    elif str(dataHW2[1]) == "都市ガス":
                        HeatSourceType = "ガス給湯機"
                    elif str(dataHW2[1]) == "液化石油ガス":
                        HeatSourceType = "ガス給湯機"
                    elif str(dataHW2[1]) == "重油":
                        HeatSourceType = "ボイラ"
                    elif str(dataHW2[1]) == "灯油":
                        HeatSourceType = "ボイラ"
                    elif str(dataHW2[1]) == "他人から供給された熱（温水）":
                        HeatSourceType = "地域熱供給"
                    elif str(dataHW2[1]) == "他人から供給された熱（蒸気）":
                        HeatSourceType = "地域熱供給"
                    else:
                        validation["error"].append( "様式5-2.給湯機器 "+ str(i+1) +"行目:「②燃料種類」の入力に誤りがあります。") 

                    RatedCapacity = check_value(dataHW2[2], "様式5-2.給湯機器 "+ str(i+1) +"行目:「③定格加熱能力」", True, None, "数値", None, 0, None)
                    efficiency = check_value(dataHW2[3], "様式5-2.給湯機器 "+ str(i+1) +"行目:「④熱源効率」", True, None, "数値", None, 0, None)

                    if RatedCapacity == None or RatedCapacity == "":
                        RatedFuelConsumption = None
                    elif efficiency == None  or efficiency == "" or efficiency <= 0:
                        RatedFuelConsumption = None
                    else:
                        RatedFuelConsumption = RatedCapacity / efficiency

                    InsulationType = str(dataHW2[4]).replace("１","1")

                    data["HotwaterSupplySystems"][unitKey] = {
                        "HeatSourceUnit":[
                            {
                                "UsageType": "給湯負荷用",
                                "HeatSourceType": HeatSourceType,
                                "Number": 1,
                                "RatedCapacity": RatedCapacity,
                                "RatedPowerConsumption": 0,
                                "RatedFuelConsumption": RatedFuelConsumption,
                            }
                        ],
                        "InsulationType":
                            check_value(InsulationType, "様式5-2.給湯機器 "+ str(i+1) +"行目:「⑤配管保温仕様」", True, None, "文字列", input_options["配管保温仕様"], None, None),
                        "PipeSize": 
                            check_value(dataHW2[5], "様式5-2.給湯機器 "+ str(i+1) +"行目:「⑥接続口径」", True, None, "数値", None, 0, None),
                        "SolarSystemArea":
                            check_value(dataHW2[6], "様式5-2.給湯機器 "+ str(i+1) +"行目:「⑦有効集熱面積」", False, None, "数値", None, 0, None),
                        "SolarSystemDirection":
                            check_value(dataHW2[7], "様式5-2.給湯機器 "+ str(i+1) +"行目:「⑧集熱面の方位角」", False, None, "数値", None, -360, 360),
                        "SolarSystemAngle": 
                            check_value(dataHW2[8], "様式5-2.給湯機器 "+ str(i+1) +"行目:「⑨集熱面の傾斜角」", False, None, "数値", None, -180, 180),
                        "Info":
                            check_value(dataHW2[9], "様式5-2.給湯機器 "+ str(i+1) +"行目:「⑩備考」", False, None, "文字列", None, 0, None),
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
                dataEV[9] = "VVVF(電力回生あり)"
            elif str(dataEV[9]) == "VVVF（電力回生なし、ギアレス）":
                dataEV[9] = "VVVF(電力回生なし、ギアレス)"
            elif str(dataEV[9]) == "VVVF（電力回生あり、ギアレス）":
                dataEV[9] = "VVVF(電力回生あり、ギアレス)"
            
            # 階と室名が空欄でない場合
            if (dataEV[0] != "") and (dataEV[1] != "") :

                # 階＋室をkeyとする
                roomKey = str(dataEV[0]) + '_' + str(dataEV[1])

                if roomKey in data["Elevators"]:  # 昇降機については、室名の重複があり得る。

                    data["Elevators"][roomKey]["Elevator"].append(
                        {
                            "ElevatorName":
                                check_value(dataEV[4], "様式6.昇降機 "+ str(i+1) +"行目:「②機器名称」", False, "-", "文字列", None, None, None),                            
                            "Number": 
                                check_value(dataEV[5], "様式6.昇降機 "+ str(i+1) +"行目:「③台数」", True, None, "数値", None, 0, None),   
                            "LoadLimit":
                                check_value(dataEV[6], "様式6.昇降機 "+ str(i+1) +"行目:「④積載量」", True, None, "数値", None, 0, None),   
                            "Velocity":
                                check_value(dataEV[7], "様式6.昇降機 "+ str(i+1) +"行目:「⑤速度」", True, None, "数値", None, 0, None),   
                            "TransportCapacityFactor":
                                check_value(dataEV[8], "様式6.昇降機 "+ str(i+1) +"行目:「⑥輸送能力係数」", True, 1, "数値", None, 0, None),  
                            "ControlType":
                                check_value(dataEV[9], "様式6.昇降機 "+ str(i+1) +"行目:「⑦速度制御方式」", True, "交流帰還制御", "文字列", input_options["速度制御方式"], 0, None),  
                            "Info":
                                check_value(dataEV[10], "様式6.昇降機 "+ str(i+1) +"行目:「⑧備考」", False, None, "文字列", None, None, None),
                        }
                    )
                    
                else:

                    data["Elevators"][roomKey] = {
                        "Elevator": [
                            {
                                "ElevatorName":
                                    check_value(dataEV[4], "様式6.昇降機 "+ str(i+1) +"行目:「②機器名称」", False, "-", "文字列", None, None, None),                            
                                "Number": 
                                    check_value(dataEV[5], "様式6.昇降機 "+ str(i+1) +"行目:「③台数」", True, None, "数値", None, 0, None),   
                                "LoadLimit":
                                    check_value(dataEV[6], "様式6.昇降機 "+ str(i+1) +"行目:「④積載量」", True, None, "数値", None, 0, None),   
                                "Velocity":
                                    check_value(dataEV[7], "様式6.昇降機 "+ str(i+1) +"行目:「⑤速度」", True, None, "数値", None, 0, None),   
                                "TransportCapacityFactor":
                                    check_value(dataEV[8], "様式6.昇降機 "+ str(i+1) +"行目:「⑥輸送能力係数」", True, 1, "数値", None, 0, None),  
                                "ControlType":
                                    check_value(dataEV[9], "様式6.昇降機 "+ str(i+1) +"行目:「⑦速度制御方式」", True, "交流帰還制御", "文字列", input_options["速度制御方式"], 0, None),  
                                "Info":
                                    check_value(dataEV[10], "様式6.昇降機 "+ str(i+1) +"行目:「⑧備考」", False, None, "文字列", None, None, None),
                            }
                        ]
                    }

            elif (dataEV[5] != ""):

                data["Elevators"][roomKey]["Elevator"].append(
                    {
                        "ElevatorName":
                            check_value(dataEV[4], "様式6.昇降機 "+ str(i+1) +"行目:「②機器名称」", False, "-", "文字列", None, None, None),                            
                        "Number": 
                            check_value(dataEV[5], "様式6.昇降機 "+ str(i+1) +"行目:「③台数」", True, None, "数値", None, 0, None),   
                        "LoadLimit":
                            check_value(dataEV[6], "様式6.昇降機 "+ str(i+1) +"行目:「④積載量」", True, None, "数値", None, 0, None),   
                        "Velocity":
                            check_value(dataEV[7], "様式6.昇降機 "+ str(i+1) +"行目:「⑤速度」", True, None, "数値", None, 0, None),   
                        "TransportCapacityFactor":
                            check_value(dataEV[8], "様式6.昇降機 "+ str(i+1) +"行目:「⑥輸送能力係数」", True, 1, "数値", None, 0, None),  
                        "ControlType":
                            check_value(dataEV[9], "様式6.昇降機 "+ str(i+1) +"行目:「⑦速度制御方式」", True, "交流帰還制御", "文字列", input_options["速度制御方式"], 0, None),  
                        "Info":
                            check_value(dataEV[10], "様式6.昇降機 "+ str(i+1) +"行目:「⑧備考」", False, None, "文字列", None, None, None),
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

                if dataPV[0] in data["PhotovoltaicSystems"]:

                    validation["error"].append( "様式7-1.太陽光発電:「①太陽光発電システム名称」に重複があります（"+ str(i+1) +"行目「"+ dataPV[0] +"」）。")

                else:

                    data["PhotovoltaicSystems"][dataPV[0]] = {

                        "PowerConditionerEfficiency":
                            check_value(dataPV[1], "様式7-1.太陽光発電 "+ str(i+1) +"行目:「②パワーコンディショナの効率」", False, 0.927, "数値", None, 0, 1),
                        "CellType":
                            check_value(dataPV[2], "様式7-1.太陽光発電 "+ str(i+1) +"行目:「③太陽電池の種類」", True, None, "文字列", input_options["太陽電池の種類"], None, None),
                        "ArraySetupType":
                            check_value(dataPV[3], "様式7-1.太陽光発電 "+ str(i+1) +"行目:「④アレイ設置方式」", True, None, "文字列", input_options["アレイ設置方式"], None, None),
                        "ArrayCapacity":
                            check_value(dataPV[4], "様式7-1.太陽光発電 "+ str(i+1) +"行目:「⑤アレイのシステム容量」", True, None, "数値", None, 0, None),
                        "Direction":
                            check_value(dataPV[5], "様式7-1.太陽光発電 "+ str(i+1) +"行目:「⑥パネルの方位角」", True, None, "数値", None, -360, 360),
                        "Angle":
                            check_value(dataPV[6], "様式7-1.太陽光発電 "+ str(i+1) +"行目:「⑦パネルの傾斜角」", True, None, "数値", None, -180, 180),
                        "Info": 
                            check_value(dataPV[1], "様式7-1.太陽光発電 "+ str(i+1) +"行目:「⑧備考」", False, None, "文字列", None, None, None),
                    
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

                # 重複チェック
                if dataCG[0] in data["CogenerationSystems"]:

                    validation["error"].append( "様式7-3.コジェネ:「①コージェネレーション設備名称」に重複があります（"+ str(i+1) +"行目「"+ dataCG[0] +"」）。")

                else:

                    data["CogenerationSystems"][dataCG[0]] = {

                        "RatedCapacity":
                            check_value(dataCG[1], "様式7-3.コジェネ "+ str(i+1) +"行目:「②定格発電出力」", True, None, "数値", None, 0, None),
                        "Number":
                            check_value(dataCG[2], "様式7-3.コジェネ "+ str(i+1) +"行目:「③設置台数」", True, None, "数値", None, 0, None),
                        "PowerGenerationEfficiency_100":
                            check_value(dataCG[3], "様式7-3.コジェネ "+ str(i+1) +"行目:「④発電効率（負荷率1.00)」", True, None, "数値", None, 0, 1),
                        "PowerGenerationEfficiency_75":
                            check_value(dataCG[4], "様式7-3.コジェネ "+ str(i+1) +"行目:「⑤発電効率（負荷率0.75)」", True, None, "数値", None, 0, 1),                    
                        "PowerGenerationEfficiency_50":
                            check_value(dataCG[5], "様式7-3.コジェネ "+ str(i+1) +"行目:「⑥発電効率（負荷率0.50)」", True, None, "数値", None, 0, 1),       
                        "HeatGenerationEfficiency_100":
                            check_value(dataCG[6], "様式7-3.コジェネ "+ str(i+1) +"行目:「⑦排熱効率（負荷率1.00)」", True, None, "数値", None, 0, 1),
                        "HeatGenerationEfficiency_75":
                            check_value(dataCG[7], "様式7-3.コジェネ "+ str(i+1) +"行目:「⑧排熱効率（負荷率0.75)」", True, None, "数値", None, 0, 1),
                        "HeatGenerationEfficiency_50":
                            check_value(dataCG[8], "様式7-3.コジェネ "+ str(i+1) +"行目:「⑨排熱効率（負荷率0.50)」", True, None, "数値", None, 0, 1),

                        "HeatRecoveryPriorityCooling":
                            check_value(dataCG[9], "様式7-3.コジェネ "+ str(i+1) +"行目:「⑩排熱利用優先順位（空調冷熱源)」", False, None, "文字列", input_options["排熱利用優先順位"], None, None),
                        "HeatRecoveryPriorityHeating":
                            check_value(dataCG[10], "様式7-3.コジェネ "+ str(i+1) +"行目:「⑪排熱利用優先順位（空調温熱源)」", False, None, "文字列", input_options["排熱利用優先順位"], None, None),
                        "HeatRecoveryPriorityHotWater":
                            check_value(dataCG[11], "様式7-3.コジェネ "+ str(i+1) +"行目:「⑫排熱利用優先順位（給湯)」", False, None, "文字列", input_options["排熱利用優先順位"], None, None),
                        "24hourOperation":
                            check_value(dataCG[12], "様式7-3.コジェネ "+ str(i+1) +"行目:「⑬24時間運転の有無」", False, "無", "文字列", input_options["有無"], None, None),
                        
                        "CoolingSystem":
                            check_value(dataCG[13], "様式7-3.コジェネ "+ str(i+1) +"行目:「⑭排熱利用系統（空調冷熱源)」", False, None, "文字列", data["HeatsourceSystem"], None, None),
                        "HeatingSystem":
                            check_value(dataCG[14], "様式7-3.コジェネ "+ str(i+1) +"行目:「⑮排熱利用系統（空調温熱源)」", False, None, "文字列", data["HeatsourceSystem"], None, None),
                        "HowWaterSystem":
                            check_value(dataCG[15], "様式7-3.コジェネ "+ str(i+1) +"行目:「⑯排熱利用系統（給湯)」", False, None, "文字列", data["HotwaterSupplySystems"], None, None),
                        "Info":
                            check_value(dataCG[16], "様式7-3.コジェネ "+ str(i+1) +"行目:「⑰備考」", False, None, "文字列", None, None, None),

                    }

        #-------------------
        # Varidation
        #-------------------
        for csg_system in data["CogenerationSystems"]:

            if check_duplicates([
                data["CogenerationSystems"][csg_system]["HeatRecoveryPriorityCooling"],
                data["CogenerationSystems"][csg_system]["HeatRecoveryPriorityHeating"], 
                data["CogenerationSystems"][csg_system]["HeatRecoveryPriorityHotWater"]]):

                validation["error"].append( "様式7-3.コジェネ: コージェネレーション設備名称「"+ csg_system +"」の排熱利用優先順位に重複があります。")

            if data["CogenerationSystems"][csg_system]["HeatRecoveryPriorityCooling"] == "" and \
                data["CogenerationSystems"][csg_system]["HeatRecoveryPriorityHeating"] == "" and \
                data["CogenerationSystems"][csg_system]["HeatRecoveryPriorityHotWater"] == "":

                validation["error"].append( "様式7-3.コジェネ: コージェネレーション設備名称「"+ csg_system +"」の排熱利用優先順位が入力されていません。")

            if data["CogenerationSystems"][csg_system]["CoolingSystem"] == "" and \
                data["CogenerationSystems"][csg_system]["HeatingSystem"] == "" and \
                data["CogenerationSystems"][csg_system]["HowWaterSystem"] == "":

                validation["error"].append( "様式7-3.コジェネ: コージェネレーション設備名称「"+ csg_system +"」の排熱利用系統が入力されていません。")

            if (data["CogenerationSystems"][csg_system]["HeatRecoveryPriorityCooling"] != "" and data["CogenerationSystems"][csg_system]["CoolingSystem"] == ""):
                validation["error"].append( "様式7-3.コジェネ: コージェネレーション設備名称「"+ csg_system +"」の排熱利用系統（冷熱源）が入力されていません。")

            if (data["CogenerationSystems"][csg_system]["HeatRecoveryPriorityCooling"] == "" and data["CogenerationSystems"][csg_system]["CoolingSystem"] != ""):
                validation["error"].append( "様式7-3.コジェネ: コージェネレーション設備名称「"+ csg_system +"」の排熱利用優先順位（冷熱源）が入力されていません。")

            if (data["CogenerationSystems"][csg_system]["HeatRecoveryPriorityHeating"] != "" and data["CogenerationSystems"][csg_system]["HeatingSystem"] == ""):
                validation["error"].append( "様式7-3.コジェネ: コージェネレーション設備名称「"+ csg_system +"」の排熱利用系統（温熱源）が入力されていません。")

            if (data["CogenerationSystems"][csg_system]["HeatRecoveryPriorityHeating"] == "" and data["CogenerationSystems"][csg_system]["HeatingSystem"] != ""):
                validation["error"].append( "様式7-3.コジェネ: コージェネレーション設備名称「"+ csg_system +"」の排熱利用優先順位（温熱源）が入力されていません。")

            if (data["CogenerationSystems"][csg_system]["HeatRecoveryPriorityHotWater"] != "" and data["CogenerationSystems"][csg_system]["HowWaterSystem"] == ""):
                validation["error"].append( "様式7-3.コジェネ: コージェネレーション設備名称「"+ csg_system +"」の排熱利用系統（給湯）が入力されていません。")

            if (data["CogenerationSystems"][csg_system]["HeatRecoveryPriorityHotWater"] == "" and data["CogenerationSystems"][csg_system]["HowWaterSystem"] != ""):
                validation["error"].append( "様式7-3.コジェネ: コージェネレーション設備名称「"+ csg_system +"」の排熱利用優先順位（給湯）が入力されていません。")


    if "SP-1) 変流量・変風量制御" in wb.sheet_names():

        data["SpecialInputData"]["flow_control"] = {}

        # シートの読み込み
        sheet_SP1 = wb.sheet_by_name("SP-1) 変流量・変風量制御")

        # 行のループ（nrowsが10より小さいと空行列になる）
        for i in range(10,sheet_SP1.nrows):

            # シートから「行」の読み込み
            dataSP1 = sheet_SP1.row_values(i)

            if dataSP1[0] != "":

                data["SpecialInputData"]["flow_control"][dataSP1[0]] = {
                    "Type": "任意評定",
                    "a4": float(dataSP1[1]),
                    "a3": float(dataSP1[2]),
                    "a2": float(dataSP1[3]),
                    "a1": float(dataSP1[4]),
                    "a0": float(dataSP1[5])
                }

    if "SP-3) 熱源水温度" in wb.sheet_names():

        data["SpecialInputData"]["heatsource_temperature_monthly"] = {}

        # シートの読み込み
        sheet_SP3 = wb.sheet_by_name("SP-3) 熱源水温度")

        # 行のループ（nrowsが10より小さいと空行列になる）
        for i in range(10,sheet_SP3.nrows):

            # シートから「行」の読み込み
            dataSP3 = sheet_SP3.row_values(i)

            if dataSP3[0] != "":

                data["SpecialInputData"]["heatsource_temperature_monthly"][dataSP3[0]] = {
                    "1月":  float(dataSP3[1]), 
                    "2月":  float(dataSP3[2]), 
                    "3月":  float(dataSP3[3]), 
                    "4月":  float(dataSP3[4]), 
                    "5月":  float(dataSP3[5]), 
                    "6月":  float(dataSP3[6]), 
                    "7月":  float(dataSP3[7]), 
                    "8月":  float(dataSP3[8]),  
                    "9月":  float(dataSP3[9]), 
                    "10月": float(dataSP3[10]), 
                    "11月": float(dataSP3[11]), 
                    "12月": float(dataSP3[12])
                }


    if "SP-4) 室負荷" in wb.sheet_names():

        data["SpecialInputData"]["Qroom"] = {}

        # シートの読み込み
        sheet_SP4 = wb.sheet_by_name("SP-4) 室負荷")
        # 初期化
        roomKey = None

        # 行のループ
        for i in range(10,sheet_SP4.nrows):

            # シートから「行」の読み込み
            dataSP4 = sheet_SP4.row_values(i)

            # 階と室名が空欄でない場合
            if (dataSP4[0] != "") and (dataSP4[1] != ""):

                # 階＋室＋ゾーン名をkeyとする（上書き）
                if (dataSP4[2] != ""):
                    roomKey = str(dataSP4[0]) + '_' + str(dataSP4[1]) + '_' + str(dataSP4[2])
                else:
                    roomKey = str(dataSP4[0]) + '_' + str(dataSP4[1])

            if roomKey not in data["SpecialInputData"]["Qroom"]:
                data["SpecialInputData"]["Qroom"][roomKey] = {}

            Qroom_input = list()
            for dd in range(0,365):
                Qroom_input.append(float(dataSP4[4+dd]))

            if dataSP4[3] == "冷房":
                data["SpecialInputData"]["Qroom"][roomKey]["QroomDc"] = Qroom_input
            elif dataSP4[3] == "暖房":
                data["SpecialInputData"]["Qroom"][roomKey]["QroomDh"] = Qroom_input
            else:
                raise Exception("室負荷の種類が不正です。")


    if "SP-5) 気象データ" in wb.sheet_names():

        # シートの読み込み
        sheet_SP5 = wb.sheet_by_name("SP-5) 気象データ")

        # 行のループ
        Tout_8760 = []
        Xout_8760 = []
        Iod_8760  = []
        Ios_8760  = []
        Inn_8760  = []

        for i in range(10,sheet_SP5.nrows):

            # シートから「行」の読み込み
            dataSP5 = sheet_SP5.row_values(i)

            Tout_8760.append(float(dataSP5[4]))
            Xout_8760.append(float(dataSP5[5]))
            Iod_8760.append(float(dataSP5[6]))
            Ios_8760.append(float(dataSP5[7]))
            Inn_8760.append(float(dataSP5[8]))

        # データの処理がなされていたら、365×24の行列に変更して保存
        if Tout_8760 != []:
            data["SpecialInputData"]["climate_data"] = {
                "Tout": bc.trans_8760to36524(Tout_8760),
                "Xout": bc.trans_8760to36524(Xout_8760),
                "Iod": bc.trans_8760to36524(Iod_8760),
                "Ios": bc.trans_8760to36524(Ios_8760),
                "Inn": bc.trans_8760to36524(Inn_8760)
            }

    if "SP-6) カレンダー" in wb.sheet_names():

        data["SpecialInputData"]["calender"] = {}

        # シートの読み込み
        sheet_SP6 = wb.sheet_by_name("SP-6) カレンダー")

        for i in range(10,sheet_SP6.nrows):

            # シートから「行」の読み込み
            dataSP6 = sheet_SP6.row_values(i)

            building_type = dataSP6[0]
            room_type = dataSP6[1]
            calender_num = [int(x) for x in dataSP6[2:]]  # 整数型に変換


            # 建物用途が既に登録されているかを判定
            if building_type not in data["SpecialInputData"]["calender"]:

                data["SpecialInputData"]["calender"][building_type] = {}
                data["SpecialInputData"]["calender"][building_type] = {
                    room_type : calender_num
                }

            else:
                data["SpecialInputData"]["calender"][building_type][room_type] = calender_num


    if "SP-7) 室スケジュール" in wb.sheet_names():

        data["SpecialInputData"]["room_schedule"] = {}

        # シートの読み込み
        sheet_SP7 = wb.sheet_by_name("SP-7) 室スケジュール")
        # 初期化
        roomKey = None

        for i in range(10,sheet_SP7.nrows):

            # シートから「行」の読み込み
            dataSP7 = sheet_SP7.row_values(i)

            # 階と室名が空欄でない場合
            if (dataSP7[0] != "") and (dataSP7[1] != ""):

                roomKey = str(dataSP7[0]) + '_' + str(dataSP7[1])

                data["SpecialInputData"]["room_schedule"][roomKey] = {
                    "roomDayMode": "",
                    "schedule": {}
                }

                # 使用時間帯
                if dataSP7[2] == "終日":
                    data["SpecialInputData"]["room_schedule"][roomKey]["roomDayMode"] = "終日"
                elif dataSP7[2] == "昼":
                    data["SpecialInputData"]["room_schedule"][roomKey]["roomDayMode"] = "昼"
                elif dataSP7[2] == "夜":
                    data["SpecialInputData"]["room_schedule"][roomKey]["roomDayMode"] = "夜"
                else:
                    raise Exception("使用時間帯の入力が不正です")

                if dataSP7[3] == "室の同時使用率":
                    data["SpecialInputData"]["room_schedule"][roomKey]["schedule"]["室の同時使用率"] =  bc.trans_8760to36524(dataSP7[4:])
                elif dataSP7[3] == "照明発熱密度比率":
                    data["SpecialInputData"]["room_schedule"][roomKey]["schedule"]["照明発熱密度比率"] =  bc.trans_8760to36524(dataSP7[4:])
                elif dataSP7[3] == "人体発熱密度比率":
                    data["SpecialInputData"]["room_schedule"][roomKey]["schedule"]["人体発熱密度比率"] =  bc.trans_8760to36524(dataSP7[4:])
                elif dataSP7[3] == "機器発熱密度比率":
                    data["SpecialInputData"]["room_schedule"][roomKey]["schedule"]["機器発熱密度比率"] =  bc.trans_8760to36524(dataSP7[4:])
                else:
                    raise Exception("スケジュールの種類が不正です")

            # 階と室名が空欄であり、かつ、スケジュールの種類の入力がある場合
            elif (dataSP7[0] == "") and (dataSP7[1] == "") and (dataSP7[3] != ""):

                if dataSP7[3] == "室の同時使用率":
                    data["SpecialInputData"]["room_schedule"][roomKey]["schedule"]["室の同時使用率"] =  bc.trans_8760to36524(dataSP7[4:])
                elif dataSP7[3] == "照明発熱密度比率":
                    data["SpecialInputData"]["room_schedule"][roomKey]["schedule"]["照明発熱密度比率"] =  bc.trans_8760to36524(dataSP7[4:])
                elif dataSP7[3] == "人体発熱密度比率":
                    data["SpecialInputData"]["room_schedule"][roomKey]["schedule"]["人体発熱密度比率"] =  bc.trans_8760to36524(dataSP7[4:])
                elif dataSP7[3] == "機器発熱密度比率":
                    data["SpecialInputData"]["room_schedule"][roomKey]["schedule"]["機器発熱密度比率"] =  bc.trans_8760to36524(dataSP7[4:])
                else:
                    raise Exception("スケジュールの種類が不正です")

    if "SP-8) 日射熱取得率" in wb.sheet_names():

        data["SpecialInputData"]["window_Ivalue"] = {}

        # シートの読み込み
        sheet_SP8 = wb.sheet_by_name("SP-8) 日射熱取得率")

        for i in range(10,sheet_SP8.nrows):

            # シートから「行」の読み込み
            dataSP8 = sheet_SP8.row_values(i)

            data["SpecialInputData"]["window_Ivalue"][dataSP8[0]] = dataSP8[1:]


    if "SP-9) 室使用条件" in wb.sheet_names():

        data["SpecialInputData"]["room_usage_condition"] = {}

        # シートの読み込み
        sheet_SP9 = wb.sheet_by_name("SP-9) 室使用条件")

        for i in range(10,sheet_SP9.nrows):

            # シートから「行」の読み込み
            dataSP9 = sheet_SP9.row_values(i)
    
            if dataSP9[0] != "" and dataSP9[1] != "":

                # 建物用途
                if dataSP9[0] not in data["SpecialInputData"]["room_usage_condition"]:
                    data["SpecialInputData"]["room_usage_condition"][dataSP9[0]] = {}

                # 室用途
                data["SpecialInputData"]["room_usage_condition"][dataSP9[0]][dataSP9[1]] = {
                    "照明発熱参照値" : dataSP9[2],
                    "人体発熱参照値" : dataSP9[3],
                    "機器発熱参照値" : dataSP9[4],
                    "作業強度指数" : dataSP9[5],
                    "外気導入量" : dataSP9[6],
                    "年間換気時間" : dataSP9[7],
                    "年間湯使用量（洗面）" : dataSP9[8],
                    "年間湯使用量（シャワー）" : dataSP9[9],
                    "年間湯使用量（厨房）" : dataSP9[10],
                    "年間湯使用量（その他）" : dataSP9[11]
                }


    if "SP-10) 空調負荷" in wb.sheet_names():

        data["SpecialInputData"]["Qahu"] = {}

        # シートの読み込み
        sheet_SP10 = wb.sheet_by_name("SP-10) 空調負荷")

        for i in range(10,sheet_SP10.nrows):

            # シートから「行」の読み込み
            dataSP10 = sheet_SP10.row_values(i)
            
            if dataSP10[0] != "":
            
                data["SpecialInputData"]["Qahu"][dataSP10[0]] = bc.trans_8760to36524(dataSP10[1:])


    if "SP-11) 湯使用量" in wb.sheet_names():

        data["SpecialInputData"]["hotwater_demand_daily"] = {}

        # シートの読み込み
        sheet_SP11 = wb.sheet_by_name("SP-11) 湯使用量")
        # 初期化
        roomKey = None

        for i in range(10,sheet_SP11.nrows):

            # シートから「行」の読み込み
            dataSP11 = sheet_SP11.row_values(i)

            # 階と室名が空欄でない場合
            if (dataSP11[0] != "") and (dataSP11[1] != ""):

                roomKey = str(dataSP11[0]) + '_' + str(dataSP11[1])

                data["SpecialInputData"]["hotwater_demand_daily"][roomKey] = {}

                if dataSP11[2] == "洗面":
                    data["SpecialInputData"]["hotwater_demand_daily"][roomKey]["洗面"] = dataSP11[3:]
                elif dataSP11[2] == "シャワー":
                    data["SpecialInputData"]["hotwater_demand_daily"][roomKey]["シャワー"] =  dataSP11[3:]
                elif dataSP11[2] == "厨房":
                    data["SpecialInputData"]["hotwater_demand_daily"][roomKey]["厨房"] =  dataSP11[3:]
                elif dataSP11[2] == "その他":
                    data["SpecialInputData"]["hotwater_demand_daily"][roomKey]["その他"] =  dataSP11[3:]
                else:
                    raise Exception("使用用途が不正です")

            # 階と室名が空欄であり、かつ、使用用途ｓの入力がある場合
            elif (dataSP11[0] == "") and (dataSP11[1] == "") and (dataSP11[2] != ""):

                if dataSP11[2] == "洗面":
                    data["SpecialInputData"]["hotwater_demand_daily"][roomKey]["洗面"] = dataSP11[3:]
                elif dataSP11[2] == "シャワー":
                    data["SpecialInputData"]["hotwater_demand_daily"][roomKey]["シャワー"] =  dataSP11[3:]
                elif dataSP11[2] == "厨房":
                    data["SpecialInputData"]["hotwater_demand_daily"][roomKey]["厨房"] =  dataSP11[3:]
                elif dataSP11[2] == "その他":
                    data["SpecialInputData"]["hotwater_demand_daily"][roomKey]["その他"] =  dataSP11[3:]
                else:
                    raise Exception("使用用途が不正です")


    # バリデーションの実行
    # bc.inputdata_validation(data)

    return data, validation


if __name__ == '__main__':

    print('----- make_inputdata.py -----')

    #-----------------------
    # WEBPRO Ver3シートの例
    #-----------------------
    # directory = "./sample/"
    # case_name = 'Builelib_inputSheet'

    # inputdata = make_jsondata_from_Ver4_sheet(directory + case_name + ".xlsx")

    # # json出力
    # with open(directory + case_name + ".json",'w', encoding='utf-8') as fw:
    #     json.dump(inputdata,fw,indent=4,ensure_ascii=False)

    #-----------------------
    # WEBPRO Ver2シートの例
    #-----------------------
    directory = "./sample/"

    case_name = 'WEBPRO_inputSheet_sample_error'

    inputdata, validation = make_jsondata_from_Ver2_sheet(directory + case_name + ".xlsm")

    print(validation)

    # json出力
    with open(directory + case_name + ".json",'w', encoding='utf-8') as fw:
        json.dump(inputdata,fw,indent=4,ensure_ascii=False)


    #-----------------------
    # WEBPRO Ver2シートの例
    #-----------------------
    # directory = "./tests/photovoltaic/"

    # case_name = 'PV_case01'

    # inputdata = make_jsondata_from_Ver2_sheet(directory + case_name + ".xlsm")

    # # json出力
    # with open(directory + case_name + ".json",'w', encoding='utf-8') as fw:
    #     json.dump(inputdata,fw,indent=4,ensure_ascii=False)


    #-----------------------
    # WEBPRO Ver2シートの例（連続）
    #-----------------------
    # directory = "./tests/airconditioning/"

    # for id in range(1,51):
    #     if id < 10:
    #         case_name = 'ACtest_Case00' + str(int(id))
    #     else:
    #         case_name = 'ACtest_Case0' + str(int(id))

    #     inputdata = make_jsondata_from_Ver2_sheet(directory + case_name + ".xlsm")

    #     # json出力
    #     with open(directory + case_name + ".json",'w', encoding='utf-8') as fw:
    #         json.dump(inputdata,fw,indent=4,ensure_ascii=False)


    # #-----------------------
    # # WEBPRO Ver2シートの例（連続）
    # #-----------------------
    # directory = "./tests/cogeneration/"

    # for id in range(9,10):
    #     if id < 10:
    #         case_name = 'Case_office_0' + str(int(id))
    #     else:
    #         case_name = 'Case_office_' + str(int(id))

    #     inputdata = make_jsondata_from_Ver2_sheet(directory + case_name + ".xlsm")

    #     # json出力
    #     with open(directory + case_name + ".json",'w', encoding='utf-8') as fw:
    #         json.dump(inputdata,fw,indent=4,ensure_ascii=False)
