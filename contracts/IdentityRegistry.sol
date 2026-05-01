// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract IdentityRegistry {
    struct Agent {
        string name;
        string role;
        bool active;
        uint256 registeredAt;
    }

    mapping(address => Agent) public agents;
    address[] public agentList;
    address public owner;

    event AgentRegistered(address indexed agent, string name, string role);
    event AgentDeactivated(address indexed agent);

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function registerAgent(address _agent, string memory _name, string memory _role) external onlyOwner {
        require(!agents[_agent].active || bytes(agents[_agent].name).length == 0, "Agent already registered");
        agents[_agent] = Agent({
            name: _name,
            role: _role,
            active: true,
            registeredAt: block.timestamp
        });
        agentList.push(_agent);
        emit AgentRegistered(_agent, _name, _role);
    }

    function deactivateAgent(address _agent) external onlyOwner {
        require(agents[_agent].active, "Agent not active");
        agents[_agent].active = false;
        emit AgentDeactivated(_agent);
    }

    function getAgent(address _agent) external view returns (string memory name, string memory role, bool active) {
        Agent memory a = agents[_agent];
        return (a.name, a.role, a.active);
    }

    function getAgentCount() external view returns (uint256) {
        return agentList.length;
    }
}