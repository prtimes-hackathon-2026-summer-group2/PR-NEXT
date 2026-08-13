"""メッセージ配列をOpenAI互換APIが要求する型に変換するモジュール"""

from openai.types.chat import ChatCompletionMessageParam

from src.api.llm.schemas.completion_schema import MessageItem


def convert_to_openai_messages(messages: list[MessageItem]) -> list[ChatCompletionMessageParam]:
    """OpenAI互換APIに送信するメッセージ配列に変換する

    Args:
        messages (list[MessageItem]): 変換元のメッセージ配列

    Returns:
        list[ChatCompletionMessageParam]: 変換後のメッセージ配列

    """
    openai_messages: list[ChatCompletionMessageParam] = []
    for message in messages:
        if message.role == "system":
            openai_messages.append({"role": "system", "content": message.content})
        elif message.role == "user":
            openai_messages.append({"role": "user", "content": message.content})
        elif message.role == "assistant":
            openai_messages.append({"role": "assistant", "content": message.content})
    return openai_messages
