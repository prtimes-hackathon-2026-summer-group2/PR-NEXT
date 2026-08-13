import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  experimental: {
    // compiler API を使い、ビルド時の型検証を有効に保つ。
    useTypeScriptCli: false,
  },
};

export default nextConfig;
