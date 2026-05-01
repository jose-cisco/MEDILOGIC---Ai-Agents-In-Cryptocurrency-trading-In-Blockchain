"""EAAC — Ethereum AI Agent Coordinate Or API endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.core.eaac import eaac_service, CoordinationPhase

router = APIRouter()


class AgentRegistrationRequest(BaseModel):
    agent_id: str
    did: str
    public_key: str
    role: str = "AGENT_ROLE"


class CoordinationStartRequest(BaseModel):
    agent_id: str
    input_data_hash: str


class CoordinationAdvanceRequest(BaseModel):
    coordination_id: str
    new_phase: str
    output_hash: str


class DecisionAnchorRequest(BaseModel):
    coordination_id: str
    final_decision_hash: str


@router.post("/register")
async def register_agent(request: AgentRegistrationRequest):
    identity = eaac_service.register_agent(
        agent_id=request.agent_id,
        did=request.did,
        public_key=request.public_key,
        role=request.role,
    )
    return {"success": True, "identity": {
        "agent_id": identity.agent_id,
        "did": identity.did,
        "role": identity.role,
        "status": identity.status.value,
        "attestation_hash": identity.attestation_hash,
    }}


@router.get("/verify/{agent_id}")
async def verify_agent(agent_id: str):
    result = eaac_service.verify_agent_identity(agent_id)
    return result


@router.post("/coordination/start")
async def start_coordination(request: CoordinationStartRequest):
    record = eaac_service.begin_coordination(
        agent_id=request.agent_id,
        input_data_hash=request.input_data_hash,
    )
    return {"success": True, "coordination_id": record.coordination_id,
            "phase": record.phase.value, "attestation": record.attestation}


@router.post("/coordination/advance")
async def advance_coordination(request: CoordinationAdvanceRequest):
    record = eaac_service.get_coordination_record(request.coordination_id)
    if not record:
        raise HTTPException(status_code=404, detail="Coordination not found")
    try:
        new_phase = CoordinationPhase(request.new_phase)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid phase: {request.new_phase}")
    record = eaac_service.advance_phase(record, new_phase, request.output_hash)
    return {"success": True, "coordination_id": record.coordination_id,
            "phase": record.phase.value, "attestation": record.attestation}


@router.post("/coordination/anchor")
async def anchor_decision(request: DecisionAnchorRequest):
    record = eaac_service.get_coordination_record(request.coordination_id)
    if not record:
        raise HTTPException(status_code=404, detail="Coordination not found")
    entry = eaac_service.anchor_decision(record, request.final_decision_hash)
    return {"success": True, "response_id": entry.response_id,
            "response_hash": entry.response_hash, "on_chain_tx": entry.on_chain_tx}


@router.get("/coordination/{coordination_id}")
async def get_coordination(coordination_id: str):
    result = eaac_service.verify_coordination_chain(coordination_id)
    return result


@router.get("/agents/{agent_id}/coordinations")
async def list_agent_coordinations(agent_id: str):
    records = eaac_service.list_agent_coordinations(agent_id)
    return {"coordinations": [
        {"coordination_id": r.coordination_id, "phase": r.phase.value,
         "attestation": r.attestation, "timestamp": r.timestamp}
        for r in records
    ]}