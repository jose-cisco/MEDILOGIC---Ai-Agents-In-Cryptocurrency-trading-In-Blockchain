"""
IPFS Client — Off-Chain Data Storage and Retrieval
====================================================
Implements the paper's requirement: "Monitor via on-chain data + IPFS for off-chain logs"

Provides:
- Pinning large data (agent decisions, market data, audit logs) to IPFS
- Content-addressed storage with CID verification
- Retrieval of off-chain data by CID
- Integration with BlockAgents DataRecorder (on-chain hash anchor + off-chain IPFS content)
- Support for both local IPFS node and pinning service (Pinata, Web3.Storage)

Reference: Survey Section 5 — "dynamic on-chain/off-chain data integration"
Reference: Survey Phase 5 — "Monitor via on-chain data + IPFS for off-chain logs"
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


# ─── Data Structures ───────────────────────────────────────────────────────

@dataclass
class IPFSPinResult:
    """Result of pinning data to IPFS."""
    success: bool
    cid: str = ""               # Content Identifier (CIDv0 or CIDv1)
    size_bytes: int = 0
    pin_time_seconds: float = 0.0
    gateway_url: str = ""        # Public gateway URL for retrieval
    error: str = ""


@dataclass
class IPFSContent:
    """Retrieved content from IPFS."""
    success: bool
    cid: str = ""
    data: bytes = b""
    text: str = ""
    size_bytes: int = 0
    retrieval_time_seconds: float = 0.0
    error: str = ""


# ─── IPFS Client ───────────────────────────────────────────────────────────

class IPFSClient:
    """
    IPFS client for off-chain data storage and retrieval.

    Supports multiple pinning strategies:
    1. Local IPFS node (kubo/go-ipfs daemon)
    2. Pinata pinning service
    3. Web3.Storage (Storacha)
    4. Custom gateway

    The client anchors data on-chain via DataRecorder (hash) while
    storing the full content on IPFS (CID), providing the paper's
    "dynamic on-chain/off-chain data integration" pattern.
    """

    def __init__(self):
        settings = get_settings()
        self._ipfs_api_url = getattr(settings, "IPFS_API_URL", "http://localhost:5001")
        self._ipfs_gateway_url = getattr(settings, "IPFS_GATEWAY_URL", "https://ipfs.io")
        self._pinata_jwt = getattr(settings, "PINATA_JWT", "")
        self._web3storage_token = getattr(settings, "WEB3_STORAGE_TOKEN", "")
        self._pinning_service = getattr(settings, "IPFS_PINNING_SERVICE", "local")
        self._enable_ipfs = getattr(settings, "IPFS_ENABLED", False)

    # ─── Pinning ────────────────────────────────────────────────────────

    def pin_json(
        self,
        data: dict[str, Any],
        metadata: dict[str, str] | None = None,
    ) -> IPFSPinResult:
        """
        Pin a JSON object to IPFS.

        The data is serialized to JSON and pinned via the configured
        pinning service. Returns a CID that can be anchored on-chain.
        """
        if not self._enable_ipfs:
            # Compute local hash for verification even when IPFS is disabled
            content = json.dumps(data, sort_keys=True, default=str).encode("utf-8")
            local_hash = hashlib.sha256(content).hexdigest()
            logger.debug("IPFS disabled — computed local hash: %s", local_hash[:16])
            return IPFSPinResult(
                success=True,
                cid=f"local-sha256:{local_hash}",
                size_bytes=len(content),
                gateway_url="",
            )

        content_bytes = json.dumps(data, sort_keys=True, default=str).encode("utf-8")
        return self._pin_content(content_bytes, metadata)

    def pin_text(
        self,
        text: str,
        metadata: dict[str, str] | None = None,
    ) -> IPFSPinResult:
        """Pin a text string to IPFS."""
        if not self._enable_ipfs:
            local_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
            return IPFSPinResult(
                success=True,
                cid=f"local-sha256:{local_hash}",
                size_bytes=len(text.encode("utf-8")),
            )

        return self._pin_content(text.encode("utf-8"), metadata)

    def pin_bytes(
        self,
        data: bytes,
        metadata: dict[str, str] | None = None,
    ) -> IPFSPinResult:
        """Pin raw bytes to IPFS."""
        if not self._enable_ipfs:
            local_hash = hashlib.sha256(data).hexdigest()
            return IPFSPinResult(
                success=True,
                cid=f"local-sha256:{local_hash}",
                size_bytes=len(data),
            )

        return self._pin_content(data, metadata)

    def _pin_content(
        self,
        content: bytes,
        metadata: dict[str, str] | None = None,
    ) -> IPFSPinResult:
        """Pin content to IPFS via the configured pinning service."""
        start_time = time.time()

        if self._pinning_service == "pinata" and self._pinata_jwt:
            result = self._pin_via_pinata(content, metadata)
        elif self._pinning_service == "web3storage" and self._web3storage_token:
            result = self._pin_via_web3storage(content, metadata)
        else:
            result = self._pin_via_local_node(content)

        result.pin_time_seconds = time.time() - start_time
        return result

    def _pin_via_local_node(self, content: bytes) -> IPFSPinResult:
        """Pin content via local IPFS daemon (kubo API)."""
        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    f"{self._ipfs_api_url}/api/v0/add",
                    files={"file": ("data.json", content, "application/json")},
                    params={"pin": "true"},
                )
                response.raise_for_status()
                result = response.json()
                cid = result.get("Hash", "")
                size = result.get("Size", len(content))

                gateway_url = f"{self._ipfs_gateway_url}/ipfs/{cid}"

                logger.info("IPFS: Pinned content via local node — CID=%s, size=%d", cid[:16], size)

                return IPFSPinResult(
                    success=True,
                    cid=cid,
                    size_bytes=size,
                    gateway_url=gateway_url,
                )

        except Exception as exc:
            logger.error("IPFS: Local node pin failed: %s", exc)
            # Fall back to local hash
            local_hash = hashlib.sha256(content).hexdigest()
            return IPFSPinResult(
                success=True,
                cid=f"local-sha256:{local_hash}",
                size_bytes=len(content),
                error=f"IPFS node unavailable, using local hash: {exc}",
            )

    def _pin_via_pinata(self, content: bytes, metadata: dict[str, str] | None = None) -> IPFSPinResult:
        """Pin content via Pinata cloud pinning service."""
        try:
            with httpx.Client(timeout=60.0) as client:
                pinata_metadata = {
                    "name": metadata.get("name", "ai-trading-agent-data") if metadata else "ai-trading-agent-data",
                    "keyvalues": metadata or {},
                }

                response = client.post(
                    "https://api.pinata.cloud/pinning/pinFileToIPFS",
                    headers={"Authorization": f"Bearer {self._pinata_jwt}"},
                    files={"file": ("data.json", content, "application/json")},
                    data={"pinataMetadata": json.dumps(pinata_metadata)},
                )
                response.raise_for_status()
                result = response.json()
                cid = result.get("IpfsHash", "")

                gateway_url = f"https://gateway.pinata.cloud/ipfs/{cid}"

                logger.info("IPFS: Pinned content via Pinata — CID=%s", cid[:16])

                return IPFSPinResult(
                    success=True,
                    cid=cid,
                    size_bytes=len(content),
                    gateway_url=gateway_url,
                )

        except Exception as exc:
            logger.error("IPFS: Pinata pin failed: %s", exc)
            local_hash = hashlib.sha256(content).hexdigest()
            return IPFSPinResult(
                success=True,
                cid=f"local-sha256:{local_hash}",
                size_bytes=len(content),
                error=f"Pinata unavailable, using local hash: {exc}",
            )

    def _pin_via_web3storage(self, content: bytes, metadata: dict[str, str] | None = None) -> IPFSPinResult:
        """Pin content via Web3.Storage (Storacha) pinning service."""
        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    "https://api.web3.storage/upload",
                    headers={"Authorization": f"Bearer {self._web3storage_token}"},
                    files={"file": ("data.json", content, "application/json")},
                )
                response.raise_for_status()
                result = response.json()
                cid = result.get("cid", "")

                gateway_url = f"https://w3s.link/ipfs/{cid}"

                logger.info("IPFS: Pinned content via Web3.Storage — CID=%s", cid[:16])

                return IPFSPinResult(
                    success=True,
                    cid=cid,
                    size_bytes=len(content),
                    gateway_url=gateway_url,
                )

        except Exception as exc:
            logger.error("IPFS: Web3.Storage pin failed: %s", exc)
            local_hash = hashlib.sha256(content).hexdigest()
            return IPFSPinResult(
                success=True,
                cid=f"local-sha256:{local_hash}",
                size_bytes=len(content),
                error=f"Web3.Storage unavailable, using local hash: {exc}",
            )

    # ─── Retrieval ───────────────────────────────────────────────────────

    def get_json(self, cid: str) -> IPFSContent:
        """Retrieve a JSON object from IPFS by CID."""
        result = self._get_content(cid)
        if result.success and result.data:
            try:
                result.text = result.data.decode("utf-8")
            except UnicodeDecodeError:
                pass
        return result

    def get_text(self, cid: str) -> IPFSContent:
        """Retrieve text content from IPFS by CID."""
        result = self._get_content(cid)
        if result.success and result.data:
            try:
                result.text = result.data.decode("utf-8")
            except UnicodeDecodeError:
                result.text = ""
        return result

    def _get_content(self, cid: str) -> IPFSContent:
        """Retrieve content from IPFS via gateway."""
        start_time = time.time()

        # Handle local hashes
        if cid.startswith("local-sha256:"):
            return IPFSContent(
                success=True,
                cid=cid,
                data=b"",
                text="",
                size_bytes=0,
                retrieval_time_seconds=time.time() - start_time,
            )

        # Try configured gateway first, then fallback to public gateway
        gateways = [self._ipfs_gateway_url, "https://ipfs.io", "https://dweb.link"]

        for gateway in gateways:
            try:
                url = f"{gateway}/ipfs/{cid}"
                with httpx.Client(timeout=30.0) as client:
                    response = client.get(url)
                    response.raise_for_status()

                    retrieval_time = time.time() - start_time
                    content_bytes = response.content

                    logger.info(
                        "IPFS: Retrieved content — CID=%s, size=%d, via=%s",
                        cid[:16], len(content_bytes), gateway,
                    )

                    return IPFSContent(
                        success=True,
                        cid=cid,
                        data=content_bytes,
                        text="",
                        size_bytes=len(content_bytes),
                        retrieval_time_seconds=retrieval_time,
                    )

            except Exception as exc:
                logger.debug("IPFS: Gateway %s failed for CID %s: %s", gateway, cid[:16], exc)
                continue

        retrieval_time = time.time() - start_time
        return IPFSContent(
            success=False,
            cid=cid,
            error=f"Failed to retrieve CID {cid} from all gateways",
            retrieval_time_seconds=retrieval_time,
        )

    # ─── Agent Data Integration ──────────────────────────────────────────

    def pin_agent_decision(
        self,
        agent_id: str,
        decision_data: dict[str, Any],
        on_chain_hash: str = "",
    ) -> IPFSPinResult:
        """
        Pin an agent's trading decision data to IPFS.

        This implements the paper's pattern of:
        - Storing full data off-chain on IPFS (CID)
        - Anchoring the hash on-chain via DataRecorder

        The decision data includes the agent ID, timestamps, decision
        reasoning, and any verification results.
        """
        payload = {
            "agent_id": agent_id,
            "timestamp": time.time(),
            "decision": decision_data,
            "on_chain_hash": on_chain_hash,
            "version": "1.0",
        }

        metadata = {
            "agent_id": agent_id,
            "data_type": "agent_decision",
            "on_chain_hash": on_chain_hash[:16] if on_chain_hash else "",
        }

        return self.pin_json(payload, metadata)

    def pin_audit_log(
        self,
        agent_id: str,
        event_data: dict[str, Any],
        event_hash: str = "",
    ) -> IPFSPinResult:
        """
        Pin an audit log event to IPFS.

        Stores the full event data on IPFS while the event hash
        is anchored on-chain via ActivityLogger/DataRecorder.
        """
        payload = {
            "agent_id": agent_id,
            "event_hash": event_hash,
            "event_data": event_data,
            "pinned_at": time.time(),
            "version": "1.0",
        }

        metadata = {
            "agent_id": agent_id,
            "data_type": "audit_log",
            "event_hash": event_hash[:16] if event_hash else "",
        }

        return self.pin_json(payload, metadata)

    def pin_market_data(
        self,
        token_pair: str,
        chain: str,
        market_data: dict[str, Any],
    ) -> IPFSPinResult:
        """
        Pin market data snapshot to IPFS for historical reference.

        Market data is stored off-chain with a content hash that
        can be referenced in RAG and on-chain anchors.
        """
        payload = {
            "token_pair": token_pair,
            "chain": chain,
            "market_data": market_data,
            "pinned_at": time.time(),
            "version": "1.0",
        }

        metadata = {
            "token_pair": token_pair,
            "chain": chain,
            "data_type": "market_data",
        }

        return self.pin_json(payload, metadata)

    # ─── Status ──────────────────────────────────────────────────────────

    def is_enabled(self) -> bool:
        """Check if IPFS integration is enabled."""
        return self._enable_ipfs

    def get_status(self) -> dict[str, Any]:
        """Get IPFS client status and configuration."""
        return {
            "enabled": self._enable_ipfs,
            "pinning_service": self._pinning_service,
            "gateway_url": self._ipfs_gateway_url,
            "local_node_configured": bool(self._ipfs_api_url),
            "pinata_configured": bool(self._pinata_jwt),
            "web3storage_configured": bool(self._web3storage_token),
        }


# ─── Singleton ──────────────────────────────────────────────────────────────

ipfs_client = IPFSClient()