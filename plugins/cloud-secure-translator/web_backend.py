from fastapi import APIRouter, Request

router = APIRouter()

@router.post("/translate")
async def translate(request: Request):
    # This runs on the Cloud Server (Port 8000), NOT Local Core
    data = await request.json()
    return {
        "status": "success", 
        "data": f"[WEB-TRANSLATED] {data.get('payload', {}).get('text')}"
    }