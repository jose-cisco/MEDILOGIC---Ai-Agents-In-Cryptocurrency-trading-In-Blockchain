import json
import time
from typing import Optional
from web3 import Web3
from app.core.config import get_settings


class EthereumClient:
    def __init__(self):
        settings = get_settings()
        self.w3 = (
            Web3(Web3.HTTPProvider(settings.ETHEREUM_RPC_URL))
            if settings.ETHEREUM_RPC_URL
            else None
        )

    def is_connected(self) -> bool:
        if not self.w3:
            return False
        return self.w3.is_connected()

    def get_balance(self, address: str) -> float:
        if not self.w3:
            return 0.0
        checksum = self.w3.to_checksum_address(address)
        wei = self.w3.eth.get_balance(checksum)
        return float(Web3.from_wei(wei, "ether"))

    def get_gas_price(self) -> int:
        if not self.w3:
            return 0
        return self.w3.eth.gas_price

    def get_block_number(self) -> int:
        if not self.w3:
            return 0
        return self.w3.eth.block_number

    def get_token_price_via_uniswap(self, token_address: str) -> Optional[float]:
        return None

    def build_and_send_transaction(
        self,
        from_address: str,
        to_address: str,
        value_eth: float,
        private_key: str,
        gas_limit: int = 21000,
    ) -> Optional[str]:
        if not self.w3:
            return None
        try:
            nonce = self.w3.eth.get_transaction_count(from_address)
            tx = {
                "nonce": nonce,
                "to": to_address,
                "value": Web3.to_wei(value_eth, "ether"),
                "gas": gas_limit,
                "gasPrice": self.w3.eth.gas_price,
                "chainId": self.w3.eth.chain_id,
            }
            signed = self.w3.eth.account.sign_transaction(tx, private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            return receipt.transactionHash.hex()
        except Exception as e:
            return None


class SmartContractManager:
    BILL_REGISTRY_ABI = json.loads("""[
        {"inputs":[{"name":"user","type":"address"},{"name":"amount","type":"uint256"}],"name":"recordPayment","outputs":[],"stateMutability":"nonpayable","type":"function"},
        {"inputs":[{"name":"user","type":"address"}],"name":"hasPaid","outputs":[{"name":"","type":"bool"}],"stateMutability":"view","type":"function"},
        {"inputs":[{"name":"agent","type":"address"},{"name":"reward","type":"uint256"}],"name":"rewardAgent","outputs":[],"stateMutability":"nonpayable","type":"function"},
        {"inputs":[],"name":"getTotalBills","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"}
    ]""")

    IDENTITY_REGISTRY_ABI = json.loads("""[
        {"inputs":[{"name":"agent","type":"address"},{"name":"name","type":"string"},{"name":"role","type":"string"}],"name":"registerAgent","outputs":[],"stateMutability":"nonpayable","type":"function"},
        {"inputs":[{"name":"agent","type":"address"}],"name":"getAgent","outputs":[{"name":"name","type":"string"},{"name":"role","type":"string"},{"name":"active","type":"bool"}],"stateMutability":"view","type":"function"},
        {"inputs":[{"name":"agent","type":"address"}],"name":"deactivateAgent","outputs":[],"stateMutability":"nonpayable","type":"function"}
    ]""")

    ACTIVITY_LOGGER_ABI = json.loads("""[
        {"inputs":[{"name":"agentId","type":"string"},{"name":"eventHash","type":"bytes32"}],"name":"logActivity","outputs":[],"stateMutability":"nonpayable","type":"function"}
    ]""")

    def __init__(
        self,
        eth_client: EthereumClient,
        bill_registry_address: str = "",
        identity_registry_address: str = "",
        activity_logger_address: str = "",
        policy_enforcer_address: str = "",
        dispute_resolver_address: str = "",
    ):
        self.eth_client = eth_client
        self.bill_registry_address = bill_registry_address
        self.identity_registry_address = identity_registry_address
        self.activity_logger_address = activity_logger_address
        self.policy_enforcer_address = policy_enforcer_address
        self.dispute_resolver_address = dispute_resolver_address

    def _get_contract(self, address: str, abi: list):
        if not self.eth_client.w3 or not address:
            return None
        return self.eth_client.w3.eth.contract(
            address=self.eth_client.w3.to_checksum_address(address),
            abi=abi,
        )

    def check_payment(self, user_address: str) -> bool:
        contract = self._get_contract(
            self.bill_registry_address, self.BILL_REGISTRY_ABI
        )
        if not contract:
            return True
        try:
            return contract.functions.hasPaid(user_address).call()
        except Exception:
            return False

    def record_payment(
        self, user_address: str, amount_wei: int, private_key: str
    ) -> Optional[str]:
        contract = self._get_contract(
            self.bill_registry_address, self.BILL_REGISTRY_ABI
        )
        if not contract or not self.eth_client.w3:
            return None
        try:
            nonce = self.eth_client.w3.eth.get_transaction_count(user_address)
            tx = contract.functions.recordPayment(
                user_address, amount_wei
            ).build_transaction(
                {
                    "from": user_address,
                    "nonce": nonce,
                    "gas": 200000,
                    "gasPrice": self.eth_client.w3.eth.gas_price,
                }
            )
            signed = self.eth_client.w3.eth.account.sign_transaction(tx, private_key)
            tx_hash = self.eth_client.w3.eth.send_raw_transaction(
                signed.raw_transaction
            )
            receipt = self.eth_client.w3.eth.wait_for_transaction_receipt(
                tx_hash, timeout=120
            )
            return receipt.transactionHash.hex()
        except Exception:
            return None

    def register_agent(
        self, agent_address: str, name: str, role: str, private_key: str
    ) -> Optional[str]:
        contract = self._get_contract(
            self.identity_registry_address, self.IDENTITY_REGISTRY_ABI
        )
        if not contract or not self.eth_client.w3:
            return None
        try:
            nonce = self.eth_client.w3.eth.get_transaction_count(agent_address)
            tx = contract.functions.registerAgent(
                agent_address, name, role
            ).build_transaction(
                {
                    "from": agent_address,
                    "nonce": nonce,
                    "gas": 200000,
                    "gasPrice": self.eth_client.w3.eth.gas_price,
                }
            )
            signed = self.eth_client.w3.eth.account.sign_transaction(tx, private_key)
            tx_hash = self.eth_client.w3.eth.send_raw_transaction(
                signed.raw_transaction
            )
            receipt = self.eth_client.w3.eth.wait_for_transaction_receipt(
                tx_hash, timeout=120
            )
            return receipt.transactionHash.hex()
        except Exception:
            return None

    def anchor_activity(self, agent_id: str, event_hash: str) -> Optional[str]:
        """
        Best-effort on-chain anchoring for audit logs.
        Uses local connected account if available, otherwise no-op.
        """
        contract = self._get_contract(
            self.activity_logger_address, self.ACTIVITY_LOGGER_ABI
        )
        if not contract or not self.eth_client.w3:
            return None
        try:
            accounts = self.eth_client.w3.eth.accounts
            if not accounts:
                return None
            sender = accounts[0]
            nonce = self.eth_client.w3.eth.get_transaction_count(sender)
            event_bytes32 = event_hash if event_hash.startswith("0x") else "0x" + event_hash
            tx = contract.functions.logActivity(agent_id, event_bytes32).build_transaction(
                {
                    "from": sender,
                    "nonce": nonce,
                    "gas": 220000,
                    "gasPrice": self.eth_client.w3.eth.gas_price,
                }
            )
            tx_hash = self.eth_client.w3.eth.send_transaction(tx)
            receipt = self.eth_client.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            return receipt.transactionHash.hex()
        except Exception:
            return None
