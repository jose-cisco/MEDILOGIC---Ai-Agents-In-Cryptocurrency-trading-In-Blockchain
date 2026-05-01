// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract DisputeResolver {
    enum DisputeStatus { Open, Resolved, Rejected }

    struct Dispute {
        address reporter;
        string agentId;
        bytes32 eventHash;
        string reason;
        DisputeStatus status;
        uint256 createdAt;
        uint256 resolvedAt;
    }

    address public owner;
    Dispute[] public disputes;

    event DisputeFiled(uint256 indexed disputeId, string indexed agentId, bytes32 indexed eventHash, address reporter);
    event DisputeResolved(uint256 indexed disputeId, DisputeStatus status);

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function fileDispute(string calldata agentId, bytes32 eventHash, string calldata reason) external returns (uint256) {
        disputes.push(Dispute({
            reporter: msg.sender,
            agentId: agentId,
            eventHash: eventHash,
            reason: reason,
            status: DisputeStatus.Open,
            createdAt: block.timestamp,
            resolvedAt: 0
        }));
        uint256 id = disputes.length - 1;
        emit DisputeFiled(id, agentId, eventHash, msg.sender);
        return id;
    }

    function resolveDispute(uint256 disputeId, bool accepted) external onlyOwner {
        require(disputeId < disputes.length, "invalid dispute id");
        Dispute storage d = disputes[disputeId];
        require(d.status == DisputeStatus.Open, "already closed");
        d.status = accepted ? DisputeStatus.Resolved : DisputeStatus.Rejected;
        d.resolvedAt = block.timestamp;
        emit DisputeResolved(disputeId, d.status);
    }

    function getDisputeCount() external view returns (uint256) {
        return disputes.length;
    }
}
