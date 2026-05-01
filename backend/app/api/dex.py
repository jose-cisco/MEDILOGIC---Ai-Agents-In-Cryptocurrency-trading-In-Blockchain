"""DEX Executor API — On-chain trade execution on Ethereum/Solana DeFi."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.blockchain.dex_executor import dex_executor, DEXPlatform, DEXTradeParams

router = APIRouter()


class QuoteRequest(BaseModel):
    token_in: str
    token_out: str
    amount_in: float
    platform: str = "uniswap_v2"


class SwapRequest(BaseModel):
    token_in: str
    token_out: str
    amount_in: float
    amount_out_min: float = 0.0
    deadline_seconds: int = 300
    platform: str = "uniswap_v2"
    chain: str = "ethereum"
    slippage_tolerance: float = 0.005
    gas_priority: str = "medium"
    private_key: str = ""


@router.get("/quote/ethereum")
async def get_ethereum_quote(
    token_in: str,
    token_out: str,
    amount_in: float,
    platform: str = "uniswap_v2",
):
    result = dex_executor.get_quote_ethereum(
        token_in=token_in,
        token_out=token_out,
        amount_in=amount_in,
        platform=DEXPlatform(platform),
    )
    return result


@router.post("/swap/ethereum")
async def execute_ethereum_swap(request: SwapRequest):
    if not request.private_key:
        raise HTTPException(status_code=400, detail="private_key required for Ethereum swaps")
    params = DEXTradeParams(
        token_in=request.token_in,
        token_out=request.token_out,
        amount_in=request.amount_in,
        amount_out_min=request.amount_out_min,
        deadline_seconds=request.deadline_seconds,
        platform=DEXPlatform(request.platform),
        chain="ethereum",
        slippage_tolerance=request.slippage_tolerance,
        gas_priority=request.gas_priority,
    )
    result = dex_executor.execute_swap_ethereum(params, request.private_key)
    return {
        "success": result.success,
        "status": result.status.value,
        "tx_hash": result.tx_hash,
        "platform": result.platform.value,
        "chain": result.chain,
        "token_in": result.token_in,
        "token_out": result.token_out,
        "amount_in": result.amount_in,
        "amount_out": result.amount_out,
        "gas_used": result.gas_used,
        "confirmation_time": result.confirmation_time,
        "error": result.error,
    }


@router.post("/swap/solana")
async def execute_solana_swap(request: SwapRequest):
    params = DEXTradeParams(
        token_in=request.token_in,
        token_out=request.token_out,
        amount_in=request.amount_in,
        amount_out_min=request.amount_out_min,
        deadline_seconds=request.deadline_seconds,
        platform=DEXPlatform("jupiter") if request.chain == "solana" else DEXPlatform(request.platform),
        chain="solana",
        slippage_tolerance=request.slippage_tolerance,
    )
    # Pass private_key as string (supports base58, JSON array, base64)
    # The executor's _parse_solana_keypair handles all formats
    result = dex_executor.execute_swap_solana(params, request.private_key if request.private_key else None)
    return {
        "success": result.success,
        "status": result.status.value,
        "tx_hash": result.tx_hash,
        "platform": result.platform.value,
        "chain": result.chain,
        "token_in": result.token_in,
        "token_out": result.token_out,
        "amount_in": result.amount_in,
        "amount_out": result.amount_out,
        "confirmation_time": result.confirmation_time,
        "error": result.error,
    }