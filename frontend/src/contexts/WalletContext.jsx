/**
 * WalletContext.jsx
 * =================
 * Multi-chain wallet connection for Ethereum and Solana.
 * Supports MetaMask, Phantom, WalletConnect.
 */
import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { ethers } from 'ethers';

// Wallet types
const WALLET_TYPES = {
  METAMASK: 'metamask',
  PHANTOM: 'phantom',
  WALLETCONNECT: 'walletconnect',
};

// Chain types
const CHAIN_TYPES = {
  ETHEREUM: 'ethereum',
  SOLANA: 'solana',
};

// Create context
const WalletContext = createContext(null);

// Chain configurations
const CHAIN_CONFIG = {
  ethereum: {
    chainId: '0x1', // Mainnet
    chainIdHex: '0x1',
    chainName: 'Ethereum Mainnet',
    nativeCurrency: { name: 'Ether', symbol: 'ETH', decimals: 18 },
    rpcUrls: ['https://mainnet.infura.io/v3/'],
    blockExplorerUrls: ['https://etherscan.io'],
  },
  base: {
    chainId: '0x2105', // 8453
    chainIdHex: '0x2105',
    chainName: 'Base',
    nativeCurrency: { name: 'Ether', symbol: 'ETH', decimals: 18 },
    rpcUrls: ['https://mainnet.base.org'],
    blockExplorerUrls: ['https://basescan.org'],
  },
  baseSepolia: {
    chainId: '0x14a34', // 84532
    chainIdHex: '0x14a34',
    chainName: 'Base Sepolia',
    nativeCurrency: { name: 'Ether', symbol: 'ETH', decimals: 18 },
    rpcUrls: ['https://sepolia.base.org'],
    blockExplorerUrls: ['https://sepolia.basescan.org'],
  },
};

export function WalletProvider({ children }) {
  // Ethereum wallet state
  const [ethAddress, setEthAddress] = useState(null);
  const [ethBalance, setEthBalance] = useState('0');
  const [ethChainId, setEthChainId] = useState(null);
  const [ethProvider, setEthProvider] = useState(null);
  const [ethSigner, setEthSigner] = useState(null);
  
  // Solana wallet state
  const [solAddress, setSolAddress] = useState(null);
  const [solBalance, setSolBalance] = useState('0');
  
  // General state
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState(null);
  const [activeChain, setActiveChain] = useState(CHAIN_TYPES.ETHEREUM);

  // Check if wallets are installed
  const isMetaMaskInstalled = typeof window !== 'undefined' && window.ethereum?.isMetaMask;
  const isPhantomInstalled = typeof window !== 'undefined' && window.solana?.isPhantom;

  // ─── Ethereum Wallet Functions ────────────────────────────────────────────

  const connectMetaMask = useCallback(async () => {
    if (!isMetaMaskInstalled) {
      setError('MetaMask is not installed. Please install it from https://metamask.io');
      return false;
    }

    setIsConnecting(true);
    setError(null);

    try {
      const provider = new ethers.BrowserProvider(window.ethereum);
      const accounts = await provider.send('eth_requestAccounts', []);
      
      if (accounts.length === 0) {
        throw new Error('No accounts found');
      }

      const signer = await provider.getSigner();
      const address = await signer.getAddress();
      const balance = await provider.getBalance(address);
      const network = await provider.getNetwork();

      setEthProvider(provider);
      setEthSigner(signer);
      setEthAddress(address);
      setEthBalance(ethers.formatEther(balance));
      setEthChainId(network.chainId.toString());
      setActiveChain(CHAIN_TYPES.ETHEREUM);

      // Store connection preference
      localStorage.setItem('wallet_connected', WALLET_TYPES.METAMASK);
      
      setIsConnecting(false);
      return true;
    } catch (err) {
      setError(err.message);
      setIsConnecting(false);
      return false;
    }
  }, [isMetaMaskInstalled]);

  const switchToBase = useCallback(async () => {
    if (!window.ethereum) return false;

    try {
      await window.ethereum.request({
        method: 'wallet_switchEthereumChain',
        params: [{ chainId: CHAIN_CONFIG.base.chainId }],
      });
      return true;
    } catch (switchError) {
      // Chain not added, add it
      if (switchError.code === 4902) {
        try {
          await window.ethereum.request({
            method: 'wallet_addEthereumChain',
            params: [CHAIN_CONFIG.base],
          });
          return true;
        } catch (addError) {
          setError('Failed to add Base network');
          return false;
        }
      }
      setError('Failed to switch network');
      return false;
    }
  }, []);

  const switchToBaseSepolia = useCallback(async () => {
    if (!window.ethereum) return false;

    try {
      await window.ethereum.request({
        method: 'wallet_switchEthereumChain',
        params: [{ chainId: CHAIN_CONFIG.baseSepolia.chainId }],
      });
      return true;
    } catch (switchError) {
      if (switchError.code === 4902) {
        try {
          await window.ethereum.request({
            method: 'wallet_addEthereumChain',
            params: [CHAIN_CONFIG.baseSepolia],
          });
          return true;
        } catch (addError) {
          setError('Failed to add Base Sepolia network');
          return false;
        }
      }
      setError('Failed to switch network');
      return false;
    }
  }, []);

  // ─── Solana Wallet Functions ──────────────────────────────────────────────

  const connectPhantom = useCallback(async () => {
    if (!isPhantomInstalled) {
      setError('Phantom wallet is not installed. Please install it from https://phantom.app');
      return false;
    }

    setIsConnecting(true);
    setError(null);

    try {
      const response = await window.solana.connect();
      const publicKey = response.publicKey.toString();
      
      setSolAddress(publicKey);
      setActiveChain(CHAIN_TYPES.SOLANA);

      // Fetch balance
      try {
        const connection = new (await import('@solana/web3.js')).Connection(
          'https://api.mainnet-beta.solana.com',
          'confirmed'
        );
        const balance = await connection.getBalance(new (await import('@solana/web3.js')).PublicKey(publicKey));
        setSolBalance((balance / 1e9).toFixed(4));
      } catch (e) {
        setSolBalance('0');
      }

      localStorage.setItem('wallet_connected', WALLET_TYPES.PHANTOM);
      
      setIsConnecting(false);
      return true;
    } catch (err) {
      setError(err.message);
      setIsConnecting(false);
      return false;
    }
  }, [isPhantomInstalled]);

  // ─── Disconnect Functions ─────────────────────────────────────────────────

  const disconnect = useCallback(async () => {
    // Disconnect MetaMask
    if (ethAddress && window.ethereum) {
      // MetaMask doesn't have a true disconnect, but we can clear state
      setEthAddress(null);
      setEthBalance('0');
      setEthChainId(null);
      setEthProvider(null);
      setEthSigner(null);
    }

    // Disconnect Phantom
    if (solAddress && window.solana) {
      try {
        await window.solana.disconnect();
      } catch (e) {
        // Ignore disconnect errors
      }
      setSolAddress(null);
      setSolBalance('0');
    }

    localStorage.removeItem('wallet_connected');
    setActiveChain(CHAIN_TYPES.ETHEREUM);
  }, [ethAddress, solAddress]);

  // ─── Auto-reconnect on load ───────────────────────────────────────────────

  useEffect(() => {
    const reconnect = async () => {
      const lastWallet = localStorage.getItem('wallet_connected');
      
      if (lastWallet === WALLET_TYPES.METAMASK && isMetaMaskInstalled) {
        await connectMetaMask();
      } else if (lastWallet === WALLET_TYPES.PHANTOM && isPhantomInstalled) {
        await connectPhantom();
      }
    };

    // Listen for account changes
    if (window.ethereum) {
      window.ethereum.on('accountsChanged', (accounts) => {
        if (accounts.length === 0) {
          setEthAddress(null);
          setEthBalance('0');
        } else {
          setEthAddress(accounts[0]);
          // Refresh balance
          if (ethProvider) {
            ethProvider.getBalance(accounts[0]).then((balance) => {
              setEthBalance(ethers.formatEther(balance));
            });
          }
        }
      });

      window.ethereum.on('chainChanged', (chainId) => {
        setEthChainId(parseInt(chainId, 16).toString());
        window.location.reload(); // Recommended by MetaMask
      });
    }

    if (window.solana) {
      window.solana.on('disconnect', () => {
        setSolAddress(null);
        setSolBalance('0');
      });

      window.solana.on('accountChanged', (publicKey) => {
        if (publicKey) {
          setSolAddress(publicKey.toString());
        } else {
          setSolAddress(null);
          setSolBalance('0');
        }
      });
    }

    reconnect();
  }, [isMetaMaskInstalled, isPhantomInstalled, connectMetaMask, connectPhantom, ethProvider]);

  // ─── Sign Transaction ──────────────────────────────────────────────────────

  const signMessage = useCallback(async (message) => {
    if (activeChain === CHAIN_TYPES.ETHEREUM && ethSigner) {
      return await ethSigner.signMessage(message);
    } else if (activeChain === CHAIN_TYPES.SOLANA && window.solana) {
      const encoded = new TextEncoder().encode(message);
      const signed = await window.solana.signMessage(encoded, 'utf8');
      return Buffer.from(signed.signature).toString('hex');
    }
    throw new Error('No wallet connected');
  }, [activeChain, ethSigner]);

  const sendTransaction = useCallback(async (to, value, data = '0x') => {
    if (!ethSigner) {
      throw new Error('No wallet connected');
    }

    const tx = await ethSigner.sendTransaction({
      to,
      value: ethers.parseEther(value.toString()),
      data,
    });

    return tx.hash;
  }, [ethSigner]);

  // ─── Context Value ────────────────────────────────────────────────────────

  const value = {
    // Ethereum
    ethAddress,
    ethBalance,
    ethChainId,
    ethProvider,
    ethSigner,
    
    // Solana
    solAddress,
    solBalance,
    
    // General
    activeChain,
    isConnecting,
    error,
    
    // Wallet status
    isMetaMaskInstalled,
    isPhantomInstalled,
    isConnected: !!(ethAddress || solAddress),
    walletType: ethAddress ? WALLET_TYPES.METAMASK : solAddress ? WALLET_TYPES.PHANTOM : null,
    
    // Actions
    connectMetaMask,
    connectPhantom,
    disconnect,
    switchToBase,
    switchToBaseSepolia,
    signMessage,
    sendTransaction,
    
    // Chain info
    chainName: ethChainId === '1' ? 'Ethereum' : 
               ethChainId === '8453' ? 'Base' : 
               ethChainId === '84532' ? 'Base Sepolia' : 
               'Unknown',
  };

  return (
    <WalletContext.Provider value={value}>
      {children}
    </WalletContext.Provider>
  );
}

// ─── Hook ──────────────────────────────────────────────────────────────────

export function useWallet() {
  const context = useContext(WalletContext);
  if (!context) {
    throw new Error('useWallet must be used within a WalletProvider');
  }
  return context;
}

// ─── Wallet Types and chains exports ───────────────────────────────────────

export { WALLET_TYPES, CHAIN_TYPES, CHAIN_CONFIG };