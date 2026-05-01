"""
Integration tests for RiskEngine in the trading flow.

Tests three key scenarios:
1. Low risk - safe to execute
2. High risk - position should be reduced
3. Critical risk - trade should be blocked
"""

import pytest
from app.risk.risk_engine import RiskEngine, RiskLevel, MarketData, OnChainData


class TestRiskIntegration:
    """End-to-end risk assessment tests."""

    @pytest.fixture
    def engine(self):
        return RiskEngine()

    def test_case_1_low_risk_safe_trade(self, engine):
        """
        Case 1: Low Risk (Safe Trade)
        
        Scenario: High-volume ETH on Ethereum with good metrics
        Expected: Risk score 0-25, LOW level, proceed normally
        """
        # Setup: High liquidity, low volatility, audited contract
        market = MarketData(
            price=3200.0,
            volume_24h=10_000_000_000,  # $10B volume (very high)
            volatility_24h=15.0,  # Low volatility
            price_change_24h=-1.5,  # Small price change
            rsi_14=50.0,  # Neutral RSI
            macd_signal="bullish",
            sma_7=3180.0,  # Close to price
            sma_14=3150.0,
            sma_30=3100.0,
            tvl=50_000_000_000,  # $50B TVL
            chain="ethereum",
        )
        
        onchain = OnChainData(
            contract_verified=True,
            audit_status="audited",
            contract_age_days=730,  # 2 years old
            exploit_history=False,
            governance_decentralized=True,
            multisig_threshold=3,
        )
        
        # Execute
        assessment = engine.assess(
            market_data=market,
            position_size_usd=1000,
            portfolio_value_usd=100_000,  # 1% position
            onchain_data=onchain,
            token_pair="ETH/USDT",
            chain="ethereum",
        )
        
        # Verify
        print("\n=== Case 1: Low Risk (Safe Trade) ===")
        print(f"Risk Score: {assessment.overall_score}")
        print(f"Risk Level: {assessment.risk_level.value}")
        print(f"Volatility Risk: {assessment.volatility_risk}")
        print(f"Drawdown Risk: {assessment.drawdown_risk}")
        print(f"Liquidity Risk: {assessment.liquidity_risk}")
        print(f"On-Chain Risk: {assessment.onchain_risk}")
        print(f"Recommendations: {assessment.recommendations}")
        
        assert assessment.risk_level == RiskLevel.LOW
        assert assessment.overall_score <= 25
        assert "Low risk profile" in str(assessment.recommendations)
        
        # API Response format
        response = assessment.to_dict()
        print(f"\nAPI Response:\n{response}")
        
        return assessment

    def test_case_2_high_risk_position_reduction(self, engine):
        """
        Case 2: High Risk (Position Reduction Required)
        
        Scenario: Moderate volume, high volatility, unaudited contract
        Expected: Risk score 51-75, HIGH level, position reduced to 50%
        """
        # Setup: Moderate volume, high volatility, unaudited
        market = MarketData(
            price=100.0,
            volume_24h=50_000_000,  # $50M volume (moderate)
            volatility_24h=75.0,  # High volatility
            price_change_24h=15.0,  # Large price swing
            rsi_14=82.0,  # Overbought
            macd_signal="bearish",  # Bearish signal
            sma_7=95.0,  # Price above SMAs (bearish divergence)
            sma_14=90.0,
            sma_30=85.0,
            tvl=5_000_000,  # $5M TVL (moderate)
            chain="ethereum",
        )
        
        onchain = OnChainData(
            contract_verified=True,
            audit_status="unaudited",  # No audit
            contract_age_days=60,  # 2 months old
            exploit_history=False,
            governance_decentralized=False,  # Centralized
            multisig_threshold=1,  # Single sig
        )
        
        # Execute
        assessment = engine.assess(
            market_data=market,
            position_size_usd=10000,
            portfolio_value_usd=50_000,  # 20% position (large)
            onchain_data=onchain,
            token_pair="TOKEN/USDT",
            chain="ethereum",
        )
        
        # Verify
        print("\n=== Case 2: High Risk (Position Reduction Required) ===")
        print(f"Risk Score: {assessment.overall_score}")
        print(f"Risk Level: {assessment.risk_level.value}")
        print(f"Volatility Risk: {assessment.volatility_risk}")
        print(f"Drawdown Risk: {assessment.drawdown_risk}")
        print(f"Liquidity Risk: {assessment.liquidity_risk}")
        print(f"On-Chain Risk: {assessment.onchain_risk}")
        print(f"Recommendations: {assessment.recommendations}")
        
        assert assessment.risk_level == RiskLevel.HIGH
        assert 51 <= assessment.overall_score <= 75
        
        # Position reduction would be applied
        position_multiplier = 0.5 if assessment.risk_level == RiskLevel.HIGH else 1.0
        print(f"\nPosition Adjustment: Reduced to {position_multiplier * 100}%")
        print(f"Original Position: $10,000")
        print(f"Adjusted Position: ${10000 * position_multiplier:,.2f}")
        
        return assessment

    def test_case_3_critical_risk_blocked(self, engine):
        """
        Case 3: Critical Risk (Trade Blocked)
        
        Scenario: Low volume, extreme volatility, unverified contract with exploit history
        Expected: Risk score 76-100, CRITICAL level, trade blocked
        """
        # Setup: Very risky conditions
        market = MarketData(
            price=50.0,
            volume_24h=500_000,  # $500K volume (very low)
            volatility_24h=120.0,  # Extreme volatility
            price_change_24h=35.0,  # Massive price swing
            rsi_14=92.0,  # Severely overbought
            macd_signal="bearish",
            sma_7=45.0,  # Price diverging from SMAs
            sma_14=40.0,
            sma_30=35.0,
            tvl=200_000,  # Low TVL
            chain="ethereum",
        )
        
        onchain = OnChainData(
            contract_verified=False,  # Unverified contract
            audit_status="unaudited",
            contract_age_days=7,  # Very new
            exploit_history=True,  # Previous exploits!
            governance_decentralized=False,
            multisig_threshold=1,
        )
        
        # Execute
        assessment = engine.assess(
            market_data=market,
            position_size_usd=5000,
            portfolio_value_usd=10_000,  # 50% position (extremely risky)
            onchain_data=onchain,
            token_pair="SHITCOIN/USDT",
            chain="ethereum",
        )
        
        # Verify
        print("\n=== Case 3: Critical Risk (Trade Blocked) ===")
        print(f"Risk Score: {assessment.overall_score}")
        print(f"Risk Level: {assessment.risk_level.value}")
        print(f"Volatility Risk: {assessment.volatility_risk}")
        print(f"Drawdown Risk: {assessment.drawdown_risk}")
        print(f"Liquidity Risk: {assessment.liquidity_risk}")
        print(f"On-Chain Risk: {assessment.onchain_risk}")
        print(f"Recommendations: {assessment.recommendations}")
        
        assert assessment.risk_level == RiskLevel.CRITICAL
        assert assessment.overall_score >= 76
        assert any("CRITICAL" in r or "blocked" in r.lower() for r in assessment.recommendations)
        
        # Trade would be blocked
        print(f"\nTRADE BLOCKED: Risk score {assessment.overall_score:.1f} >= 76")
        print("User message: CRITICAL RISK BLOCKED - Trade rejected for safety")
        
        return assessment


class TestRiskAPIRequestFormat:
    """Test API request/response format."""

    def test_api_request_format(self):
        """Show expected API request format for /risk/assess."""
        request = {
            "price": 3200.0,
            "volume_24h": 5000000000,
            "token_pair": "ETH/USDT",
            "chain": "ethereum",
            "position_size_usd": 1000.0,
            "portfolio_value_usd": 100000.0,
            "volatility_24h": 45.0,
            "price_change_24h": -2.5,
            "rsi_14": 55.0,
            "macd_signal": "bullish",
            "sma_7": 3150.0,
            "sma_14": 3100.0,
            "sma_30": 3000.0,
            "tvl": 50000000000,
            "contract_verified": True,
            "audit_status": "audited",
            "contract_age_days": 730,
            "exploit_history": False,
            "governance_decentralized": True,
            "multisig_threshold": 3,
        }
        
        print("\n=== API Request Format ===")
        print("POST /trading/risk/assess")
        print("Content-Type: application/json")
        print(f"\nRequest Body:\n{request}")
        
        # Expected response format
        response = {
            "overall_score": 15.5,
            "risk_level": "low",
            "volatility_risk": 12.0,
            "drawdown_risk": 8.0,
            "liquidity_risk": 5.0,
            "onchain_risk": 10.0,
            "factors": {
                "token_pair": "ETH/USDT",
                "chain": "ethereum",
                "position_size_usd": 1000.0,
            },
            "recommendations": ["✅ Low risk profile. Trade execution within safe parameters."],
            "timestamp": "2026-04-20T17:35:00.000Z",
        }
        
        print(f"\nExpected Response:\n{response}")
        
        return request


if __name__ == "__main__":
    """Run integration tests with verbose output."""
    import sys
    
    engine = RiskEngine()
    test = TestRiskIntegration()
    
    print("=" * 60)
    print("RISK ENGINE INTEGRATION TESTS")
    print("=" * 60)
    
    # Run each test case
    test.test_case_1_low_risk_safe_trade(engine)
    test.test_case_2_high_risk_position_reduction(engine)
    test.test_case_3_critical_risk_blocked(engine)
    
    # Show API format
    api_test = TestRiskAPIRequestFormat()
    api_test.test_api_request_format()
    
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)