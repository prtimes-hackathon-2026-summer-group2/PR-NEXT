"""pgvectorのHNSW索引に関する共有サービスロジック"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from psycopg import sql

if TYPE_CHECKING:
    from psycopg import AsyncCursor

# HNSWの探索候補数を設定するSQL
#
# SET LOCAL はパラメータのバインドに対応していないため、同等の効果を持つ set_config() を使う。
# 第3引数の true が SET LOCAL 相当(現在のトランザクション内でのみ有効)を意味する。
_SET_EF_SEARCH_SQL = sql.SQL("SELECT set_config('hnsw.ef_search', %(ef_search)s::text, true);")


async def apply_ef_search(cursor: AsyncCursor[Any], ef_search: int) -> None:
    """HNSWの探索候補数(hnsw.ef_search)を、現在のトランザクション内に限り設定する

    pgvectorのHNSW索引は、探索時に保持する候補リストの大きさを `hnsw.ef_search` で決める。
    この値がそのまま取得できる件数の上限として効き、SQLのLIMITをいくら大きくしても
    ef_searchを超える件数は返らない(既定値は40)。そのため意味検索を実行する側は、
    取得したい件数に合わせてこの関数を呼ぶ必要がある。

    Args:
        cursor (AsyncCursor[Any]): 意味検索を実行するカーソル(同一トランザクション内である必要がある)
        ef_search (int): 設定する探索候補数。取得したい件数と同じ値を渡す

    """
    await cursor.execute(_SET_EF_SEARCH_SQL, {"ef_search": ef_search})
