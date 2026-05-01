"""
Paper Trading Engine — Forward Testing with Virtual Money
===========================================================

Paper trading (also called Forward Testing) runs the AI agent live on
real-time market data, but without using real money. Trades are simulated
in a virtual account.

Key Differences from Backtesting:
--------------------------------
| Aspect           | Backtesting          | Paper Trading        |
|------------------|---------------------|----------------------|
| Data used        | Historical (past)   | Live / real-time     |
| Speed            | Very fast           | Real-time (real wait)|
| Realism          | Low                 | Much higher          |
| Risk             | None                | None (virtual money) |
| Best for         | Strategy dev        | Final validation     |

When to Use:
-----------
After backtesting looks good. This is the CRITICAL step before letting
the agent trade with real money or offering it to clients.

Advantages:
-----------
- Tests how the system performs in current market conditions
- Reveals real problems: slippage, API delays, liquidity issues
- Tests agent decision speed in real time
- Much closer to live trading performance

Limitations:
-----------
- Still not 100% real (no actual emotional pressure or capital risk)
- Takes real time — you have to wait for the market to move forward
"""
import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional, Callable, Any
from enum import Enum
import httpx
import uuid

logger = logging.getLogger(__name__)


class PaperTradingState(str, Enum):
    """State of a paper trading session."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"


class PaperOrderType(str, Enum):
    """Order types for paper trading."""
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"


@dataclass
class PaperPosition:
    """Virtual position held in paper trading account."""
    token_pair: str
    chain: str
    amount: float  # Token amount
    entry_price: float
    entry_time: datetime
    current_value: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0


@dataclass
class PaperOrder:
    """Virtual order in paper trading system."""
    order_id: str
    token_pair: str
    chain: str
    order_type: PaperOrderType
    side: str  # "buy" or "sell"
    amount: float  # Token amount or USD value
    price: Optional[float] = None  # For limit orders
    stop_price: Optional[float] = None  # For stop orders
    status: str = "pending"  # pending, filled, cancelled, expired
    created_at: datetime = field(default_factory=datetime.utcnow)
    filled_at: Optional[datetime] = None
    filled_price: Optional[float] = None
    slippage: float = 0.0  # Simulated slippage
    fee: float = 0.0  # Simulated fee
    reasoning: str = ""


@dataclass
class PaperTradeRecord:
    """Record of a completed paper trade."""
    trade_id: str
    token_pair: str
    chain: str
    side: str
    amount: float
    price: float
    timestamp: datetime
    reasoning: str
    confidence: float
    slippage: float
    fee: float
    pnl: float = 0.0
    pnl_pct: float = 0.0
    agent_decision_time_ms: float = 0.0
    execution_delay_ms: float = 0.0


@dataclass
class PaperTradingSession:
    """Complete paper trading session with metrics."""
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    initial_capital: float = 10000.0
    current_capital: float = 10000.0
    positions: dict[str, PaperPosition] = field(default_factory=dict)
    orders: list[PaperOrder] = field(default_factory=list)
    trades: list[PaperTradeRecord] = field(default_factory=list)
    total_pnl: float = 0.0
    total_pnl_pct: float = 0.0
    win_count: int = 0
    loss_count: int = 0
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    peak_capital: float = 10000.0
    state: PaperTradingState = PaperTradingState.IDLE
    config: dict = field(default_factory=dict)


class PaperTradingEngine:
    """
    Paper Trading Engine for forward testing with virtual money.
    
    Features:
    - Real-time market data (NOT historical like backtesting)
    - Virtual account with simulated balances
    - Realistic slippage and fee simulation
    - Latency tracking for decision and execution times
    - Position management with TP/SL simulation
    - Performance metrics tracking
    
    This is the CRITICAL validation step before live trading.
    """
    
    # Default simulation parameters (can be configured)
    DEFAULT_SLIPPAGE_PCT = 0.001  # 0.1% default slippage
    DEFAULT_FEE_PCT = 0.001  # 0.1% trading fee
    DEFAULT_DECISION_DELAY_MS = 500  # Simulated AI decision time
    DEFAULT_EXECUTION_DELAY_MS = 200  # Simulated network delay
    
    # CoinGecko API for real-time prices
    COINGECKO_API = "https://api.coingecko.com/api/v3"
    
    SYMBOL_MAP = {
        "ETH/USDT": "ethereum",
        "ETH/USDC": "ethereum",
        "SOL/USDT": "solana",
        "BTC/USDT": "bitcoin",
        "BTC/USDC": "bitcoin",
    }
    
    def __init__(
        self,
        initial_capital: float = 10000.0,
        slippage_pct: float = DEFAULT_SLIPPAGE_PCT,
        fee_pct: float = DEFAULT_FEE_PCT,
        simulate_latency: bool = True,
        decision_delay_ms: float = DEFAULT_DECISION_DELAY_MS,
        execution_delay_ms: float = DEFAULT_EXECUTION_DELAY_MS,
    ):
        """Initialize paper trading engine with configuration."""
        self.session = PaperTradingSession(
            session_id=str(uuid.uuid4()),
            initial_capital=initial_capital,
            current_capital=initial_capital,
            peak_capital=initial_capital,
            config={
                "slippage_pct": slippage_pct,
                "fee_pct": fee_pct,
                "simulate_latency": simulate_latency,
                "decision_delay_ms": decision_delay_ms,
                "execution_delay_ms": execution_delay_ms,
            }
        )
        self._callbacks: dict[str, Callable] = {}
        self._running = False
        self._price_cache: dict[str, dict] = {}
        
    async def start_session(self) -> dict:
        """
        Start a new paper trading session.
        
        Returns session info including session_id for tracking.
        """
        if self.session.state == PaperTradingState.RUNNING:
            return {
                "success": False,
                "error": "Session already running",
                "session_id": self.session.session_id,
            }
        
        self.session = PaperTradingSession(
            session_id=str(uuid.uuid4()),
            start_time=datetime.utcnow(),
            initial_capital=self.session.initial_capital,
            current_capital=self.session.initial_capital,
            peak_capital=self.session.initial_capital,
            state=PaperTradingState.RUNNING,
            config=self.session.config,
        )
        self._running = True
        
        logger.info(
            "Paper trading session started: %s | Initial capital: $%.2f",
            self.session.session_id, self.session.initial_capital
        )
        
        return {
            "success": True,
            "session_id": self.session.session_id,
            "start_time": self.session.start_time.isoformat(),
            "initial_capital": self.session.initial_capital,
            "state": self.session.state.value,
        }
    
    async def stop_session(self) -> dict:
        """Stop the current paper trading session and calculate final metrics."""
        if self.session.state != PaperTradingState.RUNNING:
            return {
                "success": False,
                "error": "No active session to stop",
            }
        
        self.session.end_time = datetime.utcnow()
        self.session.state = PaperTradingState.STOPPED
        self._running = False
        
        # Calculate final metrics
        metrics = self._calculate_metrics()
        
        logger.info(
            "Paper trading session stopped: %s | Final PnL: $%.2f (%.2f%%)",
            self.session.session_id,
            self.session.total_pnl,
            self.session.total_pnl_pct,
        )
        
        return {
            "success": True,
            "session_id": self.session.session_id,
            "end_time": self.session.end_time.isoformat(),
            "duration_seconds": (self.session.end_time - self.session.start_time).total_seconds(),
            "metrics": metrics,
        }
    
    async def get_real_time_price(self, token_pair: str) -> dict:
        """
        Fetch REAL-TIME market price from CoinGecko.
        
        This is what makes paper trading "forward testing" —
        using live data, not historical.
        
        Returns:
            dict with price, timestamp, source, and any errors
        """
        gecko_id = self.SYMBOL_MAP.get(token_pair)
        if not gecko_id:
            return {
                "success": False,
                "error": f"Unsupported token pair: {token_pair}",
                "price": None,
            }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self.COINGECKO_API}/coins/markets",
                    params={
                        "vs_currency": "usd",
                        "ids": gecko_id,
                    },
                )
                resp.raise_for_status()
                items = resp.json()
                
                if not items:
                    raise ValueError(f"No data returned for {gecko_id}")
                
                coin = items[0]
                price = float(coin["current_price"])
                timestamp = datetime.utcnow()
                
                # Cache the price
                self._price_cache[token_pair] = {
                    "price": price,
                    "timestamp": timestamp,
                    "source": "coingecko",
                }
                
                return {
                    "success": True,
                    "price": price,
                    "volume_24h": float(coin.get("total_volume", 0)),
                    "price_change_24h": float(coin.get("price_change_percentage_24h", 0)),
                    "market_cap": float(coin.get("market_cap", 0)),
                    "timestamp": timestamp.isoformat(),
                    "source": "coingecko",
                }
                
        except Exception as exc:
            logger.error("Failed to fetch real-time price for %s: %s", token_pair, exc)
            return {
                "success": False,
                "error": str(exc),
                "price": None,
                "timestamp": datetime.utcnow().isoformat(),
            }
    
    async def submit_order(
        self,
        token_pair: str,
        chain: str,
        side: str,  # "buy" or "sell"
        amount: float,
        order_type: PaperOrderType = PaperOrderType.MARKET,
        price: Optional[float] = None,
        reasoning: str = "",
        confidence: float = 0.5,
    ) -> dict:
        """
        Submit a paper trading order.
        
        This simulates:
        1. AI agent decision time (configurable delay)
        2. Network latency to exchange
        3. Realistic slippage based on market conditions
        4. Trading fees
        
        Args:
            token_pair: Trading pair (e.g., "ETH/USDT")
            chain: Blockchain (e.g., "ethereum")
            side: "buy" or "sell"
            amount: USD value for buy, token amount for sell
            order_type: MARKET, LIMIT, STOP_LOSS, TAKE_PROFIT
            price: Limit price (for LIMIT orders)
            reasoning: Agent's reasoning for the trade
            confidence: Agent's confidence (0-1)
        
        Returns:
            Order result with fill status, simulated slippage, etc.
        """
        if self.session.state != PaperTradingState.RUNNING:
            return {
                "success": False,
                "error": "Session not running",
            }
        
        order_id = str(uuid.uuid4())
        decision_start = time.time()
        
        # Get real-time price
        price_data = await self.get_real_time_price(token_pair)
        if not price_data.get("success"):
            return {
                "success": False,
                "error": f"Failed to get price: {price_data.get('error')}",
                "order_id": order_id,
            }
        
        market_price = price_data["price"]
        
        # Simulate AI decision delay
        if self.session.config.get("simulate_latency", True):
            decision_delay = self.session.config.get("decision_delay_ms", 500) / 1000.0
            await asyncio.sleep(decision_delay)
        
        decision_time_ms = (time.time() - decision_start) * 1000
        
        # Calculate slippage based on order size and market conditions
        slippage_pct = self._calculate_slippage(token_pair, amount, market_price)
        slippage = market_price * slippage_pct
        
        # Simulate execution delay
        exec_start = time.time()
        if self.session.config.get("simulate_latency", True):
            exec_delay = self.session.config.get("execution_delay_ms", 200) / 1000.0
            await asyncio.sleep(exec_delay)
        exec_time_ms = (time.time() - exec_start) * 1000
        
        # Calculate fill price with slippage
        if side == "buy":
            fill_price = market_price + slippage  # Buy at higher price (slippage against you)
        else:
            fill_price = market_price - slippage  # Sell at lower price (slippage against you)
        
        # Calculate fee
        fee_pct = self.session.config.get("fee_pct", 0.001)
        fee = amount * fee_pct
        
        # Create and process the order
        order = PaperOrder(
            order_id=order_id,
            token_pair=token_pair,
            chain=chain,
            order_type=order_type,
            side=side,
            amount=amount,
            price=price,
            status="filled",
            filled_at=datetime.utcnow(),
            filled_price=fill_price,
            slippage=slippage,
            fee=fee,
            reasoning=reasoning,
        )
        
        self.session.orders.append(order)
        
        # Process the fill
        trade = await self._process_fill(order, confidence, decision_time_ms, exec_time_ms)
        
        if trade:
            self.session.trades.append(trade)
            
            # Update metrics
            self._update_metrics(trade)
            
            logger.info(
                "Paper trade executed: %s %s %.4f @ $%.2f | Slippage: %.4f%% | Fee: $%.4f",
                side.upper(), token_pair, amount, fill_price,
                slippage_pct * 100, fee
            )
        
        return {
            "success": True,
            "order_id": order_id,
            "status": "filled",
            "side": side,
            "token_pair": token_pair,
            "amount": amount,
            "market_price": market_price,
            "fill_price": fill_price,
            "slippage_pct": slippage_pct * 100,
            "slippage_usd": slippage,
            "fee_usd": fee,
            "decision_time_ms": decision_time_ms,
            "execution_delay_ms": exec_time_ms,
            "timestamp": order.filled_at.isoformat() if order.filled_at else None,
        }
    
    async def _process_fill(
        self,
        order: PaperOrder,
        confidence: float,
        decision_time_ms: float,
        exec_time_ms: float,
    ) -> Optional[PaperTradeRecord]:
        """Process a filled order and update positions."""
        if order.side == "buy":
            # Buy: amount is USD, convert to token amount
            if not order.filled_price or order.filled_price <= 0:
                return None
            token_amount = (order.amount - order.fee) / order.filled_price
            
            # Check if we already have a position
            existing = self.session.positions.get(order.token_pair)
            if existing:
                # Average up/down
                total_tokens = existing.amount + token_amount
                avg_price = (
                    (existing.amount * existing.entry_price + token_amount * order.filled_price)
                    / total_tokens
                )
                existing.amount = total_tokens
                existing.entry_price = avg_price
            else:
                # New position
                self.session.positions[order.token_pair] = PaperPosition(
                    token_pair=order.token_pair,
                    chain=order.chain,
                    amount=token_amount,
                    entry_price=order.filled_price,
                    entry_time=order.filled_at or datetime.utcnow(),
                )
            
            # Deduct from capital
            self.session.current_capital -= (order.amount + order.slippage)
            
        else:  # sell
            # Sell: amount is token amount
            existing = self.session.positions.get(order.token_pair)
            if not existing or existing.amount <= 0:
                logger.warning("Cannot sell: no position in %s", order.token_pair)
                return None
            
            # Calculate PnL
            sell_amount = min(order.amount, existing.amount)
            gross_proceeds = sell_amount * (order.filled_price or 0)
            net_proceeds = gross_proceeds - order.fee - order.slippage
            
            entry_value = sell_amount * existing.entry_price
            pnl = net_proceeds - entry_value
            pnl_pct = (pnl / entry_value * 100) if entry_value > 0 else 0
            
            # Update position
            existing.amount -= sell_amount
            if existing.amount <= 0.0001:  # Close empty positions
                del self.session.positions[order.token_pair]
            
            # Add to capital
            self.session.current_capital += net_proceeds
            
            # Update session totals
            self.session.total_pnl += pnl
            if pnl > 0:
                self.session.win_count += 1
            else:
                self.session.loss_count += 1
            
            # Create trade record
            return PaperTradeRecord(
                trade_id=str(uuid.uuid4()),
                token_pair=order.token_pair,
                chain=order.chain,
                side=order.side,
                amount=sell_amount,
                price=order.filled_price or 0,
                timestamp=order.filled_at or datetime.utcnow(),
                reasoning=order.reasoning,
                confidence=confidence,
                slippage=order.slippage,
                fee=order.fee,
                pnl=pnl,
                pnl_pct=pnl_pct,
                agent_decision_time_ms=decision_time_ms,
                execution_delay_ms=exec_time_ms,
            )
        
        return None
    
    def _calculate_slippage(
        self,
        token_pair: str,
        amount: float,
        market_price: float,
    ) -> float:
        """
        Calculate realistic slippage based on order size and market conditions.
        
        Larger orders relative to market liquidity = more slippage.
        This helps paper trading reveal real execution challenges.
        """
        base_slippage = self.session.config.get("slippage_pct", 0.001)
        
        # Scale slippage based on order size (larger orders = more slippage)
        # This is a simplified model - real slippage depends on order book depth
        size_factor = 1.0
        if amount > 10000:
            size_factor = 1.5  # Large orders get 50% more slippage
        elif amount > 50000:
            size_factor = 2.0  # Very large orders get 2x slippage
        
        # Add randomness to simulate market volatility
        import random
        random_factor = random.uniform(0.8, 1.2)
        
        return base_slippage * size_factor * random_factor
    
    def _update_metrics(self, trade: PaperTradeRecord) -> None:
        """Update session metrics after each trade."""
        # Update total PnL
        self.session.total_pnl_pct = (
            (self.session.current_capital - self.session.initial_capital)
            / self.session.initial_capital * 100
        )
        
        # Track drawdown
        self.session.peak_capital = max(self.session.peak_capital, self.session.current_capital)
        if self.session.peak_capital > 0:
            drawdown = (self.session.peak_capital - self.session.current_capital) / self.session.peak_capital
            self.session.max_drawdown = self.session.peak_capital - self.session.current_capital
            self.session.max_drawdown_pct = drawdown * 100
    
    def _calculate_metrics(self) -> dict:
        """Calculate comprehensive performance metrics."""
        total_trades = self.session.win_count + self.session.loss_count
        win_rate = (self.session.win_count / total_trades * 100) if total_trades > 0 else 0
        
        # Calculate average latency
        avg_decision_time = 0.0
        avg_exec_time = 0.0
        if self.session.trades:
            decision_times = [t.agent_decision_time_ms for t in self.session.trades]
            exec_times = [t.execution_delay_ms for t in self.session.trades]
            avg_decision_time = sum(decision_times) / len(decision_times)
            avg_exec_time = sum(exec_times) / len(exec_times)
        
        return {
            "session_id": self.session.session_id,
            "initial_capital": self.session.initial_capital,
            "final_capital": self.session.current_capital,
            "total_pnl_usd": self.session.total_pnl,
            "total_pnl_pct": self.session.total_pnl_pct,
            "total_trades": total_trades,
            "winning_trades": self.session.win_count,
            "losing_trades": self.session.loss_count,
            "win_rate_pct": win_rate,
            "max_drawdown_usd": self.session.max_drawdown,
            "max_drawdown_pct": self.session.max_drawdown_pct,
            "avg_decision_time_ms": avg_decision_time,
            "avg_execution_delay_ms": avg_exec_time,
            "duration_minutes": (
                (self.session.end_time or datetime.utcnow()) - self.session.start_time
            ).total_seconds() / 60,
        }
    
    async def get_session_status(self) -> dict:
        """Get current session status and metrics."""
        return {
            "session_id": self.session.session_id,
            "state": self.session.state.value,
            "start_time": self.session.start_time.isoformat(),
            "current_capital": self.session.current_capital,
            "positions": {
                pair: {
                    "token_pair": pos.token_pair,
                    "amount": pos.amount,
                    "entry_price": pos.entry_price,
                    "current_value": pos.current_value,
                    "unrealized_pnl": pos.unrealized_pnl,
                }
                for pair, pos in self.session.positions.items()
            },
            "metrics": self._calculate_metrics(),
        }
    
    async def update_position_values(self) -> dict:
        """
        Update all position values with current real-time prices.
        
        This should be called periodically to track unrealized PnL.
        """
        for pair, position in self.session.positions.items():
            price_data = await self.get_real_time_price(pair)
            if price_data.get("success"):
                position.current_value = position.amount * price_data["price"]
                position.unrealized_pnl = position.current_value - (position.amount * position.entry_price)
                position.unrealized_pnl_pct = (
                    position.unrealized_pnl / (position.amount * position.entry_price) * 100
                    if position.entry_price > 0 else 0
                )
        
        return {
            "updated": True,
            "positions": {
                pair: {
                    "token_pair": pos.token_pair,
                    "current_value": pos.current_value,
                    "unrealized_pnl": pos.unrealized_pnl,
                    "unrealized_pnl_pct": pos.unrealized_pnl_pct,
                }
                for pair, pos in self.session.positions.items()
            },
        }


# Singleton instance for easy access
_paper_trading_engine: Optional[PaperTradingEngine] = None


def get_paper_trading_engine(initial_capital: float = 10000.0) -> PaperTradingEngine:
    """Get or create the paper trading engine singleton."""
    global _paper_trading_engine
    if _paper_trading_engine is None:
        _paper_trading_engine = PaperTradingEngine(initial_capital=initial_capital)
    return _paper_trading_engine