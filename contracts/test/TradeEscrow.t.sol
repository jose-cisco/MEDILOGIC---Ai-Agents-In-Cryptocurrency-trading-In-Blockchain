// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../TradeEscrow.sol";

contract TradeEscrowTest is Test {
    TradeEscrow public escrow;
    
    address public owner = address(0x1);
    address public tradingAgent = address(0x2);
    address public feeRecipient = address(0x3);
    address public x402Recipient = address(0x4);
    address public user = address(0x5);
    
    // Mock ERC20 token
    MockERC20 public token;
    
    function setUp() public {
        vm.startPrank(owner);
        
        escrow = new TradeEscrow(
            tradingAgent,
            feeRecipient,
            x402Recipient,
            100 ether,  // max trade size
            10          // daily trade limit
        );
        
        // Deploy mock token
        token = new MockERC20("Test Token", "TEST", 18);
        
        // Add token as supported
        escrow.addSupportedToken(address(token));
        
        vm.stopPrank();
    }
    
    // ─── Deployment Tests ─────────────────────────────────────────────────────
    
    function test_Deployment() public view {
        assertEq(escrow.owner(), owner);
        assertEq(escrow.tradingAgent(), tradingAgent);
        assertEq(escrow.feeRecipient(), feeRecipient);
        assertEq(escrow.x402Recipient(), x402Recipient);
        assertEq(escrow.maxTradeSize(), 100 ether);
        assertEq(escrow.dailyTradeLimit(), 10);
        assertEq(escrow.tradingFeeBps(), 50);  // 0.5%
        assertEq(escrow.profitShareBps(), 1000);  // 10%
    }
    
    // ─── Deposit Tests ────────────────────────────────────────────────────────
    
    function test_DepositETH() public {
        vm.deal(user, 10 ether);
        
        vm.prank(user);
        escrow.depositETH{value: 5 ether}();
        
        assertEq(escrow.tradingBalance(), 5 ether);
        assertEq(escrow.tokenBalances(address(0)), 5 ether);
    }
    
    function test_DepositToken() public {
        token.mint(user, 1000 * 10**18);
        
        vm.startPrank(user);
        token.approve(address(escrow), 500 * 10**18);
        escrow.depositToken(address(token), 500 * 10**18);
        vm.stopPrank();
        
        assertEq(escrow.tradingBalance(), 500 * 10**18);
        assertEq(escrow.tokenBalances(address(token)), 500 * 10**18);
    }
    
    // ─── Trade Execution Tests ────────────────────────────────────────────────
    
    function test_ExecuteTrade() public {
        // Deposit ETH first
        vm.deal(user, 10 ether);
        vm.prank(user);
        escrow.depositETH{value: 10 ether}();
        
        // Execute trade as trading agent
        vm.startPrank(tradingAgent);
        
        bytes32 tradeId = keccak256("trade1");
        uint256 fee = escrow.executeTrade(
            tradeId,
            address(0),  // ETH
            address(token),  // token out
            1 ether,
            100 * 10**18,
            true  // is profit
        );
        
        vm.stopPrank();
        
        // Fee should be 0.5% of 1 ether = 0.005 ether
        assertEq(fee, 0.005 ether);
        assertEq(escrow.totalTrades(), 1);
        assertEq(escrow.totalFeesCollected(), 0.005 ether);
    }
    
    function test_ExecuteTradeOnlyAgent() public {
        vm.prank(user);
        vm.expectRevert("TradeEscrow: only trading agent");
        escrow.executeTrade(
            keccak256("trade1"),
            address(0),
            address(token),
            1 ether,
            100 * 10**18,
            true
        );
    }
    
    function test_ExecuteTradeDailyLimit() public {
        // Deposit ETH
        vm.deal(user, 100 ether);
        vm.prank(user);
        escrow.depositETH{value: 100 ether}();
        
        // Execute 10 trades (daily limit)
        vm.startPrank(tradingAgent);
        for (uint i = 0; i < 10; i++) {
            escrow.executeTrade(
                keccak256(abi.encode(i)),
                address(0),
                address(token),
                1 ether,
                100 * 10**18,
                true
            );
        }
        
        // 11th trade should fail
        vm.expectRevert("TradeEscrow: daily trade limit reached");
        escrow.executeTrade(
            keccak256("trade11"),
            address(0),
            address(token),
            1 ether,
            100 * 10**18,
            true
        );
        vm.stopPrank();
    }
    
    // ─── Fee Configuration Tests ──────────────────────────────────────────────
    
    function test_SetFeeConfiguration() public {
        vm.prank(owner);
        escrow.setFeeConfiguration(100, 2000, 500);
        
        assertEq(escrow.tradingFeeBps(), 100);
        assertEq(escrow.profitShareBps(), 2000);
        assertEq(escrow.x402AllocationBps(), 500);
    }
    
    function test_SetFeeConfigurationTooHigh() public {
        vm.prank(owner);
        vm.expectRevert("TradeEscrow: trading fee too high");
        escrow.setFeeConfiguration(1001, 1000, 0);
    }
    
    // ─── Withdrawal Tests ─────────────────────────────────────────────────────
    
    function test_WithdrawProfits() public {
        // Setup: deposit and execute profitable trade
        vm.deal(user, 10 ether);
        vm.prank(user);
        escrow.depositETH{value: 10 ether}();
        
        vm.prank(tradingAgent);
        escrow.executeTrade(
            keccak256("trade1"),
            address(0),
            address(token),
            1 ether,
            100 * 10**18,
            true  // is profit
        );
        
        // Withdraw profits
        uint256 ownerBalanceBefore = owner.balance;
        vm.prank(owner);
        escrow.withdrawProfits(address(0), escrow.totalProfit());
        
        assertGt(owner.balance, ownerBalanceBefore);
    }
    
    function test_WithdrawProfitsOnlyOwner() public {
        vm.prank(user);
        vm.expectRevert("TradeEscrow: only owner");
        escrow.withdrawProfits(address(0), 1 ether);
    }
    
    // ─── Admin Tests ──────────────────────────────────────────────────────────
    
    function test_SetTradingAgent() public {
        address newAgent = address(0x999);
        vm.prank(owner);
        escrow.setTradingAgent(newAgent);
        
        assertEq(escrow.tradingAgent(), newAgent);
    }
    
    function test_TransferOwnership() public {
        address newOwner = address(0x999);
        
        vm.prank(owner);
        escrow.transferOwnership(newOwner);
        
        assertEq(escrow.pendingOwner(), newOwner);
        
        vm.prank(newOwner);
        escrow.acceptOwnership();
        
        assertEq(escrow.owner(), newOwner);
    }
    
    function test_AddSupportedToken() public {
        MockERC20 newToken = new MockERC20("New Token", "NEW", 18);
        
        vm.prank(owner);
        escrow.addSupportedToken(address(newToken));
        
        assertTrue(escrow.supportedTokens(address(newToken)));
    }
}

// Mock ERC20 for testing
contract MockERC20 {
    string public name;
    string public symbol;
    uint8 public decimals;
    uint256 public totalSupply;
    
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;
    
    constructor(string memory _name, string memory _symbol, uint8 _decimals) {
        name = _name;
        symbol = _symbol;
        decimals = _decimals;
    }
    
    function mint(address to, uint256 amount) external {
        balanceOf[to] += amount;
        totalSupply += amount;
    }
    
    function transfer(address to, uint256 amount) external returns (bool) {
        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;
        return true;
    }
    
    function transferFrom(address from, address to, uint256 amount) external returns (bool) {
        allowance[from][msg.sender] -= amount;
        balanceOf[from] -= amount;
        balanceOf[to] += amount;
        return true;
    }
    
    function approve(address spender, uint256 amount) external returns (bool) {
        allowance[msg.sender][spender] = amount;
        return true;
    }
}