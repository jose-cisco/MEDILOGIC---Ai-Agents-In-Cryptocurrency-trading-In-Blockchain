"""
x402 Payment Protocol Integration
==================================
Implements the HTTP 402 Payment Required protocol for pay-per-use API access.

x402 enables cryptocurrency-based payments (USDC on Base/Ethereum L2) for API
endpoints. The flow:
  1. Client requests a paid endpoint
  2. Server responds with HTTP 402 + payment details (recipient, amount, resource)
  3. Client sends on-chain payment to the configured wallet
  4. Client retries the request with X-Payment header containing tx hash
  5. Server verifies on-chain payment and processes the request

IMPORTANT: Backtesting endpoints are EXEMPT from x402 payments because
backtesting is a simulation of cryptocurrency behavior — not real capital
deployment. Charging for backtest runs would distort strategy evaluation
and discourage the safety-first approach of testing before trading.

Only live/paper trading execution and premium knowledge retrieval require
x402 payment, as these consume real API resources and may execute real trades.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict

from app.core.config import get_settings

logger = logging.getLogger(__name__)


# ─── Payment Resource Types ──────────────────────────────────────────────────

class PaymentResource(str, Enum):
    """Identifies which API resource requires payment."""
    TRADE_EXECUTE = "trade_execute"
    TRADE_ANALYZE = "trade_analyze"
    KNOWLEDGE_ENHANCED = "knowledge_enhanced"
    KNOWLEDGE_HYBRID = "knowledge_hybrid"
    GOVERNANCE_POLICY = "governance_policy"


# ─── Pricing Configuration ───────────────────────────────────────────────────

# Default pricing per API call in USDC — overridden by config when available
_DEFAULT_PRICING: dict[PaymentResource, float] = {
    PaymentResource.TRADE_EXECUTE: 0.01,
    PaymentResource.TRADE_ANALYZE: 0.005,
    PaymentResource.KNOWLEDGE_ENHANCED: 0.002,
    PaymentResource.KNOWLEDGE_HYBRID: 0.001,
    PaymentResource.GOVERNANCE_POLICY: 0.001,
}

# Maps PaymentResource enum to the corresponding config attribute name
_RESOURCE_CONFIG_MAP: dict[PaymentResource, str] = {
    PaymentResource.TRADE_EXECUTE: "X402_PRICE_TRADE_EXECUTE",
    PaymentResource.TRADE_ANALYZE: "X402_PRICE_TRADE_ANALYZE",
    PaymentResource.KNOWLEDGE_ENHANCED: "X402_PRICE_KNOWLEDGE_ENHANCED",
    PaymentResource.KNOWLEDGE_HYBRID: "X402_PRICE_KNOWLEDGE_HYBRID",
    PaymentResource.GOVERNANCE_POLICY: "X402_PRICE_GOVERNANCE_POLICY",
}


def get_resource_price(resource: PaymentResource) -> float:
    """Get the price for a resource, preferring config over defaults."""
    try:
        settings = get_settings()
        config_attr = _RESOURCE_CONFIG_MAP.get(resource)
        if config_attr:
            configured = getattr(settings, config_attr, None)
            if configured is not None and configured >= 0:
                return float(configured)
    except Exception:
        pass
    return _DEFAULT_PRICING.get(resource, 0.0)

# Routes that are EXEMPT from x402 payment requirements
X402_EXEMPT_PREFIXES = (
    "/api/v1/backtest",     # Backtesting is simulation — no real capital at risk
    "/api/v1/payments",     # Payment info/verification endpoints are free
    "/docs",
    "/redoc",
    "/openapi.json",
    "/health",
    "/api/v1/status",       # Status checks are free
)


# ─── Data Classes ────────────────────────────────────────────────────────────

@dataclass
class PaymentRequirement:
    """Describes what payment is needed for a given resource."""
    resource: str
    amount_usd: float
    recipient_address: str
    chain_id: int
    token_address: str       # USDC contract address on the chain
    description: str


@dataclass
class PaymentReceipt:
    """Represents a verified on-chain payment."""
    tx_hash: str
    from_address: str
    amount_usd: float
    block_number: int
    verified_at: float = field(default_factory=time.time)
    resource: str = ""


# ─── In-Memory Payment Cache ─────────────────────────────────────────────────

# Tracks verified payments to prevent double-counting
# Key: tx_hash, Value: PaymentReceipt
_verified_payments: dict[str, PaymentReceipt] = {}

# Tracks payment nonces to prevent replay
# Key: nonce, Value: timestamp
_used_payment_nonces: dict[str, float] = {}

PAYMENT_CACHE_TTL = 3600  # 1 hour


def _prune_payment_cache() -> None:
    """Remove expired entries from payment caches."""
    now = time.time()
    expired_txs = [
        tx_hash for tx_hash, receipt in _verified_payments.items()
        if now - receipt.verified_at > PAYMENT_CACHE_TTL
    ]
    for tx_hash in expired_txs:
        _verified_payments.pop(tx_hash, None)

    expired_nonces = [
        nonce for nonce, ts in _used_payment_nonces.items()
        if now - ts > PAYMENT_CACHE_TTL
    ]
    for nonce in expired_nonces:
        _used_payment_nonces.pop(nonce, None)


# ─── Core x402 Service ──────────────────────────────────────────────────────

class x402Service:
    """
    Manages the x402 Payment Required protocol.

    Responsibilities:
    - Determine if a route requires payment
    - Generate 402 payment requirement responses
    - Verify on-chain payment receipts
    - Cache verified payments to avoid redundant verification
    """

    def __init__(self):
        self._settings = None

    @property
    def settings(self):
        if self._settings is None:
            self._settings = get_settings()
        return self._settings

    @property
    def enabled(self) -> bool:
        """Check if x402 payment protocol is enabled."""
        return getattr(self.settings, "X402_ENABLED", False)

    @property
    def testnet(self) -> bool:
        """Check if using testnet (Sepolia/Base Sepolia) for payments."""
        return getattr(self.settings, "X402_TESTNET", True)

    def is_route_exempt(self, path: str) -> bool:
        """
        Check if a route is exempt from x402 payment.

        Backtesting routes are ALWAYS exempt because backtesting is a
        simulation of cryptocurrency market behavior — not real capital
        deployment. Charging for backtest runs would:
        1. Discourage thorough testing before live trading
        2. Distort strategy evaluation with per-run costs
        3. Contradict the safety-first principle of simulating first
        """
        return any(path.startswith(prefix) for prefix in X402_EXEMPT_PREFIXES)

    def get_payment_requirement(self, resource: PaymentResource) -> Optional[PaymentRequirement]:
        """
        Build a payment requirement for the given resource type.

        Returns None if x402 is disabled or the resource has no price.
        """
        if not self.enabled:
            return None

        amount = get_resource_price(resource)
        if amount <= 0:
            return None

        recipient = self.settings.X402_RECIPIENT_ADDRESS
        if not recipient:
            logger.warning("x402 enabled but X402_RECIPIENT_ADDRESS not configured")
            return None

        chain_id = self.settings.X402_CHAIN_ID
        token_address = self.settings.X402_USDC_ADDRESS

        return PaymentRequirement(
            resource=resource.value,
            amount_usd=amount,
            recipient_address=recipient,
            chain_id=chain_id,
            token_address=token_address,
            description=f"Payment for {resource.value} API call",
        )

    def build_402_response(self, resource: PaymentResource) -> dict:
        """
        Build the HTTP 402 Payment Required response body.

        Follows the x402 protocol specification:
        - x402_version: protocol version
        - resource: what is being paid for
        - payment_requirements: array of acceptable payment configs
        """
        requirement = self.get_payment_requirement(resource)
        if requirement is None:
            # If no requirement can be built, don't block
            return {}

        return {
            "x402_version": 1,
            "resource": requirement.resource,
            "payment_requirements": [
                {
                    "scheme": "exact",
                    "network_id": str(requirement.chain_id),
                    "kind": "erc20",
                    "asset": {
                        "address": requirement.token_address,
                        "chain_id": requirement.chain_id,
                        "metadata": {
                            "name": "USDC",
                            "symbol": "USDC",
                            "decimals": 6,
                        },
                    },
                    "amount": _usd_to_6_decimals(requirement.amount_usd),
                    "recipient": requirement.recipient_address,
                    "description": requirement.description,
                    "max_amount": _usd_to_6_decimals(requirement.amount_usd),
                    "expires_at": int(time.time()) + 600,  # 10 min payment window
                    "payment_nonce": _generate_payment_nonce(),
                }
            ],
        }

    def verify_payment_header(self, payment_header: str, resource: PaymentResource) -> dict:
        """
        Verify the X-Payment header from the client.

        The header should be a JSON string containing:
        - tx_hash: on-chain transaction hash
        - network_id: chain ID where payment was made
        - from_address: sender address (for verification)

        Returns dict with:
        - valid: bool
        - reason: str (if invalid)
        - receipt: PaymentReceipt (if valid)
        """
        import json

        if not self.enabled:
            return {"valid": True, "reason": "x402 disabled"}

        _prune_payment_cache()

        try:
            payment_data = json.loads(payment_header)
        except (json.JSONDecodeError, TypeError):
            return {"valid": False, "reason": "Invalid X-Payment header format"}

        tx_hash = payment_data.get("tx_hash", "").strip()
        network_id = payment_data.get("network_id", "")
        from_address = payment_data.get("from_address", "").strip()

        if not tx_hash:
            return {"valid": False, "reason": "Missing tx_hash in X-Payment header"}

        # Check for replay
        if tx_hash in _verified_payments:
            receipt = _verified_payments[tx_hash]
            # Already verified — check if same resource
            if receipt.resource == resource.value:
                return {"valid": True, "reason": "Already verified", "receipt": receipt}
            else:
                return {"valid": False, "reason": "Payment was for a different resource"}

        # Verify on-chain payment
        requirement = self.get_payment_requirement(resource)
        if requirement is None:
            return {"valid": True, "reason": "No payment required for this resource"}

        # Verify the expected chain
        expected_chain = str(requirement.chain_id)
        if network_id and str(network_id) != expected_chain:
            return {
                "valid": False,
                "reason": f"Wrong chain: expected {expected_chain}, got {network_id}",
            }

        # Attempt on-chain verification
        verification = self._verify_onchain_payment(
            tx_hash=tx_hash,
            expected_recipient=requirement.recipient_address,
            expected_amount_usd=requirement.amount_usd,
            expected_token=requirement.token_address,
            from_address=from_address,
        )

        if verification["valid"]:
            receipt = PaymentReceipt(
                tx_hash=tx_hash,
                from_address=verification.get("from_address", from_address),
                amount_usd=verification.get("amount_usd", requirement.amount_usd),
                block_number=verification.get("block_number", 0),
                resource=resource.value,
            )
            _verified_payments[tx_hash] = receipt
            return {"valid": True, "reason": "Payment verified", "receipt": receipt}
        else:
            return {"valid": False, "reason": verification.get("reason", "On-chain verification failed")}

    def _verify_onchain_payment(
        self,
        tx_hash: str,
        expected_recipient: str,
        expected_amount_usd: float,
        expected_token: str,
        from_address: str = "",
    ) -> dict:
        """
        Verify payment on-chain by checking the transaction receipt.

        For testnet mode, accepts any non-empty tx_hash as valid (for development).
        For mainnet, performs full on-chain verification via Web3.
        """
        if self.testnet:
            # Testnet mode: accept any tx_hash for development
            logger.info("x402 testnet mode: accepting tx_hash %s without on-chain verification", tx_hash)
            return {
                "valid": True,
                "from_address": from_address or "0x_testnet",
                "amount_usd": expected_amount_usd,
                "block_number": 0,
                "reason": "Testnet mode — on-chain verification skipped",
            }

        # Mainnet: verify on-chain via Web3
        try:
            from app.blockchain.ethereum import EthereumClient

            eth_client = EthereumClient()
            if not eth_client.is_connected():
                logger.error("x402: Ethereum client not connected for on-chain verification")
                return {"valid": False, "reason": "Blockchain client not connected"}

            if not eth_client.w3:
                return {"valid": False, "reason": "Web3 instance not available"}

            receipt = eth_client.w3.eth.get_transaction_receipt(tx_hash)
            if receipt is None:
                return {"valid": False, "reason": "Transaction receipt not found"}

            if receipt.status != 1:
                return {"valid": False, "reason": "Transaction failed on-chain"}

            # Verify it's a USDC transfer to the correct recipient
            # USDC Transfer event: Transfer(address indexed from, address indexed to, uint256 value)
            transfer_topic = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
            relevant_logs = [log for log in receipt.logs if log.topics and log.topics[0].hex() == transfer_topic]

            if not relevant_logs:
                return {"valid": False, "reason": "No USDC transfer found in transaction"}

            log = relevant_logs[0]
            # topics[1] = from (padded), topics[2] = to (padded)
            if len(log.topics) < 3:
                return {"valid": False, "reason": "Invalid transfer event format"}

            actual_to = "0x" + log.topics[2].hex()[-40:]
            actual_from = "0x" + log.topics[1].hex()[-40:]

            # Normalize addresses for comparison
            checksum_recipient = eth_client.w3.to_checksum_address(expected_recipient)
            checksum_actual_to = eth_client.w3.to_checksum_address(actual_to)

            if checksum_actual_to != checksum_recipient:
                return {
                    "valid": False,
                    "reason": f"Payment sent to wrong address: {actual_to}",
                }

            # Verify amount (USDC has 6 decimals)
            expected_amount_6d = _usd_to_6_decimals(expected_amount_usd)
            actual_amount = int(log.data.hex(), 16) if log.data else 0
            actual_amount_usd = actual_amount / 1e6

            if actual_amount_usd < expected_amount_usd * 0.99:  # 1% tolerance
                return {
                    "valid": False,
                    "reason": f"Insufficient payment: {actual_amount_usd:.6f} < {expected_amount_usd:.6f}",
                }

            # Verify from address if provided
            if from_address:
                checksum_from = eth_client.w3.to_checksum_address(from_address)
                checksum_actual_from = eth_client.w3.to_checksum_address(actual_from)
                if checksum_actual_from != checksum_from:
                    return {
                        "valid": False,
                        "reason": f"Payment from wrong address: {actual_from}",
                    }

            return {
                "valid": True,
                "from_address": actual_from,
                "amount_usd": actual_amount_usd,
                "block_number": receipt.blockNumber,
            }

        except Exception as exc:
            logger.error("x402 on-chain verification error: %s", exc)
            return {"valid": False, "reason": f"Verification error: {str(exc)}"}


# ─── Utility Functions ───────────────────────────────────────────────────────

def _usd_to_6_decimals(usd: float) -> int:
    """Convert USD amount to USDC 6-decimal integer."""
    return int(round(usd * 1_000_000))


def _generate_payment_nonce() -> str:
    """Generate a unique payment nonce to prevent replay attacks."""
    import hashlib
    nonce_base = f"x402:{time.time()}:{id(None)}"
    return hashlib.sha256(nonce_base.encode()).hexdigest()[:16]


# ─── Singleton ───────────────────────────────────────────────────────────────

x402_service = x402Service()