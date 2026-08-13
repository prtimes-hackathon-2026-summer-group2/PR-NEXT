"""アプリケーション全体で共有するグローバルリソースの定義と初期化"""

import threading
from dataclasses import dataclass, field

from sentence_transformers import SentenceTransformer

# 環境変数
from src.core.config import settings
from src.core.device import get_device

# ============================================================
# グローバルリソースの定義 (`main.py`の`lifespan`内で初期化)
# ============================================================


@dataclass
class MLModels:
    """機械学習モデルをインスタンス化して管理するデータクラス

    Note:
        SudachiPyの`Tokenizer`はスレッドセーフではなく、複数スレッドから同時に
        `tokenize()`を呼ぶと`RuntimeError: Already borrowed`が発生する。
        辞書(`Dictionary`)自体は共有可能なため、辞書のみをここに保持し、
        `Tokenizer`は`get_sudachi_tokenizer()`経由でスレッドごとに生成・キャッシュする。
        (`SentenceTransformer`は複数スレッドからの同時`encode()`が可能なため共有してよい)

    """

    embedding_model: SentenceTransformer | None = None
    # スレッドごとの`Tokenizer`の保管場所(スレッドをまたいで共有されない領域)
    thread_local: threading.local = field(default_factory=threading.local, repr=False)

    def clear(self) -> None:
        """インスタンスから削除する"""
        self.embedding_model = None
        self.sudachi_dictionary = None
        self.sudachi_mode_search = None
        # 各スレッドが保持している`Tokenizer`への参照も破棄する
        self.thread_local = threading.local()


# --- インスタンス化 ---
ml_models = MLModels()


# ============================================================
# 初期化処理
# ============================================================


def init_ml_models() -> None:
    """埋め込みモデルを初期化する

    Note:
        モデルのロードはCPU/ディスクバウンドかつ数十秒かかる場合があるため、
        起動時(リクエスト受付前)にのみ呼ばれることを前提に同期関数のままとしている。

    """
    print("埋め込みモデルをロードしています...")
    print(f"モデル名: {settings.EMBEDDING_MODEL} | 次元数: {settings.EMBEDDING_DIMENSION}")
    device = get_device()
    ml_models.embedding_model = SentenceTransformer(
        settings.EMBEDDING_MODEL,
        device=str(device),
        token=settings.HF_TOKEN,
    )
