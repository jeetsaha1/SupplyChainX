# SupplyChainX Contracts

The Solidity source lives in `contracts/ProductRegistry.sol`. Hardhat is
configured in the project root and uses that directory as its source path.

## Compile and generate artifacts

From `D:\VSCODE\SupplyChainX\contracts`:

```powershell
npm install
npm run compile
```

Compilation writes the ABI and bytecode to:

```text
contracts/artifacts/contracts/ProductRegistry.sol/ProductRegistry.json
```

The ABI is available at the `abi` property in that JSON file. The backend can
eventually load it with:

```python
import json
from pathlib import Path

artifact_path = (
    Path(__file__).resolve().parents[3]
    / "contracts"
    / "artifacts"
    / "contracts"
    / "ProductRegistry.sol"
    / "ProductRegistry.json"
)
abi = json.loads(artifact_path.read_text()) ["abi"]
```

The blockchain service should keep simulated mode enabled until an RPC URL,
deployer wallet, and deployed contract address are configured.