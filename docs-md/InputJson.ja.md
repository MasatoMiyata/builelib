# 入力JSON仕様

このページは、Builelib が受け取る入力JSONの仕様を説明します。  
他のプログラムから入力JSONを作成・検証するときは、次の3つを添付または参照してください。

| ファイル | 役割 |
| --- | --- |
| `src/builelib/input/inputdata/webproJsonSchema.json` | 構造、型、必須項目、数値範囲、固定選択肢を検証するJSON Schema |
| `src/builelib/input/inputdata/input_options.json` | データベース由来の選択肢一覧 |
| `docs-md/InputJson.ja.md` | 人間向けの説明書 |

APIを使う場合は、同じ情報を `/schema`、`/options`、`/validate` から取得・検証できます。

## 基本方針

入力JSONの機械可読な正本は `webproJsonSchema.json` です。  
このスキーマは JSON Schema Draft-07 形式で、`jsonschema` などの一般的な検証ライブラリで利用できます。

選択肢のうち、建物用途、室用途、方位、設備方式などデータベースから生成されるものは `input_options.json` を参照します。  
`webproJsonSchema.json` に固定で記載されている `enum` と、`input_options.json` の両方を確認することで、他プログラム側でも入力値を安定して検証できます。

`SpecialInputData` は任意拡張領域です。現時点では仕様が固定されていないため、詳細なスキーマ制約は設けません。

## 全体構造

入力JSONはオブジェクトです。トップレベルには次のセクションを持ちます。

| キー | 必須 | 役割 |
| --- | --- | --- |
| `Building` | 必須 | 建物全体の基本情報 |
| `Rooms` | 必須 | 室の一覧 |
| `EnvelopeSet` | 任意 | 外皮構成と開口部の割り当て |
| `WallConfigure` | 任意 | 外壁・屋根などの断熱仕様 |
| `WindowConfigure` | 任意 | 窓仕様 |
| `ShadingConfigure` | 任意 | 日よけ仕様 |
| `AirConditioningZone` | 任意 | 空調ゾーン |
| `HeatsourceSystem` | 任意 | 熱源システム |
| `SecondaryPumpSystem` | 任意 | 二次ポンプシステム |
| `AirHandlingSystem` | 任意 | 空調機システム |
| `VentilationRoom` | 任意 | 換気対象室 |
| `VentilationUnit` | 任意 | 換気設備 |
| `LightingSystems` | 任意 | 照明設備 |
| `HotwaterRoom` | 任意 | 給湯対象室 |
| `HotwaterSupplySystems` | 任意 | 給湯設備 |
| `Elevators` | 任意 | 昇降機 |
| `PhotovoltaicSystems` | 任意 | 太陽光発電設備 |
| `CogenerationSystems` | 任意 | コージェネレーション設備 |
| `SpecialInputData` | 任意 | Builelib独自の拡張入力 |
| `CalculationMode` | 任意 | 計算モード、SPシート有効フラグ、一次エネルギー換算係数など |

最小構成では `Building` と `Rooms` が必要です。設備を計算対象にする場合は、対応するセクションを追加します。

```json
{
  "Building": {
    "Name": "サンプル建物",
    "Region": "6",
    "AnnualSolarRegion": "A3",
    "BuildingFloorArea": 1000.0
  },
  "Rooms": {
    "1F_事務室": {
      "buildingType": "事務所等",
      "roomType": "事務室",
      "roomArea": 100.0
    }
  }
}
```

## IDキーと参照関係

多くのセクションは、任意の名称をキーにしたオブジェクトです。  
たとえば `Rooms` では `"1F_事務室"` が室ID、`PhotovoltaicSystems` では `"太陽光A"` が設備IDになります。

IDキーは、同じJSON内の他セクションから参照されます。例として、換気、照明、給湯、昇降機などの室別入力は `Rooms` の室IDと対応します。

主な依存関係は次のとおりです。

| セクション | 前提となるセクション |
| --- | --- |
| `EnvelopeSet` | `Building`, `Rooms`, `WallConfigure`, `WindowConfigure` |
| `VentilationRoom` | `Building`, `Rooms`, `VentilationUnit` |
| `LightingSystems` | `Building`, `Rooms` |
| `HotwaterRoom` | `Building`, `Rooms`, `HotwaterSupplySystems` |
| `Elevators` | `Building`, `Rooms` |

参照先IDが存在するかどうかの厳密なクロスチェックは、JSON Schemaだけでは表現しきれません。計算前には `/validate` または Builelib の検証処理も併用してください。

## 型の読み方

JSON Schemaでは、各項目の型を次のように表します。

| 型 | 意味 |
| --- | --- |
| `string` | 文字列 |
| `number` | 数値。整数も小数も含みます |
| `boolean` | `true` または `false` |
| `null` | 値なし |
| `object` | キーと値を持つオブジェクト |
| `array` | 配列 |

`type` が `["string", "null"]` のような配列の場合は、どちらの型も許容されます。  
`anyOf` は複数の条件のうち、いずれかを満たせば有効という意味です。

## 必須項目、範囲、既定値

各オブジェクトの `required` に記載された項目は必須です。  
`minimum` と `maximum` がある数値項目は、その範囲内の値を指定してください。  
`maxLength` がある文字列項目は、その文字数以下にしてください。

`default` は入力が省略された場合の参考値です。JSON Schema単体の検証では、通常は値を自動補完しません。Builelib がExcelからJSONを生成する処理では、項目によって既定値を設定します。

## 選択肢

選択肢は2種類あります。

| 種類 | 参照先 |
| --- | --- |
| スキーマ固定の選択肢 | `webproJsonSchema.json` の `enum` |
| データベース由来の選択肢 | `input_options.json` または `/options` |

`input_options.json` は `database_loader.get_input_options()` の結果です。  
室用途のように建物用途に依存する選択肢は、次のような階層構造になります。

```json
{
  "室用途": {
    "事務所等": [
      "事務室",
      "会議室"
    ]
  }
}
```

他プログラムでフォームや入力補完を作る場合は、`input_options.json` を使って選択肢を表示し、保存前に `webproJsonSchema.json` で構造を検証してください。

## SpecialInputData

`SpecialInputData` は、SPシートやBuilelib独自機能で使う任意拡張領域です。  
現在は、気象データ、任意の室使用条件、任意の熱源特性、時刻別負荷など、複数の拡張データを格納できます。

この領域は今後も変更される可能性があるため、今回の仕様では詳細な型や必須項目を固定しません。  
外部プログラムでは、`SpecialInputData` を省略可能な `object` として扱い、既知のキーだけを解釈してください。

## 推奨検証手順

他プログラムで入力JSONを使用する場合は、次の順序で検証してください。

1. JSONとして読み込めることを確認する。
2. `webproJsonSchema.json` で構造、型、必須項目、範囲を検証する。
3. `input_options.json` でDB由来の選択肢を確認する。
4. 必要に応じて `/validate` でBuilelib側の検証結果を確認する。
5. 計算実行前に、参照IDの対応関係を確認する。

!!! note
    `SpecialInputData.flow_control` で任意追加された制御方式など、一部の拡張値はBuilelibの検証処理でスキーマに動的注入されます。拡張入力を含むJSONでは、素の `webproJsonSchema.json` だけでなく `/validate` または `builelib.commons.inputdata_validation()` による検証を併用してください。

Pythonでの最小検証例です。

```python
import json
from jsonschema import Draft7Validator

with open("webproJsonSchema.json", encoding="utf-8") as f:
    schema = json.load(f)

with open("input.json", encoding="utf-8") as f:
    inputdata = json.load(f)

validator = Draft7Validator(schema)
errors = sorted(validator.iter_errors(inputdata), key=lambda e: list(e.path))

if errors:
    for error in errors:
        path = " -> ".join(str(p) for p in error.absolute_path) or "root"
        print(f"{path}: {error.message}")
else:
    print("valid")
```

## APIでの取得

Builelib APIを利用する場合は、次のエンドポイントを使えます。

| エンドポイント | 内容 |
| --- | --- |
| `GET /schema` | `webproJsonSchema.json` を返します |
| `GET /options` | 入力値の選択肢一覧を返します |
| `POST /validate` | 入力JSONを検証し、エラー一覧を返します |
