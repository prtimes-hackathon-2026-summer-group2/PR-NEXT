"""LLMテキスト一括生成APIで使用するサービスロジック"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.api.llm.schemas.completion_schema import (
    CompletionResponse,
    GenerationParams,
    UsageData,
)

# 環境変数・クライアント
from src.core.config import llm_client, settings

# 型チェック時のみインポートするブロック
if TYPE_CHECKING:
    from openai.types.chat import ChatCompletion, ChatCompletionMessageParam


async def generate_text_completion(
    messages: list[ChatCompletionMessageParam],
    generation_params: GenerationParams,
) -> CompletionResponse:
    """メッセージ配列に対してLLMが生成したテキストを一括で取得する

    LLM APIとの通信エラーや、モデルが空応答を返した場合はそのまま例外を送出する。
    ユーザー起因のエラーではないため、ここでは捕捉せずmain.pyのグローバル例外
    ハンドラに処理を委ねる(500エラーとして返却・ログ出力される)。

    Args:
        messages (list[ChatCompletionMessageParam]): メッセージ配列
        generation_params (GenerationParams): 生成パラメータ

    Raises:
        RuntimeError: LLMから有効な応答(content/usage)が得られなかった場合

    Returns:
        CompletionResponse: 生成されたテキストとメタデータ

    """
    # --- 未指定(None)のパラメータはリクエストから除外する ---
    # reasoning_effort等、非対応モデルにnullを送ると400エラーになるパラメータがあるため、
    # 明示的に指定された値のみをkwargsとして渡す(NOT_GIVENのデフォルト挙動に委ねる)。
    optional_params = {
        key: value
        for key, value in {
            "temperature": generation_params.temperature,
            "top_p": generation_params.top_p,
            "max_tokens": generation_params.max_tokens,
            "reasoning_effort": generation_params.reasoning_effort,
        }.items()
        if value is not None
    }

    # --- 生成実行 ---
    response: ChatCompletion = await llm_client.chat.completions.create(
        model=settings.LLM_MODEL_NAME,
        messages=messages,
        stream=False,
        **optional_params,
    )

    # --- レスポンスからテキスト取得 ---
    content = response.choices[0].message.content
    usage = response.usage
    if not content or not usage:
        raise RuntimeError(f"LLM APIから有効な応答が得られませんでした: {response!r}")

    return CompletionResponse(
        content=content,
        usage=UsageData(
            model=settings.LLM_MODEL_NAME,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens,
        ),
    )
