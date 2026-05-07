# 📚 Campus Library DApp ⛓️

A full-stack, decentralized web application (DApp) that revolutionizes campus library management using Blockchain technology. Users can browse the catalog, borrow books using a custom cryptocurrency, and read them through a secure, DRM-protected PDF viewer with live annotation tools.

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Solidity](https://img.shields.io/badge/Solidity-%23363636.svg?style=for-the-badge&logo=solidity&logoColor=white)
![Flask](https://img.shields.io/badge/flask-%23000.svg?style=for-the-badge&logo=flask&logoColor=white)
![Web3.py](https://img.shields.io/badge/Web3.py-F16822?style=for-the-badge&logo=ethereum&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)

---

## 📸 UI Sneak Peek

Here is a quick look at the application. 

### User Interface (Home & Catalog)
![User Home Page](./assets/user-home-page.png)
![Full Catalog](./assets/user-full-catalog.jpeg)

### Admin Panel (Dashboard & Book Management)
![Admin Dashboard](./assets/admin-dashboard.jpeg)
![Admin Batch Add](./assets/admin-batch-add.png)

> 💡 **Note:** Want to see more? Check out the [`assets/`](./assets/) folder for a complete gallery of screenshots, including Security Tests, Ownership Transfer, Balance Checker, and more!

---

## ✨ Key Features

* **Dual Smart Contracts:**
  Built on two Solidity contracts:
  * `LibraryRegistry` → manages books and borrowing
  * `LibraryCoin` → ERC20-like token for payments

* **Dynamic Pricing:**
  Book borrowing cost depends on:
  * Selected duration (Day / Week / Month)
  * Base book price

* **Secure PDF Reader:**
  * Accessible only for users with active on-chain loans
  * DRM protection (no download / no right-click)
  * Canvas overlay for live annotations

* **Dual Interfaces:**
  * 🌐 Web GUI (Flask + JavaScript)
  * 💻 Terminal CLI (Python)

* **Advanced Admin Panel:**
  * Add books (with image + PDF)
  * Dynamic pricing per duration
  * Edit / delete / restore books
  * Mint tokens
  * Pause system
  * Transfer ownership
  * Export CSV snapshots

* **Security & Testing:**
  * Automated deployment scripts
  * Role-Based Access Control (RBAC)
  * Security test suite

---

## 🏗️ System Architecture

* **Blockchain Layer:** Ganache (Local Ethereum Testnet) + Solidity
* **Backend:** Python + Flask + Web3.py
* **Frontend:** HTML5 + CSS3 + Vanilla JavaScript
* **Storage:** Local secure storage with hashed filenames

---

## 📂 Project Structure

```text
campus_library_dapp/
├── app/
│   ├── terminal.py
│   └── web_server.py
├── assets/                  <-- (Check for all project screenshots!)
├── contracts/
│   ├── LibraryCoin.sol
│   └── LibraryRegistry.sol
├── data/
│   ├── balances_snapshot.csv
│   └── snapshot.csv
├── frontend/
│   ├── css/
│   ├── js/
│   ├── admin.html
│   ├── dashboard.html
│   └── index.html
├── scripts/
│   ├── auto_setup.py
│   ├── background_jobs.py
│   └── security_tests.py
├── uploads/
│   ├── images/
│   └── pdfs/
├── README.md
├── config.py
├── directory-tree.txt
└── requirements.txt

```

---

## 🚀 Getting Started

### Prerequisites

* Python 3.8+
* Ganache (running on http://127.0.0.1:7545)
* Git

---

### Installation

```bash
git clone [https://github.com/YoussefAtef15/campus-library-dapp.git]
cd campus_library_dapp

python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt
```

---

### Deploy Smart Contracts

```bash
python scripts/auto_setup.py
```

---

## 🖥️ Usage

### Web Interface

```bash
python app/web_server.py
```

Open in browser:
http://127.0.0.1:5000

* Use a private key from Ganache
* First account acts as Admin

---

### Terminal CLI

```bash
python app/terminal.py
```

---

### Run Security Tests

```bash
python scripts/security_tests.py
```

---

## 🛡️ Security Mechanisms

* **File Name Hashing:**
  Prevents path length issues and secures file access

* **DRM PDF Viewer:**

  * Prevents downloading and right-click actions
  * Verifies active loan before granting access

* **RBAC (Role-Based Access Control):**

  * Admin-only functions are protected
  * Unauthorized access results in transaction failure


---

## 👨‍💻 Authors

**Youssef Atef** |
**Omar Yasser** 
