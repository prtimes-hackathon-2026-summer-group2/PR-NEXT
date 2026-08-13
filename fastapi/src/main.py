"""FastAPIのエントリーポイント

開発サーバー起動
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

uvicorn src.main:app --host 0.0.0.0 --port 8000
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# from fastapi.routing import APIRoute
# 環境変数 / グローバルリソース等
from src.core import global_resources
from src.core.config import settings
from src.core.database import database_manager
from src.core.device import get_device
from src.core.metadata import AppMetadata

# ==========================================
# ログ設定の初期化
# ==========================================

"""
DEBUG (10): 開発時の動作確認など、詳細な情報。
INFO (20): 正常な動作の記録。
WARNING (30): エラーではないが、注意が必要な状態。
ERROR (40): 重大な問題が発生し、一部の機能が実行できなかった状態。
CRITICAL (50): プログラム自体が停止してしまうような致命的なエラー。
"""

# --- ログの基本設定 ---
logging.basicConfig(
    # ログレベルの閾値: 設定したレベル以上のログだけが出力される
    level=logging.INFO,
    # 出力形式の定義: "発生日時 - レベル - ロガー名(発生場所) - メッセージ"
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)

# --- ロガーのインスタンス化 ---
# __name__: 実行中のモジュール名(ファイル名)が自動挿入
# --> どのファイルのどの部分でエラーが起きたのかを特定できる
logger = logging.getLogger(__name__)

# ==========================================
# ライフサイクルイベント(起動・終了時の処理)
# ==========================================


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator:
    """アプリケーションのライフサイクル管理

    - yield前: アプリ起動時の処理
    - yield後: アプリ終了時の処理
    """
    # --- 起動時の処理 ---
    print("アプリケーションを起動しています...")
    device = get_device()
    print(f"処理デバイス: {device}")
    # 機械学習モデル辞書の初期化
    # (数十秒かかる同期処理だが、リクエスト受付前でありイベントループを塞いでも影響がないためそのまま呼ぶ)
    global_resources.init_ml_models()
    print("データベースプールを初期化しています...")
    try:
        await database_manager.initialize()  # プールを作成・接続テスト
        print("データベース接続に成功しました。")
    except Exception as error:
        print(f"データベース接続に失敗しました。\n詳細: {error}")
        raise RuntimeError("Database connection failed.") from error
    print("アプリケーションを起動しました。リクエストを受け付けます。")

    yield  # ← ここでアプリケーションが実行される

    # --- 終了時の処理 ---
    print("アプリケーションを終了しています...")
    # グローバルリソースの削除
    global_resources.ml_models.clear()
    # コネクションプールのクローズ(借用中の接続の返却を待ってから閉じられる)
    await database_manager.close()
    print("アプリケーションを終了しました。")


# ==========================================
# アプリケーションのインスタンス化
# ==========================================

app = FastAPI(
    # メタデータ指定
    title=AppMetadata.TITLE,
    version=AppMetadata.VERSION,
    summary=AppMetadata.SUMMARY,
    description=AppMetadata.DESCRIPTION,
    openapi_tags=AppMetadata.TAGS,
    contact=AppMetadata.CONTACT,
    # ライフスパン指定
    lifespan=lifespan,
)

# ==========================================
# CORS設定
# ==========================================

# CORSはブラウザが利用者を保護するための仕組みであり、サーバー側のアクセス制御ではない。
# curlやスクリプトからのアクセスには一切効かないため、これを認証・認可の代わりにはしないこと。
# 許可オリジンは環境ごとに異なるため .env (CORS_ALLOW_ORIGINS) で指定する。
# ブラウザから直接呼び出さない構成(BFF経由でのサーバー間通信)であれば、空のままでよい。
if settings.CORS_ALLOW_ORIGIN_LIST:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ALLOW_ORIGIN_LIST,  # 許可する通信元URL
        allow_methods=["GET", "POST"],  # 許可するメソッド
        allow_headers=["*"],  # 許可するリクエストヘッダー
    )

# ==========================================
# ルーター登録
# ==========================================


# ==========================================
# アプリ全体に適用する例外ハンドリング
#
# エラーレスポンスの形
# 本APIが返すエラーは、ステータスコードによらず detail に人間可読な文字列を持つ。
# {"detail": "指定された法人は見つかりません。"}
#
# 利用側が「detailが文字列か配列か」を判定する分岐を書かずに済ませるための統一である。
# バリデーションエラー(422)のみ、フィールド単位の内訳を errors に併設する
# (detailは内訳を1行へ要約した文字列であり、他のステータスと同じく常に文字列)。
# ==========================================

def format_validation_errors(errors: list[dict]) -> str:
    """バリデーションエラーの内訳を、detail用の1行の文字列へ要約する

    Pydanticの loc は ("query", "limit") のように (パラメータの位置, フィールド名)
    の形を取る。先頭の位置情報を落としてフィールド名だけを取り出し、メッセージと
    組み合わせる。body直下のエラーなど、フィールド名まで特定できない場合は
    位置情報をそのまま使う。
    """
    formatted = []
    for error in errors:
        location = ".".join(str(part) for part in error["loc"][1:]) or str(error["loc"][0])
        formatted.append(f"{location}: {error['msg']}")
    return " / ".join(formatted)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, exception: RequestValidationError) -> JSONResponse:
    """リクエストのバリデーションエラー(422)を、本APIのエラー形に揃えて返す。

    FastAPIの既定のハンドラは detail にフィールド単位の配列をそのまま入れるため、
    detailが文字列である他のエラーと形が食い違う。detailは要約した文字列にし、
    元の内訳は errors に移す。
    """
    # jsonable_encoderを挟むのは、Pydanticのctxに例外オブジェクト等の
    # そのままではJSONへ変換できない値が含まれ得るため(FastAPIの既定実装と同じ)
    errors = jsonable_encoder(exception.errors())

    return JSONResponse(
        status_code=422,
        content={
            "detail": format_validation_errors(errors),
            "errors": errors,
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exception: Exception) -> JSONResponse:
    """アプリケーション全体でキャッチされなかった予期せぬ例外を処理する。

    サーバーには詳細なログを残し、クライアントには安全なメッセージを返す。
    想定内のエラー(ユーザー起因)については各ルーター内で明示的にキャッチ・発生させる。(404など)
    """
    # --- サーバーのログにレベル"ERROR"のスタックトレース(詳細)を出力 ---
    logger.error(
        "システムエラーが発生しました: %s %s",  # 変数を %s に置き換える
        request.method,  # 1つ目の %s に入る値
        request.url,  # 2つ目の %s に入る値
        exc_info=exception,  # 例外の詳細な発生経路を自動的に連結して出力
    )

    # クライアントには詳細を隠蔽した汎用的なエラーを返す
    return JSONResponse(
        status_code=500,
        content={"detail": "サーバー内部で予期せぬエラーが発生しました。しばらく経ってから再度お試しください。"},
    )




# ==========================================
# 動作確認用エンドポイント
# ==========================================


@app.get("/", tags=["health"], response_model=None)
def read_root() ->  dict:
    """ルートページ"""
    return {"document": "http://localhost:8000/docs"}


@app.get("/health", tags=["health"])
async def health_check() -> dict:
    """動作確認(データベースへの疎通確認を含む)

    プールが初期化済みか(closed/None)だけを見る方式では、個々のコネクションが
    切断されていても検知できないため、実際に1本借用してクエリを実行できるかで確認する。
    """
    try:
        async with database_manager.get_pool().connection(timeout=5) as conn:
            await conn.execute("SELECT 1")
    except Exception as error:
        logger.exception("ヘルスチェック: データベースへの疎通確認に失敗しました")
        raise HTTPException(status_code=503, detail="データベースに接続できません。") from error

    return {"status": "ok"}
