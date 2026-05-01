// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../BillRegistry.sol";
import "../VerificationAgent.sol";
import "../ActivityLogger.sol";

/// @notice Tests that only the owner can call protected functions
contract BillRegistrySecurityTest is Test {
    BillRegistry public registry;
    address owner = address(0xA0CE);
    address attacker = address(0xBAD);

    function setUp() public {
        vm.prank(owner);
        registry = new BillRegistry();
    }

    function testOwnerCanRecordPayment() public {
        vm.prank(owner);
        registry.recordPayment(address(0x1), 100);
        assertTrue(registry.hasPaid(address(0x1)));
    }

    function testRevert_NonOwnerCannotRecordPaymentAlt() public {
        vm.prank(attacker);
        vm.expectRevert("Only owner");
        registry.recordPayment(address(0x1), 100);
    }

    function testRevert_NonOwnerCannotRecordPayment() public {
        vm.prank(attacker);
        vm.expectRevert("Only owner");
        registry.recordPayment(address(0x2), 200);
    }

    function testRevert_NonOwnerCannotReward() public {
        vm.prank(attacker);
        vm.expectRevert("Only owner");
        registry.rewardAgent(address(attacker), 1 ether);
    }
}

contract VerificationAgentSecurityTest is Test {
    VerificationAgent public agent;
    address owner = address(0xA0CE);
    address attacker = address(0xBAD);

    function setUp() public {
        vm.prank(owner);
        agent = new VerificationAgent(7500);
    }

    function testOwnerCanVerifyTrade() public {
        bytes32 hash = keccak256("trade1");
        vm.prank(owner);
        agent.verifyTrade(hash, owner, address(0x1), true, "ok");
        assertTrue(agent.verifiedTrades(hash));
    }

    function testRevert_NonOwnerCannotVerify() public {
        vm.prank(attacker);
        vm.expectRevert("Only owner");
        agent.verifyTrade(keccak256("bad"), attacker, attacker, true, "hack");
    }
}

contract ActivityLoggerSecurityTest is Test {
    ActivityLogger public logger;
    address owner = address(0xA0CE);
    address attacker = address(0xBAD);

    function setUp() public {
        vm.prank(owner);
        logger = new ActivityLogger();
    }

    function testOwnerCanLog() public {
        vm.prank(owner);
        logger.logActivity("agent-1", keccak256("event1"));
        assertEq(logger.getActivityCount(), 1);
    }

    function testRevert_NonOwnerCannotLog() public {
        vm.prank(attacker);
        vm.expectRevert("Only owner");
        logger.logActivity("agent-1", keccak256("event1"));
    }

    function testRevert_InvalidHash() public {
        vm.prank(owner);
        vm.expectRevert("invalid hash");
        logger.logActivity("agent-1", bytes32(0));
    }
}