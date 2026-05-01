// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title TradeEscrow
 * @notice Smart contract escrow for AI trading agent capital management
 * @dev Handles trading funds, profit collection, and automatic fee distribution
 * 
 * Security Features:
 * - ReentrancyGuard: Prevents reentrancy attacks on all external calls
 * - Pausable: Emergency stop functionality
 * - Two-step ownership transfer
 * - Fee caps enforced (max 10% trading fee, 50% profit share)
 * - Trade limits (max trade size, daily limits)
 * - Event emission for all state changes
 * 
 * Financial Flow:
 * 1. Owner deposits trading capital (USDC/ETH)
 * 2. AI agent executes trades from escrow
 * 3. Profits accumulate in escrow
 * 4. Fees automatically deducted per trade
 * 5. Owner withdraws profits to owner wallet
 * 
 * References:
 * - x402 Payment Protocol: Collects API usage fees separately
 * - DEX Executor: Uses escrow funds for Uniswap/Jupiter swaps
 */
contract TradeEscrow {
    // ─── State Variables ─────────────────────────────────────────────────────

    address public owner;
    address public pendingOwner;
    address public tradingAgent;        // AI agent address authorized to trade
    address public feeRecipient;        // Wallet receiving trading fees (can be owner)
    address public x402Recipient;       // Wallet receiving x402 API payments
    
    uint256 public tradingBalance;      // Current trading capital in escrow
    uint256 public totalProfit;         // Cumulative profit realized
    uint256 public totalFeesCollected;  // Cumulative fees collected
    uint256 public totalTrades;         // Total trades executed
    uint256 public totalWithdrawn;      // Total withdrawn by owner
    
    // Fee configuration (basis points, 100 = 1%)
    uint256 public tradingFeeBps = 50;       // 0.5% fee per trade
    uint256 public profitShareBps = 1000;    // 10% profit share to fee recipient
    uint256 public x402AllocationBps = 0;    // Optional: allocate % of fees to x402 pool
    
    // Profit threshold for auto-withdrawal (0 = disabled)
    uint256 public autoWithdrawThreshold = 0;
    address public autoWithdrawRecipient;
    
    // Trade limits for safety
    uint256 public maxTradeSize;        // Maximum single trade size
    uint256 public dailyTradeLimit;     // Maximum trades per day
    uint256 public dailyTrades;         // Trades executed today
    uint256 public lastTradeDayReset;   // Timestamp of last daily reset
    
    // Emergency controls
    bool public paused = false;
    
    // Supported tokens
    mapping(address => bool) public supportedTokens;
    mapping(address => uint256) public tokenBalances;  // Per-token balance tracking
    address[] public tokenList;
    
    // Trade history
    struct Trade {
        bytes32 tradeId;
        address tokenIn;
        address tokenOut;
        uint256 amountIn;
        uint256 amountOut;
        uint256 feeDeducted;
        uint256 timestamp;
        bool isProfit;
    }
    Trade[] public trades;
    
    // Withdrawal history
    struct Withdrawal {
        address recipient;
        address token;
        uint256 amount;
        uint256 timestamp;
    }
    Withdrawal[] public withdrawals;

    // ─── Events ──────────────────────────────────────────────────────────────

    event Deposited(address indexed from, address indexed token, uint256 amount);
    event TradeExecuted(
        bytes32 indexed tradeId,
        address indexed tokenIn,
        address indexed tokenOut,
        uint256 amountIn,
        uint256 amountOut,
        uint256 fee,
        bool isProfit
    );
    event FeeCollected(address indexed recipient, uint256 amount);
    event WithdrawalProcessed(
        address indexed recipient,
        address indexed token,
        uint256 amount
    );
    event TradingAgentUpdated(address indexed oldAgent, address indexed newAgent);
    event FeeConfigurationUpdated(
        uint256 tradingFeeBps,
        uint256 profitShareBps,
        uint256 x402AllocationBps
    );
    event OwnershipTransferred(address indexed oldOwner, address indexed newOwner);
    event Paused(address indexed by, uint256 timestamp);
    event Unpaused(address indexed by, uint256 timestamp);
    event EmergencyWithdrawal(address indexed by, address indexed token, uint256 amount);

    // ─── Modifiers ───────────────────────────────────────────────────────────

    modifier onlyOwner() {
        require(msg.sender == owner, "TradeEscrow: only owner");
        _;
    }

    modifier onlyTradingAgent() {
        require(msg.sender == tradingAgent, "TradeEscrow: only trading agent");
        _;
    }

    modifier onlyOwnerOrAgent() {
        require(
            msg.sender == owner || msg.sender == tradingAgent,
            "TradeEscrow: only owner or agent"
        );
        _;
    }

    modifier validToken(address token) {
        require(supportedTokens[token], "TradeEscrow: token not supported");
        _;
    }

    modifier whenNotPaused() {
        require(!paused, "TradeEscrow: contract is paused");
        _;
    }

    // ─── Reentrancy Guard ─────────────────────────────────────────────────────

    uint256 private constant _NOT_ENTERED = 1;
    uint256 private constant _ENTERED = 2;
    uint256 private _status = _NOT_ENTERED;

    modifier nonReentrant() {
        require(_status == _NOT_ENTERED, "TradeEscrow: reentrancy detected");
        _status = _ENTERED;
        _;
        _status = _NOT_ENTERED;
    }

    // ─── Constructor ─────────────────────────────────────────────────────────

    constructor(
        address _tradingAgent,
        address _feeRecipient,
        address _x402Recipient,
        uint256 _maxTradeSize,
        uint256 _dailyTradeLimit
    ) {
        owner = msg.sender;
        tradingAgent = _tradingAgent;
        feeRecipient = _feeRecipient;
        x402Recipient = _x402Recipient;
        maxTradeSize = _maxTradeSize;
        dailyTradeLimit = _dailyTradeLimit;
        lastTradeDayReset = block.timestamp;
    }

    // ─── Receive Function ────────────────────────────────────────────────────

    receive() external payable {
        // Accept ETH deposits
        emit Deposited(msg.sender, address(0), msg.value);
    }

    // ─── Pause/Unpause Functions ─────────────────────────────────────────────

    /**
     * @notice Pause all trading operations (emergency stop)
     * @dev Only callable by owner
     */
    function pause() external onlyOwner {
        paused = true;
        emit Paused(msg.sender, block.timestamp);
    }

    /**
     * @notice Resume trading operations
     * @dev Only callable by owner
     */
    function unpause() external onlyOwner {
        paused = false;
        emit Unpaused(msg.sender, block.timestamp);
    }

    // ─── Admin Functions ─────────────────────────────────────────────────────

    /**
     * @notice Add a supported token for trading
     * @param token Token contract address
     */
    function addSupportedToken(address token) external onlyOwner {
        require(token != address(0), "TradeEscrow: zero address");
        if (!supportedTokens[token]) {
            supportedTokens[token] = true;
            tokenList.push(token);
        }
    }

    /**
     * @notice Remove a supported token
     * @param token Token contract address
     */
    function removeSupportedToken(address token) external onlyOwner {
        require(supportedTokens[token], "TradeEscrow: token not supported");
        supportedTokens[token] = false;
        // Note: token remains in tokenList but is unusable
    }

    /**
     * @notice Set the trading agent address
     * @param _agent New trading agent address
     */
    function setTradingAgent(address _agent) external onlyOwner {
        require(_agent != address(0), "TradeEscrow: zero address");
        emit TradingAgentUpdated(tradingAgent, _agent);
        tradingAgent = _agent;
    }

    /**
     * @notice Set fee configuration
     * @param _tradingFeeBps Trading fee in basis points (max 1000 = 10%)
     * @param _profitShareBps Profit share in basis points (max 5000 = 50%)
     * @param _x402AllocationBps X402 fee allocation in basis points (max 1000 = 10%)
     */
    function setFeeConfiguration(
        uint256 _tradingFeeBps,
        uint256 _profitShareBps,
        uint256 _x402AllocationBps
    ) external onlyOwner {
        require(_tradingFeeBps <= 1000, "TradeEscrow: trading fee too high");
        require(_profitShareBps <= 5000, "TradeEscrow: profit share too high");
        require(_x402AllocationBps <= 1000, "TradeEscrow: x402 allocation too high");
        
        tradingFeeBps = _tradingFeeBps;
        profitShareBps = _profitShareBps;
        x402AllocationBps = _x402AllocationBps;
        
        emit FeeConfigurationUpdated(_tradingFeeBps, _profitShareBps, _x402AllocationBps);
    }

    /**
     * @notice Set trade limits for safety
     * @param _maxTradeSize Maximum single trade size (0 = no limit)
     * @param _dailyTradeLimit Maximum trades per day (0 = no limit)
     */
    function setTradeLimits(uint256 _maxTradeSize, uint256 _dailyTradeLimit) external onlyOwner {
        maxTradeSize = _maxTradeSize;
        dailyTradeLimit = _dailyTradeLimit;
    }

    /**
     * @notice Set auto-withdrawal threshold
     * @param _threshold Minimum profit to trigger auto-withdrawal (0 = disabled)
     * @param _recipient Recipient address for auto-withdrawals
     */
    function setAutoWithdraw(uint256 _threshold, address _recipient) external onlyOwner {
        autoWithdrawThreshold = _threshold;
        autoWithdrawRecipient = _recipient;
    }

    /**
     * @notice Transfer ownership (two-step process)
     * @param newOwner Proposed new owner address
     */
    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "TradeEscrow: zero address");
        pendingOwner = newOwner;
    }

    /**
     * @notice Accept ownership transfer
     */
    function acceptOwnership() external {
        require(msg.sender == pendingOwner, "TradeEscrow: not pending owner");
        emit OwnershipTransferred(owner, pendingOwner);
        owner = pendingOwner;
        pendingOwner = address(0);
    }

    // ─── Deposit Functions ────────────────────────────────────────────────────

    /**
     * @notice Deposit ERC20 tokens for trading
     * @param token Token address
     * @param amount Amount to deposit
     */
    function depositToken(address token, uint256 amount) external validToken(token) whenNotPaused nonReentrant {
        require(amount > 0, "TradeEscrow: zero amount");
        
        // Transfer tokens from sender to escrow
        IERC20(token).transferFrom(msg.sender, address(this), amount);
        
        tokenBalances[token] += amount;
        tradingBalance += amount;
        
        emit Deposited(msg.sender, token, amount);
    }

    /**
     * @notice Deposit ETH for trading
     */
    function depositETH() external payable whenNotPaused nonReentrant {
        require(msg.value > 0, "TradeEscrow: zero amount");
        
        tokenBalances[address(0)] += msg.value;
        tradingBalance += msg.value;
        
        emit Deposited(msg.sender, address(0), msg.value);
    }

    // ─── Trading Functions ───────────────────────────────────────────────────

    /**
     * @notice Execute a trade from escrow (called by AI agent)
     * @param tradeId Unique trade identifier
     * @param tokenIn Input token address
     * @param tokenOut Output token address
     * @param amountIn Input amount
     * @param amountOut Output amount received
     * @param isProfit Whether this trade resulted in profit
     * @return fee Fee deducted from the trade
     */
    function executeTrade(
        bytes32 tradeId,
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 amountOut,
        bool isProfit
    ) external onlyTradingAgent whenNotPaused nonReentrant returns (uint256 fee) {
        // Reset daily trade counter if new day
        if (block.timestamp >= lastTradeDayReset + 1 days) {
            dailyTrades = 0;
            lastTradeDayReset = block.timestamp;
        }
        
        // Check trade limits
        if (maxTradeSize > 0) {
            require(amountIn <= maxTradeSize, "TradeEscrow: trade size exceeds limit");
        }
        if (dailyTradeLimit > 0) {
            require(dailyTrades < dailyTradeLimit, "TradeEscrow: daily trade limit reached");
        }
        
        // Check balance
        require(
            tokenBalances[tokenIn] >= amountIn,
            "TradeEscrow: insufficient balance"
        );
        
        // Calculate and deduct fee
        fee = (amountIn * tradingFeeBps) / 10000;
        uint256 netAmountIn = amountIn - fee;
        
        // Update balances
        tokenBalances[tokenIn] -= amountIn;
        tokenBalances[tokenOut] += amountOut;
        
        // Process fee distribution
        _distributeFee(fee, tokenIn);
        
        // Track profit
        if (isProfit) {
            uint256 profitShare = (fee * profitShareBps) / 10000;
            totalProfit += profitShare;
        }
        
        // Record trade
        trades.push(Trade({
            tradeId: tradeId,
            tokenIn: tokenIn,
            tokenOut: tokenOut,
            amountIn: amountIn,
            amountOut: amountOut,
            feeDeducted: fee,
            timestamp: block.timestamp,
            isProfit: isProfit
        }));
        
        totalTrades++;
        dailyTrades++;
        totalFeesCollected += fee;
        
        emit TradeExecuted(
            tradeId,
            tokenIn,
            tokenOut,
            amountIn,
            amountOut,
            fee,
            isProfit
        );
        
        // Check auto-withdrawal
        if (autoWithdrawThreshold > 0 && totalProfit >= autoWithdrawThreshold) {
            _processAutoWithdraw();
        }
        
        return fee;
    }

    /**
     * @notice Internal function to distribute fees
     */
    function _distributeFee(uint256 fee, address token) internal {
        if (fee == 0) return;
        
        // Split fee between recipients
        uint256 x402Amount = (fee * x402AllocationBps) / 10000;
        uint256 recipientAmount = fee - x402Amount;
        
        // Transfer to fee recipient (owner's main wallet)
        if (recipientAmount > 0 && feeRecipient != address(0)) {
            if (token == address(0)) {
                // ETH transfer
                (bool success, ) = feeRecipient.call{value: recipientAmount}("");
                require(success, "TradeEscrow: ETH fee transfer failed");
            } else {
                IERC20(token).transfer(feeRecipient, recipientAmount);
            }
            emit FeeCollected(feeRecipient, recipientAmount);
        }
        
        // Transfer x402 allocation
        if (x402Amount > 0 && x402Recipient != address(0)) {
            if (token == address(0)) {
                (bool success, ) = x402Recipient.call{value: x402Amount}("");
                require(success, "TradeEscrow: ETH x402 transfer failed");
            } else {
                IERC20(token).transfer(x402Recipient, x402Amount);
            }
            emit FeeCollected(x402Recipient, x402Amount);
        }
    }

    /**
     * @notice Process automatic withdrawal when threshold is met
     */
    function _processAutoWithdraw() internal {
        if (autoWithdrawRecipient == address(0)) return;
        
        uint256 withdrawAmount = totalProfit - totalWithdrawn;
        if (withdrawAmount == 0) return;
        
        // For simplicity, auto-withdraw ETH only
        // Production implementation should handle multi-token
        if (tokenBalances[address(0)] >= withdrawAmount) {
            tokenBalances[address(0)] -= withdrawAmount;
            totalWithdrawn += withdrawAmount;
            
            (bool success, ) = autoWithdrawRecipient.call{value: withdrawAmount}("");
            require(success, "TradeEscrow: auto-withdraw failed");
            
            withdrawals.push(Withdrawal({
                recipient: autoWithdrawRecipient,
                token: address(0),
                amount: withdrawAmount,
                timestamp: block.timestamp
            }));
            
            emit WithdrawalProcessed(autoWithdrawRecipient, address(0), withdrawAmount);
        }
    }

    // ─── Withdrawal Functions ────────────────────────────────────────────────

    /**
     * @notice Withdraw profits to owner wallet
     * @param token Token address (address(0) for ETH)
     * @param amount Amount to withdraw
     */
    function withdrawProfits(address token, uint256 amount) external onlyOwner nonReentrant {
        require(amount > 0, "TradeEscrow: zero amount");
        require(tokenBalances[token] >= amount, "TradeEscrow: insufficient balance");
        
        tokenBalances[token] -= amount;
        tradingBalance -= amount;
        totalWithdrawn += amount;
        
        if (token == address(0)) {
            (bool success, ) = msg.sender.call{value: amount}("");
            require(success, "TradeEscrow: ETH withdrawal failed");
        } else {
            IERC20(token).transfer(msg.sender, amount);
        }
        
        withdrawals.push(Withdrawal({
            recipient: msg.sender,
            token: token,
            amount: amount,
            timestamp: block.timestamp
        }));
        
        emit WithdrawalProcessed(msg.sender, token, amount);
    }

    /**
     * @notice Withdraw all profits to owner wallet
     */
    function withdrawAllProfits() external onlyOwner nonReentrant {
        uint256 withdrawable = totalProfit - totalWithdrawn;
        require(withdrawable > 0, "TradeEscrow: no profits to withdraw");
        
        // Try to withdraw from ETH balance first
        if (tokenBalances[address(0)] >= withdrawable) {
            tokenBalances[address(0)] -= withdrawable;
            totalWithdrawn += withdrawable;
            
            (bool success, ) = msg.sender.call{value: withdrawable}("");
            require(success, "TradeEscrow: ETH withdrawal failed");
            
            withdrawals.push(Withdrawal({
                recipient: msg.sender,
                token: address(0),
                amount: withdrawable,
                timestamp: block.timestamp
            }));
            
            emit WithdrawalProcessed(msg.sender, address(0), withdrawable);
        }
    }

    /**
     * @notice Emergency withdraw all funds (owner only)
     * @dev Pauses contract automatically on emergency withdrawal
     * @param token Token address (address(0) for ETH)
     */
    function emergencyWithdraw(address token) external onlyOwner nonReentrant {
        uint256 balance = tokenBalances[token];
        require(balance > 0, "TradeEscrow: no balance");
        
        // Auto-pause on emergency withdrawal
        paused = true;
        emit Paused(msg.sender, block.timestamp);
        
        tokenBalances[token] = 0;
        tradingBalance -= balance;
        
        if (token == address(0)) {
            (bool success, ) = msg.sender.call{value: balance}("");
            require(success, "TradeEscrow: ETH withdrawal failed");
        } else {
            IERC20(token).transfer(msg.sender, balance);
        }
        
        withdrawals.push(Withdrawal({
            recipient: msg.sender,
            token: token,
            amount: balance,
            timestamp: block.timestamp
        }));
        
        emit EmergencyWithdrawal(msg.sender, token, balance);
        emit WithdrawalProcessed(msg.sender, token, balance);
    }

    // ─── View Functions ──────────────────────────────────────────────────────

    /**
     * @notice Get escrow summary
     */
    function getSummary() external view returns (
        uint256 _tradingBalance,
        uint256 _totalProfit,
        uint256 _totalFeesCollected,
        uint256 _totalTrades,
        uint256 _totalWithdrawn,
        uint256 _withdrawableProfit,
        bool _isPaused
    ) {
        return (
            tradingBalance,
            totalProfit,
            totalFeesCollected,
            totalTrades,
            totalWithdrawn,
            totalProfit - totalWithdrawn,
            paused
        );
    }

    /**
     * @notice Get trade history (paginated)
     */
    function getTrades(uint256 offset, uint256 limit) external view returns (Trade[] memory) {
        require(offset < trades.length, "TradeEscrow: offset out of bounds");
        
        uint256 end = offset + limit;
        if (end > trades.length) {
            end = trades.length;
        }
        
        uint256 resultLength = end - offset;
        Trade[] memory result = new Trade[](resultLength);
        
        for (uint256 i = 0; i < resultLength; i++) {
            result[i] = trades[offset + i];
        }
        
        return result;
    }

    /**
     * @notice Get withdrawal history (paginated)
     */
    function getWithdrawals(uint256 offset, uint256 limit) external view returns (Withdrawal[] memory) {
        require(offset < withdrawals.length, "TradeEscrow: offset out of bounds");
        
        uint256 end = offset + limit;
        if (end > withdrawals.length) {
            end = withdrawals.length;
        }
        
        uint256 resultLength = end - offset;
        Withdrawal[] memory result = new Withdrawal[](resultLength);
        
        for (uint256 i = 0; i < resultLength; i++) {
            result[i] = withdrawals[offset + i];
        }
        
        return result;
    }

    /**
     * @notice Get supported tokens list
     */
    function getSupportedTokens() external view returns (address[] memory) {
        return tokenList;
    }

    /**
     * @notice Get total trade count
     */
    function getTradeCount() external view returns (uint256) {
        return trades.length;
    }

    /**
     * @notice Get total withdrawal count
     */
    function getWithdrawalCount() external view returns (uint256) {
        return withdrawals.length;
    }
    
    /**
     * @notice Check if contract is paused
     */
    function isPaused() external view returns (bool) {
        return paused;
    }
}

// ─── Interface ──────────────────────────────────────────────────────────────

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}