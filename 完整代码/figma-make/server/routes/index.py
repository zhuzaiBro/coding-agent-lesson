"""健康检查 / 根路径探活。"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def index():
    """部署后用于确认 API 进程已启动。"""
    return "Welcome to the API server!"
