"""A_releaseパイプラインで共有する型定義。"""

from dataclasses import dataclass


@dataclass
class ReleaseLeadParagraphRecord:
    """ベクトル化対象の1行ぶんのデータ(複合主キー・リード文)。"""

    company_id: int
    release_id: int
    lead_paragraph: str
