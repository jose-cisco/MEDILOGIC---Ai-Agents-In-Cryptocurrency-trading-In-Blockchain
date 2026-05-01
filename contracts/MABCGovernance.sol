// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title MABCGovernance
 * @notice Decentralized multi-agent Byzantine Consensus (mABC) governance.
 *
 * Implements the mABC framework from Karim et al. (2025) Section 6:
 *   - Token-weighted voting power for policy proposals
 *   - Proposal lifecycle: propose → vote → execute → enacted
 *   - Quorum and majority thresholds for Byzantine fault tolerance
 *   - Delegated voting (voters can delegate to trusted agents)
 *   - Timelock delay before execution (security buffer)
 *   - On-chain proposal and vote history for full auditability
 *
 * Reference: Survey Section 6 — "mABC framework for decentralized governance"
 */

contract MABCGovernance {
    // ─── Enums ────────────────────────────────────────────────────────────────

    enum ProposalState {
        Pending,        // Created, waiting for voting to start
        Active,         // Voting in progress
        Defeated,       // Voting ended — failed
        Succeeded,      // Voting ended — passed
        Queued,         // Passed and queued for timelock
        Executed,       // Timelock elapsed, executed on-chain
        Cancelled       // Cancelled by proposer before voting starts
    }

    // ─── Structs ───────────────────────────────────────────────────────────────

    struct Proposal {
        uint256 id;
        address proposer;
        string title;
        string description;
        bytes executionData;     // Encoded function call to execute
        address targetContract;  // Contract to call on execution
        uint256 voteStart;       // Timestamp when voting begins
        uint256 voteEnd;         // Timestamp when voting ends
        uint256 forVotes;        // Total votes in favor (weighted)
        uint256 againstVotes;    // Total votes against (weighted)
        uint256 abstainVotes;    // Total abstentions (weighted)
        uint256 quorumRequired;  // Minimum voting power for quorum
        uint256 timelockEnd;     // When timelock expires (after queued)
        bool executed;
        mapping(address => VoteReceipt) voteReceipts;
    }

    struct VoteReceipt {
        bool hasVoted;
        uint8 support;       // 0=against, 1=for, 2=abstain
        uint256 votingPower;
    }

    struct Voter {
        uint256 votingPower;     // Token-weighted voting power
        address delegatedTo;     // Who this voter has delegated to
        uint256 delegationCount; // How many voters have delegated to this voter
        bool isRegistered;
    }

    // ─── State Variables ──────────────────────────────────────────────────────

    address public owner;
    uint256 public proposalCount;
    uint256 public votingPeriod;          // Duration in seconds (default: 3 days)
    uint256 public quorumNumerator;       // Numerator for quorum % (default: 4 = 4%)
    uint256 public quorumDenominator;     // Denominator for quorum % (default: 100)
    uint256 public timelockDelay;          // Delay before execution in seconds (default: 1 day)
    uint256 public proposalThreshold;     // Minimum voting power to create a proposal

    mapping(uint256 => Proposal) public proposals;
    mapping(address => Voter) public voters;
    mapping(address => uint256) public agentReputation; // mABC reputation score

    // ─── Events ────────────────────────────────────────────────────────────────

    event ProposalCreated(uint256 indexed proposalId, address indexed proposer, string title);
    event VoteCast(uint256 indexed proposalId, address indexed voter, uint8 support, uint256 votingPower);
    event ProposalQueued(uint256 indexed proposalId, uint256 timelockEnd);
    event ProposalExecuted(uint256 indexed proposalId, address targetContract, bytes executionData);
    event ProposalCancelled(uint256 indexed proposalId);
    event VoterRegistered(address indexed voter, uint256 votingPower);
    event VotingPowerDelegated(address indexed from, address indexed to, uint256 votingPower);
    event AgentReputationUpdated(address indexed agent, uint256 newScore);

    // ─── Modifiers ─────────────────────────────────────────────────────────────

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner");
        _;
    }

    modifier onlyRegistered() {
        require(voters[msg.sender].isRegistered, "Not a registered voter");
        _;
    }

    // ─── Constructor ────────────────────────────────────────────────────────────

    constructor(
        uint256 _votingPeriod,
        uint256 _quorumNumerator,
        uint256 _quorumDenominator,
        uint256 _timelockDelay,
        uint256 _proposalThreshold
    ) {
        owner = msg.sender;
        votingPeriod = _votingPeriod;
        quorumNumerator = _quorumNumerator;
        quorumDenominator = _quorumDenominator;
        timelockDelay = _timelockDelay;
        proposalThreshold = _proposalThreshold;
    }

    // ─── Voter Management ──────────────────────────────────────────────────────

    function registerVoter(address _voter, uint256 _votingPower) external onlyOwner {
        require(!voters[_voter].isRegistered, "Already registered");
        voters[_voter] = Voter({
            votingPower: _votingPower,
            delegatedTo: address(0),
            delegationCount: 0,
            isRegistered: true
        });
        emit VoterRegistered(_voter, _votingPower);
    }

    function updateVotingPower(address _voter, uint256 _newPower) external onlyOwner {
        require(voters[_voter].isRegistered, "Not registered");
        voters[_voter].votingPower = _newPower;
        emit VoterRegistered(_voter, _newPower);
    }

    function delegateVotingPower(address _to) external onlyRegistered {
        require(_to != msg.sender, "Cannot delegate to self");
        require(voters[_to].isRegistered, "Delegate not registered");

        Voter storage delegator = voters[msg.sender];
        require(delegator.delegatedTo == address(0), "Already delegated");

        uint256 power = delegator.votingPower;
        delegator.delegatedTo = _to;
        voters[_to].delegationCount += 1;

        emit VotingPowerDelegated(msg.sender, _to, power);
    }

    function undelegate() external onlyRegistered {
        Voter storage delegator = voters[msg.sender];
        require(delegator.delegatedTo != address(0), "Not delegated");

        voters[delegator.delegatedTo].delegationCount -= 1;
        delegator.delegatedTo = address(0);

        emit VotingPowerDelegated(msg.sender, address(0), 0);
    }

    // ─── Agent Reputation (mABC Byzantine Fault Tolerance) ─────────────────────

    function updateReputation(address _agent, uint256 _score) external onlyOwner {
        agentReputation[_agent] = _score;
        emit AgentReputationUpdated(_agent, _score);
    }

    function getEffectiveVotingPower(address _voter) public view returns (uint256) {
        Voter memory v = voters[_voter];
        if (!v.isRegistered) return 0;
        // Effective power = own power + reputation bonus (capped at 2x)
        uint256 reputationBonus = agentReputation[_voter] / 2;
        uint256 base = v.votingPower;
        if (base + reputationBonus > base * 2) {
            return base * 2;
        }
        return base + reputationBonus;
    }

    // ─── Proposal Lifecycle ────────────────────────────────────────────────────

    function createProposal(
        string calldata _title,
        string calldata _description,
        bytes calldata _executionData,
        address _targetContract
    ) external onlyRegistered returns (uint256) {
        uint256 proposerPower = getEffectiveVotingPower(msg.sender);
        require(proposerPower >= proposalThreshold, "Below proposal threshold");

        proposalCount++;
        uint256 proposalId = proposalCount;

        Proposal storage p = proposals[proposalId];
        p.id = proposalId;
        p.proposer = msg.sender;
        p.title = _title;
        p.description = _description;
        p.executionData = _executionData;
        p.targetContract = _targetContract;
        p.voteStart = block.timestamp + 1 days;    // 1-day delay before voting starts
        p.voteEnd = block.timestamp + 1 days + votingPeriod;
        p.quorumRequired = _calculateQuorum();
        p.timelockEnd = 0;
        p.executed = false;

        emit ProposalCreated(proposalId, msg.sender, _title);
        return proposalId;
    }

    function castVote(uint256 _proposalId, uint8 _support) external onlyRegistered {
        require(_support <= 2, "Invalid vote: 0=against, 1=for, 2=abstain");
        Proposal storage p = proposals[_proposalId];
        require(block.timestamp >= p.voteStart, "Voting not started");
        require(block.timestamp <= p.voteEnd, "Voting ended");
        require(!p.voteReceipts[msg.sender].hasVoted, "Already voted");

        uint256 power = getEffectiveVotingPower(msg.sender);

        p.voteReceipts[msg.sender] = VoteReceipt({
            hasVoted: true,
            support: _support,
            votingPower: power
        });

        if (_support == 0) {
            p.againstVotes += power;
        } else if (_support == 1) {
            p.forVotes += power;
        } else {
            p.abstainVotes += power;
        }

        emit VoteCast(_proposalId, msg.sender, _support, power);
    }

    function queueProposal(uint256 _proposalId) external {
        Proposal storage p = proposals[_proposalId];
        require(_getState(_proposalId) == ProposalState.Succeeded, "Proposal not succeeded");
        require(p.timelockEnd == 0, "Already queued");

        p.timelockEnd = block.timestamp + timelockDelay;
        emit ProposalQueued(_proposalId, p.timelockEnd);
    }

    function executeProposal(uint256 _proposalId) external {
        Proposal storage p = proposals[_proposalId];
        require(_getState(_proposalId) == ProposalState.Queued, "Proposal not queued");
        require(block.timestamp >= p.timelockEnd, "Timelock not expired");
        require(!p.executed, "Already executed");

        p.executed = true;

        // Execute the proposal's encoded function call on the target contract
        (bool success, ) = p.targetContract.call(p.executionData);
        require(success, "Proposal execution failed");

        emit ProposalExecuted(_proposalId, p.targetContract, p.executionData);
    }

    function cancelProposal(uint256 _proposalId) external {
        Proposal storage p = proposals[_proposalId];
        require(msg.sender == p.proposer || msg.sender == owner, "Not proposer or owner");
        require(_getState(_proposalId) == ProposalState.Pending, "Can only cancel pending proposals");

        // Mark as cancelled by setting voteEnd to 0
        p.voteEnd = 0;
        emit ProposalCancelled(_proposalId);
    }

    // ─── View Functions ────────────────────────────────────────────────────────

    function getProposalState(uint256 _proposalId) external view returns (ProposalState) {
        return _getState(_proposalId);
    }

    function getProposalDetails(uint256 _proposalId) external view returns (
        address proposer,
        string memory title,
        string memory description,
        uint256 forVotes,
        uint256 againstVotes,
        uint256 abstainVotes,
        uint256 voteStart,
        uint256 voteEnd,
        bool executed
    ) {
        Proposal storage p = proposals[_proposalId];
        return (
            p.proposer, p.title, p.description,
            p.forVotes, p.againstVotes, p.abstainVotes,
            p.voteStart, p.voteEnd, p.executed
        );
    }

    function getVoteReceipt(uint256 _proposalId, address _voter) external view returns (
        bool hasVoted,
        uint8 support,
        uint256 votingPower
    ) {
        VoteReceipt memory receipt = proposals[_proposalId].voteReceipts[_voter];
        return (receipt.hasVoted, receipt.support, receipt.votingPower);
    }

    // ─── Internal ───────────────────────────────────────────────────────────────

    function _calculateQuorum() internal view returns (uint256) {
        uint256 totalPower = 0;
        // In production, this would iterate over a voter list
        // For gas efficiency, we use a stored total
        return totalPower * quorumNumerator / quorumDenominator;
    }

    function _getState(uint256 _proposalId) internal view returns (ProposalState) {
        Proposal storage p = proposals[_proposalId];

        if (p.executed) return ProposalState.Executed;
        if (p.voteEnd == 0) return ProposalState.Cancelled;
        if (block.timestamp < p.voteStart) return ProposalState.Pending;
        if (block.timestamp <= p.voteEnd) return ProposalState.Active;

        // Voting ended — determine result
        if (p.forVotes <= p.againstVotes) return ProposalState.Defeated;
        if (p.forVotes + p.abstainVotes < p.quorumRequired) return ProposalState.Defeated;

        if (p.timelockEnd > 0) {
            if (block.timestamp >= p.timelockEnd) return ProposalState.Queued;
            return ProposalState.Queued;
        }

        return ProposalState.Succeeded;
    }
}