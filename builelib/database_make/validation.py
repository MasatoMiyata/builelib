import jsonschema
import json

targetFile = 'REFLIST.json'
schemaFile = './builelib/database_make/schema/q_room_COEFFI_schema.json'

# スキーマの読み込み
with open(schemaFile, encoding='utf-8') as file_obj:
    schema_data = json.load(file_obj)

# インプットデータの読み込み
with open(targetFile, encoding='utf-8') as file_obj:
    check_data = json.load(file_obj)


# バリデーションの実行
try:
    jsonschema.validate(check_data, schema_data)
except jsonschema.ValidationError as e:
    print(e.message)
