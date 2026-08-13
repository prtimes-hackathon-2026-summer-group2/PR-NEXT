"""プレスリリース関連のエンドポイント"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from psycopg import AsyncConnection

# DB接続
from src.core.database import get_db_connection

# スキーマ
from .schemas.search_release_schema import SearchReleaseRequest, SearchReleaseResponse

# サービスロジック
from .services import search_release_service

router = APIRouter(prefix="/press-release", tags=["press-release"])

# ============================================================
# 類似プレスリリース検索APIエンドポイント
# ============================================================


@router.get(
    path="/search",
    response_model_exclude_none=True,
    summary="類似プレスリリース検索API",
)
async def search_similar_releases_endpoint(
    request: Annotated[SearchReleaseRequest, Depends()],
    conn: Annotated[AsyncConnection, Depends(get_db_connection)],
) -> SearchReleaseResponse:
    """## 類似プレスリリース検索API

    作成中のプレスリリースのリード文を入力として、意味的に類似する過去のプレスリリースを
    類似度順に取得します。

    ### 検索対象について
    全リリースではなく、以下の基準であらかじめ選定した`release_search_corpus`(1万件)が対象です。

    - 作成日時が現在時刻から5年以上前
    - リード文が空文字でない
    - 上記を満たす中でページビュー数が上位1万件

    経過年数・PVともに一定水準を満たすリリースのみを対象にすることで、
    「中長期的に一定の影響を持ったプレスリリース」との類似度を見る用途を想定しています。

    ### 絞り込みについて
    日付・カテゴリ等による絞り込みは現時点では持たず、入力文のみを受け取るシンプルな構成です。
    """
    # --- 想定内の例外処理 (想定外はグローバル例外ハンドラに投げる) ---
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="検索クエリを入力してください")

    # --- 検索処理実行 ---
    search_result = await search_release_service.execute_release_search(
        conn=conn,
        request=request,
    )

    # --- レスポンス構築 ---
    response_json = {
        "query": request.query,
        "top_n": request.top_n,
        "hits": search_result.hits,
        "data": search_result.data,
    }

    return SearchReleaseResponse.model_validate(response_json)
