import { useState, useEffect } from 'react'
import { API_BASE } from '../App'
import { useAppMode } from '../contexts/AppModeContext'

const SCAN_CHAINS = ['ethereum', 'bsc', 'polygon', 'arbitrum', 'base', 'optimism']
const SEVERITY_COLORS = { high: 'var(--accent-red)', medium: 'var(--accent-yellow)', low: 'var(--accent-blue)', info: 'var(--text-secondary)' }

const SCAN_MODE_SOURCE = 'source'
const SCAN_MODE_ADDRESS = 'address'

const DEFAULT_CONTRACT = `// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract VulnerableVault {
    mapping(address => uint) public balances;
    function deposit() public payable { balances[msg.sender] += msg.value; }
    function withdraw() public {
        (bool s,) = msg.sender.call{value: balances[msg.sender]}("");
        require(s);
        balances[msg.sender] = 0;  // ⚠ Reentrancy bug
    }
}`

export default function SecurityPage() {
  const { isSimulation } = useAppMode()
  const [history, setHistory] = useState([])
  const [historyLoading, setHistoryLoading] = useState(true)
  const [scanMode, setScanMode] = useState(SCAN_MODE_SOURCE)

  // Source code mode
  const [contractSource, setContractSource] = useState(DEFAULT_CONTRACT)

  // Address mode
  const [contractAddress, setContractAddress] = useState('')
  const [chain, setChain] = useState('ethereum')

  const [scanning, setScanning] = useState(false)
  const [latestResult, setLatestResult] = useState(null)
  const [scanError, setScanError] = useState(null)

  const fetchHistory = async () => {
    try {
      const res = await fetch(`${API_BASE}/vulnerability/history`)
      const data = await res.json()
      setHistory(data.history || [])
    } catch (e) { console.error('Failed to fetch history', e) }
    setHistoryLoading(false)
  }

  useEffect(() => { fetchHistory() }, [])

  const handleScan = async () => {
    setScanning(true)
    setLatestResult(null)
    setScanError(null)
    try {
      let endpoint, body

      if (scanMode === SCAN_MODE_SOURCE) {
        if (!contractSource.trim()) { setScanning(false); return }
        endpoint = `${API_BASE}/vulnerability/scan`
        body = { contract_source: contractSource, contract_name: 'ManualScan_' + Date.now().toString().slice(-4) }
      } else {
        if (!contractAddress.trim()) { setScanning(false); return }
        endpoint = `${API_BASE}/vulnerability/scan/address`
        body = { address: contractAddress.trim(), chain }
      }

      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })

      if (!res.ok) {
        const err = await res.json()
        setScanError(err.detail || `HTTP ${res.status}`)
        setScanning(false)
        return
      }

      const data = await res.json()
      setLatestResult(data)
      fetchHistory()
    } catch (e) {
      setScanError(e.message)
    }
    setScanning(false)
  }

  const ModeBtn = ({ id, label }) => (
    <button
      onClick={() => { setScanMode(id); setLatestResult(null); setScanError(null) }}
      style={{
        padding: '8px 18px',
        border: 'none',
        cursor: 'pointer',
        fontWeight: 600,
        fontSize: 13,
        borderRadius: '8px 8px 0 0',
        background: scanMode === id ? 'var(--bg-card)' : 'transparent',
        color: scanMode === id ? 'var(--accent-blue)' : 'var(--text-secondary)',
        borderBottom: scanMode === id ? '2px solid var(--accent-blue)' : '2px solid transparent',
        transition: 'all 0.2s',
      }}
    >{label}</button>
  )

  const scanLabel = scanning
    ? (scanMode === SCAN_MODE_ADDRESS ? '🔍 Fetching source & analysing…' : '🛡️ Analysing with Ensemble LLMs…')
    : (scanMode === SCAN_MODE_ADDRESS ? '🔎 Fetch & Scan Contract Address' : '🚀 Start Security Scan')

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold mb-1">Security & Vulnerability Scanner</h1>
        <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
          Ensemble LLM Analysis (GLM-5.1 + Grok 4.20) • FELLMVP Security Verification • 98.8% Accuracy
          {isSimulation && <span className="text-emerald-500 font-bold ml-2">(Simulation Mode - Free Local Models Only)</span>}
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Scan Form */}
        <div className="card">
          <div className="flex gap-1 mb-4" style={{ borderBottom: '1px solid var(--border)' }}>
            <ModeBtn id={SCAN_MODE_SOURCE} label="📋 Paste Source Code" />
            <ModeBtn id={SCAN_MODE_ADDRESS} label="🔗 Contract Address" />
          </div>

          {scanMode === SCAN_MODE_SOURCE && (
            <div className="space-y-3">
              <label className="text-xs font-medium block" style={{ color: 'var(--text-secondary)' }}>
                Solidity Source Code — paste any contract to scan with Ensemble LLMs
              </label>
              <textarea
                rows={14}
                value={contractSource}
                onChange={(e) => setContractSource(e.target.value)}
                className="w-full font-mono text-xs p-3 rounded-lg"
                style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)', resize: 'vertical' }}
              />
            </div>
          )}

          {scanMode === SCAN_MODE_ADDRESS && (
            <div className="space-y-4">
              <div>
                <label className="text-xs font-medium mb-1 block" style={{ color: 'var(--text-secondary)' }}>
                  Contract Address
                </label>
                <input
                  type="text"
                  value={contractAddress}
                  onChange={(e) => setContractAddress(e.target.value)}
                  placeholder="0x..."
                  className="w-full font-mono"
                />
              </div>
              <div>
                <label className="text-xs font-medium mb-1 block" style={{ color: 'var(--text-secondary)' }}>
                  Network
                </label>
                <select value={chain} onChange={(e) => setChain(e.target.value)} className="w-full">
                  {SCAN_CHAINS.map(c => (
                    <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>
                  ))}
                </select>
              </div>
              <div className="p-3 rounded-lg text-xs" style={{ background: 'rgba(59,130,246,0.05)', border: '1px solid rgba(59,130,246,0.15)', color: 'var(--text-secondary)' }}>
                ℹ️ Source is fetched from the block explorer (Etherscan / BscScan / etc.). Only <strong>verified contracts</strong> can be scanned. Add <code>ETHERSCAN_API_KEY</code> to your <code>.env</code> for higher rate limits.
              </div>
            </div>
          )}

          <button
            onClick={handleScan}
            disabled={scanning || (scanMode === SCAN_MODE_SOURCE ? !contractSource.trim() : !contractAddress.trim())}
            className="btn-primary w-full mt-4"
          >
            {scanLabel}
          </button>

          {scanError && (
            <div className="mt-3 p-3 rounded-lg text-xs" style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid var(--accent-red)', color: 'var(--accent-red)' }}>
              ❌ {scanError}
            </div>
          )}
        </div>

        {/* Results + History */}
        <div className="space-y-6">
          {latestResult && (
            <div className="card border-2" style={{ borderColor: latestResult.passed ? 'var(--accent-green)' : 'var(--accent-red)' }}>
              <div className="flex justify-between items-center mb-4">
                <div>
                  <h3 className="font-bold">{latestResult.contract_name}</h3>
                  {latestResult.contract_address && (
                    <div className="text-xs font-mono opacity-60 break-all">{latestResult.contract_address} ({latestResult.chain})</div>
                  )}
                </div>
                <span className={`px-3 py-1 rounded-full text-xs font-bold ${latestResult.passed ? 'metric-positive' : 'metric-negative'}`}>
                  {latestResult.passed ? 'PASSED' : 'REJECTED'}
                </span>
              </div>

              <div className="grid grid-cols-3 gap-3 mb-4 text-center">
                {[
                  { label: 'Risk Score', value: `${(latestResult.overall_risk_score * 100).toFixed(1)}%` },
                  { label: 'Confidence', value: `${(latestResult.ensemble_confidence * 100).toFixed(1)}%` },
                  { label: 'Findings', value: latestResult.findings_count },
                ].map(({ label, value }) => (
                  <div key={label} className="p-2 rounded" style={{ background: 'var(--bg-secondary)' }}>
                    <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>{label}</div>
                    <div className="text-lg font-bold">{value}</div>
                  </div>
                ))}
              </div>

              <div className="space-y-3 max-h-64 overflow-y-auto pr-1">
                {latestResult.findings?.map((f, i) => (
                  <div key={i} className="p-3 rounded-lg text-xs" style={{ background: 'var(--bg-secondary)', borderLeft: `3px solid ${SEVERITY_COLORS[f.severity] || 'var(--border)'}` }}>
                    <div className="flex justify-between font-bold mb-1">
                      <span>{f.title}</span>
                      <div className="flex items-center gap-2">
                        <div className="flex gap-0.5">
                          <span title="GLM-5.1 Reasoning Verified" style={{ opacity: f.glm_verified ? 1 : 0.2 }}>🧠</span>
                          <span title="Grok 4.20 Verified" style={{ opacity: f.grok_verified ? 1 : 0.2 }}>🛡️</span>
                        </div>
                        <span className="uppercase" style={{ color: SEVERITY_COLORS[f.severity] }}>{f.severity}</span>
                      </div>
                    </div>
                    {f.line_number && <div className="opacity-50 mb-1">Line {f.line_number}</div>}
                    <p className="opacity-80 mb-2">{f.description}</p>
                    <div className="font-medium" style={{ color: 'var(--accent-green)' }}>💡 {f.recommendation}</div>
                  </div>
                ))}
                {latestResult.findings_count === 0 && (
                  <div className="text-center py-4 text-sm metric-positive">No vulnerabilities detected ✓</div>
                )}
              </div>
            </div>
          )}

          <div className="card">
            <h3 className="font-bold mb-4">Scan History</h3>
            <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
              {historyLoading ? (
                <div className="text-center py-6 opacity-50">Loading history…</div>
              ) : history.length === 0 ? (
                <div className="text-center py-8 text-sm opacity-50 italic">No scan history found</div>
              ) : (
                history.map((h, i) => (
                  <div key={i} className="flex items-center justify-between p-3 rounded-lg text-sm" style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}>
                    <div>
                      <div className="font-medium">{h.contract_name}</div>
                      <div className="text-xs opacity-50">{new Date(h.timestamp * 1000).toLocaleString()}</div>
                    </div>
                    <div className="text-right">
                      <div className={`font-bold ${h.passed ? 'metric-positive' : 'metric-negative'}`}>
                        {(h.overall_risk_score * 100).toFixed(1)}% Risk
                      </div>
                      <div className="text-xs opacity-50">{h.findings_count} issue(s)</div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
