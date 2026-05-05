// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract LibraryCoin {
    string public name = "Library Coin";
    string public symbol = "LBC";
    uint8 public decimals = 18;
    uint256 public totalSupply;

    address public admin;
    mapping(address => uint256) private _balances;
    mapping(address => mapping(address => uint256)) private _allowances;

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
    event Minted(address indexed to, uint256 amount);
    event OwnershipTransferred(address indexed previousAdmin, address indexed newAdmin);

    modifier onlyAdmin() {
        require(msg.sender == admin, "LibraryCoin: caller is not the admin");
        _;
    }

    constructor() {
        admin = msg.sender;
    }

    function balanceOf(address account) public view returns (uint256) {
        return _balances[account];
    }

    function transfer(address to, uint256 amount) public returns (bool) {
        require(to != address(0), "LibraryCoin: transfer to the zero address");
        require(_balances[msg.sender] >= amount, "LibraryCoin: insufficient balance");

        _balances[msg.sender] -= amount;
        _balances[to] += amount;

        emit Transfer(msg.sender, to, amount);
        return true;
    }

    function approve(address spender, uint256 amount) public returns (bool) {
        require(spender != address(0), "LibraryCoin: approve to the zero address");
        _allowances[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }

    function allowance(address owner, address spender) public view returns (uint256) {
        return _allowances[owner][spender];
    }

    function transferFrom(address from, address to, uint256 amount) public returns (bool) {
        require(from != address(0), "LibraryCoin: transfer from the zero address");
        require(to != address(0), "LibraryCoin: transfer to the zero address");
        require(_balances[from] >= amount, "LibraryCoin: insufficient balance");
        require(_allowances[from][msg.sender] >= amount, "LibraryCoin: allowance exceeded");

        _balances[from] -= amount;
        _balances[to] += amount;
        _allowances[from][msg.sender] -= amount;

        emit Transfer(from, to, amount);
        return true;
    }

    function mint(address to, uint256 amount) public onlyAdmin {
        require(to != address(0), "LibraryCoin: mint to the zero address");
        require(amount > 0, "LibraryCoin: mint amount must be greater than zero");

        totalSupply += amount;
        _balances[to] += amount;

        emit Transfer(address(0), to, amount);
        emit Minted(to, amount);
    }

    // NEW: Function to transfer coin contract ownership
    function transferOwnership(address newAdmin) public onlyAdmin {
        require(newAdmin != address(0), "LibraryCoin: new admin is the zero address");
        require(newAdmin != admin, "LibraryCoin: new admin is same as current admin");

        address previousAdmin = admin;
        admin = newAdmin;

        emit OwnershipTransferred(previousAdmin, newAdmin);
    }
}