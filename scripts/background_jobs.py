import json
import csv
import os
import time
import sys
from web3 import Web3
from web3.logs import DISCARD
from datetime import datetime

# RPC Configuration
GANACHE_URL = "http://127.0.0.1:7545"
CONFIG_FILE = "../config.json"
POLL_INTERVAL = 2


def load_config():
    """Loads contract addresses and ABIs from the generated config file."""
    if not os.path.exists(CONFIG_FILE):
        print("ERROR: config.json not found. Run auto_setup.py first.")
        sys.exit(1)
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)


def connect():
    """Returns a connected Web3 instance."""
    w3 = Web3(Web3.HTTPProvider(GANACHE_URL))
    if not w3.is_connected():
        print("ERROR: Cannot connect to Ganache.")
        sys.exit(1)
    return w3


def get_contracts(w3, config):
    """Initializes and returns contract objects."""
    coin = w3.eth.contract(
        address=config["coin"]["address"],
        abi=config["coin"]["abi"]
    )
    registry = w3.eth.contract(
        address=config["registry"]["address"],
        abi=config["registry"]["abi"]
    )
    return coin, registry


def decode_event(w3, registry, receipt, event_name):
    """Safely decodes events from a transaction receipt."""
    try:
        if event_name == "BookBorrowed":
            logs = registry.events.BookBorrowed().process_receipt(receipt, errors=DISCARD)
        elif event_name == "BookReturned":
            logs = registry.events.BookReturned().process_receipt(receipt, errors=DISCARD)
        else:
            return []
        return logs
    except Exception:
        return []


def scan_block_for_alerts(w3, registry, block_number):
    """Scans a specific block for borrow/return events to trigger live alerts."""
    alerts = []
    try:
        block = w3.eth.get_block(block_number, full_transactions=True)
        registry_address = registry.address.lower()

        for tx in block.transactions:
            # Handle Web3 AttributeDict dynamically
            tx_to = tx.get("to") if hasattr(tx, 'get') else None

            if tx_to and tx_to.lower() == registry_address:
                try:
                    receipt = w3.eth.get_transaction_receipt(tx["hash"])

                    borrowed_logs = decode_event(w3, registry, receipt, "BookBorrowed")
                    for log in borrowed_logs:
                        borrower = log["args"]["borrower"]
                        book_id = log["args"]["bookId"]
                        alerts.append(
                            f"ALERT: A book was just borrowed! (Book ID {book_id} by {borrower})"
                        )

                    returned_logs = decode_event(w3, registry, receipt, "BookReturned")
                    for log in returned_logs:
                        borrower = log["args"]["borrower"]
                        book_id = log["args"]["bookId"]
                        alerts.append(
                            f"ALERT: A book was just returned! (Book ID {book_id} by {borrower})"
                        )
                except Exception:
                    continue
    except Exception:
        pass
    return alerts


def run_live_alert_monitor(w3, registry):
    """Runs a continuous loop to monitor new blocks for library activity."""
    print("Starting live alert monitor. Press Ctrl+C to stop.")
    print("Watching for BookBorrowed and BookReturned events ...\n")

    last_block = w3.eth.block_number
    print(f"Current block: {last_block}. Waiting for new blocks ...\n")

    while True:
        try:
            current_block = w3.eth.block_number
            if current_block > last_block:
                for block_num in range(last_block + 1, current_block + 1):
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    alerts = scan_block_for_alerts(w3, registry, block_num)
                    for alert in alerts:
                        print(f"[{timestamp}] {alert}")
                last_block = current_block
            time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            print("\nAlert monitor stopped.")
            break
        except Exception as e:
            print("Monitor error:", str(e))
            time.sleep(POLL_INTERVAL)


def collect_all_accounts(w3, registry, coin):
    """Scans the entire blockchain history to extract all active account addresses."""
    accounts_set = set(w3.eth.accounts)  # Include default Ganache accounts
    registry_address = registry.address.lower()
    coin_address = coin.address.lower()
    latest = w3.eth.block_number

    for block_num in range(0, latest + 1):
        if block_num % 10 == 0 or block_num == latest:
            print(f"Scanning block {block_num}...")

        try:
            block = w3.eth.get_block(block_num, full_transactions=True)
            for tx in block.transactions:
                # Safely extract addresses regardless of Web3 version dict structure
                if isinstance(tx, dict) or hasattr(tx, 'get'):
                    from_addr = tx.get("from")
                    to_addr = tx.get("to")
                else:
                    tx_obj = w3.eth.get_transaction(tx)
                    from_addr = tx_obj.get("from")
                    to_addr = tx_obj.get("to")

                if from_addr:
                    accounts_set.add(from_addr)
                if to_addr:
                    accounts_set.add(to_addr)
        except Exception:
            continue

    # Clean up empty or null values
    accounts_set.discard(None)
    accounts_set.discard("")

    # Filter out smart contract addresses to only keep user accounts
    final_accounts = []
    for addr in accounts_set:
        if addr and addr.lower() not in [registry_address, coin_address]:
            final_accounts.append(addr)

    return final_accounts


def export_balance_snapshot(w3, registry, coin):
    """Generates a CSV report of LBC and ETH balances for all blockchain accounts based exactly on Final Project Guide."""
    print("\nScanning blockchain to collect all active accounts ...")

    accounts = collect_all_accounts(w3, registry, coin)
    print(f"\nTotal number of addresses found: {len(accounts)}")
    print("Computing balances ...")

    rows = []
    for addr in accounts:
        try:
            checksum_addr = w3.to_checksum_address(addr)

            # Fetch balances directly from the blockchain
            coin_balance_wei = coin.functions.balanceOf(checksum_addr).call()
            eth_balance_wei = w3.eth.get_balance(checksum_addr)

            # Format strictly as required
            coin_balance = float(w3.from_wei(coin_balance_wei, "ether"))
            eth_balance = float(w3.from_wei(eth_balance_wei, "ether"))

            rows.append({
                "Address": checksum_addr,
                "LibraryCoinBalance": str(int(coin_balance)) if coin_balance.is_integer() else f"{coin_balance:.4f}",
                "ETHBalance": f"{eth_balance:.6f}"
            })
        except Exception as e:
            print(f"  Skipping {addr}: {e}")

    # Ensure the 'data' directory exists dynamically based on the project structure
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
    os.makedirs(data_dir, exist_ok=True)

    # Save exactly as 'snapshot.csv' as required by guide
    csv_path = os.path.join(data_dir, "snapshot.csv")

    try:
        with open(csv_path, "w", newline="") as csvfile:
            # Exact columns requested
            fieldnames = ["Address", "LibraryCoinBalance", "ETHBalance"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        print(f"Balance snapshot successfully saved to: {os.path.abspath(csv_path)}")
    except Exception as e:
        print(f"  Failed to write CSV file: {e}")


def print_data_history_report(w3, registry):
    """Prints a fast analytical report of the most borrowed books."""
    print("\n--- Book Loan Frequency Report ---")
    try:
        total_books = registry.functions.bookCount().call()
    except Exception:
        print("Error fetching book count. Make sure the contract is deployed.")
        return

    if total_books == 0:
        print("No books in the registry.")
        return

    borrow_counts = {}
    for book_id in range(1, total_books + 1):
        try:
            loan_count = registry.functions.getLoanCount(book_id).call()
            book_data = registry.functions.getBook(book_id).call()
            # struct returns: (id, title, author, available)
            title = book_data[1]
            author = book_data[2]
            borrow_counts[book_id] = (title, author, loan_count)
        except Exception:
            continue

    # Sort books by number of loans (descending)
    sorted_books = sorted(borrow_counts.items(), key=lambda x: x[1][2], reverse=True)

    print("\n" + "-" * 65)
    print(f"{'ID':<5} {'Title':<35} {'Author':<18} {'Loans':<6}")
    print("-" * 65)
    for book_id, (title, author, count) in sorted_books:
        print(f"{book_id:<5} {title[:33]:<35} {author[:16]:<18} {count:<6}")
    print("-" * 65)


def main():
    config = load_config()
    w3 = connect()
    coin, registry = get_contracts(w3, config)

    print("=== Background Jobs ===")
    print("  1. Run Live Alert Monitor")
    print("  2. Export Balance Snapshot to CSV")
    print("  3. Print Data History Report")
    choice = input("Choice: ").strip()

    if choice == "1":
        run_live_alert_monitor(w3, registry)
    elif choice == "2":
        export_balance_snapshot(w3, registry, coin)
    elif choice == "3":
        print_data_history_report(w3, registry)
    else:
        print("Invalid choice.")


if __name__ == "__main__":
    main()