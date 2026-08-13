"""類似プレスリリース検索用コーパースの初期投入スクリプト

release / release_statistic から、以下の基準を満たす行を release_search_corpus へ複製する。
(ベクトル列 lead_paragraph_vector はここでは投入せず、A2_create_vector.py が別途処理する)

## 対象行の選定基準
- created_at が現在時刻から MIN_AGE_YEARS 年以上前
- lead_paragraph が空文字でない
- 上記を満たす行のうち、page_view の降順で上位 TARGET_ROW_COUNT 件

## 実行方法
プロジェクトルートから以下のコマンドを実行:
`uv run python -m src.pipeline.A_release.A1_populate_corpus
"""

import psycopg
from psycopg import sql

from src.core.config import settings

# 選定基準: 経過年数
MIN_AGE_YEARS = 5

# 選定基準: 対象件数の上限
TARGET_ROW_COUNT = 10000


def populate_corpus() -> None:
    """選定基準を満たす行をrelease_search_corpusへ投入するメイン処理"""
    print("\n=== 検索コーパスへの初期投入処理を開始します ===")
    print(f"選定基準: created_atが現在時刻から{MIN_AGE_YEARS}年以上前 / lead_paragraphが非空 / page_view降順で上位{TARGET_ROW_COUNT}件\n")

    # テンプレートの定義
    # ON CONFLICT DO NOTHING: 複合主キー(company_id, release_id)が既に存在する場合は何もしない
    # (再実行しても重複投入されず、冪等に扱える)
    insert_sql = sql.SQL("""
        INSERT INTO release_search_corpus (
            company_id, release_id, title, lead_paragraph, page_view, created_at
        )
        SELECT
            r.company_id, r.release_id, r.title, r.lead_paragraph, s.page_view, r.created_at
        FROM
            release r
        JOIN
            release_statistic s ON s.release_id = r.release_id AND s.company_id = r.company_id
        WHERE
            r.created_at < CURRENT_DATE - ({min_age_years} * INTERVAL '1 year')
            AND r.lead_paragraph <> ''
        ORDER BY
            s.page_view DESC
        LIMIT {limit}
        ON CONFLICT (company_id, release_id) DO NOTHING;
    """).format(
        min_age_years=sql.Literal(MIN_AGE_YEARS),
        limit=sql.Literal(TARGET_ROW_COUNT),
    )

    with psycopg.connect(settings.DATABASE_URL) as conn, conn.cursor() as cursor:
        cursor.execute(insert_sql)
        inserted = cursor.rowcount
        conn.commit()

        cursor.execute("SELECT COUNT(*) FROM release_search_corpus;")
        total = cursor.fetchone()
        total_count = total[0] if total else 0

    print(f"新規投入: {inserted}件")
    print(f"release_search_corpus 総件数: {total_count}件")
    print("\n=== 検索コーパスへの初期投入処理が完了しました ===\n")


if __name__ == "__main__":
    populate_corpus()
