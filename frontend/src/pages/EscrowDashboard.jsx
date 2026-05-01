/**
 * EscrowDashboard.jsx
 * ===================
 * Comprehensive dashboard for:
 * - Trading capital escrow management
 * - Profit withdrawal to owner wallet
 * - x402 API payment collection
 * - Automatic fee splitting
 * - PnL tracking
 * - Wallet connection for deposits/withdrawals
 */
import { useState, useEffect } from 'react';
import { BarChart3, TrendingUp, Wallet, DollarSign, ArrowUpRight, ArrowDownRight, Settings, Clock, AlertCircle, Link2, Check } from 'lucide-react';
import { useWallet } from '../contexts/WalletContext';
import WalletConnectButton from '../components/WalletConnectButton';

const API_BASE = '/api/v1';

export default function EscrowDashboard() {
  // Wallet connection
  const { 
    isConnected, 
    ethAddress, 
    ethBalance, 
    ethChainId,
    switchToBase,
    switchToBaseSepolia,
    sendTransaction,
    signMessage,
    chainName,
    walletType
  } = useWallet();

  const [escrowSummary, setEscrowSummary] = useState(null);
  const [pnlData, setPnlData] = useState(null);
  const [profitSplit, setProfitSplit] = useState(null);
  const [trades, setTrades] = useState([]);
  const [withdrawals, setWithdrawals] = useState([]);
  const [x402Payments, setX402Payments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Configuration modals
  const [showFeeConfig, setShowFeeConfig] = useState(false);
  const [showWithdrawModal, setShowWithdrawModal] = useState(false);
  const [showDepositModal, setShowDepositModal] = useState(false);

  // Form states
  const [withdrawAmount, setWithdrawAmount] = useState('');
  const [depositAmount, setDepositAmount] = useState('');
  const [feeConfig, setFeeConfig] = useState({
    trading_fee_bps: 50,
    profit_share_bps: 1000,
    x402_allocation_bps: 0,
  });

  // Transaction state
  const [txPending, setTxPending] = useState(false);
  const [txHash, setTxHash] = useState(null);

  useEffect(() => {
    fetchAllData();
    const interval = setInterval(fetchAllData, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const fetchAllData = async () => {
    try {
      const [escrowRes, pnlRes, profitSplitRes, tradesRes, withdrawalsRes, x402Res] = await Promise.all([
        fetch(`${API_BASE}/escrow/summary`).then(r => r.json()),
        fetch(`${API_BASE}/escrow/pnl-dashboard`).then(r => r.json()),
        fetch(`${API_BASE}/escrow/profit-split`).then(r => r.json()),
        fetch(`${API_BASE}/escrow/trades?limit=10`).then(r => r.json()),
        fetch(`${API_BASE}/escrow/withdrawals?limit=10`).then(r => r.json()),
        fetch(`${API_BASE}/escrow/x402-payments?limit=10`).then(r => r.json()),
      ]);

      setEscrowSummary(escrowRes);
      setPnlData(pnlRes);
      setProfitSplit(profitSplitRes);
      setTrades(tradesRes);
      setWithdrawals(withdrawalsRes);
      setX402Payments(x402Res);
      setLoading(false);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  const handleWithdraw = async () => {
    if (!withdrawAmount || parseFloat(withdrawAmount) <= 0) return;
    
    try {
      const res = await fetch(`${API_BASE}/escrow/withdraw`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          token_address: '0x0000000000000000000000000000000000000000',
          amount: parseFloat(withdrawAmount),
        }),
      });
      
      if (res.ok) {
        setShowWithdrawModal(false);
        setWithdrawAmount('');
        fetchAllData();
      } else {
        const err = await res.json();
        alert(`Withdrawal failed: ${err.detail}`);
      }
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  };

  const handleWithdrawAll = async () => {
    try {
      const res = await fetch(`${API_BASE}/escrow/withdraw-all`, {
        method: 'POST',
      });
      
      if (res.ok) {
        fetchAllData();
      } else {
        const err = await res.json();
        alert(`Withdrawal failed: ${err.detail}`);
      }
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  };

  const handleDeposit = async () => {
    if (!depositAmount || parseFloat(depositAmount) <= 0) return;
    
    try {
      const res = await fetch(`${API_BASE}/escrow/deposit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          token_address: '0x0000000000000000000000000000000000000000',
          amount: parseFloat(depositAmount),
        }),
      });
      
      if (res.ok) {
        setShowDepositModal(false);
        setDepositAmount('');
        fetchAllData();
      }
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  };

  const handleFeeConfig = async () => {
    try {
      const res = await fetch(`${API_BASE}/escrow/configure/fees`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(feeConfig),
      });
      
      if (res.ok) {
        setShowFeeConfig(false);
        fetchAllData();
      }
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-lg text-gray-400">Loading escrow dashboard...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-red-400 flex items-center gap-2">
          <AlertCircle className="w-5 h-5" />
          Error: {error}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-white">Escrow & Revenue Dashboard</h1>
          <p className="text-gray-400 mt-1">
            Smart contract escrow for trading capital, profit collection, and x402 payments
          </p>
        </div>
        <div className="flex items-center gap-4">
          {/* Wallet Connection */}
          <WalletConnectButton 
            onConnect={(type) => {
              console.log('Wallet connected:', type);
              fetchAllData();
            }}
          />
          <button
            onClick={() => setShowFeeConfig(true)}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg flex items-center gap-2"
          >
            <Settings className="w-4 h-4" />
            Configure Fees
          </button>
        </div>
      </div>

      {/* Connected Wallet Info */}
      {isConnected && (
        <div className="bg-gray-800 rounded-xl p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-3 h-3 rounded-full bg-green-500 animate-pulse" />
            <div>
              <p className="text-sm text-gray-400">Connected Wallet</p>
              <p className="font-mono text-sm">{ethAddress?.slice(0, 10)}...{ethAddress?.slice(-8)}</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-right">
              <p className="text-xs text-gray-500">Balance</p>
              <p className="font-mono">{parseFloat(ethBalance).toFixed(4)} ETH</p>
            </div>
            <div className="text-right">
              <p className="text-xs text-gray-500">Network</p>
              <p className="text-sm">{chainName}</p>
            </div>
            {/* Network Switch for Base */}
            {walletType === 'metamask' && (
              <div className="flex gap-2">
                <button
                  onClick={switchToBase}
                  className={`px-3 py-1 text-xs rounded-lg transition-colors ${
                    ethChainId === '8453' ? 'bg-blue-500/20 text-blue-400' : 'bg-gray-700 hover:bg-gray-600'
                  }`}
                >
                  Base
                </button>
                <button
                  onClick={switchToBaseSepolia}
                  className={`px-3 py-1 text-xs rounded-lg transition-colors ${
                    ethChainId === '84532' ? 'bg-blue-500/20 text-blue-400' : 'bg-gray-700 hover:bg-gray-600'
                  }`}
                >
                  Base Sepolia
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Trading Balance */}
        <div className="bg-gray-800 rounded-xl p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Trading Balance</p>
              <p className="text-2xl font-bold text-white mt-1">
                ${escrowSummary?.trading_balance?.toFixed(2) || '0.00'}
              </p>
            </div>
            <div className="p-3 bg-blue-500/20 rounded-lg">
              <Wallet className="w-6 h-6 text-blue-400" />
            </div>
          </div>
          <button
            onClick={() => setShowDepositModal(true)}
            className="mt-4 w-full py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-sm"
          >
            Deposit Capital
          </button>
        </div>

        {/* Total Profit */}
        <div className="bg-gray-800 rounded-xl p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Total Profit</p>
              <p className="text-2xl font-bold text-green-400 mt-1">
                ${escrowSummary?.total_profit?.toFixed(2) || '0.00'}
              </p>
            </div>
            <div className="p-3 bg-green-500/20 rounded-lg">
              <TrendingUp className="w-6 h-6 text-green-400" />
            </div>
          </div>
          <p className="text-gray-500 text-sm mt-2">
            Withdrawable: ${escrowSummary?.withdrawable_profit?.toFixed(2) || '0.00'}
          </p>
        </div>

        {/* Trading Fees */}
        <div className="bg-gray-800 rounded-xl p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Trading Fees Collected</p>
              <p className="text-2xl font-bold text-yellow-400 mt-1">
                ${escrowSummary?.total_fees_collected?.toFixed(2) || '0.00'}
              </p>
            </div>
            <div className="p-3 bg-yellow-500/20 rounded-lg">
              <DollarSign className="w-6 h-6 text-yellow-400" />
            </div>
          </div>
          <p className="text-gray-500 text-sm mt-2">
            Fee rate: {(escrowSummary?.trading_fee_bps / 100).toFixed(2)}%
          </p>
        </div>

        {/* x402 Payments */}
        <div className="bg-gray-800 rounded-xl p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">x402 API Payments</p>
              <p className="text-2xl font-bold text-purple-400 mt-1">
                ${profitSplit?.x402_payments_collected?.toFixed(2) || '0.00'}
              </p>
            </div>
            <div className="p-3 bg-purple-500/20 rounded-lg">
              <BarChart3 className="w-6 h-6 text-purple-400" />
            </div>
          </div>
          <p className="text-gray-500 text-sm mt-2">
            From {x402Payments?.payment_count || 0} API calls
          </p>
        </div>
      </div>

      {/* Withdrawal Section */}
      <div className="bg-gray-800 rounded-xl p-6">
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <ArrowUpRight className="w-5 h-5 text-green-400" />
          Withdraw Profits to Owner Wallet
        </h2>
        <div className="flex items-center gap-4">
          <div className="flex-1">
            <p className="text-gray-400 text-sm mb-2">
              Withdrawable Profit: <span className="text-green-400 font-bold">${escrowSummary?.withdrawable_profit?.toFixed(2) || '0.00'}</span>
            </p>
            <p className="text-gray-500 text-xs">
              Recipient: {escrowSummary?.owner_address || 'Not configured'}
            </p>
          </div>
          <button
            onClick={() => setShowWithdrawModal(true)}
            className="px-4 py-2 bg-green-600 hover:bg-green-500 rounded-lg"
          >
            Withdraw Amount
          </button>
          <button
            onClick={handleWithdrawAll}
            className="px-4 py-2 bg-green-700 hover:bg-green-600 rounded-lg"
          >
            Withdraw All
          </button>
        </div>
      </div>

      {/* Revenue Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* PnL Dashboard */}
        <div className="bg-gray-800 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Revenue Breakdown</h2>
          {pnlData && (
            <div className="space-y-4">
              <div className="flex justify-between items-center p-3 bg-gray-700/50 rounded-lg">
                <span className="text-gray-400">Trading Profits</span>
                <span className="text-green-400 font-mono">${pnlData.revenue?.trading_profits?.toFixed(2) || '0.00'}</span>
              </div>
              <div className="flex justify-between items-center p-3 bg-gray-700/50 rounded-lg">
                <span className="text-gray-400">Trading Fees</span>
                <span className="text-yellow-400 font-mono">${pnlData.revenue?.trading_fees?.toFixed(2) || '0.00'}</span>
              </div>
              <div className="flex justify-between items-center p-3 bg-gray-700/50 rounded-lg">
                <span className="text-gray-400">x402 API Payments</span>
                <span className="text-purple-400 font-mono">${pnlData.revenue?.x402_api_payments?.toFixed(2) || '0.00'}</span>
              </div>
              <div className="border-t border-gray-700 pt-3 flex justify-between items-center">
                <span className="text-white font-semibold">Total Revenue</span>
                <span className="text-white font-bold font-mono">${pnlData.revenue?.total?.toFixed(2) || '0.00'}</span>
              </div>
            </div>
          )}
        </div>

        {/* Fee Distribution */}
        <div className="bg-gray-800 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Fee Distribution</h2>
          {profitSplit && (
            <div className="space-y-4">
              <div className="flex justify-between items-center p-3 bg-gray-700/50 rounded-lg">
                <span className="text-gray-400">Trading Fee Rate</span>
                <span className="text-white font-mono">{(profitSplit.trading_fee_bps / 100).toFixed(2)}%</span>
              </div>
              <div className="flex justify-between items-center p-3 bg-gray-700/50 rounded-lg">
                <span className="text-gray-400">Profit Share Rate</span>
                <span className="text-white font-mono">{(profitSplit.profit_share_bps / 100).toFixed(2)}%</span>
              </div>
              <div className="flex justify-between items-center p-3 bg-gray-700/50 rounded-lg">
                <span className="text-gray-400">x402 Allocation</span>
                <span className="text-white font-mono">{(profitSplit.x402_allocation_bps / 100).toFixed(2)}%</span>
              </div>
              <div className="border-t border-gray-700 pt-3">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-gray-400">Owner Share</span>
                  <span className="text-green-400 font-mono">${profitSplit.owner_share?.toFixed(2) || '0.00'}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-400">x402 Pool</span>
                  <span className="text-purple-400 font-mono">${profitSplit.x402_share?.toFixed(2) || '0.00'}</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Trade History */}
      <div className="bg-gray-800 rounded-xl p-6">
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Clock className="w-5 h-5 text-gray-400" />
          Recent Trades
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-left text-gray-400 text-sm border-b border-gray-700">
                <th className="pb-3">Trade ID</th>
                <th className="pb-3">Token In</th>
                <th className="pb-3">Token Out</th>
                <th className="pb-3">Amount In</th>
                <th className="pb-3">Amount Out</th>
                <th className="pb-3">Fee</th>
                <th className="pb-3">Result</th>
                <th className="pb-3">Time</th>
              </tr>
            </thead>
            <tbody>
              {trades.length === 0 ? (
                <tr>
                  <td colSpan={8} className="text-center text-gray-500 py-8">
                    No trades recorded yet
                  </td>
                </tr>
              ) : (
                trades.map((trade, idx) => (
                  <tr key={idx} className="border-b border-gray-700/50">
                    <td className="py-3 font-mono text-xs text-gray-400">
                      {trade.trade_id?.slice(0, 16)}...
                    </td>
                    <td className="py-3 font-mono text-xs">{trade.token_in?.slice(0, 10)}...</td>
                    <td className="py-3 font-mono text-xs">{trade.token_out?.slice(0, 10)}...</td>
                    <td className="py-3">{trade.amount_in?.toFixed(4)}</td>
                    <td className="py-3">{trade.amount_out?.toFixed(4)}</td>
                    <td className="py-3 text-yellow-400">{trade.fee_deducted?.toFixed(6)}</td>
                    <td className="py-3">
                      {trade.is_profit ? (
                        <span className="flex items-center gap-1 text-green-400">
                          <ArrowUpRight className="w-4 h-4" />
                          Profit
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 text-red-400">
                          <ArrowDownRight className="w-4 h-4" />
                          Loss
                        </span>
                      )}
                    </td>
                    <td className="py-3 text-gray-400 text-xs">
                      {new Date(trade.timestamp).toLocaleString()}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Withdrawal History */}
      <div className="bg-gray-800 rounded-xl p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Withdrawal History</h2>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-left text-gray-400 text-sm border-b border-gray-700">
                <th className="pb-3">Recipient</th>
                <th className="pb-3">Token</th>
                <th className="pb-3">Amount</th>
                <th className="pb-3">Time</th>
              </tr>
            </thead>
            <tbody>
              {withdrawals.length === 0 ? (
                <tr>
                  <td colSpan={4} className="text-center text-gray-500 py-8">
                    No withdrawals yet
                  </td>
                </tr>
              ) : (
                withdrawals.map((w, idx) => (
                  <tr key={idx} className="border-b border-gray-700/50">
                    <td className="py-3 font-mono text-xs">{w.recipient?.slice(0, 20)}...</td>
                    <td className="py-3 font-mono text-xs">{w.token?.slice(0, 10)}...</td>
                    <td className="py-3 text-green-400">${w.amount?.toFixed(2)}</td>
                    <td className="py-3 text-gray-400 text-xs">
                      {new Date(w.timestamp).toLocaleString()}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Fee Configuration Modal */}
      {showFeeConfig && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-xl p-6 w-full max-w-md">
            <h3 className="text-lg font-semibold text-white mb-4">Configure Fee Distribution</h3>
            <div className="space-y-4">
              <div>
                <label className="text-gray-400 text-sm">Trading Fee (basis points)</label>
                <input
                  type="number"
                  value={feeConfig.trading_fee_bps}
                  onChange={(e) => setFeeConfig({ ...feeConfig, trading_fee_bps: parseInt(e.target.value) })}
                  className="w-full mt-1 px-3 py-2 bg-gray-700 rounded-lg text-white"
                  max={1000}
                />
                <p className="text-gray-500 text-xs mt-1">
                  Current: {(feeConfig.trading_fee_bps / 100).toFixed(2)}%
                </p>
              </div>
              <div>
                <label className="text-gray-400 text-sm">Profit Share (basis points)</label>
                <input
                  type="number"
                  value={feeConfig.profit_share_bps}
                  onChange={(e) => setFeeConfig({ ...feeConfig, profit_share_bps: parseInt(e.target.value) })}
                  className="w-full mt-1 px-3 py-2 bg-gray-700 rounded-lg text-white"
                  max={5000}
                />
                <p className="text-gray-500 text-xs mt-1">
                  Current: {(feeConfig.profit_share_bps / 100).toFixed(2)}%
                </p>
              </div>
              <div>
                <label className="text-gray-400 text-sm">x402 Allocation (basis points)</label>
                <input
                  type="number"
                  value={feeConfig.x402_allocation_bps}
                  onChange={(e) => setFeeConfig({ ...feeConfig, x402_allocation_bps: parseInt(e.target.value) })}
                  className="w-full mt-1 px-3 py-2 bg-gray-700 rounded-lg text-white"
                  max={1000}
                />
                <p className="text-gray-500 text-xs mt-1">
                  Portion of fees to x402 pool: {(feeConfig.x402_allocation_bps / 100).toFixed(2)}%
                </p>
              </div>
            </div>
            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowFeeConfig(false)}
                className="flex-1 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleFeeConfig}
                className="flex-1 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg"
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Withdraw Modal */}
      {showWithdrawModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-xl p-6 w-full max-w-md">
            <h3 className="text-lg font-semibold text-white mb-4">Withdraw Profits</h3>
            <p className="text-gray-400 text-sm mb-4">
              Withdrawable: ${escrowSummary?.withdrawable_profit?.toFixed(2) || '0.00'}
            </p>
            <div>
              <label className="text-gray-400 text-sm">Amount to Withdraw</label>
              <input
                type="number"
                value={withdrawAmount}
                onChange={(e) => setWithdrawAmount(e.target.value)}
                className="w-full mt-1 px-3 py-2 bg-gray-700 rounded-lg text-white"
                placeholder="0.00"
                max={escrowSummary?.withdrawable_profit || 0}
              />
            </div>
            <div className="flex gap-3 mt-6">
              <button
                onClick={() => {
                  setShowWithdrawModal(false);
                  setWithdrawAmount('');
                }}
                className="flex-1 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleWithdraw}
                className="flex-1 py-2 bg-green-600 hover:bg-green-500 rounded-lg"
              >
                Withdraw
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Deposit Modal */}
      {showDepositModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-xl p-6 w-full max-w-md">
            <h3 className="text-lg font-semibold text-white mb-4">Deposit Trading Capital</h3>
            <div>
              <label className="text-gray-400 text-sm">Amount to Deposit (ETH)</label>
              <input
                type="number"
                value={depositAmount}
                onChange={(e) => setDepositAmount(e.target.value)}
                className="w-full mt-1 px-3 py-2 bg-gray-700 rounded-lg text-white"
                placeholder="0.00"
              />
              <p className="text-gray-500 text-xs mt-2">
                This will be deposited to the smart contract escrow for AI trading.
              </p>
            </div>
            <div className="flex gap-3 mt-6">
              <button
                onClick={() => {
                  setShowDepositModal(false);
                  setDepositAmount('');
                }}
                className="flex-1 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleDeposit}
                className="flex-1 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg"
              >
                Deposit
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}