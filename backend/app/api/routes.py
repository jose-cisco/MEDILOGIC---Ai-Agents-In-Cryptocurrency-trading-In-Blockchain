from fastapi import APIRouter
from app.api.trading import router as trading_router
from app.api.backtest import router as backtest_router
from app.api.status import router as status_router
from app.api.knowledge import router as knowledge_router
from app.api.governance import router as governance_router
from app.api.payments import router as payments_router
from app.api.eaac import router as eaac_router
from app.api.mabc import router as mabc_router
from app.api.vuln_scan import router as vuln_scan_router
from app.api.dex import router as dex_router
from app.api.ipfs_routes import router as ipfs_router
from app.api.traders import router as traders_router
from app.api.escrow import router as escrow_router
from app.api.auth import router as auth_router
from app.api.notifications import router as notifications_router
from app.api.paper_trading import router as paper_trading_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(notifications_router, prefix="/notifications", tags=["notifications"])
api_router.include_router(trading_router, prefix="/trading", tags=["trading"])
api_router.include_router(backtest_router, prefix="/backtest", tags=["backtest"])
api_router.include_router(status_router, prefix="/status", tags=["status"])
api_router.include_router(knowledge_router, prefix="/knowledge", tags=["knowledge"])
api_router.include_router(governance_router, prefix="/governance", tags=["governance"])
api_router.include_router(payments_router, prefix="/payments", tags=["payments"])
api_router.include_router(eaac_router, prefix="/eaac", tags=["eaac"])
api_router.include_router(mabc_router, prefix="/mabc", tags=["mabc"])
api_router.include_router(vuln_scan_router, prefix="/vulnerability", tags=["vulnerability"])
api_router.include_router(dex_router, prefix="/dex", tags=["dex"])
api_router.include_router(ipfs_router, prefix="/ipfs", tags=["ipfs"])
api_router.include_router(traders_router, prefix="/traders", tags=["traders"])
api_router.include_router(escrow_router, prefix="/escrow", tags=["escrow"])
api_router.include_router(paper_trading_router, prefix="/paper", tags=["paper"])
