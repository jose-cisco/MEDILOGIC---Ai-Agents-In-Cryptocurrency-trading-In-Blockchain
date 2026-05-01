import { useState, useEffect } from 'react'
import { API_BASE } from '../App'

const STEPS = [
  { id: 1, label: 'Request', icon: '→', desc: 'Client calls a paid endpoint' },
  { id: 2, label: '402 Response', icon: '⚡', desc: 'Server replies with price + wallet details' },
  { id: 3, label: 'Sign & Send', icon: '✍️', desc: 'Wallet signs and sends USDC on-chain' },
  { id: 4, label: 'Retry', icon: '↩', desc: 'Client retries with tx_hash in X-Payment header' },
  { id: 5, label: 'Verified', icon: '✓', desc: 'Server verifies on-chain and processes request' },
]

const RESOURCES = [
  { id: 'trade_execute', label: 'Trade Execution', route: '/trading/execute', icon: '🚀' },
  { id: 'trade_analyze', label: 'Market Analysis', route: '/trading/analyze', icon: '📊' },
  { id: 'knowledge_hybrid', label: 'Hybrid RAG Query', route: '/knowledge/hybrid-query', icon: '📚' },
  { id: 'knowledge_enhanced', label: 'Enhanced Context', route: '/knowledge/enhanced-context', icon: '🔬' },
  { id: 'governance_policy', label: 'Policy Check', route: '/governance/policy-check', icon: '⚖️' },
]

const EXEMPT_ROUTES = [
  { route: '/backtest/*', reason: 'Simulation — no real capital' },
  { route: '/payments/*', reason: 'Payment info is always free' },
  { route: '/status/*', reason: 'Health checks are free' },
  { route: '/docs, /redoc', reason: 'API documentation' },
]

export default function PaymentsPage() {
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [activeStep, setActiveStep] = useState(null)
  const [selectedResource, setSelectedResource] = useState('trade_execute')
  const [verifyTxHash, setVerifyTxHash] = useState('')
  const [verifyNetwork, setVerifyNetwork] = useState('8453')
  const [verifyFrom, setVerifyFrom] = useState('')
  const [verifyResult, setVerifyResult] = useState(null)
  const [verifying, setVerifying] = useState(false)
  const [requirement, setRequirement] = useState(null)
  const [fetchingReq, setFetchingReq] = useState(false)

  useEffect(() => {
    fetch(`${API_BASE}/payments/status`)
      .then(r => r.json())
      .then(d => setStatus(d))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  // Step 2: fetch live 402 payment requirement from backend
  const fetchRequirement = async () => {
    setFetchingReq(true)
    setRequirement(null)
    try {
      const res = await fetch(`${API_BASE}/payments/requirement/${selectedResource}`)
      const data = await res.json()
      setRequirement(data)
    } catch (e) {
      setRequirement({ error: e.message })
    }
    setFetchingReq(false)
  }

  // Step 4: verify a payment tx_hash
  const handleVerify = async () => {
    if (!verifyTxHash.trim()) return
    setVerifying(true)
    setVerifyResult(null)
    try {
      const res = await fetch(`${API_BASE}/payments/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tx_hash: verifyTxHash.trim(),
          network_id: verifyNetwork,
          from_address: verifyFrom.trim(),
          resource: selectedResource,
        }),
      })
      setVerifyResult(await res.json())
    } catch (e) {
      setVerifyResult({ valid: false, reason: e.message })
    }
    setVerifying(false)
  }

  if (loading) return <div className="text-center py-16">Loading payment protocol…</div>

  const reqData = requirement?.payment_requirements?.[0]
  const amountUsd = reqData ? (reqData.amount / 1e6).toFixed(6) : '—'
  const selectedPricing = status?.pricing_usd?.[selectedResource]

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold mb-1">x402 Payment Protocol</h1>
        <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
          Pay-per-use AI services · No accounts, no credits, no API key rotation · Just send USDC and go
        </p>
      </div>

      {/* Traditional vs x402 Comparison */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="card" style={{ borderLeft: '3px solid var(--accent-red)', opacity: 0.85 }}>
          <h3 className="font-bold mb-3 text-sm uppercase tracking-wider" style={{ color: 'var(--accent-red)' }}>❌ Traditional API Flow</h3>
          <ol className="space-y-2 text-sm">
            {['Register account & verify email', 'Enter billing info & buy credits', 'Receive API key via email', 'Manage quota & rate limits', 'Rotate keys on expiry or compromise'].map((s, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="mt-0.5 w-5 h-5 rounded-full text-xs flex items-center justify-center flex-shrink-0 font-bold" style={{ background: 'rgba(239,68,68,0.15)', color: 'var(--accent-red)' }}>{i + 1}</span>
                <span style={{ color: 'var(--text-secondary)' }}>{s}</span>
              </li>
            ))}
          </ol>
        </div>
        <div className="card" style={{ borderLeft: '3px solid var(--accent-green)' }}>
          <h3 className="font-bold mb-3 text-sm uppercase tracking-wider" style={{ color: 'var(--accent-green)' }}>✓ x402 Flow</h3>
          <ol className="space-y-2 text-sm">
            {[
              'Request → paid endpoint',
              '← 402: here\'s the price & recipient wallet',
              'Wallet signs & sends USDC on-chain',
              'Retry → with X-Payment: {"tx_hash":"…"}',
              '← Server verifies on-chain → response',
            ].map((s, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="mt-0.5 w-5 h-5 rounded-full text-xs flex items-center justify-center flex-shrink-0 font-bold" style={{ background: 'rgba(16,185,129,0.15)', color: 'var(--accent-green)' }}>{i + 1}</span>
                <span className="font-mono text-xs" style={{ color: 'var(--text-primary)' }}>{s}</span>
              </li>
            ))}
          </ol>
        </div>
      </div>

      {/* Interactive flow */}
      <div className="card">
        <h2 className="font-semibold text-lg mb-1">Interactive Protocol Walkthrough</h2>
        <p className="text-xs mb-5" style={{ color: 'var(--text-secondary)' }}>Click each step to inspect the real payloads your backend sends and receives.</p>

        {/* Resource selector */}
        <div className="mb-5">
          <label className="text-xs font-medium mb-2 block" style={{ color: 'var(--text-secondary)' }}>Select Resource</label>
          <div className="flex flex-wrap gap-2">
            {RESOURCES.map(r => (
              <button
                key={r.id}
                onClick={() => { setSelectedResource(r.id); setRequirement(null); setVerifyResult(null) }}
                style={{
                  padding: '6px 12px',
                  borderRadius: 8,
                  border: `1px solid ${selectedResource === r.id ? 'var(--accent-blue)' : 'var(--border)'}`,
                  background: selectedResource === r.id ? 'rgba(59,130,246,0.1)' : 'var(--bg-secondary)',
                  color: selectedResource === r.id ? 'var(--accent-blue)' : 'var(--text-secondary)',
                  cursor: 'pointer',
                  fontSize: 12,
                  fontWeight: 600,
                  transition: 'all 0.15s',
                }}
              >
                {r.icon} {r.label}
              </button>
            ))}
          </div>
        </div>

        {/* Step timeline */}
        <div className="flex items-start gap-0 mb-6 overflow-x-auto pb-2">
          {STEPS.map((step, i) => (
            <div key={step.id} className="flex items-start">
              <div
                onClick={() => setActiveStep(activeStep === step.id ? null : step.id)}
                style={{
                  cursor: 'pointer',
                  textAlign: 'center',
                  minWidth: 90,
                  padding: '10px 8px',
                  borderRadius: 10,
                  background: activeStep === step.id ? 'rgba(59,130,246,0.1)' : 'transparent',
                  border: `1px solid ${activeStep === step.id ? 'var(--accent-blue)' : 'transparent'}`,
                  transition: 'all 0.2s',
                }}
              >
                <div style={{ fontSize: 22 }}>{step.icon}</div>
                <div style={{ fontSize: 11, fontWeight: 700, marginTop: 4, color: activeStep === step.id ? 'var(--accent-blue)' : 'var(--text-primary)' }}>{step.label}</div>
                <div style={{ fontSize: 10, marginTop: 2, color: 'var(--text-secondary)', lineHeight: 1.3 }}>{step.desc}</div>
              </div>
              {i < STEPS.length - 1 && (
                <div style={{ marginTop: 18, color: 'var(--text-secondary)', fontSize: 18, flexShrink: 0 }}>→</div>
              )}
            </div>
          ))}
        </div>

        {/* Step detail panels */}
        {activeStep === 1 && (
          <StepPanel title="Step 1 — Initial Request (No Payment)">
            <div className="space-y-2 text-xs font-mono">
              <div style={{ color: 'var(--text-secondary)' }}>Client sends:</div>
              <CodeBlock>{`POST /api/v1${RESOURCES.find(r => r.id === selectedResource)?.route}
Content-Type: application/json

{ ...payload }`}</CodeBlock>
              <div style={{ color: 'var(--text-secondary)', marginTop: 8 }}>No X-Payment header. Server will respond with 402.</div>
            </div>
          </StepPanel>
        )}

        {activeStep === 2 && (
          <StepPanel title="Step 2 — Server Returns 402 Payment Required">
            <button onClick={fetchRequirement} disabled={fetchingReq} className="btn-primary mb-4 px-6 py-2 text-sm">
              {fetchingReq ? 'Fetching…' : '📡 Fetch Live 402 Payload from Backend'}
            </button>
            {!status?.enabled && (
              <div className="mb-3 p-3 rounded text-xs" style={{ background: 'rgba(234,179,8,0.08)', border: '1px solid rgba(234,179,8,0.2)', color: 'var(--accent-yellow)' }}>
                ⚠️ x402 is currently disabled (<code>X402_ENABLED=false</code>). Enable it in your <code>.env</code> to see real 402 responses. The example below shows the expected shape.
              </div>
            )}
            {requirement && (
              <CodeBlock>{JSON.stringify(requirement, null, 2)}</CodeBlock>
            )}
            {!requirement && (
              <CodeBlock>{`HTTP/1.1 402 Payment Required
X-Payment-Required: true
X-Payment-Resource: ${selectedResource}

{
  "x402_version": 1,
  "resource": "${selectedResource}",
  "payment_requirements": [{
    "scheme": "exact",
    "kind": "erc20",
    "asset": {
      "address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
      "metadata": { "name": "USDC", "decimals": 6 }
    },
    "amount": ${Math.round((selectedPricing || 0.01) * 1e6)},
    "recipient": "0x<your_wallet>",
    "expires_at": ${Math.floor(Date.now() / 1000) + 600}
  }]
}`}</CodeBlock>
            )}
          </StepPanel>
        )}

        {activeStep === 3 && (
          <StepPanel title="Step 3 — Sign & Send USDC On-Chain">
            <div className="space-y-3 text-xs">
              <p style={{ color: 'var(--text-secondary)' }}>Your wallet sends a USDC ERC-20 transfer to the recipient address. Amount is read from the <code>amount</code> field (6 decimal integer).</p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {[
                  { label: 'Token', value: 'USDC (ERC-20)' },
                  { label: 'Chain', value: status?.testnet ? 'Base Sepolia (testnet)' : 'Base Mainnet' },
                  { label: 'Amount', value: `$${(selectedPricing || 0.01).toFixed(4)} USDC` },
                  { label: 'Recipient', value: status?.recipient_address || '0x<configured wallet>' },
                  { label: 'Window', value: '10 minutes to complete' },
                  { label: 'Nonce', value: 'Server-generated, prevents replay' },
                ].map(({ label, value }) => (
                  <div key={label} className="p-3 rounded-lg" style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}>
                    <div style={{ color: 'var(--text-secondary)' }}>{label}</div>
                    <div className="font-medium font-mono break-all mt-1">{value}</div>
                  </div>
                ))}
              </div>
              <div className="p-3 rounded-lg text-xs" style={{ background: 'rgba(16,185,129,0.05)', border: '1px solid rgba(16,185,129,0.15)' }}>
                💡 On testnet, any tx_hash is accepted. In production, the backend reads the real USDC <code>Transfer</code> event from the block.
              </div>
            </div>
          </StepPanel>
        )}

        {activeStep === 4 && (
          <StepPanel title="Step 4 — Retry with X-Payment Header">
            <div className="space-y-3 text-xs font-mono">
              <div style={{ color: 'var(--text-secondary)' }}>Client retries the original request with X-Payment header:</div>
              <CodeBlock>{`POST /api/v1${RESOURCES.find(r => r.id === selectedResource)?.route}
Content-Type: application/json
X-Payment: {"tx_hash":"0x<transaction_hash>","network_id":"${status?.chain_id || 8453}","from_address":"0x<your_wallet>"}

{ ...same original payload }`}</CodeBlock>
              <p className="font-sans" style={{ color: 'var(--text-secondary)' }}>The middleware intercepts this, verifies the tx_hash on-chain, attaches a receipt to <code>request.state.x402_receipt</code>, and forwards to the handler.</p>
            </div>
          </StepPanel>
        )}

        {activeStep === 5 && (
          <StepPanel title="Step 5 — Verify a Transaction">
            <div className="space-y-3">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-medium mb-1 block" style={{ color: 'var(--text-secondary)' }}>Transaction Hash</label>
                  <input className="w-full font-mono text-xs" type="text" value={verifyTxHash} onChange={e => setVerifyTxHash(e.target.value)} placeholder="0x..." />
                </div>
                <div>
                  <label className="text-xs font-medium mb-1 block" style={{ color: 'var(--text-secondary)' }}>From Address (optional)</label>
                  <input className="w-full font-mono text-xs" type="text" value={verifyFrom} onChange={e => setVerifyFrom(e.target.value)} placeholder="0x..." />
                </div>
              </div>
              <div>
                <label className="text-xs font-medium mb-1 block" style={{ color: 'var(--text-secondary)' }}>Network ID (Chain ID)</label>
                <select className="w-full text-sm" value={verifyNetwork} onChange={e => setVerifyNetwork(e.target.value)}>
                  <option value="8453">8453 — Base Mainnet</option>
                  <option value="84532">84532 — Base Sepolia (Testnet)</option>
                  <option value="1">1 — Ethereum Mainnet</option>
                </select>
              </div>
              <button onClick={handleVerify} disabled={verifying || !verifyTxHash.trim()} className="btn-primary w-full">
                {verifying ? 'Verifying on-chain…' : '🔍 Verify Payment'}
              </button>
              {verifyResult && (
                <div className="p-4 rounded-lg text-xs" style={{
                  background: verifyResult.valid ? 'rgba(16,185,129,0.08)' : 'rgba(239,68,68,0.08)',
                  border: `1px solid ${verifyResult.valid ? 'var(--accent-green)' : 'var(--accent-red)'}`,
                }}>
                  <div className="font-bold mb-2" style={{ color: verifyResult.valid ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                    {verifyResult.valid ? '✓ Payment Verified' : '✗ Verification Failed'}
                  </div>
                  <CodeBlock>{JSON.stringify(verifyResult, null, 2)}</CodeBlock>
                </div>
              )}
            </div>
          </StepPanel>
        )}
      </div>

      {/* Claw402 Provider Panel */}
      <Claw402Panel />

      {/* OpenRouter Provider Panel */}
      <OpenRouterPanel />

      {/* Pricing + Status */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="card space-y-3">
          <h2 className="font-semibold text-lg">Resource Pricing (USDC)</h2>
          <div className="space-y-2">
            {RESOURCES.map(r => (
              <div key={r.id} className="flex justify-between items-center p-3 rounded-lg" style={{ background: 'var(--bg-secondary)', border: selectedResource === r.id ? '1px solid var(--accent-blue)' : '1px solid var(--border)' }}>
                <span className="text-sm">{r.icon} {r.label}</span>
                <span className="font-bold text-sm">${(status?.pricing_usd?.[r.id] || 0).toFixed(4)}</span>
              </div>
            ))}
          </div>
          <div className="pt-2 border-t text-xs italic" style={{ borderColor: 'var(--border)', color: 'var(--text-secondary)' }}>
            All prices in USDC. Backtesting is always free.
          </div>
        </div>

        <div className="card space-y-3">
          <h2 className="font-semibold text-lg">Network & Status</h2>
          <div className="space-y-2 text-sm">
            {[
              { label: 'Protocol Status', value: status?.enabled ? 'ACTIVE' : 'DISABLED (X402_ENABLED=false)', ok: status?.enabled },
              { label: 'Network', value: status?.testnet ? 'Base Sepolia (Testnet)' : 'Base Mainnet' },
              { label: 'Chain ID', value: status?.chain_id },
              { label: 'USDC Contract', value: status?.usdc_address },
              { label: 'Recipient Configured', value: status?.recipient_configured ? 'Yes ✓' : 'Not set', ok: status?.recipient_configured },
            ].map(({ label, value, ok }) => (
              <div key={label} className="flex justify-between items-start p-2 rounded" style={{ background: 'var(--bg-secondary)' }}>
                <span style={{ color: 'var(--text-secondary)' }}>{label}</span>
                <span className={`font-medium text-right break-all ml-3 font-mono text-xs ${ok === true ? 'metric-positive' : ok === false ? 'metric-negative' : ''}`}>{String(value ?? '—')}</span>
              </div>
            ))}
          </div>

          <div>
            <div className="text-xs font-medium mb-2 mt-2" style={{ color: 'var(--text-secondary)' }}>Exempt Routes (always free)</div>
            <div className="space-y-1">
              {EXEMPT_ROUTES.map(r => (
                <div key={r.route} className="flex justify-between text-xs p-2 rounded" style={{ background: 'var(--bg-primary)' }}>
                  <code style={{ color: 'var(--accent-blue)' }}>{r.route}</code>
                  <span style={{ color: 'var(--text-secondary)' }}>{r.reason}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function StepPanel({ title, children }) {
  return (
    <div className="p-4 rounded-xl" style={{ background: 'var(--bg-secondary)', border: '1px solid var(--accent-blue)' }}>
      <div className="font-bold mb-3 text-sm" style={{ color: 'var(--accent-blue)' }}>{title}</div>
      {children}
    </div>
  )
}

function CodeBlock({ children }) {
  return (
    <pre style={{
      background: 'var(--bg-primary)',
      border: '1px solid var(--border)',
      borderRadius: 8,
      padding: '12px 16px',
      fontSize: 11,
      fontFamily: 'monospace',
      overflowX: 'auto',
      whiteSpace: 'pre-wrap',
      wordBreak: 'break-all',
      color: 'var(--text-primary)',
      lineHeight: 1.6,
    }}>
      {children}
    </pre>
  )
}

const PROVIDER_META = {
  deepseek:  { label: 'DeepSeek',  icon: '🔵', color: '#4f8ef7' },
  xai:       { label: 'xAI',       icon: '⚫', color: '#9ca3af' },
  minimax:   { label: 'MiniMax',   icon: '🪐', color: '#ff4d4f' },
}

function OpenRouterPanel() {
  const [info, setInfo] = useState(null)
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState(null)

  useEffect(() => {
    fetch(`${API_BASE}/payments/providers/openrouter`)
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json() })
      .then(setInfo)
      .catch(e => setErr(e.message))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="card" style={{ border: '1px solid rgba(16,185,129,0.3)', background: 'linear-gradient(135deg, rgba(16,185,129,0.03) 0%, var(--bg-card) 100%)' }}>
      <div className="flex flex-wrap items-start justify-between gap-4 mb-4">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <span style={{ fontSize: 24 }}>🌐</span>
            <h2 className="text-xl font-bold">OpenRouter</h2>
            <span className="px-2 py-0.5 rounded text-xs font-bold" style={{ background: 'rgba(16,185,129,0.15)', color: '#10b981' }}>
              Advanced Reasoning Priority
            </span>
          </div>
          <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
            High-reasoning models (GLM-5.1, Grok 4.20) with <strong style={{ color: 'var(--text-primary)' }}>enforced reasoning parameters</strong>.
          </p>
        </div>
      </div>

      {loading && <div className="text-sm py-4 opacity-50">Loading OpenRouter info…</div>}
      {err && <div className="text-sm py-4 text-red-500">⚠ {err}</div>}

      {info && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {info.models.map(m => (
              <div key={m.id} className="p-3 rounded-lg" style={{ background: 'var(--bg-secondary)', border: m.is_enforced ? '1px solid rgba(16,185,129,0.3)' : '1px solid var(--border)' }}>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-sm">{m.label}</span>
                    {m.is_enforced && (
                      <span className="px-1.5 py-0.5 rounded text-[8px] font-bold uppercase" style={{ background: 'rgba(16,185,129,0.15)', color: '#10b981' }}>
                        Primary
                      </span>
                    )}
                  </div>
                  {m.reasoning_enforced && (
                    <span className="px-1.5 py-0.5 rounded text-[10px] font-bold" style={{ background: 'rgba(59,130,246,0.15)', color: 'var(--accent-blue)' }}>
                      🧠 REASONING
                    </span>
                  )}
                </div>
                {m.pricing ? (
                  <div className="space-y-1">
                    <div className="flex justify-between text-[10px]">
                      <span className="opacity-50">Prompt / 1M:</span>
                      <span className="font-mono text-accent-green">${(m.pricing.prompt * 1e6).toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between text-[10px]">
                      <span className="opacity-50">Completion / 1M:</span>
                      <span className="font-mono text-accent-green">${(m.pricing.completion * 1e6).toFixed(2)}</span>
                    </div>
                  </div>
                ) : (
                  <div className="text-[10px] opacity-40 italic">Pricing data unavailable</div>
                )}
                <div className="text-[10px] font-mono opacity-40 mt-2 truncate">{m.id}</div>
              </div>
            ))}
          </div>

          <div className="pt-4 border-t" style={{ borderColor: 'var(--border)' }}>
            <div className="flex justify-between items-center text-xs">
              <span style={{ color: 'var(--text-secondary)' }}>Status: </span>
              <span className={info.configured ? 'text-green-500 font-bold' : 'text-yellow-500 font-bold'}>
                {info.configured ? 'CONFIGURED ✓' : 'KEY MISSING ✗'}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function Claw402Panel() {
  const [info, setInfo] = useState(null)
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState(null)

  useEffect(() => {
    fetch(`${API_BASE}/payments/providers/claw402`)
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json() })
      .then(setInfo)
      .catch(e => setErr(e.message))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="card" style={{ border: '1px solid rgba(99,102,241,0.4)', background: 'linear-gradient(135deg, rgba(99,102,241,0.04) 0%, var(--bg-card) 100%)' }}>
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <span style={{ fontSize: 28 }}>⚡</span>
            <h2 className="text-xl font-bold">Claw402</h2>
            <span className="px-2 py-0.5 rounded text-xs font-bold" style={{ background: 'rgba(99,102,241,0.15)', color: '#818cf8' }}>
              Built-in x402 Provider
            </span>
          </div>
          <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
            No accounts. No API keys. No prepaid credits. <strong style={{ color: 'var(--text-primary)' }}>One wallet, every model.</strong>
          </p>
        </div>
        <div className="flex gap-3 text-center">
          {[
            { v: info?.total_models ?? '15+', l: 'Models' },
            { v: 'Base',                      l: 'Chain'  },
            { v: 'USDC',                      l: 'Token'  },
          ].map(({ v, l }) => (
            <div key={l} className="px-4 py-2 rounded-xl" style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)', minWidth: 64 }}>
              <div className="text-lg font-bold" style={{ color: '#818cf8' }}>{v}</div>
              <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>{l}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Flow tagline */}
      <div className="flex flex-wrap items-center gap-2 mb-6 text-sm font-mono overflow-x-auto">
        {[
          { t: 'Request',          c: 'var(--text-secondary)' },
          { t: '→',                c: 'var(--text-secondary)', plain: true },
          { t: '402 + price',      c: '#f97316' },
          { t: '→',                c: 'var(--text-secondary)', plain: true },
          { t: 'wallet signs USDC',c: '#818cf8' },
          { t: '→',                c: 'var(--text-secondary)', plain: true },
          { t: 'retry',            c: '#60a5fa' },
          { t: '→',                c: 'var(--text-secondary)', plain: true },
          { t: 'done ✓',           c: '#34d399' },
        ].map(({ t, c, plain }, i) => (
          plain
            ? <span key={i} style={{ color: c }}>{t}</span>
            : <span key={i} className="px-2 py-0.5 rounded font-bold" style={{ background: `${c}18`, color: c, border: `1px solid ${c}33` }}>{t}</span>
        ))}
      </div>

      {/* Model grid */}
      {loading && <div className="text-sm text-center py-6 opacity-50">Loading model catalogue…</div>}
      {err    && <div className="text-sm text-center py-4" style={{ color: 'var(--accent-red)' }}>⚠ Could not load catalogue: {err}</div>}

      {info && (
        <div className="space-y-5">
          {Object.entries(info.models_by_provider).map(([providerKey, models]) => {
            const meta = PROVIDER_META[providerKey] || { label: providerKey, icon: '🤖', color: '#6b7280' }
            return (
              <div key={providerKey}>
                <div className="flex items-center gap-2 mb-2">
                  <span>{meta.icon}</span>
                  <span className="text-xs font-bold uppercase tracking-wider" style={{ color: meta.color }}>{meta.label}</span>
                  <span className="text-xs opacity-40">({models.length})</span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {models.map(m => (
                    <span
                      key={m.model_id}
                      title={m.model_id}
                      style={{
                        padding: '4px 10px',
                        borderRadius: 8,
                        background: `${meta.color}12`,
                        border: `1px solid ${meta.color}30`,
                        color: meta.color,
                        fontSize: 12,
                        fontWeight: 600,
                        cursor: 'default',
                      }}
                    >
                      {m.label}
                    </span>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Wallet status + setup */}
      <div className="mt-6 pt-5 grid grid-cols-1 md:grid-cols-2 gap-4" style={{ borderTop: '1px solid var(--border)' }}>
        {/* Wallet status */}
        <div className="p-4 rounded-xl" style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}>
          <div className="text-xs font-bold uppercase tracking-wider mb-3" style={{ color: 'var(--text-secondary)' }}>Wallet Status</div>
          <div className="space-y-2 text-xs">
            {[
              { label: 'Wallet Configured', value: info?.wallet_configured ? 'Yes ✓' : 'Not set', ok: info?.wallet_configured },
              { label: 'Wallet Address',    value: info?.wallet_address || '—', mono: true },
              { label: 'Base URL',          value: info?.base_url || '—', mono: true },
              { label: 'Auto-Pay Ceiling',  value: '$1.00 USDC / request' },
            ].map(({ label, value, ok, mono }) => (
              <div key={label} className="flex justify-between gap-2">
                <span style={{ color: 'var(--text-secondary)' }}>{label}</span>
                <span
                  className={`text-right break-all ${mono ? 'font-mono' : 'font-medium'} ${ok === true ? 'metric-positive' : ok === false ? 'metric-negative' : ''}`}
                  style={{ maxWidth: '60%' }}
                >
                  {value}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Setup guide */}
        <div className="p-4 rounded-xl" style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}>
          <div className="text-xs font-bold uppercase tracking-wider mb-3" style={{ color: 'var(--text-secondary)' }}>Setup (.env)</div>
          <CodeBlock>{`# Add to backend/.env
CLAW402_WALLET_PRIVATE_KEY=0x<hot_wallet_key>
CLAW402_MODEL=claude-opus-4-5  # default

# Then select any Claw402 model in the
# Trading Dashboard → model_1 / model_2
# e.g. model_1=claude-opus-4-5

# ⚠ Use a DEDICATED hot wallet.
#   Load only the USDC you need.`}</CodeBlock>
          <a
            href="https://claw402.com"
            target="_blank"
            rel="noopener noreferrer"
            className="mt-3 block text-center text-xs font-semibold py-2 rounded-lg"
            style={{ background: 'rgba(99,102,241,0.12)', color: '#818cf8', border: '1px solid rgba(99,102,241,0.25)' }}
          >
            claw402.com → docs &amp; getting started ↗
          </a>
        </div>
      </div>
    </div>
  )
}
