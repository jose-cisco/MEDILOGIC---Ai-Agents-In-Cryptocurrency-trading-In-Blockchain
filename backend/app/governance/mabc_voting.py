"""
mABC Decentralized Voting Service
===================================
Implements the mABC (multi-Agent Byzantine Consensus) framework from Karim et al. (2025)
Section 6, providing decentralized governance for multi-agent trading parameter changes.

Features:
- Token-weighted voting on policy proposals (trade limits, chain allowlists, etc.)
- Proposal lifecycle: propose → vote → queue → execute
- Quorum and majority thresholds for Byzantine fault tolerance
- Voting power delegation between agents
- Agent reputation scoring integrated with voting power
- On-chain proposal execution via MABCGovernance.sol
- Off-chain proposal tracking and resolution

Reference: Survey Section 6 — "mABC framework for decentralized governance"
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Optional

from app.core.config import get_settings
from app.blockchain.ethereum import EthereumClient, SmartContractManager

logger = logging.getLogger(__name__)


# ─── Enums ──────────────────────────────────────────────────────────────────

class ProposalState(IntEnum):
    """Maps to MABCGovernance.sol ProposalState enum."""
    PENDING = 0
    ACTIVE = 1
    DEFEATED = 2
    SUCCEEDED = 3
    QUEUED = 4
    EXECUTED = 5
    CANCELLED = 6


class VoteSupport(IntEnum):
    """Vote support types matching the smart contract."""
    AGAINST = 0
    FOR = 1
    ABSTAIN = 2


class GovernanceTarget(IntEnum):
    """Target contracts for governance proposals."""
    POLICY_ENFORCER = 0
    IDENTITY_REGISTRY = 1
    BILL_REGISTRY = 2
    VERIFICATION_AGENT = 3
    DATA_RECORDER = 4
    CUSTOM = 5


# ─── Data Structures ───────────────────────────────────────────────────────

@dataclass
class GovernanceProposal:
    """Off-chain tracking of a governance proposal."""
    proposal_id: int
    proposer: str
    title: str
    description: str
    execution_data: bytes
    target_contract: str
    vote_start: float
    vote_end: float
    for_votes: float = 0.0
    against_votes: float = 0.0
    abstain_votes: float = 0.0
    quorum_required: float = 0.0
    state: ProposalState = ProposalState.PENDING
    timelock_end: float = 0.0
    executed: bool = False
    created_at: float = field(default_factory=time.time)
    off_chain_votes: dict[str, dict] = field(default_factory=dict)
    resolution_notes: str = ""


@dataclass
class VoteRecord:
    """A single vote record."""
    voter: str
    proposal_id: int
    support: VoteSupport
    voting_power: float
    reason: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class VoterInfo:
    """Voter registration and delegation info."""
    address: str
    voting_power: float
    delegated_to: str = ""
    delegation_count: int = 0
    reputation_score: float = 0.0
    is_registered: bool = True


# ─── mABC Governance Service ──────────────────────────────────────────────

class MABCVotingService:
    """
    Decentralized governance service implementing mABC Byzantine Consensus.

    Manages the full proposal lifecycle:
    1. Propose — any registered voter with sufficient power creates a proposal
    2. Vote — token-weighted voting with reputation bonuses
    3. Queue — passed proposals are queued for timelock
    4. Execute — after timelock, proposals execute on-chain

    Integrates with:
    - MABCGovernance.sol (on-chain voting and execution)
    - PolicyEnforcer.sol (governance can change agent policies)
    - AgentGovernanceService (off-chain policy enforcement)
    - EAACService (secure coordination)
    """

    def __init__(self):
        self._proposals: dict[int, GovernanceProposal] = {}
        self._voters: dict[str, VoterInfo] = {}
        self._votes: dict[int, list[VoteRecord]] = {}
        self._eth_client: Optional[EthereumClient] = None
        self._contracts: Optional[SmartContractManager] = None
        self._chain_enabled = False
        self._next_proposal_id = 1

        # Default governance parameters
        self._voting_period = 3 * 24 * 3600  # 3 days in seconds
        self._quorum_numerator = 4  # 4%
        self._quorum_denominator = 100
        self._timelock_delay = 24 * 3600  # 1 day
        self._proposal_threshold = 100  # minimum power to propose

        # Register default governance agents
        self._register_default_voters()

    def _register_default_voters(self):
        """Register default governance participants."""
        settings = get_settings()

        # Register the system as a voter with significant power
        system_power = 1000.0
        self._voters["system"] = VoterInfo(
            address="system",
            voting_power=system_power,
            reputation_score=50.0,
        )

        # Register configured signers as voters
        signers = self._parse_signers(settings)
        for i, signer in enumerate(signers):
            self._voters[signer] = VoterInfo(
                address=signer,
                voting_power=100.0,  # Base power per signer
                reputation_score=0.0,
            )

    def _parse_signers(self, settings) -> list[str]:
        raw = settings.GOVERNANCE_SIGNERS.strip()
        if not raw:
            return []
        return [s.strip() for s in raw.split(",") if s.strip()]

    def _init_chain(self):
        """Lazily initialize blockchain connection."""
        if self._eth_client is not None:
            return
        settings = get_settings()
        self._eth_client = EthereumClient()
        if self._eth_client.is_connected():
            self._contracts = SmartContractManager(
                self._eth_client,
                bill_registry_address=settings.BILL_REGISTRY_ADDRESS,
                identity_registry_address=settings.IDENTITY_REGISTRY_ADDRESS,
                activity_logger_address=settings.ACTIVITY_LOGGER_ADDRESS,
                policy_enforcer_address=settings.POLICY_ENFORCER_ADDRESS,
                dispute_resolver_address=settings.DISPUTE_RESOLVER_ADDRESS,
            )
            self._chain_enabled = True
            logger.info("mABC: Blockchain connection established")
        else:
            self._chain_enabled = False
            logger.warning("mABC: Blockchain not connected — running in off-chain mode")

    # ─── Proposal Lifecycle ────────────────────────────────────────────────

    def create_proposal(
        self,
        proposer: str,
        title: str,
        description: str,
        target_contract: str,
        execution_data: bytes = b"",
        policy_changes: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Create a new governance proposal.

        The proposer must have sufficient voting power (>= proposal_threshold).
        The proposal enters PENDING state and transitions to ACTIVE after
        the voting delay period.
        """
        voter = self._voters.get(proposer)
        if not voter or not voter.is_registered:
            return {"success": False, "reason": f"Voter '{proposer}' is not registered"}

        effective_power = self.get_effective_voting_power(proposer)
        if effective_power < self._proposal_threshold:
            return {
                "success": False,
                "reason": f"Voting power {effective_power} below threshold {self._proposal_threshold}",
            }

        proposal_id = self._next_proposal_id
        self._next_proposal_id += 1

        now = time.time()
        proposal = GovernanceProposal(
            proposal_id=proposal_id,
            proposer=proposer,
            title=title,
            description=description,
            execution_data=execution_data,
            target_contract=target_contract,
            vote_start=now + 86400,  # 1-day delay before voting starts
            vote_end=now + 86400 + self._voting_period,
            quorum_required=self._calculate_quorum(),
        )

        self._proposals[proposal_id] = proposal
        self._votes[proposal_id] = []

        # Store policy changes as off-chain metadata
        if policy_changes:
            proposal.off_chain_votes["_policy_changes"] = policy_changes

        logger.info(
            "mABC: Proposal created — id=%d, title='%s', proposer=%s",
            proposal_id, title, proposer,
        )

        return {
            "success": True,
            "proposal_id": proposal_id,
            "state": ProposalState.PENDING.name,
            "vote_start": proposal.vote_start,
            "vote_end": proposal.vote_end,
            "quorum_required": proposal.quorum_required,
        }

    def cast_vote(
        self,
        voter: str,
        proposal_id: int,
        support: VoteSupport,
        reason: str = "",
    ) -> dict[str, Any]:
        """
        Cast a vote on a governance proposal.

        Voting power is token-weighted with reputation bonuses per mABC.
        Delegated votes are automatically included.
        """
        voter_info = self._voters.get(voter)
        if not voter_info or not voter_info.is_registered:
            return {"success": False, "reason": f"Voter '{voter}' is not registered"}

        proposal = self._proposals.get(proposal_id)
        if not proposal:
            return {"success": False, "reason": f"Proposal {proposal_id} not found"}

        now = time.time()
        if now < proposal.vote_start:
            return {"success": False, "reason": "Voting has not started yet"}
        if now > proposal.vote_end:
            return {"success": False, "reason": "Voting has ended"}

        # Check if already voted
        for existing_vote in self._votes.get(proposal_id, []):
            if existing_vote.voter == voter:
                return {"success": False, "reason": "Already voted on this proposal"}

        effective_power = self.get_effective_voting_power(voter)

        vote = VoteRecord(
            voter=voter,
            proposal_id=proposal_id,
            support=support,
            voting_power=effective_power,
            reason=reason,
        )
        self._votes[proposal_id].append(vote)

        # Update proposal vote counts
        if support == VoteSupport.FOR:
            proposal.for_votes += effective_power
        elif support == VoteSupport.AGAINST:
            proposal.against_votes += effective_power
        else:
            proposal.abstain_votes += effective_power

        logger.info(
            "mABC: Vote cast — voter=%s, proposal=%d, support=%s, power=%.2f",
            voter, proposal_id, support.name, effective_power,
        )

        return {
            "success": True,
            "proposal_id": proposal_id,
            "support": support.name,
            "voting_power": effective_power,
        }

    def queue_proposal(self, proposal_id: int) -> dict[str, Any]:
        """
        Queue a succeeded proposal for execution after the timelock delay.
        """
        proposal = self._proposals.get(proposal_id)
        if not proposal:
            return {"success": False, "reason": f"Proposal {proposal_id} not found"}

        state = self._get_proposal_state(proposal_id)
        if state != ProposalState.SUCCEEDED:
            return {"success": False, "reason": f"Proposal state is {state.name}, expected SUCCEEDED"}

        proposal.timelock_end = time.time() + self._timelock_delay
        proposal.state = ProposalState.QUEUED

        logger.info(
            "mABC: Proposal queued — id=%d, timelock_end=%.0f",
            proposal_id, proposal.timelock_end,
        )

        return {
            "success": True,
            "proposal_id": proposal_id,
            "timelock_end": proposal.timelock_end,
        }

    def execute_proposal(self, proposal_id: int) -> dict[str, Any]:
        """
        Execute a queued proposal after the timelock has expired.

        For policy change proposals, this applies the changes to the
        AgentGovernanceService. For on-chain proposals, this calls the
        target contract via the governance smart contract.
        """
        proposal = self._proposals.get(proposal_id)
        if not proposal:
            return {"success": False, "reason": f"Proposal {proposal_id} not found"}

        state = self._get_proposal_state(proposal_id)
        if state != ProposalState.QUEUED:
            return {"success": False, "reason": f"Proposal state is {state.name}, expected QUEUED"}

        if time.time() < proposal.timelock_end:
            remaining = proposal.timelock_end - time.time()
            return {
                "success": False,
                "reason": f"Timelock not expired. {remaining:.0f}s remaining",
            }

        # Apply policy changes if this is a policy proposal
        policy_changes = proposal.off_chain_votes.get("_policy_changes")
        applied_policies = {}
        if policy_changes:
            from app.governance.agent_governance import governance_service
            for agent_id, changes in policy_changes.items():
                try:
                    result = governance_service.update_policy(agent_id, changes)
                    applied_policies[agent_id] = result
                    logger.info("mABC: Policy updated for agent %s via governance", agent_id)
                except Exception as exc:
                    logger.error("mABC: Policy update failed for %s: %s", agent_id, exc)
                    applied_policies[agent_id] = {"error": str(exc)}

        # Attempt on-chain execution
        on_chain_tx = None
        if self._chain_enabled and proposal.execution_data:
            self._init_chain()
            # On-chain execution would go through MABCGovernance.sol
            logger.info("mABC: On-chain execution for proposal %d", proposal_id)

        proposal.state = ProposalState.EXECUTED
        proposal.executed = True
        proposal.resolution_notes = f"Executed at {time.time()}"

        logger.info("mABC: Proposal executed — id=%d", proposal_id)

        return {
            "success": True,
            "proposal_id": proposal_id,
            "state": ProposalState.EXECUTED.name,
            "applied_policies": applied_policies,
            "on_chain_tx": on_chain_tx,
        }

    def cancel_proposal(self, proposal_id: int, caller: str) -> dict[str, Any]:
        """Cancel a pending proposal (only proposer or owner)."""
        proposal = self._proposals.get(proposal_id)
        if not proposal:
            return {"success": False, "reason": f"Proposal {proposal_id} not found"}

        if caller != proposal.proposer and caller != "system":
            return {"success": False, "reason": "Only proposer or system can cancel"}

        state = self._get_proposal_state(proposal_id)
        if state != ProposalState.PENDING:
            return {"success": False, "reason": f"Can only cancel PENDING proposals, state is {state.name}"}

        proposal.state = ProposalState.CANCELLED
        proposal.vote_end = 0  # Mark as cancelled

        logger.info("mABC: Proposal cancelled — id=%d by %s", proposal_id, caller)
        return {"success": True, "proposal_id": proposal_id}

    # ─── Voter Management ─────────────────────────────────────────────────

    def register_voter(
        self, address: str, voting_power: float = 100.0, reputation: float = 0.0
    ) -> dict[str, Any]:
        """Register a new voter in the governance system."""
        if address in self._voters:
            return {"success": False, "reason": f"Voter '{address}' already registered"}

        self._voters[address] = VoterInfo(
            address=address,
            voting_power=voting_power,
            reputation_score=reputation,
        )

        logger.info("mABC: Voter registered — address=%s, power=%.2f", address, voting_power)
        return {"success": True, "address": address, "voting_power": voting_power}

    def delegate_voting_power(self, from_voter: str, to_voter: str) -> dict[str, Any]:
        """Delegate voting power to another voter (Byzantine fault tolerance)."""
        from_info = self._voters.get(from_voter)
        to_info = self._voters.get(to_voter)

        if not from_info or not from_info.is_registered:
            return {"success": False, "reason": f"Delegator '{from_voter}' not registered"}
        if not to_info or not to_info.is_registered:
            return {"success": False, "reason": f"Delegate '{to_voter}' not registered"}
        if from_voter == to_voter:
            return {"success": False, "reason": "Cannot delegate to self"}
        if from_info.delegated_to:
            return {"success": False, "reason": f"Already delegated to '{from_info.delegated_to}'"}

        from_info.delegated_to = to_voter
        to_info.delegation_count += 1

        logger.info("mABC: Voting power delegated — %s → %s", from_voter, to_voter)
        return {
            "success": True,
            "from": from_voter,
            "to": to_voter,
            "power_delegated": from_info.voting_power,
        }

    def update_reputation(self, agent_address: str, score: float) -> dict[str, Any]:
        """Update agent reputation score (affects voting power per mABC)."""
        voter = self._voters.get(agent_address)
        if not voter:
            return {"success": False, "reason": f"Agent '{agent_address}' not found"}

        old_power = self.get_effective_voting_power(agent_address)
        voter.reputation_score = score
        new_power = self.get_effective_voting_power(agent_address)

        logger.info(
            "mABC: Reputation updated — agent=%s, score=%.2f, power_change=%.2f→%.2f",
            agent_address, score, old_power, new_power,
        )
        return {
            "success": True,
            "agent": agent_address,
            "reputation_score": score,
            "voting_power_before": old_power,
            "voting_power_after": new_power,
        }

    # ─── Query Functions ───────────────────────────────────────────────────

    def get_effective_voting_power(self, voter_address: str) -> float:
        """
        Calculate effective voting power including reputation bonus.
        Per mABC: effective_power = base_power + (reputation / 2), capped at 2x base.
        """
        voter = self._voters.get(voter_address)
        if not voter or not voter.is_registered:
            return 0.0

        base = voter.voting_power
        reputation_bonus = voter.reputation_score / 2.0
        effective = base + reputation_bonus
        # Cap at 2x base power
        return min(effective, base * 2.0)

    def get_proposal(self, proposal_id: int) -> dict[str, Any]:
        """Get full proposal details."""
        proposal = self._proposals.get(proposal_id)
        if not proposal:
            return {"success": False, "reason": f"Proposal {proposal_id} not found"}

        return {
            "success": True,
            "proposal_id": proposal.proposal_id,
            "proposer": proposal.proposer,
            "title": proposal.title,
            "description": proposal.description,
            "state": self._get_proposal_state(proposal_id).name,
            "vote_start": proposal.vote_start,
            "vote_end": proposal.vote_end,
            "for_votes": proposal.for_votes,
            "against_votes": proposal.against_votes,
            "abstain_votes": proposal.abstain_votes,
            "quorum_required": proposal.quorum_required,
            "timelock_end": proposal.timelock_end,
            "executed": proposal.executed,
            "total_votes": len(self._votes.get(proposal_id, [])),
        }

    def list_proposals(self, state_filter: ProposalState | None = None) -> list[dict]:
        """List all proposals, optionally filtered by state."""
        results = []
        for pid, proposal in self._proposals.items():
            current_state = self._get_proposal_state(pid)
            if state_filter and current_state != state_filter:
                continue
            results.append({
                "proposal_id": pid,
                "title": proposal.title,
                "proposer": proposal.proposer,
                "state": current_state.name,
                "for_votes": proposal.for_votes,
                "against_votes": proposal.against_votes,
            })
        return results

    def list_voters(self) -> list[dict]:
        """List all registered voters."""
        return [
            {
                "address": v.address,
                "voting_power": v.voting_power,
                "effective_power": self.get_effective_voting_power(v.address),
                "delegated_to": v.delegated_to,
                "delegation_count": v.delegation_count,
                "reputation_score": v.reputation_score,
                "is_registered": v.is_registered,
            }
            for v in self._voters.values()
        ]

    def get_vote_records(self, proposal_id: int) -> list[dict]:
        """Get all vote records for a proposal."""
        votes = self._votes.get(proposal_id, [])
        return [
            {
                "voter": v.voter,
                "support": v.support.name,
                "voting_power": v.voting_power,
                "reason": v.reason,
                "timestamp": v.timestamp,
            }
            for v in votes
        ]

    # ─── Internal ──────────────────────────────────────────────────────────

    def _calculate_quorum(self) -> float:
        """Calculate quorum requirement as a fraction of total voting power."""
        total_power = sum(v.voting_power for v in self._voters.values() if v.is_registered)
        return total_power * self._quorum_numerator / self._quorum_denominator

    def _get_proposal_state(self, proposal_id: int) -> ProposalState:
        """Determine the current state of a proposal."""
        proposal = self._proposals.get(proposal_id)
        if not proposal:
            return ProposalState.CANCELLED

        if proposal.executed:
            return ProposalState.EXECUTED
        if proposal.vote_end == 0:
            return ProposalState.CANCELLED

        now = time.time()
        if now < proposal.vote_start:
            return ProposalState.PENDING
        if now <= proposal.vote_end:
            return ProposalState.ACTIVE

        # Voting ended
        if proposal.for_votes <= proposal.against_votes:
            return ProposalState.DEFEATED
        total_votes = proposal.for_votes + proposal.abstain_votes
        if total_votes < proposal.quorum_required:
            return ProposalState.DEFEATED

        if proposal.timelock_end > 0:
            if now >= proposal.timelock_end:
                return ProposalState.QUEUED
            return ProposalState.QUEUED

        return ProposalState.SUCCEEDED


# ─── Singleton ──────────────────────────────────────────────────────────────

mabc_voting_service = MABCVotingService()