"""
Backtest API
============
Backtesting endpoints for strategy simulation.

x402 PAYMENT EXEMPTION:
  Backtesting routes are EXEMPT from x402 payment requirements.
  Backtesting is a simulation of cryptocurrency market behavior — not real
  capital deployment. Charging for backtest runs would:
  1. Discourage thorough testing before live trading
  2. Distort strategy evaluation with per-run costs
  3. Contradict the safety-first principle of "simulate first, trade later"

  The x402 middleware (auth.py) automatically exempts all /api/v1/backtest/*
  routes from payment verification. No X-Payment header is needed here.
"""
from fastapi import APIRouter, HTTPException
from app.schemas.models import BacktestRequest, BacktestResult
from app.core.llm import (
    is_backtest_mode,
    custom_llm_provider,
    custom_llm_api_key,
    custom_llm_base_url,
    custom_llm_model,
)

router = APIRouter()


class LazyBacktestEngine:
    """
    Delay importing heavy scientific stack until actually needed.
    This prevents app import-time crashes if local NumPy wheels are broken.
    """

    def __init__(self):
        self._engine = None

    def _get_engine(self):
        if self._engine is None:
            from app.backtesting.engine_safe import BacktestEngine

            self._engine = BacktestEngine()
        return self._engine

    def run_backtest(self, *args, **kwargs):
        return self._get_engine().run_backtest(*args, **kwargs)


engine = LazyBacktestEngine()


@router.post("/run", response_model=BacktestResult)
async def run_backtest(request: BacktestRequest):
    # Enforce zero-cost mode for this execution context
    is_backtest_mode.set(True)
    
    # Set custom LLM context for backtest if provided
    custom_llm_provider.set(request.custom_llm_provider)
    custom_llm_api_key.set(request.custom_llm_api_key)
    custom_llm_base_url.set(request.custom_llm_base_url)
    custom_llm_model.set(request.custom_llm_model)

    try:
        metrics = engine.run_backtest(
            strategy=request.strategy,
            token_pair=request.token_pair,
            start_date=request.start_date,
            end_date=request.end_date,
            initial_capital=request.initial_capital,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backtest error: {str(e)}")

    return BacktestResult(
        strategy=request.strategy,
        token_pair=request.token_pair,
        start_date=request.start_date,
        end_date=request.end_date,
        initial_capital=metrics.initial_capital,
        final_capital=metrics.final_capital,
        total_return_pct=metrics.total_return_pct,
        sharpe_ratio=metrics.sharpe_ratio,
        max_drawdown_pct=metrics.max_drawdown_pct,
        win_rate=metrics.win_rate,
        total_trades=metrics.total_trades,
        winning_trades=metrics.winning_trades,
        losing_trades=metrics.losing_trades,
        avg_trade_return_pct=metrics.avg_trade_return_pct,
        profit_factor=metrics.profit_factor,
        data_source=getattr(metrics, "data_source", "synthetic"),
        trades=metrics.trades,
        rag_metadata=getattr(metrics, "rag_metadata", None) or None,
        x402_metadata={
            "payment_required": False,
            "exempt": True,
            "reason": "Backtesting is a simulation of crypto market behavior — not real capital deployment. "
                     "x402 payments are not required for backtest runs.",
        },
    )


@router.post("/run-rules")
async def run_rules_backtest(
    token_pair: str = "ETH/USDT",
    start_date: str = ...,
    end_date: str = ...,
    initial_capital: float = 10000.0,
):
    # Enforce zero-cost mode for this execution context
    is_backtest_mode.set(True)
    metrics = engine.run_backtest(
        strategy="RSI + MACD + SMA crossover rules-based",
        token_pair=token_pair,
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital,
        use_llm=False,
    )
    return BacktestResult(
        strategy="rules-based",
        token_pair=token_pair,
        start_date=start_date,
        end_date=end_date,
        initial_capital=metrics.initial_capital,
        final_capital=metrics.final_capital,
        total_return_pct=metrics.total_return_pct,
        sharpe_ratio=metrics.sharpe_ratio,
        max_drawdown_pct=metrics.max_drawdown_pct,
        win_rate=metrics.win_rate,
        total_trades=metrics.total_trades,
        winning_trades=metrics.winning_trades,
        losing_trades=metrics.losing_trades,
        avg_trade_return_pct=metrics.avg_trade_return_pct,
        profit_factor=metrics.profit_factor,
        data_source=getattr(metrics, "data_source", "synthetic"),
        trades=metrics.trades,
        rag_metadata=getattr(metrics, "rag_metadata", None) or None,
        x402_metadata={
            "payment_required": False,
            "exempt": True,
            "reason": "Backtesting is a simulation of crypto market behavior — not real capital deployment. "
                     "x402 payments are not required for backtest runs.",
        },
    )


@router.get("/strategies")
async def list_strategies():
    return {
        "strategies": [
            {
                "id": "momentum",
                "name": "Momentum Trading",
                "description": "Follow market momentum using RSI + MACD signals with trend confirmation",
            },
            {
                "id": "mean_reversion",
                "name": "Mean Reversion",
                "description": "Buy oversold, sell overbought based on Bollinger Bands and RSI extremes",
            },
            {
                "id": "breakout",
                "name": "Breakout Strategy",
                "description": "Enter on volume-backed breakouts above resistance levels",
            },
            {
                "id": "grid",
                "name": "Grid Trading",
                "description": "Place buy/sell orders at regular intervals to profit from volatility",
            },
            {
                "id": "dca",
                "name": "Dollar-Cost Averaging",
                "description": "Invest fixed amounts at regular intervals regardless of price",
            },
        ]
    }
