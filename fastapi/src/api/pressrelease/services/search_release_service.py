"""類似プレスリリース検索APIで使用するサービスロジック"""

from __future__ import annotations

from typing import TYPE_CHECKING

from psycopg import sql
from psycopg.rows import dict_row

from src.api.pressrelease.services.models import ReleaseSearchResult

# 環境変数(次元数)
from src.core.config import settings

# HNSW索引の探索候補数の設定
from src.shared.services.vector_index_service import apply_ef_search

# 自然言語処理(埋め込み推論)
from src.shared.utils.nlp_process import get_query_vector

if TYPE_CHECKING:
    from psycopg import AsyncConnection

    from src.api.pressrelease.schemas.search_release_schema import SearchReleaseRequest


async def execute_release_search(
    conn: AsyncConnection,
    request: SearchReleaseRequest,
) -> ReleaseSearchResult:
    """入力文に類似するプレスリリースを意味検索で取得する

    release_search_corpus(lead_paragraph_vectorを持つ検索コーパス)に対してHNSW近傍探索を行い、
    上位top_n件の(company_id, release_id)を得た上で、表示用データはrelease本体・company・
    release_statistic・タグ系テーブルへ再JOINして取得する(release_search_corpusは索引としてのみ使う)。

    キーワード検索・ハイブリッド検索・日付等の絞り込みは持たない意味検索のみのシンプルな構成のため、
    hybrid時に複数コネクションを並列使用する特許検索とは異なり、単一コネクションで完結する。

    Args:
        conn (AsyncConnection): DB接続
        request (SearchReleaseRequest): 検索リクエスト(入力文・取得件数)

    Returns:
        ReleaseSearchResult: 取得件数, 検索結果

    """
    # 検索クエリのベクトル化(CPUバウンドのためスレッドへ退避される)
    vector = await get_query_vector(request.query)

    params = {"vector": vector, "top_n": request.top_n}

    # ==========================================
    # 候補抽出(意味検索) + 表示用データの再JOIN を1クエリで行う
    #
    # - candidates: release_search_corpusに対するHNSW近傍探索。次元数の型キャストは
    #   HNSWインデックス作成時(A3_init_vector_index.py)と完全に一致させる必要がある
    #   (一致しないとインデックスが使われず全件スキャンになる)
    # - business_categories / keywords は1リリースにつき複数行になるため、
    #   LATERALサブクエリでarray_aggに集約する(該当なしの場合はCOALESCEで空配列にする)
    # ==========================================
    search_sql_template = sql.SQL("""
        WITH candidates AS (
            SELECT
                company_id, release_id,
                -- コサイン類似度(Cosine Similarity)は `1 - コサイン距離` で計算可能
                1 - ((lead_paragraph_vector::vector({dimension})) <=> %(vector)s::vector) AS similarity_score
            FROM
                release_search_corpus
            WHERE
                lead_paragraph_vector IS NOT NULL
            ORDER BY
                -- 類似度スコア順に並べ替え(ここでも次元数の型変換を加える)
                (lead_paragraph_vector::vector({dimension})) <=> %(vector)s::vector,
                -- スコアが同点の場合の順序を一意に確定させる第2ソートキー
                company_id, release_id
            LIMIT %(top_n)s
        )
        SELECT
            cand.company_id, cand.release_id, cand.similarity_score,
            r.title, r.subtitle, r.lead_paragraph, r.created_at,
            co.company_name, ind.industry_name AS industry,
            st.page_view, st.unique_user, st.like_count,
            COALESCE(bc_agg.business_categories, ARRAY[]::text[]) AS business_categories,
            COALESCE(kw_agg.keywords, ARRAY[]::text[]) AS keywords
        FROM
            candidates cand
        JOIN release r ON r.company_id = cand.company_id AND r.release_id = cand.release_id
        JOIN company co ON co.company_id = cand.company_id
        LEFT JOIN industry ind ON ind.industry_id = co.industry_id
        JOIN release_statistic st ON st.company_id = cand.company_id AND st.release_id = cand.release_id
        LEFT JOIN LATERAL (
            SELECT array_agg(bc.business_category_name ORDER BY rbc.main_flg DESC) AS business_categories
            FROM release_business_category rbc
            JOIN business_category bc ON bc.business_category_id = rbc.business_category_id
            WHERE rbc.company_id = cand.company_id AND rbc.release_id = cand.release_id
        ) bc_agg ON true
        LEFT JOIN LATERAL (
            SELECT array_agg(k.keyword_name ORDER BY rk.sort_priority) AS keywords
            FROM release_keyword rk
            JOIN keyword k ON k.keyword_id = rk.keyword_id
            WHERE rk.company_id = cand.company_id AND rk.release_id = cand.release_id
        ) kw_agg ON true
        ORDER BY
            cand.similarity_score DESC;
    """)

    search_sql = search_sql_template.format(dimension=sql.Literal(settings.EMBEDDING_DIMENSION))

    async with conn.cursor(row_factory=dict_row) as cursor:
        # HNSWの探索候補数をtop_nに合わせる(既定値の40ではtop_n件に届かない場合がある)
        await apply_ef_search(cursor, request.top_n)
        await cursor.execute(search_sql, params)
        results = await cursor.fetchall()

    return ReleaseSearchResult(hits=len(results), data=results)
