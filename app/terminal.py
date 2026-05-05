import os
import time
import getpass
import hashlib
import json
import csv
import sys
import re
import web3
from web3.logs import DISCARD

# RPC Configuration
RPC_URL = "http://127.0.0.1:7545"
# SHA-256 hash for the password 'admin123'
ADMIN_PASSWORD_HASH = "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9"


def load_deployment():
    """Loads contract addresses and ABIs from the generated config file."""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config.json")
    if not os.path.exists(config_path) or os.path.getsize(config_path) == 0:
        print("ERROR: config.json is missing or empty. Please run 'python scripts/auto_setup.py' first.")
        sys.exit(1)
    with open(config_path, "r") as f:
        config_data = json.load(f)
    return {
        "registry_address": config_data["registry"]["address"],
        "registry_abi": config_data["registry"]["abi"],
        "coin_address": config_data["coin"]["address"],
        "coin_abi": config_data["coin"]["abi"]
    }


def get_w3():
    """Returns a connected Web3 instance."""
    return web3.Web3(web3.Web3.HTTPProvider(RPC_URL))


def safe_transact(w3, contract_func, account):
    """
    Safely builds, signs, and sends a transaction.
    Extracts clean and user-friendly error messages if the transaction fails.
    """
    try:
        # Build transaction
        tx = contract_func.build_transaction({
            'from': account.address,
            'nonce': w3.eth.get_transaction_count(account.address),
            'gasPrice': w3.eth.gas_price
        })
        signed = w3.eth.account.sign_transaction(tx, account.key)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
        return receipt, None
    except Exception as e:
        err_str = str(e).lower()

        # Handle specific revert reasons cleanly
        if "does not exist" in err_str:
            return None, "Book does not exist."
        elif "paused" in err_str:
            return None, "Contract is currently paused."
        elif "not available" in err_str:
            return None, "Book is not available."
        elif "limit reached" in err_str:
            return None, "Maximum borrow limit reached."
        elif "insufficient lbc" in err_str:
            return None, "Insufficient Library Coin balance."
        elif "insufficient allowance" in err_str:
            return None, "Insufficient token allowance (You must approve first)."
        elif "payment transfer failed" in err_str:
            return None, "Payment failed during transfer."
        elif "invalid duration" in err_str:
            return None, "Invalid duration selected."

        match_reason = re.search(r"'reason':\s*'([^']+)'", err_str)
        if match_reason:
            return None, match_reason.group(1)

        return None, "Transaction failed. Please check inputs and state."


def load_contract(w3, name, abi):
    """Loads a contract instance using its name and ABI."""
    deploy = load_deployment()
    addr = deploy[name + "_address"]
    return w3.eth.contract(address=addr, abi=abi)


def prompt_registration(w3, registry, account):
    """Registers the user on their first login if not already registered."""
    registered = registry.functions.isRegistered(account.address).call()
    if not registered:
        name = input("Enter your display name: ").strip()
        if name:
            print("Registering user on blockchain... Please wait.")
            receipt, err = safe_transact(w3, registry.functions.registerUser(name), account)
            if err:
                print(f"Registration failed: {err}")
            else:
                print("User registered successfully.\n")


def show_header(w3, registry, account):
    """Displays the user's name or guest status."""
    name = registry.functions.userNames(account.address).call()
    if name:
        print(f"\n--- Campus Library (Logged in as: {name}) ---")
    else:
        print("\n--- Campus Library (Guest) ---")


def view_catalog(w3, registry):
    """Fetches and prints all active books dynamically using O(1) fetch."""
    print("\n[Library Catalog]")
    try:
        total = registry.functions.bookCount().call()
        if total == 0:
            print("  No books available in the catalog.")
        else:
            for i in range(1, total + 1):
                book = registry.functions.getBook(i).call()
                # struct: id, title, author, basePrice, imageHash, pdfHash, available, exists
                if book[7]:  # If exists == True
                    status = "Available" if book[6] else "Borrowed"
                    price_eth = w3.from_wei(book[3], "ether")
                    print(
                        f"  ID: {book[0]:<2} | Title: {book[1]:<25} | Author: {book[2]:<15} | Base Price: {price_eth} LBC | Status: {status}")
    except Exception as e:
        print(f"  Error fetching catalog: {e}")
    print("-" * 45)


def activity_history(w3, registry, coin, address):
    print(f"\n[Activity History for {address}]")
    found = False
    address_lower = address.lower()
    zero_addr = "0x0000000000000000000000000000000000000000"

    try:
        latest_block = w3.eth.block_number
        for i in range(latest_block + 1):
            try:
                block = w3.eth.get_block(i, full_transactions=True)
                for tx in block.transactions:
                    receipt = w3.eth.get_transaction_receipt(tx.hash)
                    if receipt['status'] != 1:
                        continue

                    borrows = registry.events.BookBorrowed().process_receipt(receipt, errors=DISCARD)
                    for b in borrows:
                        if b['args']['borrower'].lower() == address_lower:
                            paid = w3.from_wei(b['args']['finalPrice'], 'ether')
                            print(
                                f"  > [Block {b['blockNumber']:<4}] Borrowed Book ID: {b['args']['bookId']} (Paid: {paid} LBC)")
                            found = True

                    returns = registry.events.BookReturned().process_receipt(receipt, errors=DISCARD)
                    for r in returns:
                        if r['args']['borrower'].lower() == address_lower:
                            print(f"  > [Block {r['blockNumber']:<4}] Returned Book ID: {r['args']['bookId']}")
                            found = True

                    transfers = coin.events.Transfer().process_receipt(receipt, errors=DISCARD)
                    for t in transfers:
                        to_addr = t['args']['to'].lower()
                        from_addr = t['args']['from'].lower()

                        if to_addr == address_lower:
                            val = w3.from_wei(t['args']['value'], 'ether')
                            if from_addr == zero_addr:
                                print(f"  > [Block {t['blockNumber']:<4}] Minted/Received: {val} LBC (System)")
                            else:
                                print(f"  > [Block {t['blockNumber']:<4}] Received: {val} LBC")
                            found = True
                        elif from_addr == address_lower:
                            val = w3.from_wei(t['args']['value'], 'ether')
                            print(f"  > [Block {t['blockNumber']:<4}] Sent/Paid: {val} LBC")
                            found = True
            except Exception:
                pass

        if not found:
            print("  No activity found for this account.")
    except Exception as e:
        print(f"  Could not fetch history completely. Error: {e}")
    print("-" * 45)


def balance_checker(w3, registry, coin, address):
    try:
        coin_bal = coin.functions.balanceOf(address).call()
        eth_bal = w3.eth.get_balance(address)
        print("\n[Account Balances]")
        print(f"  Address: {address}")
        print(f"  Library Coin: {w3.from_wei(coin_bal, 'ether')} LBC")
        print(f"  ETH Balance:  {w3.from_wei(eth_bal, 'ether'):.4f} ETH")
    except Exception:
        print("  Error fetching balances.")
    print("-" * 45)


def get_pricing_inputs(w3):
    """Helper function to collect duration and pricing inputs from terminal."""
    durations = []
    prices = []
    print("\nDefine pricing tiers (0 to finish):")
    DAY = 86400;
    WEEK = 604800;
    MONTH = 2592000

    print("Standard durations: Day (86400), Week (604800), Month (2592000)")
    while True:
        try:
            d = int(input("Enter duration in seconds (or 0 to stop): "))
            if d == 0:
                if len(durations) == 0:
                    print("You must add at least one duration.")
                    continue
                break
            p = float(input(f"Enter additional LBC price for this duration: "))
            durations.append(d)
            prices.append(w3.to_wei(p, "ether"))
        except ValueError:
            print("Invalid input.")
    return durations, prices


def admin_menu(w3, registry, coin, account):
    pwd = getpass.getpass("Enter admin password: ")
    if hashlib.sha256(pwd.encode()).hexdigest() != ADMIN_PASSWORD_HASH:
        print("Access denied. Incorrect password.")
        return

    try:
        admin_addr = registry.functions.admin().call()
        if account.address.lower() != admin_addr.lower():
            print("Access denied. You are not the authorized contract admin.")
            return
    except Exception:
        print("Error verifying admin status.")
        return

    while True:
        print("\n==============================")
        print("ADMIN CONTROL PANEL")
        print("==============================")

        print("\n[1] Book Management")
        print("1. Add New Book")
        print("2. Update Book Info")
        print("3. Toggle Book Status (Hide/Show)")
        print("4. Batch Add Books")
        print("5. View All Books")

        print("\n[2] Coin Management")
        print("6. Mint Library Coins")
        print("7. View Total Minted Coins")

        print("\n[3] System Controls")
        print("8. Pause System (Emergency Stop)")
        print("9. Resume System")
        print("10. View System Status (Paused / Active)")

        print("\n[4] Analytics & Reports")
        print("11. View System Summary Dashboard")
        print("12. Export Balance Snapshot (CSV)")
        print("13. View Most Borrowed Books Report")

        print("\n[5] Ownership & Security")
        print("14. Transfer Admin Ownership")
        print("15. View Current Admin Address")

        print("\n[0] Exit Admin Panel")

        choice = input("\nEnter your choice: ").strip()

        if choice == "0":
            print("Exiting Admin Panel...")
            break

        elif choice == "1":
            title = input("Enter book title: ").strip()
            author = input("Enter book author: ").strip()
            if title and author:
                try:
                    bp = float(input("Enter base price (LBC): "))
                    basePrice = w3.to_wei(bp, "ether")
                    imgHash = input("Enter image hash/URL: ").strip()
                    pdfHash = input("Enter PDF hash/URL: ").strip()

                    durations, prices = get_pricing_inputs(w3)

                    print("Processing transaction...")
                    receipt, err = safe_transact(w3, registry.functions.addBook(
                        title, author, basePrice, imgHash, pdfHash, durations, prices
                    ), account)
                    print("Book added successfully." if not err else f"Failed: {err}")
                except ValueError:
                    print("Invalid numerical input.")
            else:
                print("Title and author cannot be empty.")

        elif choice == "2":
            try:
                bid = int(input("Enter Book ID to update: "))
                title = input("Enter NEW book title: ").strip()
                author = input("Enter NEW book author: ").strip()
                bp = float(input("Enter NEW base price (LBC): "))
                basePrice = w3.to_wei(bp, "ether")
                imgHash = input("Enter NEW image hash/URL: ").strip()
                pdfHash = input("Enter NEW PDF hash/URL: ").strip()

                durations, prices = get_pricing_inputs(w3)

                print("Processing transaction...")
                receipt, err = safe_transact(w3, registry.functions.updateBook(
                    bid, title, author, basePrice, imgHash, pdfHash, durations, prices
                ), account)
                print("Book updated successfully." if not err else f"Failed: {err}")
            except ValueError:
                print("Invalid numerical input.")

        elif choice == "3":
            try:
                bid = int(input("Enter Book ID to toggle status: "))
                print("Processing transaction...")
                receipt, err = safe_transact(w3, registry.functions.toggleBookExistence(bid), account)
                print("Book status toggled successfully." if not err else f"Failed: {err}")
            except ValueError:
                print("Invalid numerical input.")

        elif choice == "4":
            try:
                n = int(input("Number of books to batch add: "))
                titles = [];
                authors = [];
                basePrices = [];
                imgHashes = [];
                pdfHashes = [];
                all_durs = [];
                all_prices = []

                for i in range(n):
                    print(f"\n--- Book {i + 1} ---")
                    titles.append(input("Title: ").strip())
                    authors.append(input("Author: ").strip())
                    basePrices.append(w3.to_wei(float(input("Base Price (LBC): ")), "ether"))
                    imgHashes.append(input("Image Hash: ").strip())
                    pdfHashes.append(input("PDF Hash: ").strip())

                    durs, prs = get_pricing_inputs(w3)
                    all_durs.append(durs)
                    all_prices.append(prs)

                confirm = input(f"\nAre you sure you want to add {n} books? (y/n): ").strip().lower()
                if confirm == 'y':
                    print("Processing transaction...")
                    receipt, err = safe_transact(w3, registry.functions.batchAddBooks(
                        titles, authors, basePrices, imgHashes, pdfHashes, all_durs, all_prices
                    ), account)
                    print("Books added successfully." if not err else f"Failed: {err}")
            except ValueError:
                print("Invalid input format.")

        elif choice == "5":
            view_catalog(w3, registry)

        elif choice == "6":
            to_addr = input("Mint to address: ").strip()
            if w3.is_address(to_addr):
                try:
                    amt = float(input("Amount to mint (LBC): "))
                    amt_wei = w3.to_wei(amt, 'ether')
                    print("Processing transaction...")
                    receipt, err = safe_transact(w3, coin.functions.mint(w3.to_checksum_address(to_addr), amt_wei),
                                                 account)
                    print("Coins minted successfully." if not err else f"Failed: {err}")
                except ValueError:
                    print("Invalid amount.")
            else:
                print("Invalid address format.")

        elif choice == "7":
            try:
                total = coin.functions.totalSupply().call()
                print(f"Total Minted Coins: {w3.from_wei(total, 'ether')} LBC")
            except Exception as e:
                print(f"Error fetching total supply: {e}")

        elif choice == "8":
            print("Processing transaction...")
            receipt, err = safe_transact(w3, registry.functions.pause(), account)
            print("System paused." if not err else f"Failed: {err}")

        elif choice == "9":
            print("Processing transaction...")
            receipt, err = safe_transact(w3, registry.functions.resume(), account)
            print("System resumed." if not err else f"Failed: {err}")

        elif choice == "10":
            try:
                is_paused = registry.functions.paused().call()
                print(f"System Status: {'Paused' if is_paused else 'Active'}")
            except Exception as e:
                print(f"Error checking status: {e}")

        elif choice == "11":
            print("\n[System Summary Dashboard]")
            try:
                total_books = registry.functions.bookCount().call()
                total_minted = coin.functions.totalSupply().call()
                print(f"  - Total Books: {total_books}")
                print(f"  - Total Coins Minted: {w3.from_wei(total_minted, 'ether')} LBC")

                latest = w3.eth.block_number
                tx_count = 0
                user_tx_counts = {}
                admin_addr_lower = account.address.lower()

                print("  Scanning blocks for transaction data...")
                for block_num in range(latest + 1):
                    try:
                        block = w3.eth.get_block(block_num, full_transactions=True)
                        for tx in block.transactions:
                            tx_count += 1
                            sender = tx.get("from") if isinstance(tx, dict) else w3.eth.get_transaction(tx).get("from")
                            # Exclude Admin from Top Users Calculation
                            if sender and sender.lower() != admin_addr_lower:
                                user_tx_counts[sender] = user_tx_counts.get(sender, 0) + 1
                    except Exception:
                        continue

                print(f"  - Total Transactions: {tx_count}")
                top_users = sorted(user_tx_counts.items(), key=lambda x: x[1], reverse=True)[:3]
                print("  - Top Active Users:")
                if not top_users:
                    print("      No active users found yet.")
                for u, count in top_users:
                    print(f"      {u}: {count} txs")
            except Exception as e:
                print(f"Error loading dashboard: {e}")

        elif choice == "12":
            print("\n[Balance Snapshot Exporter]")
            print("Scanning blockchain for active accounts...")
            accounts_set = set(w3.eth.accounts)
            registry_address = registry.address.lower()
            coin_address = coin.address.lower()
            latest = w3.eth.block_number

            for block_num in range(0, latest + 1):
                if block_num % 10 == 0 or block_num == latest:
                    print(f"Scanning block {block_num} / {latest}...")
                try:
                    block = w3.eth.get_block(block_num, full_transactions=True)
                    for tx in block.transactions:
                        if isinstance(tx, dict) or hasattr(tx, 'get'):
                            from_addr = tx.get("from")
                            to_addr = tx.get("to")
                        else:
                            tx_obj = w3.eth.get_transaction(tx)
                            from_addr = tx_obj.get("from")
                            to_addr = tx_obj.get("to")

                        if from_addr: accounts_set.add(from_addr)
                        if to_addr: accounts_set.add(to_addr)
                except Exception:
                    continue

            accounts_set.discard(None)
            accounts_set.discard("")
            final_accounts = [a for a in accounts_set if a.lower() not in [registry_address, coin_address]]

            print(f"Total number of unique addresses found: {len(final_accounts)}")
            print("Fetching balances...")

            rows = []
            for addr in final_accounts:
                try:
                    checksum_addr = w3.to_checksum_address(addr)
                    c_bal = coin.functions.balanceOf(checksum_addr).call()
                    e_bal = w3.eth.get_balance(checksum_addr)
                    rows.append({
                        "Address": checksum_addr,
                        "LibraryCoinBalance": f"{float(w3.from_wei(c_bal, 'ether')):.4f}",
                        "ETHBalance": f"{float(w3.from_wei(e_bal, 'ether')):.6f}"
                    })
                except Exception:
                    pass

            data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
            os.makedirs(data_dir, exist_ok=True)
            csv_path = os.path.join(data_dir, "snapshot.csv")

            try:
                with open(csv_path, "w", newline="") as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=["Address", "LibraryCoinBalance", "ETHBalance"])
                    writer.writeheader()
                    writer.writerows(rows)
                print(f"Success! Exported {len(rows)} accounts to {os.path.abspath(csv_path)}")
            except Exception as e:
                print(f"Failed to write CSV: {e}")

        elif choice == "13":
            print("\n--- Most Borrowed Books Report ---")
            try:
                total_books = registry.functions.bookCount().call()
                if total_books == 0:
                    print("No books in the registry.")
                else:
                    borrow_counts = {}
                    for book_id in range(1, total_books + 1):
                        try:
                            loan_count = registry.functions.getLoanCount(book_id).call()
                            book_data = registry.functions.getBook(book_id).call()
                            if book_data[7]:  # if exists
                                borrow_counts[book_id] = (book_data[1], book_data[2], loan_count)
                        except Exception:
                            continue

                    sorted_books = sorted(borrow_counts.items(), key=lambda x: x[1][2], reverse=True)
                    print("-" * 65)
                    print(f"{'ID':<5} {'Title':<35} {'Author':<18} {'Loans':<6}")
                    print("-" * 65)
                    for book_id, (title, author, count) in sorted_books:
                        print(f"{book_id:<5} {title[:33]:<35} {author[:16]:<18} {count:<6}")
                    print("-" * 65)
            except Exception as e:
                print(f"Error generating report: {e}")

        elif choice == "14":
            new_addr = input("New admin address: ").strip()
            if w3.is_address(new_addr):
                print("Processing transaction for LibraryCoin...")
                receipt_coin, err_coin = safe_transact(w3, coin.functions.transferOwnership(new_addr), account)
                if err_coin:
                    print(f"Failed to transfer Coin ownership: {err_coin}")
                else:
                    print("Processing transaction for LibraryRegistry...")
                    receipt_reg, err_reg = safe_transact(w3, registry.functions.transferOwnership(new_addr), account)
                    if not err_reg:
                        print("Ownership transferred for both contracts successfully.")
                        print("Returning to Main Menu...")
                        break
                    else:
                        print(f"Failed to transfer Registry ownership: {err_reg}")
            else:
                print("Invalid address format.")

        elif choice == "15":
            try:
                admin_address = registry.functions.admin().call()
                print(f"Current Admin Address: {admin_address}")
            except Exception as e:
                print(f"Error fetching admin address: {e}")

        else:
            print("Invalid choice. Please try again.")


def main():
    w3 = get_w3()
    if not w3.is_connected():
        print("Cannot connect to Ganache node. Exiting.")
        return

    registry_abi = load_deployment()["registry_abi"]
    coin_abi = load_deployment()["coin_abi"]
    registry_address = load_deployment()["registry_address"]

    registry = load_contract(w3, "registry", registry_abi)
    coin = load_contract(w3, "coin", coin_abi)

    priv_key = input("Enter private key: ").strip()
    if not priv_key.startswith("0x"):
        priv_key = "0x" + priv_key

    try:
        account = w3.eth.account.from_key(priv_key)
    except Exception:
        print("Invalid private key format. Exiting.")
        return

    prompt_registration(w3, registry, account)

    while True:
        show_header(w3, registry, account)
        print("1. View Library Catalog")
        print("2. Borrow a Book")
        print("3. Return a Book")
        print("4. Read a Borrowed Book")
        print("5. My Activity History")
        print("6. Check My Balances")
        print("7. Admin Settings")
        print("8. Exit")
        choice = input("Select an option (1-8): ")

        if choice == "1":
            view_catalog(w3, registry)

        elif choice == "2":
            try:
                MAX_BORROW_LIMIT = registry.functions.MAX_BORROW_LIMIT().call()
            except Exception:
                MAX_BORROW_LIMIT = 3

            try:
                coin_bal = coin.functions.balanceOf(account.address).call()
                if coin_bal <= 0:
                    print("  [Error] Your Library Coin balance is 0. Transaction strictly blocked.")
                    continue
            except Exception:
                pass

            try:
                borrowed_ids = registry.functions.getUserBorrowedBooks(account.address).call()
                if len(borrowed_ids) >= MAX_BORROW_LIMIT:
                    print(f"  [Error] You have reached the maximum borrow limit of {MAX_BORROW_LIMIT} books.")
                    continue
            except Exception:
                pass

            print("\n[Available Books to Borrow]")
            available_books = []

            try:
                total_books = registry.functions.bookCount().call()
                for i in range(1, total_books + 1):
                    book = registry.functions.getBook(i).call()
                    if book[6] and book[7]:  # isAvailable and exists
                        available_books.append(book)
                        bp_eth = w3.from_wei(book[3], "ether")
                        print(
                            f"  {len(available_books)}. Title: '{book[1]}' (ID: {book[0]}) - Base Price: {bp_eth} LBC")
            except Exception:
                pass

            if not available_books:
                print("  No books are currently available to borrow.")
                continue

            try:
                selection = int(input("\nSelect the number of the book to borrow (or 0 to cancel): "))
                if selection == 0:
                    continue
                if 1 <= selection <= len(available_books):
                    selected_book = available_books[selection - 1]
                    bid = selected_book[0]
                    b_title = selected_book[1]
                    base_price = selected_book[3]

                    durs, prs = registry.functions.getBookPricing(bid).call()
                    if not durs:
                        print("  [Error] No pricing defined for this book.")
                        continue

                    print("\nAvailable Durations:")
                    for idx, d in enumerate(durs):
                        days = d // 86400
                        p_eth = w3.from_wei(prs[idx], "ether")
                        print(f"  {idx + 1}. {days} days (+{p_eth} LBC)")

                    dur_sel = int(input("\nSelect duration number: "))
                    if not (1 <= dur_sel <= len(durs)):
                        print("Invalid selection.")
                        continue

                    chosen_dur = durs[dur_sel - 1]
                    chosen_price = prs[dur_sel - 1]
                    final_price = base_price + chosen_price
                    final_price_eth = w3.from_wei(final_price, "ether")

                    confirm = input(
                        f"Borrow '{b_title}' for {chosen_dur // 86400} days? Total Cost: {final_price_eth} LBC. (y/n): ").strip().lower()
                    if confirm != 'y':
                        continue

                    # 1. Approve Tokens
                    print(f"Approving {final_price_eth} LBC for LibraryRegistry...")
                    receipt, err = safe_transact(w3, coin.functions.approve(registry_address, final_price), account)
                    if err:
                        print(f"Approval failed: {err}")
                        continue

                    # 2. Borrow Book
                    print(f"Processing borrow transaction for Book ID {bid}...")
                    receipt, err = safe_transact(w3, registry.functions.borrowBook(bid, chosen_dur), account)
                    if not err:
                        print("Book Borrowed Successfully.")
                    else:
                        print(f"Failed: {err}")
                else:
                    print("Invalid selection.")
            except ValueError:
                print("Invalid input format.")

        elif choice == "3":
            print("\n[Your Borrowed Books]")
            borrowed_books = []

            try:
                borrowed_ids = registry.functions.getUserBorrowedBooks(account.address).call()
                for bid in borrowed_ids:
                    book = registry.functions.getBook(bid).call()
                    borrowed_books.append(book)
            except Exception as e:
                print(f"Error fetching borrowed books: {e}")

            if not borrowed_books:
                print("  You currently have no books to return.")
                continue

            for idx, book in enumerate(borrowed_books, 1):
                print(f"  {idx}. Title: '{book[1]}' (ID: {book[0]})")

            try:
                selection = int(input("\nSelect the number of the book to return (or 0 to cancel): "))
                if selection == 0:
                    continue
                if 1 <= selection <= len(borrowed_books):
                    bid = borrowed_books[selection - 1][0]
                    b_title = borrowed_books[selection - 1][1]

                    confirm = input(f"Are you sure you want to return '{b_title}'? (y/n): ").strip().lower()
                    if confirm != 'y':
                        print("Return cancelled.")
                        continue

                    print(f"Processing return for Book ID {bid}...")
                    receipt, err = safe_transact(w3, registry.functions.returnBook(bid), account)
                    if not err:
                        print("Book Returned Successfully.")
                    else:
                        print(f"Failed: {err}")
                else:
                    print("Invalid selection.")
            except ValueError:
                print("Invalid input format.")

        elif choice == "4":
            print("\n[Read a Borrowed Book]")
            borrowed_books = []
            try:
                borrowed_ids = registry.functions.getUserBorrowedBooks(account.address).call()
                for bid in borrowed_ids:
                    book = registry.functions.getBook(bid).call()
                    borrowed_books.append(book)
            except Exception as e:
                print(f"Error fetching borrowed books: {e}")

            if not borrowed_books:
                print("  You currently have no books to read.")
                continue

            for idx, book in enumerate(borrowed_books, 1):
                print(f"  {idx}. Title: '{book[1]}' (ID: {book[0]})")

            try:
                selection = int(input("\nSelect the number of the book to read (or 0 to cancel): "))
                if selection == 0:
                    continue
                if 1 <= selection <= len(borrowed_books):
                    selected_book = borrowed_books[selection - 1]

                    # Verify active access matching the GUI PDF Viewer protection
                    has_access = registry.functions.hasActiveAccess(selected_book[0], account.address).call()

                    if has_access:
                        print("\n" + "=" * 55)
                        print(f"📖 Opening PDF Viewer for: {selected_book[1]}")
                        print(f"🔗 File Hash Link: {selected_book[5]}")
                        print(">> [Simulated View: Imagine reading the secure PDF here...] <<")
                        print("=" * 55 + "\n")
                    else:
                        print("  [Error] Your borrow period for this book has expired. Please return it.")
                else:
                    print("Invalid selection.")
            except ValueError:
                print("Invalid input format.")

        elif choice == "5":
            addr = input("Press Enter to use your address, or paste another address: ").strip()
            if not addr:
                addr = account.address
            if w3.is_address(addr):
                activity_history(w3, registry, coin, addr)
            else:
                print("Invalid address format.")

        elif choice == "6":
            addr = input("Press Enter to use your address, or paste another address: ").strip()
            if not addr:
                addr = account.address
            if w3.is_address(addr):
                balance_checker(w3, registry, coin, addr)
            else:
                print("Invalid address format.")

        elif choice == "7":
            admin_menu(w3, registry, coin, account)

        elif choice == "8":
            print("Logging out... Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")
        time.sleep(1)


if __name__ == "__main__":
    main()