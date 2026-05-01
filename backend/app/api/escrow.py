"""
Trade Escrow API
================
Manages smart contract escrow for trading capital, profit withdrawal,
and automatic fee distribution.

Financial Flow:
1. Owner deposits trading capital to TradeEscrow contract
2. AI agent executes trades via escrow
3. Profits accumulate in escrow with automatic fee deduction
4. Owner withdraws profits via /escrow/withdraw endpoint
5. x402 payments collected separately (see payments.py)
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import logging

from app.core.config import get_settings
from app.core.auth import require_auth

logger = logging.getLogger(__name__)

router = APIRouter()


# ─── Request/Response Models ──────────────────────────────────────────────────

class DepositRequest(BaseModel):
    """Request to deposit funds to escrow."""
    token_address: str = Field(
        default="0x0000000000000000000000000000000000000000",
        description="Token address (0x0 for ETH)"
    )
    amount: float = Field(..., gt=0, description="Amount to deposit")


class WithdrawRequest(BaseModel):
    """Request to withdraw profits from escrow."""
    token_address: str = Field(
        default="0x0000000000000000000000000000000000000000",
        description="Token address (0x0 for ETH)"
    )
    amount: float = Field(..., gt=0, description="Amount to withdraw")


class FeeConfigRequest(BaseModel):
    """Request to update fee configuration."""
    trading_fee_bps: int = Field(..., ge=0, le=1000, description="Trading fee in basis points")
    profit_share_bps: int = Field(..., ge=0, le=5000, description="Profit share in basis points")
    x402_allocation_bps: int = Field(
        default=0, ge=0, le=1000,
        description="x402 fee allocation in basis points"
    )


class TradeLimitsRequest(BaseModel):
    """Request to update trade limits."""
    max_trade_size: float = Field(default=0, ge=0, description="Maximum single trade size")
    daily_trade_limit: int = Field(default=0, ge=0, description="Maximum trades per day")


class AutoWithdrawConfigRequest(BaseModel):
    """Request to configure auto-withdrawal."""
    threshold: float = Field(..., ge=0, description="Profit threshold for auto-withdrawal")
    recipient: str = Field(..., description="Recipient address")


class EscrowSummaryResponse(BaseModel):
    """Escrow summary response."""
    trading_balance: float
    total_profit: float
    total_fees_collected: float
    total_trades: int
    total_withdrawn: float
    withdrawable_profit: float
    owner_address: str
    trading_agent_address: str
    fee_recipient_address: str
    x402_recipient_address: str
    trading_fee_bps: int
    profit_share_bps: int
    x402_allocation_bps: int
    auto_withdraw_threshold: float
    max_trade_size: float
    daily_trade_limit: int


class TradeRecord(BaseModel):
    """Single trade record."""
    trade_id: str
    token_in: str
    token_out: str
    amount_in: float
    amount_out: float
    fee_deducted: float
    timestamp: str
    is_profit: bool


class WithdrawalRecord(BaseModel):
    """Single withdrawal record."""
    recipient: str
    token: str
    amount: float
    timestamp: str


class ProfitSplitResponse(BaseModel):
    """Profit split configuration and status."""
    trading_fee_bps: int
    profit_share_bps: int
    x402_allocation_bps: int
    x402_payments_collected: float
    trading_fees_collected: float
    total_revenue: float
    owner_share: float
    x402_share: float
    auto_withdraw_enabled: bool
    auto_withdraw_threshold: float


# ─── Mock Data Store (Replace with actual contract calls in production) ─────

# In production, these would interact with the TradeEscrow smart contract
_escrow_state = {
    "trading_balance": 0.0,
    "total_profit": 0.0,
    "total_fees_collected": 0.0,
    "total_trades": 0,
    "total_withdrawn": 0.0,
    "trades": [],
    "withdrawals": [],
    "trading_fee_bps": 50,
    "profit_share_bps": 1000,
    "x402_allocation_bps": 0,
    "auto_withdraw_threshold": 0.0,
    "max_trade_size": 0.0,
    "daily_trade_limit": 0,
}

# Track x402 payments separately (from payments.py)
_x402_payments = {
    "total_collected": 0.0,
    "payments": [],  # List of {tx_hash, amount, resource, timestamp}
}


# ─── Helper Functions ──────────────────────────────────────────────────────

def _get_escrow_contract():
    """Get or create escrow contract connection."""
    settings = get_settings()
    # In production, this would return a web3 contract instance
    # from app.blockchain.ethereum import EthereumClient
    # eth = EthereumClient()
    # return eth.w3.eth.contract(...)
    return None


def _record_x402_payment(amount: float, resource: str, tx_hash: str):
    """Record an x402 payment (called from payments middleware)."""
    _x402_payments["total_collected"] += amount
    _x402_payments["payments"].append({
        "tx_hash": tx_hash,
        "amount": amount,
        "resource": resource,
        "timestamp": datetime.utcnow().isoformat(),
    })


# ─── Endpoints ──────────────────────────────────────────────────────────────

@router.get("/summary", response_model=EscrowSummaryResponse)
async def get_escrow_summary(request: Request):
    """
    Get comprehensive escrow summary.
    
    Returns trading balance, profits, fees, and configuration.
    """
    settings = get_settings()
    
    # In production, call contract's getSummary()
    # contract = _get_escrow_contract()
    # summary = contract.functions.getSummary().call()
    
    return EscrowSummaryResponse(
        trading_balance=_escrow_state["trading_balance"],
        total_profit=_escrow_state["total_profit"],
        total_fees_collected=_escrow_state["total_fees_collected"],
        total_trades=_escrow_state["total_trades"],
        total_withdrawn=_escrow_state["total_withdrawn"],
        withdrawable_profit=_escrow_state["total_profit"] - _escrow_state["total_withdrawn"],
        owner_address=settings.X402_RECIPIENT_ADDRESS or "0x_not_configured",
        trading_agent_address="0x_trading_agent",  # From contract
        fee_recipient_address=settings.X402_RECIPIENT_ADDRESS or "0x_not_configured",
        x402_recipient_address=settings.X402_RECIPIENT_ADDRESS or "0x_not_configured",
        trading_fee_bps=_escrow_state["trading_fee_bps"],
        profit_share_bps=_escrow_state["profit_share_bps"],
        x402_allocation_bps=_escrow_state["x402_allocation_bps"],
        auto_withdraw_threshold=_escrow_state["auto_withdraw_threshold"],
        max_trade_size=_escrow_state["max_trade_size"],
        daily_trade_limit=_escrow_state["daily_trade_limit"],
    )


@router.post("/deposit")
async def deposit_to_escrow(
    deposit_request: DepositRequest,
    request: Request
):
    """
    Deposit trading capital to escrow.
    
    In production, this triggers a blockchain transaction:
    1. User signs transaction to transfer tokens/ETH to escrow
    2. Escrow contract records deposit
    3. Funds become available for AI trading
    """
    # In production:
    # contract = _get_escrow_contract()
    # if token_address == "0x0":
    #     tx = contract.functions.depositETH().transact({"value": amount_wei})
    # else:
    #     # Approve token transfer first
    #     token_contract.functions.approve(escrow_address, amount).transact()
    #     tx = contract.functions.depositToken(token_address, amount).transact()
    
    _escrow_state["trading_balance"] += deposit_request.amount
    
    logger.info(
        "Escrow deposit: %.6f tokens to %s",
        deposit_request.amount,
        deposit_request.token_address
    )
    
    return {
        "success": True,
        "amount": deposit_request.amount,
        "token": deposit_request.token_address,
        "new_balance": _escrow_state["trading_balance"],
        "message": "Deposit recorded (simulated). In production, blockchain transaction required.",
    }


@router.post("/withdraw")
async def withdraw_profits(
    withdraw_request: WithdrawRequest,
    request: Request
):
    """
    Withdraw profits from escrow to owner wallet.
    
    Only withdrawable profits (total_profit - total_withdrawn) can be withdrawn.
    In production, this triggers a blockchain transaction.
    """
    withdrawable = _escrow_state["total_profit"] - _escrow_state["total_withdrawn"]
    
    if withdraw_request.amount > withdrawable:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot withdraw more than withdrawable profits ({withdrawable:.6f})"
        )
    
    if withdraw_request.amount > _escrow_state["trading_balance"]:
        raise HTTPException(
            status_code=400,
            detail="Insufficient balance in escrow"
        )
    
    # In production:
    # contract = _get_escrow_contract()
    # tx = contract.functions.withdrawProfits(token_address, amount_wei).transact()
    
    _escrow_state["trading_balance"] -= withdraw_request.amount
    _escrow_state["total_withdrawn"] += withdraw_request.amount
    _escrow_state["withdrawals"].append({
        "recipient": request.client.host if request.client else "unknown",
        "token": withdraw_request.token_address,
        "amount": withdraw_request.amount,
        "timestamp": datetime.utcnow().isoformat(),
    })
    
    logger.info(
        "Escrow withdrawal: %.6f tokens to owner",
        withdraw_request.amount
    )
    
    return {
        "success": True,
        "amount": withdraw_request.amount,
        "token": withdraw_request.token_address,
        "remaining_profit": _escrow_state["total_profit"] - _escrow_state["total_withdrawn"],
        "tx_hash": "0x_simulated_withdrawal_" + datetime.utcnow().strftime("%Y%m%d%H%M%S"),
    }


@router.post("/withdraw-all")
async def withdraw_all_profits(request: Request):
    """
    Withdraw all withdrawable profits to owner wallet.
    """
    withdrawable = _escrow_state["total_profit"] - _escrow_state["total_withdrawn"]
    
    if withdrawable <= 0:
        raise HTTPException(
            status_code=400,
            detail="No withdrawable profits"
        )
    
    _escrow_state["trading_balance"] -= withdrawable
    _escrow_state["total_withdrawn"] += withdrawable
    
    return {
        "success": True,
        "amount": withdrawable,
        "tx_hash": "0x_simulated_withdrawal_" + datetime.utcnow().strftime("%Y%m%d%H%M%S"),
    }


@router.post("/configure/fees")
async def configure_fees(
    fee_config: FeeConfigRequest,
    request: Request
):
    """
    Configure fee distribution.
    
    - trading_fee_bps: Fee per trade (basis points)
    - profit_share_bps: Profit share to fee recipient (basis points)
    - x402_allocation_bps: Portion of fees to x402 recipient (basis points)
    
    Total fees must not exceed 100% (10000 bps).
    """
    # In production:
    # contract = _get_escrow_contract()
    # tx = contract.functions.setFeeConfiguration(
    #     fee_config.trading_fee_bps,
    #     fee_config.profit_share_bps,
    #     fee_config.x402_allocation_bps
    # ).transact()
    
    _escrow_state["trading_fee_bps"] = fee_config.trading_fee_bps
    _escrow_state["profit_share_bps"] = fee_config.profit_share_bps
    _escrow_state["x402_allocation_bps"] = fee_config.x402_allocation_bps
    
    logger.info(
        "Fee configuration updated: trading=%d bps, profit_share=%d bps, x402=%d bps",
        fee_config.trading_fee_bps,
        fee_config.profit_share_bps,
        fee_config.x402_allocation_bps
    )
    
    return {
        "success": True,
        "trading_fee_bps": fee_config.trading_fee_bps,
        "profit_share_bps": fee_config.profit_share_bps,
        "x402_allocation_bps": fee_config.x402_allocation_bps,
    }


@router.post("/configure/limits")
async def configure_trade_limits(
    limits: TradeLimitsRequest,
    request: Request
):
    """
    Configure trading limits for safety.
    
    - max_trade_size: Maximum single trade size (0 = unlimited)
    - daily_trade_limit: Maximum trades per day (0 = unlimited)
    """
    _escrow_state["max_trade_size"] = limits.max_trade_size
    _escrow_state["daily_trade_limit"] = limits.daily_trade_limit
    
    return {
        "success": True,
        "max_trade_size": limits.max_trade_size,
        "daily_trade_limit": limits.daily_trade_limit,
    }


@router.post("/configure/auto-withdraw")
async def configure_auto_withdraw(
    config: AutoWithdrawConfigRequest,
    request: Request
):
    """
    Configure automatic profit withdrawal.
    
    When profits reach threshold, automatically withdraw to recipient.
    Set threshold=0 to disable.
    """
    _escrow_state["auto_withdraw_threshold"] = config.threshold
    
    # In production:
    # contract = _get_escrow_contract()
    # tx = contract.functions.setAutoWithdraw(threshold_wei, recipient).transact()
    
    return {
        "success": True,
        "auto_withdraw_threshold": config.threshold,
        "recipient": config.recipient,
        "enabled": config.threshold > 0,
    }


@router.get("/profit-split", response_model=ProfitSplitResponse)
async def get_profit_split(request: Request):
    """
    Get profit split configuration and status.
    
    Shows how revenue is split between:
    - Trading fees (per trade)
    - Profit share (from profitable trades)
    - x402 API payments (collected separately)
    """
    settings = get_settings()
    
    trading_fees = _escrow_state["total_fees_collected"]
    x402_payments = _x402_payments["total_collected"]
    total_revenue = trading_fees + x402_payments
    
    # Calculate splits
    x402_split = (trading_fees * _escrow_state["x402_allocation_bps"]) / 10000
    owner_split = trading_fees - x402_split
    
    return ProfitSplitResponse(
        trading_fee_bps=_escrow_state["trading_fee_bps"],
        profit_share_bps=_escrow_state["profit_share_bps"],
        x402_allocation_bps=_escrow_state["x402_allocation_bps"],
        x402_payments_collected=x402_payments,
        trading_fees_collected=trading_fees,
        total_revenue=total_revenue,
        owner_share=owner_split,
        x402_share=x402_split,
        auto_withdraw_enabled=_escrow_state["auto_withdraw_threshold"] > 0,
        auto_withdraw_threshold=_escrow_state["auto_withdraw_threshold"],
    )


@router.get("/trades", response_model=List[TradeRecord])
async def get_trade_history(
    offset: int = 0,
    limit: int = 50,
    request: Request = None
):
    """
    Get trade history from escrow.
    """
    trades = _escrow_state["trades"][offset:offset + limit]
    return [
        TradeRecord(
            trade_id=t.get("trade_id", ""),
            token_in=t.get("token_in", ""),
            token_out=t.get("token_out", ""),
            amount_in=t.get("amount_in", 0),
            amount_out=t.get("amount_out", 0),
            fee_deducted=t.get("fee_deducted", 0),
            timestamp=t.get("timestamp", ""),
            is_profit=t.get("is_profit", False),
        )
        for t in trades
    ]


@router.get("/withdrawals", response_model=List[WithdrawalRecord])
async def get_withdrawal_history(
    offset: int = 0,
    limit: int = 50,
    request: Request = None
):
    """
    Get withdrawal history from escrow.
    """
    withdrawals = _escrow_state["withdrawals"][offset:offset + limit]
    return [
        WithdrawalRecord(
            recipient=w.get("recipient", ""),
            token=w.get("token", ""),
            amount=w.get("amount", 0),
            timestamp=w.get("timestamp", ""),
        )
        for w in withdrawals
    ]


@router.get("/x402-payments")
async def get_x402_payments(
    offset: int = 0,
    limit: int = 50,
    request: Request = None
):
    """
    Get x402 API payment history (separate from trading fees).
    
    x402 payments are collected from external API users who pay
    per API call for trade execution, analysis, etc.
    """
    payments = _x402_payments["payments"][offset:offset + limit]
    return {
        "total_collected": _x402_payments["total_collected"],
        "payment_count": len(_x402_payments["payments"]),
        "payments": payments,
    }


@router.post("/record-trade")
async def record_trade_execution(
    trade_id: str,
    token_in: str,
    token_out: str,
    amount_in: float,
    amount_out: float,
    is_profit: bool,
    request: Request
):
    """
    Record a trade execution (internal, called by trading agent).
    
    This endpoint is called after a DEX swap to record the trade
    in the escrow and deduct fees.
    """
    # Calculate fee
    fee = (amount_in * _escrow_state["trading_fee_bps"]) / 10000
    
    # Record trade
    _escrow_state["trades"].append({
        "trade_id": trade_id,
        "token_in": token_in,
        "token_out": token_out,
        "amount_in": amount_in,
        "amount_out": amount_out,
        "fee_deducted": fee,
        "timestamp": datetime.utcnow().isoformat(),
        "is_profit": is_profit,
    })
    
    _escrow_state["total_trades"] += 1
    _escrow_state["total_fees_collected"] += fee
    
    if is_profit:
        profit_share = (fee * _escrow_state["profit_share_bps"]) / 10000
        _escrow_state["total_profit"] += profit_share
    
    return {
        "success": True,
        "trade_id": trade_id,
        "fee_deducted": fee,
        "is_profit": is_profit,
    }


@router.get("/pnl-dashboard")
async def get_pnl_dashboard(request: Request):
    """
    Comprehensive PnL dashboard combining:
    - Trading PnL from escrow
    - x402 API payment collection
    - Fee distribution
    - Withdrawal status
    """
    settings = get_settings()
    
    trading_pnl = _escrow_state["total_profit"]
    fees_collected = _escrow_state["total_fees_collected"]
    x402_collected = _x402_payments["total_collected"]
    
    # Revenue breakdown
    revenue = {
        "trading_profits": trading_pnl,
        "trading_fees": fees_collected,
        "x402_api_payments": x402_collected,
        "total": trading_pnl + fees_collected + x402_collected,
    }
    
    # Fee distribution
    x402_share = (fees_collected * _escrow_state["x402_allocation_bps"]) / 10000
    owner_fee_share = fees_collected - x402_share
    
    distribution = {
        "owner_wallet": {
            "trading_profits": trading_pnl - _escrow_state["total_withdrawn"],
            "fee_share": owner_fee_share,
            "x402_payments": x402_collected,
            "total": (trading_pnl - _escrow_state["total_withdrawn"]) + owner_fee_share + x402_collected,
        },
        "x402_pool": {
            "fee_allocation": x402_share,
        },
    }
    
    # Withdrawable amounts
    withdrawable = {
        "trading_profits": trading_pnl - _escrow_state["total_withdrawn"],
        "x402_payments": x402_collected,  # Direct to recipient
    }
    
    return {
        "summary": {
            "total_trades": _escrow_state["total_trades"],
            "total_profit": trading_pnl,
            "total_fees": fees_collected,
            "total_x402": x402_collected,
            "total_withdrawn": _escrow_state["total_withdrawn"],
            "withdrawable": withdrawable["trading_profits"],
        },
        "revenue": revenue,
        "distribution": distribution,
        "withdrawable": withdrawable,
        "configuration": {
            "trading_fee_bps": _escrow_state["trading_fee_bps"],
            "profit_share_bps": _escrow_state["profit_share_bps"],
            "x402_allocation_bps": _escrow_state["x402_allocation_bps"],
            "auto_withdraw_enabled": _escrow_state["auto_withdraw_threshold"] > 0,
            "auto_withdraw_threshold": _escrow_state["auto_withdraw_threshold"],
        },
        "recipient_addresses": {
            "owner": settings.X402_RECIPIENT_ADDRESS or "not configured",
            "x402_recipient": settings.X402_RECIPIENT_ADDRESS or "not configured",
        },
    }