"""類似プレスリリース検索APIで使用するスキーマ

## 共通事項
- BaseModelではルーター層で使用する関数の引数として認識しないため、リクエストは標準ライブラリのdataclassで定義する

## hitsについて
全てのヒット件数ではなく、top_nに対して実際に取得できた件数のこと(意味検索の候補プールは
release_search_corpus全体のためtop_nに満たないことは通常ないが、念のため保持する)。
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Annotated

from fastapi import Query
from pydantic import BaseModel, Field

# 検索クエリの最大文字数(埋め込み推論の負荷を抑えるための上限。過去のリード文実測の最大値(500字)に十分な余裕を持たせた)
MAX_QUERY_LENGTH = 2000


@dataclass
class SearchReleaseRequest:
    """類似プレスリリース検索APIのリクエスト"""

    query: Annotated[str, Query(max_length=MAX_QUERY_LENGTH, description="作成中のプレスリリースのリード文")]
    top_n: Annotated[int, Query(ge=1, le=100, description="取得する類似リリースの件数")] = 10


# ==========================================
# プレスリリース1件のデータスキーマ
# ==========================================


class ReleaseItem(BaseModel):
    """レスポンスに含まれる類似プレスリリース1件あたりのデータ"""

    # --- 識別子(release本体・関連テーブルへの再JOINに使うキー) ---
    company_id: int = Field(..., description="企業ID")
    release_id: int = Field(..., description="プレスリリースID(company_id内で採番されるため単独では一意にならない)")
    # --- 検索スコア ---
    similarity_score: float = Field(..., description="入力文との類似度(コサイン類似度。1に近いほど類似)")
    # --- release本体 ---
    title: str = Field(..., description="タイトル")
    subtitle: str = Field(..., description="サブタイトル")
    lead_paragraph: str = Field(..., description="リード文")
    created_at: datetime = Field(..., description="作成日時")
    # --- company ---
    company_name: str = Field(..., description="企業名")
    industry: str = Field(..., description="業種")
    # --- release_statistic(都度取得。release_search_corpus投入時点のスナップショットではない) ---
    page_view: int = Field(..., description="ページビュー数")
    unique_user: int = Field(..., description="ユニークユーザー数")
    like_count: int = Field(..., description="お気に入り数")
    # --- タグ系 ---
    business_categories: list[str] = Field(..., description="事業カテゴリ")
    keywords: list[str] = Field(..., description="キーワードタグ(sort_priority順)")


# ==========================================
# API全体のレスポンススキーマ
# ==========================================


class SearchReleaseResponse(BaseModel):
    """類似プレスリリース検索APIのレスポンス"""

    query: str = Field(..., description="入力された検索クエリ")
    top_n: int = Field(..., description="指定された取得件数")
    hits: int = Field(..., description="実際に取得できた件数")
    data: list[ReleaseItem] = Field(..., description="類似度順の検索結果リスト")
