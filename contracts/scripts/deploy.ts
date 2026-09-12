import { network } from "hardhat";

const { ethers } = await network.connect();
const registry = await ethers.deployContract("ProductRegistry");
await registry.waitForDeployment();

console.log(`ProductRegistry deployed to ${await registry.getAddress()}`);