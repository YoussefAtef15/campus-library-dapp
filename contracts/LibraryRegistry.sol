// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

interface ILibraryCoin {
    function balanceOf(address account) external view returns (uint256);
    function allowance(address owner, address spender) external view returns (uint256);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
}

contract LibraryRegistry {

    address public admin;
    bool public paused;
    ILibraryCoin public coin;

    uint256 public constant MAX_BORROW_LIMIT = 3;

    struct Book {
        uint256 id;
        string title;
        string author;
        uint256 basePrice;
        string imageHash;
        string pdfHash;
        bool available;
        bool exists;
    }

    struct LoanRecord {
        address borrower;
        uint256 borrowedAt;
        uint256 expiresAt;
        uint256 returnedAt;
        bool returned;
    }

    uint256 public bookCount;

    mapping(uint256 => Book) public books;
    mapping(uint256 => LoanRecord[]) public loanHistory;
    mapping(address => string) public userNames;
    mapping(address => bool) public isRegistered;
    mapping(address => uint256[]) public userBorrowedBooks;

    // Dynamic Pricing Mappings
    mapping(uint256 => uint256[]) public bookDurations;
    mapping(uint256 => mapping(uint256 => uint256)) public durationPrices;

    event BookAdded(uint256 indexed id, string title, string author, uint256 basePrice);
    event BookUpdated(uint256 indexed id, string title, string author, uint256 basePrice);
    event BookStatusChanged(uint256 indexed id, bool exists);
    event BookBorrowed(address indexed borrower, uint256 indexed bookId, uint256 timestamp, uint256 expiresAt, uint256 finalPrice);
    event BookReturned(address indexed borrower, uint256 indexed bookId, uint256 timestamp);
    event UserRegistered(address indexed user, string name);
    event OwnershipTransferred(address indexed previousAdmin, address indexed newAdmin);
    event Paused(address indexed by);
    event Resumed(address indexed by);

    modifier onlyOwner() {
        require(msg.sender == admin, "LibraryRegistry: caller is not the admin");
        _;
    }

    modifier whenNotPaused() {
        require(!paused, "LibraryRegistry: contract is paused");
        _;
    }

    constructor(address _coinAddress) {
        admin = msg.sender;
        paused = false;
        bookCount = 0;
        coin = ILibraryCoin(_coinAddress);
    }

    function getAdmin() public view returns (address) {
        return admin;
    }

    function addBook(
        string memory title,
        string memory author,
        uint256 basePrice,
        string memory imageHash,
        string memory pdfHash,
        uint256[] memory durations,
        uint256[] memory prices
    ) public onlyOwner {
        require(bytes(title).length > 0, "LibraryRegistry: title cannot be empty");
        require(bytes(author).length > 0, "LibraryRegistry: author cannot be empty");
        require(durations.length == prices.length, "LibraryRegistry: durations and prices length mismatch");

        bookCount++;
        books[bookCount] = Book({
            id: bookCount,
            title: title,
            author: author,
            basePrice: basePrice,
            imageHash: imageHash,
            pdfHash: pdfHash,
            available: true,
            exists: true
        });

        for (uint256 i = 0; i < durations.length; i++) {
            bookDurations[bookCount].push(durations[i]);
            durationPrices[bookCount][durations[i]] = prices[i];
        }

        emit BookAdded(bookCount, title, author, basePrice);
    }

    function updateBook(
        uint256 bookId,
        string memory title,
        string memory author,
        uint256 basePrice,
        string memory imageHash,
        string memory pdfHash,
        uint256[] memory durations,
        uint256[] memory prices
    ) public onlyOwner {
        require(books[bookId].exists, "LibraryRegistry: book does not exist");
        require(bytes(title).length > 0, "LibraryRegistry: title cannot be empty");
        require(bytes(author).length > 0, "LibraryRegistry: author cannot be empty");
        require(durations.length == prices.length, "LibraryRegistry: durations and prices length mismatch");

        books[bookId].title = title;
        books[bookId].author = author;
        books[bookId].basePrice = basePrice;
        books[bookId].imageHash = imageHash;
        books[bookId].pdfHash = pdfHash;

        delete bookDurations[bookId];

        for (uint256 i = 0; i < durations.length; i++) {
            bookDurations[bookId].push(durations[i]);
            durationPrices[bookId][durations[i]] = prices[i];
        }

        emit BookUpdated(bookId, title, author, basePrice);
    }

    function toggleBookExistence(uint256 bookId) public onlyOwner {
        require(bookId > 0 && bookId <= bookCount, "LibraryRegistry: invalid book id");
        books[bookId].exists = !books[bookId].exists;

        if(!books[bookId].exists) {
             books[bookId].available = false;
        } else {
             // Check if it's currently borrowed before making it available
             bool isBorrowed = false;
             LoanRecord[] storage records = loanHistory[bookId];
             if (records.length > 0 && !records[records.length - 1].returned) {
                 isBorrowed = true;
             }
             books[bookId].available = !isBorrowed;
        }

        emit BookStatusChanged(bookId, books[bookId].exists);
    }

    function batchAddBooks(
        string[] memory titles,
        string[] memory authors,
        uint256[] memory basePrices,
        string[] memory imageHashes,
        string[] memory pdfHashes,
        uint256[][] memory durations,
        uint256[][] memory prices
    ) public onlyOwner {
        require(titles.length > 0, "LibraryRegistry: titles array is empty");
        require(
            titles.length == authors.length &&
            authors.length == basePrices.length &&
            basePrices.length == imageHashes.length &&
            imageHashes.length == pdfHashes.length &&
            pdfHashes.length == durations.length &&
            durations.length == prices.length,
            "LibraryRegistry: arrays length mismatch"
        );

        for (uint256 i = 0; i < titles.length; i++) {
            addBook(titles[i], authors[i], basePrices[i], imageHashes[i], pdfHashes[i], durations[i], prices[i]);
        }
    }

    function registerUser(string memory name) public whenNotPaused {
        require(!isRegistered[msg.sender], "LibraryRegistry: user already registered");
        require(bytes(name).length > 0, "LibraryRegistry: name cannot be empty");

        userNames[msg.sender] = name;
        isRegistered[msg.sender] = true;

        emit UserRegistered(msg.sender, name);
    }

    function borrowBook(uint256 bookId, uint256 duration) public whenNotPaused {
        require(isRegistered[msg.sender], "LibraryRegistry: user not registered");
        require(books[bookId].exists, "LibraryRegistry: book does not exist");
        require(books[bookId].available, "LibraryRegistry: book is not available");
        require(userBorrowedBooks[msg.sender].length < MAX_BORROW_LIMIT, "LibraryRegistry: limit reached");

        bool validDuration = false;
        uint256 durationPrice = 0;
        for (uint256 i = 0; i < bookDurations[bookId].length; i++) {
            if (bookDurations[bookId][i] == duration) {
                validDuration = true;
                durationPrice = durationPrices[bookId][duration];
                break;
            }
        }
        require(validDuration, "LibraryRegistry: invalid duration selected");

        uint256 finalPrice = books[bookId].basePrice + durationPrice;

        require(coin.balanceOf(msg.sender) >= finalPrice, "LibraryRegistry: insufficient LBC balance");
        require(coin.allowance(msg.sender, address(this)) >= finalPrice, "LibraryRegistry: insufficient allowance");

        require(coin.transferFrom(msg.sender, admin, finalPrice), "LibraryRegistry: payment transfer failed");

        books[bookId].available = false;
        uint256 expiresAt = block.timestamp + duration;

        loanHistory[bookId].push(LoanRecord({
            borrower: msg.sender,
            borrowedAt: block.timestamp,
            expiresAt: expiresAt,
            returnedAt: 0,
            returned: false
        }));

        userBorrowedBooks[msg.sender].push(bookId);

        emit BookBorrowed(msg.sender, bookId, block.timestamp, expiresAt, finalPrice);
    }

    function returnBook(uint256 bookId) public whenNotPaused {
        require(!books[bookId].available, "LibraryRegistry: book is already available");

        LoanRecord[] storage records = loanHistory[bookId];
        bool found = false;
        for (uint256 i = records.length; i > 0; i--) {
            if (records[i - 1].borrower == msg.sender && !records[i - 1].returned) {
                records[i - 1].returned = true;
                records[i - 1].returnedAt = block.timestamp;
                found = true;
                break;
            }
        }

        require(found, "LibraryRegistry: no active loan found for this user and book");

        // Only make it available if the Admin didn't delete it
        if(books[bookId].exists) {
            books[bookId].available = true;
        }

        uint256[] storage userBooks = userBorrowedBooks[msg.sender];
        for (uint256 i = 0; i < userBooks.length; i++) {
            if (userBooks[i] == bookId) {
                userBooks[i] = userBooks[userBooks.length - 1];
                userBooks.pop();
                break;
            }
        }

        emit BookReturned(msg.sender, bookId, block.timestamp);
    }

    function hasActiveAccess(uint256 bookId, address user) public view returns (bool) {
        LoanRecord[] storage records = loanHistory[bookId];
        for (uint256 i = records.length; i > 0; i--) {
            if (records[i - 1].borrower == user && !records[i - 1].returned) {
                return block.timestamp <= records[i - 1].expiresAt;
            }
        }
        return false;
    }

    function getUserBorrowedBooks(address user) public view returns (uint256[] memory) {
        return userBorrowedBooks[user];
    }

    function getBookPricing(uint256 bookId) public view returns (uint256[] memory, uint256[] memory) {
        uint256[] memory durs = bookDurations[bookId];
        uint256[] memory prs = new uint256[](durs.length);
        for(uint i=0; i<durs.length; i++) {
            prs[i] = durationPrices[bookId][durs[i]];
        }
        return (durs, prs);
    }

    function getBook(uint256 bookId) public view returns (
        uint256 id,
        string memory title,
        string memory author,
        uint256 basePrice,
        string memory imageHash,
        string memory pdfHash,
        bool available,
        bool exists
    ) {
        Book storage b = books[bookId];
        return (b.id, b.title, b.author, b.basePrice, b.imageHash, b.pdfHash, b.available, b.exists);
    }

    function getLoanCount(uint256 bookId) public view returns (uint256) {
        return loanHistory[bookId].length;
    }

    function pause() public onlyOwner {
        require(!paused, "LibraryRegistry: already paused");
        paused = true;
        emit Paused(msg.sender);
    }

    function resume() public onlyOwner {
        require(paused, "LibraryRegistry: not paused");
        paused = false;
        emit Resumed(msg.sender);
    }

    function transferOwnership(address newAdmin) public onlyOwner {
        require(newAdmin != address(0), "LibraryRegistry: new admin is the zero address");
        require(newAdmin != admin, "LibraryRegistry: new admin is same as current admin");
        address previousAdmin = admin;
        admin = newAdmin;
        emit OwnershipTransferred(previousAdmin, newAdmin);
    }
}