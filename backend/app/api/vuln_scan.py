"""Vulnerability Scanner API — Ensemble LLM contract scanning."""
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.core.vulnerability_scanner import vulnerability_scanner
from app.core.config import get_settings

router = APIRouter()


class ScanRequest(BaseModel):
    contract_source: str
    contract_name: str = "unknown"
    model_1: str = "glm-5.1"
    model_2: str = "grok-4.20"


class AddressScanRequest(BaseModel):
    address: str
    chain: str = "ethereum"   # ethereum | bsc | polygon | arbitrum | base
    model_1: str = "glm-5.1"
    model_2: str = "grok-4.20"


class BatchScanRequest(BaseModel):
    contracts: dict[str, str]  # name → source
    model_1: str = "glm-5.1"
    model_2: str = "grok-4.20"


@router.post("/scan")
async def scan_contract(request: ScanRequest):
    result = vulnerability_scanner.scan_contract(
        contract_source=request.contract_source,
        contract_name=request.contract_name,
        model_1=request.model_1,
        model_2=request.model_2,
    )
    return {
        "scan_id": result.scan_id,
        "contract_name": result.contract_name,
        "contract_hash": result.contract_hash[:16] + "...",
        "overall_risk_score": result.overall_risk_score,
        "ensemble_confidence": result.ensemble_confidence,
        "planner_risk_score": result.planner_risk_score,
        "verifier_risk_score": result.verifier_risk_score,
        "passed": result.passed,
        "findings_count": len(result.findings),
        "findings": [
            {
                "category": f.category.value,
                "severity": f.severity.value,
                "title": f.title,
                "description": f.description[:200] + "..." if len(f.description) > 200 else f.description,
                "line_number": f.line_number,
                "recommendation": f.recommendation[:200] + "..." if len(f.recommendation) > 200 else f.recommendation,
                "confidence": f.confidence,
                "detected_by": f.detected_by,
            }
            for f in result.findings
        ],
        "duration_seconds": result.scan_duration_seconds,
    }


# ─── Chain → Etherscan-compatible API base ────────────────────────────────────
_EXPLORER_APIS = {
    "ethereum":  "https://api.etherscan.io/api",
    "bsc":       "https://api.bscscan.com/api",
    "polygon":   "https://api.polygonscan.com/api",
    "arbitrum":  "https://api.arbiscan.io/api",
    "base":      "https://api.basescan.org/api",
    "optimism":  "https://api-optimistic.etherscan.io/api",
}


@router.post("/scan/address")
async def scan_contract_address(request: AddressScanRequest):
    """
    Fetch verified Solidity source from a block explorer (Etherscan-compatible),
    then run the Ensemble LLM vulnerability scan on the retrieved source code.
    """
    settings = get_settings()
    api_key = settings.ETHERSCAN_API_KEY if hasattr(settings, "ETHERSCAN_API_KEY") else ""
    base_url = _EXPLORER_APIS.get(request.chain.lower())
    if not base_url:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported chain '{request.chain}'. Supported: {list(_EXPLORER_APIS.keys())}",
        )

    params = {
        "module": "contract",
        "action": "getsourcecode",
        "address": request.address,
        "apikey": api_key or "YourApiKeyToken",
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(base_url, params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Block explorer request failed: {e}")

    if data.get("status") != "1" or not data.get("result"):
        raise HTTPException(status_code=404, detail="Contract not found or source not verified on explorer.")

    result_list = data["result"]
    if isinstance(result_list, list) and result_list:
        item = result_list[0]
    else:
        raise HTTPException(status_code=404, detail="Empty result from block explorer.")

    source_code = item.get("SourceCode", "")
    contract_name = item.get("ContractName", request.address[:10])

    if not source_code or source_code.strip() in ("", "0x"):
        raise HTTPException(
            status_code=422,
            detail="Source code not verified on block explorer. Only verified contracts can be scanned.",
        )

    # Strip Etherscan's JSON wrapper (multi-file contracts are wrapped in {{ ... }})
    if source_code.startswith("{{"):
        try:
            import json as _json
            unwrapped = _json.loads(source_code[1:-1])
            files = unwrapped.get("sources", {})
            source_code = "\n\n".join(v.get("content", "") for v in files.values())
        except Exception:
            pass  # keep raw if parse fails

    result = vulnerability_scanner.scan_contract(
        contract_source=source_code,
        contract_name=contract_name,
        model_1=request.model_1,
        model_2=request.model_2,
    )
    return {
        "scan_id": result.scan_id,
        "contract_name": result.contract_name,
        "contract_address": request.address,
        "chain": request.chain,
        "contract_hash": result.contract_hash[:16] + "...",
        "overall_risk_score": result.overall_risk_score,
        "ensemble_confidence": result.ensemble_confidence,
        "planner_risk_score": result.planner_risk_score,
        "verifier_risk_score": result.verifier_risk_score,
        "passed": result.passed,
        "findings_count": len(result.findings),
        "findings": [
            {
                "category": f.category.value,
                "severity": f.severity.value,
                "title": f.title,
                "description": f.description[:200] + "..." if len(f.description) > 200 else f.description,
                "line_number": f.line_number,
                "recommendation": f.recommendation[:200] + "..." if len(f.recommendation) > 200 else f.recommendation,
                "confidence": f.confidence,
                "detected_by": f.detected_by,
            }
            for f in result.findings
        ],
        "duration_seconds": result.scan_duration_seconds,
    }


@router.post("/scan/batch")
async def scan_batch(request: BatchScanRequest):
    results = vulnerability_scanner.scan_contracts_batch(
        contracts=request.contracts,
        model_1=request.model_1,
        model_2=request.model_2,
    )
    summary = {}
    for name, result in results.items():
        summary[name] = {
            "scan_id": result.scan_id,
            "overall_risk_score": result.overall_risk_score,
            "ensemble_confidence": result.ensemble_confidence,
            "passed": result.passed,
            "findings_count": len(result.findings),
            "duration_seconds": result.scan_duration_seconds,
        }
    return {"total_scanned": len(results), "results": summary}


@router.post("/scan/all-deployed")
async def scan_all_deployed(model_1: str = "glm-5.1", model_2: str = "grok-4.20"):
    results = vulnerability_scanner.scan_all_deployed_contracts(model_1=model_1, model_2=model_2)
    summary = {}
    for name, result in results.items():
        summary[name] = {
            "scan_id": result.scan_id,
            "overall_risk_score": result.overall_risk_score,
            "passed": result.passed,
            "findings_count": len(result.findings),
        }
    return {"total_scanned": len(results), "results": summary}


@router.get("/history")
async def get_scan_history(limit: int = 20):
    return {"history": vulnerability_scanner.get_scan_history(limit=limit)}


@router.get("/result/{scan_id}")
async def get_scan_result(scan_id: str):
    result = vulnerability_scanner.get_scan_result(scan_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Scan {scan_id} not found")
    return {
        "scan_id": result.scan_id,
        "contract_name": result.contract_name,
        "overall_risk_score": result.overall_risk_score,
        "ensemble_confidence": result.ensemble_confidence,
        "passed": result.passed,
        "findings": [
            {
                "category": f.category.value,
                "severity": f.severity.value,
                "title": f.title,
                "description": f.description,
                "recommendation": f.recommendation,
                "confidence": f.confidence,
                "detected_by": f.detected_by,
            }
            for f in result.findings
        ],
    }