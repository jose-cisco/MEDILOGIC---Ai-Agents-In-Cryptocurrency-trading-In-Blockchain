// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract PolicyEnforcer {
    struct Policy {
        uint256 maxTradesPerHour;
        uint256 maxNotionalUsd;
        bool active;
        bytes32 policyConfigHash; // off-chain JSON/IPFS hash anchor
    }

    mapping(address => Policy) public policies;
    address public owner;

    event PolicyUpdated(address indexed agent, uint256 maxTradesPerHour, uint256 maxNotionalUsd, bytes32 policyConfigHash);
    event AgentPaused(address indexed agent, bool active);

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function setPolicy(
        address agent,
        uint256 maxTradesPerHour,
        uint256 maxNotionalUsd,
        bytes32 policyConfigHash
    ) external onlyOwner {
        policies[agent] = Policy({
            maxTradesPerHour: maxTradesPerHour,
            maxNotionalUsd: maxNotionalUsd,
            active: true,
            policyConfigHash: policyConfigHash
        });
        emit PolicyUpdated(agent, maxTradesPerHour, maxNotionalUsd, policyConfigHash);
    }

    function setAgentActive(address agent, bool active) external onlyOwner {
        require(policies[agent].maxTradesPerHour > 0, "policy not set");
        policies[agent].active = active;
        emit AgentPaused(agent, active);
    }
}
