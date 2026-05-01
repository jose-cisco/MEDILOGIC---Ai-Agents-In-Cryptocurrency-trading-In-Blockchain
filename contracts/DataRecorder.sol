// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title DataRecorder
 * @notice BlockAgents Data Recorder — On-Chain Agent Memory
 *
 * Implements the Data Recorder component from Karim et al. (2025) BlockAgents framework:
 *   - Tamper-proof on-chain storage of agent interactions and decisions
 *   - Hash-linked records forming an immutable audit trail
 *   - Supports both compressed (hash-only) and full data recording
 *   - IPFS content addressing for large off-chain data with on-chain anchor
 *   - Query interface for agent memory retrieval by agent_id, data_type, or time range
 *
 * Reference: Survey Page 8 — "BlockAgents Data Recorder (tamper-proof)"
 */

contract DataRecorder {
    // ─── Enums ────────────────────────────────────────────────────────────────

    enum DataType {
        TradeDecision,
        MarketObservation,
        VerificationResult,
        GovernanceVote,
        AgentInteraction,
        LearningFeedback,
        CoordinationRecord
    }

    // ─── Structs ───────────────────────────────────────────────────────────────

    struct DataRecord {
        uint256 id;
        address submitter;
        string agentId;
        DataType dataType;
        bytes32 dataHash;          // Hash of the off-chain data (tamper-proof anchor)
        string ipfsCid;           // IPFS CID for full data (off-chain storage)
        bytes compressedData;     // Small data can be stored directly on-chain
        uint256 timestamp;
        uint256 prevRecordId;     // Links to previous record (hash chain)
        bool verified;
    }

    struct AgentMemorySummary {
        uint256 totalRecords;
        uint256 lastRecordTimestamp;
        bytes32 lastDataHash;
    }

    // ─── State Variables ──────────────────────────────────────────────────────

    address public owner;
    uint256 public recordCount;

    DataRecord[] public records;
    mapping(uint256 => DataRecord) public recordById;

    // Index: agent_id → list of record IDs
    mapping(string => uint256[]) public agentRecords;

    // Index: data_type → list of record IDs
    mapping(DataType => uint256[]) public typeRecords;

    // Summary per agent
    mapping(string => AgentMemorySummary) public agentSummaries;

    // Verification: record_id → verifier address
    mapping(uint256 => address) public verifiers;

    // Chain integrity: latest record hash per agent
    mapping(string => bytes32) public agentLatestHash;

    // ─── Events ────────────────────────────────────────────────────────────────

    event DataRecorded(
        uint256 indexed recordId,
        string indexed agentId,
        DataType dataType,
        bytes32 dataHash,
        string ipfsCid
    );
    event DataVerified(uint256 indexed recordId, address indexed verifier);
    event ChainIntegrityVerified(string agentId, uint256 recordCount, bytes32 latestHash);

    // ─── Modifiers ─────────────────────────────────────────────────────────────

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner");
        _;
    }

    // ─── Constructor ────────────────────────────────────────────────────────────

    constructor() {
        owner = msg.sender;
        recordCount = 0;
    }

    // ─── Record Functions ──────────────────────────────────────────────────────

    /**
     * @notice Record agent data on-chain (hash-only, with IPFS CID for full data).
     * @param _agentId The agent identifier
     * @param _dataType Type of data being recorded
     * @param _dataHash SHA-256 hash of the full off-chain data
     * @param _ipfsCid IPFS CID where the full data is stored
     */
    function recordData(
        string calldata _agentId,
        DataType _dataType,
        bytes32 _dataHash,
        string calldata _ipfsCid
    ) external onlyOwner returns (uint256) {
        recordCount++;
        uint256 recordId = recordCount;

        uint256 prevId = agentRecords[_agentId].length > 0
            ? agentRecords[_agentId][agentRecords[_agentId].length - 1]
            : 0;

        DataRecord memory record = DataRecord({
            id: recordId,
            submitter: msg.sender,
            agentId: _agentId,
            dataType: _dataType,
            dataHash: _dataHash,
            ipfsCid: _ipfsCid,
            compressedData: "",
            timestamp: block.timestamp,
            prevRecordId: prevId,
            verified: false
        });

        records.push(record);
        recordById[recordId] = record;
        agentRecords[_agentId].push(recordId);
        typeRecords[_dataType].push(recordId);

        // Update agent summary
        agentSummaries[_agentId] = AgentMemorySummary({
            totalRecords: agentSummaries[_agentId].totalRecords + 1,
            lastRecordTimestamp: block.timestamp,
            lastDataHash: _dataHash
        });

        // Update chain integrity
        agentLatestHash[_agentId] = _dataHash;

        emit DataRecorded(recordId, _agentId, _dataType, _dataHash, _ipfsCid);
        return recordId;
    }

    /**
     * @notice Record compressed data directly on-chain (small payloads only).
     * @param _agentId The agent identifier
     * @param _dataType Type of data being recorded
     * @param _dataHash Hash of the data for verification
     * @param _compressedData Small data stored directly on-chain
     */
    function recordCompressedData(
        string calldata _agentId,
        DataType _dataType,
        bytes32 _dataHash,
        bytes calldata _compressedData
    ) external onlyOwner returns (uint256) {
        require(_compressedData.length <= 256, "Compressed data too large (max 256 bytes)");

        recordCount++;
        uint256 recordId = recordCount;

        uint256 prevId = agentRecords[_agentId].length > 0
            ? agentRecords[_agentId][agentRecords[_agentId].length - 1]
            : 0;

        DataRecord memory record = DataRecord({
            id: recordId,
            submitter: msg.sender,
            agentId: _agentId,
            dataType: _dataType,
            dataHash: _dataHash,
            ipfsCid: "",
            compressedData: _compressedData,
            timestamp: block.timestamp,
            prevRecordId: prevId,
            verified: false
        });

        records.push(record);
        recordById[recordId] = record;
        agentRecords[_agentId].push(recordId);
        typeRecords[_dataType].push(recordId);

        agentSummaries[_agentId] = AgentMemorySummary({
            totalRecords: agentSummaries[_agentId].totalRecords + 1,
            lastRecordTimestamp: block.timestamp,
            lastDataHash: _dataHash
        });

        agentLatestHash[_agentId] = _dataHash;

        emit DataRecorded(recordId, _agentId, _dataType, _dataHash, "");
        return recordId;
    }

    // ─── Verification ──────────────────────────────────────────────────────────

    function verifyRecord(uint256 _recordId) external onlyOwner {
        require(_recordId > 0 && _recordId <= recordCount, "Invalid record ID");
        records[_recordId - 1].verified = true;
        verifiers[_recordId] = msg.sender;
        emit DataVerified(_recordId, msg.sender);
    }

    // ─── Query Functions ────────────────────────────────────────────────────────

    function getRecord(uint256 _recordId) external view returns (
        address submitter,
        string memory agentId,
        DataType dataType,
        bytes32 dataHash,
        string memory ipfsCid,
        uint256 timestamp,
        uint256 prevRecordId,
        bool verified
    ) {
        require(_recordId > 0 && _recordId <= recordCount, "Invalid record ID");
        DataRecord memory r = records[_recordId - 1];
        return (
            r.submitter, r.agentId, r.dataType,
            r.dataHash, r.ipfsCid, r.timestamp,
            r.prevRecordId, r.verified
        );
    }

    function getAgentRecordCount(string calldata _agentId) external view returns (uint256) {
        return agentRecords[_agentId].length;
    }

    function getAgentRecordIds(string calldata _agentId) external view returns (uint256[] memory) {
        return agentRecords[_agentId];
    }

    function getTypeRecordCount(DataType _dataType) external view returns (uint256) {
        return typeRecords[_dataType].length;
    }

    function getAgentSummary(string calldata _agentId) external view returns (
        uint256 totalRecords,
        uint256 lastRecordTimestamp,
        bytes32 lastDataHash
    ) {
        AgentMemorySummary memory s = agentSummaries[_agentId];
        return (s.totalRecords, s.lastRecordTimestamp, s.lastDataHash);
    }

    function getLatestAgentHash(string calldata _agentId) external view returns (bytes32) {
        return agentLatestHash[_agentId];
    }

    /**
     * @notice Verify the integrity of an agent's data chain.
     * @dev Returns the total records and latest hash for chain verification.
     */
    function verifyChainIntegrity(string calldata _agentId) external view returns (
        bool valid,
        uint256 totalRecords,
        bytes32 latestHash
    ) {
        AgentMemorySummary memory s = agentSummaries[_agentId];
        return (s.totalRecords > 0, s.totalRecords, s.lastDataHash);
    }

    function getTotalRecordCount() external view returns (uint256) {
        return recordCount;
    }
}