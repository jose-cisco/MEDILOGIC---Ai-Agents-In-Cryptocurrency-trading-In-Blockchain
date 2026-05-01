"""
Risk-Adjusted Performance Metrics

Calculates performance metrics using historical risk assessments:
- Sharpe ratio
- Maximum drawdown
- Win rate by risk level
- Risk-adjusted returns
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from app.risk.risk_storage import RiskStorage

logger = logging.getLogger(__name__)


@dataclass
class RiskMetrics:
    """Risk-adjusted performance metrics."""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float  # 0.0 to 1.0
    avg_risk_score: float
    sharpe_ratio: Optional[float]
    max_drawdown: float
    risk_adjusted_return: Optional[float]
    win_rate_by_level: dict[str, float]
    avg_position_multiplier: float
    blocked_trades: int
    period_days: int


class RiskMetricsCalculator:
    """
    Calculate risk-adjusted performance metrics from historical data.
    
    Usage:
        storage = get_risk_storage()
        calculator = RiskMetricsCalculator(storage)
        metrics = calculator.calculate_metrics()
        print(f"Sharpe Ratio: {metrics.sharpe_ratio}")
        print(f"Win Rate: {metrics.win_rate * 100:.1f}%")
    """
    
    def __init__(self, storage: RiskStorage):
        self.storage = storage
    
    def calculate_metrics(
        self,
        returns: Optional[list[float]] = None,
        risk_free_rate: float = 0.04,  # 4% annual risk-free rate
        period_days: int = 30,
    ) -> RiskMetrics:
        """
        Calculate comprehensive risk metrics.
        
        Args:
            returns: List of trade returns (optional, simulated if not provided)
            risk_free_rate: Annual risk-free rate for Sharpe calculation
            period_days: Lookback period in days
        
        Returns:
            RiskMetrics with all calculated values
        """
        # Get historical assessments
        recent = self.storage.get_recent(limit=1000)
        stats = self.storage.get_statistics()
        
        if not recent:
            return self._empty_metrics()
        
        # Basic counts
        total_trades = len(recent)
        blocked = sum(1 for r in recent if r.outcome == "blocked")
        executed = [r for r in recent if r.outcome != "blocked"]
        
        # Win rate calculation (simulated based on risk score)
        # In production, this would use actual trade outcomes
        winning_trades = sum(
            1 for r in executed
            if r.overall_score < 50  # Lower risk = higher win probability
        )
        losing_trades = len(executed) - winning_trades
        
        win_rate = winning_trades / len(executed) if executed else 0.0
        
        # Average risk score
        avg_risk_score = stats.get("average_scores", {}).get("overall", 0)
        
        # Sharpe ratio calculation
        sharpe_ratio = None
        if returns and len(returns) > 1:
            sharpe_ratio = self._calculate_sharpe_ratio(returns, risk_free_rate)
        
        # Maximum drawdown
        max_drawdown = self._estimate_max_drawdown(executed)
        
        # Risk-adjusted return
        risk_adjusted_return = None
        if returns and avg_risk_score > 0:
            avg_return = sum(returns) / len(returns) if returns else 0
            risk_adjusted_return = avg_return / (avg_risk_score / 100) if avg_risk_score > 0 else 0
        
        # Win rate by risk level
        win_rate_by_level = self._calculate_win_rate_by_level(executed)
        
        # Average position multiplier
        avg_multiplier = stats.get("position_statistics", {}).get("avg_position_multiplier", 1.0)
        
        return RiskMetrics(
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=round(win_rate, 3),
            avg_risk_score=round(avg_risk_score, 2),
            sharpe_ratio=round(sharpe_ratio, 3) if sharpe_ratio else None,
            max_drawdown=round(max_drawdown, 3),
            risk_adjusted_return=round(risk_adjusted_return, 4) if risk_adjusted_return else None,
            win_rate_by_level={k: round(v, 3) for k, v in win_rate_by_level.items()},
            avg_position_multiplier=round(avg_multiplier, 3),
            blocked_trades=blocked,
            period_days=period_days,
        )
    
    def _calculate_sharpe_ratio(
        self,
        returns: list[float],
        risk_free_rate: float = 0.04,
    ) -> float:
        """
        Calculate Sharpe ratio.
        
        Sharpe = (E[R] - Rf) / σ(R)
        
        Where:
            E[R] = Expected return (mean)
            Rf = Risk-free rate
            σ(R) = Standard deviation of returns
        """
        if not returns or len(returns) < 2:
            return 0.0
        
        import statistics
        
        mean_return = statistics.mean(returns)
        std_return = statistics.stdev(returns)
        
        if std_return == 0:
            return 0.0
        
        # Annualize assuming daily returns
        annualized_mean = mean_return * 252  # Trading days per year
        annualized_std = std_return * (252 ** 0.5)
        
        sharpe = (annualized_mean - risk_free_rate) / annualized_std
        return sharpe
    
    def _estimate_max_drawdown(self, executed_trades: list) -> float:
        """
        Estimate maximum drawdown from risk scores.
        
        Higher risk scores indicate higher potential drawdown.
        This is a proxy estimation - in production, use actual PnL data.
        """
        if not executed_trades:
            return 0.0
        
        # Estimate drawdown based on risk scores
        # Higher scores = higher potential drawdown
        high_risk_trades = [t for t in executed_trades if t.overall_score >= 50]
        
        if not high_risk_trades:
            return 0.05  # 5% for low risk portfolio
        
        # Estimate drawdown from risk scores
        avg_high_risk = sum(t.overall_score for t in high_risk_trades) / len(high_risk_trades)
        estimated_drawdown = avg_high_risk / 100 * 0.5  # Scale factor
        
        return min(estimated_drawdown, 0.50)  # Cap at 50%
    
    def _calculate_win_rate_by_level(self, trades: list) -> dict[str, float]:
        """Calculate win rate for each risk level."""
        levels = ["low", "moderate", "high", "critical"]
        win_rates = {}
        
        for level in levels:
            level_trades = [t for t in trades if t.risk_level == level]
            if not level_trades:
                win_rates[level] = 0.0
                continue
            
            # Simulated win rate based on risk level
            # Lower risk = higher win probability
            base_rates = {"low": 0.7, "moderate": 0.55, "high": 0.35, "critical": 0.15}
            win_rates[level] = base_rates.get(level, 0.5)
        
        return win_rates
    
    def _empty_metrics(self) -> RiskMetrics:
        """Return empty metrics when no data available."""
        return RiskMetrics(
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0.0,
            avg_risk_score=0.0,
            sharpe_ratio=None,
            max_drawdown=0.0,
            risk_adjusted_return=None,
            win_rate_by_level={},
            avg_position_multiplier=1.0,
            blocked_trades=0,
            period_days=0,
        )
    
    def generate_report(self, metrics: RiskMetrics) -> str:
        """Generate a human-readable metrics report."""
        report = f"""
╔══════════════════════════════════════════════════════════════╗
║              RISK-ADJUSTED PERFORMANCE METRICS               ║
╠══════════════════════════════════════════════════════════════╣
║ Period: {metrics.period_days} days
╠══════════════════════════════════════════════════════════════╣
║ TRADE STATISTICS                                             ║
║   Total Trades:     {metrics.total_trades:>6}                                  ║
║   Winning Trades:  {metrics.winning_trades:>6}                                  ║
║   Losing Trades:   {metrics.losing_trades:>6}                                  ║
║   Blocked Trades:   {metrics.blocked_trades:>6}                                  ║
║   Win Rate:         {metrics.win_rate * 100:>6.1f}%                                 ║
╠══════════════════════════════════════════════════════════════╣
║ RISK METRICS                                                 ║
║   Avg Risk Score:   {metrics.avg_risk_score:>6.1f} / 100                         ║
║   Max Drawdown:     {metrics.max_drawdown * 100:>6.1f}%                               ║
║   Avg Position:     {metrics.avg_position_multiplier * 100:>6.1f}% of requested              ║
╠══════════════════════════════════════════════════════════════╣
║ RISK-ADJUSTED RETURNS                                        ║
║   Sharpe Ratio:     {metrics.sharpe_ratio:>6.2f if metrics.sharpe_ratio else 'N/A':>6}                               ║
║   Risk-Adj Return:  {metrics.risk_adjusted_return:>6.2f if metrics.risk_adjusted_return else 'N/A':>6}                               ║
╠══════════════════════════════════════════════════════════════╣
║ WIN RATE BY RISK LEVEL                                       ║"""
        
        for level, rate in metrics.win_rate_by_level.items():
            report += f"\n║   {level.upper():10s}:    {rate * 100:>5.1f}%                              ║"
        
        report += "\n╚══════════════════════════════════════════════════════════════╝"
        
        return report


class RiskCalibrator:
    """
    Calibrate risk weights based on historical performance.
    
    Analyzes correlation between risk scores and outcomes to
    suggest optimal weight adjustments.
    """
    
    def __init__(self, storage: RiskStorage):
        self.storage = storage
    
    def suggest_weight_adjustments(self) -> dict:
        """
        Analyze historical data to suggest weight adjustments.
        
        Returns:
            Dict with suggested weights and reasoning
        """
        stats = self.storage.get_statistics()
        avg_scores = stats.get("average_scores", {})
        
        # Current weights
        current_weights = {
            "volatility": 0.30,
            "drawdown": 0.25,
            "liquidity": 0.25,
            "onchain": 0.20,
        }
        
        # Suggested adjustments based on which components are driving risk
        suggestions = {}
        reasoning = []
        
        vol_avg = avg_scores.get("volatility", 25)
        dd_avg = avg_scores.get("drawdown", 25)
        liq_avg = avg_scores.get("liquidity", 25)
        chain_avg = avg_scores.get("onchain", 25)
        
        # If volatility is consistently high, increase its weight
        if vol_avg > 40:
            suggestions["volatility"] = 0.35
            reasoning.append("Volatility scores high - increase weight for better detection")
        elif vol_avg < 20:
            suggestions["volatility"] = 0.25
            reasoning.append("Volatility scores low - can reduce weight")
        
        # If on-chain risk is high, increase weight
        if chain_avg > 35:
            suggestions["onchain"] = 0.25
            reasoning.append("On-chain risk elevated - increase weight for safety")
        
        # Normalize weights to sum to 1.0
        if suggestions:
            total = sum(suggestions.values())
            if total != 1.0:
                for key in suggestions:
                    suggestions[key] = suggestions[key] / total * len(suggestions)
        
        return {
            "current_weights": current_weights,
            "suggested_weights": suggestions or current_weights,
            "average_component_scores": avg_scores,
            "reasoning": reasoning or ["Current weights appear well-calibrated"],
        }


class RiskAlerter:
    """
    Monitor and alert on risk conditions.
    
    Sends alerts when:
    - Risk scores are consistently high
    - Multiple CRITICAL blocks in short period
    - Unusual risk patterns detected
    """
    
    def __init__(self, alert_threshold: float = 70.0, window_size: int = 10):
        self.alert_threshold = alert_threshold
        self.window_size = window_size
        self._recent_scores: list[float] = []
    
    def check_alerts(self, current_score: float, risk_level: str) -> list[dict]:
        """
        Check if alerts should be triggered.
        
        Returns:
            List of alert dictionaries
        """
        alerts = []
        
        # Add to recent scores
        self._recent_scores.append(current_score)
        if len(self._recent_scores) > self.window_size:
            self._recent_scores.pop(0)
        
        # Alert 1: Single CRITICAL score
        if risk_level == "critical":
            alerts.append({
                "level": "CRITICAL",
                "message": f"CRITICAL risk score detected: {current_score:.1f}",
                "action": "Trade blocked. Review market conditions.",
                "timestamp": datetime.utcnow().isoformat(),
            })
        
        # Alert 2: Consistently high scores
        if len(self._recent_scores) >= self.window_size:
            avg_recent = sum(self._recent_scores) / len(self._recent_scores)
            if avg_recent > self.alert_threshold:
                alerts.append({
                    "level": "WARNING",
                    "message": f"Consistently high risk: {avg_recent:.1f} avg over {self.window_size} trades",
                    "action": "Consider pausing trading or reducing position sizes.",
                    "timestamp": datetime.utcnow().isoformat(),
                })
        
        # Alert 3: Rapid risk increase
        if len(self._recent_scores) >= 5:
            recent_5 = self._recent_scores[-5:]
            older_5 = self._recent_scores[-10:-5] if len(self._recent_scores) >= 10 else []
            if older_5:
                recent_avg = sum(recent_5) / len(recent_5)
                older_avg = sum(older_5) / len(older_5)
                if recent_avg > older_avg * 1.5:  # 50% increase
                    alerts.append({
                        "level": "WARNING",
                        "message": f"Rapid risk increase detected: {older_avg:.1f} → {recent_avg:.1f}",
                        "action": "Market conditions deteriorating. Review risk parameters.",
                        "timestamp": datetime.utcnow().isoformat(),
                    })
        
        # Log alerts
        for alert in alerts:
            logger.warning(
                "RISK ALERT [%s]: %s",
                alert["level"],
                alert["message"],
            )
        
        return alerts


# Convenience function
def get_risk_metrics() -> RiskMetrics:
    """Get current risk metrics using default storage."""
    from app.risk.risk_storage import get_risk_storage
    
    storage = get_risk_storage()
    calculator = RiskMetricsCalculator(storage)
    return calculator.calculate_metrics()