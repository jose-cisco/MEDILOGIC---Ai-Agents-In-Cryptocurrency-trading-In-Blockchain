"""
Mock Money Simulation — Simulated Cryptocurrency Trading
=========================================================
Provides simulated cryptocurrency balances for backtesting.
Users trade with virtual (mock) money instead of real capital.

This module manages:
  - Virtual portfolio with multiple crypto assets (BTC, ETH, SOL, USDT)
  - Simulated order execution with NO fees or slippage (pure simulation)
  - Portfolio tracking and P&L calculation
  - Risk limits on the mock portfolio

All balances are virtual — no real money is at risk.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from enum import Enum

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class MockOrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class MockOrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"


@dataclass
class MockBalance:
    """Simulated cryptocurrency balance."""
    usdt: float = 0.0
    btc: float = 0.0
    eth: float = 0.0
    sol: float = 0.0

    def total_usd(self, prices: dict) -> float:
        """Calculate total portfolio value in USD using current prices."""
        return (
            self.usdt
            + self.btc * prices.get("BTC", 0)
            + self.eth * prices.get("ETH", 0)
            + self.sol * prices.get("SOL", 0)
        )


@dataclass
class MockOrder:
    """A simulated order in the mock money system."""
    order_id: str
    side: MockOrderSide
    order_type: MockOrderType
    symbol: str  # e.g. "ETH/USDT"
    quantity: float  # in base currency
    price: float  # execution price
    fee_usdt: float = 0.0  # Always 0 — no fees in simulation
    slippage_pct: float = 0.0  # Always 0 — no slippage in simulation
    executed_at: str = ""
    portfolio_value_after: float = 0.0

    def to_dict(self) -> dict:
        return {
            "order_id": self.order_id,
            "side": self.side.value,
            "type": self.order_type.value,
            "symbol": self.symbol,
            "quantity": round(self.quantity, 8),
            "price": round(self.price, 2),
            "fee_usdt": round(self.fee_usdt, 4),
            "slippage_pct": round(self.slippage_pct * 100, 4),
            "executed_at": self.executed_at,
            "portfolio_value_after": round(self.portfolio_value_after, 2),
        }


@dataclass
class MockTradeResult:
    """Result of a simulated trade execution."""
    success: bool
    order: Optional[MockOrder] = None
    error: str = ""
    balance_after: Optional[MockBalance] = None
    portfolio_value_usd: float = 0.0


class MockMoneyAccount:
    """
    Simulated cryptocurrency trading account.
    
    Manages virtual balances and executes mock trades with NO fees
    or slippage. This is a pure simulation — the goal is to see how
    earnings happen with virtual money, not to simulate real trading costs.
    No real money is involved.
    
    Usage:
        account = MockMoneyAccount()
        result = account.execute_trade("buy", "ETH/USDT", 1.0, 3200.0)
    """

    # Symbol → (base_asset, quote_asset) mapping
    SYMBOL_MAP = {
        "BTC/USDT": ("btc", "usdt"),
        "ETH/USDT": ("eth", "usdt"),
        "SOL/USDT": ("sol", "usdt"),
        "ETH/USDC": ("eth", "usdt"),  # Treat USDC same as USDT for simulation
        "SOL/USDC": ("sol", "usdt"),
    }

    def __init__(
        self,
        initial_usdt: float | None = None,
        initial_btc: float | None = None,
        initial_eth: float | None = None,
        initial_sol: float | None = None,
    ):
        settings = get_settings()
        self.balance = MockBalance(
            usdt=initial_usdt if initial_usdt is not None else settings.MOCK_MONEY_INITIAL_USD,
            btc=initial_btc if initial_btc is not None else settings.MOCK_MONEY_INITIAL_BTC,
            eth=initial_eth if initial_eth is not None else settings.MOCK_MONEY_INITIAL_ETH,
            sol=initial_sol if initial_sol is not None else settings.MOCK_MONEY_INITIAL_SOL,
        )
        self.fee_pct = 0.0  # No fees — pure simulation
        self.slippage_pct = 0.0  # No slippage — pure simulation
        self.orders: list[MockOrder] = []
        self._order_counter = 0
        self._initial_portfolio_value: float | None = None

    def _next_order_id(self) -> str:
        self._order_counter += 1
        return f"MOCK-{self._order_counter:06d}"

    def get_initial_portfolio_value(self, prices: dict) -> float:
        """Get the initial portfolio value (cached after first call)."""
        if self._initial_portfolio_value is None:
            settings = get_settings()
            init_balance = MockBalance(
                usdt=settings.MOCK_MONEY_INITIAL_USD,
                btc=settings.MOCK_MONEY_INITIAL_BTC,
                eth=settings.MOCK_MONEY_INITIAL_ETH,
                sol=settings.MOCK_MONEY_INITIAL_SOL,
            )
            self._initial_portfolio_value = init_balance.total_usd(prices)
        return self._initial_portfolio_value

    def execute_trade(
        self,
        side: str,
        symbol: str,
        quantity: float,
        price: float,
        current_prices: dict | None = None,
    ) -> MockTradeResult:
        """
        Execute a simulated trade with mock money.
        
        No fees or slippage are applied — this is a pure simulation
        to see how earnings happen with virtual money.
        
        Applies:
          - Balance checks (cannot spend more than available)
        
        Args:
            side: "buy" or "sell"
            symbol: Trading pair (e.g. "ETH/USDT")
            quantity: Amount in base currency to buy/sell
            price: Current market price
            current_prices: Dict of {"BTC": price, "ETH": price, ...} for portfolio valuation
            
        Returns:
            MockTradeResult with execution details
        """
        if not current_prices:
            current_prices = {}

        pair = self.SYMBOL_MAP.get(symbol)
        if not pair:
            return MockTradeResult(
                success=False,
                error=f"Unsupported symbol: {symbol}. Supported: {list(self.SYMBOL_MAP.keys())}",
            )

        base_asset, quote_asset = pair
        base_qty = getattr(self.balance, base_asset)
        quote_qty = getattr(self.balance, quote_asset)

        # No slippage — use the exact market price
        exec_price = price

        notional = quantity * exec_price  # Total in quote currency

        # No fee — pure simulation
        fee = 0.0

        if side.lower() == "buy":
            # Check if we have enough quote currency (USDT)
            total_cost = notional  # No fee added
            if total_cost > quote_qty:
                # Adjust quantity to what we can afford
                quantity = quote_qty / exec_price
                notional = quantity * exec_price
                total_cost = notional
                if quantity <= 0:
                    return MockTradeResult(
                        success=False,
                        error="Insufficient USDT balance for this trade.",
                    )

            # Update balances — buy base asset with quote asset
            setattr(self.balance, quote_asset, round(quote_qty - total_cost, 8))
            setattr(self.balance, base_asset, round(base_qty + quantity, 8))

        elif side.lower() == "sell":
            # Check if we have enough base currency
            if quantity > base_qty:
                quantity = base_qty
                notional = quantity * exec_price

            if quantity <= 0:
                return MockTradeResult(
                    success=False,
                    error=f"Insufficient {base_asset.upper()} balance for this trade.",
                )

            # No fee deducted — pure simulation
            net_proceeds = notional
            setattr(self.balance, base_asset, round(base_qty - quantity, 8))
            setattr(self.balance, quote_asset, round(quote_qty + net_proceeds, 8))

        else:
            return MockTradeResult(
                success=False,
                error=f"Invalid side: {side}. Must be 'buy' or 'sell'.",
            )

        # Create order record
        order = MockOrder(
            order_id=self._next_order_id(),
            side=MockOrderSide(side.lower()),
            order_type=MockOrderType.MARKET,
            symbol=symbol,
            quantity=quantity,
            price=exec_price,
            fee_usdt=fee,
            slippage_pct=self.slippage_pct,
            executed_at=datetime.now(timezone.utc).isoformat(),
            portfolio_value_after=self.balance.total_usd(current_prices),
        )
        self.orders.append(order)

        return MockTradeResult(
            success=True,
            order=order,
            balance_after=MockBalance(
                usdt=self.balance.usdt,
                btc=self.balance.btc,
                eth=self.balance.eth,
                sol=self.balance.sol,
            ),
            portfolio_value_usd=order.portfolio_value_after,
        )

    def get_portfolio_summary(self, prices: dict) -> dict:
        """Get a summary of the mock portfolio."""
        total_value = self.balance.total_usd(prices)
        initial_value = self.get_initial_portfolio_value(prices)
        pnl = total_value - initial_value
        pnl_pct = (pnl / initial_value * 100) if initial_value > 0 else 0

        return {
            "balances": {
                "USDT": round(self.balance.usdt, 2),
                "BTC": round(self.balance.btc, 8),
                "ETH": round(self.balance.eth, 8),
                "SOL": round(self.balance.sol, 8),
            },
            "prices_used": {k: round(v, 2) for k, v in prices.items()},
            "total_value_usd": round(total_value, 2),
            "initial_value_usd": round(initial_value, 2),
            "pnl_usd": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
            "total_trades": len(self.orders),
            "total_fees_paid": round(sum(o.fee_usdt for o in self.orders), 4),
            "is_mock": True,
            "disclaimer": "ALL BALANCES ARE SIMULATED — NO REAL MONEY IS AT RISK",
        }

    def reset(self):
        """Reset the mock account to initial balances."""
        settings = get_settings()
        self.balance = MockBalance(
            usdt=settings.MOCK_MONEY_INITIAL_USD,
            btc=settings.MOCK_MONEY_INITIAL_BTC,
            eth=settings.MOCK_MONEY_INITIAL_ETH,
            sol=settings.MOCK_MONEY_INITIAL_SOL,
        )
        self.orders = []
        self._order_counter = 0
        self._initial_portfolio_value = None


# ─── In-memory account store ────────────────────────────────────────────────
# Maps user email → MockMoneyAccount
_mock_accounts: dict[str, MockMoneyAccount] = {}


def get_mock_account(email: str) -> MockMoneyAccount:
    """Get or create a mock money account for a user."""
    key = email.lower().strip()
    if key not in _mock_accounts:
        _mock_accounts[key] = MockMoneyAccount()
    return _mock_accounts[key]


def reset_mock_account(email: str) -> MockMoneyAccount:
    """Reset a user's mock account to initial balances."""
    key = email.lower().strip()
    if key in _mock_accounts:
        _mock_accounts[key].reset()
    else:
        _mock_accounts[key] = MockMoneyAccount()
    return _mock_accounts[key]
