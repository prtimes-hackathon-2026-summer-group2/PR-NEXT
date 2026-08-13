-- 00_init_extensions.sql / 拡張機能の有効化
-- 00 --> 実行順を制御するための命名規則(ファイルの並び順)

-- pgvector: ベクトルデータを保存・検索する機能を利用可能にする
CREATE EXTENSION IF NOT EXISTS vector;
