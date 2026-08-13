"""リード文のベクトルに対してHNSWインデックスを作成するスクリプト

A2_create_vector.py によるベクトル変換が完了した後に実行すること。

## 実行方法
プロジェクトルートから以下のコマンドを実行:
`uv run python -m src.pipeline.A_release.A3_init_vector_index`
"""

import time

import psycopg
from psycopg import sql

from src.core.config import settings


def create_vector_index() -> None:
    """環境変数の次元数に基づき、HNSWインデックスを作成する"""
    print("\n=== HNSWインデックスの作成処理を開始します ===")

    print(f"\nモデル: {settings.EMBEDDING_MODEL}")
    print(f"次元数: {settings.EMBEDDING_DIMENSION}")

    print("\nHNSWインデックスを作成中...")
    start_time = time.time()
    with psycopg.connect(settings.DATABASE_URL) as conn:
        # テンプレートの定義
        query_template = sql.SQL("""
            CREATE INDEX IF NOT EXISTS
                idx_release_search_corpus_lead_paragraph_vector_hnsw
            ON
                release_search_corpus
            USING
                -- カラム自体に次元数の指定がなくても、インデックス作成時にキャストして次元を指定できる
                hnsw ((lead_paragraph_vector::vector({dimension})) vector_cosine_ops);
        """)

        # フォーマット適用
        query = query_template.format(dimension=sql.Literal(settings.EMBEDDING_DIMENSION))

        conn.execute(query)
        conn.commit()
        total_time = time.time() - start_time
        print(f"\n=== 次元数 {settings.EMBEDDING_DIMENSION} のHNSWインデックスを作成しました ===")
        print(f"総処理時間: {total_time:.2f} 秒\n")


if __name__ == "__main__":
    create_vector_index()
