"""
Claw402 x402 Auto-Pay Transport
================================
A custom httpx transport that wraps every outbound request to Claw402's API.

Flow per LLM call:
  1. Send request to api.claw402.com
  2. If 402 → parse payment_requirements from body
  3. Sign & submit USDC transfer on Base via eth_account + web3
  4. Retry original request with X-Payment header containing tx_hash
  5. Return successful response to caller

This makes Claw402 transparent to LangChain — it looks like any OpenAI-
compatible provider. The x402 handshake happens entirely inside the transport.

Configuration (backend/.env):
  CLAW402_BASE_URL=https://api.claw402.com/v1
  CLAW402_MODEL=claude-opus-4-5
  CLAW402_WALLET_PRIVATE_KEY=0x<hot_wallet_private_key>
  CLAW402_USDC_ADDRESS=0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913

WARNING:
  CLAW402_WALLET_PRIVATE_KEY should belong to a dedicated hot wallet.
  Only load it with enough USDC for your expected usage. Never reuse a
  high-value wallet for automated transaction signing.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# Max USDC (USD) we'll auto-pay per single LLM request — safety ceiling
MAX_AUTO_PAY_USD = 1.0


class Claw402Transport(httpx.BaseTransport):
    """
    httpx transport that intercepts HTTP 402 responses from Claw402,
    submits a USDC payment on Base, then retries the original request.
    """

    def __init__(self, wrapped: httpx.BaseTransport):
        self._wrapped = wrapped

    def handle_request(self, request: httpx.Request) -> httpx.Response:  # type: ignore[override]
        # First attempt — no payment header
        response = self._wrapped.handle_request(request)

        if response.status_code != 402:
            return response

        # Parse 402 body
        try:
            body = json.loads(response.content)
        except Exception:
            logger.warning("Claw402: 402 response body is not valid JSON — cannot auto-pay")
            return response

        reqs = body.get("payment_requirements", [])
        if not reqs:
            logger.warning("Claw402: 402 response has no payment_requirements")
            return response

        req = reqs[0]
        amount_raw: int = req.get("amount", 0)        # USDC 6-decimal integer
        recipient: str = req.get("recipient", "")
        network_id: str = str(req.get("network_id", "8453"))
        token_address: str = req.get("asset", {}).get("address", "")

        amount_usd = amount_raw / 1_000_000
        if amount_usd > MAX_AUTO_PAY_USD:
            logger.error(
                "Claw402: refusing auto-pay of $%.4f — exceeds safety ceiling $%.2f",
                amount_usd, MAX_AUTO_PAY_USD,
            )
            return response

        logger.info(
            "Claw402: auto-paying $%.4f USDC to %s on chain %s",
            amount_usd, recipient, network_id,
        )

        tx_hash = _submit_usdc_payment(
            recipient=recipient,
            amount_raw=amount_raw,
            token_address=token_address,
            chain_id=int(network_id),
        )

        if not tx_hash:
            logger.error("Claw402: payment submission failed — returning original 402")
            return response

        # Build X-Payment header per x402 spec
        payment_header = json.dumps({
            "tx_hash": tx_hash,
            "network_id": network_id,
            "from_address": _get_wallet_address(),
        })

        # Retry original request with payment proof
        retried = httpx.Request(
            method=request.method,
            url=request.url,
            headers={**dict(request.headers), "X-Payment": payment_header},
            content=request.content,
        )
        logger.info("Claw402: retrying request with tx_hash=%s", tx_hash[:18])
        return self._wrapped.handle_request(retried)


# ─── On-chain payment helpers ─────────────────────────────────────────────────

def _get_settings():
    from app.core.config import get_settings
    return get_settings()


def _get_wallet_address() -> str:
    """Derive wallet address from configured private key."""
    try:
        from eth_account import Account
        pk = _get_settings().CLAW402_WALLET_PRIVATE_KEY
        if not pk:
            return "0x0000000000000000000000000000000000000000"
        acct = Account.from_key(pk)
        return acct.address
    except Exception:
        return "0x0000000000000000000000000000000000000000"


def _submit_usdc_payment(
    recipient: str,
    amount_raw: int,
    token_address: str,
    chain_id: int,
) -> Optional[str]:
    """
    Submit an ERC-20 USDC transfer on Base and return the tx_hash.
    Returns None on failure.
    """
    settings = _get_settings()
    pk = settings.CLAW402_WALLET_PRIVATE_KEY

    if not pk:
        logger.warning(
            "Claw402: CLAW402_WALLET_PRIVATE_KEY not set — cannot auto-pay. "
            "Add your hot wallet key to .env to enable keyless x402 payments."
        )
        return None

    try:
        from web3 import Web3
        from eth_account import Account

        # Base mainnet RPC (falls back to public endpoint)
        rpc_url = settings.ETHEREUM_RPC_URL or "https://mainnet.base.org"
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not w3.is_connected():
            logger.error("Claw402: web3 not connected to %s", rpc_url)
            return None

        acct = Account.from_key(pk)

        # ERC-20 transfer ABI (transfer function only)
        erc20_abi = [
            {
                "name": "transfer",
                "type": "function",
                "inputs": [
                    {"name": "to", "type": "address"},
                    {"name": "amount", "type": "uint256"},
                ],
                "outputs": [{"name": "", "type": "bool"}],
                "stateMutability": "nonpayable",
            }
        ]

        usdc = w3.eth.contract(
            address=Web3.to_checksum_address(token_address or settings.CLAW402_USDC_ADDRESS),
            abi=erc20_abi,
        )

        nonce = w3.eth.get_transaction_count(acct.address)
        gas_price = w3.eth.gas_price

        tx = usdc.functions.transfer(
            Web3.to_checksum_address(recipient),
            amount_raw,
        ).build_transaction({
            "chainId": chain_id,
            "from": acct.address,
            "nonce": nonce,
            "gasPrice": gas_price,
            "gas": 80_000,       # conservative upper bound for ERC-20 transfer
        })

        signed = w3.eth.account.sign_transaction(tx, pk)
        tx_hash_bytes = w3.eth.send_raw_transaction(signed.raw_transaction)
        tx_hash = tx_hash_bytes.hex()

        logger.info("Claw402: USDC transfer submitted — tx_hash=%s", tx_hash)

        # Wait up to 30 s for confirmation
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)
        if receipt.status != 1:
            logger.error("Claw402: USDC transfer reverted — tx_hash=%s", tx_hash)
            return None

        logger.info(
            "Claw402: USDC transfer confirmed in block %d", receipt.blockNumber
        )
        return tx_hash

    except Exception as exc:
        logger.error("Claw402: payment submission error: %s", exc)
        return None


# ─── Public factory ───────────────────────────────────────────────────────────

def build_claw402_http_client() -> httpx.Client:
    """
    Build an httpx.Client with the Claw402 auto-pay transport injected.
    Pass this as http_client= to ChatOpenAI to enable keyless x402 payments.
    """
    inner = httpx.HTTPTransport(retries=1)
    transport = Claw402Transport(wrapped=inner)
    return httpx.Client(transport=transport, timeout=120.0)
