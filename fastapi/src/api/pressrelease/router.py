"""プレスリリース関連のエンドポイント"""

from fastapi import APIRouter

router = APIRouter(prefix="/press-release", tags=["press-release"])
