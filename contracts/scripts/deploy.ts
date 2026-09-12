import { network } from "hardhat";

const rpcUrl = process.env.RPC_URL || "https://rpc-amoy.polygon.technology";
const privateKey = process.env.WALLET_PRIVATE_KEY;

if (!privateKey || privateKey === "change-me-before-deployment" || privateKey === "change-me-in-environment") {
	throw new Error(
		"WALLET_PRIVATE_KEY is missing. Add a funded Polygon Amoy testnet wallet key to contracts/.env before deploying.",
	);
}

if (!privateKey.startsWith("0x") || privateKey.length !== 66) {
	throw new Error("WALLET_PRIVATE_KEY must be a 32-byte private key beginning with 0x.");
}

console.log(`Deploying ProductRegistry to Polygon Amoy via ${rpcUrl}`);
const { ethers } = await network.connect();
const registry = await ethers.deployContract("ProductRegistry");
await registry.waitForDeployment();

const address = await registry.getAddress();
console.log(`ProductRegistry deployed to ${address}`);
console.log(`Explorer: https://amoy.polygonscan.com/address/${address}`);