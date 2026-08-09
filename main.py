"""
builelib FastAPI メインモジュール

エンドポイント一覧:
    GET  /calculate              - Excelファイルベースの計算（後方互換）
    POST /calculate              - JSON入力データで計算し結果を返す
    POST /validate               - 入力データのバリデーション（計算なし）
    GET  /schema                 - webproJsonSchema.json を返す
    GET  /options                - 入力値の選択肢一覧を返す
    POST /project/{id}/save      - プロジェクトを保存する
    GET  /project/{id}           - 保存されたプロジェクトを読み込む
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from builelib.runner import calculate, calculate_from_json
from builelib.input.make_inputdata import get_input_options, normalize_input
from builelib import database_loader


# ----------------------------------------------------------------
# アプリ初期化
# ----------------------------------------------------------------
app = FastAPI(
    title="builelib API",
    version="2.3.0",
    description="非住宅建築物エネルギー消費量計算 API",
    docs_url="/docs",
    redoc_url="/redoc",
)

# 共有データディレクトリ
SHARED_DATA_DIR = Path(os.environ.get("BUILELIB_DATA_DIR", "/usr/src/data"))

# リクエストボディの上限（既定値: 30 MiB）
MAX_REQUEST_BODY_BYTES = int(
    os.environ.get("BUILELIB_MAX_REQUEST_BODY_BYTES", str(30 * 1024 * 1024))
)

# CORS許可元。複数指定する場合はカンマ区切りで設定する。
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "BUILELIB_CORS_ALLOWED_ORIGINS",
        "https://builelib.net",
    ).split(",")
    if origin.strip()
]


@app.middleware("http")
async def limit_request_body_size(request: Request, call_next):
    """POST等のリクエストボディが上限を超える場合は拒否する。"""
    if request.method not in {"POST", "PUT", "PATCH"}:
        return await call_next(request)

    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            declared_size = int(content_length)
        except ValueError:
            return JSONResponse(status_code=400, content={"detail": "Content-Length が不正です"})
        if declared_size < 0:
            return JSONResponse(status_code=400, content={"detail": "Content-Length が不正です"})
        if declared_size > MAX_REQUEST_BODY_BYTES:
            return JSONResponse(
                status_code=413,
                content={"detail": "リクエストサイズが上限を超えています"},
            )

    # Content-Length が省略・偽装された場合に備えて実データ量も確認する。
    body = await request.body()
    if len(body) > MAX_REQUEST_BODY_BYTES:
        return JSONResponse(
            status_code=413,
            content={"detail": "リクエストサイズが上限を超えています"},
        )

    return await call_next(request)


# CORS設定（本番環境では builelib.net のみ許可）
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

# プロジェクト保存ディレクトリ（永続ボリューム /usr/src/data にマウントされる）
PROJECTS_DIR = Path(
    os.environ.get("BUILELIB_PROJECTS_DIR", str(SHARED_DATA_DIR / "projects"))
)

# Excelファイルベース計算で許可する拡張子
ALLOWED_INPUT_EXTENSIONS = {".xlsx", ".xlsm"}

# JSONスキーマのパス
_SCHEMA_PATH = Path(__file__).parent / "src/builelib/input/inputdata/webproJsonSchema.json"

# JSONスキーマのキャッシュ（起動時に1回だけ読み込む）
_CACHED_SCHEMA: dict | None = None


def _get_schema() -> dict:
    """JSONスキーマをキャッシュ付きで返す"""
    global _CACHED_SCHEMA
    if _CACHED_SCHEMA is None:
        if not _SCHEMA_PATH.exists():
            raise FileNotFoundError(f"スキーマファイルが見つかりません: {_SCHEMA_PATH}")
        with open(_SCHEMA_PATH, encoding="utf-8") as f:
            _CACHED_SCHEMA = json.load(f)
    return _CACHED_SCHEMA


def _normalize_project_id(project_id: str) -> str:
    """project_id をUUID v4として検証し、正規化した文字列を返す。"""
    try:
        parsed_id = uuid.UUID(project_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="project_id はUUID v4形式で指定してください")

    if parsed_id.version != 4:
        raise HTTPException(status_code=400, detail="project_id はUUID v4形式で指定してください")

    return str(parsed_id)


def _resolve_calculation_file(file_name: str) -> Path:
    """計算対象が共有データ領域内の許可されたExcelファイルであることを確認する。"""
    shared_data_dir = SHARED_DATA_DIR.resolve()
    requested_path = Path(file_name)
    if not requested_path.is_absolute():
        requested_path = shared_data_dir / requested_path
    resolved_path = requested_path.resolve()

    try:
        resolved_path.relative_to(shared_data_dir)
    except ValueError:
        raise HTTPException(
            status_code=403,
            detail="共有データ領域外のファイルは指定できません",
        )

    if resolved_path.suffix.lower() not in ALLOWED_INPUT_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="計算対象は .xlsx または .xlsm ファイルに限定されています",
        )

    if not resolved_path.is_file():
        raise HTTPException(status_code=404, detail="計算対象ファイルが見つかりません")

    return resolved_path


# ----------------------------------------------------------------
# Pydantic モデル（Pydantic v2 対応）
# ----------------------------------------------------------------

class BuildingInputData(BaseModel):
    """POST /calculate および POST /project/{id}/save のリクエストボディ

    webproJsonSchema に準拠した建物入力データ。
    Building と Rooms のみ必須。その他の設備は省略可能。
    """

    model_config = {"extra": "allow"}   # スキーマ外のフィールド（平面図データ等）も許容

    # 必須フィールド
    Building: dict[str, Any]
    Rooms: dict[str, Any]

    # 設備フィールド（省略可能）
    CalculationMode:       dict[str, Any] | None = None
    EnvelopeSet:           dict[str, Any] | None = None
    WallConfigure:         dict[str, Any] | None = None
    WindowConfigure:       dict[str, Any] | None = None
    ShadingConfigure:      dict[str, Any] | None = None
    AirConditioningZone:   dict[str, Any] | None = None
    HeatsourceSystem:      dict[str, Any] | None = None
    SecondaryPumpSystem:   dict[str, Any] | None = None
    AirHandlingSystem:     dict[str, Any] | None = None
    VentilationRoom:       dict[str, Any] | None = None
    VentilationUnit:       dict[str, Any] | None = None
    LightingSystems:       dict[str, Any] | None = None
    HotwaterRoom:          dict[str, Any] | None = None
    HotwaterSupplySystems: dict[str, Any] | None = None
    Elevators:             dict[str, Any] | None = None
    PhotovoltaicSystems:   dict[str, Any] | None = None
    CogenerationSystems:   dict[str, Any] | None = None
    SpecialInputData:      dict[str, Any] | None = None


class CalculateResponse(BaseModel):
    """POST /calculate のレスポンス"""
    result: dict[str, Any]
    errors: list[str]


class ValidationResponse(BaseModel):
    """POST /validate のレスポンス"""
    valid: bool
    errors: list[str]
    warnings: list[str]


class ProjectSaveResponse(BaseModel):
    """POST /project/{id}/save のレスポンス"""
    project_id: str
    saved_at: str


# ----------------------------------------------------------------
# エンドポイント
# ----------------------------------------------------------------

@app.get("/", summary="APIの稼働確認")
def root():
    """APIの稼働確認用エンドポイント"""
    return {
        "service": "builelib API",
        "version": "2.0.0",
        "docs": "/docs",
        "status": "running",
    }


@app.get("/calculate", summary="Excelファイルベースの計算", tags=["計算"])
def calculate_from_file(file_name: str):
    """
    既存のExcelファイルパスを指定して計算する。
    計算結果をファイル(json, CSV等)に書き出す。
    """
    input_path = _resolve_calculation_file(file_name)
    try:
        calculate(str(input_path))
        return {
            "status": "ok",
            "message": f"計算完了。結果ファイルを確認してください: {input_path.name}",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"計算エラー: {str(e)}")


@app.post("/calculate", response_model=CalculateResponse, summary="JSON入力データで計算", tags=["計算"])
def calculate_from_json_endpoint(inputdata: BuildingInputData):
    """
    webproJsonSchema準拠のJSONを受け取り、計算結果（BEI等）をレスポンスで返す。
    ファイル出力は行わない。

    リクエストボディ例:
    ```json
    {
        "Building": {
            "BuildingAddress": {"Region": "6", "AnnualSolarRegion": "A3"}
        },
        "Rooms": {
            "事務室_1": {
                "buildingType": "事務所等",
                "roomType": "事務室",
                "floorArea": 300.0
            }
        },
        "LightingSystems": { ... }
    }
    ```
    """
    # Pydanticモデルを dict に変換（None フィールドは除外）
    # → 計算エンジンの inputdata.get("AirConditioningZone") が正しく動作する
    input_dict = inputdata.model_dump(exclude_none=True)

    # 英語表示値を日本語DBキーに変換（日本語入力はそのまま通過）
    normalize_input(input_dict)

    try:
        calc_output = calculate_from_json(input_dict)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"計算エラー: {str(e)}")

    return CalculateResponse(
        result=calc_output["result"],
        errors=calc_output["errors"],
    )


@app.post("/validate", response_model=ValidationResponse, summary="入力データのバリデーション", tags=["バリデーション"])
def validate_input(inputdata: dict[str, Any]):
    """
    入力データを計算せずにJSONスキーマでバリデーションする。
    フォーム入力中のリアルタイム検証に使用する。

    - 部分的なデータ（Building・Rooms が省略されていても）を受け付ける
    - スキーマ違反のフィールドをすべてリストアップして返す
    """
    errors: list[str] = []
    warnings: list[str] = []

    try:
        schema = _get_schema()
        validator = jsonschema.Draft7Validator(schema)
        validation_errors = sorted(
            validator.iter_errors(inputdata),
            key=lambda e: list(e.path)
        )
        for error in validation_errors:
            path = " -> ".join(str(p) for p in error.path) if error.path else "root"
            errors.append(f"[{path}] {error.message}")
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        errors.append(f"バリデーション処理エラー: {str(e)}")

    return ValidationResponse(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


@app.get("/schema", summary="JSONスキーマを返す", tags=["メタデータ"])
def get_json_schema():
    """
    webproJsonSchema.json の内容をそのまま返す。
    フロントエンドの動的フォーム生成に使用する。
    """
    try:
        return _get_schema()
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"スキーマ読み込みエラー: {str(e)}")


@app.get("/options", summary="入力値の選択肢一覧を返す", tags=["メタデータ"])
def get_options(lang: str = "ja"):
    """
    入力値の選択肢一覧を返す。
    フロントエンドのドロップダウン生成に使用する。

    - `lang=ja`（デフォルト）: 日本語の選択肢リスト（従来動作）
    - `lang=en`: 英語の選択肢リスト

    含まれる選択肢例:
    - 地域区分: ["1", "2", ..., "8"]
    - 建物用途: ["事務所等", "ホテル等", ...]  / lang=en: ["Office, etc.", "Hotel, etc.", ...]
    - 室用途: {"事務所等": ["事務室", ...], ...} / lang=en: {"Office, etc.": ["Office room", ...], ...}
    - 熱源機種: ["ウォータチリングユニット(空冷式)", ...]
    """
    try:
        options = get_input_options()
        if lang != "ja":
            options = database_loader.translate_input_options(options, lang)
        return options
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"オプション取得エラー: {str(e)}")


@app.post(
    "/project/{project_id}/save",
    response_model=ProjectSaveResponse,
    summary="プロジェクトを保存する",
    tags=["プロジェクト管理"],
)
def save_project(project_id: str, inputdata: BuildingInputData):
    """
    入力データをサーバーサイドに保存する。

    - project_id に "new" を指定すると、UUIDを自動採番する
    - 既存の project_id を指定すると上書き保存する
    - 保存先: PROJECTS_DIR/{project_id}.json
      （既定値: /usr/src/data/projects、BUILELIB_PROJECTS_DIR で変更可能）
    """
    # "new" の場合は UUID を自動採番
    if project_id == "new":
        project_id = str(uuid.uuid4())
    else:
        project_id = _normalize_project_id(project_id)

    # ディレクトリ作成
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

    save_path = PROJECTS_DIR / f"{project_id}.json"
    saved_at = datetime.now(timezone.utc).isoformat()

    try:
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "project_id": project_id,
                    "saved_at": saved_at,
                    "data": inputdata.model_dump(exclude_none=True),
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存エラー: {str(e)}")

    return ProjectSaveResponse(project_id=project_id, saved_at=saved_at)


@app.get("/project/{project_id}", summary="保存されたプロジェクトを読み込む", tags=["プロジェクト管理"])
def load_project(project_id: str):
    """
    保存されたプロジェクトの入力データを返す。

    レスポンス構造:
    ```json
    {
        "project_id": "uuid-...",
        "saved_at": "2025-01-01T00:00:00+00:00",
        "data": { ... 入力データ ... }
    }
    ```
    """
    project_id = _normalize_project_id(project_id)
    save_path = PROJECTS_DIR / f"{project_id}.json"

    if not save_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"プロジェクト '{project_id}' が見つかりません"
        )

    try:
        with open(save_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"読み込みエラー: {str(e)}")


# ----------------------------------------------------------------
# ローカル開発用（uvicorn 直接起動）
# ----------------------------------------------------------------
if __name__ == "__main__":
    
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
