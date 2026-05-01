/**
 * WalletConnectButton.jsx
 * ========================
 * Multi-chain wallet connection button with dropdown.
 * Supports MetaMask (Ethereum) and Phantom (Solana).
 */
import { useState, useRef, useEffect } from 'react';
import { useWallet, WALLET_TYPES, CHAIN_CONFIG } from '../contexts/WalletContext';
import { Wallet, ChevronDown, Copy, ExternalLink, LogOut, AlertCircle, CheckCircle } from 'lucide-react';

export default function WalletConnectButton({ onConnect, showChainSwitch = true }) {
  const {
    ethAddress,
    ethBalance,
    ethChainId,
    solAddress,
    solBalance,
    activeChain,
    isConnecting,
    error,
    isMetaMaskInstalled,
    isPhantomInstalled,
    isConnected,
    walletType,
    connectMetaMask,
    connectPhantom,
    disconnect,
    switchToBase,
    switchToBaseSepolia,
    chainName,
  } = useWallet();

  const [showDropdown, setShowDropdown] = useState(false);
  const [copied, setCopied] = useState(false);
  const dropdownRef = useRef(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const copyAddress = async () => {
    const address = ethAddress || solAddress;
    if (address) {
      await navigator.clipboard.writeText(address);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const formatAddress = (address) => {
    if (!address) return '';
    return `${address.slice(0, 6)}...${address.slice(-4)}`;
  };

  const handleConnect = async (walletType) => {
    let success = false;
    if (walletType === 'metamask') {
      success = await connectMetaMask();
    } else if (walletType === 'phantom') {
      success = await connectPhantom();
    }
    if (success && onConnect) {
      onConnect(walletType);
    }
    setShowDropdown(false);
  };

  // Not connected state
  if (!isConnected) {
    return (
      <div className="relative" ref={dropdownRef}>
        <button
          onClick={() => setShowDropdown(!showDropdown)}
          disabled={isConnecting}
          className="flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors"
          style={{
            background: 'var(--accent-blue)',
            color: 'white',
          }}
        >
          <Wallet className="w-4 h-4" />
          {isConnecting ? 'Connecting...' : 'Connect Wallet'}
          <ChevronDown className="w-4 h-4" />
        </button>

        {showDropdown && (
          <div
            className="absolute top-full right-0 mt-2 w-72 rounded-xl shadow-xl z-50"
            style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}
          >
            <div className="p-4">
              <p className="text-sm text-gray-400 mb-3">Select your wallet</p>

              {/* MetaMask Option */}
              <button
                onClick={() => handleConnect('metamask')}
                disabled={!isMetaMaskInstalled}
                className={`w-full flex items-center gap-3 p-3 rounded-lg transition-colors ${
                  isMetaMaskInstalled
                    ? 'hover:bg-white/5 cursor-pointer'
                    : 'opacity-50 cursor-not-allowed'
                }`}
                style={{ border: '1px solid var(--border)' }}
              >
                <div className="w-8 h-8 rounded-lg bg-orange-500/20 flex items-center justify-center">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                    <path
                      d="M21.5 6L13 2L4.5 6L6 7.5L4 11L6.5 13.5L5 18L13 22L21 18L19.5 13.5L22 11L20 7.5L21.5 6Z"
                      fill="#F6851B"
                    />
                    <path d="M13 2L6 7.5L13 6.5V2Z" fill="#E2761B" />
                    <path d="M13 2L20 7.5L13 6.5V2Z" fill="#E4761B" />
                  </svg>
                </div>
                <div className="flex-1 text-left">
                  <p className="font-medium">MetaMask</p>
                  <p className="text-xs text-gray-500">
                    {isMetaMaskInstalled ? 'Ethereum & EVM chains' : 'Not installed'}
                  </p>
                </div>
                {!isMetaMaskInstalled && (
                  <ExternalLink className="w-4 h-4 text-gray-400" />
                )}
              </button>

              {/* Phantom Option */}
              <button
                onClick={() => handleConnect('phantom')}
                disabled={!isPhantomInstalled}
                className={`w-full flex items-center gap-3 p-3 rounded-lg transition-colors mt-2 ${
                  isPhantomInstalled
                    ? 'hover:bg-white/5 cursor-pointer'
                    : 'opacity-50 cursor-not-allowed'
                }`}
                style={{ border: '1px solid var(--border)' }}
              >
                <div className="w-8 h-8 rounded-lg bg-purple-500/20 flex items-center justify-center">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                    <path
                      d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8z"
                      fill="#AB4DFF"
                    />
                    <path d="M12 6l-2 8h4l-2-8z" fill="#AB4DFF" />
                  </svg>
                </div>
                <div className="flex-1 text-left">
                  <p className="font-medium">Phantom</p>
                  <p className="text-xs text-gray-500">
                    {isPhantomInstalled ? 'Solana network' : 'Not installed'}
                  </p>
                </div>
                {!isPhantomInstalled && (
                  <ExternalLink className="w-4 h-4 text-gray-400" />
                )}
              </button>

              {error && (
                <div className="mt-3 p-2 rounded-lg bg-red-500/10 text-red-400 text-xs flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  {error}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    );
  }

  // Connected state
  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setShowDropdown(!showDropdown)}
        className="flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors"
        style={{
          background: 'var(--bg-secondary)',
          border: '1px solid var(--border)',
        }}
      >
        {/* Status indicator */}
        <div className="w-2 h-2 rounded-full bg-green-500" />
        
        {/* Balance */}
        <span className="text-sm text-gray-400">
          {walletType === 'metamask' ? `${parseFloat(ethBalance).toFixed(4)} ETH` : `${solBalance} SOL`}
        </span>
        
        {/* Address */}
        <span className="text-sm font-mono">
          {formatAddress(ethAddress || solAddress)}
        </span>
        
        <ChevronDown className="w-4 h-4 text-gray-400" />
      </button>

      {showDropdown && (
        <div
          className="absolute top-full right-0 mt-2 w-80 rounded-xl shadow-xl z-50"
          style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}
        >
          <div className="p-4">
            {/* Connected wallet info */}
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-green-500" />
                <span className="text-sm text-gray-400">Connected</span>
              </div>
              <span className="text-xs px-2 py-1 rounded-lg" style={{ background: 'var(--bg-primary)' }}>
                {chainName}
              </span>
            </div>

            {/* Address */}
            <div className="p-3 rounded-lg" style={{ background: 'var(--bg-primary)' }}>
              <p className="text-xs text-gray-500 mb-1">Address</p>
              <div className="flex items-center justify-between">
                <p className="font-mono text-sm truncate">
                  {ethAddress || solAddress}
                </p>
                <button
                  onClick={copyAddress}
                  className="p-1 hover:bg-white/10 rounded"
                >
                  {copied ? (
                    <CheckCircle className="w-4 h-4 text-green-400" />
                  ) : (
                    <Copy className="w-4 h-4 text-gray-400" />
                  )}
                </button>
              </div>
            </div>

            {/* Balance */}
            <div className="p-3 rounded-lg mt-2" style={{ background: 'var(--bg-primary)' }}>
              <p className="text-xs text-gray-500 mb-1">Balance</p>
              <p className="text-lg font-bold">
                {walletType === 'metamask' 
                  ? `${parseFloat(ethBalance).toFixed(4)} ETH`
                  : `${solBalance} SOL`
                }
              </p>
            </div>

            {/* Chain Switch */}
            {showChainSwitch && walletType === 'metamask' && (
              <div className="mt-4">
                <p className="text-xs text-gray-500 mb-2">Switch Network</p>
                <div className="flex gap-2">
                  <button
                    onClick={switchToBase}
                    className={`flex-1 py-2 text-xs rounded-lg transition-colors ${
                      ethChainId === '8453' ? 'bg-blue-500/20 text-blue-400' : 'hover:bg-white/5'
                    }`}
                    style={{ border: '1px solid var(--border)' }}
                  >
                    Base
                  </button>
                  <button
                    onClick={switchToBaseSepolia}
                    className={`flex-1 py-2 text-xs rounded-lg transition-colors ${
                      ethChainId === '84532' ? 'bg-blue-500/20 text-blue-400' : 'hover:bg-white/5'
                    }`}
                    style={{ border: '1px solid var(--border)' }}
                  >
                    Base Sepolia
                  </button>
                </div>
              </div>
            )}

            {/* Disconnect */}
            <button
              onClick={() => {
                disconnect();
                setShowDropdown(false);
              }}
              className="w-full mt-4 flex items-center justify-center gap-2 py-2 rounded-lg text-red-400 hover:bg-red-500/10 transition-colors"
              style={{ border: '1px solid rgba(239, 68, 68, 0.3)' }}
            >
              <LogOut className="w-4 h-4" />
              Disconnect
            </button>
          </div>
        </div>
      )}
    </div>
  );
}