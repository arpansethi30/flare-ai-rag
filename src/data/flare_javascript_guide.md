# JavaScript Integration with Flare Network

This guide provides a comprehensive overview of how to integrate JavaScript applications with the Flare Network.

## Table of Contents

1. [Environment Setup](#environment-setup)
2. [Connecting to Flare](#connecting-to-flare)
3. [Interacting with FTSO](#interacting-with-ftso)
4. [Working with Smart Contracts](#working-with-smart-contracts)
5. [Example Applications](#example-applications)
6. [Troubleshooting](#troubleshooting)

## Environment Setup

To get started with Flare development using JavaScript, you'll need to set up your environment:

```bash
# Create a new project directory
mkdir flare-js-app
cd flare-js-app

# Initialize a new Node.js project
npm init -y

# Install required dependencies
npm install ethers@5.7.2 dotenv axios
```

Create a `.env` file to store your configuration:

```
FLARE_RPC_URL=https://flare-api.flare.network/ext/bc/C/rpc
PRIVATE_KEY=your_private_key_here
```

## Connecting to Flare

Create a `config.js` file to handle your connection to Flare:

```javascript
// config.js
require('dotenv').config();
const { ethers } = require('ethers');

// Create provider for Flare Network
const provider = new ethers.providers.JsonRpcProvider(process.env.FLARE_RPC_URL);

// Create a wallet if you need to sign transactions
const wallet = process.env.PRIVATE_KEY 
  ? new ethers.Wallet(process.env.PRIVATE_KEY, provider) 
  : null;

// Test connection
async function testConnection() {
  try {
    const blockNumber = await provider.getBlockNumber();
    console.log(`✅ Connected to Flare Network! Current block: ${blockNumber}`);
    return true;
  } catch (error) {
    console.error(`❌ Connection failed: ${error.message}`);
    return false;
  }
}

module.exports = {
  provider,
  wallet,
  testConnection
};
```

## Interacting with FTSO

The Flare Time Series Oracle (FTSO) provides decentralized price feeds. Here's how to interact with it:

```javascript
// ftso.js
const { provider } = require('./config');
const { ethers } = require('ethers');

// FTSO Registry contract address on Flare Mainnet
const FTSO_REGISTRY_ADDRESS = '0x6D222fb4544ba230d4b90BA1BfC0A01A94E254c9';

// Minimal ABI for the FTSO Registry
const FTSO_REGISTRY_ABI = [
  "function getPriceForSymbol(string _symbol) view returns (uint256 _price, uint256 _timestamp, uint256 _decimals)"
];

// Create contract instance
const ftsoRegistry = new ethers.Contract(
  FTSO_REGISTRY_ADDRESS,
  FTSO_REGISTRY_ABI,
  provider
);

// Get price for a symbol
async function getPrice(symbol) {
  try {
    const [price, timestamp, decimals] = await ftsoRegistry.getPriceForSymbol(symbol);
    
    // Convert to human-readable format
    const formattedPrice = ethers.utils.formatUnits(price, decimals);
    const date = new Date(timestamp.toNumber() * 1000);
    
    return {
      symbol,
      price: formattedPrice,
      timestamp: date.toISOString(),
      rawData: { price, timestamp, decimals }
    };
  } catch (error) {
    console.error(`Error fetching price for ${symbol}: ${error.message}`);
    return null;
  }
}

module.exports = {
  getPrice
};
```

## Working with Smart Contracts

Here's how to deploy and interact with a simple smart contract on Flare:

```javascript
// deploy.js
const { wallet } = require('./config');
const { ethers } = require('ethers');

// Simple storage contract
const CONTRACT_ABI = [
  "function store(uint256 value) public",
  "function retrieve() public view returns (uint256)"
];

const CONTRACT_BYTECODE = "0x608060405234801561001057600080fd5b50610150806100206000396000f3fe608060405234801561001057600080fd5b50600436106100365760003560e01c80632e64cec11461003b5780636057361d14610059575b600080fd5b610043610075565b60405161005091906100a1565b60405180910390f35b610073600480360381019061006e91906100ed565b61007e565b005b60008054905090565b8060008190555050565b6000819050919050565b61009b81610088565b82525050565b60006020820190506100b66000830184610092565b92915050565b600080fd5b6100ca81610088565b81146100d557600080fd5b50565b6000813590506100e7816100c1565b92915050565b600060208284031215610103576101026100bc565b5b6000610111848285016100d8565b9150509291505056fea2646970667358221220322c78243e61b783558509c9cc22cb8493dde6925aa5e89a08cdf6e22f279ef164736f6c63430008120033";

async function deployContract() {
  try {
    // Create contract factory
    const factory = new ethers.ContractFactory(
      CONTRACT_ABI,
      CONTRACT_BYTECODE,
      wallet
    );
    
    console.log('Deploying contract...');
    const contract = await factory.deploy();
    
    // Wait for deployment to be confirmed
    await contract.deployed();
    console.log(`Contract deployed at: ${contract.address}`);
    
    return contract;
  } catch (error) {
    console.error(`Deployment failed: ${error.message}`);
    return null;
  }
}

async function interactWithContract(contractAddress) {
  try {
    // Create contract instance
    const contract = new ethers.Contract(
      contractAddress,
      CONTRACT_ABI,
      wallet
    );
    
    // Store a value
    console.log('Storing value 42...');
    const tx = await contract.store(42);
    await tx.wait();
    
    // Retrieve the value
    const value = await contract.retrieve();
    console.log(`Retrieved value: ${value.toString()}`);
    
    return value.toString();
  } catch (error) {
    console.error(`Interaction failed: ${error.message}`);
    return null;
  }
}

module.exports = {
  deployContract,
  interactWithContract
};
```

## Example Applications

### 1. Price Dashboard

Create a simple price dashboard for Flare assets:

```javascript
// dashboard.js
const { testConnection } = require('./config');
const { getPrice } = require('./ftso');

async function runDashboard() {
  // Test connection
  const connected = await testConnection();
  if (!connected) return;
  
  // Define symbols to track
  const symbols = ['FLR', 'BTC', 'ETH', 'XRP', 'DOGE'];
  
  console.log('🚀 Flare Network Price Dashboard 🚀');
  console.log('=====================================');
  
  // Get prices for all symbols
  for (const symbol of symbols) {
    const priceData = await getPrice(symbol);
    
    if (priceData) {
      console.log(`${symbol}: $${parseFloat(priceData.price).toFixed(4)} (Updated: ${priceData.timestamp})`);
    } else {
      console.log(`${symbol}: Unable to fetch price`);
    }
  }
}

runDashboard();
```

### 2. Event Listener

Monitor FTSO price submissions:

```javascript
// monitor.js
const { provider } = require('./config');
const { ethers } = require('ethers');

// FTSO Manager contract address
const FTSO_MANAGER_ADDRESS = '0x1000000000000000000000000000000000000003';

// Minimal ABI for the event we want to listen to
const FTSO_MANAGER_ABI = [
  "event PriceFinalized(address indexed ftso, uint256 indexed epoch, uint256 price, uint256 timestamp)"
];

async function monitorPrices() {
  // Create contract instance
  const ftsoManager = new ethers.Contract(
    FTSO_MANAGER_ADDRESS,
    FTSO_MANAGER_ABI,
    provider
  );
  
  console.log('🔍 Monitoring FTSO price finalizations...');
  console.log('Press Ctrl+C to stop');
  
  // Listen for price finalization events
  ftsoManager.on('PriceFinalized', (ftso, epoch, price, timestamp, event) => {
    const formattedPrice = ethers.utils.formatUnits(price, 5);
    const date = new Date(timestamp.toNumber() * 1000);
    
    console.log(`
      New Price Finalized:
      FTSO: ${ftso}
      Epoch: ${epoch}
      Price: ${formattedPrice}
      Time: ${date.toISOString()}
    `);
  });
}

monitorPrices();
```

## Troubleshooting

### Common Issues and Solutions

1. **Connection Issues**
   - Verify your RPC URL is correct
   - Check if your network has any firewall restrictions
   - Try using a different RPC endpoint

2. **Transaction Failures**
   - Ensure you have enough FLR for gas
   - Check if your private key is correct
   - Verify contract addresses are correct for the network you're using

3. **FTSO Data Issues**
   - Some symbols might not be supported
   - Price feeds are updated periodically, not continuously
   - Check decimals when displaying prices

### Debugging Tips

```javascript
// Add this to your code for better error messages
process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
});
```

## Resources

- [Flare Developer Hub](https://dev.flare.network/)
- [ethers.js Documentation](https://docs.ethers.io/v5/)
- [Flare Network GitHub](https://github.com/flare-foundation)

---

For more information and detailed examples, visit the [Flare Developer Hub](https://dev.flare.network/). 