"""
builelib FastAPI エンドポイント テスト（フェーズ1）

pytest + FastAPI TestClient を使用。
サーバーを別途起動する必要はなくpytest 単体で実行。

実行方法:
    cd builelib-package/builelib
    pytest tests/test_api.py -v
"""

import json
import sys
import os
import pytest

# main.py が builelib/ 直下にあるため sys.path に追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


# ================================================================
# フィクスチャ
# ================================================================

@pytest.fixture
def minimal_payload():
    """Building + Rooms のみの最小構成ペイロード"""
    return {
        "Building": {
            "BuildingAddress": {
                "Region": "6",
                "AnnualSolarRegion": "A3"
            }
        },
        "Rooms": {
            "1F_事務室": {
                "buildingType": "事務所等",
                "roomType": "事務室",
                "roomArea": 300.0
            }
        }
    }


@pytest.fixture
def sample_001_payload():
    """Builelib_inputSheet_sample_001 から生成した入力 JSON（フル計算用）"""
    json_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "examples", "sample_001_input.json"
    )
    if not os.path.exists(json_path):
        pytest.skip(f"サンプル JSON が見つかりません: {json_path}")
    with open(json_path, encoding="utf-8") as f:
        return json.load(f)


# ================================================================
# GET /  — 稼働確認
# ================================================================

def test_root_returns_running_status():
    """GET / が正常なステータス情報を返す"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert data["service"] == "builelib API"
    assert "version" in data
    assert "docs" in data


# ================================================================
# GET /options  — 選択肢一覧
# ================================================================

def test_options_returns_categories():
    """GET /options が選択肢辞書を返す"""
    response = client.get("/options")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert len(data) >= 10  # 39カテゴリ


def test_options_contains_required_keys():
    """GET /options に必須カテゴリが含まれる"""
    response = client.get("/options")
    data = response.json()
    assert "建物用途" in data
    assert "地域区分" in data
    assert "室用途" in data
    assert "熱源機種" in data


def test_options_building_types():
    """建物用途が9種類含まれる"""
    response = client.get("/options")
    data = response.json()
    building_types = data["建物用途"]
    assert "事務所等" in building_types
    assert "ホテル等" in building_types
    assert "病院等" in building_types
    assert len(building_types) == 9


def test_options_region_codes():
    """地域区分が1〜8の8種類含まれる"""
    response = client.get("/options")
    data = response.json()
    assert data["地域区分"] == ["1", "2", "3", "4", "5", "6", "7", "8"]


# ================================================================
# GET /schema  — JSON スキーマ
# ================================================================

def test_schema_returns_json_schema():
    """GET /schema が webproJsonSchema を返す"""
    response = client.get("/schema")
    assert response.status_code == 200
    data = response.json()
    assert data.get("title") == "Builelib Input Data JSON Schema"
    assert data.get("type") == "object"
    assert "properties" in data


def test_schema_has_required_top_level_properties():
    """スキーマに主要なトップレベルプロパティが含まれる"""
    response = client.get("/schema")
    data = response.json()
    props = data["properties"]
    assert "Building" in props
    assert "Rooms" in props
    assert "LightingSystems" in props
    assert "AirConditioningZone" in props


def test_schema_is_cached():
    """GET /schema を2回呼んでも同じ結果が返る（キャッシュ確認）"""
    r1 = client.get("/schema")
    r2 = client.get("/schema")
    assert r1.json() == r2.json()


# ================================================================
# POST /validate  — バリデーション
# ================================================================

def test_validate_missing_building_is_invalid():
    """Building が欠けていると valid=False"""
    payload = {"Rooms": {"1F_test": {"buildingType": "事務所等"}}}
    response = client.post("/validate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert any("Building" in e for e in data["errors"])


def test_validate_missing_rooms_is_invalid():
    """Rooms が欠けていると valid=False"""
    payload = {"Building": {"BuildingAddress": {"Region": "6"}}}
    response = client.post("/validate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert any("Rooms" in e for e in data["errors"])


def test_validate_empty_object_is_invalid():
    """空オブジェクト {} は valid=False"""
    response = client.post("/validate", json={})
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False


def test_validate_response_has_required_fields():
    """レスポンスに valid / errors / warnings フィールドが存在する"""
    response = client.post("/validate", json={})
    data = response.json()
    assert "valid" in data
    assert "errors" in data
    assert "warnings" in data
    assert isinstance(data["errors"], list)
    assert isinstance(data["warnings"], list)


# ================================================================
# POST /calculate  — JSON 直接計算
# ================================================================

def test_calculate_requires_building_and_rooms():
    """Building または Rooms が欠けると 422 エラー"""
    response = client.post("/calculate", json={"Rooms": {}})
    assert response.status_code == 422  # Pydantic バリデーションエラー


def test_calculate_returns_result_structure(minimal_payload):
    """POST /calculate が result + errors 構造を返す"""
    response = client.post("/calculate", json=minimal_payload)
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    assert "errors" in data
    assert isinstance(data["result"], dict)
    assert isinstance(data["errors"], list)


def test_calculate_result_has_bei_keys(minimal_payload):
    """result に BEI 関連キーが含まれる"""
    response = client.post("/calculate", json=minimal_payload)
    data = response.json()
    result = data["result"]
    assert "BEI" in result
    assert "BEI_AC" in result
    assert "BEI_V" in result
    assert "BEI_L" in result
    assert "設計一次エネルギー消費量[MJ]" in result
    assert "基準一次エネルギー消費量[MJ]" in result


def test_calculate_full_sample(sample_001_payload):
    """sample_001 のフル計算で BEI が期待値と一致する"""
    response = client.post("/calculate", json=sample_001_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["errors"] == [], f"計算エラーが発生: {data['errors']}"

    result = data["result"]
    # BEI = 0.83 を確認（±0.01 の許容誤差）
    assert abs(result["BEI"] - 0.83) < 0.01, f"BEI が期待値と異なる: {result['BEI']}"
    assert abs(result["BEI_AC"] - 0.96) < 0.01
    assert abs(result["BEI_V"]  - 0.91) < 0.01
    assert abs(result["BEI_L"]  - 0.82) < 0.01


def test_calculate_no_file_output(tmp_path, minimal_payload):
    """POST /calculate がカレントディレクトリに result.json を出力しない"""
    # ※ calc_energy() の output_dir="" 問題のため、この検証は参考値
    #    将来 output_dir=None 対応後に強化する
    import glob
    before = set(glob.glob("*.json"))
    client.post("/calculate", json=minimal_payload)
    after = set(glob.glob("*.json"))
    new_files = after - before
    # result_XX.json 系のファイルが増えていないことを確認
    api_result_files = [f for f in new_files if f.startswith("result_")]
    assert api_result_files == [], f"意図しないファイルが出力されました: {api_result_files}"


# ================================================================
# POST /project/{id}/save + GET /project/{id}  — プロジェクト管理
# ================================================================

def test_save_project_with_new_generates_uuid(minimal_payload):
    """project_id=new で保存すると UUID が採番される"""
    response = client.post("/project/new/save", json=minimal_payload)
    assert response.status_code == 200
    data = response.json()
    assert "project_id" in data
    assert "saved_at" in data
    # UUID フォーマット確認（8-4-4-4-12）
    pid = data["project_id"]
    parts = pid.split("-")
    assert len(parts) == 5


def test_save_and_load_project_roundtrip(minimal_payload):
    """保存したプロジェクトを読み込むと同じデータが返る"""
    # 保存
    save_resp = client.post("/project/new/save", json=minimal_payload)
    assert save_resp.status_code == 200
    project_id = save_resp.json()["project_id"]

    # 読み込み
    load_resp = client.get(f"/project/{project_id}")
    assert load_resp.status_code == 200
    loaded = load_resp.json()

    assert loaded["project_id"] == project_id
    assert "data" in loaded
    assert loaded["data"]["Building"] == minimal_payload["Building"]
    assert loaded["data"]["Rooms"] == minimal_payload["Rooms"]


def test_save_project_with_explicit_id(minimal_payload):
    """明示的な project_id で保存・上書きができる"""
    pid = "test-project-explicit-id-12345"
    r1 = client.post(f"/project/{pid}/save", json=minimal_payload)
    assert r1.status_code == 200
    assert r1.json()["project_id"] == pid

    # 上書き保存
    r2 = client.post(f"/project/{pid}/save", json=minimal_payload)
    assert r2.status_code == 200
    assert r2.json()["project_id"] == pid


def test_load_nonexistent_project_returns_404():
    """存在しない project_id は 404 を返す"""
    response = client.get("/project/this-project-does-not-exist-xyz-999")
    assert response.status_code == 404


def test_calculate_endpoint_accepts_extra_fields():
    """extra='allow' により、平面図データ等の追加フィールドを受け付ける"""
    payload = {
        "Building": {"BuildingAddress": {"Region": "6", "AnnualSolarRegion": "A3"}},
        "Rooms": {"1F_test": {"buildingType": "事務所等", "roomType": "事務室", "roomArea": 100.0}},
        "_floorPlanPolygons": {"1F_test": [[0, 0], [10000, 0], [10000, 10000], [0, 10000]]},
    }
    response = client.post("/calculate", json=payload)
    # 422 ではなく 200 が返ること（追加フィールドを拒否しない）
    assert response.status_code == 200
