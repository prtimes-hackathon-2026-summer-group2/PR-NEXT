"""アプリのメタデータを定義するモジュール"""

from typing import ClassVar


class AppMetadata:
    """FastAPIのインスタンス化時に指定するメタデータ定数群"""

    TITLE: str = "PR_NEXT"
    VERSION: str = "1.0.0"
    SUMMARY: str = "PRTIMESのデータベースを活用し、プレスリリースの検索等を行うAPIを提供します。"

    CONTACT: ClassVar[dict[str, str]] = {
        "name": "GitHub",
        "url": "https://github.com/prtimes-hackathon-2026-summer-group2/PR-NEXT.git",
    }

    # タグ名をASCIIにしている理由:
    # OpenAPIスキーマのタグは、生成ツールによってはクライアント側のファイル名・クラス名・
    # 名前空間の元として使われる。日本語のままでは生成される識別子が壊れる可能性があるため、
    # 名前はASCIIとし、日本語の説明は description 側へ寄せている。
    TAGS: ClassVar[list[dict[str, str]]] = [
        {"name": "press-release", "description": "プレスリリースを検索・取得します。"},
    ]

    DESCRIPTION: str = """
FastAPIの責務: データの検索・加工
Next.jsの責務: 
""".strip()
