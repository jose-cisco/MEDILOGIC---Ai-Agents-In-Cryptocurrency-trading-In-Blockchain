"""IPFS API — Off-chain data storage and retrieval endpoints."""
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Any, Optional
from app.core.ipfs_client import ipfs_client

router = APIRouter()


class PinJsonRequest(BaseModel):
    data: dict[str, Any]
    metadata: Optional[dict[str, str]] = None


class PinTextRequest(BaseModel):
    text: str
    metadata: Optional[dict[str, str]] = None


class PinAgentDecisionRequest(BaseModel):
    agent_id: str
    decision_data: dict[str, Any]
    on_chain_hash: str = ""


class PinAuditLogRequest(BaseModel):
    agent_id: str
    event_data: dict[str, Any]
    event_hash: str = ""


class PinMarketDataRequest(BaseModel):
    token_pair: str
    chain: str
    market_data: dict[str, Any]


@router.get("/status")
async def ipfs_status():
    return ipfs_client.get_status()


@router.post("/pin/json")
async def pin_json(request: PinJsonRequest):
    result = ipfs_client.pin_json(request.data, request.metadata)
    return {
        "success": result.success,
        "cid": result.cid,
        "size_bytes": result.size_bytes,
        "gateway_url": result.gateway_url,
        "pin_time_seconds": result.pin_time_seconds,
        "error": result.error,
    }


@router.post("/pin/text")
async def pin_text(request: PinTextRequest):
    result = ipfs_client.pin_text(request.text, request.metadata)
    return {
        "success": result.success,
        "cid": result.cid,
        "size_bytes": result.size_bytes,
        "gateway_url": result.gateway_url,
        "pin_time_seconds": result.pin_time_seconds,
        "error": result.error,
    }


@router.get("/get/{cid}")
async def get_content(cid: str):
    result = ipfs_client.get_json(cid)
    return {
        "success": result.success,
        "cid": result.cid,
        "size_bytes": result.size_bytes,
        "retrieval_time_seconds": result.retrieval_time_seconds,
        "error": result.error,
    }


@router.post("/pin/agent-decision")
async def pin_agent_decision(request: PinAgentDecisionRequest):
    result = ipfs_client.pin_agent_decision(
        agent_id=request.agent_id,
        decision_data=request.decision_data,
        on_chain_hash=request.on_chain_hash,
    )
    return {
        "success": result.success,
        "cid": result.cid,
        "size_bytes": result.size_bytes,
        "gateway_url": result.gateway_url,
        "error": result.error,
    }


@router.post("/pin/audit-log")
async def pin_audit_log(request: PinAuditLogRequest):
    result = ipfs_client.pin_audit_log(
        agent_id=request.agent_id,
        event_data=request.event_data,
        event_hash=request.event_hash,
    )
    return {
        "success": result.success,
        "cid": result.cid,
        "size_bytes": result.size_bytes,
        "gateway_url": result.gateway_url,
        "error": result.error,
    }


@router.post("/pin/market-data")
async def pin_market_data(request: PinMarketDataRequest):
    result = ipfs_client.pin_market_data(
        token_pair=request.token_pair,
        chain=request.chain,
        market_data=request.market_data,
    )
    return {
        "success": result.success,
        "cid": result.cid,
        "size_bytes": result.size_bytes,
        "gateway_url": result.gateway_url,
        "error": result.error,
    }