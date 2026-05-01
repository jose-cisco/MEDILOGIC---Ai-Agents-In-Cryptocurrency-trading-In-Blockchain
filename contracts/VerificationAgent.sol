// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract VerificationAgent {
    struct Verification {
        address planner;
        address verifier;
        bytes32 tradeHash;
        bool approved;
        uint256 timestamp;
        string reason;
    }

    Verification[] public verifications;
    mapping(bytes32 => bool) public verifiedTrades;

    address public owner;
    uint256 public minConfidenceBps;

    event TradeVerified(bytes32 indexed tradeHash, bool approved, string reason);

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner");
        _;
    }

    constructor(uint256 _minConfidenceBps) {
        owner = msg.sender;
        minConfidenceBps = _minConfidenceBps;
    }

    function verifyTrade(
        bytes32 _tradeHash,
        address _planner,
        address _verifier,
        bool _approved,
        string memory _reason
    ) external onlyOwner {
        verifications.push(Verification({
            planner: _planner,
            verifier: _verifier,
            tradeHash: _tradeHash,
            approved: _approved,
            timestamp: block.timestamp,
            reason: _reason
        }));

        verifiedTrades[_tradeHash] = _approved;
        emit TradeVerified(_tradeHash, _approved, _reason);
    }

    function isVerified(bytes32 _tradeHash) external view returns (bool) {
        return verifiedTrades[_tradeHash];
    }

    function setMinConfidence(uint256 _newBps) external onlyOwner {
        minConfidenceBps = _newBps;
    }

    function getVerificationCount() external view returns (uint256) {
        return verifications.length;
    }
}