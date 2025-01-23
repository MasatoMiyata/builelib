# from numpy import False_
import xlrd
import json
import jsonschema
import os
import copy

import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import commons as bc

# テンプレートファイルの保存場所
template_directory =  os.path.dirname(os.path.abspath(__file__)) + "/inputdata/"

# データベースファイルの保存場所
database_directory =  os.path.dirname(os.path.abspath(__file__)) + "/database/"

# 入力値の選択肢一覧
input_options = {
    "有無": ["有","無"],
    "地域区分": ["1","2","3","4","5","6","7","8"],
    "年間日射地域区分": ["A1","A2","A3","A4","A5"],
    "建物用途": ["事務所等","ホテル等","病院等","物販店舗等","学校等","飲食店等","集会所等","工場等","共同住宅"],
    "室用途": {
        "事務所等":["事務室","電子計算機器事務室","会議室","喫茶室","社員食堂","中央監視室","更衣室又は倉庫","廊下","ロビー","便所","喫煙室","厨房","屋内駐車場","機械室","電気室","湯沸室等","食品庫等","印刷室等","廃棄物保管場所等","非主要室"],
        "ホテル等":["客室","客室内の浴室等","終日利用されるフロント","終日利用される事務室","終日利用される廊下","終日利用されるロビー","終日利用される共用部の便所","終日利用される喫煙室","宴会場","会議室","結婚式場","レストラン","ラウンジ","バー","店舗",
            "社員食堂","更衣室又は倉庫","日中のみ利用されるフロント","日中のみ利用される事務室","日中のみ利用される廊下","日中のみ利用されるロビー","日中のみ利用される共用部の便所","日中のみ利用される喫煙室","厨房","屋内駐車場","機械室","電気室","湯沸室等","食品庫等","印刷室等","廃棄物保管場所等","非主要室"],
        "病院等":["病室","浴室等","看護職員室","終日利用される廊下","終日利用されるロビー","終日利用される共用部の便所","終日利用される喫煙室","診察室","待合室","手術室","検査室","集中治療室","解剖室等","レストラン","事務室","更衣室又は倉庫",
        "日中のみ利用される廊下","日中のみ利用されるロビー","日中のみ利用される共用部の便所","日中のみ利用される喫煙室","厨房","屋内駐車場","機械室","電気室","湯沸室等","食品庫等","印刷室等","廃棄物保管場所等","非主要室"],
        "物販店舗等":["大型店の売場","専門店の売場","スーパーマーケットの売場","荷さばき場","事務室","更衣室又は倉庫","ロビー","便所","喫煙室","厨房","屋内駐車場","機械室","電気室","湯沸室等","食品庫等","印刷室等","廃棄物保管場所等","非主要室"],
        "学校等":["小中学校の教室","高等学校の教室","職員室","小中学校又は高等学校の食堂","大学の教室","大学の食堂","事務室","研究室","電子計算機器演習室","実験室","実習室","講堂又は体育館","宿直室",
            "更衣室又は倉庫","廊下","ロビー","便所","喫煙室","厨房","屋内駐車場","機械室","電気室","湯沸室等","食品庫等","印刷室等","廃棄物保管場所等","非主要室"],
        "飲食店等":["レストランの客室","軽食店の客室","喫茶店の客室","バー","フロント","事務室","更衣室又は倉庫","廊下","ロビー","便所","喫煙室","厨房","屋内駐車場","機械室","電気室","湯沸室等","食品庫等","印刷室等","廃棄物保管場所等","非主要室"],
        "集会所等":["アスレチック場の運動室","アスレチック場のロビー","アスレチック場の便所","アスレチック場の喫煙室","公式競技用スケート場","公式競技用体育館","一般競技用スケート場","一般競技用体育館","レクリエーション用スケート場","レクリエーション用体育館","競技場の客席",
            "競技場のロビー","競技場の便所","競技場の喫煙室","公衆浴場の浴室","公衆浴場の脱衣所","公衆浴場の休憩室","公衆浴場のロビー","公衆浴場の便所","公衆浴場の喫煙室","映画館の客席","映画館のロビー","映画館の便所","映画館の喫煙室","図書館の図書室","図書館のロビー",
            "図書館の便所","図書館の喫煙室","博物館の展示室","博物館のロビー","博物館の便所","博物館の喫煙室","劇場の楽屋","劇場の舞台","劇場の客席","劇場のロビー","劇場の便所","劇場の喫煙室","カラオケボックス","ボーリング場","ぱちんこ屋","競馬場又は競輪場の客席",
            "競馬場又は競輪場の券売場","競馬場又は競輪場の店舗","競馬場又は競輪場のロビー","競馬場又は競輪場の便所","競馬場又は競輪場の喫煙室","社寺の本殿","社寺のロビー","社寺の便所","社寺の喫煙室","厨房","屋内駐車場","機械室","電気室","湯沸室等","食品庫等","印刷室等","廃棄物保管場所等","非主要室"],
        "工場等":["倉庫","屋外駐車場又は駐輪場"],
        "共同住宅":["屋内廊下","ロビー","管理人室","集会室","屋外廊下","屋内駐車場","機械室","電気室","廃棄物保管場所等"]
    },
    "方位": ["北","北東","東","南東","南","南西","西","北西","水平（上）","水平（下）"],
    "外壁の種類": ["日の当たる外壁","日の当たらない外壁","地盤に接する外壁","内壁"],
    "外壁の種類(WEBPRO)": ["外壁","接地壁"],
    "構造種別": ["木造","鉄筋コンクリート造等","鉄骨造","その他"],
    "断熱性能の入力方法": ["熱貫流率を入力","建材構成を入力","断熱材種類を入力"],
    "断熱材番号":["1","2","3","4","21","22","41","42","43","44","45","46","47","48","61","62","63","64","65","66","67","68","69","70","71","72","73","81","82","83","84","85","86","87","88","89","90",
        "101","102","103","104","105","106","107","121","122","123","124","125","126","127","128","129","130","131","132","133","134","141","142","143","144","145","146","161","162","163",
        "181","182","183","184","185","186","187","188","189","190","201","202","203","204","221","222","301","302"],
    "窓性能の入力方法": ["性能値を入力","ガラスの性能を入力","ガラスの種類を入力"],
    "建具の種類": ["樹脂製","木製","金属樹脂複合製","金属木複合製","金属製","樹脂製(単板ガラス)","樹脂製(複層ガラス)","木製(単板ガラス)","木製(複層ガラス)","金属樹脂複合製(単板ガラス)","金属樹脂複合製(複層ガラス)","金属木複合製(単板ガラス)","金属木複合製(複層ガラス)","金属製(単板ガラス)","金属製(複層ガラス)"],
    "ガラスの層数": ["複層","単層"],
    "ガラスの種類": ["3WgG06","3WgG07","3WgG08","3WgG09","3WgG10","3WgG11","3WgG12","3WgG13","3WgG14","3WgG15","3WgG16","3WsG06","3WsG07","3WsG08","3WsG09","3WsG10","3WsG11","3WsG12","3WsG13","3WsG14","3WsG15","3WsG16",
        "3WgA06","3WgA07","3WgA08","3WgA09","3WgA10","3WgA11","3WgA12","3WgA13","3WgA14","3WgA15","3WgA16","3WsA06","3WsA07","3WsA08","3WsA09","3WsA10","3WsA11","3WsA12","3WsA13","3WsA14","3WsA15","3WsA16",
        "3LgG06","3LgG07","3LgG08","3LgG09","3LgG10","3LgG11","3LgG12","3LgG13","3LgG14","3LgG15","3LgG16","3LsG06","3LsG07","3LsG08","3LsG09","3LsG10","3LsG11","3LsG12","3LsG13","3LsG14","3LsG15","3LsG16",
        "3LgA06","3LgA07","3LgA08","3LgA09","3LgA10","3LgA11","3LgA12","3LgA13","3LgA14","3LgA15","3LgA16","3LsA06","3LsA07","3LsA08","3LsA09","3LsA10","3LsA11","3LsA12","3LsA13","3LsA14","3LsA15","3LsA16",
        "3FA06","3FA07","3FA08","3FA09","3FA10","3FA11","3FA12","3FA13","3FA14","3FA15","3FA16","2LgG06","2LgG07","2LgG08","2LgG09","2LgG10","2LgG11","2LgG12","2LgG13","2LgG14","2LgG15","2LgG16","2LsG06","2LsG07","2LsG08","2LsG09","2LsG10","2LsG11","2LsG12","2LsG13","2LsG14","2LsG15","2LsG16",
        "2LgA06","2LgA07","2LgA08","2LgA09","2LgA10","2LgA11","2LgA12","2LgA13","2LgA14","2LgA15","2LgA16","2LsA06","2LsA07","2LsA08","2LsA09","2LsA10","2LsA11","2LsA12","2LsA13","2LsA14","2LsA15","2LsA16","2FA06","2FA07","2FA08","2FA09","2FA10","2FA11","2FA12","2FA13","2FA14","2FA15","2FA16","T","S"],
    "冷暖同時供給の有無": ["無","有","有（室負荷）","有（外気負荷）"],
    "蓄熱の種類": ["水蓄熱(混合型)","水蓄熱(成層型)","氷蓄熱"],
    "熱源機種": ["ウォータチリングユニット(空冷式)","ウォータチリングユニット(空冷式モジュール形)","ウォータチリングユニット(水冷式)","ウォータチリングユニット(水冷式地中熱タイプ1)","ウォータチリングユニット(水冷式地中熱タイプ2)","ウォータチリングユニット(水冷式地中熱タイプ3)","ウォータチリングユニット(水冷式地中熱タイプ4)",
        "ウォータチリングユニット(水冷式地中熱タイプ5)","スクリュー冷凍機","ターボ冷凍機","インバータターボ冷凍機","ブラインターボ冷凍機(蓄熱時)","ブラインターボ冷凍機(追掛時)","ウォータチリングユニット(空冷式氷蓄熱用)",
        "ウォータチリングユニット(空冷式モジュール形氷蓄熱用)","スクリュー冷凍機(氷蓄熱用)","吸収式冷凍機(都市ガス)","吸収式冷凍機(冷却水変流量、都市ガス)","吸収式冷凍機(LPG)","吸収式冷凍機(冷却水変流量、LPG)",
        "吸収式冷凍機(重油)","吸収式冷凍機(冷却水変流量、重油)","吸収式冷凍機(灯油)","吸収式冷凍機(冷却水変流量、灯油)","吸収式冷凍機(蒸気)","吸収式冷凍機(冷却水変流量、蒸気)","吸収式冷凍機(温水)",
        "吸収式冷凍機(一重二重併用形、都市ガス)","吸収式冷凍機(一重二重併用形、冷却水変流量、都市ガス)","吸収式冷凍機(一重二重併用形、LPG)","吸収式冷凍機(一重二重併用形、冷却水変流量、LPG)",
        "吸収式冷凍機(一重二重併用形、蒸気)","吸収式冷凍機(一重二重併用形、冷却水変流量、蒸気)","小型貫流ボイラ(都市ガス)","小型貫流ボイラ(LPG)","小型貫流ボイラ(重油)","小型貫流ボイラ(灯油)",
        "貫流ボイラ(都市ガス)","貫流ボイラ(LPG)","貫流ボイラ(重油)","貫流ボイラ(灯油)","温水ボイラ(都市ガス)","温水ボイラ(LPG)","温水ボイラ(重油)","温水ボイラ(灯油)","蒸気ボイラ(都市ガス)",
        "蒸気ボイラ(LPG)","蒸気ボイラ(重油)","蒸気ボイラ(灯油)","温水発生機(都市ガス)","温水発生機(LPG)","温水発生機(重油)","温水発生機(灯油)","パッケージエアコンディショナ(空冷式)",
        "パッケージエアコンディショナ(水冷式熱回収形)","パッケージエアコンディショナ(水冷式)","パッケージエアコンディショナ(水冷式地中熱タイプ1)","パッケージエアコンディショナ(水冷式地中熱タイプ2)",
        "パッケージエアコンディショナ(水冷式地中熱タイプ3)","パッケージエアコンディショナ(水冷式地中熱タイプ4)","パッケージエアコンディショナ(水冷式地中熱タイプ5)","ガスヒートポンプ冷暖房機(都市ガス)",
        "ガスヒートポンプ冷暖房機(LPG)","ルームエアコンディショナ","FF式ガス暖房機(都市ガス)","FF式ガス暖房機(LPG)","FF式石油暖房機","地域熱供給(冷水)","地域熱供給(温水)","地域熱供給(蒸気)",
        "熱交換器","電気式ヒーター","電気蓄熱暖房器","温風暖房機(都市ガス)","温風暖房機(LPG)","温風暖房機(重油)","温風暖房機(灯油)","ガスヒートポンプ冷暖房機(消費電力自給装置付、都市ガス)","ガスヒートポンプ冷暖房機(消費電力自給装置付、LPG)",
        "ウォータチリングユニット(水冷式地中熱タイプA)","ウォータチリングユニット(水冷式地中熱タイプB)","ウォータチリングユニット(水冷式地中熱タイプC)",
        "ウォータチリングユニット(水冷式地中熱タイプD)","ウォータチリングユニット(水冷式地中熱タイプE)","ウォータチリングユニット(水冷式地中熱タイプF)",
        "パッケージエアコンディショナ(水冷式地中熱タイプA)","パッケージエアコンディショナ(水冷式地中熱タイプB)","パッケージエアコンディショナ(水冷式地中熱タイプC)",
        "パッケージエアコンディショナ(水冷式地中熱タイプD)","パッケージエアコンディショナ(水冷式地中熱タイプE)","パッケージエアコンディショナ(水冷式地中熱タイプF)"],
    "流量制御方式": ["無","定流量制御","回転数制御"],               
    "空調機タイプ": ["空調機","FCU","送風機","室内機","全熱交ユニット","放熱器","天井放射冷暖房パネル"],
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

def convert_window_frame_type(frame_type_webpro):
    """
    WEBPROの「建具の種類」からBuilelibの「建具の種類」に変換する関数
    """

    if frame_type_webpro == "木製(単板ガラス)":
        frame_type = "木製"
        layer_type = "単層"
    elif frame_type_webpro == "木製(複層ガラス)":
        frame_type = "木製"
        layer_type = "複層"
    elif frame_type_webpro == "樹脂製(単板ガラス)":
        frame_type = "樹脂製"
        layer_type = "単層"
    elif frame_type_webpro == "樹脂製(複層ガラス)" or frame_type_webpro == "樹脂":
        frame_type = "樹脂製"
        layer_type = "複層"
    elif frame_type_webpro == "金属木複合製(単板ガラス)":
        frame_type = "金属木複合製"
        layer_type = "単層"
    elif frame_type_webpro == "金属木複合製(複層ガラス)":
        frame_type = "金属木複合製"
        layer_type = "複層"
    elif frame_type_webpro == "金属樹脂複合製(単板ガラス)":
        frame_type = "金属樹脂複合製"
        layer_type = "単層"
    elif frame_type_webpro == "金属樹脂複合製(複層ガラス)" or frame_type_webpro == "アルミ樹脂複合":
        frame_type = "金属樹脂複合製"
        layer_type = "複層"
    elif frame_type_webpro == "金属製(単板ガラス)":
        frame_type = "金属製"
        layer_type = "単層"
    elif frame_type_webpro == "金属製(複層ガラス)" or frame_type_webpro == "アルミ":
        frame_type = "金属製"
        layer_type = "複層"
    else:
        frame_type = None
        layer_type = None


    return frame_type, layer_type


# 検証結果メッセージ （global変数）
validation = {}


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
    
    elif (required == False) and (input_data == "") and (default == None) and (data_type == "数値"):

        input_data = None

    elif (required == False) and (input_data == "") and (default == None) and (data_type == "文字列"):

        input_data = None

    elif (required == False) and (input_data == "") and (default == "") and (data_type == "文字列"):

        input_data = ""

    elif (required == False) and (input_data == "") and (default == "無") and (data_type == "文字列"):

        input_data = "無"

    elif (required == False) and (input_data == "") and (default == 0) and (data_type == "数値"):

        input_data = 0

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
                if input_data < float(lower_limit):
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

    global validation
    validation = {
        "error": [],
        "warning": []
    }

    # if "validation" in locals():
    #     print("localsにあります")
    #     print(validation)
    # if "validation" in globals():
    #     print("globalsにあります")
    #     print(validation)
    
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

    global validation
    validation = {
        "error": [],
        "warning": []
    }

    # if "validation" in locals():
    #     print("localsにあります")
    #     print(validation)
    # if "validation" in globals():
    #     print("globalsにあります")
    #     print(validation)

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


    #----------------------------------
    # 様式0 基本情報入力シート の読み込み
    #----------------------------------
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


    #----------------------------------
    # 様式1 室仕様入力シート の読み込み
    # （ Builelibでは、各設備のシートに記載された建物用途・室用途は使わず、様式1の情報を使う ）
    #----------------------------------
    if "1) 室仕様" in wb.sheet_names():

        # シートの読み込み
        sheet_BL = wb.sheet_by_name("1) 室仕様")
        # 初期化
        roomKey = None

        # シート名称
        sheet_BL_name = sheet_BL.row_values(0)[0]

        # 行のループ
        for i in range(10,sheet_BL.nrows):

            # シートから「行」の読み込み
            dataBL = sheet_BL.row_values(i)

            # 階と室名が空欄でない場合
            if (dataBL[0] != "") and (dataBL[1] != ""):

                # 数値で入力された室名を文字列に変換
                if sheet_BL.cell_type(i,1) == xlrd.XL_CELL_NUMBER:
                    dataBL[1] = str(int(sheet_BL.cell_value(i,1)))

                # 階＋室をkeyとする
                roomKey = str(dataBL[0]) + '_' + str(dataBL[1])

                if roomKey in data["Rooms"]:

                    validation["error"].append( "様式1.室仕様:「①階・室名」の組み合わせに重複があります（"+ str(i+1) +"行目「"+ roomKey +"」）。")

                else:

                    # 主たる建物用途
                    mainbuildingType = dataBL[2]

                    if sheet_BL_name[-5:] == "Rev.2":  # 2024年4月以降のシート（室用途が2列に分離）

                        buildingType = str(dataBL[3])
                        roomType = str(dataBL[4])

                    else:

                        # 建物用途
                        buildingType = str(dataBL[2])
                        roomType = str(dataBL[3])                            

                        # 2022.10更新のWebプログラムに対応（建物用途-室用途）
                        if "-" in roomType:
                            buildingType = roomType.split("-")[0]
                            roomType = roomType.split("-")[1]

                    # 建物用途の読み替え
                    if buildingType == "百貨店等":
                        buildingType = "物販店舗等"
                        validation["warning"].append( "様式1.室仕様 "+ str(i+1) +"行目: 建物用途「百貨店等」を「物販店舗等」に置き換えました。")

                    # 室用途の読み替え
                    if roomType == "ゴミ置場等":
                        roomType = "廃棄物保管場所等"
                        validation["warning"].append( "様式1.室仕様 "+ str(i+1) +"行目: 室用途「ゴミ置場等」を「廃棄物保管場所等」に置き換えました。")


                    # 建物用途のチェック
                    buildingType = check_value(buildingType, "様式1.室仕様 "+ str(i+1) +"行目:「②建物用途」", True, None, "文字列", input_options["建物用途"], None, None)
                    
                    # 室用途のチェック
                    if buildingType in  input_options["室用途"]:
                        roomType = check_value(roomType, "様式1.室仕様 "+ str(i+1) +"行目:「②室用途」", True, None, "文字列", input_options["室用途"][buildingType], None, None)
                    else:
                        validation["warning"].append( "様式1.室仕様 "+ str(i+1) +"行目:「②室用途」の整合性チェックができませんでした。")


                    if sheet_BL_name[-5:] == "Rev.2":  # 2024年4月以降のシート（室用途が2列に分離）

                        # ゾーンはないと想定。
                        data["Rooms"][roomKey] = {
                                "mainbuildingType": mainbuildingType,
                                "buildingType": buildingType,  
                                "roomType": roomType,
                                "floorHeight": 
                                    check_value(dataBL[5+1], "様式1.室仕様 "+ str(i+1) +"行目:「④階高」", False, None, "数値", None, 0, None),
                                "ceilingHeight":
                                    check_value(dataBL[6+1], "様式1.室仕様 "+ str(i+1) +"行目:「⑤天井高」", False, None, "数値", None, 0, None),
                                "roomArea":
                                    check_value(dataBL[4+1], "様式1.室仕様 "+ str(i+1) +"行目:「③室面積」", True, None, "数値", None, 0, None),
                                "zone": None,
                                "modelBuildingType":
                                    check_value(dataBL[11+1], "様式1.室仕様 "+ str(i+1) +"行目:「⑦モデル建物」", False, None, "文字列", None, None, None),
                                "buildingGroup": None,
                                "Info": 
                                    check_value(dataBL[12+1], "様式1.室仕様 "+ str(i+1) +"行目:「⑧備考」", False, None, "文字列", None, None, None),
                        }

                    else:

                        # ゾーンはないと想定。
                        data["Rooms"][roomKey] = {
                                "mainbuildingType": mainbuildingType,
                                "buildingType": buildingType,  
                                "roomType": roomType,
                                "floorHeight": 
                                    check_value(dataBL[5], "様式1.室仕様 "+ str(i+1) +"行目:「④階高」", False, None, "数値", None, 0, None),
                                "ceilingHeight":
                                    check_value(dataBL[6], "様式1.室仕様 "+ str(i+1) +"行目:「⑤天井高」", False, None, "数値", None, 0, None),
                                "roomArea":
                                    check_value(dataBL[4], "様式1.室仕様 "+ str(i+1) +"行目:「③室面積」", True, None, "数値", None, 0, None),
                                "zone": None,
                                "modelBuildingType":
                                    check_value(dataBL[11], "様式1.室仕様 "+ str(i+1) +"行目:「⑦モデル建物」", False, None, "文字列", None, None, None),
                                "buildingGroup": None,
                                "Info": 
                                    check_value(dataBL[12], "様式1.室仕様 "+ str(i+1) +"行目:「⑧備考」", False, None, "文字列", None, None, None),
                        }


    #----------------------------------
    # 様式2-1 空調ゾーン入力シート の読み込み
    #----------------------------------
    if "2-1) 空調ゾーン" in wb.sheet_names():
        
        # シートの読み込み
        sheet_AC1 = wb.sheet_by_name("2-1) 空調ゾーン")
        # 初期化
        roomKey = None

        # 行のループ
        for i in range(10,sheet_AC1.nrows):

            # シートから「行」の読み込み
            dataAC1 = sheet_AC1.row_values(i)

            # 数値で入力された室名を文字列に変換
            if sheet_AC1.cell_type(i,8) == xlrd.XL_CELL_NUMBER:
                dataAC1[8] = str(int(sheet_AC1.cell_value(i,8)))

            # 階と室名が空欄でない場合
            if (dataAC1[7] != "") and (dataAC1[8] != ""):

                # 階＋室+ゾーン名をkeyとする
                roomKey = str(dataAC1[7]) + '_' + str(dataAC1[8])

                if roomKey in data["AirConditioningZone"]:

                    validation["error"].append( "様式2-1.空調ゾーン:「②階・空調ゾーン名」の組み合わせに重複があります（"+ str(i+1) +"行目「"+ roomKey +"」）。")

                elif roomKey not in data["Rooms"]:

                    validation["error"].append( "様式2-1.空調ゾーン:「②空調ゾーン」が 様式1.室仕様入力シートで定義されてません。" +
                        "Builelibでは「①室の仕様」と「②空調ゾーン」の内容を等しくしてください（"+ str(i+1) +"行目「"+ roomKey +"」）。") 

                else:

                    AHU_insideLoad  = check_value(dataAC1[9], "様式2-1.空調ゾーン "+ str(i+1) +"行目:「③空調機群名称（室負荷）」", True, None, "文字列", None, None, None)
                    AHU_outdoorLoad = check_value(dataAC1[10], "様式2-1.空調ゾーン "+ str(i+1) +"行目:「④空調機群名称（外気負荷）」", True, None, "文字列", None, None, None)

                    # 冷暖同時供給については、暫定で「無」を入れておく。後に再度判定。
                    data["AirConditioningZone"][roomKey] = {
                        "isNatualVentilation": "無",
                        "isSimultaneousSupply": "無",
                        "AHU_cooling_insideLoad": AHU_insideLoad,
                        "AHU_cooling_outdoorLoad": AHU_outdoorLoad,
                        "AHU_heating_insideLoad": AHU_insideLoad,
                        "AHU_heating_outdoorLoad": AHU_outdoorLoad,
                        "Info":
                            check_value(dataAC1[11], "様式2-1.空調ゾーン "+ str(i+1) +"行目:「⑤備考」", False, None, "文字列", None, None, None),
                    }


    #----------------------------------
    # 様式2-2 外壁構成入力シート の読み込み
    #----------------------------------
    if "2-2) 外壁構成 " in wb.sheet_names():

        # シートの読み込み
        sheet_BE2 = wb.sheet_by_name("2-2) 外壁構成 ")
        # 初期化
        eltKey = None
        inputMethod = None

        # シート名称
        sheet_BE2_name = sheet_BE2.row_values(0)[0]

        # 行のループ
        for i in range(10,sheet_BE2.nrows):

            # シートから「行」の読み込み
            dataBE2 = sheet_BE2.row_values(i)

            # 断熱仕様名称が空欄でない場合
            if (dataBE2[0] != ""):

                # 断熱仕様名称をkeyとする（上書き）
                eltKey = check_value(dataBE2[0], "様式2-2.外壁構成 "+ str(i+1) +"行目:「①外壁名称」", True, None, "文字列", None, 0, None)

                if eltKey in data["WallConfigure"]:

                    validation["error"].append( "様式2-2.外壁構成:「①外壁名称」に重複があります（"+ str(i+1) +"行目「"+ eltKey +"」）。")

                else:
                
                    # 外壁の種類(WEBPRO)
                    walltype_webpro = check_value(dataBE2[1], "様式2-2.外壁構成 "+ str(i+1) +"行目:「②壁の種類」", True, None, "文字列", input_options["外壁の種類(WEBPRO)"], None, None)

                    # 日射吸収率(2024年4月 日射吸収率が入力可能に)
                    if sheet_BE2_name[-5:] == "Rev.2":
                        solarAbsorptionRatio = check_value(dataBE2[7], "様式2-2.外壁構成 "+ str(i+1) +"行目:「⑧日射吸収率」", False, None, "数値", None, 0, None)
                    else:
                        solarAbsorptionRatio = None

                    # 入力方法を識別
                    if dataBE2[2] != "":
                        inputMethod = "熱貫流率を入力"
                    else:
                        inputMethod = "建材構成を入力"
                    
                    if inputMethod == "熱貫流率を入力":

                        if sheet_BE2_name[-5:] == "Rev.2": 

                            data["WallConfigure"][eltKey] = {
                                    "wall_type_webpro": walltype_webpro,
                                    "structureType": "その他",
                                    "solarAbsorptionRatio": solarAbsorptionRatio,
                                    "inputMethod": inputMethod,
                                    "Uvalue":
                                        check_value(dataBE2[2], "様式2-2.外壁構成 "+ str(i+1) +"行目:「③熱貫流率」", True, None, "数値", None, 0, None),
                                    "Info":
                                        check_value(dataBE2[8], "様式2-2.外壁構成 "+ str(i+1) +"行目:「⑨備考」", False, None, "文字列", None, None, None),
                                }
                        
                        else:

                            data["WallConfigure"][eltKey] = {
                                    "wall_type_webpro": walltype_webpro,
                                    "structureType": "その他",
                                    "solarAbsorptionRatio": solarAbsorptionRatio,
                                    "inputMethod": inputMethod,
                                    "Uvalue":
                                        check_value(dataBE2[2], "様式2-2.外壁構成 "+ str(i+1) +"行目:「③熱貫流率」", True, None, "数値", None, 0, None),
                                    "Info":
                                        check_value(dataBE2[6], "様式2-2.外壁構成 "+ str(i+1) +"行目:「⑦備考」", False, None, "文字列", None, None, None),
                                }

                    elif inputMethod == "建材構成を入力":

                        # 次の行を読み込み
                        dataBE2 = sheet_BE2.row_values(i+1)

                        if sheet_BE2_name[-5:] == "Rev.2": 

                            if (dataBE2[4] != "") or (dataBE2[5] != ""):

                                material_name = dataBE2[4].replace(' ', '')

                                if material_name == "吹付け硬質ウレタンフォームＡ種1":
                                    dataBE2[4] = "吹付け硬質ウレタンフォームA種1"
                                elif material_name == "吹付け硬質ウレタンフォームＡ種3":
                                    dataBE2[4] = "吹付け硬質ウレタンフォームA種3"

                                data["WallConfigure"][eltKey] = {
                                        "wall_type_webpro": walltype_webpro,
                                        "structureType": "その他",
                                        "solarAbsorptionRatio": solarAbsorptionRatio,
                                        "inputMethod": inputMethod,
                                        "layers": [
                                            {
                                            "materialID": 
                                                check_value(material_name, "様式2-2.外壁構成 "+ str(i+1) +"行目:「⑤建材名称」", False, None, "文字列", None, None, None),
                                            "conductivity":
                                                check_value(dataBE2[5], "様式2-2.外壁構成 "+ str(i+1) +"行目:「⑥厚み」", False, None, "数値", None, 0, None),
                                            "thickness":
                                                check_value(dataBE2[6], "様式2-2.外壁構成 "+ str(i+1) +"行目:「⑦厚み」", False, None, "数値", None, 0, None),
                                            "Info":
                                                check_value(dataBE2[8], "様式2-2.外壁構成 "+ str(i+1) +"行目:「⑨備考」", False, None, "文字列", None, None, None),
                                            }
                                        ]
                                    }

                            else:
                                
                                # 1行目が空白の場合
                                data["WallConfigure"][eltKey] = {
                                        "wall_type_webpro": walltype_webpro,
                                        "structureType": "その他",
                                        "solarAbsorptionRatio": solarAbsorptionRatio,
                                        "inputMethod": inputMethod,
                                        "layers": [
                                        ]
                                    }

                            for loop in range(2,10):

                                # 次の行を読み込み
                                dataBE2 = sheet_BE2.row_values(i+loop)
                                
                                if (dataBE2[4] != "") or (dataBE2[5] != ""):

                                    material_name = dataBE2[4].replace(' ', '')

                                    if dataBE2[4].replace(' ', '') == "吹付け硬質ウレタンフォームＡ種1":
                                        dataBE2[4] = "吹付け硬質ウレタンフォームA種1"
                                    elif dataBE2[4].replace(' ', '') == "吹付け硬質ウレタンフォームＡ種3":
                                        dataBE2[4] = "吹付け硬質ウレタンフォームA種3"
                                        
                                    data["WallConfigure"][eltKey]["layers"].append(
                                        {
                                            "materialID": 
                                                check_value(material_name, "様式2-2.外壁構成 "+ str(i+1) +"行目:「⑤建材名称」", False, None, "文字列", None, None, None),
                                            "conductivity":
                                                check_value(dataBE2[5], "様式2-2.外壁構成 "+ str(i+1) +"行目:「⑥厚み」", False, None, "数値", None, 0, None),
                                            "thickness":
                                                check_value(dataBE2[6], "様式2-2.外壁構成 "+ str(i+1) +"行目:「⑦厚み」", False, None, "数値", None, 0, None),
                                            "Info":
                                                check_value(dataBE2[8], "様式2-2.外壁構成 "+ str(i+1) +"行目:「⑨備考」", False, None, "文字列", None, None, None),
                                        }
                                    )


                        else:

                            if dataBE2[4] != "":

                                material_name = dataBE2[4].replace(' ', '')

                                if material_name == "吹付け硬質ウレタンフォームＡ種1":
                                    dataBE2[4] = "吹付け硬質ウレタンフォームA種1"
                                elif material_name == "吹付け硬質ウレタンフォームＡ種3":
                                    dataBE2[4] = "吹付け硬質ウレタンフォームA種3"

                                data["WallConfigure"][eltKey] = {
                                        "wall_type_webpro": walltype_webpro,
                                        "structureType": "その他",
                                        "solarAbsorptionRatio": solarAbsorptionRatio,
                                        "inputMethod": inputMethod,
                                        "layers": [
                                            {
                                            "materialID": 
                                                check_value(material_name, "様式2-2.外壁構成 "+ str(i+1) +"行目:「⑤建材名称」", False, None, "文字列", None, None, None),
                                            "conductivity": None,
                                            "thickness":
                                                check_value(dataBE2[5], "様式2-2.外壁構成 "+ str(i+1) +"行目:「⑥厚み」", False, None, "数値", None, 0, None),
                                            "Info":
                                                check_value(dataBE2[6], "様式2-2.外壁構成 "+ str(i+1) +"行目:「⑦備考」", False, None, "文字列", None, None, None),
                                            }
                                        ]
                                    }

                            else:
                                
                                # 1行目が空白の場合
                                data["WallConfigure"][eltKey] = {
                                        "wall_type_webpro": walltype_webpro,
                                        "structureType": "その他",
                                        "solarAbsorptionRatio": solarAbsorptionRatio,
                                        "inputMethod": inputMethod,
                                        "layers": [
                                        ]
                                    }

                            for loop in range(2,10):

                                # 次の行を読み込み
                                dataBE2 = sheet_BE2.row_values(i+loop)
                                
                                if dataBE2[4] != "":

                                    material_name = dataBE2[4].replace(' ', '')

                                    if dataBE2[4].replace(' ', '') == "吹付け硬質ウレタンフォームＡ種1":
                                        dataBE2[4] = "吹付け硬質ウレタンフォームA種1"
                                    elif dataBE2[4].replace(' ', '') == "吹付け硬質ウレタンフォームＡ種3":
                                        dataBE2[4] = "吹付け硬質ウレタンフォームA種3"
                                        
                                    data["WallConfigure"][eltKey]["layers"].append(
                                        {
                                            "materialID": 
                                                check_value(material_name, "様式2-2.外壁構成 "+ str(i+1) +"行目:「⑤建材名称」", False, None, "文字列", None, None, None),
                                            "conductivity": None,
                                            "thickness":
                                                check_value(dataBE2[5], "様式2-2.外壁構成 "+ str(i+1) +"行目:「⑥厚み」", False, None, "数値", None, 0, None),
                                            "Info":
                                                check_value(dataBE2[6], "様式2-2.外壁構成 "+ str(i+1) +"行目:「⑦備考」", False, None, "文字列", None, None, None),
                                        }
                                    )


    #----------------------------------
    # 様式2-3 窓仕様入力シート の読み込み
    #----------------------------------
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
                eltKey = check_value(dataBE3[0], "様式2-3.窓仕様 "+ str(i+1) +"行目:「①開口部名称」", True, None, "文字列", None, 0, None)

                if eltKey in data["WindowConfigure"]:

                    validation["error"].append( "様式2-3.窓仕様:「①開口部名称」に重複があります（"+ str(i+1) +"行目「"+ eltKey +"」）。")

                else:

                    # 入力方法を識別
                    if (dataBE3[1] != "") and (dataBE3[2] != ""):
                        inputMethod = "性能値を入力"
                    elif (dataBE3[5] != "") and (dataBE3[6] != ""):
                        inputMethod = "ガラスの性能を入力"
                    elif (dataBE3[4] != ""):
                        inputMethod = "ガラスの種類を入力"
                    else:
                        validation["error"].append( "様式2-3.窓仕様 "+ str(i+1) +"行目: 入力が不正です。")

                    if inputMethod == "性能値を入力":

                        data["WindowConfigure"][eltKey] = {
                                "windowArea": 1,
                                "windowWidth": None,
                                "windowHeight": None,
                                "inputMethod": inputMethod,
                                "windowUvalue": 
                                    check_value(dataBE3[1], "様式2-3.窓仕様 "+ str(i+1) +"行目:「②窓の熱貫流率」", True, None, "数値", None, 0, None),
                                "windowIvalue":
                                    check_value(dataBE3[2], "様式2-3.窓仕様 "+ str(i+1) +"行目:「③窓の日射熱取得率」", True, None, "数値", None, 0, None),
                                "layerType": "単層",
                                "glassUvalue":
                                    check_value(dataBE3[5], "様式2-3.窓仕様 "+ str(i+1) +"行目:「⑥ガラスの熱貫流率」", False, None, "数値", None, 0, None),
                                "glassIvalue":
                                    check_value(dataBE3[6], "様式2-3.窓仕様 "+ str(i+1) +"行目:「⑦ガラスの日射熱取得率」", False, None, "数値", None, 0, None),
                                "Info":
                                    check_value(dataBE3[7], "様式2-3.窓仕様 "+ str(i+1) +"行目:「⑧備考」", False, None, "文字列", None, None, None),
                            }

                    elif inputMethod == "ガラスの性能を入力":

                        frame_type_webpro = check_value(dataBE3[3], "様式2-3.窓仕様 "+ str(i+1) +"行目:「④建具の種類」", True, None, "文字列", input_options["建具の種類"], None, None)
                        frameType, layer_type = convert_window_frame_type(frame_type_webpro)

                        data["WindowConfigure"][eltKey] = {
                                "windowArea": 1,
                                "windowWidth": None,
                                "windowHeight": None,
                                "inputMethod": inputMethod,
                                "frameType": frameType,
                                "layerType": layer_type,
                                "glassUvalue":
                                    check_value(dataBE3[5], "様式2-3.窓仕様 "+ str(i+1) +"行目:「⑥ガラスの熱貫流率」", True, None, "数値", None, 0, None),
                                "glassIvalue":
                                    check_value(dataBE3[6], "様式2-3.窓仕様 "+ str(i+1) +"行目:「⑦ガラスの日射熱取得率」", True, None, "数値", None, 0, None),
                                "Info":
                                    check_value(dataBE3[7], "様式2-3.窓仕様 "+ str(i+1) +"行目:「⑧備考」", False, None, "文字列", None, None, None),
                            }

                    elif inputMethod == "ガラスの種類を入力":

                        frame_type_webpro = check_value(dataBE3[3], "様式2-3.窓仕様 "+ str(i+1) +"行目:「④建具の種類」", True, None, "文字列", input_options["建具の種類"], None, None)
                        frame_type, layer_type = convert_window_frame_type(frame_type_webpro)
                            
                        data["WindowConfigure"][eltKey] = {
                                "windowArea": 1,
                                "windowWidth": None,
                                "windowHeight": None,
                                "inputMethod": inputMethod,
                                "frameType": frame_type,
                                "glassID":
                                    check_value(dataBE3[4], "様式2-3.窓仕様 "+ str(i+1) +"行目:「⑤ガラスの種類」", True, None, "文字列", input_options["ガラスの種類"], None, None),
                                "Info":
                                    check_value(dataBE3[7], "様式2-3.窓仕様 "+ str(i+1) +"行目:「⑧備考」", False, None, "文字列", None, None, None),
                            }

                    else:
                        validation["error"].append( "様式2-3.窓仕様 "+ str(i+1) +"行目: 入力が不正です。")


    #----------------------------------
    # 様式2-4 外皮入力シート の読み込み
    # （ Builelibでは、窓面積 を窓の枚数と読み替える。 ）
    #----------------------------------
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

            # 数値で入力された室名を文字列に変換
            if sheet_BE1.cell_type(i,1) == xlrd.XL_CELL_NUMBER:
                dataBE1[1] = str(int(sheet_BE1.cell_value(i,1)))
                
            # 階と室名が空欄でない場合
            if (dataBE1[0] != "") and (dataBE1[1] != ""):

                # 階＋室＋ゾーン名をkeyとする（上書き）
                roomKey = str(dataBE1[0]) + '_' + str(dataBE1[1])

                if roomKey in data["EnvelopeSet"]:

                    validation["error"].append( "様式2-4.外皮:「①空調ゾーン名称」に重複があります（"+ str(i+1) +"行目「"+ roomKey +"」）。")
                
                elif roomKey not in data["AirConditioningZone"]:

                    validation["error"].append( "様式2-4.外皮:「①空調ゾーン名称」が 様式2-1.空調ゾーン入力シートで定義されてません。（"+ str(i+1) +"行目「"+ roomKey +"」）。")

                else:

                    # 外壁の種類の判定（Ver.2のみ）
                    if str(dataBE1[2]) == "日陰":
                        dataBE1[2] = "北"
                        wallType = "日の当たらない外壁"
                        validation["warning"].append( "様式2-4.外皮 "+ str(i+1) +"行目: 方位「日陰」を「北（日の当たらない外壁）」に置き換えました。")
                    elif str(dataBE1[2]) == "水平":
                        dataBE1[2] = "水平（下）"
                        wallType = "日の当たる外壁"
                        validation["warning"].append( "様式2-4.外皮 "+ str(i+1) +"行目: 方位「水平」を「水平（下）」に置き換えました。")
                    else:
                        wallType = "日の当たる外壁"

                    # 日よけ効果係数
                    if dataBE1[3] != "" and dataBE1[4] != "":
                        EavesID = "庇" + str(int(evaes_num))
                        evaes_num += 1

                        data["ShadingConfigure"][EavesID] = {
                            "shadingEffect_C":
                                check_value(dataBE1[3], "様式2-4.外皮 "+ str(i+1) +"行目:「③日よけ効果係数（冷房）」", False, None, "数値", None, 0, 1),
                            "shadingEffect_H":
                                check_value(dataBE1[4], "様式2-4.外皮 "+ str(i+1) +"行目:「③日よけ効果係数（暖房）」", False, None, "数値", None, 0, 1),
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
                                    "Direction":
                                        check_value(dataBE1[2], "様式2-4.外皮 "+ str(i+1) +"行目:「②方位」", True, None, "文字列", input_options["方位"], None, None),
                                    "EnvelopeArea":
                                        check_value(dataBE1[6], "様式2-4.外皮 "+ str(i+1) +"行目:「⑤外皮面積（窓含）」", True, None, "数値", None, 0, None),
                                    "EnvelopeWidth": None,
                                    "EnvelopeHeight": None,
                                    "WallSpec":
                                        check_value(dataBE1[5], "様式2-4.外皮 "+ str(i+1) +"行目:「④外壁名称」", True, None, "文字列", data["WallConfigure"], None, None),  
                                    "WallType": wallType,
                                    "WindowList":[
                                        {
                                            "WindowID":
                                                check_value(dataBE1[7], "様式2-4.外皮 "+ str(i+1) +"行目:「⑥開口部名称」", False, "無", "文字列", data["WindowConfigure"], None, None),  
                                            "WindowNumber":
                                                check_value(dataBE1[8], "様式2-4.外皮 "+ str(i+1) +"行目:「⑦窓面積」", False, None, "数値", None, 0, None),
                                            "isBlind":
                                                check_value(dataBE1[9], "様式2-4.外皮 "+ str(i+1) +"行目:「⑧ブラインドの有無」", False, "無", "文字列", input_options["有無"], None, None),
                                            "EavesID": EavesID,
                                            "Info":
                                                check_value(dataBE1[10], "様式2-4.外皮 "+ str(i+1) +"行目:「⑨備考」", False, None, "文字列", None, None, None),
                                        }
                                    ]       
                                }
                            ],
                        }

            else: # 階と室名が空欄である場合

                if (dataBE1[2] == "") and (roomKey in data["EnvelopeSet"]):  # 方位が空白である場合 →　日よけ効果係数と窓のみ読み込む

                    if (dataBE1[5] != ""): # もし方位が空白で外壁名称に入力があったらエラー 
                        dataBE1[5] = "無"
                        validation["error"].append( "様式2-4.外皮 "+ str(i+1) +"行目: 「④外壁名称」が入力されている行は「②方位」の入力が必須です。")

                    # 日よけ効果係数
                    if dataBE1[3] != "" and dataBE1[4] != "":
                        EavesID = "庇" + str(int(evaes_num))
                        evaes_num += 1

                        data["ShadingConfigure"][EavesID] = {
                            "shadingEffect_C":
                                check_value(dataBE1[3], "様式2-4.外皮 "+ str(i+1) +"行目:「③日よけ効果係数（冷房）」", False, None, "数値", None, 0, 1),
                            "shadingEffect_H":
                                check_value(dataBE1[4], "様式2-4.外皮 "+ str(i+1) +"行目:「③日よけ効果係数（暖房）」", False, None, "数値", None, 0, 1),
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
                    
                    if (dataBE1[7] != ""):
                        
                        data["EnvelopeSet"][roomKey]["WallList"][-1]["WindowList"].append(
                            {
                                "WindowID":
                                    check_value(dataBE1[7], "様式2-4.外皮 "+ str(i+1) +"行目:「⑥開口部名称」", False, "無", "文字列", data["WindowConfigure"], None, None),  
                                "WindowNumber":
                                    check_value(dataBE1[8], "様式2-4.外皮 "+ str(i+1) +"行目:「⑦窓面積」", False, None, "数値", None, 0, None),
                                "isBlind":
                                    check_value(dataBE1[9], "様式2-4.外皮 "+ str(i+1) +"行目:「⑧ブラインドの有無」", False, "無", "文字列", input_options["有無"], None, None),
                                "EavesID": EavesID,
                                "Info":
                                    check_value(dataBE1[10], "様式2-4.外皮 "+ str(i+1) +"行目:「⑨備考」", False, None, "文字列", None, None, None),
                            }
                        )

                elif roomKey in data["EnvelopeSet"]: # 方位が空白ではない場合。

                    # 外壁の種類の判定（Ver.2のみ）
                    if str(dataBE1[2]) == "日陰":
                        dataBE1[2] = "北"
                        wallType = "日の当たらない外壁"
                        validation["warning"].append( "様式2-4.外皮 "+ str(i+1) +"行目: 方位「日陰」を「北（日の当たらない外壁）」に置き換えました。")
                    elif str(dataBE1[2]) == "水平":
                        dataBE1[2] = "水平（下）"
                        wallType = "日の当たる外壁"
                        validation["warning"].append( "様式2-4.外皮 "+ str(i+1) +"行目: 方位「水平」を「水平（下）」に置き換えました。")
                    else:
                        wallType = "日の当たる外壁"

                    # 日よけ効果係数
                    if dataBE1[3] != "" and dataBE1[4] != "":
                        EavesID = "庇" + str(int(evaes_num))
                        evaes_num += 1

                        data["ShadingConfigure"][EavesID] = {
                            "shadingEffect_C":
                                check_value(dataBE1[3], "様式2-4.外皮 "+ str(i+1) +"行目:「③日よけ効果係数（冷房）」", False, None, "数値", None, 0, 1),
                            "shadingEffect_H":
                                check_value(dataBE1[4], "様式2-4.外皮 "+ str(i+1) +"行目:「③日よけ効果係数（暖房）」", False, None, "数値", None, 0, 1),
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
                            "Direction":
                                check_value(dataBE1[2], "様式2-4.外皮 "+ str(i+1) +"行目:「②方位」", True, None, "文字列", input_options["方位"], None, None),
                            "EnvelopeArea":
                                check_value(dataBE1[6], "様式2-4.外皮 "+ str(i+1) +"行目:「⑤外皮面積（窓含）」", True, None, "数値", None, 0, None),
                            "EnvelopeWidth": None,
                            "EnvelopeHeight": None,
                            "WallSpec":
                                check_value(dataBE1[5], "様式2-4.外皮 "+ str(i+1) +"行目:「④外壁名称」", True, None, "文字列", data["WallConfigure"], None, None),  
                            "WallType": wallType,
                            "WindowList":[
                                {
                                    "WindowID":
                                        check_value(dataBE1[7], "様式2-4.外皮 "+ str(i+1) +"行目:「⑥開口部名称」", False, "無", "文字列", data["WindowConfigure"], None, None),  
                                    "WindowNumber":
                                        check_value(dataBE1[8], "様式2-4.外皮 "+ str(i+1) +"行目:「⑦窓面積」", False, None, "数値", None, 0, None),
                                    "isBlind":
                                        check_value(dataBE1[9], "様式2-4.外皮 "+ str(i+1) +"行目:「⑧ブラインドの有無」", False, "無", "文字列", input_options["有無"], None, None),
                                    "EavesID": EavesID,
                                    "Info":
                                        check_value(dataBE1[10], "様式2-4.外皮 "+ str(i+1) +"行目:「⑨備考」", False, None, "文字列", None, None, None),
                                }
                            ]       
                        }
                    )



    ## 接地壁の扱い（様式2-2 → 様式2-4）
    for eltKey in data["WallConfigure"]:
        if data["WallConfigure"][eltKey]["wall_type_webpro"] == "接地壁":
            for room_name in data["EnvelopeSet"]:
                for wall_id, wall_conf in enumerate(data["EnvelopeSet"][room_name]["WallList"]):
                    if wall_conf["WallSpec"] == eltKey:
                        data["EnvelopeSet"][room_name]["WallList"][wall_id]["WallType"] = "地盤に接する外壁"


    #----------------------------------
    # 様式2-5 熱源入力シート の読み込み
    #----------------------------------
    if "2-5) 熱源" in wb.sheet_names():
        
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
                
                unitKey = check_value(dataAC2[0], "様式2-5.熱源 "+ str(i+1) +"行目:「①熱源群名称」", True, None, "文字列", None, None, None)
                
                if unitKey in data["HeatsourceSystem"]:

                    validation["error"].append( "様式2-5.熱源:「①熱源群名称」に重複があります（"+ str(i+1) +"行目「"+ unitKey +"」）。")

                else:

                    # 冷暖同時供給の有無
                    if dataAC2[1] == "有":
                        isSimultaneous_flag = "有"
                    else:
                        isSimultaneous_flag = "無"

                    # 台数制御の有無
                    if dataAC2[2] == "有":
                        staging_control_flag = "有"
                    else:
                        staging_control_flag = "無"

                    # 熱源群名称が入力されている箇所は、蓄熱有無を判定する。
                    if dataAC2[3] == "氷蓄熱" or dataAC2[3] == "水蓄熱(成層型)" or dataAC2[3] == "水蓄熱(混合型)":
                        storage_flag = True
                        oikake_flag  = False
                    elif dataAC2[3] == "追掛":
                        storage_flag = False
                        oikake_flag  = True
                    else:
                        storage_flag = False
                        oikake_flag  = False

                    if storage_flag:
                        modeKey_C = "冷房(蓄熱)"
                        modeKey_H = "暖房(蓄熱)"
                        StorageType = check_value(dataAC2[3], "様式2-5.熱源 "+ str(i+1) +"行目:「④蓄熱システム（運転モード）」", True, None, "文字列", input_options["蓄熱の種類"], None, None)
                        StorageSize = check_value(dataAC2[4], "様式2-5.熱源 "+ str(i+1) +"行目:「⑤蓄熱システム（蓄熱容量）」", True, None, "数値", None, 0, None)                           
                    else:
                        modeKey_C = "冷房"
                        modeKey_H = "暖房"
                        StorageType = None
                        StorageSize = None


                    if (dataAC2[5] != ""): # 熱源機種名称が入力されている。 

                        # 熱源機種
                        HeatsourceType = check_value(dataAC2[5], "様式2-5.熱源 "+ str(i+1) +"行目:「⑥熱源機種」", True, None, "文字列", input_options["熱源機種"], None, None)

                        if (dataAC2[6] != "") and (HeatsourceType in HeatSourcePerformance): # 冷熱源がある。

                            if HeatSourcePerformance[HeatsourceType]["冷房時の特性"]["燃料種類"] == "電力":    # 燃料種類が電力であれば
                                HeatsourceRatedPowerConsumption = \
                                    check_value(dataAC2[10], "様式2-5.熱源 "+ str(i+1) +"行目:「⑪主機定格消費エネルギー」", False, 0, "数値", None, None, None)
                                Heatsource_sub_RatedPowerConsumption = \
                                    check_value(dataAC2[11], "様式2-5.熱源 "+ str(i+1) +"行目:「⑫補機定格消費電力」", False, 0, "数値", None, None, None)
                                HeatsourceRatedFuelConsumption  = 0
                            else:
                                HeatsourceRatedPowerConsumption = 0
                                Heatsource_sub_RatedPowerConsumption = \
                                    check_value(dataAC2[11], "様式2-5.熱源 "+ str(i+1) +"行目:「⑫補機定格消費電力」", False, 0, "数値", None, None, None)
                                HeatsourceRatedFuelConsumption = \
                                    check_value(dataAC2[10], "様式2-5.熱源 "+ str(i+1) +"行目:「⑪主機定格消費エネルギー」", False, 0, "数値", None, None, None)

                            unit_spec = {
                                    "StorageType": StorageType,
                                    "StorageSize": StorageSize,
                                    "isStagingControl": staging_control_flag,
                                    "isSimultaneous_for_ver2" : isSimultaneous_flag,
                                    "Heatsource" :[
                                        {
                                            "HeatsourceType": HeatsourceType,
                                            "Number":
                                                check_value(dataAC2[7], "様式2-5.熱源 "+ str(i+1) +"行目:「⑧台数」", True, None, "数値", None, None, None),
                                            "SupplyWaterTempSummer": 
                                                check_value(dataAC2[8], "様式2-5.熱源 "+ str(i+1) +"行目:「⑨送水温度」", False, None, "数値", None, None, None),
                                            "SupplyWaterTempMiddle":
                                                check_value(dataAC2[8], "様式2-5.熱源 "+ str(i+1) +"行目:「⑨送水温度」", False, None, "数値", None, None, None),
                                            "SupplyWaterTempWinter":
                                                check_value(dataAC2[8], "様式2-5.熱源 "+ str(i+1) +"行目:「⑨送水温度」", False, None, "数値", None, None, None),
                                            "HeatsourceRatedCapacity":
                                                check_value(dataAC2[9], "様式2-5.熱源 "+ str(i+1) +"行目:「⑩定格冷却能力」", True, None, "数値", None, None, None),
                                            "HeatsourceRatedPowerConsumption": HeatsourceRatedPowerConsumption,
                                            "HeatsourceRatedFuelConsumption": HeatsourceRatedFuelConsumption,
                                            "Heatsource_sub_RatedPowerConsumption": Heatsource_sub_RatedPowerConsumption,
                                            "PrimaryPumpPowerConsumption":
                                                check_value(dataAC2[12], "様式2-5.熱源 "+ str(i+1) +"行目:「⑬一次ポンプ定格消費電力」", False, 0, "数値", None, None, None),
                                            "PrimaryPumpContolType": "無",
                                            "CoolingTowerCapacity":
                                                check_value(dataAC2[13], "様式2-5.熱源 "+ str(i+1) +"行目:「⑭冷却塔定格冷却能力」", False, 0, "数値", None, None, None),
                                            "CoolingTowerFanPowerConsumption":
                                                check_value(dataAC2[14], "様式2-5.熱源 "+ str(i+1) +"行目:「⑮冷却塔ファン消費電力」", False, 0, "数値", None, None, None),
                                            "CoolingTowerPumpPowerConsumption":
                                                check_value(dataAC2[15], "様式2-5.熱源 "+ str(i+1) +"行目:「⑮冷却水ポンプ消費電力」", False, 0, "数値", None, None, None),
                                            "CoolingTowerContolType": "無",
                                            "Info":
                                                check_value(dataAC2[23], "様式2-5.熱源 "+ str(i+1) +"行目:「⑰備考」", False, None, "文字列", None, None, None),
                                        }
                                    ]
                                }

                            if unitKey in data["HeatsourceSystem"]:
                                data["HeatsourceSystem"][unitKey][modeKey_C] = unit_spec
                            else:
                                data["HeatsourceSystem"][unitKey] = {modeKey_C : unit_spec}

                        elif (HeatsourceType in HeatSourcePerformance):

                            # 熱源機器がない場合は、群の情報のみを入力する。
                            unit_spec = {
                                    "StorageType": StorageType,
                                    "StorageSize": StorageSize,
                                    "isStagingControl": staging_control_flag,
                                    "isSimultaneous_for_ver2" : isSimultaneous_flag,
                                    "Heatsource" :[],
                                }
                            if unitKey in data["HeatsourceSystem"]:
                                data["HeatsourceSystem"][unitKey][modeKey_C] = unit_spec
                            else:
                                data["HeatsourceSystem"][unitKey] = {modeKey_C : unit_spec}


                        if (dataAC2[16] != "") and (HeatsourceType in HeatSourcePerformance):     # 温熱源がある。
                            
                            if HeatSourcePerformance[HeatsourceType]["暖房時の特性"]["燃料種類"] == "電力":    # 燃料種類が電力であれば
                                HeatsourceRatedPowerConsumption = \
                                    check_value(dataAC2[20], "様式2-5.熱源 "+ str(i+1) +"行目:「⑪主機定格消費エネルギー」", False, 0, "数値", None, None, None)
                                Heatsource_sub_RatedPowerConsumption = \
                                    check_value(dataAC2[21], "様式2-5.熱源 "+ str(i+1) +"行目:「⑫補機定格消費電力」", False, 0, "数値", None, None, None)
                                HeatsourceRatedFuelConsumption  = 0
                            else:
                                HeatsourceRatedPowerConsumption = 0
                                Heatsource_sub_RatedPowerConsumption = \
                                    check_value(dataAC2[21], "様式2-5.熱源 "+ str(i+1) +"行目:「⑫補機定格消費電力」", False, 0, "数値", None, None, None)
                                HeatsourceRatedFuelConsumption  = \
                                    check_value(dataAC2[20], "様式2-5.熱源 "+ str(i+1) +"行目:「⑪主機定格消費エネルギー」", False, 0, "数値", None, None, None)
                                                                    

                            unit_spec =  {
                                "StorageType": StorageType,
                                "StorageSize": StorageSize,
                                "isStagingControl": staging_control_flag,
                                "isSimultaneous_for_ver2" : isSimultaneous_flag,
                                "Heatsource" :[
                                    {
                                        "HeatsourceType": HeatsourceType,
                                        "Number":
                                            check_value(dataAC2[17], "様式2-5.熱源 "+ str(i+1) +"行目:「⑧台数」", True, None, "数値", None, None, None),
                                        "SupplyWaterTempSummer":
                                            check_value(dataAC2[18], "様式2-5.熱源 "+ str(i+1) +"行目:「⑨送水温度」", False, None, "数値", None, None, None),
                                        "SupplyWaterTempMiddle":
                                            check_value(dataAC2[18], "様式2-5.熱源 "+ str(i+1) +"行目:「⑨送水温度」", False, None, "数値", None, None, None),
                                        "SupplyWaterTempWinter":
                                            check_value(dataAC2[18], "様式2-5.熱源 "+ str(i+1) +"行目:「⑨送水温度」", False, None, "数値", None, None, None),
                                        "HeatsourceRatedCapacity":
                                            check_value(dataAC2[19], "様式2-5.熱源 "+ str(i+1) +"行目:「⑩定格冷却能力」", True, None, "数値", None, None, None),
                                        "HeatsourceRatedPowerConsumption": HeatsourceRatedPowerConsumption,
                                        "HeatsourceRatedFuelConsumption": HeatsourceRatedFuelConsumption,
                                        "Heatsource_sub_RatedPowerConsumption": Heatsource_sub_RatedPowerConsumption,
                                        "PrimaryPumpPowerConsumption":
                                            check_value(dataAC2[22], "様式2-5.熱源 "+ str(i+1) +"行目:「⑬一次ポンプ定格消費電力」", False, 0, "数値", None, None, None),
                                        "PrimaryPumpContolType": "無",
                                        "CoolingTowerCapacity": 0,
                                        "CoolingTowerFanPowerConsumption": 0,
                                        "CoolingTowerPumpPowerConsumption": 0,
                                        "CoolingTowerContolType": "無",
                                        "Info":
                                            check_value(dataAC2[23], "様式2-5.熱源 "+ str(i+1) +"行目:「⑰備考」", False, None, "文字列", None, None, None),
                                    }
                                ]
                            }

                            if unitKey in data["HeatsourceSystem"]:
                                data["HeatsourceSystem"][unitKey][modeKey_H] = unit_spec
                            else:
                                data["HeatsourceSystem"][unitKey] = {modeKey_H : unit_spec}

                        elif (HeatsourceType in HeatSourcePerformance):

                            # 熱源機器がない場合は、群の情報のみを入力する。
                            unit_spec = {
                                    "StorageType": StorageType,
                                    "StorageSize": StorageSize,
                                    "isStagingControl": staging_control_flag,
                                    "isSimultaneous_for_ver2" : isSimultaneous_flag,
                                    "Heatsource" :[],
                                }
                            if unitKey in data["HeatsourceSystem"]:
                                data["HeatsourceSystem"][unitKey][modeKey_H] = unit_spec
                            else:
                                data["HeatsourceSystem"][unitKey] = {modeKey_H : unit_spec}
                            

            elif (dataAC2[3] == "") or (dataAC2[3] == data["HeatsourceSystem"][unitKey][modeKey_C]["StorageType"] ) \
                or (dataAC2[3] == "追掛" and oikake_flag ) :  # 蓄熱運転モードが「空欄」もしくは「前行と同じ」である場合 → 熱源機種を追加（複数台設置）

                if (dataAC2[5] != ""): # 熱源機種名称が入力されている。 

                    # 熱源機種
                    HeatsourceType = check_value(dataAC2[5], "様式2-5.熱源 "+ str(i+1) +"行目:「⑥熱源機種」", True, None, "文字列", input_options["熱源機種"], None, None)

                    if (dataAC2[6] != "") and (HeatsourceType in HeatSourcePerformance): # 冷熱源がある。

                        if HeatSourcePerformance[HeatsourceType]["冷房時の特性"]["燃料種類"] == "電力":    # 燃料種類が電力であれば
                            HeatsourceRatedPowerConsumption = \
                                check_value(dataAC2[10], "様式2-5.熱源 "+ str(i+1) +"行目:「⑪主機定格消費エネルギー」", False, 0, "数値", None, None, None)
                            Heatsource_sub_RatedPowerConsumption = \
                                check_value(dataAC2[11], "様式2-5.熱源 "+ str(i+1) +"行目:「⑫補機定格消費電力」", False, 0, "数値", None, None, None)
                            HeatsourceRatedFuelConsumption  = 0
                        else:
                            HeatsourceRatedPowerConsumption = 0
                            Heatsource_sub_RatedPowerConsumption = \
                                check_value(dataAC2[11], "様式2-5.熱源 "+ str(i+1) +"行目:「⑫補機定格消費電力」", False, 0, "数値", None, None, None)
                            HeatsourceRatedFuelConsumption = \
                                check_value(dataAC2[10], "様式2-5.熱源 "+ str(i+1) +"行目:「⑪主機定格消費エネルギー」", False, 0, "数値", None, None, None)


                        data["HeatsourceSystem"][unitKey][modeKey_C]["Heatsource"].append(
                            {
                                "HeatsourceType": HeatsourceType,
                                "Number":
                                    check_value(dataAC2[7], "様式2-5.熱源 "+ str(i+1) +"行目:「⑧台数」", True, None, "数値", None, None, None),
                                "SupplyWaterTempSummer": 
                                    check_value(dataAC2[8], "様式2-5.熱源 "+ str(i+1) +"行目:「⑨送水温度」", False, None, "数値", None, None, None),
                                "SupplyWaterTempMiddle":
                                    check_value(dataAC2[8], "様式2-5.熱源 "+ str(i+1) +"行目:「⑨送水温度」", False, None, "数値", None, None, None),
                                "SupplyWaterTempWinter":
                                    check_value(dataAC2[8], "様式2-5.熱源 "+ str(i+1) +"行目:「⑨送水温度」", False, None, "数値", None, None, None),
                                "HeatsourceRatedCapacity":
                                    check_value(dataAC2[9], "様式2-5.熱源 "+ str(i+1) +"行目:「⑩定格冷却能力」", True, None, "数値", None, None, None),
                                "HeatsourceRatedPowerConsumption": HeatsourceRatedPowerConsumption,
                                "HeatsourceRatedFuelConsumption": HeatsourceRatedFuelConsumption,
                                "Heatsource_sub_RatedPowerConsumption": Heatsource_sub_RatedPowerConsumption,
                                "PrimaryPumpPowerConsumption":
                                    check_value(dataAC2[12], "様式2-5.熱源 "+ str(i+1) +"行目:「⑬一次ポンプ定格消費電力」", False, 0, "数値", None, None, None),
                                "PrimaryPumpContolType": "無",
                                "CoolingTowerCapacity":
                                    check_value(dataAC2[13], "様式2-5.熱源 "+ str(i+1) +"行目:「⑭冷却塔定格冷却能力」", False, 0, "数値", None, None, None),
                                "CoolingTowerFanPowerConsumption":
                                    check_value(dataAC2[14], "様式2-5.熱源 "+ str(i+1) +"行目:「⑮冷却塔ファン消費電力」", False, 0, "数値", None, None, None),
                                "CoolingTowerPumpPowerConsumption":
                                    check_value(dataAC2[15], "様式2-5.熱源 "+ str(i+1) +"行目:「⑮冷却水ポンプ消費電力」", False, 0, "数値", None, None, None),
                                "CoolingTowerContolType": "無",
                                "Info":
                                    check_value(dataAC2[23], "様式2-5.熱源 "+ str(i+1) +"行目:「⑰備考」", False, None, "文字列", None, None, None),
                            }
                        )

                    if (dataAC2[16] != "") and (HeatsourceType in HeatSourcePerformance):     # 温熱源がある。
                        
                        if HeatSourcePerformance[HeatsourceType]["暖房時の特性"]["燃料種類"] == "電力":    # 燃料種類が電力であれば
                            HeatsourceRatedPowerConsumption = \
                                check_value(dataAC2[20], "様式2-5.熱源 "+ str(i+1) +"行目:「⑪主機定格消費エネルギー」", False, 0, "数値", None, None, None)
                            Heatsource_sub_RatedPowerConsumption = \
                                check_value(dataAC2[21], "様式2-5.熱源 "+ str(i+1) +"行目:「⑫補機定格消費電力」", False, 0, "数値", None, None, None)
                            HeatsourceRatedFuelConsumption  = 0
                        else:
                            HeatsourceRatedPowerConsumption = 0
                            Heatsource_sub_RatedPowerConsumption = \
                                check_value(dataAC2[21], "様式2-5.熱源 "+ str(i+1) +"行目:「⑫補機定格消費電力」", False, 0, "数値", None, None, None)
                            HeatsourceRatedFuelConsumption  = \
                                check_value(dataAC2[20], "様式2-5.熱源 "+ str(i+1) +"行目:「⑪主機定格消費エネルギー」", False, 0, "数値", None, None, None)
                                                                

                        data["HeatsourceSystem"][unitKey][modeKey_H]["Heatsource"].append(
                            {
                                "HeatsourceType": HeatsourceType,
                                "Number":
                                    check_value(dataAC2[17], "様式2-5.熱源 "+ str(i+1) +"行目:「⑧台数」", True, None, "数値", None, None, None),
                                "SupplyWaterTempSummer":
                                    check_value(dataAC2[18], "様式2-5.熱源 "+ str(i+1) +"行目:「⑨送水温度」", False, None, "数値", None, None, None),
                                "SupplyWaterTempMiddle":
                                    check_value(dataAC2[18], "様式2-5.熱源 "+ str(i+1) +"行目:「⑨送水温度」", False, None, "数値", None, None, None),
                                "SupplyWaterTempWinter":
                                    check_value(dataAC2[18], "様式2-5.熱源 "+ str(i+1) +"行目:「⑨送水温度」", False, None, "数値", None, None, None),
                                "HeatsourceRatedCapacity":
                                    check_value(dataAC2[19], "様式2-5.熱源 "+ str(i+1) +"行目:「⑩定格冷却能力」", True, None, "数値", None, None, None),
                                "HeatsourceRatedPowerConsumption": HeatsourceRatedPowerConsumption,
                                "HeatsourceRatedFuelConsumption": HeatsourceRatedFuelConsumption,
                                "Heatsource_sub_RatedPowerConsumption": Heatsource_sub_RatedPowerConsumption,
                                "PrimaryPumpPowerConsumption":
                                    check_value(dataAC2[22], "様式2-5.熱源 "+ str(i+1) +"行目:「⑬一次ポンプ定格消費電力」", False, 0, "数値", None, None, None),
                                "PrimaryPumpContolType": "無",
                                "CoolingTowerCapacity": 0,
                                "CoolingTowerFanPowerConsumption": 0,
                                "CoolingTowerPumpPowerConsumption": 0,
                                "CoolingTowerContolType": "無",
                                "Info":
                                    check_value(dataAC2[23], "様式2-5.熱源 "+ str(i+1) +"行目:「⑰備考」", False, None, "文字列", None, None, None),
                            }
                        )

            elif (dataAC2[3] != ""):  # 熱源機種を追加（複数のモードがある場合）

                # 熱源群名称が入力されている箇所は、蓄熱有無を判定する。
                if dataAC2[3] == "氷蓄熱" or dataAC2[3] == "水蓄熱(成層型)" or dataAC2[3] == "水蓄熱(混合型)":
                    storage_flag = True
                    oikake_flag  = False
                elif dataAC2[3] == "追掛":
                    storage_flag = False
                    oikake_flag  = True
                else:
                    storage_flag = False
                    oikake_flag  = False
                    
                if storage_flag:
                    modeKey_C = "冷房(蓄熱)"
                    modeKey_H = "暖房(蓄熱)"
                    StorageType = check_value(dataAC2[3], "様式2-5.熱源 "+ str(i+1) +"行目:「④蓄熱システム（運転モード）」", True, None, "文字列", input_options["蓄熱の種類"], None, None)
                    StorageSize = check_value(dataAC2[4], "様式2-5.熱源 "+ str(i+1) +"行目:「⑤蓄熱システム（蓄熱容量）」", True, None, "数値", None, 0, None)                           
                else:
                    modeKey_C = "冷房"
                    modeKey_H = "暖房"
                    StorageType = None
            
                if (dataAC2[5] != ""): # 熱源機種名称が入力されている。 

                    # 熱源機種
                    HeatsourceType = check_value(dataAC2[5], "様式2-5.熱源 "+ str(i+1) +"行目:「⑥熱源機種」", True, None, "文字列", input_options["熱源機種"], None, None)

                    if (dataAC2[6] != "") and (HeatsourceType in HeatSourcePerformance): # 冷熱源がある。

                        if HeatSourcePerformance[HeatsourceType]["冷房時の特性"]["燃料種類"] == "電力":    # 燃料種類が電力であれば
                            HeatsourceRatedPowerConsumption = \
                                check_value(dataAC2[10], "様式2-5.熱源 "+ str(i+1) +"行目:「⑪主機定格消費エネルギー」", False, 0, "数値", None, None, None)
                            Heatsource_sub_RatedPowerConsumption = \
                                check_value(dataAC2[11], "様式2-5.熱源 "+ str(i+1) +"行目:「⑫補機定格消費電力」", False, 0, "数値", None, None, None)
                            HeatsourceRatedFuelConsumption  = 0
                        else:
                            HeatsourceRatedPowerConsumption = 0
                            Heatsource_sub_RatedPowerConsumption = \
                                check_value(dataAC2[11], "様式2-5.熱源 "+ str(i+1) +"行目:「⑫補機定格消費電力」", False, 0, "数値", None, None, None)
                            HeatsourceRatedFuelConsumption = \
                                check_value(dataAC2[10], "様式2-5.熱源 "+ str(i+1) +"行目:「⑪主機定格消費エネルギー」", False, 0, "数値", None, None, None)

                        unit_spec = {
                                "StorageType": StorageType,
                                "StorageSize": StorageSize,
                                "isStagingControl": staging_control_flag,
                                "isSimultaneous_for_ver2" : isSimultaneous_flag,
                                "Heatsource" :[
                                    {
                                        "HeatsourceType": HeatsourceType,
                                        "Number":
                                            check_value(dataAC2[7], "様式2-5.熱源 "+ str(i+1) +"行目:「⑧台数」", True, None, "数値", None, None, None),
                                        "SupplyWaterTempSummer": 
                                            check_value(dataAC2[8], "様式2-5.熱源 "+ str(i+1) +"行目:「⑨送水温度」", False, None, "数値", None, None, None),
                                        "SupplyWaterTempMiddle":
                                            check_value(dataAC2[8], "様式2-5.熱源 "+ str(i+1) +"行目:「⑨送水温度」", False, None, "数値", None, None, None),
                                        "SupplyWaterTempWinter":
                                            check_value(dataAC2[8], "様式2-5.熱源 "+ str(i+1) +"行目:「⑨送水温度」", False, None, "数値", None, None, None),
                                        "HeatsourceRatedCapacity":
                                            check_value(dataAC2[9], "様式2-5.熱源 "+ str(i+1) +"行目:「⑩定格冷却能力」", True, None, "数値", None, None, None),
                                        "HeatsourceRatedPowerConsumption": HeatsourceRatedPowerConsumption,
                                        "HeatsourceRatedFuelConsumption": HeatsourceRatedFuelConsumption,
                                        "Heatsource_sub_RatedPowerConsumption": Heatsource_sub_RatedPowerConsumption,
                                        "PrimaryPumpPowerConsumption":
                                            check_value(dataAC2[12], "様式2-5.熱源 "+ str(i+1) +"行目:「⑬一次ポンプ定格消費電力」", False, 0, "数値", None, None, None),
                                        "PrimaryPumpContolType": "無",
                                        "CoolingTowerCapacity":
                                            check_value(dataAC2[13], "様式2-5.熱源 "+ str(i+1) +"行目:「⑭冷却塔定格冷却能力」", False, 0, "数値", None, None, None),
                                        "CoolingTowerFanPowerConsumption":
                                            check_value(dataAC2[14], "様式2-5.熱源 "+ str(i+1) +"行目:「⑮冷却塔ファン消費電力」", False, 0, "数値", None, None, None),
                                        "CoolingTowerPumpPowerConsumption":
                                            check_value(dataAC2[15], "様式2-5.熱源 "+ str(i+1) +"行目:「⑮冷却水ポンプ消費電力」", False, 0, "数値", None, None, None),
                                        "CoolingTowerContolType": "無",
                                        "Info":
                                            check_value(dataAC2[23], "様式2-5.熱源 "+ str(i+1) +"行目:「⑰備考」", False, None, "文字列", None, None, None),
                                    }
                                ]
                            }

                        if unitKey in data["HeatsourceSystem"]:
                            data["HeatsourceSystem"][unitKey][modeKey_C] = unit_spec
                        else:
                            data["HeatsourceSystem"][unitKey] = {modeKey_C : unit_spec}

                    elif (HeatsourceType in HeatSourcePerformance):

                        # 熱源機器がない場合は、群の情報のみを入力する。
                        unit_spec = {
                                "StorageType": StorageType,
                                "StorageSize": StorageSize,
                                "isStagingControl": staging_control_flag,
                                "isSimultaneous_for_ver2" : isSimultaneous_flag,
                                "Heatsource" :[],
                            }
                        if unitKey in data["HeatsourceSystem"]:
                            data["HeatsourceSystem"][unitKey][modeKey_C] = unit_spec
                        else:
                            data["HeatsourceSystem"][unitKey] = {modeKey_C : unit_spec}


                    if (dataAC2[16] != "") and (HeatsourceType in HeatSourcePerformance):     # 温熱源がある。
                        
                        if HeatSourcePerformance[HeatsourceType]["暖房時の特性"]["燃料種類"] == "電力":    # 燃料種類が電力であれば
                            HeatsourceRatedPowerConsumption = \
                                check_value(dataAC2[20], "様式2-5.熱源 "+ str(i+1) +"行目:「⑪主機定格消費エネルギー」", False, 0, "数値", None, None, None)
                            Heatsource_sub_RatedPowerConsumption = \
                                check_value(dataAC2[21], "様式2-5.熱源 "+ str(i+1) +"行目:「⑫補機定格消費電力」", False, 0, "数値", None, None, None)
                            HeatsourceRatedFuelConsumption  = 0
                        else:
                            HeatsourceRatedPowerConsumption = 0
                            Heatsource_sub_RatedPowerConsumption = \
                                check_value(dataAC2[21], "様式2-5.熱源 "+ str(i+1) +"行目:「⑫補機定格消費電力」", False, 0, "数値", None, None, None)
                            HeatsourceRatedFuelConsumption  = \
                                check_value(dataAC2[20], "様式2-5.熱源 "+ str(i+1) +"行目:「⑪主機定格消費エネルギー」", False, 0, "数値", None, None, None)
                                                                

                        unit_spec =  {
                            "StorageType": StorageType,
                            "StorageSize": StorageSize,
                            "isStagingControl": staging_control_flag,
                            "isSimultaneous_for_ver2" : isSimultaneous_flag,
                            "Heatsource" :[
                                {
                                    "HeatsourceType": HeatsourceType,
                                    "Number":
                                        check_value(dataAC2[17], "様式2-5.熱源 "+ str(i+1) +"行目:「⑧台数」", True, None, "数値", None, None, None),
                                    "SupplyWaterTempSummer":
                                        check_value(dataAC2[18], "様式2-5.熱源 "+ str(i+1) +"行目:「⑨送水温度」", False, None, "数値", None, None, None),
                                    "SupplyWaterTempMiddle":
                                        check_value(dataAC2[18], "様式2-5.熱源 "+ str(i+1) +"行目:「⑨送水温度」", False, None, "数値", None, None, None),
                                    "SupplyWaterTempWinter":
                                        check_value(dataAC2[18], "様式2-5.熱源 "+ str(i+1) +"行目:「⑨送水温度」", False, None, "数値", None, None, None),
                                    "HeatsourceRatedCapacity":
                                        check_value(dataAC2[19], "様式2-5.熱源 "+ str(i+1) +"行目:「⑩定格冷却能力」", True, None, "数値", None, None, None),
                                    "HeatsourceRatedPowerConsumption": HeatsourceRatedPowerConsumption,
                                    "HeatsourceRatedFuelConsumption": HeatsourceRatedFuelConsumption,
                                    "Heatsource_sub_RatedPowerConsumption": Heatsource_sub_RatedPowerConsumption,
                                    "PrimaryPumpPowerConsumption":
                                        check_value(dataAC2[22], "様式2-5.熱源 "+ str(i+1) +"行目:「⑬一次ポンプ定格消費電力」", False, 0, "数値", None, None, None),
                                    "PrimaryPumpContolType": "無",
                                    "CoolingTowerCapacity": 0,
                                    "CoolingTowerFanPowerConsumption": 0,
                                    "CoolingTowerPumpPowerConsumption": 0,
                                    "CoolingTowerContolType": "無",
                                    "Info":
                                        check_value(dataAC2[23], "様式2-5.熱源 "+ str(i+1) +"行目:「⑰備考」", False, None, "文字列", None, None, None),
                                }
                            ]
                        }

                        if unitKey in data["HeatsourceSystem"]:
                            data["HeatsourceSystem"][unitKey][modeKey_H] = unit_spec
                        else:
                            data["HeatsourceSystem"][unitKey] = {modeKey_H : unit_spec}

                    elif (HeatsourceType in HeatSourcePerformance):

                        # 熱源機器がない場合は、群の情報のみを入力する。
                        unit_spec = {
                                "StorageType": StorageType,
                                "StorageSize": StorageSize,
                                "isStagingControl": staging_control_flag,
                                "isSimultaneous_for_ver2" : isSimultaneous_flag,
                                "Heatsource" :[],
                            }
                        if unitKey in data["HeatsourceSystem"]:
                            data["HeatsourceSystem"][unitKey][modeKey_H] = unit_spec
                        else:
                            data["HeatsourceSystem"][unitKey] = {modeKey_H : unit_spec}


    #----------------------------------
    # 様式2-6 二次ポンプ入力シート の読み込み
    #----------------------------------
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
                
                unitKey = check_value(dataAC3[0], "様式2-6.二次ポンプ "+ str(i+1) +"行目:「①二次ポンプ群名称」", True, None, "文字列", None, None, None)

                if unitKey in data["SecondaryPumpSystem"]:

                    validation["error"].append( "様式2-6.二次ポンプ:「①二次ポンプ群名称」に重複があります（"+ str(i+1) +"行目「"+ unitKey +"」）。")

                else:

                    if dataAC3[2] != "":

                        modeKey = "冷房"

                        unit_spec = {
                                "TemperatureDifference":
                                    check_value(dataAC3[2], "様式2-6.二次ポンプ "+ str(i+1) +"行目:「③冷房時温度差」", True, None, "数値", None, 0, None),
                                "isStagingControl": 
                                    check_value(dataAC3[1], "様式2-6.二次ポンプ "+ str(i+1) +"行目:「②台数制御の有無」", False, "無", "文字列", input_options["有無"], None, None),
                                "SecondaryPump" :[
                                    {
                                        "Number" :
                                            check_value(dataAC3[5], "様式2-6.二次ポンプ "+ str(i+1) +"行目:「⑤台数」", True, None, "数値", None, 0, None),
                                        "RatedWaterFlowRate":
                                            check_value(dataAC3[6], "様式2-6.二次ポンプ "+ str(i+1) +"行目:「⑥定格流量」", True, None, "数値", None, 0, None),
                                        "RatedPowerConsumption":
                                            check_value(dataAC3[7], "様式2-6.二次ポンプ "+ str(i+1) +"行目:「⑦定格消費電力」", True, None, "数値", None, 0, None),
                                        "ContolType":
                                            check_value(dataAC3[8], "様式2-6.二次ポンプ "+ str(i+1) +"行目:「⑧流量制御方式」", False, "無", "文字列", input_options["流量制御方式"], None, None),
                                        "MinOpeningRate":
                                            check_value(dataAC3[9], "様式2-6.二次ポンプ "+ str(i+1) +"行目:「⑨変流量時最小流量比」", False, None, "数値", None, 0, 100),
                                        "Info":                                        
                                            check_value(dataAC3[10], "様式2-6.二次ポンプ "+ str(i+1) +"行目:「⑩備考」", False, None, "文字列", None, None, None),
                                    }
                                ]
                            }

                        if unitKey in data["SecondaryPumpSystem"]:
                            data["SecondaryPumpSystem"][unitKey][modeKey] = unit_spec
                        else:
                            data["SecondaryPumpSystem"][unitKey] = { modeKey : unit_spec }
                
                    if dataAC3[3] != "":

                        modeKey = "暖房"

                        unit_spec = {
                                "TemperatureDifference":
                                    check_value(dataAC3[3], "様式2-6.二次ポンプ "+ str(i+1) +"行目:「③暖房時温度差」", True, None, "数値", None, 0, None),
                                "isStagingControl": 
                                    check_value(dataAC3[1], "様式2-6.二次ポンプ "+ str(i+1) +"行目:「②台数制御の有無」", False, "無", "文字列", input_options["有無"], None, None),
                                "SecondaryPump" :[
                                    {
                                        "Number" :
                                            check_value(dataAC3[5], "様式2-6.二次ポンプ "+ str(i+1) +"行目:「⑤台数」", True, None, "数値", None, 0, None),
                                        "RatedWaterFlowRate":
                                            check_value(dataAC3[6], "様式2-6.二次ポンプ "+ str(i+1) +"行目:「⑥定格流量」", True, None, "数値", None, 0, None),
                                        "RatedPowerConsumption":
                                            check_value(dataAC3[7], "様式2-6.二次ポンプ "+ str(i+1) +"行目:「⑦定格消費電力」", True, None, "数値", None, 0, None),
                                        "ContolType":
                                            check_value(dataAC3[8], "様式2-6.二次ポンプ "+ str(i+1) +"行目:「⑧流量制御方式」", False, "無", "文字列", input_options["流量制御方式"], None, None),
                                        "MinOpeningRate":
                                            check_value(dataAC3[9], "様式2-6.二次ポンプ "+ str(i+1) +"行目:「⑨変流量時最小流量比」", False, None, "数値", None, 0, 100),
                                        "Info":                                        
                                            check_value(dataAC3[10], "様式2-6.二次ポンプ "+ str(i+1) +"行目:「⑩備考」", False, None, "文字列", None, None, None),
                                    }
                                ]
                            }

                        if unitKey in data["SecondaryPumpSystem"]:
                            data["SecondaryPumpSystem"][unitKey][modeKey] = unit_spec
                        else:
                            data["SecondaryPumpSystem"][unitKey] = { modeKey : unit_spec }
                            

            elif (dataAC3[0] == "") and (dataAC3[4] != "") and (unitKey in data["SecondaryPumpSystem"]):

                if "冷房" in data["SecondaryPumpSystem"][unitKey]:

                    data["SecondaryPumpSystem"][unitKey]["冷房"]["SecondaryPump"].append(
                        {
                            "Number" :
                                check_value(dataAC3[5], "様式2-6.二次ポンプ "+ str(i+1) +"行目:「⑤台数」", True, None, "数値", None, 0, None),
                            "RatedWaterFlowRate":
                                check_value(dataAC3[6], "様式2-6.二次ポンプ "+ str(i+1) +"行目:「⑥定格流量」", True, None, "数値", None, 0, None),
                            "RatedPowerConsumption":
                                check_value(dataAC3[7], "様式2-6.二次ポンプ "+ str(i+1) +"行目:「⑦定格消費電力」", True, None, "数値", None, 0, None),
                            "ContolType":
                                check_value(dataAC3[8], "様式2-6.二次ポンプ "+ str(i+1) +"行目:「⑧流量制御方式」", False, "無", "文字列", input_options["流量制御方式"], None, None),
                            "MinOpeningRate":
                                check_value(dataAC3[9], "様式2-6.二次ポンプ "+ str(i+1) +"行目:「⑨変流量時最小流量比」", False, None, "数値", None, 0, 100),
                            "Info":                                        
                                check_value(dataAC3[10], "様式2-6.二次ポンプ "+ str(i+1) +"行目:「⑩備考」", False, None, "文字列", None, None, None),
                        }
                    )

                if "暖房" in data["SecondaryPumpSystem"][unitKey]:

                    data["SecondaryPumpSystem"][unitKey]["暖房"]["SecondaryPump"].append(
                        {
                            "Number" :
                                check_value(dataAC3[5], "様式2-6.二次ポンプ "+ str(i+1) +"行目:「⑤台数」", True, None, "数値", None, 0, None),
                            "RatedWaterFlowRate":
                                check_value(dataAC3[6], "様式2-6.二次ポンプ "+ str(i+1) +"行目:「⑥定格流量」", True, None, "数値", None, 0, None),
                            "RatedPowerConsumption":
                                check_value(dataAC3[7], "様式2-6.二次ポンプ "+ str(i+1) +"行目:「⑦定格消費電力」", True, None, "数値", None, 0, None),
                            "ContolType":
                                check_value(dataAC3[8], "様式2-6.二次ポンプ "+ str(i+1) +"行目:「⑧流量制御方式」", False, "無", "文字列", input_options["流量制御方式"], None, None),
                            "MinOpeningRate":
                                check_value(dataAC3[9], "様式2-6.二次ポンプ "+ str(i+1) +"行目:「⑨変流量時最小流量比」", False, None, "数値", None, 0, 100),
                            "Info":                                        
                                check_value(dataAC3[10], "様式2-6.二次ポンプ "+ str(i+1) +"行目:「⑩備考」", False, None, "文字列", None, None, None),
                        }
                    )
    
    
    #----------------------------------
    # 様式2-7 空調機入力シート の読み込み
    #----------------------------------
    
    if "2-7) 空調機" in wb.sheet_names():
        
        # シートの読み込み
        sheet_AC4 = wb.sheet_by_name("2-7) 空調機")
        # 初期化
        unitKey = None

        # シート名称
        sheet_AC4_name = sheet_AC4.row_values(0)[0]

        # 行のループ
        for i in range(10,sheet_AC4.nrows):

            # シートから「行」の読み込み
            dataAC4 = sheet_AC4.row_values(i)

            # 空調機群名称が空欄でない場合
            if (dataAC4[0] != ""):      
                
                unitKey = check_value(dataAC4[0], "様式2-7.空調機 "+ str(i+1) +"行目:「①空調機群名称」", True, None, "文字列", None, None, None)
                
                if unitKey in data["AirHandlingSystem"]:

                    validation["error"].append( "様式2-7.空調機:「①空調機群名称」に重複があります（"+ str(i+1) +"行目「"+ unitKey +"」）。")

                else:

                    E_fan1 = check_value(dataAC4[6], "様式2-7.空調機 "+ str(i+1) +"行目:「⑦送風機定格消費電力（給気）」", False, 0, "数値", None, 0, None)
                    E_fan2 = check_value(dataAC4[7], "様式2-7.空調機 "+ str(i+1) +"行目:「⑧送風機定格消費電力（還気）」", False, 0, "数値", None, 0, None)
                    E_fan3 = check_value(dataAC4[8], "様式2-7.空調機 "+ str(i+1) +"行目:「⑨送風機定格消費電力（外気）」", False, 0, "数値", None, 0, None)
                    E_fan4 = check_value(dataAC4[9], "様式2-7.空調機 "+ str(i+1) +"行目:「⑩送風機定格消費電力（排気）」", False, 0, "数値", None, 0, None)

                    if sheet_AC4_name[-5:] == "Rev.2":      # 2024年4月 全熱交換器の列が追加

                        if dataAC4[14] == "全熱交換器あり・様式2-9記載あり":
                            validation["error"].append( "様式2-7.空調機:「⑮全熱交換器の有無」の選択肢が「全熱交換器あり・様式2-9記載あり」である場合は計算ができません。")

                        data["AirHandlingSystem"][unitKey] = {
                            "isEconomizer": 
                                check_value(dataAC4[13], "様式2-7.空調機 "+ str(i+1) +"行目:「⑭外気冷房の有無」", False, "無", "文字列", input_options["有無"], None, None), 
                            "EconomizerMaxAirVolume":
                                check_value(dataAC4[5], "様式2-7.空調機 "+ str(i+1) +"行目:「⑥設計最大外気風量」", False, None, "数値", None, None, None), 
                            "isOutdoorAirCut":
                                check_value(dataAC4[12], "様式2-7.空調機 "+ str(i+1) +"行目:「⑬予熱時外気取り入れ停止の有無」", False, "無", "文字列", input_options["有無"], None, None),
                            "Pump_cooling": 
                                check_value(dataAC4[21], "様式2-7.空調機 "+ str(i+1) +"行目:「㉒二次ポンプ群名称（冷熱）」", False, None, "文字列", data["SecondaryPumpSystem"], None, None),
                            "Pump_heating":
                                check_value(dataAC4[22], "様式2-7.空調機 "+ str(i+1) +"行目:「㉓二次ポンプ群名称（温熱）」", False, None, "文字列", data["SecondaryPumpSystem"], None, None),
                            "HeatSource_cooling":
                                check_value(dataAC4[23], "様式2-7.空調機 "+ str(i+1) +"行目:「㉔熱源群名称（冷熱）」", False, None, "文字列", data["HeatsourceSystem"], None, None),
                            "HeatSource_heating":
                                check_value(dataAC4[24], "様式2-7.空調機 "+ str(i+1) +"行目:「㉕熱源群名称（温熱）」", False, None, "文字列", data["HeatsourceSystem"], None, None),
                            "AirHandlingUnit" :[
                                {
                                    "Type":
                                        check_value(dataAC4[2], "様式2-7.空調機 "+ str(i+1) +"行目:「③空調機タイプ」", True, None, "文字列", input_options["空調機タイプ"], None, None), 
                                    "Number":
                                        check_value(dataAC4[1], "様式2-7.空調機 "+ str(i+1) +"行目:「②台数」", True, None, "数値", None, None, None), 
                                    "RatedCapacityCooling":
                                        check_value(dataAC4[3], "様式2-7.空調機 "+ str(i+1) +"行目:「④定格冷却能力」", False, None, "数値", None, None, None),                                 
                                    "RatedCapacityHeating":
                                        check_value(dataAC4[4], "様式2-7.空調機 "+ str(i+1) +"行目:「⑤定格加熱能力」", False, None, "数値", None, None, None), 
                                    "FanType": None,
                                    "FanAirVolume":
                                        check_value(dataAC4[16], "様式2-7.空調機 "+ str(i+1) +"行目:「⑰全熱交換器の設計風量」", False, None, "数値", None, None, None),    
                                    "FanPowerConsumption": E_fan1+E_fan2+E_fan3+E_fan4,
                                    "FanControlType":
                                        check_value(dataAC4[10], "様式2-7.空調機 "+ str(i+1) +"行目:「⑪風量制御方式」", False, "無", "文字列", input_options["風量制御方式"], None, None),
                                    "FanMinOpeningRate":
                                        check_value(dataAC4[11], "様式2-7.空調機 "+ str(i+1) +"行目:「⑫変風量時最小風量比」", False, None, "数値", None, 0, 100),                                   
                                    "AirHeatExchangeRatioCooling":
                                        check_value(dataAC4[17], "様式2-7.空調機 "+ str(i+1) +"行目:「⑱全熱交換効率（冷房時）」", False, None, "数値", None, 0, 100),
                                    "AirHeatExchangeRatioHeating":
                                        check_value(dataAC4[18], "様式2-7.空調機 "+ str(i+1) +"行目:「⑲全熱交換効率（暖房時）」", False, None, "数値", None, 0, 100),
                                    "AirHeatExchangerEffectiveAirVolumeRatio": None,
                                    "AirHeatExchangerControl":
                                        check_value(dataAC4[19], "様式2-7.空調機 "+ str(i+1) +"行目:「⑳自動換気切替機能の有無」", False, "無", "文字列", input_options["有無"], None, None),
                                    "AirHeatExchangerPowerConsumption":
                                        check_value(dataAC4[20], "様式2-7.空調機 "+ str(i+1) +"行目:「㉑ローター消費電力」", False, None, "数値", None, 0, None),
                                    "Info":
                                        check_value(dataAC4[25], "様式2-7.空調機 "+ str(i+1) +"行目:「㉕備考」", False, None, "文字列", None, None, None),
                                    "isAirHeatExchanger": check_value(dataAC4[14], "様式2-7.空調機 "+ str(i+1) +"行目:「⑮全熱交換器の有無」", False, "無", "文字列", None, None, None), 
                                    "AirHeatExchanger_name": check_value(dataAC4[15], "様式2-7.空調機 "+ str(i+1) +"行目:「⑯全熱交換器の名称」", False, "無", "文字列", None, None, None), 
                                }
                            ]
                        }
                    
                    else:

                        data["AirHandlingSystem"][unitKey] = {
                            "isEconomizer": 
                                check_value(dataAC4[13], "様式2-7.空調機 "+ str(i+1) +"行目:「⑭外気冷房の有無」", False, "無", "文字列", input_options["有無"], None, None), 
                            "EconomizerMaxAirVolume":
                                check_value(dataAC4[5], "様式2-7.空調機 "+ str(i+1) +"行目:「⑥設計最大外気風量」", False, None, "数値", None, None, None), 
                            "isOutdoorAirCut":
                                check_value(dataAC4[12], "様式2-7.空調機 "+ str(i+1) +"行目:「⑬予熱時外気取り入れ停止の有無」", False, "無", "文字列", input_options["有無"], None, None),
                            "Pump_cooling": 
                                check_value(dataAC4[19], "様式2-7.空調機 "+ str(i+1) +"行目:「⑳二次ポンプ群名称（冷熱）」", False, None, "文字列", data["SecondaryPumpSystem"], None, None),
                            "Pump_heating":
                                check_value(dataAC4[20], "様式2-7.空調機 "+ str(i+1) +"行目:「㉑二次ポンプ群名称（温熱）」", False, None, "文字列", data["SecondaryPumpSystem"], None, None),
                            "HeatSource_cooling":
                                check_value(dataAC4[21], "様式2-7.空調機 "+ str(i+1) +"行目:「㉒熱源群名称（冷熱）」", False, None, "文字列", data["HeatsourceSystem"], None, None),
                            "HeatSource_heating":
                                check_value(dataAC4[22], "様式2-7.空調機 "+ str(i+1) +"行目:「㉓熱源群名称（温熱）」", False, None, "文字列", data["HeatsourceSystem"], None, None),
                            "AirHandlingUnit" :[
                                {
                                    "Type":
                                        check_value(dataAC4[2], "様式2-7.空調機 "+ str(i+1) +"行目:「③空調機タイプ」", True, None, "文字列", input_options["空調機タイプ"], None, None), 
                                    "Number":
                                        check_value(dataAC4[1], "様式2-7.空調機 "+ str(i+1) +"行目:「②台数」", True, None, "数値", None, None, None), 
                                    "RatedCapacityCooling":
                                        check_value(dataAC4[3], "様式2-7.空調機 "+ str(i+1) +"行目:「④定格冷却能力」", False, None, "数値", None, None, None),                                 
                                    "RatedCapacityHeating":
                                        check_value(dataAC4[4], "様式2-7.空調機 "+ str(i+1) +"行目:「⑤定格加熱能力」", False, None, "数値", None, None, None), 
                                    "FanType": None,
                                    "FanAirVolume":
                                        check_value(dataAC4[15], "様式2-7.空調機 "+ str(i+1) +"行目:「⑯全熱交換器の設計風量」", False, None, "数値", None, None, None),    
                                    "FanPowerConsumption": E_fan1+E_fan2+E_fan3+E_fan4,
                                    "FanControlType":
                                        check_value(dataAC4[10], "様式2-7.空調機 "+ str(i+1) +"行目:「⑪風量制御方式」", False, "無", "文字列", input_options["風量制御方式"], None, None),
                                    "FanMinOpeningRate":
                                        check_value(dataAC4[11], "様式2-7.空調機 "+ str(i+1) +"行目:「⑫変風量時最小風量比」", False, None, "数値", None, 0, 100),                                   
                                    "AirHeatExchangeRatioCooling":
                                        check_value(dataAC4[16], "様式2-7.空調機 "+ str(i+1) +"行目:「⑰全熱交換効率」", False, None, "数値", None, 0, 100),
                                    "AirHeatExchangeRatioHeating":
                                        check_value(dataAC4[16], "様式2-7.空調機 "+ str(i+1) +"行目:「⑰全熱交換効率」", False, None, "数値", None, 0, 100),
                                    "AirHeatExchangerEffectiveAirVolumeRatio": None,
                                    "AirHeatExchangerControl":
                                        check_value(dataAC4[17], "様式2-7.空調機 "+ str(i+1) +"行目:「⑱自動換気切替機能の有無」", False, "無", "文字列", input_options["有無"], None, None),
                                    "AirHeatExchangerPowerConsumption":
                                        check_value(dataAC4[18], "様式2-7.空調機 "+ str(i+1) +"行目:「⑲ローター消費電力」", False, None, "数値", None, 0, None),
                                    "Info":
                                        check_value(dataAC4[23], "様式2-7.空調機 "+ str(i+1) +"行目:「㉔備考」", False, None, "文字列", None, None, None),
                                    "isAirHeatExchanger": check_value(dataAC4[14], "様式2-7.空調機 "+ str(i+1) +"行目:「⑮全熱交換器の有無」", False, "無", "文字列", None, None, None), 
                                    "AirHeatExchanger_name": None, 
                                }
                            ]
                        }

            elif (dataAC4[2] != "") and (unitKey in data["AirHandlingSystem"]):     

                E_fan1 = check_value(dataAC4[6], "様式2-7.空調機 "+ str(i+1) +"行目:「⑦送風機定格消費電力（給気）」", False, 0, "数値", None, 0, None)
                E_fan2 = check_value(dataAC4[7], "様式2-7.空調機 "+ str(i+1) +"行目:「⑧送風機定格消費電力（還気）」", False, 0, "数値", None, 0, None)
                E_fan3 = check_value(dataAC4[8], "様式2-7.空調機 "+ str(i+1) +"行目:「⑨送風機定格消費電力（外気）」", False, 0, "数値", None, 0, None)
                E_fan4 = check_value(dataAC4[9], "様式2-7.空調機 "+ str(i+1) +"行目:「⑩送風機定格消費電力（排気）」", False, 0, "数値", None, 0, None)

                if sheet_AC4_name[-5:] == "Rev.2":      # 2024年4月 全熱交換器の列が追加

                    if dataAC4[14] == "全熱交換器あり・様式2-9記載あり":
                        validation["error"].append( "様式2-7.空調機:「⑮全熱交換器の有無」の選択肢が「全熱交換器あり・様式2-9記載あり」である場合は計算ができません。")

                    data["AirHandlingSystem"][unitKey]["AirHandlingUnit"].append(
                        {
                            "Type":
                                check_value(dataAC4[2], "様式2-7.空調機 "+ str(i+1) +"行目:「③空調機タイプ」", True, None, "文字列", input_options["空調機タイプ"], None, None), 
                            "Number":
                                check_value(dataAC4[1], "様式2-7.空調機 "+ str(i+1) +"行目:「②台数」", True, None, "数値", None, None, None), 
                            "RatedCapacityCooling":
                                check_value(dataAC4[3], "様式2-7.空調機 "+ str(i+1) +"行目:「④定格冷却能力」", False, None, "数値", None, None, None),                                 
                            "RatedCapacityHeating":
                                check_value(dataAC4[4], "様式2-7.空調機 "+ str(i+1) +"行目:「⑤定格加熱能力」", False, None, "数値", None, None, None), 
                            "FanType": None,
                            "FanAirVolume":
                                check_value(dataAC4[16], "様式2-7.空調機 "+ str(i+1) +"行目:「⑰全熱交換器の設計風量」", False, None, "数値", None, None, None),    
                            "FanPowerConsumption": E_fan1+E_fan2+E_fan3+E_fan4,
                            "FanControlType":
                                check_value(dataAC4[10], "様式2-7.空調機 "+ str(i+1) +"行目:「⑪風量制御方式」", False, "無", "文字列", input_options["風量制御方式"], None, None),
                            "FanMinOpeningRate":
                                check_value(dataAC4[11], "様式2-7.空調機 "+ str(i+1) +"行目:「⑫変風量時最小風量比」", False, None, "数値", None, 0, 100),                                   
                            "AirHeatExchangeRatioCooling":
                                check_value(dataAC4[17], "様式2-7.空調機 "+ str(i+1) +"行目:「⑱全熱交換効率（冷房時）」", False, None, "数値", None, 0, 100),
                            "AirHeatExchangeRatioHeating":
                                check_value(dataAC4[18], "様式2-7.空調機 "+ str(i+1) +"行目:「⑲全熱交換効率（暖房時）」", False, None, "数値", None, 0, 100),
                            "AirHeatExchangerEffectiveAirVolumeRatio": None,
                            "AirHeatExchangerControl":
                                check_value(dataAC4[19], "様式2-7.空調機 "+ str(i+1) +"行目:「⑳自動換気切替機能の有無」", False, "無", "文字列", input_options["有無"], None, None),
                            "AirHeatExchangerPowerConsumption":
                                check_value(dataAC4[20], "様式2-7.空調機 "+ str(i+1) +"行目:「㉑ローター消費電力」", False, None, "数値", None, 0, None),
                            "Info":
                                check_value(dataAC4[25], "様式2-7.空調機 "+ str(i+1) +"行目:「㉕備考」", False, None, "文字列", None, None, None),
                            "isAirHeatExchanger": check_value(dataAC4[14], "様式2-7.空調機 "+ str(i+1) +"行目:「⑮全熱交換器の有無」", False, "無", "文字列", None, None, None), 
                            "AirHeatExchanger_name": check_value(dataAC4[15], "様式2-7.空調機 "+ str(i+1) +"行目:「⑯全熱交換器の名称」", False, "無", "文字列", None, None, None), 
                        }
                    )

                else:

                    data["AirHandlingSystem"][unitKey]["AirHandlingUnit"].append(
                        {
                            "Type":
                                check_value(dataAC4[2], "様式2-7.空調機 "+ str(i+1) +"行目:「③空調機タイプ」", True, None, "文字列", input_options["空調機タイプ"], None, None), 
                            "Number":
                                check_value(dataAC4[1], "様式2-7.空調機 "+ str(i+1) +"行目:「②台数」", True, None, "数値", None, None, None), 
                            "RatedCapacityCooling":
                                check_value(dataAC4[3], "様式2-7.空調機 "+ str(i+1) +"行目:「④定格冷却能力」", False, None, "数値", None, None, None),                                 
                            "RatedCapacityHeating":
                                check_value(dataAC4[4], "様式2-7.空調機 "+ str(i+1) +"行目:「⑤定格加熱能力」", False, None, "数値", None, None, None), 
                            "FanType": None,
                            "FanAirVolume":
                                check_value(dataAC4[15], "様式2-7.空調機 "+ str(i+1) +"行目:「⑯全熱交換器の設計風量」", False, None, "数値", None, None, None),    
                            "FanPowerConsumption": E_fan1+E_fan2+E_fan3+E_fan4,
                            "FanControlType":
                                check_value(dataAC4[10], "様式2-7.空調機 "+ str(i+1) +"行目:「⑪風量制御方式」", False, "無", "文字列", input_options["風量制御方式"], None, None),
                            "FanMinOpeningRate":
                                check_value(dataAC4[11], "様式2-7.空調機 "+ str(i+1) +"行目:「⑫変風量時最小風量比」", False, None, "数値", None, 0, 100),                                   
                            "AirHeatExchangeRatioCooling":
                                check_value(dataAC4[16], "様式2-7.空調機 "+ str(i+1) +"行目:「⑰全熱交換効率」", False, None, "数値", None, 0, 100),
                            "AirHeatExchangeRatioHeating":
                                check_value(dataAC4[16], "様式2-7.空調機 "+ str(i+1) +"行目:「⑰全熱交換効率」", False, None, "数値", None, 0, 100),
                            "AirHeatExchangerEffectiveAirVolumeRatio": None,
                            "AirHeatExchangerControl":
                                check_value(dataAC4[17], "様式2-7.空調機 "+ str(i+1) +"行目:「⑱自動換気切替機能の有無」", False, "無", "文字列", input_options["有無"], None, None),
                            "AirHeatExchangerPowerConsumption":
                                check_value(dataAC4[18], "様式2-7.空調機 "+ str(i+1) +"行目:「⑲ローター消費電力」", False, None, "数値", None, 0, None),
                            "Info":
                                check_value(dataAC4[22], "様式2-7.空調機 "+ str(i+1) +"行目:「㉔備考」", False, None, "文字列", None, None, None),
                            "isAirHeatExchanger": check_value(dataAC4[14], "様式2-7.空調機 "+ str(i+1) +"行目:「⑮全熱交換器の有無」", False, "無", "文字列", None, None, None), 
                            "AirHeatExchanger_name": None, 
                        }
                    )

                # 外気冷房制御のチェック（継続行に書いていれば有効にする）
                isEconomizer = check_value(dataAC4[13], "様式2-7.空調機 "+ str(i+1) +"行目:「⑭外気冷房の有無」", False, "無", "文字列", input_options["有無"], None, None)
                EconomizerMaxAirVolume = check_value(dataAC4[5], "様式2-7.空調機 "+ str(i+1) +"行目:「⑥設計最大外気風量」", False, None, "数値", None, None, None)
                if isEconomizer == "有" and EconomizerMaxAirVolume != "":
                    data["AirHandlingSystem"][unitKey]["isEconomizer"] = isEconomizer
                    data["AirHandlingSystem"][unitKey]["EconomizerMaxAirVolume"] = EconomizerMaxAirVolume

                # 予熱時外気取り入れ停止の有無
                isOutdoorAirCut = check_value(dataAC4[12], "様式2-7.空調機 "+ str(i+1) +"行目:「⑬予熱時外気取り入れ停止の有無」", False, "無", "文字列", input_options["有無"], None, None),
                if isOutdoorAirCut == "有":
                    data["AirHandlingSystem"][unitKey]["isOutdoorAirCut"] = isOutdoorAirCut


    ## Varidation
    for zone_name in data["AirConditioningZone"]:

        unit_name = data["AirConditioningZone"][zone_name]["AHU_cooling_insideLoad"]
        if unit_name not in data["AirHandlingSystem"]:
            validation["error"].append( "様式2-1.空調ゾーン:「③空調機群名称（室負荷処理）」が 様式2-7.空調機群入力シートで定義されてません（ ゾーン "+ zone_name +"「"+ unit_name +"」）。") 

        unit_name = data["AirConditioningZone"][zone_name]["AHU_cooling_outdoorLoad"]
        if unit_name not in data["AirHandlingSystem"]:
            validation["error"].append( "様式2-1.空調ゾーン:「④空調機群名称（外気負荷処理）」が 様式2-7.空調機群入力シートで定義されてません（ ゾーン "+ zone_name +"「"+ unit_name +"」）。") 


    #----------------------------------
    # 冷暖同時供給の有無の判定（冷房暖房ともに「有」であれば「有」とする）
    #----------------------------------
    for zone_name in data["AirConditioningZone"]:

        # 接続している空調機群 （様式2-1）
        AHU_c_insideload  = data["AirConditioningZone"][zone_name]["AHU_cooling_insideLoad"]
        AHU_c_outdoorload = data["AirConditioningZone"][zone_name]["AHU_cooling_outdoorLoad"]
        AHU_h_insideload  = data["AirConditioningZone"][zone_name]["AHU_heating_insideLoad"]
        AHU_h_outdoorload = data["AirConditioningZone"][zone_name]["AHU_heating_outdoorLoad"]

        # 空調機群が設定されていることを確認
        if (AHU_c_insideload in data["AirHandlingSystem"]) and (AHU_c_outdoorload in data["AirHandlingSystem"]) \
            and (AHU_h_insideload in data["AirHandlingSystem"]) and (AHU_h_outdoorload in data["AirHandlingSystem"]):

            # 熱源機群名称（冷房）
            iREF_c_i = data["AirHandlingSystem"][AHU_c_insideload]["HeatSource_cooling"]
            iREF_c_o = data["AirHandlingSystem"][AHU_c_outdoorload]["HeatSource_cooling"]

            # 熱源機群名称（暖房）
            iREF_h_i = data["AirHandlingSystem"][AHU_h_insideload]["HeatSource_heating"]
            iREF_h_o = data["AirHandlingSystem"][AHU_h_outdoorload]["HeatSource_heating"]

            # 熱源群が設定されていることを確認。
            if (iREF_c_i in data["HeatsourceSystem"]) and (iREF_c_o in data["HeatsourceSystem"]) \
                and (iREF_h_i in data["HeatsourceSystem"]) and (iREF_h_o in data["HeatsourceSystem"]):

                # 両方とも冷暖同時供給有無が「有」であったら
                if data["HeatsourceSystem"][iREF_c_i]["冷房"]["isSimultaneous_for_ver2"] == "有" and \
                    data["HeatsourceSystem"][iREF_c_o]["冷房"]["isSimultaneous_for_ver2"] == "有" and \
                    data["HeatsourceSystem"][iREF_h_i]["暖房"]["isSimultaneous_for_ver2"] == "有" and \
                    data["HeatsourceSystem"][iREF_h_o]["暖房"]["isSimultaneous_for_ver2"] == "有":

                    data["AirConditioningZone"][zone_name]["isSimultaneousSupply"] = "有"

                # 外調系統だけ冷暖同時であれば（暫定措置）
                elif data["HeatsourceSystem"][iREF_c_i]["冷房"]["isSimultaneous_for_ver2"] == "無" and \
                    data["HeatsourceSystem"][iREF_c_o]["冷房"]["isSimultaneous_for_ver2"] == "有" and \
                    data["HeatsourceSystem"][iREF_h_i]["暖房"]["isSimultaneous_for_ver2"] == "無" and \
                    data["HeatsourceSystem"][iREF_h_o]["暖房"]["isSimultaneous_for_ver2"] == "有":

                    data["AirConditioningZone"][zone_name]["isSimultaneousSupply"] = "有（外気負荷）"

                # 室負荷系統だけ冷暖同時であれば（暫定措置）
                elif data["HeatsourceSystem"][iREF_c_i]["冷房"]["isSimultaneous_for_ver2"] == "有" and \
                    data["HeatsourceSystem"][iREF_c_o]["冷房"]["isSimultaneous_for_ver2"] == "無" and \
                    data["HeatsourceSystem"][iREF_h_i]["暖房"]["isSimultaneous_for_ver2"] == "有" and \
                    data["HeatsourceSystem"][iREF_h_o]["暖房"]["isSimultaneous_for_ver2"] == "無":

                    data["AirConditioningZone"][zone_name]["isSimultaneousSupply"] = "有（室負荷）"


    # isSimultaneous_for_ver2 要素　を削除
    for iREF in data["HeatsourceSystem"]:
        if "冷房" in data["HeatsourceSystem"][iREF]:
            del data["HeatsourceSystem"][iREF]["冷房"]["isSimultaneous_for_ver2"]
        if "暖房" in data["HeatsourceSystem"][iREF]:
            del data["HeatsourceSystem"][iREF]["暖房"]["isSimultaneous_for_ver2"]


    #----------------------------------
    # 様式3-1 換気対象室入力シート の読み込み
    #----------------------------------
    if "3-1) 換気室" in wb.sheet_names():
        
        # シートの読み込み
        sheet_V1 = wb.sheet_by_name("3-1) 換気室")
        # 初期化
        roomKey = None

        # 行のループ
        for i in range(10,sheet_V1.nrows):

            # シートから「行」の読み込み
            dataV = sheet_V1.row_values(i)

            # 数値で入力された室名を文字列に変換
            if sheet_V1.cell_type(i,1) == xlrd.XL_CELL_NUMBER:
                dataV[1] = str(int(sheet_V1.cell_value(i,1)))

            # 階と室名が空欄でない場合
            if (dataV[0] != "") and (dataV[1] != ""):

                # 階＋室をkeyとする
                roomKey = str(dataV[0]) + '_' + str(dataV[1])

                if roomKey not in data["Rooms"]:

                    validation["error"].append( "様式3-1.換気対象室:「①換気対象室」が 様式1.室仕様入力シートで定義されてません（"+ str(i+1) +"行目「"+ roomKey +"」）。") 

                elif roomKey in data["VentilationRoom"]:

                    validation["error"].append( "様式3-1.換気対象室:「①換気対象室」に重複があります（"+ str(i+1) +"行目「"+ roomKey +"」）。") 

                else:

                    unitKey = check_value(dataV[6], "様式3-1.換気対象室 "+ str(i+1) +"行目:「③換気機器名称」", True, None, "文字列", None, None, None)

                    data["VentilationRoom"][roomKey] = {
                            "VentilationType": None,
                            "VentilationUnitRef":{
                                unitKey :{
                                    "UnitType":
                                        check_value(dataV[5], "様式3-1.換気対象室 "+ str(i+1) +"行目:「②換気種類」", True, None, "文字列", input_options["換気送風機の種類"], None, None),
                                    "Info":
                                        check_value(dataV[7], "様式3-1.換気対象室 "+ str(i+1) +"行目:「④備考」", None, None, "文字列", None, None, None),
                                }
                            }
                    }

            # 階と室名が空欄であり、かつ、機器名称に入力がある場合
            # 上記 if文 内で定義された roomKey をkeyとして、機器を追加する。
            elif (dataV[0] == "") and (dataV[1] == "") and (dataV[6] != "") and (roomKey in data["VentilationRoom"]):

                unitKey = check_value(dataV[6], "様式3-1.換気対象室 "+ str(i+1) +"行目:「③換気機器名称」", True, None, "文字列", None, None, None)

                if unitKey in data["VentilationRoom"][roomKey]["VentilationUnitRef"]:

                    validation["error"].append( "様式3-1.換気対象室: 同一の室において「③換気機器名称」に重複があります（"+ str(i+1) +"行目「"+ roomKey +"」）。") 

                else:

                    data["VentilationRoom"][roomKey]["VentilationUnitRef"][unitKey]  = {
                        "UnitType":
                            check_value(dataV[5], "様式3-1.換気対象室 "+ str(i+1) +"行目:「②換気種類」", True, None, "文字列", input_options["換気送風機の種類"], None, None),
                        "Info":
                            check_value(dataV[7], "様式3-1.換気対象室 "+ str(i+1) +"行目:「④備考」", None, None, "文字列", None, None, None),
                    }               


    #----------------------------------
    # 様式3-2 換気送風機入力シート の読み込み
    #----------------------------------
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

                if unitKey in data["VentilationUnit"]:

                    validation["error"].append( "様式3-2.換気送風機:「①換気機器名称」に重複があります（"+ str(i+1) +"行目「"+ unitKey +"」）。") 

                else:
                
                    data["VentilationUnit"][unitKey] = {
                        "Number": 1,
                        "FanAirVolume":
                            check_value(dataV[1], "様式3-2.換気送風機 "+ str(i+1) +"行目:「②設計風量」", True, None, "数値", None, 0, None),
                        "MoterRatedPower":
                            check_value(dataV[2], "様式3-2.換気送風機 "+ str(i+1) +"行目:「③電動機定格出力」", True, None, "数値", None, 0, None),
                        "PowerConsumption": None,
                        "HighEfficiencyMotor":
                            check_value(dataV[3], "様式3-2.換気送風機 "+ str(i+1) +"行目:「④高効率電動機の有無」", False, "無", "文字列", input_options["有無"], None, None),                        
                        "Inverter":
                            check_value(dataV[4], "様式3-2.換気送風機 "+ str(i+1) +"行目:「⑤インバータの有無」", False, "無", "文字列", input_options["有無"], None, None),
                        "AirVolumeControl":
                            check_value(dataV[5], "様式3-2.換気送風機 "+ str(i+1) +"行目:「⑥送風量制御」", False, "無", "文字列", input_options["換気送風量制御"], None, None),
                        "VentilationRoomType": None,
                        "AC_CoolingCapacity": None,
                        "AC_RefEfficiency": None,
                        "AC_PumpPower": None,
                        "Info":
                            check_value(dataV[6], "様式3-2.換気送風機 "+ str(i+1) +"行目:「⑦備考」", False, "無", "文字列", None, None, None),
                    }

    #----------------------------------
    # 様式3-3 換気代替空調機入力シート の読み込み
    #----------------------------------
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

            # 換気機器名称が空欄でない場合 unitKey と unitNum をリセット
            if (dataV[0] != ""):

                unitKey = check_value(dataV[0], "様式3-3.換気代替空調 "+ str(i+1) +"行目:「①換気機器名称」", True, None, "文字列", None, None, None)
                unitNum = 0

            # 送風機の種類
            if (dataV[5] != ""):

                ventilation_type = check_value(dataV[5], "様式3-3.換気代替空調 "+ str(i+1) +"行目:「⑤送風機の種類」", True, None, "文字列", input_options["換気送風機の種類"], None, None)

                if ventilation_type == "空調":
                    
                    data["VentilationUnit"][unitKey] = {
                        "Number": 1,
                        "FanAirVolume":
                            check_value(dataV[6], "様式3-3.換気代替空調 "+ str(i+1) +"行目:「⑦設計風量」", True, None, "数値", None, 0, None),
                        "MoterRatedPower":
                            check_value(dataV[7], "様式3-3.換気代替空調 "+ str(i+1) +"行目:「⑧電動機定格出力」", True, None, "数値", None, 0, None),
                        "PowerConsumption": None,
                        "HighEfficiencyMotor":
                            check_value(dataV[8], "様式3-3.換気代替空調 "+ str(i+1) +"行目:「⑨高効率電動機の有無」", False, "無", "文字列", input_options["有無"], None, None),
                        "Inverter":
                            check_value(dataV[9], "様式3-3.換気代替空調 "+ str(i+1) +"行目:「⑩インバータの有無」", False, "無", "文字列", input_options["有無"], None, None),
                        "AirVolumeControl":
                            check_value(dataV[10], "様式3-3.換気代替空調 "+ str(i+1) +"行目:「⑪送風量制御」", False, "無", "文字列", input_options["換気送風量制御"], None, None),
                        "VentilationRoomType":
                            check_value(dataV[1], "様式3-3.換気代替空調 "+ str(i+1) +"行目:「②換気対象室の用途」", True, None, "文字列か数値", input_options["換気代替空調対象室の用途"], None, None),
                        "AC_CoolingCapacity":
                            check_value(dataV[2], "様式3-3.換気代替空調 "+ str(i+1) +"行目:「③必要冷却能力」", True, None, "数値", None, 0, None),
                        "AC_RefEfficiency":
                            check_value(dataV[3], "様式3-3.換気代替空調 "+ str(i+1) +"行目:「④熱源効率」", True, None, "数値", None, 0, None),
                        "AC_PumpPower":
                            check_value(dataV[4], "様式3-3.換気代替空調 "+ str(i+1) +"行目:「⑤ポンプ定格出力」", False, 0, "数値", None, -0.01, None),
                        "Info":
                            check_value(dataV[11], "様式3-3.換気代替空調 "+ str(i+1) +"行目:「⑫備考」", False, "無", "文字列", None, None, None),
                    }
                
                elif ventilation_type in input_options["換気送風機の種類"]:

                    unitNum += 1

                    data["VentilationUnit"][unitKey + "_fan" + str(unitNum)] = {
                        "Number": 1,
                        "FanAirVolume":
                            check_value(dataV[6], "様式3-3.換気代替空調 "+ str(i+1) +"行目:「⑦設計風量」", True, None, "数値", None, 0, None),
                        "MoterRatedPower":
                            check_value(dataV[7], "様式3-3.換気代替空調 "+ str(i+1) +"行目:「⑧電動機定格出力」", True, None, "数値", None, 0, None),
                        "PowerConsumption": None,
                        "HighEfficiencyMotor":
                            check_value(dataV[8], "様式3-3.換気代替空調 "+ str(i+1) +"行目:「⑨高効率電動機の有無」", False, "無", "文字列", input_options["有無"], None, None),
                        "Inverter":
                            check_value(dataV[9], "様式3-3.換気代替空調 "+ str(i+1) +"行目:「⑩インバータの有無」", False, "無", "文字列", input_options["有無"], None, None),
                        "AirVolumeControl":
                            check_value(dataV[10], "様式3-3.換気代替空調 "+ str(i+1) +"行目:「⑪送風量制御」", False, "無", "文字列", input_options["換気送風量制御"], None, None),
                        "VentilationRoomType": None,
                        "AC_CoolingCapacity": None,
                        "AC_RefEfficiency": None,
                        "AC_PumpPower": None,
                        "Info":
                            check_value(dataV[11], "様式3-3.換気代替空調 "+ str(i+1) +"行目:「⑫備考」", False, "無", "文字列", None, None, None),
                    }

                    for room_name in data["VentilationRoom"]:
                        if unitKey in data["VentilationRoom"][room_name]["VentilationUnitRef"]:
                            data["VentilationRoom"][room_name]["VentilationUnitRef"][unitKey + "_fan" + str(unitNum)] = {
                                "UnitType": ventilation_type,
                                "Info": ""
                        }


    ## Varidation（換気）
    for room_name in data["VentilationRoom"]:
        for unit_name in data["VentilationRoom"][room_name]["VentilationUnitRef"]:
            if (unit_name != "") and (unit_name not in data["VentilationUnit"]):
                validation["error"].append( "様式3-1.換気対象室 ：換気対象室 "+ room_name +" の「③換気機器名称」で入力された機器 "+ unit_name +" は様式3-2、様式3-3で定義されていません。")


    #----------------------------------
    # 様式4 照明入力シート の読み込み
    #----------------------------------
    if "4) 照明" in wb.sheet_names():
        
        # シートの読み込み
        sheet_L = wb.sheet_by_name("4) 照明")
        # 初期化
        roomKey = None

        # 行のループ
        for i in range(10,sheet_L.nrows):

            # シートから「行」の読み込み
            dataL = sheet_L.row_values(i)

            # 数値で入力された室名を文字列に変換
            if sheet_L.cell_type(i,1) == xlrd.XL_CELL_NUMBER:
                dataL[1] = str(int(sheet_L.cell_value(i,1)))

            # 階と室名が空欄でない場合
            if (dataL[0] != "") and (dataL[1] != ""):

                roomKey = str(dataL[0]) + '_' + str(dataL[1])

                if roomKey not in data["Rooms"]:

                    validation["error"].append( "様式4.照明:「①照明対象室」が 様式1.室仕様入力シートで定義されてません（"+ str(i+1) +"行目「"+ roomKey +"」）。") 

                elif roomKey in data["LightingSystems"]:

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
            elif (dataL[0] == "") and (dataL[1] == "") and (dataL[10] != "") and (roomKey in data["LightingSystems"]):

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

    #----------------------------------
    # 様式5-1 給湯対象室入力シート の読み込み
    #----------------------------------
    if "5-1) 給湯室" in wb.sheet_names():

        # シートの読み込み
        sheet_HW1 = wb.sheet_by_name("5-1) 給湯室")
        # 初期化
        roomKey = None

        # 行のループ
        for i in range(10,sheet_HW1.nrows):

            # シートから「行」の読み込み
            dataHW1 = sheet_HW1.row_values(i)

            # 数値で入力された室名を文字列に変換
            if sheet_HW1.cell_type(i,1) == xlrd.XL_CELL_NUMBER:
                dataHW1[1] = str(int(sheet_HW1.cell_value(i,1)))

            # 階と室名が空欄でない場合
            if (dataHW1[0] != "") and (dataHW1[1] != "") :

                # 階＋室をkeyとする
                roomKey = str(dataHW1[0]) + '_' + str(dataHW1[1])

                if roomKey not in data["Rooms"]:

                    validation["error"].append( "様式5-1.給湯対象室:「①給湯対象室」が 様式1.室仕様入力シートで定義されてません（"+ str(i+1) +"行目「"+ roomKey +"」）。") 

                elif roomKey in data["HotwaterRoom"]:

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

            elif (dataHW1[6] != "") and (dataHW1[7] != "") and (roomKey in data["HotwaterRoom"]):

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

    #----------------------------------
    # 様式5-2 給湯機器入力シート の読み込み
    #----------------------------------
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
                    elif str(dataHW2[1]) == "他人から供給された熱(温水)":
                        HeatSourceType = "地域熱供給"
                    elif str(dataHW2[1]) == "他人から供給された熱（蒸気）":
                        HeatSourceType = "地域熱供給"
                    elif str(dataHW2[1]) == "他人から供給された熱(蒸気)":
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

    #----------------------------------
    # 様式6 昇降機入力シート の読み込み
    #----------------------------------
    if "6) 昇降機" in wb.sheet_names():

        # シートの読み込み
        sheet_EV = wb.sheet_by_name("6) 昇降機")
        # 初期化
        roomKey = None

        # 行のループ
        for i in range(10,sheet_EV.nrows):

            # シートから「行」の読み込み
            dataEV = sheet_EV.row_values(i)

            # 数値で入力された室名を文字列に変換
            if sheet_EV.cell_type(i,1) == xlrd.XL_CELL_NUMBER:
                dataEV[1] = str(int(sheet_EV.cell_value(i,1)))

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

                if roomKey not in data["Rooms"]:

                    validation["error"].append( "様式6.昇降機:「①主要な対象室」が 様式1.室仕様入力シートで定義されてません（"+ str(i+1) +"行目「"+ roomKey +"」）。") 

                else:

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

            elif (dataEV[5] != "") and (roomKey in data["Elevators"]):

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

    #----------------------------------
    # 様式7-1 太陽光発電入力シート の読み込み
    #----------------------------------
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
    
    #----------------------------------
    # 様式7-3 コジェネ入力シート の読み込み
    #----------------------------------
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

        ## Varidation
        for csg_system in data["CogenerationSystems"]:

            # 重複をチェックする。ただし、空欄の重複は許可する。
            if check_duplicates(list(filter(
                lambda x : x != None and x != "", [
                    data["CogenerationSystems"][csg_system]["HeatRecoveryPriorityCooling"],
                    data["CogenerationSystems"][csg_system]["HeatRecoveryPriorityHeating"],
                    data["CogenerationSystems"][csg_system]["HeatRecoveryPriorityHotWater"]
                ]))):

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


    # if "SP-5) 気象データ" in wb.sheet_names():

    #     # シートの読み込み
    #     sheet_SP5 = wb.sheet_by_name("SP-5) 気象データ")

    #     # 行のループ
    #     Tout_8760 = []
    #     Xout_8760 = []
    #     Iod_8760  = []
    #     Ios_8760  = []
    #     Inn_8760  = []

    #     for i in range(10,sheet_SP5.nrows):

    #         # シートから「行」の読み込み
    #         dataSP5 = sheet_SP5.row_values(i)

    #         Tout_8760.append(float(dataSP5[4]))
    #         Xout_8760.append(float(dataSP5[5]))
    #         Iod_8760.append(float(dataSP5[6]))
    #         Ios_8760.append(float(dataSP5[7]))
    #         Inn_8760.append(float(dataSP5[8]))

    #     # データの処理がなされていたら、365×24の行列に変更して保存
    #     if Tout_8760 != []:
    #         data["SpecialInputData"]["climate_data"] = {
    #             "Tout": bc.trans_8760to36524(Tout_8760),
    #             "Xout": bc.trans_8760to36524(Xout_8760),
    #             "Iod": bc.trans_8760to36524(Iod_8760),
    #             "Ios": bc.trans_8760to36524(Ios_8760),
    #             "Inn": bc.trans_8760to36524(Inn_8760)
    #         }

    # 様式SP-CD：気象データ入力シート
    if "SP-CD) 気象" in wb.sheet_names():

        try:

            # シートの読み込み
            sheet_SP_CD = wb.sheet_by_name("SP-CD) 気象")

            # 行のループ
            Tout_8760 = []
            Xout_8760 = []
            Iod_8760  = []
            Ios_8760  = []
            Inn_8760  = []

            for i in range(10,sheet_SP_CD.nrows):

                # シートから「行」の読み込み
                dataSPCD = sheet_SP_CD.row_values(i)

                Tout_8760.append(float(dataSPCD[1]))
                Xout_8760.append(float(dataSPCD[2]))
                Iod_8760.append(float(dataSPCD[3]))
                Ios_8760.append(float(dataSPCD[4]))
                Inn_8760.append(float(dataSPCD[5]))

            # 365×24の行列に変更して保存
            data["SpecialInputData"]["climate_data"] = {
                "Tout": bc.trans_8760to36524(Tout_8760),
                "Xout": bc.trans_8760to36524(Xout_8760),
                "Iod": bc.trans_8760to36524(Iod_8760),
                "Ios": bc.trans_8760to36524(Ios_8760),
                "Inn": bc.trans_8760to36524(Inn_8760)
            }
            
        except Exception as e:

            # 例外処理
            validation["error"].append( f"様式SP-CD.気象データ: 入力データが不正です。{e}")


    # if "SP-6) カレンダー" in wb.sheet_names():

    #     data["SpecialInputData"]["calender"] = {}

    #     # シートの読み込み
    #     sheet_SP6 = wb.sheet_by_name("SP-6) カレンダー")

    #     for i in range(10,sheet_SP6.nrows):

    #         # シートから「行」の読み込み
    #         dataSP6 = sheet_SP6.row_values(i)

    #         building_type = dataSP6[0]
    #         room_type = dataSP6[1]
    #         calender_num = [int(x) for x in dataSP6[2:]]  # 整数型に変換


    #         # 建物用途が既に登録されているかを判定
    #         if building_type not in data["SpecialInputData"]["calender"]:

    #             data["SpecialInputData"]["calender"][building_type] = {}
    #             data["SpecialInputData"]["calender"][building_type] = {
    #                 room_type : calender_num
    #             }

    #         else:
    #             data["SpecialInputData"]["calender"][building_type][room_type] = calender_num

    if "SP-RT-CP) カレンダー" in wb.sheet_names():

        try:

            data["SpecialInputData"]["calender"] = {}

            # シートの読み込み
            sheet_SP_RT_CP = wb.sheet_by_name("SP-RT-CP) カレンダー")

            # 入力されたカレンダーパターン名称を検索
            calender_p_list = sheet_SP_RT_CP.row_values(4)

            # 入力されている列について、名称と列数の対応関係を保存
            calender_column_num = {}
            for column_num in range(len(calender_p_list)):
                name = calender_p_list[column_num]
                if name != "":
                    calender_column_num[name] = column_num

            # データの読み込み
            for pattern_name in calender_column_num:
                dataSP_RT_CP_tmp = []
                for i in range(10,365+10):
                    dataSP_RT_CP_tmp.append( int(sheet_SP_RT_CP.cell_value(i, calender_column_num[pattern_name])) ) 
                data["SpecialInputData"]["calender"][pattern_name] = dataSP_RT_CP_tmp


        except Exception as e:

            # 例外処理
            validation["error"].append( f"様式SP-RT-CP カレンダーパターン: 入力データが不正です。{e}")


    # 様式SP-RT-SD 室スケジュール入力シート
    if "SP-RT-SD) スケジュール" in wb.sheet_names():

        try:

            data["SpecialInputData"]["room_schedule"] = {}

            # シートの読み込み
            sheet_SP_RT_SD = wb.sheet_by_name("SP-RT-SD) スケジュール")

            for i in range(10,sheet_SP_RT_SD.nrows):

                # シートから「行」の読み込み
                data_SP_RT_SD = sheet_SP_RT_SD.row_values(i)

                if data_SP_RT_SD[0] != "":
                    data["SpecialInputData"]["room_schedule"][data_SP_RT_SD[0]] = [float(x) for x in data_SP_RT_SD[1:25]]
            
        except Exception as e:

            # 例外処理
            validation["error"].append( f"様式SP-RT-SD.スケジュール: 入力データが不正です。{e}" )


    # if "SP-7) 室スケジュール" in wb.sheet_names():

    #     data["SpecialInputData"]["room_schedule"] = {}

    #     # シートの読み込み
    #     sheet_SP7 = wb.sheet_by_name("SP-7) 室スケジュール")
    #     # 初期化
    #     roomKey = None

    #     for i in range(10,sheet_SP7.nrows):

    #         # シートから「行」の読み込み
    #         dataSP7 = sheet_SP7.row_values(i)

    #         # 階と室名が空欄でない場合
    #         if (dataSP7[0] != "") and (dataSP7[1] != ""):

    #             roomKey = str(dataSP7[0]) + '_' + str(dataSP7[1])

    #             data["SpecialInputData"]["room_schedule"][roomKey] = {
    #                 "roomDayMode": "",
    #                 "schedule": {}
    #             }

    #             # 使用時間帯
    #             if dataSP7[2] == "終日":
    #                 data["SpecialInputData"]["room_schedule"][roomKey]["roomDayMode"] = "終日"
    #             elif dataSP7[2] == "昼":
    #                 data["SpecialInputData"]["room_schedule"][roomKey]["roomDayMode"] = "昼"
    #             elif dataSP7[2] == "夜":
    #                 data["SpecialInputData"]["room_schedule"][roomKey]["roomDayMode"] = "夜"
    #             else:
    #                 raise Exception("使用時間帯の入力が不正です")

    #             if dataSP7[3] == "室の同時使用率":
    #                 data["SpecialInputData"]["room_schedule"][roomKey]["schedule"]["室の同時使用率"] =  bc.trans_8760to36524(dataSP7[4:])
    #             elif dataSP7[3] == "照明発熱密度比率":
    #                 data["SpecialInputData"]["room_schedule"][roomKey]["schedule"]["照明発熱密度比率"] =  bc.trans_8760to36524(dataSP7[4:])
    #             elif dataSP7[3] == "人体発熱密度比率":
    #                 data["SpecialInputData"]["room_schedule"][roomKey]["schedule"]["人体発熱密度比率"] =  bc.trans_8760to36524(dataSP7[4:])
    #             elif dataSP7[3] == "機器発熱密度比率":
    #                 data["SpecialInputData"]["room_schedule"][roomKey]["schedule"]["機器発熱密度比率"] =  bc.trans_8760to36524(dataSP7[4:])
    #             else:
    #                 raise Exception("スケジュールの種類が不正です")

    #         # 階と室名が空欄であり、かつ、スケジュールの種類の入力がある場合
    #         elif (dataSP7[0] == "") and (dataSP7[1] == "") and (dataSP7[3] != ""):

    #             if dataSP7[3] == "室の同時使用率":
    #                 data["SpecialInputData"]["room_schedule"][roomKey]["schedule"]["室の同時使用率"] =  bc.trans_8760to36524(dataSP7[4:])
    #             elif dataSP7[3] == "照明発熱密度比率":
    #                 data["SpecialInputData"]["room_schedule"][roomKey]["schedule"]["照明発熱密度比率"] =  bc.trans_8760to36524(dataSP7[4:])
    #             elif dataSP7[3] == "人体発熱密度比率":
    #                 data["SpecialInputData"]["room_schedule"][roomKey]["schedule"]["人体発熱密度比率"] =  bc.trans_8760to36524(dataSP7[4:])
    #             elif dataSP7[3] == "機器発熱密度比率":
    #                 data["SpecialInputData"]["room_schedule"][roomKey]["schedule"]["機器発熱密度比率"] =  bc.trans_8760to36524(dataSP7[4:])
    #             else:
    #                 raise Exception("スケジュールの種類が不正です")


    if "SP-RT-UC) 室使用条件" in wb.sheet_names():

        try:

            data["SpecialInputData"]["room_usage_condition"] = {}

            # デフォルトデータベースの読み込み
            with open(database_directory + "RoomUsageSchedule.json", 'r', encoding='utf-8') as f:
                RoomUsageSchedule = json.load(f)

            # シートの読み込み
            sheet_SP_RT_UC = wb.sheet_by_name("SP-RT-UC) 室使用条件")

            for i in range(10,sheet_SP_RT_UC.nrows):

                # シートから「行」の読み込み
                data_SP_RT_UC = sheet_SP_RT_UC.row_values(i)

                building_type  = data_SP_RT_UC[0]  # 建物用途
                room_type_name = data_SP_RT_UC[1]  # 新しい室用途名称
                base_room_type = data_SP_RT_UC[2]  # ベースとする室用途名称

                # 建物用途
                if building_type not in RoomUsageSchedule:
                    raise Exception ("建物用途が不正です")
                elif building_type not in data["SpecialInputData"]["room_usage_condition"]:
                    data["SpecialInputData"]["room_usage_condition"][building_type] = {}

                # ベースとする室用途の条件をコピー
                if base_room_type != "":
                    data["SpecialInputData"]["room_usage_condition"][building_type][room_type_name] = copy.deepcopy(RoomUsageSchedule[building_type][base_room_type])
                    del data["SpecialInputData"]["room_usage_condition"][building_type][room_type_name]["id"]
                    del data["SpecialInputData"]["room_usage_condition"][building_type][room_type_name]["年間空調時間"]
                    del data["SpecialInputData"]["room_usage_condition"][building_type][room_type_name]["標準換気風量"]
                    del data["SpecialInputData"]["room_usage_condition"][building_type][room_type_name]["基準設定換気方式"]
                    del data["SpecialInputData"]["room_usage_condition"][building_type][room_type_name]["基準設定全圧損失"]
                    del data["SpecialInputData"]["room_usage_condition"][building_type][room_type_name]["年間照明点灯時間"]
                    del data["SpecialInputData"]["room_usage_condition"][building_type][room_type_name]["設定照度"]
                    del data["SpecialInputData"]["room_usage_condition"][building_type][room_type_name]["基準設定照明消費電力"]
                    del data["SpecialInputData"]["room_usage_condition"][building_type][room_type_name]["年間湯使用量"]
                    del data["SpecialInputData"]["room_usage_condition"][building_type][room_type_name]["年間給湯日数"]
                    del data["SpecialInputData"]["room_usage_condition"][building_type][room_type_name]["newHASP"]
                else:
                    raise Exception ("ベースとする室用途が入力されていません")
                
                # 入力

                if data_SP_RT_UC[3] != "":
                    data["SpecialInputData"]["room_usage_condition"][building_type][room_type_name]["空調運転パターン"] = data_SP_RT_UC[3]

                if data_SP_RT_UC[4] != "":
                    data["SpecialInputData"]["room_usage_condition"][building_type][room_type_name]["カレンダーパターン"] = data_SP_RT_UC[4]

                # パターン1
                if data_SP_RT_UC[5] != "":
                    if data_SP_RT_UC[5] in data["SpecialInputData"]["room_schedule"]:
                        data["SpecialInputData"]["room_usage_condition"][building_type][room_type_name]["スケジュール"]["室同時使用率"]["パターン1"] = data["SpecialInputData"]["room_schedule"][data_SP_RT_UC[5]]
                    else:
                        raise Exception ("スケジュールが規定されていません")

                if data_SP_RT_UC[6] != "":
                    if data_SP_RT_UC[6] in data["SpecialInputData"]["room_schedule"]:
                        data["SpecialInputData"]["room_usage_condition"][building_type][room_type_name]["スケジュール"]["照明発熱密度比率"]["パターン1"] = data["SpecialInputData"]["room_schedule"][data_SP_RT_UC[6]]
                    else:
                        raise Exception ("スケジュールが規定されていません")

                if data_SP_RT_UC[7] != "":
                    if data_SP_RT_UC[7] in data["SpecialInputData"]["room_schedule"]:
                        data["SpecialInputData"]["room_usage_condition"][building_type][room_type_name]["スケジュール"]["人体発熱密度比率"]["パターン1"] = data["SpecialInputData"]["room_schedule"][data_SP_RT_UC[7]]
                    else:
                        raise Exception ("スケジュールが規定されていません")

                if data_SP_RT_UC[8] != "":
                    if data_SP_RT_UC[8] in data["SpecialInputData"]["room_schedule"]:
                        data["SpecialInputData"]["room_usage_condition"][building_type][room_type_name]["スケジュール"]["機器発熱密度比率"]["パターン1"] = data["SpecialInputData"]["room_schedule"][data_SP_RT_UC[8]]
                    else:
                        raise Exception ("スケジュールが規定されていません")

                # パターン2
                if data_SP_RT_UC[9] != "":
                    if data_SP_RT_UC[9] in data["SpecialInputData"]["room_schedule"]:
                        data["SpecialInputData"]["room_usage_condition"][building_type][room_type_name]["スケジュール"]["室同時使用率"]["パターン2"] = data["SpecialInputData"]["room_schedule"][data_SP_RT_UC[9]]
                    else:
                        raise Exception ("スケジュールが規定されていません")

                if data_SP_RT_UC[10] != "":
                    if data_SP_RT_UC[10] in data["SpecialInputData"]["room_schedule"]:
                        data["SpecialInputData"]["room_usage_condition"][building_type][room_type_name]["スケジュール"]["照明発熱密度比率"]["パターン2"] = data["SpecialInputData"]["room_schedule"][data_SP_RT_UC[10]]
                    else:
                        raise Exception ("スケジュールが規定されていません")

                if data_SP_RT_UC[11] != "":
                    if data_SP_RT_UC[11] in data["SpecialInputData"]["room_schedule"]:
                        data["SpecialInputData"]["room_usage_condition"][building_type][room_type_name]["スケジュール"]["人体発熱密度比率"]["パターン2"] = data["SpecialInputData"]["room_schedule"][data_SP_RT_UC[11]]
                    else:
                        raise Exception ("スケジュールが規定されていません")

                if data_SP_RT_UC[12] != "":
                    if data_SP_RT_UC[12] in data["SpecialInputData"]["room_schedule"]:
                        data["SpecialInputData"]["room_usage_condition"][building_type][room_type_name]["スケジュール"]["機器発熱密度比率"]["パターン2"] = data["SpecialInputData"]["room_schedule"][data_SP_RT_UC[12]]
                    else:
                        raise Exception ("スケジュールが規定されていません")

                # パターン3
                if data_SP_RT_UC[13] != "":
                    if data_SP_RT_UC[13] in data["SpecialInputData"]["room_schedule"]:
                        data["SpecialInputData"]["room_usage_condition"][building_type][room_type_name]["スケジュール"]["室同時使用率"]["パターン3"] = data["SpecialInputData"]["room_schedule"][data_SP_RT_UC[13]]
                    else:
                        raise Exception ("スケジュールが規定されていません")

                if data_SP_RT_UC[14] != "":
                    if data_SP_RT_UC[14] in data["SpecialInputData"]["room_schedule"]:
                        data["SpecialInputData"]["room_usage_condition"][building_type][room_type_name]["スケジュール"]["照明発熱密度比率"]["パターン3"] = data["SpecialInputData"]["room_schedule"][data_SP_RT_UC[14]]
                    else:
                        raise Exception ("スケジュールが規定されていません")

                if data_SP_RT_UC[15] != "":
                    if data_SP_RT_UC[15] in data["SpecialInputData"]["room_schedule"]:
                        data["SpecialInputData"]["room_usage_condition"][building_type][room_type_name]["スケジュール"]["人体発熱密度比率"]["パターン3"] = data["SpecialInputData"]["room_schedule"][data_SP_RT_UC[15]]
                    else:
                        raise Exception ("スケジュールが規定されていません")

                if data_SP_RT_UC[16] != "":
                    if data_SP_RT_UC[16] in data["SpecialInputData"]["room_schedule"]:
                        data["SpecialInputData"]["room_usage_condition"][building_type][room_type_name]["スケジュール"]["機器発熱密度比率"]["パターン3"] = data["SpecialInputData"]["room_schedule"][data_SP_RT_UC[16]]
                    else:
                        raise Exception ("スケジュールが規定されていません")

                if data_SP_RT_UC[17] != "":
                    data["SpecialInputData"]["room_usage_condition"][building_type][room_type_name]["照明発熱参照値"] = float(data_SP_RT_UC[17])
                if data_SP_RT_UC[18] != "":
                    data["SpecialInputData"]["room_usage_condition"][building_type][room_type_name]["人体発熱参照値"] = float(data_SP_RT_UC[18])
                if data_SP_RT_UC[19] != "":
                    data["SpecialInputData"]["room_usage_condition"][building_type][room_type_name]["機器発熱参照値"] = float(data_SP_RT_UC[19])
                if data_SP_RT_UC[20] != "":
                    data["SpecialInputData"]["room_usage_condition"][building_type][room_type_name]["作業強度指数"] = int(data_SP_RT_UC[20])
                if data_SP_RT_UC[21] != "":
                    data["SpecialInputData"]["room_usage_condition"][building_type][room_type_name]["外気導入量"] = float(data_SP_RT_UC[21])
                if data_SP_RT_UC[22] != "":
                    data["SpecialInputData"]["room_usage_condition"][building_type][room_type_name]["年間換気時間"] = float(data_SP_RT_UC[22])

                if not (data_SP_RT_UC[23] == "" and data_SP_RT_UC[24] == "" and data_SP_RT_UC[25] == "" and data_SP_RT_UC[26] == ""):
                    
                    data["SpecialInputData"]["room_usage_condition"][building_type][room_type_name]["年間湯使用量の単位"] = "[L/m2日]"

                    if data_SP_RT_UC[23] != "":
                        data["SpecialInputData"]["room_usage_condition"][building_type][room_type_name]["年間湯使用量（洗面）"] = float(data_SP_RT_UC[23])
                    else:
                        data["SpecialInputData"]["room_usage_condition"][building_type][room_type_name]["年間湯使用量（洗面）"] = 0
                    if data_SP_RT_UC[24] != "":
                        data["SpecialInputData"]["room_usage_condition"][building_type][room_type_name]["年間湯使用量（シャワー）"] = float(data_SP_RT_UC[24])
                    else:
                        data["SpecialInputData"]["room_usage_condition"][building_type][room_type_name]["年間湯使用量（シャワー）"] = 0
                    if data_SP_RT_UC[25] != "":
                        data["SpecialInputData"]["room_usage_condition"][building_type][room_type_name]["年間湯使用量（厨房）"] = float(data_SP_RT_UC[25])
                    else:
                        data["SpecialInputData"]["room_usage_condition"][building_type][room_type_name]["年間湯使用量（厨房）"] = 0
                    if data_SP_RT_UC[26] != "":
                        data["SpecialInputData"]["room_usage_condition"][building_type][room_type_name]["年間湯使用量（その他）"] = float(data_SP_RT_UC[26])
                    else:
                        data["SpecialInputData"]["room_usage_condition"][building_type][room_type_name]["年間湯使用量（その他）"] = 0

        except Exception as e:

            # 例外処理
            validation["error"].append( f"様式SP-RT-UC 室使用条件: 入力データが不正です。{e}" )


    # 様式SP-AC-MD：空調運転モード入力シート
    if "SP-AC-MD) 空調モード" in wb.sheet_names():

        try:

            data["SpecialInputData"]["AC_operation_mode"] = {
                "operation_mode": [],
                "setpoint_temperature": [],
                "setpoint_humidity": [],
            }

            # シートの読み込み
            sheet_SP_AC_MD = wb.sheet_by_name("SP-AC-MD) 空調モード")

            for i in range(10,365+10):

                data_SP_AC_MD = sheet_SP_AC_MD.row_values(i)

                data["SpecialInputData"]["AC_operation_mode"]["operation_mode"].append( data_SP_AC_MD[1] )
                data["SpecialInputData"]["AC_operation_mode"]["setpoint_temperature"].append( data_SP_AC_MD[2] )
                data["SpecialInputData"]["AC_operation_mode"]["setpoint_humidity"].append( data_SP_AC_MD[3] )

        except Exception as e:

            # 例外処理
            validation["error"].append( f"様式SP-AC-MD. 空調モード: 入力データが不正です。{e}")



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

    case_name = 'Builelib_sample_one_room_v2'
    case_name = 'Baguio_Ayala_Land_Technohub_BPO-B_001_ベースモデル'

    # inputdata, validation = make_jsondata_from_Ver2_sheet(directory + case_name + ".xlsm")
    inputdata, validation = make_jsondata_from_Ver2_sheet(directory + case_name + ".xlsx")

    print(validation)

    # json出力
    with open(directory + case_name + ".json",'w', encoding='utf-8') as fw:
        json.dump(inputdata,fw,indent=4,ensure_ascii=False)

