# PR NEXT — Codex実装用 Next.js プロトタイプ要件定義書

## 1. 文書の目的

本書は、FastAPI が提供する既存APIを利用して、PR NEXT の Next.js プロトタイプを Codex で実装するための要件を定義する。

実装では、本書に記載されていないバックエンド機能を推測して追加しないこと。

要求の優先順位は以下とする。

* **MUST**: プロトタイプ完成に必須
* **SHOULD**: MUST完成後、時間があれば実装
* **OUT OF SCOPE**: 今回は実装しない

---

# 2. プロダクト目的

ユーザーが作成中のプレスリリースのリード文を入力すると、既存FastAPIを利用して意味的に類似する過去のプレスリリース上位5件を取得し、比較しやすいUIで表示する。

基本フローは以下とする。

```text
ユーザーが下書きを入力
        ↓
「類似プレスリリースを検索」
        ↓
Next.js Server
        ↓
FastAPIへ1回だけGET
        ↓
類似度上位5件を取得
        ↓
Top 5 + 指標比較Dashboardを表示
```

---

# 3. 今回の実装スコープ

## MUST

1. プレスリリースのリード文入力
2. FastAPIへの類似検索
3. 類似プレスリリース上位5件の表示
4. 類似度の表示
5. PR基本情報の表示
6. PV・UU・Like数の比較
7. 比較指標の切り替え
8. Loading状態
9. Error状態
10. AWS EC2上でのHTTP公開

## OUT OF SCOPE

以下は実装しない。

* AI解説生成
* OpenAI API呼び出し
* 時系列データ表示
* 将来値予測
* SNS反応データ
* メディア掲載数データ
* 検索量データ
* 認証
* ユーザー登録
* Session
* JWT
* OAuth
* 保存機能
* 検索履歴
* お気に入り
* DB直接アクセス
* Nginx
* HTTPS
* ALB
* Multi-AZ
* Auto Scaling
* Rate Limit
* API利用量管理

現在のFastAPIレスポンスに存在しないデータを、モック・乱数・推測により生成してはならない。

---

# 4. システム構成

```text
                    Internet
                       │
                  HTTP :3000
                       │
                       ▼
┌─────────────────────────────────────┐
│ AWS EC2 / Ubuntu                    │
│ Public IP                           │
│                                     │
│ Next.js App Router                  │
│                                     │
│ ・UI                                │
│ ・Server Components                 │
│ ・Client Components                 │
│ ・Server Action                     │
└────────────────┬────────────────────┘
                 │
                 │ VPC内部HTTP
                 │ 1検索につき1Request
                 ▼
┌─────────────────────────────────────┐
│ Existing Python EC2                 │
│                                     │
│ FastAPI                             │
│                                     │
│ GET /press-release/search           │
└─────────────────────────────────────┘
```

---

# 5. 責務分割

## 5.1 Browser

Browserの責務は以下のみとする。

* 下書き入力
* 検索ボタン操作
* 検索結果閲覧
* 比較指標選択
* UI状態表示

BrowserからFastAPIを直接呼び出してはならない。

---

## 5.2 Next.js

Next.jsの責務は以下とする。

### Input

* ユーザーからリード文を受け取る
* 入力値を検証する

### Integration

* FastAPIへ検索Requestを1回送信する
* ResponseをTypeScript型として受け取る
* HTTP ErrorをUI用状態へ変換する

### Presentation

* Top 5を表示する
* PR詳細情報を表示する
* PV / UU / Like数を比較する
* Loading / Error / Success状態を表示する

Next.jsは類似度計算や分析を行わない。

---

## 5.3 FastAPI

FastAPIを以下の情報のSingle Source of Truthとする。

* 類似検索結果
* 順位
* similarity_score
* プレスリリース情報
* page_view
* unique_user
* like_count
* business_categories
* keywords

Next.jsでこれらの値を推測または再計算しない。

---

# 6. FastAPI契約

Next.jsが対応するFastAPIは以下の1本だけとする。

```http
GET /press-release/search
```

## 6.1 Request Parameters

### `query`

| 項目         | 値               |
| ---------- | --------------- |
| Type       | string          |
| Required   | true            |
| Max Length | 2000            |
| 内容         | 作成中プレスリリースのリード文 |

### `top_n`

| 項目           | 値       |
| ------------ | ------- |
| Type         | integer |
| API Default  | 10      |
| API Minimum  | 1       |
| API Maximum  | 100     |
| Next.jsから送る値 | **5固定** |

Next.jsからの実際のRequestは以下とする。

```http
GET /press-release/search?query=<USER_INPUT>&top_n=5
```

`query` はURLエンコードすること。

---

# 7. Response型

FastAPIレスポンスに対応するTypeScript型を定義すること。

```ts
export type PressReleaseSearchResponse = {
  query: string;
  top_n: number;
  hits: number;
  data: SimilarPressRelease[];
};

export type SimilarPressRelease = {
  company_id: number;
  release_id: number;
  similarity_score: number;

  title: string;
  subtitle: string;
  lead_paragraph: string;

  created_at: string;

  company_name: string;
  industry: string;

  page_view: number;
  unique_user: number;
  like_count: number;

  business_categories: string[];
  keywords: string[];
};
```

型名は実装上必要であれば変更してよいが、APIフィールド名を変更してはならない。

---

# 8. Error Response

FastAPIのValidation ErrorとしてHTTP 422を扱う。

レスポンス構造は以下を想定する。

```ts
export type ValidationErrorResponse = {
  detail: {
    loc: Array<string | number>;
    msg: string;
    type: string;
    input?: unknown;
    ctx?: Record<string, unknown>;
  }[];
};
```

422の場合、FastAPIの内部構造をそのままユーザーへ表示せず、

> 入力内容を確認してください。

に相当する簡潔なメッセージを表示する。

その他のHTTPエラーでは、

> 類似プレスリリースの検索に失敗しました。もう一度お試しください。

に相当するメッセージを表示する。

Stack Trace、Private IP、内部API URLを画面へ表示してはならない。

---

# 9. 通信要件

## NET-01

1回の検索操作につきFastAPI Requestは1回だけとする。

## NET-02

以下の操作ではFastAPIへ追加Requestを送信してはならない。

* 指標切り替え
* Top5内のPR選択
* 詳細情報表示
* グラフ切り替え

すべて最初のResponseに含まれるデータを利用する。

## NET-03

FastAPI URLはサーバー側環境変数から取得する。

```env
FASTAPI_URL=http://<FASTAPI_PRIVATE_IP>:8000
```

## NET-04

以下は使用しない。

```env
NEXT_PUBLIC_FASTAPI_URL=...
```

FastAPI URLをブラウザ向けJavaScript bundleへ含めない。

---

# 10. Next.js実装方式

以下を採用する。

* Next.js
* App Router
* TypeScript
* React Server Components
* Server Action
* 必要な箇所のみClient Component
* npm

ページ全体をClient Componentにしてはならない。

---

# 11. 画面構成

プロトタイプではURLを1画面に限定する。

```text
/
```

画面内部に以下の2状態を持つ。

```text
Initial
 ↓
Searching
 ↓
Result

または

Initial
 ↓
Searching
 ↓
Error
```

検索結果を別URLへ保存する必要はない。

ブラウザReload後に検索結果が失われてもよい。

---

# 12. 初期画面要件

以下を表示する。

```text
PR NEXT

類似プレスリリースを探す

作成中のプレスリリースの
リード文を入力してください。

┌─────────────────────────────────────┐
│                                     │
│ リード文を入力                      │
│                                     │
└─────────────────────────────────────┘

                            0 / 2000

          [ 類似プレスリリースを検索 ]
```

## UI-01

textareaを使用する。

## UI-02

最大入力文字数を2000文字とする。

## UI-03

現在の文字数を表示する。

## UI-04

空文字または空白のみの場合は検索できないこと。

## UI-05

検索ボタンの文言から実行内容を理解できること。

推奨文言：

> 類似プレスリリースを検索

---

# 13. Loading状態

検索開始からResponse受信まで、検索ボタンをLoading状態にする。

例：

```text
[ 類似プレスリリースを検索しています… ]
```

同じ検索操作を重複Submitできないよう、処理中は検索ボタンをdisableにする。

これはRate Limit対策ではなく、ユーザー操作状態を明確にするためのUI要件とする。

---

# 14. 検索結果画面

検索成功後、同一ページ上で以下を表示する。

```text
┌───────────────────┬─────────────────────────────────────┐
│ 類似PR Top 5      │ 指標比較                            │
│                   │                                     │
│ #1 PR             │ [ページ閲覧数] [UU] [Like数]       │
│ similarity        │                                     │
│                   │ ┌─────────────────────────────────┐ │
│ #2 PR             │ │                                 │ │
│ similarity        │ │        Top 5 比較              │ │
│                   │ │                                 │ │
│ #3 PR             │ └─────────────────────────────────┘ │
│                   │                                     │
│ #4 PR             │ 選択PRの詳細                       │
│                   │                                     │
│ #5 PR             │ タイトル / 会社 / 業種 / etc.     │
└───────────────────┴─────────────────────────────────────┘
```

---

# 15. 類似PR Top 5

FastAPIの`data`を返却順に表示する。

Next.js側で類似度による再ソートを行わない。

各項目には最低限以下を表示する。

* 順位
* title
* company_name
* similarity_score

必要に応じて以下を補助表示する。

* created_at
* industry

---

# 16. similarity_score表示

`similarity_score` の値域はNext.js側で推測しない。

API仕様で0〜1であることが別途保証されるまでは、百分率への変換を行わない。

プロトタイプでは小数第3位程度までの表示を推奨する。

例：

```text
類似度 0.913
```

Codexは独自判断で、

```text
0.913 → 91.3%
```

へ変換してはならない。

---

# 17. 指標比較Dashboard

FastAPIから取得できる以下の3指標のみ使用する。

| API field     | UI表示      |
| ------------- | --------- |
| `page_view`   | ページ閲覧数    |
| `unique_user` | ユニークユーザー数 |
| `like_count`  | Like数     |

以下の切り替えUIを設ける。

```text
[ページ閲覧数] [ユニークユーザー数] [Like数]
```

初期選択は、

```text
ページ閲覧数
```

とする。

---

# 18. 指標比較グラフ

選択した1指標について、Top 5を比較する。

時系列グラフは作成しない。

例えばページ閲覧数の場合、

```text
ページ閲覧数

#1 █████████████████ 12,450
#2 ████████████       9,820
#3 ██████████         8,150
#4 █████████          7,920
#5 ████████           6,810
```

のように、5件の大小関係を一目で理解できる形式とする。

棒グラフまたはHorizontal Bar表示を推奨する。

グラフ描画のためだけに複雑な状態管理ライブラリを導入しない。

---

# 19. 選択PR詳細

ユーザーがTop5から1件を選択した場合、以下を表示する。

### 基本情報

* title
* subtitle
* company_name
* industry
* created_at

### リード文

* lead_paragraph

### 指標

* page_view
* unique_user
* like_count

### 分類

* business_categories
* keywords

カテゴリとキーワードはTag形式で表示する。

値が空配列の場合はTag領域を表示しなくてもよい。

---

# 20. hitsの扱い

`hits`は検索全体のヒット数として扱う。

Top5とは分けて表示する。

例：

```text
10,000件の検索対象から類似する5件を表示
```

ただし`hits`の厳密な意味についてFastAPI仕様で別定義がある場合は、その定義を優先する。

---

# 21. Component構成

最低限以下の構成とする。

```text
src/
├─ app/
│  ├─ layout.tsx
│  ├─ page.tsx
│  ├─ actions.ts
│  └─ globals.css
│
├─ components/
│  ├─ DraftForm.tsx
│  ├─ SearchResults.tsx
│  ├─ SimilarPressReleaseList.tsx
│  ├─ SimilarPressReleaseCard.tsx
│  ├─ MetricSelector.tsx
│  ├─ MetricComparison.tsx
│  └─ PressReleaseDetail.tsx
│
└─ lib/
   └─ fastapi/
      ├─ client.ts
      └─ types.ts
```

プロトタイプのため、これ以上のレイヤー分割は原則行わない。

---

# 22. ファイル責務

## `app/page.tsx`

責務：

* ページ全体のServer Component
* アプリケーションShellの構成
* 検索UIの配置

業務ロジックを書かない。

---

## `app/actions.ts`

責務：

* Server Action
* 入力validation
* `searchPressReleases()`の呼び出し
* Clientへ返せる結果への変換

FastAPI URLを直接複数箇所に記述しない。

---

## `lib/fastapi/client.ts`

責務：

* FastAPIとの唯一の通信処理
* URLSearchParams生成
* HTTP status判定
* JSON parse

このファイル以外からFastAPIへ直接`fetch()`しない。

---

## `lib/fastapi/types.ts`

責務：

* FastAPI Request / Response型
* Validation Error型

---

## `DraftForm.tsx`

責務：

* textarea
* 文字数表示
* submit
* Loading
* 入力エラー

---

## `SearchResults.tsx`

責務：

* 検索成功後のDashboard全体レイアウト

---

## `SimilarPressReleaseList.tsx`

責務：

* Top5一覧
* PR選択

---

## `MetricSelector.tsx`

責務：

* page_view
* unique_user
* like_count

の表示切り替え。

API通信は行わない。

---

## `MetricComparison.tsx`

責務：

* 選択指標のTop5比較表示

計算は表示に必要な正規化のみ許可する。

元データそのものを変更しない。

---

## `PressReleaseDetail.tsx`

責務：

* 選択したPRの詳細情報表示

---

# 23. 状態管理

Redux、Zustand等のグローバルState Managementは導入しない。

必要な状態はReactのローカルstateで管理する。

想定する状態：

```ts
type UiState = {
  selectedReleaseId: number | null;
  selectedMetric:
    | "page_view"
    | "unique_user"
    | "like_count";
};
```

検索Response自体はServer ActionのResultとして保持する。

---

# 24. Validation

Next.js側で以下を検証する。

## VAL-01

`query.trim().length > 0`

## VAL-02

`query.length <= 2000`

## VAL-03

`top_n`はUIから入力させず、コード上で5固定とする。

FastAPI側にもvalidationが存在することを前提とし、Next.js validationのみを信頼しない。

---

# 25. 表示フォーマット

## 数値

3桁区切りにする。

```text
12450
↓
12,450
```

## 日付

`created_at`はユーザー向けに読みやすい日付へ変換する。

例：

```text
2026-08-13
```

時刻がプロダクト上重要でなければ表示しなくてよい。

---

# 26. UIデザイン原則

添付された既存UIを参考にするが、そのままHTMLを移植しない。

以下を優先する。

1. 情報階層が一目で理解できる
2. Top5の順位が明確
3. 類似度と指標値を混同しない
4. 指標名を略語だけで表示しない
5. 操作可能な要素を視覚的に判別できる
6. データ量を増やしすぎない
7. デモ用PC画面で崩れない

PVではなく、

> ページ閲覧数

UUではなく、

> ユニークユーザー数

を主要ラベルとして使用する。

---

# 27. レスポンシブ要件

デスクトップを最優先とする。

MUST：

```text
1280px以上の画面で正常表示
```

SHOULD：

```text
768px以上で致命的なレイアウト崩れがない
```

スマートフォン専用UIの作り込みはOUT OF SCOPEとする。

---

# 28. 非機能要件

## NFR-01 — Simplicity

デモ完成に必要のない技術を追加しない。

## NFR-02 — Traceability

UIに表示する値はFastAPI Responseのどのfieldから来たかコード上で追跡可能にする。

## NFR-03 — Data Integrity

Next.jsでAPI値を推測・補完しない。

## NFR-04 — Failure Isolation

検索APIが失敗してもNext.jsアプリ全体をクラッシュさせない。

## NFR-05 — Server Boundary

FastAPI URLをClient Componentへ渡さない。

## NFR-06 — Maintainability

FastAPI通信を1ファイルへ集約する。

---

# 29. AWSデプロイ要件

Next.jsはAWS EC2 Ubuntuインスタンスへ配置する。

公開方式：

```text
HTTP
Public IP
Port 3000
```

アクセス形式：

```text
http://<EC2_PUBLIC_IP>:3000
```

production buildを使用する。

```bash
npm install
npm run build
npm run start -- -H 0.0.0.0 -p 3000
```

FastAPIとは同一VPC内のPrivate IPを使って通信する。

---

# 30. 実装してはいけないもの

Codexは、要件を補完する目的で以下を勝手に追加してはならない。

```text
・追加のFastAPI endpoint
・Route Handler経由の別API
・OpenAI API
・AI文章生成
・ダミー時系列データ
・ランダムデータ
・検索結果のDB保存
・認証
・ログイン画面
・検索履歴
・URLへの下書き本文埋め込み
・Redux
・複雑なClean Architecture
・Nginx
・HTTPS設定
```

既存APIとの通信は、

```text
GET /press-release/search
```

のみとする。

---

# 31. Codex実装順序

Codexは以下の順序で実装すること。

```text
1. Next.jsプロジェクト構造確認
        ↓
2. FastAPI Type定義
        ↓
3. FastAPI Client
        ↓
4. Server Action
        ↓
5. DraftForm
        ↓
6. Top5一覧
        ↓
7. 指標比較
        ↓
8. PR詳細
        ↓
9. Loading / Error
        ↓
10. UI調整
        ↓
11. npm run build
```

各主要工程の後にTypeScript errorがないことを確認する。

---

# 32. 受入試験

## AC-01 初期表示

**Given:** ユーザーが `/` にアクセスする
**Then:** 下書き入力欄と検索ボタンが表示される

---

## AC-02 空入力

**Given:** 入力欄が空
**When:** 検索を実行しようとする
**Then:** FastAPIを呼ばず入力エラーを表示する

---

## AC-03 2000文字超過

**Given:** 2000文字を超える入力
**Then:** 検索Requestを送信できない

---

## AC-04 正常検索

**Given:** 有効なリード文
**When:** 検索ボタンを押す
**Then:** FastAPIへ以下を1回送信する

```text
GET /press-release/search
query=<入力値>
top_n=5
```

---

## AC-05 Top5

**Given:** FastAPIが5件以上返す
**Then:** 画面には最大5件を表示する

---

## AC-06 データ表示

各PRについて最低限、

```text
title
company_name
similarity_score
```

が表示される。

---

## AC-07 指標切り替え

**When:** ページ閲覧数からユニークユーザー数へ変更する
**Then:** FastAPIを再度呼ばずグラフだけ更新される

---

## AC-08 詳細表示

**When:** Top5のPRを選択する
**Then:** 選択PRの詳細情報が表示される

---

## AC-09 Loading

**When:** FastAPI通信中
**Then:** Loading状態が視認でき、検索ボタンを重複操作できない

---

## AC-10 422

**Given:** FastAPIがHTTP 422を返す
**Then:** ユーザー向け入力エラーを表示する

---

## AC-11 Server Error

**Given:** FastAPIが5xxまたは通信エラー
**Then:** 再試行可能なエラーメッセージを表示する

---

## AC-12 API通信回数

1回の検索操作について、Network上のFastAPI Requestが1件であること。

---

## AC-13 FastAPI非公開

Browser Developer Tools上にFastAPIのPrivate IPが通信先として表示されないこと。

---

## AC-14 Build

以下が成功すること。

```bash
npm run build
```

TypeScript build errorを残さない。

---

# 33. Definition of Done

以下の一連の操作がEC2上の公開URLから完了した時点でプロトタイプ完成とする。

```text
公開URLへアクセス
        ↓
リード文を入力
        ↓
検索
        ↓
FastAPIへ1回通信
        ↓
類似PR最大5件表示
        ↓
PRを選択
        ↓
詳細確認
        ↓
ページ閲覧数 / UU / Like数を切り替えて比較
```

最終的なNext.jsの責務を以下の一文で定義する。

> **既存FastAPIが返す類似プレスリリース検索結果を、一般ユーザーが入力・比較・理解できるWebインターフェースとして提供する。**

本プロトタイプでは、FastAPIレスポンスに存在しない機能やデータをNext.js側で補完しない。
