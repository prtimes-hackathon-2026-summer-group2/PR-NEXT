"""LLMテキスト一括生成APIで使用するスキーマ"""

from dataclasses import dataclass
from typing import Annotated, Literal

from pydantic import BaseModel, Field

ROLE_TYPE = Literal["system", "user", "assistant"]

# ==========================================
# メッセージ配列のスキーマ
# ==========================================


class MessageItem(BaseModel):
    """メッセージ配列の要素"""

    role: ROLE_TYPE = Field(..., description="ロール", examples=["user"])
    content: str = Field(..., description="内容", examples=["こんにちは。"])


# ==========================================
# 生成パラメータのスキーマ
# ==========================================


class GenerationParams(BaseModel):
    """生成実行に関するパラメータ"""

    # --- 思考制御 ---
    reasoning_effort: Literal["none", "low", "medium", "high"] | None = Field(
        default=None,
        description="モデルが回答を生成する際にどれだけ推論(思考)にリソースを使うかを調整するパラメータ。高いほど時間や計算をかけて慎重で精度の高い回答になり、低いほど高速で簡潔な回答になる。",
        examples=[None],
    )
    # --- サンプリング制御 ---
    temperature: float | None = Field(
        default=None,
        description="出力のランダム性(多様性)を調整するパラメータ。値が低いほど決定的で安定した回答になり、高いほど多様で創造的な回答になる。",
        examples=[None],
    )
    top_p: float | None = Field(
        default=None,
        description="確率の高い単語から累積確率がpになるまでの候補に絞ってサンプリングする方式(核サンプリング)。小さいほど保守的、大きいほど多様な出力になる。",
        examples=[None],
    )
    # --- 出力制御 ---
    max_tokens: int | None = Field(default=None, description="生成する最大トークン数(出力の長さ上限)を指定する", examples=[None])


# ==========================================
# リクエストスキーマ
# ==========================================


@dataclass
class CompletionRequest:
    """LLMテキスト一括生成APIのリクエスト"""

    messages: Annotated[list[MessageItem], Field(min_length=1, description="メッセージ配列")]
    generation_params: Annotated[GenerationParams, Field(default_factory=GenerationParams, description="生成パラメータ")]


# ==========================================
# レスポンススキーマ
# ==========================================


class UsageData(BaseModel):
    """生成結果に関するメタデータ"""

    model: str = Field(..., description="生成を実行したモデル名")
    prompt_tokens: int = Field(..., description="入力トークン数")
    completion_tokens: int = Field(..., description="出力トークン数")
    total_tokens: int = Field(..., description="合計トークン数")


class CompletionResponse(BaseModel):
    """LLMテキスト一括生成APIのレスポンス"""

    content: str = Field(..., description="LLMが生成したテキスト")
    usage: UsageData = Field(..., description="生成メタデータ")
