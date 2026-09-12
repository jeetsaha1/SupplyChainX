import hardhatToolboxMochaEthersPlugin from "@nomicfoundation/hardhat-toolbox-mocha-ethers";
import { defineConfig } from "hardhat/config";
import { config as loadEnv } from "dotenv";

loadEnv();

export default defineConfig({
  plugins: [hardhatToolboxMochaEthersPlugin],
  paths: {
    sources: "./contracts",
    tests: "./test", // Fixed: usually tests are in ./test, not ./contracts/test unless you moved them
    cache: "./cache",
    artifacts: "./artifacts",
  },
  solidity: {
    profiles: {
      default: {
        version: "0.8.24", // FIXED: Changed from 0.8.34 to 0.8.24
      },
      production: {
        version: "0.8.24", // FIXED: Changed from 0.8.34 to 0.8.24
        settings: {
          optimizer: {
            enabled: true,
            runs: 200,
          },
        },
      },
    },
  },
  networks: {
    hardhatMainnet: {
      type: "edr-simulated",
      chainType: "l1",
    },
    hardhatOp: {
      type: "edr-simulated",
      chainType: "op",
    },
    amoy: {
      type: "http",
      chainType: "l1",
      url: process.env.RPC_URL || "https://rpc-amoy.polygon.technology",
      accounts: process.env.WALLET_PRIVATE_KEY ? [process.env.WALLET_PRIVATE_KEY] : [],
      chainId: 80002,
    },
  },
});