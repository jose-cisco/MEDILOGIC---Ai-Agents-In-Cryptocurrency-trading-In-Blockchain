from typing import Optional
from app.core.config import get_settings


class SolanaClient:
    def __init__(self):
        settings = get_settings()
        self.rpc_url = settings.SOLANA_RPC_URL or "https://api.mainnet-beta.solana.com"

    def is_connected(self) -> bool:
        try:
            from solana.rpc.api import Client

            client = Client(self.rpc_url)
            return client.is_connected()
        except Exception:
            return False

    def get_balance(self, public_key: str) -> float:
        try:
            from solana.rpc.api import Client
            from solders.pubkey import Pubkey

            client = Client(self.rpc_url)
            pubkey = Pubkey.from_string(public_key)
            balance_lamports = client.get_balance(pubkey).value
            return balance_lamports / 1_000_000_000
        except Exception:
            return 0.0

    def get_recent_blockhash(self) -> Optional[str]:
        try:
            from solana.rpc.api import Client

            client = Client(self.rpc_url)
            resp = client.get_latest_blockhash()
            return str(resp.value.blockhash)
        except Exception:
            return None
