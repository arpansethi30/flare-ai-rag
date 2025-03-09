# Enhanced fallback responses dictionary with code examples and detailed information
FALLBACK_RESPONSES = {
    "what is flare": """
# 🌟 Flare Network Overview

Flare is a blockchain for data, designed to provide decentralized access to high-integrity data from various sources. It's an EVM-compatible smart contract platform optimized for decentralized data acquisition, supporting:

## Key Components
- **Price and time-series data** via FTSO
- **Blockchain event and state data** via State Connector
- **Web2 API data integration**

## Technical Architecture
```
┌─────────────────────────────────────────┐
│               Flare Network              │
├─────────────┬───────────────┬───────────┤
│ FTSO System │State Connector│  FAssets  │
│ (Price Data)│ (Cross-chain) │(Wrapping) │
├─────────────┴───────────────┴───────────┤
│        EVM-Compatible Smart Contracts    │
├─────────────────────────────────────────┤
│       Byzantine Fault Tolerant Consensus │
└─────────────────────────────────────────┘
```

For more information, visit https://dev.flare.network/intro/
""",
    
    "what is ftso": """
# 📊 FTSO (Flare Time Series Oracle)

FTSO is Flare's native price oracle system that provides reliable, decentralized price data to the network.

## Key Features
- **Decentralized price feeds** from multiple independent data providers
- **Economic incentives** for accurate data provision
- **Manipulation resistance** through a robust voting system
- **Wide asset support** for crypto, forex, commodities, and more

## How It Works
```mermaid
graph TD
    A[Data Providers] -->|Submit Price Estimates| B[FTSO System]
    B -->|Weighted Median Calculation| C[Final Price]
    C -->|Used By| D[Smart Contracts]
    B -->|Rewards| A
```

## Sample Code to Query FTSO
```javascript
// Example: Query FTSO price on Flare
const ftsoRegistry = await ethers.getContractAt(
  "IFtsoRegistry", 
  "0x6D222fb4544ba230d4b90BA1BfC0A01A94E254c9"
);

// Get FLR/USD price
const [price, timestamp, decimals] = await ftsoRegistry.getPriceForSymbol("FLR");
const actualPrice = price / (10 ** decimals);
console.log(`Current FLR price: $${actualPrice}`);
```

For more information, visit https://dev.flare.network/tech/ftso/
""",
    
    "tell me about flare": """
# ☀️ Flare Network: The Blockchain for Data

Flare is the blockchain for data, offering secure, decentralized access to high-integrity data from various sources.

## Core Capabilities
- **EVM compatibility** for familiar development experience
- **Cross-chain data** through the State Connector
- **Price feeds** via the Flare Time Series Oracle (FTSO)
- **Time-series data** for various assets
- **Web2 API integration**

## Network Architecture
```
┌───────────────────────────────────────────────┐
│                 Application Layer              │
│  ┌─────────────┐  ┌─────────────┐  ┌────────┐ │
│  │    DApps    │  │  Services   │  │  APIs  │ │
│  └─────────────┘  └─────────────┘  └────────┘ │
├───────────────────────────────────────────────┤
│                 Protocol Layer                 │
│  ┌─────────────┐  ┌─────────────┐  ┌────────┐ │
│  │    FTSO     │  │    State    │  │ FAssets│ │
│  │             │  │  Connector  │  │        │ │
│  └─────────────┘  └─────────────┘  └────────┘ │
├───────────────────────────────────────────────┤
│                 Consensus Layer                │
└───────────────────────────────────────────────┘
```

## Getting Started
```bash
# Install Flare development tools
npm install -g @flarelabs/flare-cli

# Create a new Flare project
flare-cli init my-flare-project
cd my-flare-project

# Deploy to Flare testnet
flare-cli deploy --network coston
```

For more information, visit https://dev.flare.network/intro/
""",
    
    "python": """
# 🐍 Python + Flare Setup Guide for Developers

Ready to build on Flare with Python? Here's your comprehensive setup guide:

## 1️⃣ Environment Setup
```bash
# Create a virtual environment in your project
python -m venv flare-env
source flare-env/bin/activate  # On Windows: flare-env\\Scripts\\activate

# Install essential packages
pip install web3==6.15.1 requests pandas python-dotenv
```

## 2️⃣ Configure Connection
Create a `flare_config.py` file:

```python
from web3 import Web3
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Flare Mainnet connection
FLARE_RPC = "https://flare-api.flare.network/ext/bc/C/rpc"
w3 = Web3(Web3.HTTPProvider(FLARE_RPC))

# FTSO Registry contract - where all the price data lives
FTSO_REGISTRY = "0x6D222fb4544ba230d4b90BA1BfC0A01A94E254c9"  # Flare Mainnet

# Test connection
def check_connection():
    connected = w3.is_connected()
    if connected:
        print(f"✅ Connected to Flare! Current block: {w3.eth.block_number}")
    else:
        print("❌ Connection failed!")
    return connected
```

## 3️⃣ Fetch FTSO Price Data
Create `flare_ftso.py`:

```python
from flare_config import w3, FTSO_REGISTRY
import json

# ABI for the required functions only (minimal)
FTSO_REGISTRY_ABI = [
    {"inputs":[{"internalType":"string","name":"_symbol","type":"string"}],"name":"getPriceForSymbol","outputs":[{"internalType":"uint256","name":"_price","type":"uint256"},{"internalType":"uint256","name":"_timestamp","type":"uint256"},{"internalType":"uint256","name":"_decimals","type":"uint256"}],"stateMutability":"view","type":"function"}
]

registry = w3.eth.contract(address=FTSO_REGISTRY, abi=FTSO_REGISTRY_ABI)

def get_flr_price():
    try:
        # Get FLR/USD price
        price, timestamp, decimals = registry.functions.getPriceForSymbol("FLR").call()
        
        # Convert to human-readable format
        actual_price = price / (10 ** decimals)
        
        return {
            "price": actual_price,
            "timestamp": timestamp,
            "decimals": decimals
        }
    except Exception as e:
        print(f"Error fetching FTSO data: {e}")
        return None
```

## 4️⃣ Test Your Integration

```python
if __name__ == "__main__":
    from flare_config import check_connection
    
    if check_connection():
        price_data = get_flr_price()
        if price_data:
            print(f"🚀 Current FLR/USD: ${price_data['price']:.4f}")
        else:
            print("❌ Failed to get price data")
```

For more advanced examples and detailed documentation, visit https://dev.flare.network/apis/
""",

    "smart contracts": """
# 📝 Smart Contracts on Flare Network

Flare is fully EVM-compatible, allowing you to deploy and interact with Solidity smart contracts.

## Development Setup
```bash
# Install development tools
npm install -g truffle @truffle/hdwallet-provider

# Create a new Truffle project
mkdir flare-contracts && cd flare-contracts
truffle init
```

## Sample Truffle Config
```javascript
// truffle-config.js
const HDWalletProvider = require('@truffle/hdwallet-provider');
require('dotenv').config();

module.exports = {
  networks: {
    flare: {
      provider: () => new HDWalletProvider(
        process.env.PRIVATE_KEY,
        'https://flare-api.flare.network/ext/bc/C/rpc'
      ),
      network_id: 14,
      gas: 8000000,
      gasPrice: 25000000000,
      timeoutBlocks: 50,
      skipDryRun: true
    },
    coston: {
      provider: () => new HDWalletProvider(
        process.env.PRIVATE_KEY,
        'https://coston-api.flare.network/ext/bc/C/rpc'
      ),
      network_id: 16,
      gas: 8000000,
      gasPrice: 25000000000,
      timeoutBlocks: 50,
      skipDryRun: true
    }
  },
  compilers: {
    solc: {
      version: "0.8.19",
    }
  }
};
```

## Sample FTSO Data Consumer Contract
```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

interface IFtsoRegistry {
    function getPriceForSymbol(string memory _symbol) external view returns (uint256 _price, uint256 _timestamp, uint256 _decimals);
}

contract FtsoDataConsumer {
    IFtsoRegistry public ftsoRegistry;
    
    constructor(address _ftsoRegistryAddress) {
        ftsoRegistry = IFtsoRegistry(_ftsoRegistryAddress);
    }
    
    function getFlrPrice() external view returns (uint256 price, uint256 timestamp, uint256 decimals) {
        return ftsoRegistry.getPriceForSymbol("FLR");
    }
    
    function getFormattedPrice(string memory symbol) external view returns (uint256) {
        (uint256 price, , uint256 decimals) = ftsoRegistry.getPriceForSymbol(symbol);
        return price / (10 ** decimals);
    }
}
```

For more information, visit https://dev.flare.network/dev/networks/
""",

    "state connector": """
# 🔗 State Connector: Cross-Chain Data Oracle

The State Connector is Flare's protocol for securely bringing data from other blockchains onto Flare.

## Key Features
- **Cross-chain data verification** without trusted intermediaries
- **Attestation-based model** for secure data validation
- **Support for multiple blockchains** including Bitcoin, Ethereum, XRP Ledger, and more

## Architecture
```
┌─────────────────────────────────────────────────┐
│                 Flare Network                    │
│                                                  │
│  ┌─────────────────┐      ┌──────────────────┐  │
│  │  State Connector │◄────┤ Attestation Proof│  │
│  │     Protocol     │      │    Providers    │  │
│  └────────┬─────────┘      └──────────────────┘  │
│           │                                      │
└───────────┼──────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────┐
│               External Blockchains               │
│  ┌──────────┐  ┌──────────┐  ┌───────────────┐  │
│  │  Bitcoin │  │ Ethereum │  │  XRP Ledger   │  │
│  └──────────┘  └──────────┘  └───────────────┘  │
└─────────────────────────────────────────────────┘
```

## Sample Code: Verify Bitcoin Transaction
```javascript
// Example: Verify a Bitcoin transaction on Flare
const stateConnector = await ethers.getContractAt(
  "IStateConnector", 
  "0x0c13aDA1C7143Cf0a0795FFaB93eEBb6FAD6e0BB"
);

// Request attestation for a Bitcoin transaction
const attestationType = 1; // Bitcoin payment
const requestBody = ethers.utils.defaultAbiCoder.encode(
  ["bytes32", "uint256", "address"],
  [
    "0x123...abc", // Bitcoin transaction hash
    6,             // Required confirmations
    "0xYourAddress" // Recipient address
  ]
);

// Submit attestation request
await stateConnector.requestAttestations(
  attestationType,
  requestBody
);

// Later: verify the attestation
const proof = await stateConnector.getAttestations(
  attestationType,
  requestBody
);
```

For more information, visit https://dev.flare.network/tech/state-connector/
"""
} 