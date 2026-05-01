import hashlib
import json
import logging
import os
import re
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from eth_account import Account
from eth_account.messages import encode_defunct

from app.core.config import get_settings
from app.blockchain.ethereum import EthereumClient, SmartContractManager

logger = logging.getLogger(__name__)

_GOVERNANCE_DATA_DIR = os.getenv("GOVERNANCE_DATA_DIR", "/tmp/governance_data")


SEMANTIC_SIGNAL_PATTERNS = [
    r"\bactivation signal\b",
    r"\bphase transition\b",
    r"\bstaged execution\b",
    r"\bdelayed activation\b",
    r"\bselective targeting\b",
    r"\bcross[- ]chain transfer\b",
    r"\bdrain liquidity\b",
    r"\bgovernance takeover\b",
    r"\bcoordinated action\b",
]


@dataclass
class AgentProfile:
    agent_id: str
    did: str
    public_key: str
    role: str = "AGENT_ROLE"
    active: bool = True


@dataclass
class AgentPolicy:
    max_trades_per_hour: int = 20
    max_notional_usd: float = 2500.0
    allowed_chains: list[str] = None
    allowed_pairs: list[str] = None
    block_semantic_signals: bool = True

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["allowed_chains"] = self.allowed_chains or ["ethereum", "solana"]
        data["allowed_pairs"] = self.allowed_pairs or ["ETH/USDT", "SOL/USDT", "BTC/USDT", "ETH/USDC"]
        return data


class AgentGovernanceService:
    """
    Lightweight off-chain governance module inspired by:
    - Agent registry + policy enforcer + activity logger
    - Semantic signalling risk checks before execution
    """

    def __init__(self) -> None:
        self._agents: dict[str, AgentProfile] = {}
        self._policies: dict[str, AgentPolicy] = {}
        self._activity_log: list[dict[str, Any]] = []
        self._trade_windows: dict[str, deque[float]] = defaultdict(deque)
        self._last_event_hash = "GENESIS"
        self._multisig_approvals: dict[str, set[str]] = defaultdict(set)
        self._eth_client = EthereumClient()
        settings = get_settings()
        self._contracts = SmartContractManager(
            self._eth_client,
            bill_registry_address=settings.BILL_REGISTRY_ADDRESS,
            identity_registry_address=settings.IDENTITY_REGISTRY_ADDRESS,
            activity_logger_address=settings.ACTIVITY_LOGGER_ADDRESS,
            policy_enforcer_address=settings.POLICY_ENFORCER_ADDRESS,
            dispute_resolver_address=settings.DISPUTE_RESOLVER_ADDRESS,
        )

        self._load_from_disk()

        self.register_agent(
            agent_id="default-trader",
            did="did:ethr:polygon:default-trader",
            public_key="local-dev-key",
            role="AGENT_ROLE",
        )

    # ── Persistence helpers ────────────────────────────────────────
    @property
    def _state_file(self) -> Path:
        return Path(_GOVERNANCE_DATA_DIR) / "governance_state.json"

    def _persist_to_disk(self) -> None:
        """Atomically write current state so it survives restarts."""
        try:
            self._state_file.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._state_file.with_suffix(".tmp")
            state = {
                "last_event_hash": self._last_event_hash,
                "activity_log": self._activity_log[-500:],  # keep last 500
            }
            tmp.write_text(json.dumps(state, default=str))
            tmp.replace(self._state_file)
        except Exception as exc:
            logger.error("Failed to persist governance state: %s", exc)

    def _load_from_disk(self) -> None:
        """Restore state from previous run (if any)."""
        try:
            if self._state_file.exists():
                state = json.loads(self._state_file.read_text())
                self._last_event_hash = state.get("last_event_hash", "GENESIS")
                self._activity_log = state.get("activity_log", [])
                logger.info(
                    "Restored governance state: %d events, last_hash=%s",
                    len(self._activity_log),
                    self._last_event_hash[:16],
                )
        except Exception as exc:
            logger.warning("Could not load governance state from disk: %s", exc)

    def register_agent(self, agent_id: str, did: str, public_key: str, role: str = "AGENT_ROLE") -> dict[str, Any]:
        profile = AgentProfile(agent_id=agent_id, did=did, public_key=public_key, role=role)
        self._agents[agent_id] = profile
        self._policies.setdefault(agent_id, AgentPolicy())
        return asdict(profile)

    def list_agents(self) -> list[dict[str, Any]]:
        return [asdict(agent) for agent in self._agents.values()]

    def get_policy(self, agent_id: str) -> dict[str, Any]:
        policy = self._policies.get(agent_id)
        if not policy:
            policy = AgentPolicy()
            self._policies[agent_id] = policy
        return policy.as_dict()

    def update_policy(self, agent_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        current = self.get_policy(agent_id)
        merged = {**current, **updates}
        self._policies[agent_id] = AgentPolicy(
            max_trades_per_hour=int(merged["max_trades_per_hour"]),
            max_notional_usd=float(merged["max_notional_usd"]),
            allowed_chains=list(merged["allowed_chains"]),
            allowed_pairs=list(merged["allowed_pairs"]),
            block_semantic_signals=bool(merged["block_semantic_signals"]),
        )
        return self._policies[agent_id].as_dict()

    def _parse_signers(self) -> list[str]:
        raw = get_settings().GOVERNANCE_SIGNERS.strip()
        if not raw:
            return []
        return [s.strip() for s in raw.split(",") if s.strip()]

    def approve_policy_update(self, proposal_id: str, signer_id: str) -> dict[str, Any]:
        signers = set(self._parse_signers())
        if signers and signer_id not in signers:
            return {"approved": False, "reason": f"Signer '{signer_id}' is not in GOVERNANCE_SIGNERS."}
        self._multisig_approvals[proposal_id].add(signer_id)
        threshold = max(1, get_settings().GOVERNANCE_MULTISIG_THRESHOLD)
        approval_count = len(self._multisig_approvals[proposal_id])
        return {
            "approved": approval_count >= threshold,
            "approval_count": approval_count,
            "threshold": threshold,
            "approvers": sorted(self._multisig_approvals[proposal_id]),
        }

    def verify_agent_signature(
        self,
        *,
        agent_id: str,
        did: str,
        request_nonce: str,
        request_timestamp: int,
        token_pair: str,
        chain: str,
        max_position_usd: float,
        prompt: str,
        signature: str,
    ) -> dict[str, Any]:
        profile = self._agents.get(agent_id)
        if not profile:
            return {"valid": False, "reason": f"Unknown agent_id '{agent_id}'."}
        if profile.did != did:
            return {"valid": False, "reason": "DID does not match registered agent DID."}

        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        message = (
            f"{agent_id}:{did}:{request_nonce}:{request_timestamp}:"
            f"{token_pair}:{chain}:{max_position_usd:.8f}:{prompt_hash}"
        )
        try:
            recovered = Account.recover_message(encode_defunct(text=message), signature=signature)
        except Exception as exc:
            return {"valid": False, "reason": f"Invalid signature format: {exc}"}

        expected = profile.public_key.lower()
        if recovered.lower() != expected:
            return {
                "valid": False,
                "reason": f"Recovered signer {recovered} does not match registered key {profile.public_key}.",
            }

        return {"valid": True, "signed_payload": message, "recovered": recovered}

    def evaluate_semantic_signal_risk(self, prompt: str) -> dict[str, Any]:
        prompt_norm = prompt.lower()
        matches = []
        for pattern in SEMANTIC_SIGNAL_PATTERNS:
            if re.search(pattern, prompt_norm):
                matches.append(pattern.replace("\\b", ""))
        return {
            "score": len(matches),
            "matched_patterns": matches,
        }

    def pre_trade_check(
        self,
        *,
        agent_id: str,
        token_pair: str,
        chain: str,
        max_position_usd: float,
        prompt: str,
        semantic_threshold: int,
    ) -> dict[str, Any]:
        if agent_id not in self._agents:
            return {"allowed": False, "reasons": [f"Agent '{agent_id}' is not registered."], "policy": None}
        if not self._agents[agent_id].active:
            return {"allowed": False, "reasons": [f"Agent '{agent_id}' is paused."], "policy": None}

        policy = self.get_policy(agent_id)
        reasons: list[str] = []

        if chain not in policy["allowed_chains"]:
            reasons.append(f"Chain '{chain}' not in allowed_chains.")
        if token_pair not in policy["allowed_pairs"]:
            reasons.append(f"Token pair '{token_pair}' not in allowed_pairs.")
        if max_position_usd > policy["max_notional_usd"]:
            reasons.append(
                f"Requested max_position_usd={max_position_usd:.2f} exceeds policy limit "
                f"{policy['max_notional_usd']:.2f}."
            )

        now_ts = datetime.now(timezone.utc).timestamp()
        window = self._trade_windows[agent_id]
        while window and now_ts - window[0] > 3600:
            window.popleft()
        if len(window) >= policy["max_trades_per_hour"]:
            reasons.append("Trade frequency limit exceeded for current 1h window.")

        semantic = self.evaluate_semantic_signal_risk(prompt)
        if (
            policy["block_semantic_signals"]
            and semantic["score"] >= semantic_threshold
        ):
            reasons.append(
                "Prompt contains high-risk semantic coordination cues "
                f"(score={semantic['score']}, threshold={semantic_threshold})."
            )

        return {
            "allowed": len(reasons) == 0,
            "reasons": reasons,
            "policy": policy,
            "semantic_signal": semantic,
        }

    def record_execution(
        self,
        *,
        agent_id: str,
        token_pair: str,
        chain: str,
        action: str,
        amount: float,
        approved: bool,
        reasoning: str,
        risk_score: float,
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        self._trade_windows[agent_id].append(datetime.now(timezone.utc).timestamp())
        payload = {
            "timestamp": now,
            "agent_id": agent_id,
            "token_pair": token_pair,
            "chain": chain,
            "action": action,
            "amount": amount,
            "approved": approved,
            "reasoning": reasoning,
            "risk_score": risk_score,
        }
        payload_json = json.dumps(payload, sort_keys=True)
        current_hash = hashlib.sha256(f"{self._last_event_hash}:{payload_json}".encode("utf-8")).hexdigest()
        event = {
            **payload,
            "prev_hash": self._last_event_hash,
            "event_hash": current_hash,
        }
        self._activity_log.append(event)
        self._last_event_hash = current_hash
        onchain_tx = None
        settings = get_settings()
        if settings.ONCHAIN_AUDIT_ENABLED and self._eth_client.is_connected():
            onchain_tx = self._contracts.anchor_activity(
                agent_id=agent_id,
                event_hash=current_hash,
            )
        if onchain_tx:
            event["onchain_audit_tx"] = onchain_tx
        self._persist_to_disk()
        return event

    def get_activity_logs(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._activity_log[-max(1, limit):]


governance_service = AgentGovernanceService()
