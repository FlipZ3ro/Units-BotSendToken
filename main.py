import os
from web3 import Web3
from dotenv import load_dotenv
import json
import random
from colorama import Fore, Style  # Import untuk warna teks

# Load environment variables from .env file
load_dotenv()

# Initialize Web3 and other configurations
rpc_url = os.getenv("RPC_URL")  # Pastikan ini sesuai dengan alamat server RPC Anda
w3 = Web3(Web3.HTTPProvider(rpc_url))

def get_balance(w3, address):
    # Get balance in Ether
    balance_wei = w3.eth.get_balance(address)
    balance_eth = w3.from_wei(balance_wei, 'ether')
    return balance_eth

def get_token_balance(w3, token_address, account_address):
    # Load ABI from token_abi.json file
    with open('token_abi.json', 'r') as f:
        token_abi = json.load(f)

    # Create contract instance
    contract = w3.eth.contract(address=token_address, abi=token_abi)

    # Get token balance using contract function
    token_balance = contract.functions.balanceOf(account_address).call()
    token_balance_eth = token_balance / 10**18  # Convert to token units (assuming 18 decimals)
    return token_balance_eth

def send_token(w3, private_key, token_address, recipients):
    # Load ABI from token_abi.json file
    with open('token_abi.json', 'r') as f:
        token_abi = json.load(f)

    # Create contract instance
    contract = w3.eth.contract(address=token_address, abi=token_abi)

    # Get the sender's address from private key
    sender_address = w3.eth.account.from_key(private_key).address

    # Get sender's Ethereum balance before transactions
    initial_balance_eth = get_balance(w3, sender_address)
    print(f"Sender ETH balance before transactions: {initial_balance_eth} ETH")

    # Get sender's token balance before transactions
    initial_token_balance_eth = get_token_balance(w3, token_address, sender_address)
    print(f"Sender token balance before transactions: {initial_token_balance_eth} tokens")


    # Define a gas price (e.g., 50 Gwei)
    gas_price = w3.to_wei('0.00111177', 'gwei')

    # Set gas limit for token transfer
    gas_limit = 60000  # Adjust as necessary based on token contract requirements

    # Get the sender's nonce
    nonce = w3.eth.get_transaction_count(sender_address)

    # Initialize total gas needed
    total_gas = 0

    # Collect transaction data for each recipient with a sequence number
    txs = []
    tx_sequence_number = 1
    for recipient_address, amount in recipients.items():
        recipient_address_checksum = Web3.to_checksum_address(recipient_address)
        amount_in_wei = int(amount * 10**18)  # Convert amount to wei (assuming 18 decimals)
        
        # Create transaction data for token transfer
        tx_data = contract.functions.transfer(recipient_address_checksum, amount_in_wei).build_transaction({
            'gas': gas_limit,
            'gasPrice': gas_price,
            'nonce': nonce,
            'chainId': w3.eth.chain_id,
        })

        txs.append((tx_sequence_number, tx_data))
        total_gas += gas_limit  # Add gas limit to total gas
        nonce += 1
        tx_sequence_number += 1

    # Verify if the sender has enough balance for the total transaction cost
    sender_balance = w3.eth.get_balance(sender_address)
    total_cost = total_gas * gas_price
    if sender_balance < total_cost:
        raise ValueError("Insufficient balance for gas fees.")

    # Sign and send transactions
    signed_txs = []
    for tx_sequence, tx_data in txs:
        signed_tx = w3.eth.account.sign_transaction(tx_data, private_key)
        signed_txs.append((tx_sequence, signed_tx))

    for tx_sequence, signed_tx in signed_txs:
        try:
            tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            print(f"{Fore.GREEN}Transaction {tx_sequence} successfully sent. Transaction hash: {tx_hash.hex()}{Style.RESET_ALL}")
            nonce = w3.eth.get_transaction_count(sender_address)  # Update nonce after each successful transaction
        except ValueError as e:
            error_message = str(e)
            print(f"{Fore.RED}Error sending transaction {tx_sequence}: {error_message}{Style.RESET_ALL}")

# Contoh penggunaan fungsi send_token
private_key = os.getenv("PRIVATE_KEY")  # Ganti dengan cara yang sesuai untuk mendapatkan private key dari .env
token_address = os.getenv("TOKEN_ADDRESS")  # Ganti dengan alamat kontrak token ERC-20
num_transactions = int(input("Enter the number of transactions you want to send: "))

# Generate random recipient addresses dan jumlah token yang akan dikirim ke masing-masing
recipients = {}
for i in range(num_transactions):
    new_account = w3.eth.account.create()
    recipient_address = new_account.address
    amount = round(random.uniform(1, 100), 2)  # Jumlah acak token yang akan dikirim (misalnya antara 1 dan 100)
    recipients[recipient_address] = amount

send_token(w3, private_key, token_address, recipients)
