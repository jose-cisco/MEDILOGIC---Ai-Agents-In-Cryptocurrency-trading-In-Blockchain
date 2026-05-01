"""
Unit tests for RiskEngine module.

Tests cover:
1. Risk level classification
2. Component score calculations
3. Overall assessment integration
"""

import pytest
from app.risk.risk_engine import (
    RiskEngine,
    RiskLevel,
    RiskAssessment,
    MarketData,
    OnChainData,
)


class TestRiskLevelClassification:
    """Test risk level classification based on scores."""

    def test_low_risk_classification(self):
        """Scores 0-25 should classify as LOW."""
        engine = RiskEngine()
        assert engine._classify_risk_level(0) == RiskLevel.LOW
        assert engine._classify_risk_level(15) == RiskLevel.LOW
        assert engine._classify_risk_level(25) == RiskLevel.LOW

    def test_moderate_risk_classification(self):
        """Scores 26-50 should classify as MODERATE."""
        engine = RiskEngine()
        assert engine._classify_risk_level(26) == RiskLevel.MODERATE
        assert engine._classify_risk_level(40) == RiskLevel.MODERATE
        assert engine._classify_risk_level(50) == RiskLevel.MODERATE

    def test_high_risk_classification(self):
        """Scores 51-75 should classify as HIGH."""
        engine = RiskEngine()
        assert engine._classify_risk_level(51) == RiskLevel.HIGH
        assert engine._classify_risk_level(65) == RiskLevel.HIGH
        assert engine._classify_risk_level(75) == RiskLevel.HIGH

    def test_critical_risk_classification(self):
        """Scores 76-100 should classify as CRITICAL."""
        engine = RiskEngine()
        assert engine._classify_risk_level(76) == RiskLevel.CRITICAL
        assert engine._classify_risk_level(90) == RiskLevel.CRITICAL
        assert engine._classify_risk_level(100) == RiskLevel.CRITICAL


class TestVolatilityRisk:
    """Test volatility risk calculation."""

    def test_low_volatility_returns_low_score(self):
        """Low volatility should return low risk score."""
        engine = RiskEngine()
        market = MarketData(
            price=100.0,
            volume_24h=1_000_000,
            volatility_24h=10.0,  # 10% annualized = low
            rsi_14=50.0,  # Neutral RSI
        )
        score = engine._calculate_volatility_risk(market)
        assert score < 30, f"Expected low volatility score, got {score}"

    def test_high_volatility_returns_high_score(self):
        """High volatility should return high risk score."""
        engine = RiskEngine()
        market = MarketData(
            price=100.0,
            volume_24h=1_000_000,
            volatility_24h=80.0,  # 80% annualized = high
            rsi_14=50.0,
        )
        score = engine._calculate_volatility_risk(market)
        assert score > 50, f"Expected high volatility score, got {score}"

    def test_overbought_rsi_increases_risk(self):
        """RSI > 70 (overbought) should increase risk."""
        engine = RiskEngine()
        market_neutral = MarketData(
            price=100.0,
            volume_24h=1_000_000,
            volatility_24h=20.0,
            rsi_14=50.0,
        )
        market_overbought = MarketData(
            price=100.0,
            volume_24h=1_000_000,
            volatility_24h=20.0,
            rsi_14=85.0,  # Overbought
        )
        score_neutral = engine._calculate_volatility_risk(market_neutral)
        score_overbought = engine._calculate_volatility_risk(market_overbought)
        assert score_overbought > score_neutral, "Overbought RSI should increase risk"


class TestLiquidityRisk:
    """Test liquidity risk calculation."""

    def test_high_liquidity_returns_low_score(self):
        """High volume/TVL should return low risk."""
        engine = RiskEngine()
        market = MarketData(
            price=100.0,
            volume_24h=10_000_000_000,  # $10B volume
            tvl=100_000_000_000,  # $100B TVL
        )
        score = engine._calculate_liquidity_risk(market, position_size_usd=1000)
        assert score < 20, f"Expected low liquidity score, got {score}"

    def test_low_tvl_increases_risk(self):
        """Low TVL should increase risk."""
        engine = RiskEngine()
        market = MarketData(
            price=100.0,
            volume_24h=10_000_000,
            tvl=500_000,  # Under $1M TVL
        )
        score = engine._calculate_liquidity_risk(market, position_size_usd=1000)
        assert score > 30, f"Expected higher risk for low TVL, got {score}"

    def test_large_position_vs_volume_increases_risk(self):
        """Large position relative to volume increases risk."""
        engine = RiskEngine()
        market_low_vol = MarketData(
            price=100.0,
            volume_24h=100_000,  # Low volume
        )
        market_high_vol = MarketData(
            price=100.0,
            volume_24h=10_000_000,  # High volume
        )
        score_low = engine._calculate_liquidity_risk(market_low_vol, position_size_usd=10000)
        score_high = engine._calculate_liquidity_risk(market_high_vol, position_size_usd=10000)
        assert score_low > score_high, "Low volume should have higher risk"


class TestOnChainRisk:
    """Test on-chain risk calculation."""

    def test_verified_audited_contract_low_risk(self):
        """Verified + audited contract should have low on-chain risk."""
        engine = RiskEngine()
        onchain = OnChainData(
            contract_verified=True,
            audit_status="audited",
            contract_age_days=365,
            exploit_history=False,
        )
        score = engine._calculate_onchain_risk(onchain, "ethereum")
        assert score < 20, f"Expected low on-chain score, got {score}"

    def test_unverified_contract_high_risk(self):
        """Unverified contract should have high risk."""
        engine = RiskEngine()
        onchain = OnChainData(
            contract_verified=False,
        )
        score = engine._calculate_onchain_risk(onchain, "ethereum")
        assert score >= 40, f"Expected high score for unverified contract, got {score}"

    def test_exploit_history_max_risk(self):
        """Exploit history should significantly increase risk."""
        engine = RiskEngine()
        onchain_clean = OnChainData(
            contract_verified=True,
            exploit_history=False,
        )
        onchain_exploit = OnChainData(
            contract_verified=True,
            exploit_history=True,
        )
        score_clean = engine._calculate_onchain_risk(onchain_clean, "ethereum")
        score_exploit = engine._calculate_onchain_risk(onchain_exploit, "ethereum")
        assert score_exploit > score_clean + 40, "Exploit history should add significant risk"


class TestFullAssessment:
    """Test full risk assessment integration."""

    def test_low_risk_assessment(self):
        """Low risk scenario should produce LOW risk level."""
        engine = RiskEngine()
        market = MarketData(
            price=3200.0,
            volume_24h=10_000_000_000,
            volatility_24h=15.0,
            rsi_14=50.0,
            macd_signal="bullish",
            sma_7=3150.0,
            sma_14=3100.0,
            sma_30=3000.0,
            tvl=50_000_000_000,
            chain="ethereum",
        )
        onchain = OnChainData(
            contract_verified=True,
            audit_status="audited",
            contract_age_days=730,
            governance_decentralized=True,
            multisig_threshold=3,
        )
        assessment = engine.assess(
            market_data=market,
            position_size_usd=1000,
            onchain_data=onchain,
        )
        assert assessment.risk_level == RiskLevel.LOW
        assert assessment.overall_score < 25

    def test_high_risk_assessment(self):
        """High risk scenario should produce HIGH risk level."""
        engine = RiskEngine()
        market = MarketData(
            price=100.0,
            volume_24h=500_000,  # Low volume
            volatility_24h=90.0,  # High volatility
            price_change_24h=25.0,  # Large price swing
            rsi_14=85.0,  # Overbought
            macd_signal="bearish",
            sma_7=95.0,
            sma_14=90.0,
            sma_30=85.0,
            tvl=500_000,  # Low TVL
            chain="ethereum",
        )
        onchain = OnChainData(
            contract_verified=False,
            audit_status="unaudited",
            exploit_history=True,
        )
        assessment = engine.assess(
            market_data=market,
            position_size_usd=10000,
            onchain_data=onchain,
        )
        assert assessment.overall_score > 50
        assert len(assessment.recommendations) > 0

    def test_assessment_to_dict(self):
        """Assessment should serialize to dict correctly."""
        engine = RiskEngine()
        market = MarketData(
            price=100.0,
            volume_24h=1_000_000,
        )
        assessment = engine.assess(market_data=market)
        result = assessment.to_dict()
        
        assert "overall_score" in result
        assert "risk_level" in result
        assert "volatility_risk" in result
        assert "drawdown_risk" in result
        assert "liquidity_risk" in result
        assert "onchain_risk" in result
        assert "recommendations" in result
        assert isinstance(result["overall_score"], float)
        assert isinstance(result["recommendations"], list)

    def test_custom_weights(self):
        """Custom weights should affect overall score."""
        default_engine = RiskEngine()
        volatility_engine = RiskEngine(weights={
            "volatility": 0.60,  # Higher weight
            "drawdown": 0.15,
            "liquidity": 0.15,
            "onchain": 0.10,
        })
        market = MarketData(
            price=100.0,
            volume_24h=1_000_000,
            volatility_24h=50.0,  # High volatility
        )
        default_assessment = default_engine.assess(market_data=market)
        volatility_assessment = volatility_engine.assess(market_data=market)
        
        # Higher volatility weight should produce higher overall score
        assert volatility_assessment.overall_score > default_assessment.overall_score


class TestChainSpecificRisk:
    """Test chain-specific base risk."""

    def test_ethereum_lower_base_risk_than_solana(self):
        """Ethereum should have lower base risk than Solana."""
        engine = RiskEngine()
        score_eth = engine._calculate_onchain_risk(None, "ethereum")
        score_sol = engine._calculate_onchain_risk(None, "solana")
        assert score_eth < score_sol, "Ethereum should have lower base risk"
        assert score_eth == 10, "Ethereum base risk should be 10"
        assert score_sol == 20, "Solana base risk should be 20"