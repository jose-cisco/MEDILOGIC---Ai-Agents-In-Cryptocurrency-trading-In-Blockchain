"""mABC Decentralized Governance API endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.governance.mabc_voting import mabc_voting_service, VoteSupport, ProposalState

router = APIRouter()


class CreateProposalRequest(BaseModel):
    proposer: str
    title: str
    description: str
    target_contract: str = ""
    policy_changes: Optional[dict] = None


class CastVoteRequest(BaseModel):
    voter: str
    proposal_id: int
    support: int  # 0=against, 1=for, 2=abstain
    reason: str = ""


class RegisterVoterRequest(BaseModel):
    address: str
    voting_power: float = 100.0
    reputation: float = 0.0


class DelegateRequest(BaseModel):
    from_voter: str
    to_voter: str


@router.post("/proposals")
async def create_proposal(request: CreateProposalRequest):
    result = mabc_voting_service.create_proposal(
        proposer=request.proposer,
        title=request.title,
        description=request.description,
        target_contract=request.target_contract,
        policy_changes=request.policy_changes,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("reason", "Proposal creation failed"))
    return result


@router.post("/proposals/{proposal_id}/vote")
async def cast_vote(proposal_id: int, request: CastVoteRequest):
    try:
        support = VoteSupport(request.support)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid vote: 0=against, 1=for, 2=abstain")
    result = mabc_voting_service.cast_vote(
        voter=request.voter,
        proposal_id=proposal_id,
        support=support,
        reason=request.reason,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("reason", "Vote cast failed"))
    return result


@router.post("/proposals/{proposal_id}/queue")
async def queue_proposal(proposal_id: int):
    result = mabc_voting_service.queue_proposal(proposal_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("reason", "Queue failed"))
    return result


@router.post("/proposals/{proposal_id}/execute")
async def execute_proposal(proposal_id: int):
    result = mabc_voting_service.execute_proposal(proposal_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("reason", "Execution failed"))
    return result


@router.post("/proposals/{proposal_id}/cancel")
async def cancel_proposal(proposal_id: int, caller: str = "system"):
    result = mabc_voting_service.cancel_proposal(proposal_id, caller=caller)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("reason", "Cancel failed"))
    return result


@router.get("/proposals")
async def list_proposals(state: Optional[str] = None):
    state_filter = None
    if state:
        try:
            state_filter = ProposalState[state.upper()]
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid state: {state}")
    return mabc_voting_service.list_proposals(state_filter)


@router.get("/proposals/{proposal_id}")
async def get_proposal(proposal_id: int):
    result = mabc_voting_service.get_proposal(proposal_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("reason", "Proposal not found"))
    return result


@router.get("/proposals/{proposal_id}/votes")
async def get_vote_records(proposal_id: int):
    return {"votes": mabc_voting_service.get_vote_records(proposal_id)}


@router.post("/voters/register")
async def register_voter(request: RegisterVoterRequest):
    result = mabc_voting_service.register_voter(
        address=request.address,
        voting_power=request.voting_power,
        reputation=request.reputation,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("reason", "Registration failed"))
    return result


@router.post("/voters/delegate")
async def delegate_voting_power(request: DelegateRequest):
    result = mabc_voting_service.delegate_voting_power(
        from_voter=request.from_voter,
        to_voter=request.to_voter,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("reason", "Delegation failed"))
    return result


@router.get("/voters")
async def list_voters():
    return {"voters": mabc_voting_service.list_voters()}


@router.get("/voters/{address}/power")
async def get_voting_power(address: str):
    return {"address": address, "effective_voting_power": mabc_voting_service.get_effective_voting_power(address)}