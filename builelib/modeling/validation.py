import jsonschema
import json

# スキーマの読み込み
with open('webproJsonSchema.json') as file_obj:
    schema_data = json.load(file_obj)

# インプットデータの読み込み
with open('inputdata.json') as file_obj:
    check_data = json.load(file_obj)


# バリデーションの実行
try:
    jsonschema.validate(check_data, schema_data)
except jsonschema.ValidationError as e:
    print(e.message)
