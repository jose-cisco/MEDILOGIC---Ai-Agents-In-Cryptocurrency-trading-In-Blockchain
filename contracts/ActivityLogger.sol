// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract ActivityLogger {
    struct Activity {
        string agentId;
        bytes32 eventHash;
        uint256 timestamp;
        address submitter;
    }

    Activity[] public activities;
    mapping(bytes32 => bool) public knownEventHash;

    address public owner;

    event ActivityLogged(string indexed agentId, bytes32 indexed eventHash, address indexed submitter);

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function logActivity(string calldata agentId, bytes32 eventHash) external onlyOwner {
        require(eventHash != bytes32(0), "invalid hash");
        activities.push(Activity({
            agentId: agentId,
            eventHash: eventHash,
            timestamp: block.timestamp,
            submitter: msg.sender
        }));
        knownEventHash[eventHash] = true;
        emit ActivityLogged(agentId, eventHash, msg.sender);
    }

    function getActivityCount() external view returns (uint256) {
        return activities.length;
    }
}
