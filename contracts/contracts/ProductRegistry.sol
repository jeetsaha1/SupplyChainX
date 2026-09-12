// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/// @title ProductRegistry
/// @notice Minimal interface skeleton for SupplyChainX tamper-evidence anchoring.
contract ProductRegistry {
    mapping(bytes32 => bool) private registeredUnits;
    mapping(bytes32 => bytes32) private latestEventHashes;

    event UnitRegistered(bytes32 indexed unitHash);
    event EventAdded(bytes32 indexed unitHash, bytes32 indexed eventHash);

    function registerUnit(bytes32 unitHash) external {
        registeredUnits[unitHash] = true;
        emit UnitRegistered(unitHash);
    }

    function addEvent(bytes32 unitHash, bytes32 eventHash) external {
        latestEventHashes[unitHash] = eventHash;
        emit EventAdded(unitHash, eventHash);
    }

    function getLatestEventHash(bytes32 unitHash) external view returns (bytes32) {
        return latestEventHashes[unitHash];
    }
}
