from fastapi import APIRouter, HTTPException
from app.services.trader_service import trader_service
from pydantic import BaseModel

router = APIRouter()

class StatusUpdateRequest(BaseModel):
    status: str

@router.get("/")
async def list_traders():
    return trader_service.list_traders()

@router.post("/{trader_id}/status")
async def update_trader_status(trader_id: str, request: StatusUpdateRequest):
    success = trader_service.update_status(trader_id, request.status)
    if not success:
        raise HTTPException(status_code=404, detail="Trader not found")
    return {"success": True}

@router.delete("/{trader_id}")
async def delete_trader(trader_id: str):
    success = trader_service.delete_trader(trader_id)
    if not success:
        raise HTTPException(status_code=404, detail="Trader not found")
    return {"success": True}
