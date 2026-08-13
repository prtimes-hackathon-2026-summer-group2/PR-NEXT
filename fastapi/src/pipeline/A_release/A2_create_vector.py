"""ベクトル生成・更新スクリプト

release_search_corpus のリード文(lead_paragraph)をベクトル化し、
lead_paragraph_vector に保存する。

## 実行方法
プロジェクトルートから以下のコマンドを実行:
`uv run python -m src.pipeline.A_release.A2_create_vector`
"""

import time

import psycopg
import torch
from psycopg import sql
from psycopg.rows import class_row, scalar_row
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

# 環境変数
from src.core.config import settings
from src.core.device import get_device
from src.pipeline.A_release.modules.models import ReleaseLeadParagraphRecord

# モデルが一度に処理するテキストの件数(負荷調整用)
ENCODE_BATCH_SIZE = 32

# サーバーサイドカーソルが1回の通信でDBから取得する件数
STREAM_ITER_SIZE = 512


def _process_and_update(
    batch: list[ReleaseLeadParagraphRecord],
    model: SentenceTransformer,
    update_cur: psycopg.Cursor,
    update_conn: psycopg.Connection,
) -> None:
    """バッチデータをベクトル化してDBを更新する内部関数

    Args:
        batch: 処理対象の行データ(company_id, release_id, lead_paragraphを含む)
        model: ベクトル化に使用するSentenceTransformerモデル
        update_cur: UPDATE用カーソル
        update_conn: UPDATE用コネクション(commit用)

    """
    # Ruri v3の仕様に合わせて「検索文書: 」プレフィックスを付与
    # プレフィックスの有無で精度に差が出るため必須
    texts = [f"検索文書: {row.lead_paragraph}" for row in batch]

    # ベクトル化の実行(numpy配列として取得)
    embeddings = model.encode(texts, batch_size=ENCODE_BATCH_SIZE)

    # pgvectorが解釈できるようリストを文字列 "[0.1, 0.2, ...]" に変換(名前付きプレースホルダー用に辞書化)
    update_values = [
        {"vector": str(emb.tolist()), "company_id": row.company_id, "release_id": row.release_id}
        for row, emb in zip(batch, embeddings, strict=True)
    ]

    # 一括でUPDATE実行
    # ::vector と明示的にキャストすることで確実に型変換する
    update_cur.executemany(
        sql.SQL("""
        UPDATE
            release_search_corpus
        SET
            lead_paragraph_vector = %(vector)s::vector
        WHERE
            company_id = %(company_id)s AND release_id = %(release_id)s;
    """),
        update_values,
    )

    # バッチ単位でコミット(障害時のロールバック範囲をバッチ単位に限定)
    update_conn.commit()


def update_vectors() -> None:
    """ベクトル変換が未処理のレコードをストリーミング取得し、ベクトル化してDBに保存するメイン処理"""
    print("\n=== リード文のベクトル変換処理を開始します ===")
    device = get_device()
    print(f"\n使用デバイス: {device}")
    print(f"モデルをロード中... (モデル: {settings.EMBEDDING_MODEL}, 次元数: {settings.EMBEDDING_DIMENSION})")

    # モデルの初期化
    model = SentenceTransformer(settings.EMBEDDING_MODEL, device=str(device), token=settings.HF_TOKEN)
    # コンテキストウィンドウの設定
    # --> 異常に長いテキストによるメモリ超過を防ぐ
    model.max_seq_length = settings.EMBEDDING_MAX_SEQUENCE_LENGTH

    # --- 未処理の総件数を取得 (進捗バー表示用) ---
    with (
        psycopg.connect(settings.DATABASE_URL) as conn,
        conn.cursor(row_factory=scalar_row) as cursor,
    ):
        cursor.execute(
            sql.SQL("""
                SELECT COUNT(*)
                FROM
                    release_search_corpus
                WHERE
                    lead_paragraph_vector IS NULL;
            """),
        )
        total_unprocessed = cursor.fetchone() or 0

    if total_unprocessed == 0:
        print("\nベクトル化対象のデータがありません。\n")
        return

    print(f"\nベクトル化対象: {total_unprocessed}件")
    print("ベクトルに変換中...")

    # 対象データを取得するSQL
    # サーバーサイドカーソルで使用するためORDER BYは不要
    # (LIMITループと異なり、クエリは1回のみ実行される)
    select_sql = sql.SQL("""
        SELECT
            company_id, release_id, lead_paragraph
        FROM
            release_search_corpus
        WHERE
            lead_paragraph_vector IS NULL;
    """)

    # --- ストリーミング取得中にUPDATEを行うため、コネクションを分離する ---
    # (サーバーサイドカーソルを開いたまま同一コネクションでUPDATEはできない)
    with (
        psycopg.connect(settings.DATABASE_URL) as stream_conn,
        stream_conn.cursor(name="streaming_cursor", row_factory=class_row(ReleaseLeadParagraphRecord)) as stream_cursor,
        psycopg.connect(settings.DATABASE_URL) as update_conn,
        update_conn.cursor() as update_cursor,
    ):
        stream_cursor.itersize = STREAM_ITER_SIZE
        stream_cursor.execute(select_sql)

        batch: list[ReleaseLeadParagraphRecord] = []
        start_time = time.time()

        with tqdm(total=total_unprocessed, desc="ベクトル化進捗") as progress_bar:
            for row in stream_cursor:
                batch.append(row)

                # 指定したバッチサイズに達したらベクトル化とUPDATEを実行
                if len(batch) >= ENCODE_BATCH_SIZE:
                    _process_and_update(batch, model, update_cursor, update_conn)
                    progress_bar.update(len(batch))
                    batch.clear()

            # ループ終了後、端数のデータを処理
            if batch:
                _process_and_update(batch, model, update_cursor, update_conn)
                progress_bar.update(len(batch))

    print("\n=== テーブルの最適化 (VACUUM ANALYZE) を実行しています ===")
    # VACUUMコマンドは通常のトランザクション内では実行できないため、
    # autocommit=True を指定して専用のコネクションを開く。
    with psycopg.connect(settings.DATABASE_URL, autocommit=True) as vac_conn:
        vac_conn.execute("VACUUM ANALYZE release_search_corpus;")
    print("テーブルの最適化が完了しました。")

    # 処理結果の出力
    total_time = time.time() - start_time
    print("\n=== 処理が完了しました ===")
    print(f"総処理時間: {total_time:.2f}秒")
    if total_time > 0:
        print(f"処理速度: {total_unprocessed / total_time:.2f} 件/秒\n")


if __name__ == "__main__":
    try:
        # メイン処理
        update_vectors()
    # エラーハンドリング
    except KeyboardInterrupt:
        print("\n\n[中断] Ctrl+Cが入力されました。処理を中断しました。")
        print("※未コミットのデータはロールバックされ、次回実行時に再開されます。")
    except torch.cuda.OutOfMemoryError:
        # 新しいPyTorchでのGPUメモリ不足エラー
        print("\n\n[エラー] GPUのメモリ不足(CUDA OutOfMemory)が発生しました。")
        print("ヒント: ENCODE_BATCH_SIZE を下げるか、異常に長いテキストがないか確認してください。")
    except RuntimeError as error:
        # 古いPyTorch、またはその他のCUDA実行時エラー
        if "out of memory" in str(error).lower():
            print("\n\n[エラー] GPUのメモリ不足 (OOM)が発生しました。")
        else:
            # OOM以外の予期せぬエラーは通常通り表示
            raise
