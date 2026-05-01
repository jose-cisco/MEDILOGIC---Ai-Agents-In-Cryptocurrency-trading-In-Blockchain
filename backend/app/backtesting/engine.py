import json
import logging
import numpy as np
import pandas as pd
from datetime import datetime
from dataclasses import dataclass, field
from app.core.llm import get_backtest_llm
from langchain_core.messages import SystemMessage, HumanMessage
from app.rag.knowledge_base import MarketKnowledgeBase

logger = logging.getLogger(__name__)

BACKTEST_PROMPT = """You are an expert crypto trading strategy backtester AI (Ollama backtesting engine).
Given historical market data and relevant RAG knowledge, simulate trading decisions as if you were operating in real-time.

For each data point, return a JSON array of trade decisions:
[{{"date": "YYYY-MM-DD", "action": "buy|sell|hold", "amount_usd": float, "reasoning": "string", "confidence": float}}]

Strategy: {strategy}
Token Pair: {token_pair}

Rules:
- Start with initial capital of ${initial_capital}
- Max position size: 20% of current portfolio value
- Consider transaction fees of 0.1%
- Use technical analysis indicators (RSI, MACD, Moving Averages) visible in the data
- Apply zero-shot learning to detect unusual patterns
- Cross-reference with provided RAG market knowledge for historical patterns
- Record every buy/sell/hold decision with reasoning

Retrieved Market Knowledge:
{rag_context}

Historical Data:
{market_data}

Return ONLY the JSON array, no other text."""


@dataclass
class TradeRecord:
    date: str
    action: str
    amount_usd: float
    price: float
    reasoning: str
    confidence: float
    portfolio_value: float = 0.0


@dataclass
@dataclass
class BacktestMetrics:
    initial_capital: float
    final_capital: float
    total_return_pct: float
    sharpe_ratio: float
    max_drawdown_pct: float
    win_rate: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_trade_return_pct: float
    profit_factor: float
    trades: list = field(default_factory=list)
    rag_metadata: dict = field(default_factory=dict)

class BacktestEngine:
    TRADING_FEE = 0.001
    MAX_POSITION_PCT = 0.20

    def fetch_historical_data(
        self, token_pair: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        try:
            import ccxt

            exchange = ccxt.binance({"enableRateLimit": True})
            symbol = token_pair
            if "/" not in token_pair:
                symbol = f"{token_pair[:3]}/{token_pair[3:]}"
            since = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000)
            limit = 1000
            ohlcv = exchange.fetch_ohlcv(
                symbol, timeframe="1d", since=since, limit=limit
            )
            df = pd.DataFrame(
                ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"]
            )
            df["date"] = pd.to_datetime(df["timestamp"], unit="ms").dt.strftime(
                "%Y-%m-%d"
            )
            end = datetime.strptime(end_date, "%Y-%m-%d")
            df = df[pd.to_datetime(df["date"]) <= end]
            for w in [7, 14, 30]:
                df[f"sma_{w}"] = df["close"].rolling(window=w).mean()
            df["rsi"] = self._compute_rsi(df["close"], 14)
            df["macd"] = self._compute_macd(df["close"])
            df.dropna(inplace=True)
            return df
        except Exception:
            # Single seed — removed duplicate (was bug: seed set twice)
            np.random.seed(42)
            n_days = (
                datetime.strptime(end_date, "%Y-%m-%d")
                - datetime.strptime(start_date, "%Y-%m-%d")
            ).days
            dates = pd.date_range(start=start_date, periods=n_days, freq="D")
            base_price = 2000.0 if "ETH" in token_pair else 150.0
            returns = np.random.normal(0.001, 0.03, n_days)
            prices = base_price * np.cumprod(1 + returns)
            df = pd.DataFrame({"date": dates.strftime("%Y-%m-%d"), "close": prices})
            df["open"] = df["close"] * (1 + np.random.normal(0, 0.005, n_days))
            df["high"] = df[["open", "close"]].max(axis=1) * (
                1 + np.abs(np.random.normal(0, 0.01, n_days))
            )
            df["low"] = df[["open", "close"]].min(axis=1) * (
                1 - np.abs(np.random.normal(0, 0.01, n_days))
            )
            df["volume"] = np.random.uniform(1e6, 5e7, n_days)
            for w in [7, 14, 30]:
                df[f"sma_{w}"] = df["close"].rolling(window=w).mean()
            df["rsi"] = self._compute_rsi(df["close"], 14)
            df["macd"] = self._compute_macd(df["close"])
            df.dropna(inplace=True)
            return df

    @staticmethod
    def _compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
        delta = series.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        rs = avg_gain / avg_loss.replace(0, 1e-10)
        return 100 - (100 / (1 + rs))

    @staticmethod
    def _compute_macd(series: pd.Series) -> pd.Series:
        ema12 = series.ewm(span=12, adjust=False).mean()
        ema26 = series.ewm(span=26, adjust=False).mean()
        return ema12 - ema26

    def _get_rag_context_for_backtest(self, token_pair: str, strategy: str) -> tuple[str, dict]:
        """Fetch hybrid RAG context for backtesting.
        
        Returns (context_str, metadata_dict) — same format as trading graph.
        """
        try:
            kb = MarketKnowledgeBase()
            if kb.collection.count() == 0:
                return "", {}
            context_data = kb.get_enhanced_context(
                f"Backtest strategy: {strategy} for {token_pair} historical patterns",
                n_results=10,
            )
            summary = context_data.get("summary", "")
            metadata = {
                "sources": context_data.get("sources", []),
                "result_count": context_data.get("result_count", 0),
                "rrf_scores": context_data.get("rrf_scores", []),
                "semantic_scores": context_data.get("semantic_scores", []),
                "lexical_scores": context_data.get("lexical_scores", []),
                "summary": summary,
            }
            if summary:
                logger.debug(
                    "Backtest RAG: %d results for %s",
                    context_data.get("result_count", 0), token_pair
                )
            return summary, metadata
        except Exception as exc:
            logger.warning("Backtest RAG fetch failed: %s", exc)
            return "", {}

    def generate_llm_decisions(
        self,
        strategy: str,
        token_pair: str,
        start_date: str,
        end_date: str,
        initial_capital: float,
    ) -> list:
        df = self.fetch_historical_data(token_pair, start_date, end_date)
        market_data_str = df[
            [
                "date",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "rsi",
                "macd",
                "sma_7",
                "sma_14",
                "sma_30",
            ]
        ].to_string(index=False)

        rag_context, rag_metadata = self._get_rag_context_for_backtest(token_pair, strategy)

        # Use dedicated backtest LLM route with optimal tuning
        llm = get_backtest_llm()
        prompt = BACKTEST_PROMPT.format(
            strategy=strategy,
            token_pair=token_pair,
            initial_capital=initial_capital,
            market_data=market_data_str,
            rag_context=rag_context
            if rag_context
            else "No additional knowledge available.",
        )
        response = llm.invoke(
            [
                SystemMessage(
                    content="You are a crypto backtesting engine (Ollama). Return valid JSON only."
                ),
                HumanMessage(content=prompt),
            ]
        )
        try:
            content = response.content
            json_start = content.find("[")
            json_end = content.rfind("]") + 1
            if json_start >= 0 and json_end > json_start:
                decisions = json.loads(content[json_start:json_end])
            else:
                decisions = json.loads(content)
        except json.JSONDecodeError:
            decisions = self._generate_default_decisions(df)

        return decisions, df, rag_metadata

    def _generate_default_decisions(self, df: pd.DataFrame) -> list:
        decisions = []
        for _, row in df.iterrows():
            rsi = row.get("rsi", 50)
            macd = row.get("macd", 0)
            sma_7 = row.get("sma_7", row["close"])
            sma_14 = row.get("sma_14", row["close"])
            if rsi < 30 and macd > 0 and sma_7 > sma_14:
                action = "buy"
                confidence = 0.7
            elif rsi > 70 and macd < 0 and sma_7 < sma_14:
                action = "sell"
                confidence = 0.7
            else:
                action = "hold"
                confidence = 0.5
            decisions.append(
                {
                    "date": row["date"],
                    "action": action,
                    "amount_usd": 100 if action != "hold" else 0,
                    "reasoning": f"RSI={rsi:.1f}, MACD={macd:.2f}",
                    "confidence": confidence,
                }
            )
        return decisions

    def run_backtest(
        self,
        strategy: str,
        token_pair: str,
        start_date: str,
        end_date: str,
        initial_capital: float,
        use_llm: bool = True,
    ) -> BacktestMetrics:
        rag_metadata = {}
        if use_llm:
            decisions, df, rag_metadata = self.generate_llm_decisions(
                strategy, token_pair, start_date, end_date, initial_capital
            )
        else:
            df = self.fetch_historical_data(token_pair, start_date, end_date)
            decisions = self._generate_default_decisions(df)
            # Fetch RAG context for rules-based backtest too
            _, rag_metadata = self._get_rag_context_for_backtest(token_pair, strategy)

        price_map = {}
        for _, row in df.iterrows():
            price_map[row["date"]] = row["close"]

        capital = initial_capital
        position = 0.0
        position_value = 0.0
        trades: list[TradeRecord] = []
        capital_history = [initial_capital]
        peak_capital = initial_capital
        max_drawdown = 0.0
        winning = 0
        losing = 0
        entry_price = 0.0

        for d in decisions:
            date = d.get("date", "")
            action = d.get("action", "hold")
            amount_usd = d.get("amount_usd", 0)
            reasoning = d.get("reasoning", "")
            confidence = d.get("confidence", 0.5)

            if date not in price_map:
                continue
            price = price_map[date]
            max_amount = capital * self.MAX_POSITION_PCT
            amount_usd = min(amount_usd, max_amount)
            amount_usd = (
                min(amount_usd, capital)
                if action == "buy"
                else min(amount_usd, position * price)
                if position > 0
                else 0
            )

            if action == "buy" and amount_usd > 0:
                fee = amount_usd * self.TRADING_FEE
                net_amount = amount_usd - fee
                shares = net_amount / price
                position += shares
                capital -= amount_usd
                entry_price = price
                position_value = position * price
                trades.append(
                    TradeRecord(
                        date=date,
                        action="buy",
                        amount_usd=amount_usd,
                        price=price,
                        reasoning=reasoning,
                        confidence=confidence,
                        portfolio_value=capital + position_value,
                    )
                )

            elif action == "sell" and position > 0:
                shares_to_sell = min(amount_usd / price, position) if price > 0 else 0
                gross = shares_to_sell * price
                fee = gross * self.TRADING_FEE
                net_proceeds = gross - fee
                capital += net_proceeds
                if entry_price > 0:
                    if price > entry_price:
                        winning += 1
                    else:
                        losing += 1
                position -= shares_to_sell
                position_value = position * price
                trades.append(
                    TradeRecord(
                        date=date,
                        action="sell",
                        amount_usd=net_proceeds,
                        price=price,
                        reasoning=reasoning,
                        confidence=confidence,
                        portfolio_value=capital + position_value,
                    )
                )

            else:
                position_value = position * price
                trades.append(
                    TradeRecord(
                        date=date,
                        action="hold",
                        amount_usd=0,
                        price=price,
                        reasoning=reasoning,
                        confidence=confidence,
                        portfolio_value=capital + position_value,
                    )
                )

            current_value = capital + position_value
            capital_history.append(current_value)
            peak_capital = max(peak_capital, current_value)
            drawdown = (
                (peak_capital - current_value) / peak_capital if peak_capital > 0 else 0
            )
            max_drawdown = max(max_drawdown, drawdown)

        final_value = capital + position_value

        total_return = (
            (final_value - initial_capital) / initial_capital * 100
            if initial_capital > 0
            else 0
        )
        daily_returns = pd.Series(capital_history).pct_change().dropna()
        sharpe = (
            (daily_returns.mean() / daily_returns.std() * np.sqrt(252))
            if len(daily_returns) > 1 and daily_returns.std() > 0
            else 0
        )
        total_trades = sum(1 for t in trades if t.action in ("buy", "sell"))
        win_rate = (winning / total_trades * 100) if total_trades > 0 else 0
        avg_trade_return = total_return / total_trades if total_trades > 0 else 0
        gross_profit = sum(
            t.amount_usd for t in trades if t.action == "sell" and t.price > 0
        )
        gross_loss = sum(
            t.amount_usd for t in trades if t.action == "sell" and t.price <= 0
        )
        profit_factor = (
            (gross_profit / gross_loss)
            if gross_loss > 0
            else float("inf")
            if gross_profit > 0
            else 0
        )

        return BacktestMetrics(
            initial_capital=initial_capital,
            final_capital=round(final_value, 2),
            total_return_pct=round(total_return, 2),
            sharpe_ratio=round(sharpe, 2),
            max_drawdown_pct=round(max_drawdown * 100, 2),
            win_rate=round(win_rate, 2),
            total_trades=total_trades,
            winning_trades=winning,
            losing_trades=losing,
            avg_trade_return_pct=round(avg_trade_return, 2),
            profit_factor=round(profit_factor, 2)
            if profit_factor != float("inf")
            else 999.99,
            trades=[
                {
                    "date": t.date,
                    "action": t.action,
                    "amount_usd": round(t.amount_usd, 2),
                    "price": round(t.price, 2),
                    "reasoning": t.reasoning,
                    "confidence": t.confidence,
                    "portfolio_value": round(t.portfolio_value, 2),
                }
                for t in trades
            ],
            rag_metadata=rag_metadata,
        )
