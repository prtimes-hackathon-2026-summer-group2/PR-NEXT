"""LLM汎用テキスト生成APIのエンドポイント"""

from fastapi import APIRouter

# スキーマ
from .schemas.completion_schema import CompletionRequest, CompletionResponse

# サービスロジック
from .services.completion_service import generate_text_completion

# 補助関数
from .utils.messages_converter import convert_to_openai_messages

router = APIRouter(prefix="/llm", tags=["llm"])

# ============================================================
# 汎用テキスト生成(一括応答)
# ============================================================


@router.post(
    path="/completion",
    summary="LLM汎用テキスト生成API(一括応答)",
)
async def completion_endpoint(request: CompletionRequest) -> CompletionResponse:
    """## LLM汎用テキスト生成API(一括応答)

    メッセージ配列(プロンプト)に対してLLMが生成したテキストをJSONで一括返却します。
    ストリーミングには対応していません。短い処理や、システム内部でのデータ成形
    (分類・情報抽出・要約など)に適しています。
    """
    return await generate_text_completion(
        # メッセージ配列(OpenAI互換APIが要求する型に変換して送信)
        messages=convert_to_openai_messages(request.messages),
        # 生成パラメータ
        generation_params=request.generation_params,
    )
