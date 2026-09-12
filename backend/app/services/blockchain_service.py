import hashlib
import json
from pathlib import Path
from typing import Any

from app.config import settings


def _simulated_tx(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return f"0x{prefix}{digest[:59]}"


def _rpc_available() -> bool:
    if not settings.RPC_URL or settings.RPC_URL.startswith("http://localhost"):
        return False
    try:
        from web3 import Web3

        provider = Web3.HTTPProvider(settings.RPC_URL, request_kwargs={"timeout": 3})
        return Web3(provider).is_connected()
    except Exception:
        return False


def _contract() -> tuple[Any, Any, Any] | None:
    if not settings.CONTRACT_ADDRESS or settings.WALLET_PRIVATE_KEY == "change-me-in-environment":
        return None
    try:
        from web3 import Web3

        web3 = Web3(Web3.HTTPProvider(settings.RPC_URL, request_kwargs={"timeout": 5}))
        if not web3.is_connected():
            return None
        account = web3.eth.account.from_key(settings.WALLET_PRIVATE_KEY)
        artifact_path = (
            Path(__file__).resolve().parents[3]
            / "contracts"
            / "artifacts"
            / "contracts"
            / "ProductRegistry.sol"
            / "ProductRegistry.json"
        )
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        contract = web3.eth.contract(
            address=Web3.to_checksum_address(settings.CONTRACT_ADDRESS),
            abi=artifact["abi"],
        )
        return web3, account, contract
    except Exception as error:
        print(f"[blockchain] real integration unavailable: {error}")
        return None


def _bytes32(value: str) -> bytes:
    cleaned = value[2:] if value.startswith("0x") else value
    return bytes.fromhex(cleaned[:64].ljust(64, "0"))


def _send_transaction(function: Any, web3: Any, account: Any) -> str:
    transaction = function.build_transaction({
        "from": account.address,
        "nonce": web3.eth.get_transaction_count(account.address),
        "chainId": web3.eth.chain_id,
        "gas": 300000,
        "gasPrice": web3.eth.gas_price,
    })
    signed = account.sign_transaction(transaction)
    return web3.eth.send_raw_transaction(signed.raw_transaction).hex()


def register_unit_on_chain(unit_hash: str) -> str:
    client = _contract()
    if client:
        web3, account, contract = client
        try:
            tx_hash = _send_transaction(contract.functions.registerUnit(_bytes32(unit_hash)), web3, account)
            print(f"[blockchain:real] registered unit {unit_hash} -> {tx_hash}")
            return tx_hash
        except Exception as error:
            print(f"[blockchain] register failed; using simulated anchoring: {error}")
    elif _rpc_available():
        print("[blockchain] RPC reachable; contract address or wallet is not configured")
    tx_hash = _simulated_tx("sim", f"register:{unit_hash}")
    print(f"[blockchain:simulated] register unit {unit_hash} -> {tx_hash}")
    return tx_hash


def anchor_event_on_chain(event_hash: str, unit_hash: str | None = None) -> str:
    client = _contract()
    if client and unit_hash:
        web3, account, contract = client
        try:
            tx_hash = _send_transaction(contract.functions.addEvent(_bytes32(unit_hash), _bytes32(event_hash)), web3, account)
            print(f"[blockchain:real] anchored event {event_hash} -> {tx_hash}")
            return tx_hash
        except Exception as error:
            print(f"[blockchain] event anchoring failed; using simulated anchoring: {error}")
    elif _rpc_available():
        print("[blockchain] RPC reachable; contract address or wallet is not configured")
    tx_hash = _simulated_tx("sim", f"event:{event_hash}")
    print(f"[blockchain:simulated] anchor event {event_hash} -> {tx_hash}")
    return tx_hash


def get_latest_event_hash(unit_hash: str) -> str | None:
    client = _contract()
    if client:
        try:
            _, _, contract = client
            return contract.functions.getLatestEventHash(_bytes32(unit_hash)).call().hex()
        except Exception as error:
            print(f"[blockchain] latest hash lookup failed: {error}")
    return None


register_unit = register_unit_on_chain


def add_event(unit_hash: str, event_hash: str) -> str:
    return anchor_event_on_chain(event_hash, unit_hash)
