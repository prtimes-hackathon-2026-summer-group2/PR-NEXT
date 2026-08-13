"""database/tables/ 配下のテーブル定義SQLファイルを、ファイル名の昇順で順次実行するスクリプト。

各SQLファイルは CREATE ... IF NOT EXISTS の形で書かれているため冪等であり、
差分を気にせず毎回全ファイルを実行してよい(実行済みのCREATE文は単に無視される)。

## 実行方法
プロジェクトルートから以下のコマンドを実行:
`uv run python -m src.database.create_tables`
"""

from pathlib import Path
from typing import LiteralString, cast

import psycopg

from src.core.config import settings

# テーブル定義SQLファイルが配置されているディレクトリ
TABLES_DIR = Path(__file__).resolve().parent / "tables"


def _execute_sql_file(connection: psycopg.Connection, sql_path: Path) -> None:
    """1つのSQLファイルの内容を丸ごと実行する。

    execute()はPEP 675に基づきLiteralStringのみを受け付けるが、ファイルから
    読み込んだ内容は実行時に決まるstrであり、この型を満たせない。ここで読み込むのは
    リポジトリ内で管理する静的なDDLファイルのみであり、外部入力を組み込むものではないため、
    castによる型安全性の例外化は妥当と判断する。

    Args:
        connection: DB接続。
        sql_path: 実行対象のSQLファイルパス。

    """
    sql_literal_text = cast("LiteralString", sql_path.read_text(encoding="utf-8"))
    with connection.cursor() as cursor:
        cursor.execute(query=sql_literal_text)


def create_tables() -> None:
    """TABLES_DIR 配下の全SQLファイルを、ファイル名昇順で順次実行するメイン処理。

    全ファイルを1つのトランザクションにまとめ、最後に1度だけコミットする。
    冪等なDDLのみを扱うため、途中で失敗した場合は原因のファイルを修正し、
    最初から再実行すればよい(差分管理は行わない)。
    """
    print("\n=== テーブル定義SQLの実行を開始します ===")
    print(f"対象ディレクトリ: {TABLES_DIR}\n")

    sql_files = sorted(TABLES_DIR.glob("*.sql"))

    if not sql_files:
        print(f"エラー: .sqlファイルが見つかりません -> {TABLES_DIR}")
        return

    print(f"対象ファイル: {len(sql_files)}件")
    for sql_path in sql_files:
        print(f"  - {sql_path.name}")
    print()

    try:
        with psycopg.connect(settings.DATABASE_URL) as connection:
            for sql_path in sql_files:
                print(f"実行中: {sql_path.name}")
                _execute_sql_file(connection, sql_path)
            connection.commit()
    except Exception as error:
        print(f"\n[Error] SQL実行中にエラーが発生しました。変更はロールバックされます:\n{error}")
        raise

    print("\n=== 全てのテーブル定義SQLの実行が完了しました ===")


if __name__ == "__main__":
    create_tables()
