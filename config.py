import os
import json

# Network configuration
RPC_URL = "http://127.0.0.1:8545"

# Default admin account (replace with your Ganache account)
DEFAULT_ADMIN = "0xYourAdminAddressHere"

# Admin menu password hash (pre-computed for security)
ADMIN_PASSWORD_HASH = "e99a18c428cb38d5f260853678922e03abd4c98b8a2802f3f1c76f127532c9b8"

# Deployment paths
DEPLOYMENT_FILE = "deployment.json"

def load_deployment():
    if os.path.exists(DEPLOYMENT_FILE):
        with open(DEPLOYMENT_FILE, "r") as f:
            return json.load(f)
    return None

def save_deployment(data):
    with open(DEPLOYMENT_FILE, "w") as f:
        json.dump(data, f, indent=2)