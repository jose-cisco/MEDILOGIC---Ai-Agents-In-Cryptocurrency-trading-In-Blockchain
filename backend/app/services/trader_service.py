import time
import uuid

class TraderService:
    def __init__(self):
        # Initial mock traders to match the user's sample images
        self.traders = {
            "glm5-eth-base": {
                "id": "glm5-eth-base",
                "name": "Live Alpha - ETH Momentum",
                "model": "GLM-5.1 Reasoning (OpenRouter)",
                "exchange": "ETH/USDT (Base Mainnet)",
                "status": "RUNNING",
                "uptime": "14d 2h",
                "pnl": "+12.4%",
                "pnl_usd": "1450.20",
                "equity": "5970.24"
            },
            "grok-sol-solana": {
                "id": "grok-sol-solana",
                "name": "Paper Beta - SOL Arbitrage",
                "model": "Grok 4.20 (OpenRouter)",
                "exchange": "SOL/USDT (Solana)",
                "status": "RUNNING",
                "uptime": "3d 4h",
                "pnl": "+4.1%",
                "pnl_usd": "410.50",
                "equity": "10410.50"
            },
            "minimax-btc-eth": {
                "id": "minimax-btc-eth",
                "name": "Sim Gamma - BTC Trends",
                "model": "MiniMax M2.7 (Ollama)",
                "exchange": "BTC/USDT (Ethereum)",
                "status": "RUNNING",
                "uptime": "8d 12h",
                "pnl": "-1.2%",
                "pnl_usd": "-120.00",
                "equity": "9880.00"
            },
            "glm5-btc-base": {
                "id": "glm5-btc-base",
                "name": "Sim Delta - BTC Ranging",
                "model": "GLM-5 Reasoning (Ollama)",
                "exchange": "BTC/USDC (Base Mainnet)",
                "status": "STOPPED",
                "uptime": "0d 0h",
                "pnl": "+0.0%",
                "pnl_usd": "0.00",
                "equity": "10000.00"
            }
        }

    def list_traders(self):
        return list(self.traders.values())

    def update_status(self, trader_id, status):
        if trader_id in self.traders:
            self.traders[trader_id]["status"] = status
            return True
        return False

    def delete_trader(self, trader_id):
        if trader_id in self.traders:
            del self.traders[trader_id]
            return True
        return False

trader_service = TraderService()
