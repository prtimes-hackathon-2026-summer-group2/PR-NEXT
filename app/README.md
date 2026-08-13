# PR NEXT prototype

既存 FastAPI の類似プレスリリース検索結果を、入力・比較・閲覧するための Next.js プロトタイプです。

## セットアップ

Node.js は `fnm`、パッケージ管理は `pnpm` を使用します。

```bash
fnm use --install-if-missing
pnpm install
cp .env.example .env.local
pnpm dev
```

`.env.local` の `FASTAPI_URL` には、Next.js サーバーから到達できる FastAPI の URL を指定してください。ブラウザへ公開しないため、変数名に `NEXT_PUBLIC_` は付けません。

## Production

```bash
fnm use --install-if-missing
pnpm install --frozen-lockfile
pnpm build
pnpm start --hostname 0.0.0.0 --port 3000
```
