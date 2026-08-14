# PR NEXT

PR TIMES のプレスリリースデータを活用し、作成中のプレスリリースに対して意味的に類似する過去のプレスリリースを検索・比較できるプロトタイプです。プレスリリース単位の統計指標を分析する独立したPythonライブラリも同梱しています。

## 構成

本リポジトリは3つの独立したコンポーネントで構成されています。

| ディレクトリ | 役割 | 技術スタック |
| --- | --- | --- |
| [`app/`](app) | フロントエンド(Next.jsプロトタイプ) | Next.js 16 (App Router) / React 19 / TypeScript |
| [`fastapi/`](fastapi) | バックエンドAPI(既存) | FastAPI / psycopg / sentence-transformers |
| [`src/prtimes_analysis/`](src/prtimes_analysis) | プレスリリース統計・時系列分析ライブラリ | Python / pandas / numpy |

---

チーム: インダストリアル
