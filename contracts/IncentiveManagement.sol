// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./BillRegistry.sol";
import "./IdentityRegistry.sol";

contract IncentiveManagement {
    struct Incentive {
        address agent;
        uint256 rewardAmount;
        uint256 timestamp;
        string reason;
    }

    Incentive[] public incentives;
    mapping(address => uint256) public agentRewards;

    address public owner;
    IdentityRegistry public identityRegistry;
    BillRegistry public billRegistry;

    event RewardDistributed(address indexed agent, uint256 amount, string reason);

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner");
        _;
    }

    modifier onlyRegisteredAgent() {
        (string memory name, string memory role, bool active) = identityRegistry.getAgent(msg.sender);
        require(active, "Not a registered agent");
        _;
    }

    constructor(address _identityRegistry, address payable _billRegistry) {
        owner = msg.sender;
        identityRegistry = IdentityRegistry(_identityRegistry);
        billRegistry = BillRegistry(_billRegistry);
    }

    function distributeReward(address _agent, uint256 _amount, string memory _reason) external onlyOwner {
        (, , bool active) = identityRegistry.getAgent(_agent);
        require(active, "Agent not active");

        agentRewards[_agent] += _amount;
        incentives.push(Incentive({
            agent: _agent,
            rewardAmount: _amount,
            timestamp: block.timestamp,
            reason: _reason
        }));

        // Transfer funds to billRegistry using call instead of deprecated transfer
        (bool success, ) = payable(address(billRegistry)).call{value: _amount}("");
        require(success, "Transfer to billRegistry failed");
        billRegistry.rewardAgent(_agent, _amount);
        emit RewardDistributed(_agent, _amount, _reason);
    }

    function getAgentRewards(address _agent) external view returns (uint256) {
        return agentRewards[_agent];
    }

    function getIncentiveCount() external view returns (uint256) {
        return incentives.length;
    }

    receive() external payable {}
}