import jsonschema
import json

targetFile = 'QROOM_COEFFI_AREA1.json'
schemaFile = 'QROOM_COEFFI_schema.json'

# スキーマの読み込み
with open(schemaFile) as file_obj:
    schema_data = json.load(file_obj)

# インプットデータの読み込み
with open(targetFile) as file_obj:
    check_data = json.load(file_obj)


# バリデーションの実行
try:
    jsonschema.validate(check_data, schema_data)
except jsonschema.ValidationError as e:
    print(e.message)
