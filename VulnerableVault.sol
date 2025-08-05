// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract VulnerableVault {
    mapping(address => uint256) public balances;
    
    // Events
    event Deposit(address indexed user, uint256 amount);
    event Withdraw(address indexed user, uint256 amount);
    
    // Deposit ETH
    function deposit() public payable {
        require(msg.value > 0, "Must deposit something");
        balances[msg.sender] += msg.value;
        emit Deposit(msg.sender, msg.value);
    }
    
    // Vulnerable withdraw function - reentrancy vulnerability
    function withdraw(uint256 amount) public {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        
        // VULNERABILITY: External call before state update
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");
        
        // State update after external call - reentrancy vulnerability!
        balances[msg.sender] -= amount;
        
        emit Withdraw(msg.sender, amount);
    }
    
    // Get vault balance
    function getVaultBalance() public view returns (uint256) {
        return address(this).balance;
    }
    
    // Get user balance
    function getUserBalance(address user) public view returns (uint256) {
        return balances[user];
    }
    
    // Fallback to receive ETH
    receive() external payable {
        deposit();
    }
}