-- 01_release_search_corpus.sql / 類似プレスリリース検索用コーパステーブル

-- ==========================================
-- 【このテーブルの位置づけ】
-- release本体は既存のデータ基盤であり、直接ベクトル列を追加する変更は避ける方針とした。
-- そのため、検索対象として選定した一部の行(company_id, release_id)だけを
-- このテーブルへ複製し、ベクトル列はここにのみ持たせる。
--
-- release / release_statistic の全カラムをそのまま複製するのではなく、検索コーパスとして
-- 使う最小限のカラムのみを持つ(company_id, release_idで元のreleaseへ再度JOIN可能なため、
-- body等の未使用カラムが必要になった場合はそちらを参照すればよい)。
--
-- 【対象行の選定基準(2026年8月時点で確定した方針)】
-- release.created_at が現在時刻から5年以上前、かつ lead_paragraph が空文字でないものの中から、
-- release_statistic.page_view の降順で上位10,000件。実際の抽出・INSERTは
-- src/pipeline/A_release/A1_populate_corpus.py が行う(本DDLはテーブル定義のみ)。
-- ==========================================

CREATE TABLE
    IF NOT EXISTS release_search_corpus (
        company_id INTEGER NOT NULL, -- releaseへの複合外部キー(1/2)
        release_id INTEGER NOT NULL, -- releaseへの複合外部キー(2/2) / company_id内で採番されるためrelease_id単独では一意にならない
        title VARCHAR NOT NULL, -- 表示・確認用
        lead_paragraph TEXT NOT NULL, -- ベクトル化対象の原文(空文字は対象外のためNOT NULLかつ非空が保証される)
        page_view INTEGER NOT NULL, -- 選定基準になった値。将来のランキング・確認用に保持
        created_at TIMESTAMP NOT NULL, -- 選定基準(経過年数)・表示用
        lead_paragraph_vector vector, -- lead_paragraphのベクトル(意味検索用) / 未処理時はNULL
        PRIMARY KEY (company_id, release_id)
    );

-- 経過年数によるフィルタ・確認クエリ用
CREATE INDEX IF NOT EXISTS idx_release_search_corpus_created_at ON release_search_corpus (created_at);

-- HNSW(意味検索用インデックス)は、モデルに応じて次元数の動的バインドが必要なため、
-- パイプラインのPythonスクリプト側(A3_init_vector_index.py)で作成する。
