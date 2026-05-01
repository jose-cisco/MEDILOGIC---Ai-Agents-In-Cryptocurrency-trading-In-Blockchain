// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract BillRegistry {
    struct Bill {
        address user;
        uint256 amount;
        uint256 timestamp;
        bool paid;
    }

    mapping(address => bool) public hasPaid;
    mapping(address => uint256) public lastPaymentAmount;
    mapping(address => uint256) public lastPaymentTime;
    Bill[] public bills;

    address public owner;
    uint256 public totalBills;

    event PaymentRecorded(address indexed user, uint256 amount);
    event AgentRewarded(address indexed agent, uint256 reward);

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function recordPayment(address _user, uint256 _amount) external onlyOwner {
        hasPaid[_user] = true;
        lastPaymentAmount[_user] = _amount;
        lastPaymentTime[_user] = block.timestamp;
        bills.push(Bill({
            user: _user,
            amount: _amount,
            timestamp: block.timestamp,
            paid: true
        }));
        totalBills++;
        emit PaymentRecorded(_user, _amount);
    }

    function rewardAgent(address _agent, uint256 _reward) external onlyOwner {
        (bool success, ) = _agent.call{value: _reward}("");
        require(success, "Reward transfer failed");
        emit AgentRewarded(_agent, _reward);
    }

    function checkPaid(address _user) external view returns (bool) {
        return hasPaid[_user];
    }

    function getTotalBills() external view returns (uint256) {
        return totalBills;
    }

    receive() external payable {}
}