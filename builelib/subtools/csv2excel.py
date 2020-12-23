import pandas as pd
import openpyxl as px
import csv
import glob

def write_list_2d(sheet, l_2d, start_row, start_col):
    """
    リストをExcelファイルに書き込むための関数
    https://note.nkmk.me/python-openpyxl-usage/
    """
    for y, row in enumerate(l_2d):
        for x, cell in enumerate(row):
            sheet.cell(row=start_row + y,
                        column=start_col + x,
                        value=l_2d[y][x])

def csv2excel(csv_directory, output_filename):
    """
    csv_directory  : Excel化するCSVファイルが保存されたディレクトリを指定
    output_filename: 出力するExcelファイルの名称（拡張子なし）
    """

    # CSVファイルのリスト
    csvfile_list = glob.glob(csv_directory + "/*.csv")

    # テンプレートファイル（Excelファイル）を読み込む
    excel_workbook = px.load_workbook('inputSheet_template.xlsm',read_only=False, keep_vba=True)

    for csvfile_name in csvfile_list:

        # CSVファイルを読み込む
        with open(csvfile_name , newline='', encoding='cp932') as data:
            csvdata = list(csv.reader(data, delimiter=','))

        if "様式0" in csvfile_name:
            write_list_2d(excel_workbook['0) 基本情報'], csvdata[5:], 6, 1)

        elif "様式1" in csvfile_name:
            write_list_2d(excel_workbook['1) 室仕様'], csvdata[10:], 11, 1)

        elif "様式2-1" in csvfile_name:
            write_list_2d(excel_workbook['2-1) 空調ゾーン'], csvdata[10:], 11, 1)

        elif "様式2-2" in csvfile_name:
            write_list_2d(excel_workbook['2-2) 外壁構成 '], csvdata[10:], 11, 1)

        elif "様式2-3" in csvfile_name:
            write_list_2d(excel_workbook['2-3) 窓仕様'], csvdata[10:], 11, 1)

        elif "様式2-4" in csvfile_name:
            write_list_2d(excel_workbook['2-4) 外皮 '], csvdata[10:], 11, 1)

        elif "様式2-5" in csvfile_name:
            write_list_2d(excel_workbook['2-5) 熱源'], csvdata[10:], 11, 1)

        elif "様式2-6" in csvfile_name:
            write_list_2d(excel_workbook['2-6) 2次ﾎﾟﾝﾌﾟ'], csvdata[10:], 11, 1)

        elif "様式2-7" in csvfile_name:
            write_list_2d(excel_workbook['2-7) 空調機'], csvdata[10:], 11, 1)

        elif "様式3-1" in csvfile_name:
            write_list_2d(excel_workbook['3-1) 換気室'], csvdata[10:], 11, 1)

        elif "様式3-2" in csvfile_name:
            write_list_2d(excel_workbook['3-2) 換気送風機'], csvdata[10:], 11, 1)

        elif "様式3-3" in csvfile_name:
            write_list_2d(excel_workbook['3-3) 換気空調機'], csvdata[10:], 11, 1)

        elif "様式4" in csvfile_name:
            write_list_2d(excel_workbook['4) 照明'], csvdata[10:], 11, 1)

        elif "様式5-1" in csvfile_name:
            write_list_2d(excel_workbook['5-1) 給湯室'], csvdata[10:], 11, 1)

        elif "様式5-2" in csvfile_name:
            write_list_2d(excel_workbook['5-2) 給湯機器'], csvdata[10:], 11, 1)

        elif "様式6" in csvfile_name:
            write_list_2d(excel_workbook['6) 昇降機'], csvdata[10:], 11, 1)

        elif "様式7-1" in csvfile_name:
            write_list_2d(excel_workbook['7-1) 太陽光発電'], csvdata[10:], 11, 1)

        elif "様式7-3" in csvfile_name:
            write_list_2d(excel_workbook['7-3) コージェネレーション設備'], csvdata[10:], 11, 1)

        elif "様式8" in csvfile_name:
            write_list_2d(excel_workbook['8) 非空調外皮'], csvdata[10:], 11, 1)

        elif "様式9" in csvfile_name:
            write_list_2d(excel_workbook['9) モデル建物'], csvdata[10:], 11, 1)

    # 出力
    excel_workbook.save(output_filename + ".xlsm")


if __name__ == '__main__':

    csv2excel("sample", "テスト")