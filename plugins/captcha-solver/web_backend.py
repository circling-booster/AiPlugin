from fastapi import APIRouter
router = APIRouter()
@router.post("/solve")
def solve(): return {"text": "CLOUD_SOLVED"}