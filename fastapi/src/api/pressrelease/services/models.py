"""pressreleaseドメインのサービス層が返す型定義"""

from dataclasses import dataclass


@dataclass
class ReleaseSearchResult:
    """execute_release_search()が返す類似プレスリリース検索の結果"""

    hits: int
    data: list[dict]
