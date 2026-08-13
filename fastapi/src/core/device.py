"""処理デバイスを管理するモジュール"""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

# 型チェック時のみインポート
if TYPE_CHECKING:
    import torch


@lru_cache(maxsize=1)
def get_device() -> torch.device:
    """処理デバイスを識別してtorch.deviceオブジェクトを取得する。

    初回呼び出し時のみPyTorchをインポートして最適なデバイス
    を自動判定します。2回目以降の呼び出しは、キャッシュされた同じ
    torch.deviceオブジェクトを返します。

    Returns:
        torch.device: 実行環境に応じて最適化されたデバイスオブジェクト。

    Examples:
        >>> device = get_device()
        >>> print(device)
        cuda

    """
    import torch  # noqa: PLC0415 実行時の読み込みを軽量化するための遅延インポート

    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")
