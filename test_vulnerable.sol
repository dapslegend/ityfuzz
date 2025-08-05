// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract VulnerableBank {
    mapping(address => uint256) public balances;
    
    function deposit() public payable {
        balances[msg.sender] += msg.value;
    }
    
    function withdraw(uint256 amount) public {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        
        // Vulnerable: state change after external call (reentrancy)
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");
        
        balances[msg.sender] -= amount;
    }
    
    function emergencyWithdraw(address token) public {
        // Vulnerable: no access control
        payable(msg.sender).transfer(address(this).balance);
    }
    
    function calculateReward(uint256 balance, uint256 multiplier) public pure returns (uint256) {
        // Vulnerable: integer overflow
        return balance * multiplier;
    }
}
