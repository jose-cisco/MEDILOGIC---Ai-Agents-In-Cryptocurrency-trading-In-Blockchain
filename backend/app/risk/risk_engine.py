"""
Risk Engine — Multi-Factor Risk Assessment
==========================================

Calculates comprehensive risk scores for trade execution decisions.
Integrates with the trading orchestrator and API endpoints.

Risk Components:
    - Volatility Risk: Price fluctuation intensity
    - Max Drawdown Risk: Historical peak-to-trough decline
    - Liquidity Risk: Market depth and slippage potential
    - On-Chain Risk: Smart contract and protocol risks

Overall Risk Score: 0-100 (higher = riskier)
    - 0-25: Low risk (safe to execute)
    - 26-50: Moderate risk (caution advised)
    - 51-75: High risk (additional verification required)
    - 76-100: Critical risk (execution blocked)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    """Risk level classification based on overall score."""
    LOW = "low"          # 0-25
    MODERATE = "moderate"  # 26-50
    HIGH = "high"        # 51-75
    CRITICAL = "critical"  # 76-100


@dataclass
class MarketData:
    """Market data required for risk assessment."""
    price: float
    volume_24h: float
    volatility_24h: Optional[float] = None  # Annualized volatility %
    price_change_24h: Optional[float] = None  # % change
    liquidity_depth: Optional[float] = None  # Order book depth in USD
    slippage_estimate: Optional[float] = None  # Expected slippage %
    sma_7: Optional[float] = None
    sma_14: Optional[float] = None
    sma_30: Optional[float] = None
    rsi_14: Optional[float] = None
    macd_signal: Optional[str] = None
    tvl: Optional[float] = None  # Total value locked (DeFi)
    chain: str = "ethereum"
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class OnChainData:
    """On-chain metrics for blockchain risk assessment."""
    contract_verified: bool = True
    audit_status: Optional[str] = None  # "audited", "unaudited", "pending"
    tvl_usd: Optional[float] = None
    contract_age_days: Optional[int] = None
    unique_wallets_24h: Optional[int] = None
    exploit_history: bool = False
    governance_decentralized: bool = True
    multisig_threshold: Optional[int] = None


@dataclass
class RiskAssessment:
    """Complete risk assessment result."""
    overall_score: float  # 0-100
    risk_level: RiskLevel
    volatility_risk: float  # 0-100 component score
    drawdown_risk: float  # 0-100 component score
    liquidity_risk: float  # 0-100 component score
    onchain_risk: float  # 0-100 component score
    factors: dict[str, Any] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "overall_score": self.overall_score,
            "risk_level": self.risk_level.value,
            "volatility_risk": self.volatility_risk,
            "drawdown_risk": self.drawdown_risk,
            "liquidity_risk": self.liquidity_risk,
            "onchain_risk": self.onchain_risk,
            "factors": self.factors,
            "recommendations": self.recommendations,
            "timestamp": self.timestamp,
        }


class RiskEngine:
    """
    Multi-factor risk assessment engine for trading decisions.
    
    Usage:
        engine = RiskEngine()
        assessment = engine.assess(
            market_data=market_data,
            position_size_usd=1000,
            token_pair="ETH/USDT",
            chain="ethereum",
        )
        print(f"Risk Score: {assessment.overall_score}")
        print(f"Risk Level: {assessment.risk_level.value}")
    """
    
    # Weight configuration for each risk component
    DEFAULT_WEIGHTS = {
        "volatility": 0.30,    # 30% weight
        "drawdown": 0.25,     # 25% weight
        "liquidity": 0.25,    # 25% weight
        "onchain": 0.20,     # 20% weight
    }
    
    # Risk thresholds for level classification
    RISK_THRESHOLDS = {
        RiskLevel.LOW: 25,
        RiskLevel.MODERATE: 50,
        RiskLevel.HIGH: 75,
        RiskLevel.CRITICAL: 100,
    }
    
    def __init__(
        self,
        weights: Optional[dict[str, float]] = None,
        max_position_pct: float = 0.05,  # Max 5% of portfolio per trade
        volatility_threshold: float = 0.50,  # 50% annualized = high risk
        drawdown_threshold: float = 0.20,  # 20% max drawdown = high risk
    ):
        """
        Initialize the risk engine with configurable parameters.
        
        Args:
            weights: Custom weights for each risk component (must sum to 1.0)
            max_position_pct: Maximum position size as % of portfolio
            volatility_threshold: Annualized volatility % for high risk
            drawdown_threshold: Max drawdown % for high risk
        """
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
        self.max_position_pct = max_position_pct
        self.volatility_threshold = volatility_threshold
        self.drawdown_threshold = drawdown_threshold
        
        # Validate weights
        if abs(sum(self.weights.values()) - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {sum(self.weights.values())}")
    
    def assess(
        self,
        market_data: MarketData,
        position_size_usd: float = 1000.0,
        portfolio_value_usd: Optional[float] = None,
        onchain_data: Optional[OnChainData] = None,
        token_pair: str = "ETH/USDT",
        chain: str = "ethereum",
    ) -> RiskAssessment:
        """
        Perform comprehensive risk assessment.
        
        Args:
            market_data: Market data containing price, volume, indicators
            position_size_usd: Proposed position size in USD
            portfolio_value_usd: Total portfolio value for position sizing risk
            onchain_data: On-chain metrics for blockchain risk
            token_pair: Trading pair symbol
            chain: Blockchain network
        
        Returns:
            RiskAssessment with overall score and component breakdown
        """
        # Calculate component scores
        volatility_risk = self._calculate_volatility_risk(market_data)
        drawdown_risk = self._calculate_drawdown_risk(market_data)
        liquidity_risk = self._calculate_liquidity_risk(
            market_data, position_size_usd, portfolio_value_usd
        )
        onchain_risk = self._calculate_onchain_risk(onchain_data, chain)
        
        # Weighted overall score
        overall_score = (
            volatility_risk * self.weights["volatility"] +
            drawdown_risk * self.weights["drawdown"] +
            liquidity_risk * self.weights["liquidity"] +
            onchain_risk * self.weights["onchain"]
        )
        
        # Add position sizing risk if portfolio value provided
        if portfolio_value_usd and portfolio_value_usd > 0:
            position_pct = position_size_usd / portfolio_value_usd
            if position_pct > self.max_position_pct:
                # Penalize for oversized positions
                excess_ratio = (position_pct - self.max_position_pct) / self.max_position_pct
                overall_score = min(100, overall_score * (1 + excess_ratio))
        
        # Determine risk level
        risk_level = self._classify_risk_level(overall_score)
        
        # Build factors dict
        factors = {
            "token_pair": token_pair,
            "chain": chain,
            "position_size_usd": position_size_usd,
            "portfolio_value_usd": portfolio_value_usd,
            "volatility_details": {
                "volatility_24h": market_data.volatility_24h,
                "price_change_24h": market_data.price_change_24h,
                "rsi": market_data.rsi_14,
            },
            "drawdown_details": {
                "price": market_data.price,
                "sma_7": market_data.sma_7,
                "sma_14": market_data.sma_14,
                "sma_30": market_data.sma_30,
            },
            "liquidity_details": {
                "volume_24h": market_data.volume_24h,
                "tvl": market_data.tvl,
                "depth": market_data.liquidity_depth,
                "slippage": market_data.slippage_estimate,
            },
            "onchain_details": {
                "contract_verified": onchain_data.contract_verified if onchain_data else True,
                "audit_status": onchain_data.audit_status if onchain_data else None,
                "exploit_history": onchain_data.exploit_history if onchain_data else False,
            } if onchain_data else {},
        }
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            overall_score, volatility_risk, drawdown_risk, liquidity_risk, onchain_risk
        )
        
        logger.info(
            "Risk assessment completed: score=%.2f, level=%s, vol=%.2f, dd=%.2f, liq=%.2f, chain=%.2f",
            overall_score, risk_level.value, volatility_risk, drawdown_risk, liquidity_risk, onchain_risk
        )
        
        return RiskAssessment(
            overall_score=round(overall_score, 2),
            risk_level=risk_level,
            volatility_risk=round(volatility_risk, 2),
            drawdown_risk=round(drawdown_risk, 2),
            liquidity_risk=round(liquidity_risk, 2),
            onchain_risk=round(onchain_risk, 2),
            factors=factors,
            recommendations=recommendations,
        )
    
    def _calculate_volatility_risk(self, data: MarketData) -> float:
        """
        Calculate volatility risk component (0-100).
        
        Factors:
            - 24h volatility (annualized)
            - Price change magnitude
            - RSI extremes (overbought/oversold)
        """
        score = 0.0
        
        # Volatility-based risk
        if data.volatility_24h is not None:
            # Scale: 0% = 0 points, 100%+ = 100 points
            vol_score = min(100, data.volatility_24h / self.volatility_threshold * 50)
            score += vol_score * 0.5
        else:
            # Default moderate volatility if unknown
            score += 25.0
        
        # Price change impact
        if data.price_change_24h is not None:
            # Large moves (either direction) increase risk
            change_score = min(100, abs(data.price_change_24h))
            score += change_score * 0.3
        
        # RSI extremes
        if data.rsi_14 is not None:
            # RSI > 70 (overbought) or < 30 (oversold) adds risk
            if data.rsi_14 > 70:
                rsi_score = (data.rsi_14 - 70) * 3.33  # 70-100 -> 0-100
            elif data.rsi_14 < 30:
                rsi_score = (30 - data.rsi_14) * 3.33  # 0-30 -> 100-0
            else:
                rsi_score = 0
            score += rsi_score * 0.2
        
        return min(100, score)
    
    def _calculate_drawdown_risk(self, data: MarketData) -> float:
        """
        Calculate max drawdown risk component (0-100).
        
        Factors:
            - Distance from SMAs (trend deviation)
            - MACD signal direction
            - Historical drawdown estimation
        """
        score = 0.0
        
        # SMA-based trend analysis
        if all(v is not None for v in [data.sma_7, data.sma_14, data.sma_30, data.price]):
            price = data.price
            sma_7, sma_14, sma_30 = data.sma_7, data.sma_14, data.sma_30
            
            # Deviation from moving averages
            dev_7 = abs(price - sma_7) / sma_7 if sma_7 > 0 else 0
            dev_14 = abs(price - sma_14) / sma_14 if sma_14 > 0 else 0
            dev_30 = abs(price - sma_30) / sma_30 if sma_30 > 0 else 0
            
            # Average deviation scaled to 0-100
            avg_dev = (dev_7 + dev_14 + dev_30) / 3
            score += min(100, avg_dev * 500)  # 20% deviation = 100 score
            
            # Trend direction risk (bearish trends = higher risk for longs)
            if sma_7 < sma_14 < sma_30:  # Bearish alignment
                score += 20  # Additional risk for bearish trend
            elif sma_7 > sma_14 > sma_30:  # Bullish alignment
                score -= 10  # Lower risk for bullish trend
        
        # MACD signal impact
        if data.macd_signal:
            if data.macd_signal == "bearish":
                score += 15
            elif data.macd_signal == "bullish":
                score -= 5
        
        return max(0, min(100, score))
    
    def _calculate_liquidity_risk(
        self,
        data: MarketData,
        position_size_usd: float,
        portfolio_value_usd: Optional[float] = None,
    ) -> float:
        """
        Calculate liquidity risk component (0-100).
        
        Factors:
            - Trading volume relative to position
            - TVL (Total Value Locked)
            - Estimated slippage
            - Order book depth
        """
        score = 0.0
        
        # Volume-based liquidity
        if data.volume_24h is not None and data.volume_24h > 0:
            # Position as % of daily volume (higher = riskier)
            volume_ratio = position_size_usd / data.volume_24h
            # 0.1% of volume = 10 points, 1%+ = 50+ points
            score += min(50, volume_ratio * 1000)
        else:
            score += 25  # Unknown volume = moderate risk
        
        # TVL-based liquidity (DeFi)
        if data.tvl is not None and data.tvl > 0:
            # Low TVL = higher risk
            if data.tvl < 1_000_000:  # Under $1M TVL
                score += 30
            elif data.tvl < 10_000_000:  # Under $10M TVL
                score += 15
            elif data.tvl < 100_000_000:  # Under $100M TVL
                score += 5
        
        # Slippage estimate
        if data.slippage_estimate is not None:
            # 0.5% slippage = 25 points, 2%+ = 100 points
            slippage_score = min(100, data.slippage_estimate * 50)
            score += slippage_score
        
        # Order book depth
        if data.liquidity_depth is not None:
            depth_ratio = position_size_usd / data.liquidity_depth
            # 1% of depth = 10 points, 5%+ = 50+ points
            score += min(50, depth_ratio * 1000)
        
        return min(100, score)
    
    def _calculate_onchain_risk(
        self,
        data: Optional[OnChainData],
        chain: str,
    ) -> float:
        """
        Calculate on-chain risk component (0-100).
        
        Factors:
            - Contract verification status
            - Audit status
            - Exploit history
            - Governance decentralization
            - Contract age
            - Chain-specific risks (Solana: Raydium/Jupiter risks)
        """
        score = 0.0
        
        # Default for unknown on-chain data
        if data is None:
            # Chain-specific base risk
            chain_risk = {
                "ethereum": 10,  # Most established
                "solana": 20,   # Newer, more volatility
            }
            return chain_risk.get(chain, 15)
        
        # Unverified contracts = high risk
        if not data.contract_verified:
            score += 40
        
        # Audit status
        if data.audit_status:
            if data.audit_status == "unaudited":
                score += 30
            elif data.audit_status == "pending":
                score += 15
            # "audited" = no penalty
        
        # Exploit history
        if data.exploit_history:
            score += 50
        
        # Governance centralization
        if not data.governance_decentralized:
            score += 15
        
        # Contract age (newer = riskier)
        if data.contract_age_days is not None:
            if data.contract_age_days < 30:
                score += 25
            elif data.contract_age_days < 90:
                score += 15
            elif data.contract_age_days < 365:
                score += 5
        
        # Multisig threshold
        if data.multisig_threshold is not None:
            if data.multisig_threshold < 2:
                score += 20  # Single sig = centralization risk
        
        # ── Chain-specific risk factors ──
        if chain == "solana":
            # Solana-specific risks: Raydium, Jupiter, SPL tokens
            # Add base risk for Solana's newer ecosystem
            score += self._calculate_solana_specific_risk(data)
        
        return min(100, score)
    
    def _calculate_solana_specific_risk(self, data: OnChainData) -> float:
        """
        Calculate Solana-specific on-chain risks.
        
        Solana DeFi risks include:
        - Raydium liquidity pool risks (concentrated liquidity)
        - Jupiter DEX aggregator slippage risks
        - SPL token verification status
        - Program upgrade authority centralization
        - Network congestion/uptime risks
        
        Note: This adds extra risk points for Solana-specific concerns.
        """
        solana_risk = 0.0
        
        # SPL token verification (Solana's token list)
        # Unverified SPL tokens have higher scam potential
        if not data.contract_verified:
            solana_risk += 15  # Extra penalty on Solana
        
        # Program upgrade authority (Solana programs are upgradable by default)
        # If governance is not decentralized, upgrade authority is centralized
        if not data.governance_decentralized:
            solana_risk += 10  # Centralized upgrade authority risk
        
        # Contract age penalty is higher on Solana (faster-moving ecosystem)
        if data.contract_age_days is not None:
            if data.contract_age_days < 7:
                solana_risk += 20  # Very new Solana programs are risky
            elif data.contract_age_days < 30:
                solana_risk += 10
        
        # Known Solana DeFi protocol risks
        # Raydium: Concentrated liquidity can lead to larger slippage
        # Jupiter: Aggregator adds smart contract dependency layer
        # Note: In production, you'd check if the token interacts with these
        # For now, we add a base Solana DeFi risk
        solana_risk += 5  # Base Solana DeFi complexity risk
        
        return solana_risk
    
    def _classify_risk_level(self, score: float) -> RiskLevel:
        """Classify overall score into risk level."""
        if score <= self.RISK_THRESHOLDS[RiskLevel.LOW]:
            return RiskLevel.LOW
        elif score <= self.RISK_THRESHOLDS[RiskLevel.MODERATE]:
            return RiskLevel.MODERATE
        elif score <= self.RISK_THRESHOLDS[RiskLevel.HIGH]:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL

    def get_position_multiplier(self, score: float) -> float:
        """
        Calculate dynamic position multiplier based on risk score.
        
        Score-based scaling:
        - 0-25 (LOW): 100% position
        - 26-50 (MODERATE): 100% position
        - 51-75 (HIGH): Linear scale from 90% (score=51) to 50% (score=75)
        - 76-100 (CRITICAL): 0% (blocked)
        
        Returns:
            Position multiplier between 0.0 and 1.0
        """
        if score >= 76:
            # CRITICAL: Block entirely
            return 0.0
        elif score >= 51:
            # HIGH: Dynamic reduction (51 → 0.90, 75 → 0.50)
            # Linear interpolation: at 51, mult=0.90; at 75, mult=0.50
            # Formula: mult = 0.90 - (score - 51) * (0.40 / 24)
            return 0.90 - (score - 51) * (0.40 / 24)
        else:
            # LOW/MODERATE: Full position
            return 1.0
    
    def _generate_recommendations(
        self,
        overall: float,
        volatility: float,
        drawdown: float,
        liquidity: float,
        onchain: float,
    ) -> list[str]:
        """Generate actionable recommendations based on risk scores."""
        recommendations = []
        
        if overall > 75:
            recommendations.append("⚠️ CRITICAL: Trade execution blocked. Reduce position size or select different pair.")
        elif overall > 50:
            recommendations.append("⚠️ HIGH RISK: Additional verification recommended before execution.")
        
        if volatility > 70:
            recommendations.append("High volatility detected. Consider tighter stop-loss.")
        
        if drawdown > 60:
            recommendations.append("Significant drawdown risk. Trend may be reversing.")
        
        if liquidity > 60:
            recommendations.append("Low liquidity. Large positions may experience slippage.")
        
        if onchain > 50:
            recommendations.append("On-chain risks detected. Verify contract security before trading.")
        
        if overall <= 25:
            recommendations.append("✅ Low risk profile. Trade execution within safe parameters.")
        
        return recommendations


# ─────────────────────────────────────────────────────────────────────────────
# USAGE EXAMPLE
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Create the risk engine
    engine = RiskEngine()
    
    # Create market data
    market = MarketData(
        price=3200.0,
        volume_24h=5_000_000_000,  # $5B daily volume
        volatility_24h=45.0,  # 45% annualized
        price_change_24h=-2.5,  # -2.5% change
        rsi_14=55.0,  # Neutral RSI
        macd_signal="bullish",
        sma_7=3150.0,
        sma_14=3100.0,
        sma_30=3000.0,
        tvl=50_000_000_000,  # $50B TVL
        chain="ethereum",
    )
    
    # Create on-chain data
    onchain = OnChainData(
        contract_verified=True,
        audit_status="audited",
        contract_age_days=730,  # 2 years
        governance_decentralized=True,
        multisig_threshold=3,
    )
    
    # Assess risk
    assessment = engine.assess(
        market_data=market,
        position_size_usd=1000,
        portfolio_value_usd=100_000,
        onchain_data=onchain,
        token_pair="ETH/USDT",
        chain="ethereum",
    )
    
    # Print results
    print(f"Overall Risk Score: {assessment.overall_score}")
    print(f"Risk Level: {assessment.risk_level.value}")
    print(f"Volatility Risk: {assessment.volatility_risk}")
    print(f"Drawdown Risk: {assessment.drawdown_risk}")
    print(f"Liquidity Risk: {assessment.liquidity_risk}")
    print(f"On-Chain Risk: {assessment.onchain_risk}")
    print(f"Recommendations: {assessment.recommendations}")
    
    # Convert to dict for API response
    print("\nAPI Response:")
    print(assessment.to_dict())