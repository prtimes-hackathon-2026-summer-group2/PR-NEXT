"""共通設定・環境変数の読み込み"""

from openai import AsyncOpenAI
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """環境変数"""

    # --- .env ファイルを自動で読み込む設定 ---
    model_config = SettingsConfigDict(
        env_file=".env",  # プロジェクトルート直下を指定
        extra="ignore",  # 定義していない変数は無視する
    )

    # --- .env から直接読み取る値 ---
    DB_USER: str = Field(..., description="[データベース]DBユーザー名")
    DB_PASSWORD: str = Field(..., description="[データベース]DBパスワード")
    DB_NAME: str = Field(..., description="[データベース]DB名")
    DB_HOST: str = Field(..., description="[データベース]DBホスト名(RDSのエンドポイントなど)")
    DB_PORT: int = Field(default=5432, description="[データベース]接続ポート")

    # --- LLMテキスト生成関係 ---
    LLM_API_KEY: str = Field(..., description="[LLM]APIキー")
    LLM_MODEL_NAME: str = Field(..., description="[LLM]使用するモデル名")
    LLM_BASE_URL: str | None = Field(
        default=None,
        description="[LLM]APIのベースURL(省略時はOpenAI公式のエンドポイントを使用。Azure OpenAIやOllama等のOpenAI互換エンドポイントを使う場合に指定する)",
    )

    # --- ベクトル検索関係 ---
    EMBEDDING_MODEL: str = Field(..., description="[RAG]埋め込みモデル名")
    EMBEDDING_DIMENSION: int = Field(..., description="[RAG]埋め込みモデルの次元数")
    EMBEDDING_MAX_SEQUENCE_LENGTH: int = Field(..., description="[RAG]埋め込みモデルの最大トークン数")
    EMBEDDING_MAX_CONCURRENCY: int = Field(
        default=4,
        description=(
            "[RAG]埋め込み推論を同時実行する上限"
            "(CPU推論では1回の推論が複数コアを使うため、無制限に並列化するとコアの奪い合いで全体が遅くなる)"
        ),
    )
    # list型で受けるとpydantic-settingsがJSONとして解釈してしまうため、文字列で受けてプロパティで分割する
    CORS_ALLOW_ORIGINS: str = Field(
        default="",
        description=(
            "[CORS]ブラウザからの直接アクセスを許可するオリジン(カンマ区切り)。"
            "CORSはブラウザが利用者を保護する仕組みであり、サーバー側のアクセス制御ではない点に注意"
        ),
    )

    # --- None許容の値 ---
    HF_TOKEN: str | None = Field(None, description="[トークン]HuggingFaceのアクセストークン(埋め込みモデルダウンロード高速化用)")

    @property
    def CORS_ALLOW_ORIGIN_LIST(self) -> list[str]:
        """カンマ区切りのCORS許可オリジンをリストに変換して返す(空文字の場合は空リスト)"""
        return [origin.strip() for origin in self.CORS_ALLOW_ORIGINS.split(",") if origin.strip()]

    @property
    def DATABASE_URL(self) -> str:
        """環境変数の設定値を直接使って接続URLを構築する"""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

settings = Settings()  # pyright: ignore[reportCallIssue]

# --- LLMクライアントのインスタンス化 ---
llm_client = AsyncOpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)
