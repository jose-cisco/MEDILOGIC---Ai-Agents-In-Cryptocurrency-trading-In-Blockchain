import json
import logging
import math
import random
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from app.core.llm import get_backtest_llm
from langchain_core.messages import SystemMessage, HumanMessage
from app.rag.knowledge_base import MarketKnowledgeBase
from app.core.config import get_settings

logger = logging.getLogger(__name__)

BACKTEST_PROMPT = """You are an expert crypto trading strategy backtester AI.
Given historical market data and relevant RAG knowledge, simulate trading decisions.

Return JSON array only:
[{{"date":"YYYY-MM-DD","action":"buy|sell|hold","amount_usd":float,"reasoning":"string","confidence":float}}]

Strategy: {strategy}
Token Pair: {token_pair}
Initial Capital: {initial_capital}

Retrieved Market Knowledge:
{rag_context}

Historical Data:
{market_data}
"""


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
    data_source: str = "synthetic"
    trades: list[dict] = field(default_factory=list)
    rag_metadata: dict = field(default_factory=dict)

class BacktestEngine:
    TRADING_FEE = 0.001
    MAX_POSITION_PCT = 0.20

    def _load_dataset_rows(self, token_pair: str, start_date: str, end_date: str) -> list[dict]:
        settings = get_settings()
        path = Path(settings.BACKTEST_DATASET_PATH)
        if not path.exists():
            return []
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
        rows = []
        try:
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    obj = json.loads(line)
                    if obj.get("token_pair") and obj.get("token_pair") != token_pair:
                        continue
                    d = datetime.strptime(obj["date"], "%Y-%m-%d").date()
                    if start <= d <= end:
                        rows.append(
                            {
                                "date": obj["date"],
                                "open": float(obj["open"]),
                                "high": float(obj["high"]),
                                "low": float(obj["low"]),
                                "close": float(obj["close"]),
                                "volume": float(obj.get("volume", 0.0)),
                            }
                        )
        except Exception as exc:
            logger.warning("Failed loading backtest dataset file: %s", exc)
            return []
        self._enrich_indicators(rows)
        return [r for r in rows if r["sma_30"] is not None and r["rsi"] is not None]

    def _fetch_ccxt_rows(self, token_pair: str, start_date: str, end_date: str) -> list[dict]:
        try:
            import ccxt
            exchange = ccxt.binance({"enableRateLimit": True})
            since = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000)
            ohlcv = exchange.fetch_ohlcv(token_pair, timeframe="1d", since=since, limit=2000)
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
            rows = []
            for ts, o, h, l, c, v in ohlcv:
                d = datetime.utcfromtimestamp(ts / 1000).date()
                if d > end:
                    continue
                rows.append(
                    {
                        "date": d.strftime("%Y-%m-%d"),
                        "open": float(o),
                        "high": float(h),
                        "low": float(l),
                        "close": float(c),
                        "volume": float(v),
                    }
                )
            self._enrich_indicators(rows)
            return [r for r in rows if r["sma_30"] is not None and r["rsi"] is not None]
        except Exception as exc:
            logger.info("ccxt historical fetch unavailable; using synthetic fallback: %s", exc)
            return []

    def fetch_historical_data(self, token_pair: str, start_date: str, end_date: str) -> tuple[list[dict], str]:
        dataset_rows = self._load_dataset_rows(token_pair, start_date, end_date)
        if dataset_rows:
            return dataset_rows, "dataset"

        ccxt_rows = self._fetch_ccxt_rows(token_pair, start_date, end_date)
        if ccxt_rows:
            return ccxt_rows, "ccxt"

        # deterministic synthetic fallback
        random.seed(42)
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        n_days = max((end - start).days, 35)
        base_price = 2000.0 if "ETH" in token_pair else 150.0
        rows = []
        price = base_price
        closes = []
        for i in range(n_days):
            d = start + timedelta(days=i)
            daily_ret = random.gauss(0.001, 0.03)
            price = max(1.0, price * (1 + daily_ret))
            open_p = max(1.0, price * (1 + random.gauss(0, 0.005)))
            high = max(open_p, price) * (1 + abs(random.gauss(0, 0.01)))
            low = min(open_p, price) * (1 - abs(random.gauss(0, 0.01)))
            vol = random.uniform(1e6, 5e7)
            closes.append(price)
            rows.append(
                {
                    "date": d.strftime("%Y-%m-%d"),
                    "open": open_p,
                    "high": high,
                    "low": low,
                    "close": price,
                    "volume": vol,
                }
            )

        self._enrich_indicators(rows)
        return [r for r in rows if r["sma_30"] is not None and r["rsi"] is not None], "synthetic"

    @staticmethod
    def _mean(vals: list[float]) -> float:
        return sum(vals) / len(vals) if vals else 0.0

    def _rolling_mean(self, arr: list[float], window: int) -> list[float]:
        out = []
        for i in range(len(arr)):
            if i + 1 < window:
                out.append(None)
            else:
                out.append(self._mean(arr[i + 1 - window : i + 1]))
        return out

    def _compute_rsi(self, closes: list[float], period: int = 14) -> list[float]:
        rsi = [None] * len(closes)
        for i in range(period, len(closes)):
            gains = []
            losses = []
            for j in range(i - period + 1, i + 1):
                delta = closes[j] - closes[j - 1]
                gains.append(max(0.0, delta))
                losses.append(max(0.0, -delta))
            avg_gain = self._mean(gains)
            avg_loss = self._mean(losses) if self._mean(losses) > 0 else 1e-10
            rs = avg_gain / avg_loss
            rsi[i] = 100 - (100 / (1 + rs))
        return rsi

    def _compute_ema(self, arr: list[float], span: int) -> list[float]:
        out = []
        alpha = 2 / (span + 1)
        ema = arr[0] if arr else 0.0
        for v in arr:
            ema = alpha * v + (1 - alpha) * ema
            out.append(ema)
        return out

    def _enrich_indicators(self, rows: list[dict]) -> None:
        closes = [r["close"] for r in rows]
        sma7 = self._rolling_mean(closes, 7)
        sma14 = self._rolling_mean(closes, 14)
        sma30 = self._rolling_mean(closes, 30)
        rsi = self._compute_rsi(closes, 14)
        ema12 = self._compute_ema(closes, 12)
        ema26 = self._compute_ema(closes, 26)
        macd = [a - b for a, b in zip(ema12, ema26)]
        for i, r in enumerate(rows):
            r["sma_7"] = sma7[i]
            r["sma_14"] = sma14[i]
            r["sma_30"] = sma30[i]
            r["rsi"] = rsi[i]
            r["macd"] = macd[i]

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
            metadata = {
                "sources": context_data.get("sources", []),
                "result_count": context_data.get("result_count", 0),
                "rrf_scores": context_data.get("rrf_scores", []),
                "semantic_scores": context_data.get("semantic_scores", []),
                "lexical_scores": context_data.get("lexical_scores", []),
                "summary": context_data.get("summary", ""),
            }
            return context_data.get("summary", ""), metadata
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
    ) -> tuple[list, list[dict], str]:
        rows, data_source = self.fetch_historical_data(token_pair, start_date, end_date)
        preview = rows[-120:]
        market_data_str = "\n".join(
            f"{r['date']} O:{r['open']:.2f} H:{r['high']:.2f} L:{r['low']:.2f} C:{r['close']:.2f} "
            f"RSI:{(r['rsi'] or 50):.1f} MACD:{r['macd']:.3f} SMA7:{(r['sma_7'] or 0):.2f} "
            f"SMA14:{(r['sma_14'] or 0):.2f} SMA30:{(r['sma_30'] or 0):.2f}"
            for r in preview
        )
        rag_context, rag_metadata = self._get_rag_context_for_backtest(token_pair, strategy)
        llm = get_backtest_llm()
        prompt = BACKTEST_PROMPT.format(
            strategy=strategy,
            token_pair=token_pair,
            initial_capital=initial_capital,
            market_data=market_data_str,
            rag_context=rag_context if rag_context else "No additional knowledge available.",
        )
        response = llm.invoke(
            [
                SystemMessage(content="You are a crypto backtesting engine. Return valid JSON only."),
                HumanMessage(content=prompt),
            ]
        )
        try:
            content = response.content
            json_start = content.find("[")
            json_end = content.rfind("]") + 1
            decisions = json.loads(content[json_start:json_end]) if json_start >= 0 else json.loads(content)
        except Exception:
            decisions = self._generate_default_decisions(rows)
        return decisions, rows, data_source, rag_metadata

    def _generate_default_decisions(self, rows: list[dict]) -> list:
        decisions = []
        for row in rows:
            rsi = row.get("rsi") if row.get("rsi") is not None else 50
            macd = row.get("macd", 0)
            sma_7 = row.get("sma_7") if row.get("sma_7") is not None else row["close"]
            sma_14 = row.get("sma_14") if row.get("sma_14") is not None else row["close"]
            if rsi < 30 and macd > 0 and sma_7 > sma_14:
                action, confidence = "buy", 0.7
            elif rsi > 70 and macd < 0 and sma_7 < sma_14:
                action, confidence = "sell", 0.7
            else:
                action, confidence = "hold", 0.5
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
            decisions, rows, data_source, rag_metadata = self.generate_llm_decisions(
                strategy, token_pair, start_date, end_date, initial_capital
            )
        else:
            rows, data_source = self.fetch_historical_data(token_pair, start_date, end_date)
            decisions = self._generate_default_decisions(rows)
            # Fetch RAG context for rules-based backtest too
            _, rag_metadata = self._get_rag_context_for_backtest(token_pair, strategy)

        price_map = {r["date"]: r["close"] for r in rows}
        capital = initial_capital
        position = 0.0
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
            amount_usd = float(d.get("amount_usd", 0))
            reasoning = d.get("reasoning", "")
            confidence = float(d.get("confidence", 0.5))
            if date not in price_map:
                continue
            price = price_map[date]
            max_amount = capital * self.MAX_POSITION_PCT
            amount_usd = min(amount_usd, max_amount)
            if action == "buy":
                amount_usd = min(amount_usd, capital)
            elif action == "sell":
                amount_usd = min(amount_usd, position * price) if position > 0 else 0
            else:
                amount_usd = 0

            if action == "buy" and amount_usd > 0:
                fee = amount_usd * self.TRADING_FEE
                shares = (amount_usd - fee) / price
                position += shares
                capital -= amount_usd
                entry_price = price
            elif action == "sell" and position > 0:
                shares_to_sell = min(amount_usd / price, position) if price > 0 else 0
                gross = shares_to_sell * price
                net = gross - gross * self.TRADING_FEE
                capital += net
                if entry_price > 0:
                    if price > entry_price:
                        winning += 1
                    else:
                        losing += 1
                position -= shares_to_sell

            portfolio_value = capital + position * price
            trades.append(
                TradeRecord(
                    date=date,
                    action=action,
                    amount_usd=amount_usd if action != "sell" else min(amount_usd, portfolio_value),
                    price=price,
                    reasoning=reasoning,
                    confidence=confidence,
                    portfolio_value=portfolio_value,
                )
            )
            capital_history.append(portfolio_value)
            peak_capital = max(peak_capital, portfolio_value)
            drawdown = (peak_capital - portfolio_value) / peak_capital if peak_capital > 0 else 0
            max_drawdown = max(max_drawdown, drawdown)

        final_value = capital + (position * rows[-1]["close"] if rows else 0.0)
        total_return = ((final_value - initial_capital) / initial_capital * 100) if initial_capital > 0 else 0

        returns = []
        for i in range(1, len(capital_history)):
            prev = capital_history[i - 1]
            if prev > 0:
                returns.append((capital_history[i] - prev) / prev)
        mean_ret = self._mean(returns)
        std_ret = math.sqrt(self._mean([(r - mean_ret) ** 2 for r in returns])) if returns else 0.0
        sharpe = (mean_ret / std_ret * math.sqrt(252)) if std_ret > 0 else 0.0

        total_trades = sum(1 for t in trades if t.action in ("buy", "sell"))
        win_rate = (winning / total_trades * 100) if total_trades > 0 else 0
        avg_trade_return = total_return / total_trades if total_trades > 0 else 0
        gross_profit = sum(t.amount_usd for t in trades if t.action == "sell" and t.price > 0 and t.amount_usd > 0)
        gross_loss = 0.0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (999.99 if gross_profit > 0 else 0.0)

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
            profit_factor=round(profit_factor, 2),
            data_source=data_source,
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
