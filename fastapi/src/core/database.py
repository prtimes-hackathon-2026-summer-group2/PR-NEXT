"""データベースの接続情報を提供するモジュール"""

from collections.abc import AsyncGenerator

from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

# 環境変数
from src.core.config import settings


class DatabaseManager:
    """データベースのコネクションプールを管理するクラス"""

    def __init__(self) -> None:
        """インスタンス変数の初期化"""
        self.pool: AsyncConnectionPool[AsyncConnection] | None = None

    async def initialize(self) -> None:
        """プールの初期化

        Note:
            `AsyncConnectionPool`はコンストラクタでの`open=True`が非推奨のため、
            生成後に`open()`を明示的に呼ぶ。`wait=True`で`min_size`分の接続確立を待ち、
            起動時点でDBへ到達できない場合はここで失敗させる。

        """
        self.pool = AsyncConnectionPool(
            conninfo=settings.DATABASE_URL,
            min_size=5,  # 常に維持する最小コネクション数
            max_size=20,  # トラフィック増大時に許可する最大コネクション数
            open=False,  # 生成時には開かず、下の open() で明示的に開く
        )
        await self.pool.open(wait=True)

    async def close(self) -> None:
        """プールのクローズ"""
        if self.pool is not None:
            await self.pool.close()
            self.pool = None

    def get_pool(self) -> AsyncConnectionPool[AsyncConnection]:
        """初期化済みのプールを返す。未初期化の場合は例外を送出する。"""
        if self.pool is None:
            raise RuntimeError("Database pool is not initialized.")
        return self.pool


# グローバルなインスタンスを作成
database_manager = DatabaseManager()


async def get_db_connection() -> AsyncGenerator[AsyncConnection]:
    """データベース接続を提供する非同期ジェネレータ関数

    プールからコネクションを借用し、処理終了後に自動返却する。
    row_factoryはこの層では指定しない。利用側がcursor()呼び出し時に
    用途に応じたrow_factory(dict_row/class_row/scalar_rowなど)を指定すること。

    Note:
        FastAPIの Depends() による依存性注入や、async with句での利用を想定。
        1リクエスト内で複数クエリを「並列に」実行したい場合はこの依存関係では足りない。
        psycopgの`AsyncConnection`は接続単位のロックを持ち、同一接続上のクエリは
        `asyncio.gather`で並べても直列化されるため、その場合は`get_db_pool`を使い
        クエリごとに別のコネクションを借用すること。

    Yields:
        AsyncGenerator[AsyncConnection]: デフォルト(tuple_row)の接続情報

    """
    if database_manager.pool is None:
        raise RuntimeError("Database pool is not initialized.")

    # pool.connection() を async with 句で呼ぶことで、抜けた時に自動でプールに返却される
    async with database_manager.pool.connection() as conn:
        # 接続情報を返して待機
        yield conn


def get_db_pool() -> AsyncConnectionPool[AsyncConnection]:
    """コネクションプールそのものを提供する関数

    1リクエスト内で複数のクエリを並列実行する必要があるエンドポイント
    (ハイブリッド検索など)で、クエリごとに独立したコネクションを借用するために使う。

    Note:
        FastAPIの Depends() による依存性注入を想定。
        利用側は必ず `async with pool.connection() as conn:` の形で借用し、
        「1本目を保持したまま2本目を待つ」入れ子構造を作らないこと
        (プール枯渇時に自己デッドロックするため、並列に借用する)。

    Returns:
        AsyncConnectionPool[AsyncConnection]: 初期化済みのコネクションプール

    """
    return database_manager.get_pool()
