"""埋め込み処理を行う共有モジュール

Note:
    埋め込み推論はCPUバウンドな処理であり、`async def`の中でそのまま呼ぶと
    イベントループを占有して他のリクエストを巻き込んで停止させてしまう。
    そのため公開関数は`async def`とし、実処理は`asyncio.to_thread`でワーカースレッドへ逃がす。
    (末尾に`_sync`が付く関数が実処理本体で、モジュール外からは呼ばない)

"""

from __future__ import annotations

import asyncio

# 環境変数
from src.core.config import settings

# 機械学習モデル情報
from src.core.global_resources import ml_models

# 埋め込み推論の同時実行数を制限するセマフォ
# 1回の推論自体がライブラリ内部で複数コアを使うため、スレッドを増やすほど速くなるわけではなく、
# 制限しないとコアの奪い合い(スラッシング)で全リクエストのレイテンシが揃って悪化する
_embedding_semaphore = asyncio.Semaphore(settings.EMBEDDING_MAX_CONCURRENCY)


def _get_query_vector_sync(query: str) -> str:
    """検索クエリのベクトル化(実処理)"""
    if ml_models.embedding_model is None:
        raise RuntimeError("Embedding Model is not initialized.")
    # Ruri v3の仕様に合わせてプレフィックスを付与
    semantic_query = f"検索クエリ: {query}"
    # ベクトルにエンコード
    vector = ml_models.embedding_model.encode(semantic_query).tolist()
    # pgvectorで解釈できるようリストを文字列表現に変換 ("[0.1, 0.2, ...]")
    return str(vector)


async def get_query_vector(query: str) -> str:
    """検索クエリをベクトル化し、PostgreSQL用の文字列表現にして返す

    Args:
        query (str): 検索クエリ

    Returns:
        str: ベクトルの文字列表現

    """
    # 同時実行数を絞った上でワーカースレッドへ逃がす
    async with _embedding_semaphore:
        return await asyncio.to_thread(_get_query_vector_sync, query)
