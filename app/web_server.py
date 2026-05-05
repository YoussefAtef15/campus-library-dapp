import json
import os
import sys
import csv
import hashlib
from werkzeug.utils import secure_filename
from flask import Flask, render_template, jsonify, request, send_from_directory, send_file
from web3 import Web3
from web3.logs import DISCARD
from datetime import datetime

# --- Configuration ---
GANACHE_URL = "http://127.0.0.1:7545"
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config.json")
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "uploads")

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize Flask, explicitly mapping the root URL to the frontend directory
app = Flask(__name__, static_folder=FRONTEND_DIR, template_folder=FRONTEND_DIR, static_url_path='')


def load_config():
    """Load contract addresses and ABIs from config.json."""
    if not os.path.exists(CONFIG_PATH):
        print("ERROR: config.json not found. Run scripts/auto_setup.py first.")
        sys.exit(1)
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def get_w3():
    """Return a connected Web3 instance."""
    w3 = Web3(Web3.HTTPProvider(GANACHE_URL))
    if not w3.is_connected():
        print("ERROR: Cannot connect to Ganache at", GANACHE_URL)
        sys.exit(1)
    return w3


def get_contracts(w3, config):
    """Initialize and return coin and registry contract objects."""
    coin = w3.eth.contract(address=config["coin"]["address"], abi=config["coin"]["abi"])
    registry = w3.eth.contract(address=config["registry"]["address"], abi=config["registry"]["abi"])
    return coin, registry


def safe_call(func, *args):
    """Safely call a Web3 contract view function with dynamic arguments, returning None on error."""
    try:
        return func(*args).call()
    except Exception as e:
        print(f"Blockchain read error: {e}")
        return None


def ensure_0x(key: str) -> str:
    """Ensures the private key has the 0x prefix required by Web3.py to prevent 400 Errors."""
    key = key.strip()
    if key and not key.startswith("0x"):
        return "0x" + key
    return key


def parse_tx_error(e):
    """Parses raw blockchain exception strings into clean, user-friendly messages."""
    err_str = str(e).lower()
    if "paused" in err_str: return "Contract is paused."
    if "does not exist" in err_str: return "Book not found."
    if "not available" in err_str: return "Book is not available."
    if "limit reached" in err_str: return "Maximum borrow limit reached."
    if "insufficient lbc" in err_str or "insufficient allowance" in err_str: return "Insufficient Library Coin balance or Allowance."
    if "insufficient funds" in err_str: return "Insufficient ETH for gas fees."
    if "active loan found" in err_str or "did not borrow" in err_str: return "You did not borrow this book."
    if "already registered" in err_str: return "User already registered."
    if "not the admin" in err_str or "caller is not the admin" in err_str: return "Access denied. Admin only."
    if "invalid duration" in err_str: return "Invalid duration selected."
    return "Transaction failed. Please check inputs."


def generate_file_hash(file_storage):
    """Generate SHA-256 hash for a given file and reset pointer."""
    if not file_storage: return ""
    file_storage.seek(0)
    file_hash = hashlib.sha256(file_storage.read()).hexdigest()
    file_storage.seek(0)
    return file_hash


def generate_safe_filename(file_hash, original_filename):
    """
    Truncates the filename to avoid Windows Max Path limits (260 chars)
    while preserving uniqueness using the hash.
    """
    ext = os.path.splitext(original_filename)[1]
    name_without_ext = os.path.splitext(secure_filename(original_filename))[0]
    short_name = name_without_ext[:25]
    return f"{file_hash[:15]}_{short_name}{ext}"


# ==========================================
#  HTML Page Routes
# ==========================================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/admin")
def admin_page():
    return render_template("admin.html")


@app.route("/dashboard")
def dashboard_page():
    return render_template("dashboard.html")


# ==========================================
#  Data & Files Routes
# ==========================================

@app.route("/data/<path:filename>")
def download_data(filename):
    """Securely serve files from the data directory for CSV downloads directly to user's device."""
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
    return send_from_directory(data_dir, filename, as_attachment=True)


@app.route("/uploads/<path:filename>")
def serve_uploads(filename):
    """Serve public files like book cover images from the uploads folder."""
    return send_from_directory(UPLOAD_FOLDER, filename)


# ==========================================
#  API Routes - Catalog & Books
# ==========================================

@app.route("/api/books")
def api_get_books():
    """Fetch all books from the registry contract including pricing and hashes."""
    w3 = get_w3()
    config = load_config()
    _, registry = get_contracts(w3, config)

    total = safe_call(registry.functions.bookCount) or 0
    books = []

    for i in range(1, total + 1):
        book = safe_call(registry.functions.getBook, i)
        if book:
            loan_count = safe_call(registry.functions.getLoanCount, i) or 0

            durs, prs = safe_call(registry.functions.getBookPricing, i) or ([], [])
            pricing = [{"duration": d, "price": float(w3.from_wei(p, "ether"))} for d, p in zip(durs, prs)]

            books.append({
                "id": book[0],
                "title": book[1],
                "author": book[2],
                "basePrice": float(w3.from_wei(book[3], "ether")),
                "imageHash": book[4],
                "pdfHash": book[5],
                "available": book[6],
                "exists": book[7],
                "borrowCount": loan_count,
                "pricing": pricing
            })

    return jsonify({"books": books})


@app.route("/api/books/image/<int:book_id>")
def api_book_image(book_id):
    """Serve the book cover image automatically based on the book_id."""
    w3 = get_w3()
    config = load_config()
    _, registry = get_contracts(w3, config)

    book_data = safe_call(registry.functions.getBook, book_id)
    if not book_data: return "Book not found", 404

    image_hash = book_data[4]
    if not image_hash: return "Image not found", 404

    for f in os.listdir(UPLOAD_FOLDER):
        if f.startswith(image_hash[:15]) and not f.lower().endswith(".pdf"):
            return send_from_directory(UPLOAD_FOLDER, f)

    return "Image file not found on server", 404


@app.route("/api/books/borrow", methods=["POST"])
def api_borrow_book():
    """Borrow a book. Approves coin usage first, then calls borrowBook."""
    data = request.get_json()
    if not data: return jsonify({"error": "Invalid request payload"}), 400

    w3 = get_w3()
    config = load_config()
    coin, registry = get_contracts(w3, config)

    private_key = ensure_0x(data.get("private_key", ""))
    book_id = data.get("book_id")
    duration = int(data.get("duration", 0))

    if not private_key or not book_id or not duration:
        return jsonify({"error": "Missing private_key, book_id, or duration"}), 400

    try:
        account = w3.eth.account.from_key(private_key)
    except Exception:
        return jsonify({"error": "Invalid private key format"}), 400

    try:
        # Get dynamic price for approval
        book_data = safe_call(registry.functions.getBook, int(book_id))
        durs, prs = safe_call(registry.functions.getBookPricing, int(book_id))

        duration_price = 0
        for d, p in zip(durs, prs):
            if d == duration:
                duration_price = p
                break

        final_price = book_data[3] + duration_price

        nonce = w3.eth.get_transaction_count(account.address)

        # 1. Approve LBC spending
        approve_tx = coin.functions.approve(registry.address, final_price).build_transaction({
            "from": account.address,
            "nonce": nonce,
            "gas": 100000,
            "gasPrice": w3.eth.gas_price
        })
        signed_approve = w3.eth.account.sign_transaction(approve_tx, private_key)
        w3.eth.send_raw_transaction(signed_approve.raw_transaction)

        # 2. Borrow Book
        tx = registry.functions.borrowBook(int(book_id), duration).build_transaction({
            "from": account.address,
            "nonce": nonce + 1,
            "gas": 400000,
            "gasPrice": w3.eth.gas_price
        })
        signed = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

        if receipt["status"] == 1:
            return jsonify({"success": True, "message": f"Book {book_id} borrowed successfully"})
        else:
            return jsonify({"error": "Transaction reverted on-chain"}), 400
    except Exception as e:
        return jsonify({"error": parse_tx_error(e)}), 400


@app.route("/api/books/return", methods=["POST"])
def api_return_book():
    """Return a book. Requires private_key and book_id in JSON body."""
    data = request.get_json()
    if not data: return jsonify({"error": "Invalid request payload"}), 400

    w3 = get_w3()
    config = load_config()
    _, registry = get_contracts(w3, config)

    private_key = ensure_0x(data.get("private_key", ""))
    book_id = data.get("book_id")

    if not private_key or not book_id: return jsonify({"error": "Missing private_key or book_id"}), 400

    try:
        account = w3.eth.account.from_key(private_key)
    except Exception:
        return jsonify({"error": "Invalid private key format"}), 400

    try:
        tx = registry.functions.returnBook(int(book_id)).build_transaction({
            "from": account.address,
            "nonce": w3.eth.get_transaction_count(account.address),
            "gas": 300000,
            "gasPrice": w3.eth.gas_price
        })
        signed = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

        if receipt["status"] == 1:
            return jsonify({"success": True, "message": f"Book {book_id} returned successfully"})
        else:
            return jsonify({"error": "Transaction reverted on-chain"}), 400
    except Exception as e:
        return jsonify({"error": parse_tx_error(e)}), 400


@app.route("/api/books/my-borrowed", methods=["POST"])
def api_my_borrowed():
    """Get books currently borrowed by the caller."""
    data = request.get_json()
    if not data: return jsonify({"error": "Invalid request payload"}), 400

    w3 = get_w3()
    config = load_config()
    _, registry = get_contracts(w3, config)

    address = data.get("address", "")
    if not w3.is_address(address): return jsonify({"error": "Invalid address"}), 400

    borrowed_ids = safe_call(registry.functions.getUserBorrowedBooks, w3.to_checksum_address(address)) or []
    books = []
    for bid in borrowed_ids:
        book = safe_call(registry.functions.getBook, bid)
        if book:
            books.append({"id": book[0], "title": book[1], "author": book[2]})

    return jsonify({"books": books})


@app.route("/api/books/read/<int:book_id>", methods=["GET"])
def api_read_book(book_id):
    """Protected PDF viewer endpoint. Validates Smart Contract access rights."""
    private_key = request.args.get("pk", "")
    if not private_key: return "Unauthorized. Provide private key.", 401

    w3 = get_w3()
    config = load_config()
    _, registry = get_contracts(w3, config)

    try:
        account = w3.eth.account.from_key(ensure_0x(private_key))
        addr = account.address
    except Exception:
        return "Invalid Auth details.", 401

    has_access = safe_call(registry.functions.hasActiveAccess, book_id, addr)
    admin_addr = safe_call(registry.functions.getAdmin)

    # Allow if the user has an active loan, or if they are the admin
    if not has_access and addr.lower() != admin_addr.lower():
        return "Access Denied. You do not have an active loan for this book, or it has expired.", 403

    book_data = safe_call(registry.functions.getBook, book_id)
    if not book_data: return "Book not found on blockchain.", 404

    pdf_hash = book_data[5]  # pdfHash in struct

    target_file = None
    for f in os.listdir(UPLOAD_FOLDER):
        if f.startswith(pdf_hash[:15]) and f.endswith(".pdf"):
            target_file = f
            break

    if not target_file:
        return "PDF file not found on the server.", 404

    # Send the PDF cleanly
    return send_from_directory(UPLOAD_FOLDER, target_file, mimetype='application/pdf')


# ==========================================
#  API Routes - Balances & History
# ==========================================

@app.route("/api/balance/<address>")
def api_balance(address):
    """Get LBC and ETH balance for any address."""
    w3 = get_w3()
    config = load_config()
    coin, _ = get_contracts(w3, config)

    if not w3.is_address(address): return jsonify({"error": "Invalid address"}), 400

    try:
        addr = w3.to_checksum_address(address)
        coin_bal = coin.functions.balanceOf(addr).call()
        eth_bal = w3.eth.get_balance(addr)

        return jsonify({
            "address": addr,
            "coin_balance": str(coin_bal),
            "coin_readable": float(w3.from_wei(coin_bal, "ether")),
            "eth_balance": str(eth_bal),
            "eth_readable": float(w3.from_wei(eth_bal, "ether"))
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/history/<address>")
def api_history(address):
    """Scan blockchain for all activity by a specific address."""
    w3 = get_w3()
    config = load_config()
    coin, registry = get_contracts(w3, config)

    if not w3.is_address(address): return jsonify({"error": "Invalid address"}), 400

    addr_lower = address.lower()
    zero_addr = "0x0000000000000000000000000000000000000000"
    activities = []

    try:
        latest = w3.eth.block_number
        for block_num in range(latest + 1):
            try:
                block = w3.eth.get_block(block_num, full_transactions=True)
                for tx in block.transactions:
                    try:
                        receipt = w3.eth.get_transaction_receipt(tx.hash)
                        if receipt["status"] != 1: continue

                        # Borrow events
                        for log in registry.events.BookBorrowed().process_receipt(receipt, errors=DISCARD):
                            if log["args"]["borrower"].lower() == addr_lower:
                                activities.append({
                                    "block": log["blockNumber"],
                                    "type": "BORROW",
                                    "detail": f"Borrowed Book ID: {log['args']['bookId']} - Paid: {float(w3.from_wei(log['args']['finalPrice'], 'ether'))} LBC"
                                })

                        # Return events
                        for log in registry.events.BookReturned().process_receipt(receipt, errors=DISCARD):
                            if log["args"]["borrower"].lower() == addr_lower:
                                activities.append({
                                    "block": log["blockNumber"],
                                    "type": "RETURN",
                                    "detail": f"Returned Book ID: {log['args']['bookId']}"
                                })

                        # Coin transfer events
                        for log in coin.events.Transfer().process_receipt(receipt, errors=DISCARD):
                            to_addr = log["args"]["to"].lower()
                            from_addr = log["args"]["from"].lower()
                            val = float(w3.from_wei(log["args"]["value"], "ether"))

                            if to_addr == addr_lower:
                                label = "Minted" if from_addr == zero_addr else "Received"
                                activities.append({
                                    "block": log["blockNumber"],
                                    "type": "MINT" if from_addr == zero_addr else "RECEIVED",
                                    "detail": f"{label} {val} LBC"
                                })
                            elif from_addr == addr_lower:
                                activities.append({
                                    "block": log["blockNumber"],
                                    "type": "SENT",
                                    "detail": f"Sent {val} LBC"
                                })
                    except Exception:
                        continue
            except Exception:
                continue
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"address": address, "activities": activities})


# ==========================================
#  API Routes - Dashboard Stats
# ==========================================

@app.route("/api/stats")
def api_stats():
    """Dashboard statistics. Total books counter reacts to user role (Admin vs Normal User)."""
    user_address = request.args.get("address", "")
    w3 = get_w3()
    config = load_config()
    coin, registry = get_contracts(w3, config)

    is_admin = False
    admin_addr_lower = ""

    try:
        admin_addr = safe_call(registry.functions.getAdmin)
        if admin_addr:
            admin_addr_lower = admin_addr.lower()
            if user_address and w3.to_checksum_address(user_address) == w3.to_checksum_address(admin_addr):
                is_admin = True
    except Exception:
        pass

    total_books_contract = safe_call(registry.functions.bookCount) or 0

    counted_total = 0
    available = 0
    books_data = []

    for i in range(1, total_books_contract + 1):
        book = safe_call(registry.functions.getBook, i)
        if book:
            # book[7] is exists status
            if is_admin or book[7]:
                counted_total += 1
                if book[6]: available += 1
                loan_count = safe_call(registry.functions.getLoanCount, i) or 0
                books_data.append({"title": book[1], "borrows": loan_count})

    total_minted = safe_call(coin.functions.totalSupply) or 0
    total_minted_readable = float(w3.from_wei(total_minted, "ether"))

    # Count total transactions by scanning blocks (excluding Admin from Active Users)
    latest = w3.eth.block_number
    tx_count = 0
    user_tx_counts = {}

    for block_num in range(latest + 1):
        try:
            block = w3.eth.get_block(block_num, full_transactions=True)
            for tx in block.transactions:
                tx_count += 1
                sender = tx.get("from")
                if sender and sender.lower() != admin_addr_lower:
                    user_tx_counts[sender] = user_tx_counts.get(sender, 0) + 1
        except Exception:
            continue

    top_users = sorted(user_tx_counts.items(), key=lambda x: x[1], reverse=True)[:3]
    top_users_list = [{"address": addr, "count": count} for addr, count in top_users]
    most_borrowed = sorted(books_data, key=lambda x: x["borrows"], reverse=True)[:5]

    return jsonify({
        "total_books": counted_total,  # Dynamic based on role
        "available": available,
        "total_minted": total_minted_readable,
        "total_transactions": tx_count,
        "top_users": top_users_list,  # Excludes admin
        "most_borrowed": most_borrowed,
        "block_number": latest
    })


# ==========================================
#  API Routes - Auth & Registration
# ==========================================

@app.route("/api/auth", methods=["POST"])
def api_auth():
    data = request.get_json()
    if not data: return jsonify({"error": "Invalid request payload"}), 400

    private_key = ensure_0x(data.get("private_key", ""))
    is_admin_login = data.get("is_admin_login", False)

    if not private_key or private_key == "0x":
        return jsonify({"error": "Missing private key"}), 400

    try:
        w3 = get_w3()
        config = load_config()
        _, registry = get_contracts(w3, config)
    except Exception as e:
        return jsonify({"error": "Could not connect to Ganache blockchain."}), 500

    try:
        account = w3.eth.account.from_key(private_key)
        addr = account.address
    except Exception:
        return jsonify({"error": "Invalid private key format."}), 400

    name = safe_call(registry.functions.userNames, addr) or ""
    registered = safe_call(registry.functions.isRegistered, addr) or False
    admin_addr = safe_call(registry.functions.getAdmin) or ""

    is_admin = bool(admin_addr and (addr.lower() == admin_addr.lower()))

    if is_admin_login and not is_admin:
        return jsonify({"error": "Access denied. Admin only."}), 400

    return jsonify({
        "address": addr,
        "name": name,
        "registered": registered,
        "is_admin": is_admin,
        "admin_address": admin_addr
    })


@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.get_json()
    if not data: return jsonify({"error": "Invalid request payload"}), 400

    w3 = get_w3()
    config = load_config()
    _, registry = get_contracts(w3, config)

    private_key = ensure_0x(data.get("private_key", ""))
    name = data.get("name", "")

    if not private_key or not name: return jsonify({"error": "Missing private_key or name"}), 400

    try:
        account = w3.eth.account.from_key(private_key)
    except Exception:
        return jsonify({"error": "Invalid private key format"}), 400

    try:
        tx = registry.functions.registerUser(name).build_transaction({
            "from": account.address,
            "nonce": w3.eth.get_transaction_count(account.address),
            "gas": 200000,
            "gasPrice": w3.eth.gas_price
        })
        signed = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

        if receipt["status"] == 1:
            return jsonify({"success": True, "message": "Registered successfully"})
        else:
            return jsonify({"error": "Registration reverted on-chain"}), 400
    except Exception as e:
        return jsonify({"error": parse_tx_error(e)}), 400


@app.route("/api/user/<address>")
def api_user_info(address):
    w3 = get_w3()
    config = load_config()
    _, registry = get_contracts(w3, config)

    if not w3.is_address(address): return jsonify({"error": "Invalid address"}), 400

    try:
        addr = w3.to_checksum_address(address)
        name = safe_call(registry.functions.userNames, addr) or ""
        registered = safe_call(registry.functions.isRegistered, addr) or False
        return jsonify({"address": addr, "name": name, "registered": registered})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ==========================================
#  API Routes - Admin Actions
# ==========================================

@app.route("/api/admin/users", methods=["POST"])
def api_admin_users():
    """Fetch all available users for the admin transfer dropdown."""
    data = request.get_json()
    if not data: return jsonify({"error": "Invalid request payload"}), 400

    private_key = ensure_0x(data.get("private_key", ""))

    w3 = get_w3()
    config = load_config()
    _, registry = get_contracts(w3, config)

    try:
        account = w3.eth.account.from_key(private_key)
        admin_addr = safe_call(registry.functions.getAdmin)
        if not admin_addr or account.address.lower() != admin_addr.lower():
            return jsonify({"error": "Access denied. Admin only."}), 400
    except Exception:
        return jsonify({"error": "Invalid private key format"}), 400

    try:
        accounts_set = set(w3.eth.accounts)
        users = []
        for addr in accounts_set:
            try:
                addr = w3.to_checksum_address(addr)
                name = safe_call(registry.functions.userNames, addr)
                if addr.lower() != admin_addr.lower():
                    display_text = f"{name} ({addr})" if name else addr
                    users.append({"address": addr, "display": display_text})
            except Exception:
                continue

        return jsonify({"users": users})
    except Exception as e:
        return jsonify({"error": f"Failed to fetch users: {str(e)}"}), 500


@app.route("/api/admin/export-csv", methods=["POST"])
def api_admin_export_csv():
    data = request.get_json()
    if not data: return jsonify({"error": "Invalid request payload"}), 400

    private_key = ensure_0x(data.get("private_key", ""))
    if not private_key: return jsonify({"error": "Missing private key"}), 400

    w3 = get_w3()
    config = load_config()
    coin, registry = get_contracts(w3, config)

    try:
        account = w3.eth.account.from_key(private_key)
        admin_addr = safe_call(registry.functions.getAdmin)
        if not admin_addr or account.address.lower() != admin_addr.lower():
            return jsonify({"error": "Access denied. Admin only."}), 400
    except Exception:
        return jsonify({"error": "Invalid private key format"}), 400

    accounts_set = set(w3.eth.accounts)
    registry_address = registry.address.lower()
    coin_address = coin.address.lower()
    latest = w3.eth.block_number

    for block_num in range(0, latest + 1):
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
    rows = []

    for addr in final_accounts:
        try:
            checksum_addr = w3.to_checksum_address(addr)
            c_bal = coin.functions.balanceOf(checksum_addr).call()
            e_bal = w3.eth.get_balance(checksum_addr)
            rows.append({
                "Account Address": checksum_addr,
                "Library Coin Balance": f"{float(w3.from_wei(c_bal, 'ether')):.4f}",
                "ETH Balance": f"{float(w3.from_wei(e_bal, 'ether')):.6f}"
            })
        except Exception:
            pass

    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
    os.makedirs(data_dir, exist_ok=True)
    csv_path = os.path.join(data_dir, "snapshot.csv")

    try:
        with open(csv_path, "w", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=["Account Address", "Library Coin Balance", "ETH Balance"])
            writer.writeheader()
            writer.writerows(rows)
        return jsonify({"success": True, "message": f"Successfully exported {len(rows)} accounts to CSV."})
    except Exception as e:
        return jsonify({"error": f"File generation failed: {str(e)}"}), 500


@app.route("/api/admin/status")
def api_admin_status():
    w3 = get_w3()
    config = load_config()
    _, registry = get_contracts(w3, config)

    admin = safe_call(registry.functions.getAdmin) or ""
    paused = safe_call(registry.functions.paused) or False

    return jsonify({"admin": admin, "paused": paused})


@app.route("/api/admin/add-book", methods=["POST"])
def api_admin_add_book():
    """Admin: add a single book. Supports MultiPart FormData with File Uploads + JSON Fallback."""
    w3 = get_w3()
    config = load_config()
    _, registry = get_contracts(w3, config)

    if request.content_type and "multipart/form-data" in request.content_type:
        private_key = ensure_0x(request.form.get("private_key", ""))
        title = request.form.get("title", "")
        author = request.form.get("author", "")
        base_price_eth = float(request.form.get("basePrice", 0))

        image_file = request.files.get("image")
        pdf_file = request.files.get("pdf")

        try:
            durations = json.loads(request.form.get("durations", "[]"))
            prices_eth = json.loads(request.form.get("prices", "[]"))
        except Exception:
            return jsonify({"error": "Invalid JSON format for durations or prices"}), 400

        if not image_file or not pdf_file:
            return jsonify({"error": "Both Image and PDF files are required"}), 400

        image_hash = generate_file_hash(image_file)
        pdf_hash = generate_file_hash(pdf_file)

        image_filename = generate_safe_filename(image_hash, image_file.filename)
        pdf_filename = generate_safe_filename(pdf_hash, pdf_file.filename)

        image_file.save(os.path.join(UPLOAD_FOLDER, image_filename))
        pdf_file.save(os.path.join(UPLOAD_FOLDER, pdf_filename))

    else:
        data = request.get_json()
        if not data: return jsonify({"error": "Invalid request payload"}), 400
        private_key = ensure_0x(data.get("private_key", ""))
        title = data.get("title", "")
        author = data.get("author", "")
        base_price_eth = 0
        image_hash = ""
        pdf_hash = ""
        durations = []
        prices_eth = []

    if not private_key or not title or not author:
        return jsonify({"error": "Missing required fields"}), 400

    base_price = w3.to_wei(base_price_eth, "ether")
    prices = [w3.to_wei(float(p), "ether") for p in prices_eth]

    try:
        account = w3.eth.account.from_key(private_key)
        admin_addr = safe_call(registry.functions.getAdmin)
        if not admin_addr or account.address.lower() != admin_addr.lower():
            return jsonify({"error": "Access denied. Admin only."}), 400
    except Exception:
        return jsonify({"error": "Invalid private key format"}), 400

    try:
        tx = registry.functions.addBook(
            title, author, base_price, image_hash, pdf_hash, durations, prices
        ).build_transaction({
            "from": account.address,
            "nonce": w3.eth.get_transaction_count(account.address),
            "gas": 600000,
            "gasPrice": w3.eth.gas_price
        })
        signed = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

        if receipt["status"] == 1:
            return jsonify({"success": True, "message": f"Book '{title}' added successfully"})
        else:
            return jsonify({"error": "Transaction reverted on blockchain"}), 400
    except Exception as e:
        return jsonify({"error": parse_tx_error(e)}), 400


@app.route("/api/admin/update-book", methods=["POST"])
def api_admin_update_book():
    """Admin: Update an existing book's details."""
    if not request.content_type or "multipart/form-data" not in request.content_type:
        return jsonify({"error": "Must use multipart/form-data"}), 400

    w3 = get_w3()
    config = load_config()
    _, registry = get_contracts(w3, config)

    private_key = ensure_0x(request.form.get("private_key", ""))
    book_id = int(request.form.get("bookId", 0))
    title = request.form.get("title", "")
    author = request.form.get("author", "")
    base_price_eth = float(request.form.get("basePrice", 0))

    image_hash = request.form.get("existingImageHash", "")
    pdf_hash = request.form.get("existingPdfHash", "")

    image_file = request.files.get("image")
    pdf_file = request.files.get("pdf")

    if image_file and image_file.filename:
        image_hash = generate_file_hash(image_file)
        image_file.save(os.path.join(UPLOAD_FOLDER, generate_safe_filename(image_hash, image_file.filename)))

    if pdf_file and pdf_file.filename:
        pdf_hash = generate_file_hash(pdf_file)
        pdf_file.save(os.path.join(UPLOAD_FOLDER, generate_safe_filename(pdf_hash, pdf_file.filename)))

    try:
        durations = json.loads(request.form.get("durations", "[]"))
        prices_eth = json.loads(request.form.get("prices", "[]"))
    except Exception:
        return jsonify({"error": "Invalid JSON format for durations or prices"}), 400

    if not private_key or not book_id:
        return jsonify({"error": "Missing required fields"}), 400

    base_price = w3.to_wei(base_price_eth, "ether")
    prices = [w3.to_wei(float(p), "ether") for p in prices_eth]

    try:
        account = w3.eth.account.from_key(private_key)
        admin_addr = safe_call(registry.functions.getAdmin)
        if not admin_addr or account.address.lower() != admin_addr.lower():
            return jsonify({"error": "Access denied. Admin only."}), 400
    except Exception:
        return jsonify({"error": "Invalid private key format"}), 400

    try:
        tx = registry.functions.updateBook(
            book_id, title, author, base_price, image_hash, pdf_hash, durations, prices
        ).build_transaction({
            "from": account.address,
            "nonce": w3.eth.get_transaction_count(account.address),
            "gas": 600000,
            "gasPrice": w3.eth.gas_price
        })
        signed = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

        if receipt["status"] == 1:
            return jsonify({"success": True, "message": f"Book ID {book_id} updated successfully"})
        else:
            return jsonify({"error": "Transaction reverted on blockchain"}), 400
    except Exception as e:
        return jsonify({"error": parse_tx_error(e)}), 400


@app.route("/api/admin/toggle-book", methods=["POST"])
def api_admin_toggle_book():
    """Admin: Toggle book existence status (Soft Delete)."""
    data = request.get_json()
    if not data: return jsonify({"error": "Invalid request payload"}), 400

    w3 = get_w3()
    config = load_config()
    _, registry = get_contracts(w3, config)

    private_key = ensure_0x(data.get("private_key", ""))
    book_id = data.get("bookId", 0)

    if not private_key or not book_id: return jsonify({"error": "Missing fields"}), 400

    try:
        account = w3.eth.account.from_key(private_key)
        admin_addr = safe_call(registry.functions.getAdmin)
        if not admin_addr or account.address.lower() != admin_addr.lower():
            return jsonify({"error": "Access denied. Admin only."}), 400
    except Exception:
        return jsonify({"error": "Invalid private key format"}), 400

    try:
        tx = registry.functions.toggleBookExistence(int(book_id)).build_transaction({
            "from": account.address,
            "nonce": w3.eth.get_transaction_count(account.address),
            "gas": 150000,
            "gasPrice": w3.eth.gas_price
        })
        signed = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

        if receipt["status"] == 1:
            return jsonify({"success": True, "message": f"Book ID {book_id} status toggled."})
        else:
            return jsonify({"error": "Transaction reverted"}), 400
    except Exception as e:
        return jsonify({"error": parse_tx_error(e)}), 400


@app.route("/api/admin/batch-add", methods=["POST"])
def api_admin_batch_add():
    """Admin: batch add books fully supporting Multi-Part FormData and dynamically mapped arrays."""
    w3 = get_w3()
    config = load_config()
    _, registry = get_contracts(w3, config)

    if not request.content_type or "multipart/form-data" not in request.content_type:
        return jsonify({"error": "Must use multipart/form-data for batch-add"}), 400

    private_key = ensure_0x(request.form.get("private_key", ""))
    try:
        count = int(request.form.get("count", 0))
    except ValueError:
        return jsonify({"error": "Invalid batch count"}), 400

    if not private_key or count <= 0:
        return jsonify({"error": "Missing private key or empty batch"}), 400

    try:
        account = w3.eth.account.from_key(private_key)
        admin_addr = safe_call(registry.functions.getAdmin)
        if not admin_addr or account.address.lower() != admin_addr.lower():
            return jsonify({"error": "Access denied. Admin only."}), 400
    except Exception:
        return jsonify({"error": "Invalid private key format"}), 400

    titles = []
    authors = []
    base_prices = []
    image_hashes = []
    pdf_hashes = []
    durations = []
    prices = []

    for i in range(count):
        titles.append(request.form.get(f"title_{i}", ""))
        authors.append(request.form.get(f"author_{i}", ""))
        base_prices.append(w3.to_wei(float(request.form.get(f"basePrice_{i}", 0)), "ether"))

        img_file = request.files.get(f"image_{i}")
        pdf_file = request.files.get(f"pdf_{i}")

        ihash = generate_file_hash(img_file)
        phash = generate_file_hash(pdf_file)
        image_hashes.append(ihash)
        pdf_hashes.append(phash)

        if img_file: img_file.save(os.path.join(UPLOAD_FOLDER, generate_safe_filename(ihash, img_file.filename)))
        if pdf_file: pdf_file.save(os.path.join(UPLOAD_FOLDER, generate_safe_filename(phash, pdf_file.filename)))

        try:
            durs = json.loads(request.form.get(f"durations_{i}", "[]"))
            prs = json.loads(request.form.get(f"prices_{i}", "[]"))
            durations.append(durs)
            prices.append([w3.to_wei(float(p), "ether") for p in prs])
        except Exception:
            return jsonify({"error": f"Invalid JSON format for row {i + 1}"}), 400

    try:
        tx = registry.functions.batchAddBooks(
            titles, authors, base_prices, image_hashes, pdf_hashes, durations, prices
        ).build_transaction({
            "from": account.address,
            "nonce": w3.eth.get_transaction_count(account.address),
            "gas": 3000000,
            "gasPrice": w3.eth.gas_price
        })
        signed = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

        if receipt["status"] == 1:
            return jsonify({"success": True, "message": f"{len(titles)} books added"})
        else:
            return jsonify({"error": "Batch transaction reverted"}), 400
    except Exception as e:
        return jsonify({"error": parse_tx_error(e)}), 400


@app.route("/api/admin/mint", methods=["POST"])
def api_admin_mint():
    data = request.get_json()
    if not data: return jsonify({"error": "Invalid request payload"}), 400

    private_key = ensure_0x(data.get("private_key", ""))
    to_addr = data.get("to", "")
    amount = data.get("amount", 0)

    if not private_key or not to_addr or not amount: return jsonify({"error": "Missing fields"}), 400

    w3 = get_w3()
    config = load_config()
    coin, registry = get_contracts(w3, config)

    if not w3.is_address(to_addr): return jsonify({"error": "Invalid recipient address"}), 400

    try:
        account = w3.eth.account.from_key(private_key)
        admin_addr = safe_call(registry.functions.getAdmin)
        if not admin_addr or account.address.lower() != admin_addr.lower():
            return jsonify({"error": "Access denied. Admin only."}), 400
    except Exception:
        return jsonify({"error": "Invalid private key format"}), 400

    try:
        amount_wei = w3.to_wei(amount, "ether")
        tx = coin.functions.mint(w3.to_checksum_address(to_addr), amount_wei).build_transaction({
            "from": account.address,
            "nonce": w3.eth.get_transaction_count(account.address),
            "gas": 200000,
            "gasPrice": w3.eth.gas_price
        })
        signed = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

        if receipt["status"] == 1:
            return jsonify({"success": True, "message": f"Minted {amount} LBC"})
        else:
            return jsonify({"error": "Transaction reverted"}), 400
    except Exception as e:
        return jsonify({"error": parse_tx_error(e)}), 400


@app.route("/api/admin/pause", methods=["POST"])
def api_admin_pause():
    data = request.get_json()
    if not data: return jsonify({"error": "Invalid request payload"}), 400

    private_key = ensure_0x(data.get("private_key", ""))
    if not private_key: return jsonify({"error": "Missing private_key"}), 400

    w3 = get_w3()
    config = load_config()
    _, registry = get_contracts(w3, config)

    try:
        account = w3.eth.account.from_key(private_key)
        admin_addr = safe_call(registry.functions.getAdmin)
        if not admin_addr or account.address.lower() != admin_addr.lower():
            return jsonify({"error": "Access denied. Admin only."}), 400
    except Exception:
        return jsonify({"error": "Invalid private key format"}), 400

    try:
        tx = registry.functions.pause().build_transaction({
            "from": account.address,
            "nonce": w3.eth.get_transaction_count(account.address),
            "gas": 100000,
            "gasPrice": w3.eth.gas_price
        })
        signed = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

        if receipt["status"] == 1:
            return jsonify({"success": True, "message": "System paused"})
        else:
            return jsonify({"error": "Transaction reverted"}), 400
    except Exception as e:
        return jsonify({"error": parse_tx_error(e)}), 400


@app.route("/api/admin/resume", methods=["POST"])
def api_admin_resume():
    data = request.get_json()
    if not data: return jsonify({"error": "Invalid request payload"}), 400

    private_key = ensure_0x(data.get("private_key", ""))
    if not private_key: return jsonify({"error": "Missing private_key"}), 400

    w3 = get_w3()
    config = load_config()
    _, registry = get_contracts(w3, config)

    try:
        account = w3.eth.account.from_key(private_key)
        admin_addr = safe_call(registry.functions.getAdmin)
        if not admin_addr or account.address.lower() != admin_addr.lower():
            return jsonify({"error": "Access denied. Admin only."}), 400
    except Exception:
        return jsonify({"error": "Invalid private key format"}), 400

    try:
        tx = registry.functions.resume().build_transaction({
            "from": account.address,
            "nonce": w3.eth.get_transaction_count(account.address),
            "gas": 100000,
            "gasPrice": w3.eth.gas_price
        })
        signed = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

        if receipt["status"] == 1:
            return jsonify({"success": True, "message": "System resumed"})
        else:
            return jsonify({"error": "Transaction reverted"}), 400
    except Exception as e:
        return jsonify({"error": parse_tx_error(e)}), 400


@app.route("/api/admin/transfer-ownership", methods=["POST"])
def api_admin_transfer():
    data = request.get_json()
    if not data: return jsonify({"error": "Invalid request payload"}), 400

    private_key = ensure_0x(data.get("private_key", ""))
    new_admin = data.get("new_admin", "")

    if not private_key or not new_admin: return jsonify({"error": "Missing fields"}), 400

    w3 = get_w3()
    config = load_config()
    coin, registry = get_contracts(w3, config)

    if not w3.is_address(new_admin): return jsonify({"error": "Invalid new admin address"}), 400

    try:
        account = w3.eth.account.from_key(private_key)
        admin_addr = safe_call(registry.functions.getAdmin)
        if not admin_addr or account.address.lower() != admin_addr.lower():
            return jsonify({"error": "Access denied. Admin only."}), 400
    except Exception:
        return jsonify({"error": "Invalid private key format"}), 400

    try:
        new_admin_checksum = w3.to_checksum_address(new_admin)
        nonce = w3.eth.get_transaction_count(account.address)

        tx_coin = coin.functions.transferOwnership(new_admin_checksum).build_transaction({
            "from": account.address,
            "nonce": nonce,
            "gas": 100000,
            "gasPrice": w3.eth.gas_price
        })
        signed_coin = w3.eth.account.sign_transaction(tx_coin, private_key)
        tx_hash_coin = w3.eth.send_raw_transaction(signed_coin.raw_transaction)
        w3.eth.wait_for_transaction_receipt(tx_hash_coin, timeout=60)

        tx_reg = registry.functions.transferOwnership(new_admin_checksum).build_transaction({
            "from": account.address,
            "nonce": w3.eth.get_transaction_count(account.address),
            "gas": 100000,
            "gasPrice": w3.eth.gas_price
        })
        signed_reg = w3.eth.account.sign_transaction(tx_reg, private_key)
        tx_hash_reg = w3.eth.send_raw_transaction(signed_reg.raw_transaction)
        receipt_reg = w3.eth.wait_for_transaction_receipt(tx_hash_reg, timeout=60)

        if receipt_reg["status"] == 1:
            return jsonify({"success": True, "message": f"Ownership transferred successfully."})
        else:
            return jsonify({"error": "Transaction reverted"}), 400
    except Exception as e:
        return jsonify({"error": parse_tx_error(e)}), 400


if __name__ == "__main__":
    print("Starting Campus Library DApp Web Server...")
    print("Ensure Ganache is running and auto_setup.py has been executed.")
    app.run(debug=True, port=5000)